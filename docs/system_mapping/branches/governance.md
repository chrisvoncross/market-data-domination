# BR-GOV - Runtime Governance

## Metadata

- branch_id: BR-GOV
- owner: TODO
- status: active
- last_updated: 2026-04-10
- last_verified: 2026-04-10
- verification_method: live run summary + observability artifact verification

## Mission

Constrain compute and memory usage while preserving data-path safety and operability.

## Scope

In scope:
- CPU/RAM pressure measurement
- PSI pressure measurement (`/proc/pressure/{cpu,memory,io}`)
- queue pressure monitoring
- incident evidence packaging for root-cause analysis

Out of scope:
- full autoscaling controller (MVP)

## Baseline policy

- bounded queues for ingress and sinks
- drop-on-full policy at boundaries
- always-on low-overhead sampling (1s cadence)
- threshold-triggered incident capture with cooldown
- primary runtime source: `docs/handover/mvp_runtime_contract.json`

## Required metrics

- `cpu_pct`
- `rss_kb`
- `queue_depth`
- `write_lag_ms`
- dropped counters
- `cpu_some_avg10`, `memory_some_avg10`, `io_some_avg10`
- incident counters and incident artifact paths
- spike counters and spike artifact path
- stage transition counters and transition artifact path
- distribution stats (`cpu_p95/p99`, `rss_p95/p99`, `queue_p95/p99`)
- SLO anchors: `max_lag_ms=30000`, `max_drop_rate=0.0`, `max_write_p95_ms=60000`
- budget anchors: `cpu_pct=25`, `ram_mb=4096`

## Core invariants

1. Governance logic must not become top resource consumer.
2. Overload must degrade behavior before process failure.
3. Every drop or pressure incident must emit evidence.

## Open decisions

- alert burn-rate policy and paging windows

## Code locations

- runtime contract parser: `src/control_plane/runtime_contract.py`
- non-blocking observability sampler + trigger logic: `src/control_plane/observability.py`
- live run integration and summary surface: `src/control_plane/live_run.py`

## Run commands

- `scripts/first_pass_smoke.sh`
- `scripts/validate_first_pass.sh` (writes `.artifacts/native_resource_profile.txt`)
- `PYTHONPATH=src .venv/bin/python -m control_plane.live_run --duration-sec 30`
  - writes `.artifacts/live/live_summary.json`
  - writes `.artifacts/live/observability_samples.ndjson` (full run timeline)
  - writes `.artifacts/live/observability_incidents.ndjson`
  - writes `.artifacts/live/observability_spikes.ndjson`
  - writes `.artifacts/live/observability_stage_transitions.ndjson`

## Last live check

- command: `PYTHONPATH=src .venv/bin/python -m control_plane.live_run --duration-sec 300 --out-dir .artifacts/live_obs_5m_stage_refined --lance-root data/lance_obs_5m_stage_refined`
- result:
  - `sample_count=300` and `observability_samples.ndjson` contains full 5-minute timeline
  - `incident_count=1`
  - `spike_count=2`
  - `stage_transition_count=3` (`ingest->data_plane`, `data_plane->lance_write`, `lance_write->done`)
  - `cpu_p95_pct=6.672`, `cpu_p99_pct=8.484`
  - `rss_p95_kb=134116`, `rss_p99_kb=134136`
  - observability artifacts emitted:
    - `.artifacts/live_obs_5m_stage_refined/observability_samples.ndjson`
    - `.artifacts/live_obs_5m_stage_refined/observability_incidents.ndjson`
    - `.artifacts/live_obs_5m_stage_refined/observability_spikes.ndjson`
    - `.artifacts/live_obs_5m_stage_refined/observability_stage_transitions.ndjson`
