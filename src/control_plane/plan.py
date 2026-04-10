from __future__ import annotations

from dataclasses import dataclass

from control_plane.config import FarmerConfig
from control_plane.registry import TimeframeRegistry
from control_plane.runtime_contract import RuntimeContract


@dataclass(frozen=True)
class FirstPassPlan:
    symbols: list[str]
    channels: list[str]
    interval: str
    enabled_intervals: list[str]


def build_first_pass_plan(
    cfg: FarmerConfig, registry: TimeframeRegistry, runtime: RuntimeContract
) -> FirstPassPlan:
    # First-load test scope: hard cap at 50 symbols.
    symbols = cfg.symbols[:50]
    channels = [x for x in runtime.channels if x in cfg.channels]
    if len(channels) != len(runtime.channels):
        raise ValueError("Config must include all runtime contract channels for first pass")

    if "Min1" not in registry.by_name:
        raise ValueError("First pass requires Min1 interval")

    return FirstPassPlan(
        symbols=symbols,
        channels=channels,
        interval="Min1",
        enabled_intervals=sorted(registry.by_name.keys()),
    )


def validate_against_runtime_contract(
    cfg: FarmerConfig, registry: TimeframeRegistry, runtime: RuntimeContract
) -> None:
    must_have = set(runtime.channels)
    if not {"push.deal", "push.kline"}.issubset(must_have):
        raise ValueError("Runtime contract must include push.deal and push.kline")
    if not must_have.issubset(set(cfg.channels)):
        raise ValueError("Farmer config must include all runtime contract channels")
    if runtime.required_interval not in registry.by_name:
        raise ValueError(f"Required interval '{runtime.required_interval}' not configured")
