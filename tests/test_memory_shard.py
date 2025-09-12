import json
from pathlib import Path

from engine.memory import write_shard, load_latest_shard


def test_write_shard_creates_file_with_timestamp(tmp_path: Path) -> None:
    data = {"strategy_motif": "Mean reversion", "roi_result": 0.1}
    path = write_shard(data, shard_dir=tmp_path)
    assert path.exists()
    assert path.suffix == ".immshard"
    loaded = json.loads(path.read_text())
    assert loaded["strategy_motif"] == "Mean reversion"
    assert "timestamp" in loaded


def test_load_latest_shard_returns_latest(tmp_path: Path) -> None:
    write_shard({"strategy_motif": "first"}, shard_dir=tmp_path)
    write_shard({"strategy_motif": "second"}, shard_dir=tmp_path)
    latest = load_latest_shard(tmp_path)
    assert latest is not None
    assert latest["strategy_motif"] == "second"
