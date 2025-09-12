import json
import os
from datetime import datetime
from typing import Optional

SHARD_DIR = "data/shards/"

def ensure_shard_dir():
    os.makedirs(SHARD_DIR, exist_ok=True)

def write_shard(motif_name: str,
                strategy_config: dict,
                codex_prompt: str,
                codex_response: str,
                roi_result: float,
                emotional_drift: float,
                resonance_score: float,
                ΔΦ: float,
                glyphs: Optional[list] = None,
                capsule_id: Optional[str] = None):
    
    ensure_shard_dir()
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    capsule_id = capsule_id or f"IMM⇌SHARD⇌{motif_name}⇌{timestamp[:19].replace(':','-')}"

    shard = {
        "capsule_id": capsule_id,
        "timestamp": timestamp,
        "strategy_motif": motif_name,
        "config_snapshot": strategy_config,
        "codex_prompt": codex_prompt,
        "codex_response": codex_response,
        "roi_result": roi_result,
        "emotional_drift_score": emotional_drift,
        "resonance_score": resonance_score,
        "ΔΦ": round(ΔΦ, 5),
        "glyphs": glyphs or [],
        "ritual_signature": {
            "authored_by": "EchoWeaver_TradeOracle",
            "format": "immshard.v1",
            "emitted_from": "core.py"
        }
    }

    filename = os.path.join(SHARD_DIR, f"{capsule_id}.immshard.json")
    with open(filename, 'w') as f:
        json.dump(shard, f, indent=2)

    print(f"[IMM⟲SHARD]: Written → {filename}")
    return capsule_id
