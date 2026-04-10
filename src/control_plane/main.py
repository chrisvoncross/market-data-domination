from __future__ import annotations

import argparse
import json
from pathlib import Path

from control_plane.config import load_config
from control_plane.plan import build_first_pass_plan, validate_against_runtime_contract
from control_plane.registry import TimeframeRegistry
from control_plane.runtime_contract import load_runtime_contract


def main() -> None:
    parser = argparse.ArgumentParser(description="Market Data Farmer control-plane bootstrap")
    parser.add_argument(
        "--config",
        default="docs/handover/farmer-config.json",
        help="Path to farmer config JSON",
    )
    parser.add_argument(
        "--runtime-contract",
        default="docs/handover/mvp_runtime_contract.json",
        help="Path to runtime contract JSON",
    )
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    runtime = load_runtime_contract(Path(args.runtime_contract))
    registry = TimeframeRegistry.from_config(cfg)
    validate_against_runtime_contract(cfg, registry, runtime)
    plan = build_first_pass_plan(cfg, registry)

    print(
        json.dumps(
            {
                "mode": "first_pass",
                "symbols": plan.symbols,
                "channels": plan.channels,
                "interval": plan.interval,
                "enabled_intervals": plan.enabled_intervals,
                "runtime_contract_version": runtime.version,
                "dedupe_trade_id_fields": runtime.dedupe_trade_id_fields,
                "heartbeat": {
                    "idle_timeout_sec": runtime.heartbeat_idle_timeout_sec,
                    "reply_timeout_sec": runtime.heartbeat_reply_timeout_sec,
                },
                "reconnect": {
                    "backoff_base_sec": runtime.reconnect_backoff_base_sec,
                    "backoff_max_sec": runtime.reconnect_backoff_max_sec,
                },
                "budgets": {
                    "cpu_pct": runtime.cpu_budget_pct,
                    "ram_mb": runtime.ram_budget_mb,
                },
                "slo": {
                    "max_lag_ms": runtime.max_lag_ms,
                    "max_drop_rate": runtime.max_drop_rate,
                    "max_write_p95_ms": runtime.max_write_p95_ms,
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
