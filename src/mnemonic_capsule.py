"""Mnemonic capsules record the oracle's trades as mythic memories."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class CapsuleRecord:
    """Structured capsule metadata."""

    capsule_id: str
    timestamp: str
    symbol: str
    motif: Optional[str]
    entropy_regime: str
    roi_resonance: float
    payload: Dict[str, Any]


class MnemonicCapsule:
    """Stores trade context as JSONL capsules inspired by ProofBridge."""

    def __init__(self, output_path: str, ensure_directory: bool = True, enabled: bool = True) -> None:
        self.output_path = Path(output_path)
        self.enabled = enabled
        if ensure_directory:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def encode(
        self,
        symbol: str,
        motif: Optional[str],
        entropy_regime: str,
        roi_score: float,
        order: Dict[str, Any],
        drift: Dict[str, Any],
        narrative: str,
    ) -> CapsuleRecord:
        capsule_id = f"capsule-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        payload = {
            "order": order,
            "drift": drift,
            "narrative": narrative,
        }
        timestamp = order.get("timestamp") or datetime.utcnow().isoformat()
        return CapsuleRecord(
            capsule_id=capsule_id,
            timestamp=timestamp,
            symbol=symbol,
            motif=motif,
            entropy_regime=entropy_regime,
            roi_resonance=roi_score,
            payload=payload,
        )

    def save(self, capsule: CapsuleRecord) -> None:
        if not self.enabled:
            return
        record = {
            "capsule_id": capsule.capsule_id,
            "timestamp": capsule.timestamp,
            "symbol": capsule.symbol,
            "motif": capsule.motif,
            "entropy_regime": capsule.entropy_regime,
            "roi_resonance": capsule.roi_resonance,
            "payload": capsule.payload,
        }
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")


__all__ = ["MnemonicCapsule", "CapsuleRecord"]
