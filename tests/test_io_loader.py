from __future__ import annotations

from pathlib import Path

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


def test_signal_roundtrip(tmp_path: Path) -> None:
    signal = Signal(
        id="sig1",
        timestamp="2025-09-25T00:00:00Z",
        symbol="NQ",
        side="LONG",
        confidence=0.8,
        entropy_score=0.3,
        regime_state="trend_up",
    ).with_hash()
    path = tmp_path / "signals.ndjson"
    write_signals_ndjson(path, [signal])
    rows = read_signals_ndjson(path)
    assert rows[0].id == "sig1"
    assert rows[0].hash and rows[0].hash.startswith("sha256:")


def test_allocation_sum(tmp_path: Path) -> None:
    allocation = PortfolioAllocation(
        id="alloc1",
        timestamp="2025-09-25T00:00:00Z",
        allocations=[
            AllocationItem(strategy="A", symbol="CL", weight=0.6),
            AllocationItem(strategy="B", symbol="NQ", weight=0.4),
        ],
    ).with_hash()
    path = tmp_path / "alloc.json"
    write_allocation_json(path, allocation)
    loaded = read_allocation_json(path)
    assert loaded.hash and loaded.hash.startswith("sha256:")


def test_events_returns(tmp_path: Path) -> None:
    events_path = tmp_path / "events.ndjson"
    returns_path = tmp_path / "returns.ndjson"

    event = TradeEvent(
        id="e1",
        timestamp="2025-09-25T00:00:01Z",
        symbol="CL",
        event="ENTER",
        side="LONG",
        qty=1,
        price=80.1,
    )
    write_trade_events_ndjson(events_path, [event])
    assert len(read_trade_events_ndjson(events_path)) == 1

    strategy_return = StrategyReturn(
        id="r1",
        timestamp="2025-09-25T00:30:00Z",
        strategy="Sigma",
        symbol="CL",
        pnl=50.0,
        equity=100050.0,
    )
    write_strategy_returns_ndjson(returns_path, [strategy_return])
    loaded_returns = read_strategy_returns_ndjson(returns_path)
    assert loaded_returns[0].strategy == "Sigma"
