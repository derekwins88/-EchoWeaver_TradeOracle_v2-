#!/usr/bin/env python3
"""CLI entrypoint for the TradeOracle Live Pipe."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

import yaml

from stream.live_pipe import LivePipe, PipeConfig
from stream.oracle_adapter import OracleAdapter


class DemoOracle:
    """Placeholder oracle used for local smoke tests."""

    def handle_signal(self, payload):  # pragma: no cover - simple demo shim
        return {"status": "accepted"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the TradeOracle Live Pipe")
    parser.add_argument(
        "--config",
        default="config/live_pipe.yaml",
        help="Path to the pipe configuration file",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    with open(args.config, "r", encoding="utf-8") as handle:
        cfg = PipeConfig(**yaml.safe_load(handle))

    oracle = DemoOracle()
    adapter = OracleAdapter(oracle)
    LivePipe(cfg, adapter).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
