from __future__ import annotations

import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "scripts/io_cli.py", *args], check=False, text=True)


def test_cli_validate_samples() -> None:
    assert run_cli("validate", "--kind", "signals", "--path", "samples/brain_signals.ndjson").returncode == 0
    assert run_cli("validate", "--kind", "events", "--path", "samples/trade_events.ndjson").returncode == 0
    assert run_cli("validate", "--kind", "returns", "--path", "samples/strategy_returns.ndjson").returncode == 0
    assert run_cli("validate", "--kind", "alloc", "--path", "samples/portfolio_allocation.json").returncode == 0
