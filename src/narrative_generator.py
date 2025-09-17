"""Mythic narratives translating metrics into ceremonial verse."""
from __future__ import annotations

from typing import Dict, Optional

from .motif_engine import MotifSignal
from .emotional_drift import EmotionalDrift


class NarrativeGenerator:
    """Produces mythic summaries for executed rituals."""

    def __init__(self, tone: str = "mythic", include_entropy_regime: bool = True) -> None:
        self.tone = tone
        self.include_entropy_regime = include_entropy_regime

    def compose(
        self,
        symbol: str,
        motif: MotifSignal,
        drift: EmotionalDrift,
        order: Optional[Dict[str, float]],
        roi_score: float,
    ) -> str:
        motif_name = motif.name or "silence"
        order_side = order.get("side", "wait") if order else "wait"
        base = (
            f"The market whispered of {motif_name.replace('_', ' ')}, "
            f"and the Oracle answered with a {order_side} ritual on {symbol}."
        )
        drift_line = (
            f" Volatility shimmered at {drift.volatility:.4f}, volume spirits surged {drift.volume_spike:.2f} sigma, "
            f"mood drifting toward {drift.descriptor}."
        )
        roi_line = f" ROI resonance hummed at {roi_score:.4f}."
        if self.include_entropy_regime:
            regime_line = f" Entropy stood in the {motif.entropy.regime} gate."  # type: ignore[union-attr]
        else:
            regime_line = ""
        if self.tone == "mythic":
            closing = " The ledger remembers this rite." if order else " The Oracle conserved its strength."
        else:
            closing = ""
        return base + regime_line + drift_line + roi_line + closing


__all__ = ["NarrativeGenerator"]
