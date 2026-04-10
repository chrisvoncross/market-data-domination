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


def build_first_pass_plan(cfg: FarmerConfig, registry: TimeframeRegistry) -> FirstPassPlan:
    # MVP: start hardcoded-scope small; avoid 700-symbol blast radius.
    symbols = cfg.symbols[:3]
    required_channels = ["push.deal", "push.kline"]
    channels = [x for x in required_channels if x in cfg.channels]
    if len(channels) != len(required_channels):
        raise ValueError("Config must include push.deal and push.kline for first pass")

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
    must_have = {"push.deal", "push.kline"}
    if not must_have.issubset(set(runtime.channels)):
        raise ValueError("Runtime contract must include push.deal and push.kline")
    if not must_have.issubset(set(cfg.channels)):
        raise ValueError("Farmer config must include push.deal and push.kline")
    if runtime.required_interval not in registry.by_name:
        raise ValueError(f"Required interval '{runtime.required_interval}' not configured")
