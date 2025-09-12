"""Trade memory management for the EchoWeaver capsule."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class Memory:
    """Persist trade events as ``.immshard`` files.

    Parameters
    ----------
    directory:
        Directory where memory shards are stored.  The directory is created if
        it does not already exist.
    """

    def __init__(self, directory: str | Path = "data") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save_trade(self, trade: Dict[str, Any]) -> Path:
        """Persist ``trade`` data to a new ``.immshard`` file.

        Returns the path to the newly created file.
        """

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        shard_path = self.directory / f"{timestamp}.immshard"
        with shard_path.open("w", encoding="utf-8") as handle:
            json.dump(trade, handle)
        return shard_path

    def load_latest(self) -> Optional[Dict[str, Any]]:
        """Load the most recent memory shard if one exists."""
        shards = sorted(self.directory.glob("*.immshard"))
        if not shards:
            return None
        with shards[-1].open("r", encoding="utf-8") as handle:
            return json.load(handle)
