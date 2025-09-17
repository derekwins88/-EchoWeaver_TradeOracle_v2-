"""ROI resonance scoring to evaluate ritual outcomes."""
from __future__ import annotations

from typing import Dict

from .motif_engine import MotifSignal
from .emotional_drift import EmotionalDrift


class ROIResonanceScorer:
    """Scores trades using a weighted resonance metric."""

    def __init__(self, config: Dict[str, float]):
        self.profit_weight = float(config.get("profit_weight", 0.6))
        self.risk_weight = float(config.get("risk_weight", 0.3))
        self.conviction_weight = float(config.get("conviction_weight", 0.1))

    def score_trade(
        self,
        order: Dict[str, float],
        price_context: Dict[str, float],
        motif: MotifSignal,
        drift: EmotionalDrift,
    ) -> float:
        order_price = float(order.get("price", price_context.get("close", 0)))
        projected_price = float(price_context.get("projected_price", order_price))
        side = order.get("side", "buy")
        if order_price <= 0:
            return 0.0
        raw_return = (projected_price - order_price) / order_price
        if side == "sell":
            raw_return *= -1
        risk_penalty = drift.volatility
        conviction_bonus = order.get("confidence", motif.confidence)
        resonance = (
            self.profit_weight * raw_return
            - self.risk_weight * risk_penalty
            + self.conviction_weight * conviction_bonus
        )
        return float(resonance)


__all__ = ["ROIResonanceScorer"]
