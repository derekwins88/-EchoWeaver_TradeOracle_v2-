"""Generate ROI resonance visualization for CI artifacts."""
from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import kaleido

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.exchange import PaperExchange  # noqa: E402
from src.oracle import TradeOracle  # noqa: E402


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    config_path = root / "config" / "strategy.yaml"
    try:
        kaleido.get_chrome_sync()  # Ensure bundled Chromium is available
    except Exception:
        pass
    oracle = TradeOracle(str(config_path), exchange=PaperExchange(seed=11), capsule_enabled=False)
    frame = oracle.fetch_market_frame("BTC/USDT", timeframe="1h", limit=200)
    backtest = oracle.backtest(frame, symbol="BTC/USDT")
    artifacts_dir = root / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    fig = px.line(backtest, x="timestamp", y="roi_score", title="EchoWeaver ROI Resonance (CI)")
    fig.update_layout(template="plotly_dark")
    png_path = artifacts_dir / "ci_trade_resonance.png"
    try:
        fig.write_image(str(png_path))
    except Exception:  # pragma: no cover - fallback for headless environments
        import matplotlib.pyplot as plt

        plt.figure(figsize=(10, 4))
        plt.plot(backtest["timestamp"], backtest["roi_score"], color="#8b5cf6")
        plt.title("EchoWeaver ROI Resonance (fallback)")
        plt.xlabel("Timestamp")
        plt.ylabel("ROI score")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(png_path, dpi=200)
        plt.close()
    backtest.to_csv(artifacts_dir / "ci_backtest.csv", index=False)


if __name__ == "__main__":
    main()
