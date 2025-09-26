"""Performance metrics for evaluating strategy runs."""
from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np


def _as_array(values: Sequence[float] | Iterable[float]) -> np.ndarray:
    if isinstance(values, np.ndarray):
        return values.astype(float, copy=False)
    return np.asarray(list(values), dtype=float)


def cagr(equity_curve: Sequence[float] | Iterable[float], periods_per_year: int = 252) -> float:
    curve = _as_array(equity_curve)
    if curve.size == 0:
        return 0.0
    start, end = curve[0], curve[-1]
    years = max(1e-9, curve.size / periods_per_year)
    return float((end / max(start, 1e-9)) ** (1 / years) - 1.0)


def drawdown_curve(equity_curve: Sequence[float] | Iterable[float]) -> np.ndarray:
    curve = _as_array(equity_curve)
    if curve.size == 0:
        return np.asarray([], dtype=float)
    peaks = np.maximum.accumulate(curve)
    return (curve - peaks) / np.maximum(peaks, 1e-9)


def max_drawdown(equity_curve: Sequence[float] | Iterable[float]) -> float:
    dd = drawdown_curve(equity_curve)
    return float(dd.min() if dd.size else 0.0)


def ulcer_index(equity_curve: Sequence[float] | Iterable[float]) -> float:
    dd = drawdown_curve(equity_curve)
    if dd.size == 0:
        return 0.0
    return float(math.sqrt(np.mean((dd * 100.0) ** 2)))


def sharpe(returns: Sequence[float] | Iterable[float], rf: float = 0.0, periods_per_year: int = 252) -> float:
    rets = _as_array(returns)
    if rets.size == 0:
        return 0.0
    excess = np.mean(rets) - rf / periods_per_year
    sd = np.std(rets, ddof=1) + 1e-12
    return float(math.sqrt(periods_per_year) * excess / sd)


def sortino(returns: Sequence[float] | Iterable[float], rf: float = 0.0, periods_per_year: int = 252) -> float:
    rets = _as_array(returns)
    if rets.size == 0:
        return 0.0
    excess = np.mean(rets) - rf / periods_per_year
    downside = np.std(np.clip(rets, None, 0.0), ddof=1) + 1e-12
    return float(math.sqrt(periods_per_year) * excess / downside)


def mar(equity_curve: Sequence[float] | Iterable[float], periods_per_year: int = 252) -> float:
    curve = _as_array(equity_curve)
    if curve.size == 0:
        return 0.0
    growth = cagr(curve, periods_per_year)
    mdd = abs(max_drawdown(curve)) + 1e-12
    return float(growth / mdd)


def tail_loss(returns: Sequence[float] | Iterable[float], q: float = 0.95) -> float:
    rets = _as_array(returns)
    if rets.size == 0:
        return 0.0
    q = max(0.0, min(q, 1.0))
    return float(np.quantile(rets, 1 - q))


__all__ = [
    "cagr",
    "drawdown_curve",
    "max_drawdown",
    "ulcer_index",
    "sharpe",
    "sortino",
    "mar",
    "tail_loss",
]
