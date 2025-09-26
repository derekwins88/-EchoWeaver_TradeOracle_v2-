#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.io_loader import (
    AllocationItem,
    PortfolioAllocation,
    Signal,
    StrategyReturn,
    TradeEvent,
    read_allocation_json,
    read_signals_ndjson,
    read_strategy_returns_ndjson,
    read_trade_events_ndjson,
    write_allocation_json,
    write_signals_ndjson,
    write_strategy_returns_ndjson,
    write_trade_events_ndjson,
)


def cmd_validate(args: argparse.Namespace) -> None:
    if args.kind == "signals":
        read_signals_ndjson(args.path)
    elif args.kind == "events":
        read_trade_events_ndjson(args.path)
    elif args.kind == "returns":
        read_strategy_returns_ndjson(args.path)
    elif args.kind == "alloc":
        read_allocation_json(args.path)
    print("✅ valid:", args.path)


def cmd_summarize(args: argparse.Namespace) -> None:
    if args.kind == "returns":
        rows = read_strategy_returns_ndjson(args.path)
        pnl = [row.pnl for row in rows]
        equity = [row.equity for row in rows]
        print(
            "n={n}  pnl_sum={pnl_sum:.2f}  pnl_mean={pnl_mean:.2f}  eq_last={eq_last}".format(
                n=len(rows),
                pnl_sum=sum(pnl) if pnl else 0.0,
                pnl_mean=statistics.mean(pnl) if pnl else 0.0,
                eq_last=equity[-1] if equity else "—",
            )
        )
    elif args.kind == "events":
        rows = read_trade_events_ndjson(args.path)
        by_event: dict[str, int] = {}
        for row in rows:
            by_event[row.event] = by_event.get(row.event, 0) + 1
        print("counts:", json.dumps(by_event, indent=2))
    else:
        print(f"No summary implemented for {args.kind}", file=sys.stderr)


def cmd_convert(args: argparse.Namespace) -> None:
    if args.kind == "alloc":
        rows = read_strategy_returns_ndjson(args.path)
        weights: dict[tuple[str, str], float] = {}
        for row in rows:
            key = (row.strategy, row.symbol)
            sharpe = row.sharpe if row.sharpe is not None and row.sharpe > 0 else 1.0
            weights[key] = weights.get(key, 0.0) + sharpe
        total = sum(weights.values()) or 1.0
        allocations = [
            AllocationItem(strategy=strategy, symbol=symbol, weight=value / total)
            for (strategy, symbol), value in weights.items()
        ]
        allocation = PortfolioAllocation(
            id=args.alloc_id, timestamp=args.timestamp, allocations=allocations
        )
        write_allocation_json(args.out, allocation, add_hash=True)
        print("Wrote allocation:", args.out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--kind", choices=["signals", "events", "returns", "alloc"], required=True)
    validate.add_argument("--path", required=True)
    validate.set_defaults(func=cmd_validate)

    summarize = sub.add_parser("summarize")
    summarize.add_argument("--kind", choices=["events", "returns"], required=True)
    summarize.add_argument("--path", required=True)
    summarize.set_defaults(func=cmd_summarize)

    convert = sub.add_parser("convert")
    convert.add_argument("--kind", choices=["alloc"], required=True)
    convert.add_argument("--path", required=True, help="strategy_returns.ndjson")
    convert.add_argument("--alloc-id", required=True)
    convert.add_argument("--timestamp", required=True)
    convert.add_argument("--out", required=True)
    convert.set_defaults(func=cmd_convert)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
