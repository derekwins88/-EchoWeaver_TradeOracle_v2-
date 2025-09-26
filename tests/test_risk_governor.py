"""Unit tests for :mod:`src.risk`."""
from __future__ import annotations

from src.risk import RiskConfig, RiskGovernor


def _make_adapters(
    day_equity: float = 100_000.0,
    week_equity: float = 100_000.0,
    day_pnl: float = -1_000.0,
    week_pnl: float = -1_000.0,
    losses: int = 0,
    wins_since_bottom: int = 0,
):
    def equity_fn(start_of_day: bool = False, start_of_week: bool = False) -> float:
        if start_of_day:
            return day_equity
        if start_of_week:
            return week_equity
        return day_equity

    def pnl_window_fn(window: str = "day") -> float:
        return day_pnl if window == "day" else week_pnl

    def streak_fn(kind: str = "losses") -> int:
        if kind == "losses":
            return losses
        return wins_since_bottom

    return equity_fn, pnl_window_fn, streak_fn


def test_can_trade_respects_daily_cap() -> None:
    equity_fn, pnl_fn, streak_fn = _make_adapters(day_pnl=-2_500.0, day_equity=100_000.0)
    governor = RiskGovernor(RiskConfig(daily_loss_cap_pct=2.0), equity_fn, pnl_fn, streak_fn)
    assert governor.can_trade_now() is False


def test_multiplier_recovers_after_wins() -> None:
    equity_fn, pnl_fn, streak_fn = _make_adapters(losses=3, wins_since_bottom=2)
    governor = RiskGovernor(
        RiskConfig(
            streak_downshift_losses=3,
            streak_multiplier=0.6,
            recover_step=0.1,
            max_multiplier=1.0,
        ),
        equity_fn,
        pnl_fn,
        streak_fn,
    )
    assert abs(governor.size_multiplier() - 0.8) < 1e-9
