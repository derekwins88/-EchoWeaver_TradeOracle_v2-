import pandas as pd

from src.emotional_drift import EmotionalDriftTracker


def test_emotional_drift_descriptor_changes_with_volume():
    prices = [100 + (i * 0.5) for i in range(20)]
    volumes = [100] * 19 + [1000]
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range(start="2023-01-01", periods=20, freq="h"),
            "open": prices,
            "high": [p * 1.01 for p in prices],
            "low": [p * 0.99 for p in prices],
            "close": prices,
            "volume": volumes,
        }
    )
    tracker = EmotionalDriftTracker({"volatility_window": 5, "volume_spike_threshold": 2.0})
    drift = tracker.track(frame)
    assert drift.volume_spike > 0
    assert drift.descriptor in {"greed", "fear", "watchful"}
