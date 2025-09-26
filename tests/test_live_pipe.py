from __future__ import annotations

import json
import pathlib
import threading
import time

from stream.live_pipe import LivePipe, PipeConfig
from stream.oracle_adapter import OracleAdapter


class FakeOracle:
    def __init__(self) -> None:
        self.calls = 0
        self.payloads: list[dict[str, str]] = []

    def handle_signal(self, payload):
        self.calls += 1
        self.payloads.append(payload)
        return {"status": "accepted"}


def _write_ndjson(path: pathlib.Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_live_pipe_basic(tmp_path):
    inbox = tmp_path / "inbox"
    cfg = PipeConfig(
        watch_dir=str(inbox),
        state_dir=str(tmp_path / "state"),
        dlq_dir=str(tmp_path / "dlq"),
        log_dir=str(tmp_path / "logs"),
        debounce_ms=100,
        batch_timeout_ms=300,
        batch_max=10,
    )
    oracle = FakeOracle()
    pipe = LivePipe(cfg, OracleAdapter(oracle))

    thread = threading.Thread(target=pipe.run, daemon=True)
    thread.start()

    signal_path = inbox / "signals.ndjson"
    signal = {
        "id": "sig-001",
        "timestamp": "2025-01-01T00:00:00Z",
        "symbol": "NQ",
        "side": "LONG",
        "confidence": 0.8,
        "entropy_score": 0.2,
        "regime_state": "trend_up",
    }
    _write_ndjson(signal_path, [signal])

    deadline = time.time() + 3
    while oracle.calls == 0 and time.time() < deadline:
        time.sleep(0.05)

    pipe.stop()
    thread.join(timeout=2)

    assert oracle.calls >= 1
    assert oracle.payloads[0]["id"] == "sig-001"
