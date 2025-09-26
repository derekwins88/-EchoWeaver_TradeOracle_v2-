from pathlib import Path

import pandas as pd
import yaml

from src.exchange import PaperExchange
from src.mnemonic_capsule import MnemonicCapsule
from src.oracle import TradeOracle


def synthetic_frame() -> pd.DataFrame:
    prices = [100 + i for i in range(40)]
    volumes = [150 + (i % 5) * 10 for i in range(40)]
    return pd.DataFrame(
        {
            "timestamp": pd.date_range(start="2023-01-01", periods=len(prices), freq="h"),
            "open": prices,
            "high": [p * 1.02 for p in prices],
            "low": [p * 0.98 for p in prices],
            "close": prices,
            "volume": volumes,
        }
    )


def test_oracle_ritualizes_and_returns_capsule(tmp_path):
    config_path = "config/strategy.yaml"
    oracle = TradeOracle(config_path, exchange=PaperExchange(seed=5), capsule_enabled=False)
    frame = synthetic_frame()
    report = oracle.ritualize(frame, symbol="BTC/USDT", persist_capsule=False)
    assert report["motif"].entropy.value >= 0
    assert "ROI resonance" in report["narrative"] or "ROI" in report["narrative"]
    if report["order"]:
        capsule = oracle.capsules.encode(
            symbol="BTC/USDT",
            motif=report["motif"].name,
            entropy_regime=report["motif"].entropy.regime,
            roi_score=report["roi_score"],
            order=report["order"],
            drift=report["drift"].to_dict(),
            narrative=report["narrative"],
        )
        path = tmp_path / "capsules.jsonl"
        writer = MnemonicCapsule(str(path), enabled=True)
        writer.save(capsule)
        assert path.exists()


def test_backtest_exports_daily_roi(tmp_path):
    base_config = yaml.safe_load(Path("config/strategy.yaml").read_text())
    metrics_path = tmp_path / "metrics.csv"
    base_config["metrics"] = {
        "initial_cash": 50_000,
        "export_csv": True,
        "output_path": str(metrics_path),
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(base_config))
    oracle = TradeOracle(str(config_path), exchange=PaperExchange(seed=11), capsule_enabled=False)
    frame = synthetic_frame()
    oracle.backtest(frame, symbol="BTC/USDT")
    assert metrics_path.exists()
    lines = [line for line in metrics_path.read_text().splitlines() if line]
    assert lines[0] == "date,sod_equity,eod_equity,day_pnl,day_roi"
    assert len(lines) >= 2  # header + at least one trading day entry
    adr = oracle.performance.average_daily_return()
    assert isinstance(adr, float)
