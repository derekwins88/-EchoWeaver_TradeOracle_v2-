"""Exchange helpers including a deterministic paper exchange."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

import numpy as np

try:  # pragma: no cover - optional dependency guard
    import ccxt  # type: ignore
except Exception:  # pragma: no cover
    ccxt = None


@dataclass
class OhlcvBar:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    def as_list(self) -> List[float]:
        return [self.timestamp, self.open, self.high, self.low, self.close, self.volume]


class PaperExchange:
    """Deterministic OHLCV generator for offline simulations."""

    def __init__(self, seed: int = 0):
        self.random = np.random.default_rng(seed)

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 120) -> List[List[float]]:
        base_price = 20000 + self.random.integers(-500, 500)
        bars: List[OhlcvBar] = []
        current = float(base_price)
        timestamp = datetime.utcnow() - timedelta(minutes=limit)
        for _ in range(limit):
            drift = self.random.normal(0, 0.003)
            current *= (1 + drift)
            high = current * (1 + abs(self.random.normal(0, 0.002)))
            low = current * (1 - abs(self.random.normal(0, 0.002)))
            volume = float(abs(self.random.normal(1_000, 150)))
            bar = OhlcvBar(
                timestamp=int(timestamp.timestamp() * 1000),
                open=float(current / (1 + drift)),
                high=float(high),
                low=float(low),
                close=float(current),
                volume=volume,
            )
            bars.append(bar)
            timestamp += timedelta(minutes=1)
        return [bar.as_list() for bar in bars]

    def create_market_buy_order(self, symbol: str, amount: float) -> dict:  # pragma: no cover - trivial
        price = float(self.random.uniform(0.95, 1.05))
        return {"symbol": symbol, "side": "buy", "amount": amount, "price": price}

    def create_market_sell_order(self, symbol: str, amount: float) -> dict:  # pragma: no cover - trivial
        price = float(self.random.uniform(0.95, 1.05))
        return {"symbol": symbol, "side": "sell", "amount": amount, "price": price}


def build_exchange(config: dict):
    """Instantiate a CCXT exchange when available, otherwise :class:`PaperExchange`."""

    if config.get("enable_paper", False) or ccxt is None:
        return PaperExchange(seed=config.get("seed", 0))
    exchange_name = config.get("name", "binance")
    exchange_class = getattr(ccxt, exchange_name)
    exchange = exchange_class({
        "enableRateLimit": True,
    })
    if config.get("sandbox_mode"):
        exchange.set_sandbox_mode(True)
    api_key = config.get("api_key")
    secret = config.get("secret")
    if api_key and secret:
        exchange.apiKey = api_key
        exchange.secret = secret
    return exchange


__all__ = ["PaperExchange", "build_exchange"]
