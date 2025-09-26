"""Adapters for sending validated signals into the TradeOracle."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from common.io_loader import Signal


class OracleAdapter:
    """Facade that translates :class:`Signal` batches for the oracle backend."""

    def __init__(self, oracle: Any) -> None:
        self.oracle = oracle

    def dispatch_signals(self, signals: List[Signal]) -> Dict[str, Any]:
        """Dispatch a batch of signals into the wrapped oracle.

        The default implementation calls ``oracle.handle_signal`` with a plain
        ``dict`` payload. Override or subclass if the integration needs a
        different entrypoint.
        """

        accepted = 0
        rejected = 0
        reasons: Dict[str, int] = {}
        for signal in signals:
            try:
                result = self.oracle.handle_signal(asdict(signal))
            except Exception as exc:  # pragma: no cover - error path logging
                rejected += 1
                key = exc.__class__.__name__
                reasons[key] = reasons.get(key, 0) + 1
                continue

            if result and result.get("status") == "accepted":
                accepted += 1
            else:
                rejected += 1
                tag = (result or {}).get("reason", "unknown")
                reasons[tag] = reasons.get(tag, 0) + 1

        return {"accepted": accepted, "rejected": rejected, "reasons": reasons}
