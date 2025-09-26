"""Smoke tests for :mod:`src.metrics`."""
from __future__ import annotations

import numpy as np

from src.metrics import cagr, mar, max_drawdown


def test_metrics_are_positive_on_rising_curve() -> None:
    curve = np.array([100.0, 105.0, 110.0, 120.0, 125.0], dtype=float)
    returns = np.diff(curve) / curve[:-1]
    assert max_drawdown(curve) <= 0.0
    assert mar(curve) > 0.0
    assert cagr(curve) > 0.0
    # Sharpe/Sortino not explicitly tested here but we ensure returns > 0
    assert returns.mean() > 0
