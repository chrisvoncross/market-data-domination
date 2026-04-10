from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AggregationWindow:
    name: str
    window_ms: int


@dataclass(frozen=True)
class FarmerConfig:
    symbols: list[str]
    channels: list[str]
    aggregation: list[AggregationWindow]

    @property
    def intervals(self) -> list[str]:
        return [x.name for x in self.aggregation]


def _require_list_of_strings(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError(f"Expected '{key}' to be list[str]")
    return value


def load_config(path: Path) -> FarmerConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    symbols = _require_list_of_strings(raw, "symbols")
    channels = _require_list_of_strings(raw, "channels")

    agg_raw = raw.get("aggregation")
    if not isinstance(agg_raw, list) or not agg_raw:
        raise ValueError("Expected non-empty 'aggregation' list")

    windows: list[AggregationWindow] = []
    for row in agg_raw:
        if not isinstance(row, dict):
            raise ValueError("aggregation entries must be objects")
        name = row.get("name")
        window_ms = row.get("window_ms")
        if not isinstance(name, str) or not isinstance(window_ms, int):
            raise ValueError("aggregation entry requires {name:str, window_ms:int}")
        windows.append(AggregationWindow(name=name, window_ms=window_ms))

    return FarmerConfig(symbols=symbols, channels=channels, aggregation=windows)
