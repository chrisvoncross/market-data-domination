from __future__ import annotations

from dataclasses import dataclass

from control_plane.config import FarmerConfig
from control_plane.registry import TimeframeRegistry


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
