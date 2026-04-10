# BR-GOV - Runtime Governance

## Metadata

- branch_id: BR-GOV
- owner: TODO
- status: active
- last_updated: 2026-04-10
- last_verified: 2026-04-10
- verification_method: research baseline + handover review

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

## Required metrics

- `process_cpu_quota_pct`
- `rss_limit_ratio`
- `queue_pressure`
- `write_lag_ms`
- dropped counters

## Core invariants

1. Governance logic must not become top resource consumer.
2. Overload must degrade behavior before process failure.
3. Every drop or throttle action must emit evidence.

## Open decisions

- deployment-specific CPU/RAM budgets
- final SLO alert thresholds for lag/drop/write p95

## Code locations

- TODO: set concrete runtime paths for pressure classifier, adaptive sleep, queue policy, and telemetry emitters.

## Run commands

- TODO: add pressure simulation commands (CPU quota, memory pressure, queue saturation) and expected metric checks.
