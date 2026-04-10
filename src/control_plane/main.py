from __future__ import annotations

import argparse
import json
from pathlib import Path

from control_plane.config import load_config
from control_plane.plan import build_first_pass_plan
from control_plane.registry import TimeframeRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="Market Data Farmer control-plane bootstrap")
    parser.add_argument(
        "--config",
        default="docs/handover/farmer-config.json",
        help="Path to farmer config JSON",
    )
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    registry = TimeframeRegistry.from_config(cfg)
    plan = build_first_pass_plan(cfg, registry)

    print(
        json.dumps(
            {
                "mode": "first_pass",
                "symbols": plan.symbols,
                "channels": plan.channels,
                "interval": plan.interval,
                "enabled_intervals": plan.enabled_intervals,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
