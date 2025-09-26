"""Rolling walk-forward evaluation harness with simple KPIs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, Iterator, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import yaml

from src.metrics import cagr, mar, max_drawdown, sharpe, sortino, tail_loss, ulcer_index


def _seed_offset(start: str, end: str) -> int:
    payload = f"{start}-{end}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:8]
    return int(digest, 16)


def run_backtest(cfg: Dict[str, object], start: str, end: str, seed: int) -> Dict[str, Sequence[float]]:
    """Deterministic pseudo backtest producing synthetic equity curves.

    The repository does not ship a full execution engine, so we emulate
    equity progression with a seeded Gaussian walk.  Consumers can replace
    this function with a call into their actual backtest entrypoint.
    """

    horizon = int(cfg.get("simulation", {}).get("bars", 180))
    seed_with_offset = seed + _seed_offset(start, end)
    rng = np.random.default_rng(seed_with_offset)
    drift = float(cfg.get("simulation", {}).get("expected_return", 0.001))
    vol = float(cfg.get("simulation", {}).get("volatility", 0.01))
    returns = rng.normal(loc=drift, scale=vol, size=horizon)
    equity_curve = 100000.0 * np.cumprod(1.0 + returns)
    return {"equity_curve": equity_curve, "returns": returns}


def date_slices(dates: Sequence[str], train_ratio: float = 0.7, step: float = 0.1) -> Iterator[Tuple[Tuple[str, str], Tuple[str, str]]]:
    ordered = list(dates)
    if len(ordered) < 2:
        return iter(())
    window = max(1, int(len(ordered) * train_ratio))
    stride = max(1, int(len(ordered) * step))
    stops = len(ordered) - window - 1
    if stops <= 0:
        return iter(((ordered[0], ordered[window - 1]), (ordered[window - 1], ordered[-1])),)

    slices: List[Tuple[Tuple[str, str], Tuple[str, str]]] = []
    for start in range(0, stops + 1, stride):
        train = (ordered[start], ordered[start + window - 1])
        test = (ordered[start + window], ordered[min(len(ordered) - 1, start + window + stride - 1)])
        slices.append((train, test))
    return iter(slices)


def kpis(equity_curve: Sequence[float], returns: Sequence[float]) -> Dict[str, float]:
    return {
        "CAGR": cagr(equity_curve),
        "Sharpe": sharpe(returns),
        "Sortino": sortino(returns),
        "MAR": mar(equity_curve),
        "MaxDD": max_drawdown(equity_curve),
        "Ulcer": ulcer_index(equity_curve),
        "TailLoss5": tail_loss(returns, 0.95),
    }


def load_config(path: str) -> Dict[str, object]:
    with open(path, "r", encoding="utf-8") as handle:
        if path.endswith(".json"):
            return json.load(handle)
        return yaml.safe_load(handle)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Rolling walk-forward evaluation")
    parser.add_argument("--config", default="config/strategy.yaml", help="Path to strategy config")
    parser.add_argument("--dates", required=True, help="Comma separated YYYY-MM-DD boundaries")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--outdir", default="artifacts/wfo", help="Directory for CSV output")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--step", type=float, default=0.1)
    args = parser.parse_args(argv)

    os.makedirs(args.outdir, exist_ok=True)
    cfg = load_config(args.config)
    dates = [d for d in args.dates.split(",") if d]

    rows: List[Dict[str, object]] = []
    for (train_start, train_end), (test_start, test_end) in date_slices(dates, args.train_ratio, args.step):
        train_result = run_backtest(cfg, train_start, train_end, args.seed)
        test_result = run_backtest(cfg, test_start, test_end, args.seed)
        metrics = kpis(test_result["equity_curve"], test_result["returns"])
        rows.append({
            "train_start": train_start,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end,
            **metrics,
        })

    if not rows:
        print("No walk-forward slices generated")
        return

    out_csv = os.path.join(args.outdir, "summary.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"WFO written: {out_csv}")


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
