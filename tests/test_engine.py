import sys
from pathlib import Path
from os.path import dirname, abspath

sys.path.append(abspath(dirname(__file__) + "/.."))

from engine.core import run
from engine.memory import Memory


class DummyCodex:
    def send_prompt(self, prompt: str, system_msg: str | None = None) -> str:
        return "ack"


def test_memory_save_creates_shard(tmp_path: Path) -> None:
    mem = Memory(directory=tmp_path)
    shard = mem.save_trade({"foo": "bar"})
    assert shard.exists()
    assert shard.suffix == ".immshard"


def test_core_run_writes_memory(tmp_path: Path) -> None:
    # create temporary config file
    cfg = tmp_path / "strategy.yaml"
    cfg.write_text("risk: low")

    class TmpMemory(Memory):
        def __init__(self) -> None:
            super().__init__(directory=tmp_path)

    response = run(
        motif="test",
        config_path=str(cfg),
        codex_cls=DummyCodex,
        memory_cls=TmpMemory,
    )

    assert response == "ack"
    shards = list(tmp_path.glob("*.immshard"))
    assert len(shards) == 1
