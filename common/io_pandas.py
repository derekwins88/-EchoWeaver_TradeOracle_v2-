from __future__ import annotations

from dataclasses import asdict
from typing import List

import pandas as pd

from .io_loader import AllocationItem, PortfolioAllocation, Signal, StrategyReturn, TradeEvent


def signals_to_df(rows: List[Signal]) -> pd.DataFrame:
    return pd.DataFrame([asdict(row) for row in rows])


def trade_events_to_df(rows: List[TradeEvent]) -> pd.DataFrame:
    return pd.DataFrame([asdict(row) for row in rows])


def strategy_returns_to_df(rows: List[StrategyReturn]) -> pd.DataFrame:
    return pd.DataFrame([asdict(row) for row in rows])


def allocation_to_df(allocation: PortfolioAllocation) -> pd.DataFrame:
    return pd.DataFrame([asdict(item) for item in allocation.allocations])
