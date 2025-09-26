"""Filesystem watching utilities with watchdog fallback."""
from __future__ import annotations

import os
import pathlib
import time
import typing as t
from dataclasses import dataclass

try:  # pragma: no cover - exercised indirectly during runtime
    from watchdog.events import FileSystemEventHandler  # type: ignore
    from watchdog.observers import Observer  # type: ignore

    HAS_WATCHDOG = True
except Exception:  # pragma: no cover - optional dependency
    HAS_WATCHDOG = False


@dataclass
class WatchEvent:
    """Representation of a filesystem change."""

    path: pathlib.Path
    kind: str  # created | modified | deleted | moved


def _matches(path: pathlib.Path, patterns: t.Tuple[str, ...]) -> bool:
    return any(path.match(pattern) for pattern in patterns)


def iter_events(
    dir_path: t.Union[str, os.PathLike[str]],
    patterns: t.Tuple[str, ...] = ("*.ndjson",),
    poll_sec: float = 1.0,
) -> t.Iterator[WatchEvent]:
    """Yield :class:`WatchEvent` instances for files matching ``patterns``.

    The watcher prefers ``watchdog`` when available and falls back to a simple
    polling loop without introducing external dependencies.
    """

    directory = pathlib.Path(dir_path).resolve()
    directory.mkdir(parents=True, exist_ok=True)

    if HAS_WATCHDOG:  # pragma: no branch - runtime flag

        class Handler(FileSystemEventHandler):
            def __init__(self, queue: "t.Deque[WatchEvent]") -> None:
                self.queue = queue

            def on_created(self, event):  # type: ignore[override]
                if event.is_directory:
                    return
                path = pathlib.Path(event.src_path)
                if _matches(path, patterns):
                    self.queue.append(WatchEvent(path, "created"))

            def on_modified(self, event):  # type: ignore[override]
                if event.is_directory:
                    return
                path = pathlib.Path(event.src_path)
                if _matches(path, patterns):
                    self.queue.append(WatchEvent(path, "modified"))

            def on_moved(self, event):  # type: ignore[override]
                if event.is_directory:
                    return
                path = pathlib.Path(event.dest_path)
                if _matches(path, patterns):
                    self.queue.append(WatchEvent(path, "moved"))

            def on_deleted(self, event):  # type: ignore[override]
                if event.is_directory:
                    return
                path = pathlib.Path(event.src_path)
                if _matches(path, patterns):
                    self.queue.append(WatchEvent(path, "deleted"))

        from collections import deque

        queue: t.Deque[WatchEvent] = deque()
        handler = Handler(queue)
        observer = Observer()
        observer.schedule(handler, str(directory), recursive=False)
        observer.start()

        try:
            while True:
                while queue:
                    yield queue.popleft()
                time.sleep(0.1)
        finally:  # pragma: no branch - cleanup path
            observer.stop()
            observer.join()
    else:
        seen: dict[pathlib.Path, float] = {}
        while True:
            matched: t.Set[pathlib.Path] = set()
            for pattern in patterns:
                matched.update(directory.glob(pattern))

            for path in sorted(matched):
                try:
                    mtime = path.stat().st_mtime
                except FileNotFoundError:
                    continue

                if path not in seen:
                    seen[path] = mtime
                    yield WatchEvent(path, "created")
                elif mtime != seen[path]:
                    seen[path] = mtime
                    yield WatchEvent(path, "modified")

            stale = [path for path in seen if path not in matched]
            for path in stale:
                seen.pop(path, None)
                yield WatchEvent(path, "deleted")

            time.sleep(poll_sec)
