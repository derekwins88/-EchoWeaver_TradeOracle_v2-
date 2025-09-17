"""Motif detection and entropy-aware pattern logic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

from .entropy import EntropyRegimeClassifier, EntropySnapshot


@dataclass
class MotifSignal:
    """Structured motif information returned by the :class:`MotifEngine`."""

    name: Optional[str]
    entropy: EntropySnapshot
    confidence: float
    metadata: Dict[str, float]


class MotifEngine:
    """Detects narrative motifs from price/volume series."""

    def __init__(self, motif_config: Dict[str, Dict[str, float]], entropy_config: Dict[str, float]):
        self.config = motif_config
        self.entropy_config = entropy_config
        self.entropy_classifier = EntropyRegimeClassifier(
            collapse_threshold=entropy_config.get("collapse_threshold", 0.25),
            expansion_threshold=entropy_config.get("expansion_threshold", 0.75),
            bins=int(entropy_config.get("histogram_bins", 10)),
        )

    def detect(self, df: pd.DataFrame) -> MotifSignal:
        if df.empty:
            raise ValueError("Price frame is empty; motifs cannot be summoned")
        closes = df["close"].astype(float)
        entropy = self.entropy_classifier.compute(closes)
        ema_fast = closes.ewm(span=int(self.config["bullish_reversal"]["ema_fast"]), adjust=False).mean()
        ema_slow = closes.ewm(span=int(self.config["bullish_reversal"]["ema_slow"]), adjust=False).mean()
        ema_diff = float(ema_fast.iloc[-1] - ema_slow.iloc[-1])
        ema_ratio = float(ema_fast.iloc[-1] / (ema_slow.iloc[-1] + 1e-12) - 1)
        volume = df["volume"].astype(float)
        if len(volume) < 3:
            volume_z = 0.0
        else:
            volume_mean = volume.rolling(window=min(20, len(volume)), min_periods=3).mean()
            volume_std = volume.rolling(window=min(20, len(volume)), min_periods=3).std(ddof=0)
            latest_mean = (
                float(volume_mean.iloc[-1])
                if not np.isnan(volume_mean.iloc[-1])
                else float(volume.mean())
            )
            latest_std = (
                float(volume_std.iloc[-1])
                if not np.isnan(volume_std.iloc[-1])
                else float(volume.std(ddof=0) + 1e-12)
            )
            if latest_std == 0:
                volume_z = 0.0
            else:
                volume_z = float((volume.iloc[-1] - latest_mean) / latest_std)
        motif_name: Optional[str] = None
        confidence = 0.0
        if ema_diff > 0 and entropy.value >= self.config["bullish_reversal"].get("min_entropy", 0):
            motif_name = "bullish_reversal"
            confidence = self._confidence(ema_ratio, volume_z)
        elif ema_diff < 0 and entropy.value <= self.config["bearish_reversal"].get("max_entropy", 1):
            motif_name = "bearish_reversal"
            confidence = self._confidence(-ema_ratio, -volume_z)
        metadata = {
            "ema_fast": float(ema_fast.iloc[-1]),
            "ema_slow": float(ema_slow.iloc[-1]),
            "ema_ratio": ema_ratio,
            "ema_diff": ema_diff,
            "volume_z": volume_z,
        }
        metadata["expected_return"] = float(np.tanh(ema_ratio * 3))
        return MotifSignal(
            name=motif_name,
            entropy=entropy,
            confidence=float(np.clip(confidence, 0.0, 1.0)),
            metadata=metadata,
        )

    @staticmethod
    def _confidence(trend_ratio: float, volume_z: float) -> float:
        momentum_component = np.clip(trend_ratio, -1.0, 1.0)
        volume_component = np.clip(volume_z / 5.0, -1.0, 1.0)
        return float(np.clip(0.5 + 0.5 * (momentum_component + volume_component) / 2.0, 0.0, 1.0))


__all__ = ["MotifEngine", "MotifSignal"]
