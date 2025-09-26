"""Live ingestion pipe that watches for Signal NDJSON updates."""
from __future__ import annotations

import json
import pathlib
import signal as os_signal
import threading
import time
import typing as t
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from queue import Empty, SimpleQueue

from common.io_loader import Signal
from common.io_utils import canonical_hash, ndjson_write
from common.watch import WatchEvent, iter_events

from .oracle_adapter import OracleAdapter


@dataclass
class PipeConfig:
    """Runtime configuration for :class:`LivePipe`."""

    watch_dir: str = "inbox/signals"
    state_dir: str = "artifacts/pipe_state"
    dlq_dir: str = "artifacts/dlq"
    log_dir: str = "artifacts/pipe_logs"
    file_glob: str = "*.ndjson"
    debounce_ms: int = 400
    batch_max: int = 256
    batch_timeout_ms: int = 1000
    retry_max: int = 5
    retry_backoff_ms: int = 500
    dedupe_window: int = 10_000


class LivePipe:
    """Tail new Signal rows and deliver them to the oracle."""

    def __init__(self, cfg: PipeConfig, oracle_adapter: OracleAdapter) -> None:
        self.cfg = cfg
        self.oracle = oracle_adapter
        self._stop = threading.Event()
        self._dedupe = deque(maxlen=cfg.dedupe_window)
        self._offsets: dict[pathlib.Path, int] = {}
        self._retries: dict[str, int] = defaultdict(int)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for directory in (
            self.cfg.watch_dir,
            self.cfg.state_dir,
            self.cfg.dlq_dir,
            self.cfg.log_dir,
        ):
            pathlib.Path(directory).mkdir(parents=True, exist_ok=True)

    def _state_file(self, path: pathlib.Path) -> pathlib.Path:
        key = canonical_hash(str(path)).replace(":", "_")
        return pathlib.Path(self.cfg.state_dir) / f"{key}.json"

    def _load_offset(self, path: pathlib.Path) -> int:
        state_file = self._state_file(path)
        if not state_file.exists():
            return 0
        try:
            payload = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            return 0
        return int(payload.get("offset", 0))

    def _save_offset(self, path: pathlib.Path, offset: int) -> None:
        state_file = self._state_file(path)
        state_file.write_text(
            json.dumps({"path": str(path), "offset": offset}), encoding="utf-8"
        )

    def _tail_new_lines(self, path: pathlib.Path) -> t.Iterator[dict[str, t.Any]]:
        offset = self._offsets.get(path)
        if offset is None:
            offset = self._load_offset(path)
        try:
            with path.open("r", encoding="utf-8") as handle:
                handle.seek(offset)
                while True:
                    position = handle.tell()
                    line = handle.readline()
                    if not line:
                        self._offsets[path] = position
                        self._save_offset(path, position)
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except Exception as exc:
                        self._write_dlq(
                            pathlib.Path(path.name).with_suffix(".bad.ndjson"),
                            {"error": str(exc), "line": line},
                        )
        except FileNotFoundError:
            # File may have been rotated or removed before reading completed
            self._offsets.pop(path, None)

    def _write_dlq(self, filename: pathlib.Path, payload: dict[str, t.Any]) -> None:
        dlq_path = pathlib.Path(self.cfg.dlq_dir) / filename
        dlq_path.parent.mkdir(parents=True, exist_ok=True)
        with dlq_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")

    def _validate_and_dedupe(self, raw_objs: t.Iterable[dict[str, t.Any]]) -> t.List[Signal]:
        valid: list[Signal] = []
        for obj in raw_objs:
            try:
                signal = Signal(**obj)
                signal.validate()
            except Exception as exc:
                self._write_dlq(
                    pathlib.Path("invalid_signal.ndjson"),
                    {"error": str(exc), "obj": obj},
                )
                continue

            if signal.id in self._dedupe:
                continue
            self._dedupe.append(signal.id)
            valid.append(signal)
        return valid

    def stop(self) -> None:
        """Request a graceful shutdown."""

        self._stop.set()

    def run(self) -> None:
        """Start the live pipe loop."""

        if threading.current_thread() is threading.main_thread():
            os_signal.signal(os_signal.SIGINT, lambda *_: self.stop())
            os_signal.signal(os_signal.SIGTERM, lambda *_: self.stop())

        batch: list[Signal] = []
        last_emit = time.monotonic()
        debounce = self.cfg.debounce_ms / 1000.0
        timeout = self.cfg.batch_timeout_ms / 1000.0
        queue: SimpleQueue[WatchEvent] = SimpleQueue()

        def watcher() -> None:
            for event in iter_events(self.cfg.watch_dir, patterns=(self.cfg.file_glob,)):
                queue.put(event)
                if self._stop.is_set():
                    break

        watcher_thread = threading.Thread(target=watcher, daemon=True)
        watcher_thread.start()

        while not self._stop.is_set():
            try:
                event = queue.get(timeout=0.1)
            except Empty:
                event = None

            if event is not None:
                if event.kind == "deleted":
                    self._offsets.pop(event.path, None)
                else:
                    time.sleep(debounce)
                    raw = list(self._tail_new_lines(event.path))
                    batch.extend(self._validate_and_dedupe(raw))

            now = time.monotonic()
            if batch and (
                len(batch) >= self.cfg.batch_max or (now - last_emit) >= timeout
            ):
                self._dispatch_batch(batch)
                batch.clear()
                last_emit = time.monotonic()

        if batch:
            self._dispatch_batch(batch)
            batch.clear()

    def _dispatch_batch(self, signals: list[Signal], batch_id: str | None = None) -> None:
        if not signals:
            return
        if batch_id is None:
            batch_id = f"batch_{int(time.time() * 1000)}"

        try:
            result = self.oracle.dispatch_signals(signals)
        except Exception as exc:  # pragma: no cover - retries exercised via unit tests
            attempt = self._retries[batch_id] = self._retries.get(batch_id, 0) + 1
            self._log_event(
                "dispatch_error",
                {"error": str(exc), "attempt": attempt, "size": len(signals)},
            )
            if attempt < self.cfg.retry_max:
                time.sleep(self.cfg.retry_backoff_ms / 1000.0)
                self._dispatch_batch(signals, batch_id=batch_id)
            else:
                dlq_path = pathlib.Path(self.cfg.dlq_dir) / f"dispatch_fail_{batch_id}.ndjson"
                ndjson_write(dlq_path, [asdict(signal) for signal in signals])
            return

        self._retries.pop(batch_id, None)
        payload = {"size": len(signals), **result}
        self._log_event("batch_dispatch", payload)

    def _log_event(self, kind: str, payload: dict[str, t.Any]) -> None:
        log_path = pathlib.Path(self.cfg.log_dir) / "live_pipe.log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ts": time.time(), "kind": kind, **payload}) + "\n")
