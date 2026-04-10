from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeContract:
    version: str
    channels: list[str]
    required_interval: str
    dedupe_trade_id_fields: list[str]
    heartbeat_idle_timeout_sec: float
    heartbeat_reply_timeout_sec: float
    reconnect_backoff_base_sec: float
    reconnect_backoff_max_sec: float
    cpu_budget_pct: float
    ram_budget_mb: int
    max_lag_ms: int
    max_drop_rate: float
    max_write_p95_ms: int


def _read(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("runtime contract must be an object")
    return raw


def load_runtime_contract(path: Path) -> RuntimeContract:
    data = _read(path)
    dedupe = data.get("dedupe", {})
    dedupe_keys = dedupe.get("keys", {})
    dedupe_conditions = dedupe_keys.get("deal_ingest_conditions", {})
    reconnect_and_heartbeat = data.get("reconnect_and_heartbeat", {})
    heartbeat = reconnect_and_heartbeat.get("heartbeat", {})
    reconnect = reconnect_and_heartbeat.get("reconnect", {})
    budgets = data.get("budgets", {})
    slo = data.get("slo", {})

    version = data.get("contract_version")
    channels = data.get("channels")
    if not isinstance(version, str):
        raise ValueError("Missing contract_version")
    if not isinstance(channels, list) or not all(isinstance(x, str) for x in channels):
        raise ValueError("Missing/invalid channels")

    trade_id_fields = dedupe_conditions.get("trade_id_fields_accepted")
    if not isinstance(trade_id_fields, list) or not all(isinstance(x, str) for x in trade_id_fields):
        raise ValueError("Missing dedupe deal trade id fields")

    required_interval = "Min1"
    return RuntimeContract(
        version=version,
        channels=channels,
        required_interval=required_interval,
        dedupe_trade_id_fields=trade_id_fields,
        heartbeat_idle_timeout_sec=float(heartbeat.get("idle_timeout_sec", 15.0)),
        heartbeat_reply_timeout_sec=float(heartbeat.get("reply_timeout_sec", 10.0)),
        reconnect_backoff_base_sec=float(reconnect.get("backoff_base_sec", 1.0)),
        reconnect_backoff_max_sec=float(reconnect.get("backoff_max_sec", 10.0)),
        cpu_budget_pct=float(budgets.get("cpu_pct", 25.0)),
        ram_budget_mb=int(budgets.get("ram_mb", 4096)),
        max_lag_ms=int(slo.get("max_lag_ms", 30000)),
        max_drop_rate=float(slo.get("max_drop_rate", 0.0)),
        max_write_p95_ms=int(slo.get("max_write_p95_ms", 60000)),
    )
