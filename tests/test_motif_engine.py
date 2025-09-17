import pandas as pd

from src.motif_engine import MotifEngine


def build_frame(prices, volumes):
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(start="2023-01-01", periods=len(prices), freq="h"),
            "open": prices,
            "high": [p * 1.01 for p in prices],
            "low": [p * 0.99 for p in prices],
            "close": prices,
            "volume": volumes,
        }
    )


def test_motif_engine_detects_bullish_reversal():
    prices = [100, 101, 102, 103, 104, 106, 108, 110, 112, 115]
    volumes = [100, 110, 120, 130, 140, 150, 160, 200, 220, 250]
    frame = build_frame(prices, volumes)
    motif_config = {
        "bullish_reversal": {"min_entropy": 0.0, "ema_fast": 3, "ema_slow": 5},
        "bearish_reversal": {"max_entropy": 1.0, "ema_fast": 3, "ema_slow": 5},
    }
    entropy_config = {"collapse_threshold": 0.2, "expansion_threshold": 0.8, "histogram_bins": 8}
    engine = MotifEngine(motif_config, entropy_config)
    signal = engine.detect(frame)
    assert signal.name == "bullish_reversal"
    assert signal.confidence > 0
    assert 0 <= signal.entropy.value <= 1
