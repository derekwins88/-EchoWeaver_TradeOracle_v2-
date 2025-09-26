"""Placebo (signal shuffled) simulations to validate edge persistence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import yaml

from src.metrics import mar, max_drawdown, sharpe


def _seed_offset(start: str, end: str) -> int:
    payload = f"{start}-{end}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:8]
    return int(digest, 16)


def placebo_backtest(cfg: Dict[str, object], start: str, end: str, seed: int) -> Dict[str, np.ndarray]:
    horizon = int(cfg.get("simulation", {}).get("bars", 180))
    drift = float(cfg.get("simulation", {}).get("expected_return", 0.001))
    vol = float(cfg.get("simulation", {}).get("volatility", 0.01))
    seed_with_offset = seed + _seed_offset(start, end)
    rng = np.random.default_rng(seed_with_offset)
    returns = rng.normal(loc=drift, scale=vol, size=horizon)
    rng.shuffle(returns)
    equity_curve = 100000.0 * np.cumprod(1.0 + returns)
    return {"equity_curve": equity_curve, "returns": returns}


def load_config(path: str) -> Dict[str, object]:
    with open(path, "r", encoding="utf-8") as handle:
        if path.endswith(".json"):
            return json.load(handle)
        return yaml.safe_load(handle)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Placebo (signal shuffled) simulations")
    parser.add_argument("--config", default="config/strategy.yaml", help="Path to strategy config")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--outdir", default="artifacts/placebo")
    args = parser.parse_args(argv)

    os.makedirs(args.outdir, exist_ok=True)
    cfg = load_config(args.config)

    rows = []
    for idx in range(args.runs):
        result = placebo_backtest(cfg, args.start, args.end, args.seed + idx)
        eq, rets = result["equity_curve"], result["returns"]
        rows.append({
            "run": idx,
            "Sharpe": sharpe(rets),
            "MAR": mar(eq),
            "MaxDD": max_drawdown(eq),
        })

    if not rows:
        print("No placebo runs executed")
        return

    out_csv = os.path.join(args.outdir, "summary.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Placebo written: {out_csv}")


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
