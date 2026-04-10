from __future__ import annotations

from dataclasses import dataclass

from control_plane.config import FarmerConfig


@dataclass(frozen=True)
class TimeframeRegistry:
    by_name: dict[str, int]

    @classmethod
    def from_config(cls, cfg: FarmerConfig) -> "TimeframeRegistry":
        dedup: dict[str, int] = {}
        for interval in cfg.aggregation:
            dedup[interval.name] = interval.window_ms
        if not dedup:
            raise ValueError("No intervals configured")
        return cls(by_name=dedup)
