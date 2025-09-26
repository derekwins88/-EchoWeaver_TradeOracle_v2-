"""Core oracle orchestrating motifs, entropy, and rituals."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd
import yaml

from .emotional_drift import EmotionalDriftTracker
from .exchange import PaperExchange, build_exchange
from .mnemonic_capsule import MnemonicCapsule
from .motif_engine import MotifEngine, MotifSignal
from .narrative_generator import NarrativeGenerator
from .roi_scorer import ROIResonanceScorer
from .position_sizer import PositionSizer, SizerConfig
from .risk import RiskConfig, RiskGovernor
from .stop_manager import ExitConfig, StopManager


@dataclass
class _OraclePerformanceTracker:
    """Lightweight equity tracker for the oracle's advisory risk modules."""

    starting_equity: float = 100_000.0

    def __post_init__(self) -> None:
        self.equity: float = self.starting_equity
        self._day_pnl: float = 0.0
        self._week_pnl: float = 0.0
        self._current_day = None
        self._current_week = None
        self.loss_streak: int = 0
        self.wins_since_bottom: int = 0

    def observe(self, timestamp) -> None:
        if timestamp is None:
            return
        ts = pd.Timestamp(timestamp)
        day = ts.date()
        iso = ts.isocalendar()
        week = (int(iso.year), int(iso.week))
        if self._current_day != day:
            self._current_day = day
            self._day_pnl = 0.0
        if self._current_week != week:
            self._current_week = week
            self._week_pnl = 0.0

    def register_trade(self, pnl: float, timestamp) -> None:
        self.observe(timestamp)
        self.equity += pnl
        self._day_pnl += pnl
        self._week_pnl += pnl
        if pnl < 0:
            self.loss_streak += 1
            self.wins_since_bottom = 0
        elif pnl > 0:
            self.loss_streak = 0
            self.wins_since_bottom += 1

    def equity_snapshot(self, start_of_day: bool = False, start_of_week: bool = False) -> float:
        _ = start_of_day, start_of_week
        return self.equity

    def pnl_window(self, window: str = "day") -> float:
        return self._day_pnl if window == "day" else self._week_pnl

    def streak(self, kind: str = "losses") -> int:
        if kind == "losses":
            return self.loss_streak
        return self.wins_since_bottom


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
        self.performance = _OraclePerformanceTracker()

        risk_cfg = RiskConfig(**self.config.get("risk", {}))
        sizing_cfg = SizerConfig(**self.config.get("sizing", {}))
        exit_cfg = ExitConfig(**self.config.get("exits", {}))

        self.risk_governor = RiskGovernor(
            cfg=risk_cfg,
            equity_fn=self.performance.equity_snapshot,
            pnl_window_fn=self.performance.pnl_window,
            streak_fn=self.performance.streak,
        )
        self.sizer_config = sizing_cfg
        self.exit_config = exit_cfg

        self._latest_frame: Optional[pd.DataFrame] = None
        self._latest_entropy: float = 0.0
        self._latest_regime: str = "neutral"

        self.stop_manager = StopManager(
            cfg=self.exit_config,
            entropy_fn=self._entropy_value,
            regime_fn=self._regime_state,
            atr_fn=self._atr_proxy,
        )

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
        self._latest_frame = frame.copy()
        self._latest_entropy = float(motif.entropy.value)
        self._latest_regime = motif.entropy.regime
        latest_ts = None
        if "timestamp" in frame.columns and not frame["timestamp"].empty:
            latest_ts = frame["timestamp"].iloc[-1]
        self.performance.observe(latest_ts)

        size_multiplier = self.risk_governor.size_multiplier()
        can_trade = self.risk_governor.can_trade_now()
        order = None
        if can_trade:
            order = self._craft_order(symbol, frame, motif, size_multiplier)
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
            projected = float(order.get("projected_price", order["price"]))
            price = float(order["price"])
            qty = float(order.get("amount", 0.0))
            pnl = (projected - price) * qty if order.get("side") == "buy" else (price - projected) * qty
            self.performance.register_trade(pnl, latest_ts)
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
            "risk_context": {
                "can_trade": can_trade,
                "size_multiplier": size_multiplier,
            },
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

    def _craft_order(
        self,
        symbol: str,
        frame: pd.DataFrame,
        motif: MotifSignal,
        size_multiplier: float,
    ) -> Optional[Dict[str, object]]:
        if motif.name is None:
            return None
        latest_row = frame.iloc[-1]
        price = float(latest_row["close"])
        conviction = float(motif.confidence)
        projected_price = price * (1 + motif.metadata.get("expected_return", 0.0))

        sizer = PositionSizer(
            cfg=self.sizer_config,
            atr_fn=lambda lookback: self._compute_atr(frame, lookback),
            conviction_fn=lambda: conviction,
        )
        qty = sizer.compute_qty() * max(size_multiplier, 0.0)
        if qty <= 0:
            return None

        side = "buy" if motif.name == "bullish_reversal" else "sell"
        atr_value = self._compute_atr(frame, self.sizer_config.atr_lookback)
        pct_risk = self.risk_governor.cfg.per_trade_risk_pct / 100.0
        risk_per_unit = max(atr_value, price * pct_risk)
        if side == "buy":
            stop_price = max(price - risk_per_unit, 0.0)
            trade_side = "long"
        else:
            stop_price = price + risk_per_unit
            trade_side = "short"

        exit_plan = self.stop_manager.update(
            entry_price=price,
            stop_price=stop_price,
            last_price=price,
            risk_per_unit=risk_per_unit,
            side=trade_side,
        )

        order: Dict[str, object] = {
            "symbol": symbol,
            "side": side,
            "amount": float(qty),
            "price": price,
            "projected_price": float(projected_price),
            "confidence": conviction,
            "timestamp": str(latest_row.get("timestamp")),
            "stop_price": float(stop_price),
            "risk_per_unit": float(risk_per_unit),
        }
        if exit_plan:
            order["exit_plan"] = exit_plan
        return order

    def _compute_atr(self, frame: pd.DataFrame, lookback: int) -> float:
        if frame.empty:
            return max(self.sizer_config.atr_ref, self.sizer_config.atr_floor)
        window = max(1, min(len(frame), lookback))
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        prev_close = close.shift(1).fillna(close.iloc[0])
        true_range = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = true_range.rolling(window=window, min_periods=1).mean().iloc[-1]
        return float(max(atr, self.sizer_config.atr_floor))

    def _entropy_value(self) -> float:
        return float(self._latest_entropy)

    def _regime_state(self) -> str:
        return str(self._latest_regime)

    def _atr_proxy(self, lookback: int) -> float:
        if self._latest_frame is None:
            return max(self.sizer_config.atr_ref, self.sizer_config.atr_floor)
        return self._compute_atr(self._latest_frame, lookback)

    def _execute_order(self, order: Dict[str, object]) -> None:  # pragma: no cover - IO heavy
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
