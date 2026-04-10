from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa


@dataclass(frozen=True)
class LanceWriteStats:
    raw_rows: int
    feature_rows: int
    mismatch_rows: int
    intervals_written: list[str]


def _event_time_us(payload: dict[str, Any]) -> int | None:
    data = payload.get("data")
    if isinstance(data, dict):
        t = data.get("t")
        if isinstance(t, (int, float)):
            ts = int(t)
            if ts < 1_000_000_000_000:
                return ts * 1_000_000
            if ts < 1_000_000_000_000_000:
                return ts * 1000
            return ts
    ts = payload.get("ts")
    if isinstance(ts, (int, float)):
        return int(ts) * 1000
    return None


def _timestamp_us(value_us: int | None) -> Any:
    return None if value_us is None else value_us


def _raw_schema() -> pa.Schema:
    return pa.schema(
        [
            ("event_id", pa.string()),
            ("exchange", pa.string()),
            ("symbol", pa.string()),
            ("channel", pa.string()),
            ("event_time", pa.timestamp("us", tz="UTC")),
            ("recv_time", pa.timestamp("us", tz="UTC")),
            ("capture_slot", pa.int32()),
            ("payload_json", pa.large_string()),
            ("schema_version", pa.int32()),
        ]
    )


def _feature_schema() -> pa.Schema:
    return pa.schema(
        [
            ("row_id", pa.string()),
            ("symbol", pa.string()),
            ("interval", pa.string()),
            ("minute_time", pa.timestamp("ms", tz="UTC")),
            ("event_time_close", pa.timestamp("us", tz="UTC")),
            ("ingest_time_close", pa.timestamp("us", tz="UTC")),
            ("open", pa.float64()),
            ("high", pa.float64()),
            ("low", pa.float64()),
            ("close", pa.float64()),
            ("volume", pa.float64()),
            ("trade_count", pa.int64()),
            ("amount", pa.float64()),
            ("decision_kind", pa.string()),
            ("is_mismatch", pa.bool_()),
            ("mismatch_reason", pa.string()),
            ("source_contract_version", pa.string()),
            ("schema_version", pa.int32()),
        ]
    )


def _mismatch_schema() -> pa.Schema:
    return pa.schema(
        [
            ("audit_id", pa.string()),
            ("symbol", pa.string()),
            ("interval", pa.string()),
            ("minute_time", pa.timestamp("ms", tz="UTC")),
            ("expected_source", pa.string()),
            ("observed_source", pa.string()),
            ("reason", pa.string()),
            ("created_at", pa.timestamp("us", tz="UTC")),
            ("context_json", pa.large_string()),
            ("schema_version", pa.int32()),
        ]
    )


def _open_or_create_table(db: Any, name: str, schema: pa.Schema) -> Any:
    try:
        return db.open_table(name)
    except Exception:
        pass
    empty = pa.Table.from_pylist([], schema=schema)
    return db.create_table(name, data=empty, schema=schema, mode="create")


def write_live_artifacts_to_lance(
    *,
    raw_path: Path,
    data_plane_out_path: Path,
    lance_root: Path,
    contract_version: str,
    schema_version: int = 1,
) -> LanceWriteStats:
    lance_root.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(lance_root))

    raw_rows: list[dict[str, Any]] = []
    feature_by_interval: dict[str, list[dict[str, Any]]] = {}
    mismatch_rows: list[dict[str, Any]] = []
    now_us = int(time.time() * 1_000_000)

    for line in raw_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        channel = obj.get("channel")
        symbol = obj.get("symbol")
        payload = obj.get("payload")
        slot_id = obj.get("slot_id")
        if not isinstance(channel, str) or not isinstance(symbol, str) or not isinstance(payload, dict):
            continue
        event_time_us = _event_time_us(payload)
        event_id = hashlib.sha1(
            f"{channel}|{symbol}|{event_time_us}|{payload.get('ts')}".encode("utf-8")
        ).hexdigest()
        raw_rows.append(
            {
                "event_id": event_id,
                "exchange": "MEXC",
                "symbol": symbol,
                "channel": channel,
                "event_time": _timestamp_us(event_time_us),
                "recv_time": _timestamp_us(now_us),
                "capture_slot": int(slot_id) if isinstance(slot_id, int) else 0,
                "payload_json": json.dumps(payload, separators=(",", ":"), ensure_ascii=True),
                "schema_version": schema_version,
            }
        )

    for line in data_plane_out_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        event_type = obj.get("event_type")
        if event_type == "final_candle":
            symbol = obj.get("symbol")
            interval = obj.get("interval")
            minute_ms = obj.get("minute_ms")
            if not isinstance(symbol, str) or not isinstance(interval, str) or not isinstance(minute_ms, int):
                continue
            row_id = f"{symbol}:{interval}:{minute_ms}"
            row = {
                "row_id": row_id,
                "symbol": symbol,
                "interval": interval,
                "minute_time": minute_ms,
                "event_time_close": minute_ms * 1000,
                "ingest_time_close": now_us,
                "open": float(obj.get("open", 0.0)),
                "high": float(obj.get("high", 0.0)),
                "low": float(obj.get("low", 0.0)),
                "close": float(obj.get("close", 0.0)),
                "volume": float(obj.get("volume", 0.0)),
                "trade_count": int(obj.get("trade_count", 0)),
                "amount": None,
                "decision_kind": str(obj.get("decision_kind", "")),
                "is_mismatch": str(obj.get("decision_kind", "")).endswith("override_local"),
                "mismatch_reason": "snapshot_value_diff"
                if str(obj.get("decision_kind", "")).endswith("override_local")
                else None,
                "source_contract_version": contract_version,
                "schema_version": schema_version,
            }
            feature_by_interval.setdefault(interval, []).append(row)
        elif event_type == "mismatch_event":
            symbol = obj.get("symbol")
            interval = obj.get("interval")
            minute_ms = obj.get("minute_ms")
            if not isinstance(symbol, str) or not isinstance(interval, str) or not isinstance(minute_ms, int):
                continue
            audit_id = hashlib.sha1(
                f"{symbol}|{interval}|{minute_ms}|{obj.get('reason','')}".encode("utf-8")
            ).hexdigest()
            mismatch_rows.append(
                {
                    "audit_id": audit_id,
                    "symbol": symbol,
                    "interval": interval,
                    "minute_time": minute_ms,
                    "expected_source": "direct_exchange_kline",
                    "observed_source": "local_min1_reconstruct",
                    "reason": str(obj.get("reason", "unknown")),
                    "created_at": now_us,
                    "context_json": json.dumps(obj, separators=(",", ":"), ensure_ascii=True),
                    "schema_version": schema_version,
                }
            )

    raw_table = _open_or_create_table(db, "raw_events", _raw_schema())
    if raw_rows:
        raw_table.add(pa.Table.from_pylist(raw_rows, schema=_raw_schema()))

    intervals_written: list[str] = []
    total_features = 0
    for interval, rows in feature_by_interval.items():
        if not rows:
            continue
        table = _open_or_create_table(db, interval, _feature_schema())
        table.add(pa.Table.from_pylist(rows, schema=_feature_schema()))
        intervals_written.append(interval)
        total_features += len(rows)

    mismatch_table = _open_or_create_table(db, "audit_mismatch", _mismatch_schema())
    if mismatch_rows:
        mismatch_table.add(pa.Table.from_pylist(mismatch_rows, schema=_mismatch_schema()))

    return LanceWriteStats(
        raw_rows=len(raw_rows),
        feature_rows=total_features,
        mismatch_rows=len(mismatch_rows),
        intervals_written=sorted(intervals_written),
    )
