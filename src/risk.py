"""Risk governance utilities for throttling trade activity."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class RiskConfig:
    """Configuration parameters for :class:`RiskGovernor`."""

    per_trade_risk_pct: float = 0.75
    daily_loss_cap_pct: float = 2.0
    weekly_loss_cap_pct: float = 5.0
    streak_downshift_losses: int = 3
    streak_multiplier: float = 0.6
    recover_wins: int = 2
    recover_step: float = 0.1
    max_multiplier: float = 1.0


class RiskGovernor:
    """Applies pre-trade checks and adaptive throttling based on realized PnL."""

    def __init__(
        self,
        cfg: RiskConfig,
        equity_fn: Callable[..., float],
        pnl_window_fn: Callable[..., float],
        streak_fn: Callable[..., int],
    ) -> None:
        self.cfg = cfg
        self.equity_fn = equity_fn
        self.pnl_window_fn = pnl_window_fn
        self.streak_fn = streak_fn

    def can_trade_now(self) -> bool:
        """Return ``True`` when daily and weekly drawdowns are within limits."""

        sod_eq = max(self.equity_fn(start_of_day=True), 1e-9)
        sow_eq = max(self.equity_fn(start_of_week=True), 1e-9)
        day_pnl = self.pnl_window_fn(window="day")
        week_pnl = self.pnl_window_fn(window="week")
        dd_day = -day_pnl / sod_eq * 100.0
        dd_week = -week_pnl / sow_eq * 100.0
        return dd_day < self.cfg.daily_loss_cap_pct and dd_week < self.cfg.weekly_loss_cap_pct

    def size_multiplier(self) -> float:
        """Return the current position multiplier based on streaks."""

        losses = self.streak_fn(kind="losses")
        wins_since_bottom = self.streak_fn(kind="wins_since_bottom")
        multiplier = self.cfg.streak_multiplier if losses >= self.cfg.streak_downshift_losses else 1.0
        if wins_since_bottom > 0:
            multiplier += wins_since_bottom * self.cfg.recover_step
        multiplier = min(multiplier, self.cfg.max_multiplier)
        return max(0.0, multiplier)


__all__ = ["RiskConfig", "RiskGovernor"]
