"""Trade memory management for the EchoWeaver capsule."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def _slugify(text: str) -> str:
    """Return a filesystem-friendly slug derived from ``text``."""

    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def write_shard(shard_data: Dict[str, Any], shard_dir: str | Path = "data/shards") -> Path:
    """Persist ``shard_data`` to a timestamped ``.immshard`` JSON file.

    Parameters
    ----------
    shard_data:
        The data to store. A ``timestamp`` field is added automatically if
        absent.
    shard_dir:
        Directory where the shard will be written. Created if necessary.
    """

    directory = Path(shard_dir)
    directory.mkdir(parents=True, exist_ok=True)

    timestamp = shard_data.get("timestamp")
    if not timestamp:
        timestamp = datetime.utcnow().isoformat()
        shard_data["timestamp"] = timestamp

    # Build filename using timestamp and optional strategy motif
    fname = datetime.fromisoformat(timestamp).strftime("%Y%m%d%H%M%S")
    motif = shard_data.get("strategy_motif")
    if motif:
        fname += f"_{_slugify(motif)}"
    shard_path = directory / f"{fname}.immshard"

    with shard_path.open("w", encoding="utf-8") as handle:
        json.dump(shard_data, handle, ensure_ascii=False, indent=2)
    return shard_path


def load_latest_shard(shard_dir: str | Path = "data/shards") -> Optional[Dict[str, Any]]:
    """Load the most recent shard in ``shard_dir``.

    Returns ``None`` if no shard files exist.
    """

    directory = Path(shard_dir)
    shards = sorted(directory.glob("*.immshard"))
    if not shards:
        return None
    with shards[-1].open("r", encoding="utf-8") as handle:
        return json.load(handle)


class Memory:
    """Persist trade events as ``.immshard`` files."""

    def __init__(self, directory: str | Path = "data/shards") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save_trade(self, trade: Dict[str, Any]) -> Path:
        """Persist ``trade`` data to a new ``.immshard`` file."""

        return write_shard(trade, self.directory)

    def load_latest(self) -> Optional[Dict[str, Any]]:
        """Load the most recent memory shard if one exists."""

        return load_latest_shard(self.directory)
