"""Core oracle orchestrating motifs, entropy, and rituals."""
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd
import yaml

from .emotional_drift import EmotionalDriftTracker
from .exchange import PaperExchange, build_exchange
from .mnemonic_capsule import MnemonicCapsule
from .motif_engine import MotifEngine, MotifSignal
from .narrative_generator import NarrativeGenerator
from .roi_scorer import ROIResonanceScorer


class TradeOracle:
    """Mythic trading oracle coordinating motif detection and execution."""

    def __init__(
        self,
        config_path: str,
        exchange=None,
        capsule_enabled: bool = True,
    ) -> None:
        with open(config_path, "r", encoding="utf-8") as handle:
            self.config = yaml.safe_load(handle)
        motif_config = self.config.get("motif_gates", {})
        entropy_config = self.config.get("entropy", {})
        self.motif_engine = MotifEngine(motif_config, entropy_config)
        self.drift_tracker = EmotionalDriftTracker(self.config.get("emotional_drift", {}))
        self.roi_scorer = ROIResonanceScorer(self.config.get("roi_resonance", {}))
        capsule_config = self.config.get("capsule", {})
        self.capsules = MnemonicCapsule(
            capsule_config.get("output_path", "data/capsules.jsonl"),
            ensure_directory=capsule_config.get("ensure_directory", True),
            enabled=capsule_enabled,
        )
        narrative_config = self.config.get("narrative", {})
        self.narrator = NarrativeGenerator(
            tone=narrative_config.get("tone", "mythic"),
            include_entropy_regime=narrative_config.get("include_entropy_regime", True),
        )
        exchange_config = self.config.get("exchange", {})
        self.exchange = exchange if exchange is not None else build_exchange(exchange_config)
        self.paper_mode = isinstance(self.exchange, PaperExchange)

    def fetch_market_frame(self, symbol: str, timeframe: str = "1h", limit: int = 120) -> pd.DataFrame:
        raw = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        columns = ["timestamp", "open", "high", "low", "close", "volume"]
        frame = pd.DataFrame(raw, columns=columns)
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", errors="coerce")
        return frame

    def ritualize(
        self,
        frame: pd.DataFrame,
        symbol: str,
        persist_capsule: bool = True,
        execute_trade: bool = False,
    ) -> Dict[str, Optional[object]]:
        motif = self.motif_engine.detect(frame)
        drift = self.drift_tracker.track(frame)
        order = self._craft_order(symbol, frame, motif)
        price_context = {
            "close": float(frame["close"].iloc[-1]),
            "projected_price": float(order["projected_price"]) if order else float(frame["close"].iloc[-1]),
        }
        fallback_order = {"price": price_context["close"], "side": "hold"}
        roi_score = self.roi_scorer.score_trade(
            order or fallback_order,
            price_context,
            motif,
            drift,
        )
        narrative = self.narrator.compose(symbol, motif, drift, order, roi_score)
        capsule_record = None
        if order:
            if execute_trade:
                self._execute_order(order)
            capsule_record = self.capsules.encode(
                symbol=symbol,
                motif=motif.name,
                entropy_regime=motif.entropy.regime,
                roi_score=roi_score,
                order=order,
                drift=drift.to_dict(),
                narrative=narrative,
            )
            if persist_capsule:
                self.capsules.save(capsule_record)
        return {
            "motif": motif,
            "drift": drift,
            "order": order,
            "roi_score": roi_score,
            "narrative": narrative,
            "capsule": capsule_record,
        }

    def observe(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 120,
        persist_capsule: bool = True,
        execute_trade: bool = False,
    ) -> Dict[str, Optional[object]]:
        frame = self.fetch_market_frame(symbol, timeframe=timeframe, limit=limit)
        return self.ritualize(frame, symbol, persist_capsule=persist_capsule, execute_trade=execute_trade)

    def backtest(self, frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
        results = []
        min_window = max(self.drift_tracker.window, 30)
        for end in range(min_window, len(frame) + 1):
            slice_frame = frame.iloc[:end]
            report = self.ritualize(slice_frame, symbol, persist_capsule=False, execute_trade=False)
            motif: MotifSignal = report["motif"]  # type: ignore[assignment]
            drift_dict = report["drift"].to_dict()  # type: ignore[union-attr]
            results.append(
                {
                    "timestamp": slice_frame["timestamp"].iloc[-1],
                    "motif": motif.name,
                    "entropy": motif.entropy.value,
                    "entropy_regime": motif.entropy.regime,
                    "roi_score": report["roi_score"],
                    "narrative": report["narrative"],
                    "volatility": drift_dict["volatility"],
                    "volume_spike": drift_dict["volume_spike"],
                    "sentiment": drift_dict["sentiment"],
                }
            )
        return pd.DataFrame(results)

    def _craft_order(self, symbol: str, frame: pd.DataFrame, motif: MotifSignal) -> Optional[Dict[str, float]]:
        if motif.name is None:
            return None
        latest_row = frame.iloc[-1]
        price = float(latest_row["close"])
        side = "buy" if motif.name == "bullish_reversal" else "sell"
        projected_price = price * (1 + motif.metadata.get("expected_return", 0))
        return {
            "symbol": symbol,
            "side": side,
            "amount": 0.01,
            "price": price,
            "projected_price": projected_price,
            "confidence": motif.confidence,
            "timestamp": str(latest_row.get("timestamp")),
        }

    def _execute_order(self, order: Dict[str, float]) -> None:  # pragma: no cover - IO heavy
        side = order.get("side")
        amount = order.get("amount", 0)
        symbol = order.get("symbol")
        if not side or not symbol:
            return
        try:
            if side == "buy":
                self.exchange.create_market_buy_order(symbol, amount)
            elif side == "sell":
                self.exchange.create_market_sell_order(symbol, amount)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"Trade execution failed: {exc}")


__all__ = ["TradeOracle"]
