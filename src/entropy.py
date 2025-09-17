"""Entropy collapse logic inspired by living-engine-sdk."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass
class EntropySnapshot:
    """Container describing the entropy state of a price series."""

    value: float
    regime: str


class EntropyRegimeClassifier:
    """Approximate entropy collapse logic inspired by living-engine-sdk."""

    def __init__(
        self,
        collapse_threshold: float,
        expansion_threshold: float,
        bins: int = 10,
    ) -> None:
        if not 0 < collapse_threshold < expansion_threshold <= 1.0:
            raise ValueError("Entropy thresholds must satisfy 0 < collapse < expansion <= 1")
        if bins <= 1:
            raise ValueError("Entropy histogram requires at least two bins")
        self.collapse_threshold = collapse_threshold
        self.expansion_threshold = expansion_threshold
        self.bins = bins

    def compute(self, prices: Iterable[float]) -> EntropySnapshot:
        prices_array = np.asarray(list(prices), dtype=float)
        if prices_array.size < 3:
            raise ValueError("At least three prices are required to compute entropy")
        log_returns = np.diff(np.log(prices_array + 1e-12))
        hist, _ = np.histogram(log_returns, bins=self.bins, density=True)
        hist = hist[hist > 0]
        if hist.size == 0:
            normalized_entropy = 0.0
        else:
            entropy = -np.sum(hist * np.log(hist))
            normalized_entropy = float(entropy / np.log(self.bins))
        normalized_entropy = float(np.clip(normalized_entropy, 0.0, 1.0))
        regime = self.classify(normalized_entropy)
        return EntropySnapshot(value=normalized_entropy, regime=regime)

    def classify(self, entropy_value: float) -> str:
        if entropy_value <= self.collapse_threshold:
            return "collapsed"
        if entropy_value >= self.expansion_threshold:
            return "expansion"
        return "neutral"


__all__ = ["EntropySnapshot", "EntropyRegimeClassifier"]
