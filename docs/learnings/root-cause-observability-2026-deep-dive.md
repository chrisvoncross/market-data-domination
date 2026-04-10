# Root-Cause Observability Deep Dive (2026)

## Why this document

Current pain point is not "no metrics", but "insufficient root-cause fidelity at low overhead".
Goal is to reach a big-player style model:

- always-on, non-blocking, cheap baseline signals,
- triggered deep diagnostics only when pressure/anomaly thresholds fire,
- deterministic output schema for incident analysis and automation.

## Hard facts from primary sources

### Google SRE: keep monitoring symptom-oriented and actionable

Google SRE guidance stresses simple, high-signal monitoring with clear symptom focus
(latency, traffic, errors, saturation) and disciplined alerting.

Source:
- [Google SRE - Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)

Implication:
- baseline telemetry must stay compact and directly tie to user/system impact,
- avoid noisy per-event diagnostics in hot path.

### AWS/Builders-Library: static stability and control/data-plane separation

AWS guidance emphasizes control-plane vs data-plane separation and static stability
(data-plane keeps serving if control-plane is impaired).

Sources:
- [Static stability using Availability Zones](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)
- [Avoiding overload in distributed systems...](https://aws.amazon.com/builders-library/avoiding-overload-in-distributed-systems-by-putting-the-smaller-service-in-control/)

Implication:
- observability/control actions must never block data-plane loops,
- diagnostics pipeline must degrade independently from ingest/aggregation.

### Linux kernel PSI + cgroup v2: low-overhead pressure truth

Kernel PSI quantifies contention impact (`some`/`full`) and exposes both rolling averages
and absolute stall time. cgroup v2 provides concrete controls and per-cgroup pressure files.

Sources:
- [Linux PSI documentation](https://docs.kernel.org/accounting/psi.html)
- [Linux cgroup v2 guide](https://docs.kernel.org/admin-guide/cgroup-v2.html)

Key fields/mechanisms to use:
- `/proc/pressure/{cpu,memory,io}` and cgroup `*.pressure`,
- `cpu.max`, `memory.high`, `memory.max`, `io.max`,
- pressure-triggered policy transitions before catastrophic failure.

### Continuous profiling: sampling/eBPF for production "always-on"

Parca documents continuous profiling as low-overhead sampling and explicitly positions
eBPF agent profiling as production-suitable.

Source:
- [Parca Overview](https://parca.dev/docs/overview/)

### OpenTelemetry profiles in 2026

OTel Profiles are public alpha in 2026, valuable for correlation but should be treated
as progressive adoption for critical production paths.

Source:
- [OpenTelemetry Profiles concept](https://opentelemetry.io/docs/concepts/signals/profiles/)

## 2026 big-player pattern (practical)

Use a 3-layer observability stack:

1) **Layer A: Always-on baseline (very cheap, 1s cadence)**
   - process RSS, CPU pct, queue depth, write lag
   - PSI `avg10/avg60/avg300` + `total` deltas
   - reconnect/error/drop counters

2) **Layer B: Triggered enrichment (short bursts, bounded)**
   - activate when threshold crossed (e.g., memory PSI `some/full`, queue slope, lag breach)
   - capture targeted snapshots:
     - top alloc callsites (sampling),
     - queue composition,
     - per-stage latency histograms
   - strict TTL and rate limit for enrichment

3) **Layer C: Incident package (immutable, queryable)**
   - normalized incident artifact persisted as JSON/Lance rows:
     - trigger context,
     - before/after windows,
     - dominant contributors,
     - action ladder transitions.

This is non-blocking because expensive work is asynchronous, sampled, and bounded.

## Recommended libraries/tools for this project

### Mandatory baseline

- Native Python counters + monotonic timers (already in place)
- Linux PSI file polling (no extra heavy agent required)
- cgroup v2 control files for governance actions

### Profiling (phase-in)

- Parca Agent (eBPF) for continuous CPU profiling, low overhead
- Optional Pyroscope-style app-level profiling for language/runtime specifics
- OTel profiles export only after alpha-risk acceptance

## Output structure (contract proposal)

Store root-cause output in a deterministic schema (`observability_incidents`):

- `incident_id` (string)
- `trigger_time` (timestamp:us:UTC)
- `trigger_kind` (string) e.g. `memory_pressure`, `cpu_saturation`, `lag_breach`
- `window_pre_sec` (int32), `window_post_sec` (int32)
- `psi_cpu_some`, `psi_mem_some`, `psi_io_some` (float64)
- `rss_kb`, `cpu_pct`, `queue_depth`, `write_lag_ms` (float64/int64)
- `top_stage` (string)
- `top_stage_share_pct` (float64)
- `action_taken` (string) e.g. `throttle`, `drop_on_full`, `skip_maintenance`
- `confidence` (float64)
- `context_json` (large_string)

This schema is ML/LLM-friendly while preserving strict typing.

## Non-blocking guardrails (must-have)

- No synchronous profiling in hot path.
- Enrichment must be budgeted (time + cpu + memory caps).
- Drop enrichment first, not data-plane events, when diagnostics budget is exceeded.
- Never emit unbounded-cardinality labels in high-frequency metrics.

## Final conclusion

For this system, the most effective 2026 approach is:

- keep a tiny always-on metrics+PSI core,
- use threshold-triggered sampled profiling bursts (not continuous heavy tracing),
- persist incident artifacts in strict schema for deterministic RCA.

This gives near big-player operational behavior with minimal hardware overhead and
maintains architecture compliance (`Python control-plane`, `native data-plane loops`).
