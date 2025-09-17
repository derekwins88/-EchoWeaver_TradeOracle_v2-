"""Emotional drift tracking for market sentiment."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


@dataclass
class EmotionalDrift:
    """Quantified sentiment shift metrics."""

    volatility: float
    volume_spike: float
    sentiment: float
    descriptor: str

    def to_dict(self) -> Dict[str, float]:
        return {
            "volatility": self.volatility,
            "volume_spike": self.volume_spike,
            "sentiment": self.sentiment,
            "descriptor": self.descriptor,
        }


class EmotionalDriftTracker:
    """Measures volatility- and volume-based sentiment swings."""

    def __init__(self, config: Dict[str, float]):
        self.window = int(config.get("volatility_window", 14))
        self.volume_threshold = float(config.get("volume_spike_threshold", 1.5))
        self.sentiment_smoothing = int(config.get("sentiment_smoothing", 5))

    def track(self, df: pd.DataFrame) -> EmotionalDrift:
        if len(df) < self.window + 2:
            window = max(3, len(df) // 2)
        else:
            window = self.window
        returns = df["close"].astype(float).pct_change().dropna()
        volatility = float(returns.rolling(window=window, min_periods=1).std(ddof=0).iloc[-1])
        volume = df["volume"].astype(float)
        rolling_mean = volume.rolling(window=window, min_periods=1).mean().iloc[-1]
        rolling_std = volume.rolling(window=window, min_periods=1).std(ddof=0).iloc[-1]
        if rolling_std == 0 or np.isnan(rolling_std):
            volume_spike = 0.0
        else:
            volume_spike = float((volume.iloc[-1] - rolling_mean) / rolling_std)
        sentiment_raw = np.tanh((volume_spike / max(self.volume_threshold, 1e-6)) + volatility * 10)
        sentiment_series = pd.Series(np.concatenate([[0.0], returns.values]))
        sentiment_smoothed = sentiment_series.rolling(window=self.sentiment_smoothing, min_periods=1).mean().iloc[-1]
        sentiment = float(0.7 * sentiment_raw + 0.3 * sentiment_smoothed)
        if volume_spike > self.volume_threshold and sentiment >= 0:
            descriptor = "greed"
        elif volume_spike < -self.volume_threshold:
            descriptor = "fear"
        else:
            descriptor = "watchful"
        return EmotionalDrift(
            volatility=volatility,
            volume_spike=volume_spike,
            sentiment=sentiment,
            descriptor=descriptor,
        )


__all__ = ["EmotionalDriftTracker", "EmotionalDrift"]
