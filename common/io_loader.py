from __future__ import annotations

import json
import pathlib
import typing as t
from dataclasses import asdict, dataclass, field

from jsonschema import Draft202012Validator, RefResolver

from .io_utils import canonical_hash, json_read, json_write, ndjson_iter, ndjson_write, prune_nones

SCHEMA_BASE = pathlib.Path(__file__).resolve().parent / "schema"
LOCAL_ID_PREFIX = "https://spec.local/"


def _load_schema(rel: str) -> dict:
    path = (SCHEMA_BASE / rel).resolve()
    if not path.exists():
        path = (SCHEMA_BASE / pathlib.Path(rel).name).resolve()
    return json.loads(path.read_text(encoding="utf-8"))


def _to_payload(instance: t.Any) -> dict:
    return prune_nones(asdict(instance))


def _validator(schema_rel: str) -> Draft202012Validator:
    schema = _load_schema(schema_rel)

    class LocalResolver(RefResolver):
        def resolve_remote(self, uri: str):  # type: ignore[override]
            if uri.startswith(LOCAL_ID_PREFIX):
                rel = uri.replace(LOCAL_ID_PREFIX, "")
                return _load_schema(rel)
            return super().resolve_remote(uri)

    return Draft202012Validator(schema, resolver=LocalResolver.from_schema(schema))


@dataclass
class Signal:
    id: str
    timestamp: str
    symbol: str
    side: str
    confidence: float
    entropy_score: float
    regime_state: str
    features: t.Dict[str, t.Any] = field(default_factory=dict)
    hash: t.Optional[str] = None
    capsule_id: t.Optional[str] = None

    SCHEMA = "brain.signal.json"

    def validate(self) -> None:
        _validator(self.SCHEMA).validate(_to_payload(self))

    def with_hash(self, algo: str = "sha256") -> "Signal":
        payload = _to_payload(self)
        payload.pop("hash", None)
        self.hash = canonical_hash(payload, algo)
        return self


@dataclass
class TradeEvent:
    id: str
    timestamp: str
    symbol: str
    event: str
    side: str
    qty: float
    price: float
    regime_state: t.Optional[str] = None
    entropy_score: t.Optional[float] = None
    pnl: t.Optional[float] = None
    trade_id: t.Optional[str] = None
    signal_id: t.Optional[str] = None
    hash: t.Optional[str] = None
    meta: t.Dict[str, t.Any] = field(default_factory=dict)

    SCHEMA = "oracle.trade_event.json"

    def validate(self) -> None:
        _validator(self.SCHEMA).validate(_to_payload(self))

    def with_hash(self, algo: str = "sha256") -> "TradeEvent":
        payload = _to_payload(self)
        payload.pop("hash", None)
        self.hash = canonical_hash(payload, algo)
        return self


@dataclass
class StrategyReturn:
    id: str
    timestamp: str
    strategy: str
    symbol: str
    pnl: float
    equity: float
    drawdown: t.Optional[float] = None
    sharpe: t.Optional[float] = None
    regime_state: t.Optional[str] = None

    SCHEMA = "oracle.strategy_return.json"

    def validate(self) -> None:
        _validator(self.SCHEMA).validate(_to_payload(self))


@dataclass
class AllocationItem:
    strategy: str
    symbol: str
    weight: float
    entropy_risk: t.Optional[float] = None


@dataclass
class PortfolioAllocation:
    id: str
    timestamp: str
    allocations: t.List[AllocationItem]
    constraints: t.Dict[str, t.Any] = field(default_factory=dict)
    hash: t.Optional[str] = None

    SCHEMA = "portfolio.allocation.json"

    def validate(self) -> None:
        data = _to_payload(self)
        _validator(self.SCHEMA).validate(data)
        total = sum(item["weight"] for item in data["allocations"])
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"allocations weights must sum to 1.0 (got {total:.8f})")

    def with_hash(self, algo: str = "sha256") -> "PortfolioAllocation":
        payload = _to_payload(self)
        payload.pop("hash", None)
        self.hash = canonical_hash(payload, algo)
        return self


def read_signals_ndjson(path: t.Union[str, pathlib.Path]) -> t.List[Signal]:
    out: t.List[Signal] = []
    for obj in ndjson_iter(path):
        signal = Signal(**obj)
        signal.validate()
        out.append(signal)
    return out


def write_signals_ndjson(
    path: t.Union[str, pathlib.Path], signals: t.Iterable[Signal], add_hash: bool = True
) -> None:
    rows = []
    for signal in signals:
        if add_hash and not signal.hash:
            signal.with_hash()
        signal.validate()
        rows.append(_to_payload(signal))
    ndjson_write(path, rows)


def read_trade_events_ndjson(path: t.Union[str, pathlib.Path]) -> t.List[TradeEvent]:
    out: t.List[TradeEvent] = []
    for obj in ndjson_iter(path):
        event = TradeEvent(**obj)
        event.validate()
        out.append(event)
    return out


def write_trade_events_ndjson(
    path: t.Union[str, pathlib.Path], events: t.Iterable[TradeEvent], add_hash: bool = True
) -> None:
    rows: t.List[dict] = []
    for event in events:
        if add_hash and not event.hash:
            event.with_hash()
        event.validate()
        rows.append(_to_payload(event))
    ndjson_write(path, rows)


def read_strategy_returns_ndjson(path: t.Union[str, pathlib.Path]) -> t.List[StrategyReturn]:
    out: t.List[StrategyReturn] = []
    for obj in ndjson_iter(path):
        record = StrategyReturn(**obj)
        record.validate()
        out.append(record)
    return out


def write_strategy_returns_ndjson(
    path: t.Union[str, pathlib.Path], rows: t.Iterable[StrategyReturn]
) -> None:
    payload: t.List[dict] = []
    for record in rows:
        record.validate()
        payload.append(_to_payload(record))
    ndjson_write(path, payload)


def read_allocation_json(path: t.Union[str, pathlib.Path]) -> PortfolioAllocation:
    obj = json_read(path)
    allocations = [AllocationItem(**item) for item in obj.get("allocations", [])]
    allocation = PortfolioAllocation(
        id=obj["id"],
        timestamp=obj["timestamp"],
        allocations=allocations,
        constraints=obj.get("constraints", {}),
        hash=obj.get("hash"),
    )
    allocation.validate()
    return allocation


def write_allocation_json(
    path: t.Union[str, pathlib.Path], allocation: PortfolioAllocation, add_hash: bool = True
) -> None:
    if add_hash and not allocation.hash:
        allocation.with_hash()
    allocation.validate()
    json_write(path, _to_payload(allocation))
