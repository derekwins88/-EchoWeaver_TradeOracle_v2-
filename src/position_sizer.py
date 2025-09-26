"""Volatility and conviction aware position sizing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class SizerConfig:
    base_qty: float = 1.0
    atr_lookback: int = 14
    atr_floor: float = 1e-6
    atr_ref: float = 1.0
    conviction_min: float = 0.0
    conviction_max: float = 1.0
    conviction_boost: float = 1.5
    max_qty: float = 10.0


class PositionSizer:
    """Combine ATR-based volatility scaling with conviction weighting."""

    def __init__(self, cfg: SizerConfig, atr_fn: Callable[[int], float], conviction_fn: Callable[[], float]) -> None:
        self.cfg = cfg
        self.atr_fn = atr_fn
        self.conviction_fn = conviction_fn

    def compute_qty(self) -> float:
        atr = max(self.atr_fn(self.cfg.atr_lookback), self.cfg.atr_floor)
        vol_scaler = min(self.cfg.atr_ref / atr, 3.0)
        conviction = self.conviction_fn()
        conviction = max(self.cfg.conviction_min, min(conviction, self.cfg.conviction_max))
        conviction_scaler = 1.0 + (self.cfg.conviction_boost - 1.0) * conviction
        qty = self.cfg.base_qty * vol_scaler * conviction_scaler
        return max(0.0, min(qty, self.cfg.max_qty))


__all__ = ["SizerConfig", "PositionSizer"]
