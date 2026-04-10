# BR-GOV - Runtime Governance

## Metadata

- branch_id: BR-GOV
- owner: TODO
- status: active
- last_updated: 2026-04-10
- last_verified: 2026-04-10
- verification_method: runtime contract review + control-plane output check

## Mission

Constrain compute and memory usage while preserving data-path safety and operability.

## Scope

In scope:
- CPU/RAM pressure measurement
- queue pressure monitoring
- adaptive throttling/degradation actions
- compaction gating under pressure

Out of scope:
- full autoscaling controller (MVP)

## Baseline policy

- bounded queues for ingress and sinks
- drop-on-full policy at boundaries
- adaptive finalize sleep on quota/RSS pressure
- compaction only below pressure threshold
- primary runtime source: `docs/handover/mvp_runtime_contract.json`

## Required metrics

- `process_cpu_quota_pct`
- `rss_limit_ratio`
- `queue_pressure`
- `write_lag_ms`
- dropped counters
- SLO anchors: `max_lag_ms=30000`, `max_drop_rate=0.0`, `max_write_p95_ms=60000`
- budget anchors: `cpu_pct=25`, `ram_mb=4096`

## Core invariants

1. Governance logic must not become top resource consumer.
2. Overload must degrade behavior before process failure.
3. Every drop or throttle action must emit evidence.

## Open decisions

- alert burn-rate policy and paging windows

## Code locations

- runtime contract parser: `src/control_plane/runtime_contract.py`
- surfaced in bootstrap output: `src/control_plane/main.py`

## Run commands

- `scripts/first_pass_smoke.sh`
- `scripts/validate_first_pass.sh` (writes `.artifacts/native_resource_profile.txt`)
- `PYTHONPATH=src .venv/bin/python -m control_plane.live_run --duration-sec 30` (writes `.artifacts/live/live_summary.json`)

## Last live check

- 30s live run captured resource profile (`max_rss_kb`) and routed/deal/kline counters
