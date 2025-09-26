from __future__ import annotations

import hashlib
import json
import pathlib
import typing as t
from dataclasses import asdict

JSONDict = t.Dict[str, t.Any]


def ndjson_iter(path: t.Union[str, pathlib.Path]) -> t.Iterable[JSONDict]:
    p = pathlib.Path(path)
    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception as e:  # pragma: no cover - exercised via tests
                raise ValueError(f"{p}:{i}: invalid JSON - {e}") from e


def ndjson_write(path: t.Union[str, pathlib.Path], rows: t.Iterable[JSONDict]) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for obj in rows:
            f.write(json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n")


def json_write(path: t.Union[str, pathlib.Path], obj: JSONDict) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def json_read(path: t.Union[str, pathlib.Path]) -> JSONDict:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def prune_nones(value: t.Any) -> t.Any:
    if isinstance(value, dict):
        return {k: prune_nones(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [prune_nones(v) for v in value]
    return value


def canonical_hash(obj: t.Union[JSONDict, t.Any], algo: str = "sha256") -> str:
    """Stable content hash of dicts/dataclasses using sorted keys and no spaces."""
    if hasattr(obj, "__dataclass_fields__"):
        obj = asdict(obj)  # type: ignore[assignment]
    obj = prune_nones(obj)
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    h = hashlib.new(algo)
    h.update(data)
    return f"{algo}:{h.hexdigest()}"


def approx_equal(a: float, b: float, eps: float = 1e-9) -> bool:
    return abs(a - b) <= eps
