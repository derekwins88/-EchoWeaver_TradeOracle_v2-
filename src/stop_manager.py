"""Exit intent generation for managing open positions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass
class ExitConfig:
    r1_partial: float = 1.0
    r2_partial: float = 2.0
    trail_atr_mult: float = 1.5
    entropy_fail_safe: float = 0.65
    flip_on_regime_change: bool = True
    partial_pct: float = 0.25


class StopManager:
    """Derive exit intents using R-multiples, ATR trailing and fail-safes."""

    def __init__(
        self,
        cfg: ExitConfig,
        entropy_fn: Callable[[], float],
        regime_fn: Callable[[], str],
        atr_fn: Callable[[int], float],
    ) -> None:
        self.cfg = cfg
        self.entropy_fn = entropy_fn
        self.regime_fn = regime_fn
        self.atr_fn = atr_fn

    def update(
        self,
        entry_price: float,
        stop_price: float,
        last_price: float,
        risk_per_unit: float,
        side: str,
    ) -> Optional[Dict[str, object]]:
        intents = []
        r_gain = (last_price - entry_price) if side == "long" else (entry_price - last_price)
        if risk_per_unit <= 0:
            risk_per_unit = 1e-9
        r_multiple = r_gain / risk_per_unit

        if r_multiple >= self.cfg.r1_partial:
            intents.append({"action": "reduce", "pct": self.cfg.partial_pct, "tag": "R1"})
        if r_multiple >= self.cfg.r2_partial:
            intents.append({"action": "reduce", "pct": self.cfg.partial_pct, "tag": "R2"})

        atr = self.atr_fn(14)
        if side == "long":
            trail = last_price - self.cfg.trail_atr_mult * atr
            if trail > stop_price:
                intents.append({"action": "move_stop", "to": trail, "tag": "trail"})
        else:
            trail = last_price + self.cfg.trail_atr_mult * atr
            if trail < stop_price:
                intents.append({"action": "move_stop", "to": trail, "tag": "trail"})

        if self.entropy_fn() >= self.cfg.entropy_fail_safe:
            intents.append({"action": "exit_all", "tag": "entropy_spike"})
        if self.cfg.flip_on_regime_change and self.regime_fn() == "unfavorable":
            intents.append({"action": "exit_all", "tag": "regime_flip"})

        return {"intents": intents} if intents else None


__all__ = ["ExitConfig", "StopManager"]
