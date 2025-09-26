#!/usr/bin/env python3
"""
Validate JSON or NDJSON against schemas in common/schema/.
Usage:
  python scripts/validate_io.py --schema common/schema/brain.signal.json --file samples/brain_signals.ndjson
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Iterable, Tuple
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, RefResolver

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent


def load_json(path: pathlib.Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def candidate_paths(schema_dir: pathlib.Path, rel_path: pathlib.Path) -> Iterable[pathlib.Path]:
    yield schema_dir / rel_path
    yield schema_dir / rel_path.name
    yield REPO_ROOT / rel_path
    yield REPO_ROOT / "common" / rel_path.name
    yield REPO_ROOT / "common" / "schema" / rel_path.name


def validator_for(schema_path: str) -> Draft202012Validator:
    schema_file = pathlib.Path(schema_path).resolve()
    schema_dir = schema_file.parent
    schema = load_json(schema_file)

    def resolve(uri: str):
        parsed = urlparse(uri)
        if parsed.scheme == "https" and parsed.netloc == "spec.local":
            rel = pathlib.Path(parsed.path.lstrip("/"))
            seen: set[str] = set()
            for candidate in candidate_paths(schema_dir, rel):
                key = str(candidate)
                if key in seen:
                    continue
                seen.add(key)
                if candidate.exists():
                    return load_json(candidate)
        return None

    class LocalResolver(RefResolver):
        def resolve_remote(self, uri: str):  # type: ignore[override]
            document = resolve(uri)
            if document is not None:
                return document
            return super().resolve_remote(uri)

    return Draft202012Validator(schema, resolver=LocalResolver.from_schema(schema))


def iter_ndjson(file_path: pathlib.Path) -> Iterable[Tuple[int, object]]:
    with file_path.open("r", encoding="utf-8") as handle:
        for index, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                yield index, json.loads(line)
            except json.JSONDecodeError as exc:  # pragma: no cover - explicit failure path
                raise SystemExit(f"Line {index}: invalid JSON: {exc}") from exc


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True)
    parser.add_argument("--file", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)

    validator = validator_for(args.schema)
    target_path = pathlib.Path(args.file)

    try:
        if target_path.suffix == ".ndjson":
            success = True
            for index, payload in iter_ndjson(target_path):
                errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
                if errors:
                    success = False
                    print(f"❌ Line {index} failed:")
                    for error in errors:
                        location = ".".join(str(part) for part in error.path)
                        prefix = f"{location}: " if location else ""
                        print(f"   - {prefix}{error.message}")
            if not success:
                return 1
            print("✅ NDJSON validated.")
        else:
            payload = load_json(target_path.resolve())
            validator.validate(payload)
            print("✅ JSON validated.")
    except Exception as exc:  # pragma: no cover - CLI surface
        raise SystemExit(str(exc)) from exc

    return 0


if __name__ == "__main__":
    sys.exit(main())
