# MVP Plan v1 - MEXC -> Lance with Low-Overhead Governance

## Objective

Build a minimal but production-credible pipeline that:

1. ingests market data from MEXC reliably,
2. writes normalized events into Lance,
3. enforces low-cost CPU/RAM governance with measurable limits.

## Non-goals (MVP exclusions)

- no multi-exchange routing
- no full feature-engineering layer
- no distributed orchestration platform
- no heavy observability stack rollout on day 1

## Target constraints

- single host or minimal node footprint
- fixed CPU and memory envelopes via cgroup v2
- observability overhead budget explicitly capped

## Architecture slice

- `collector` (MEXC WS client, reconnect, heartbeat, gap detection)
- `normalizer` (strict schema, event-time and ingest-time fields)
- `buffer` (bounded queue, explicit drop/backpressure policy)
- `writer` (Lance micro-batch append)
- `governor` (PSI + cgroup + process metrics -> actions)
- `telemetry` (minimal OTel pipeline + structured logs)

## MVP milestones

### Milestone 1 - Ingest and durability baseline

- Connect to MEXC for 1-3 symbols
- Auto-reconnect with jittered backoff
- Persist trades and top-of-book updates to Lance partitions by date/symbol

Definition of done:
- 6h uninterrupted run
- zero process crashes
- deterministic schema validation pass

### Milestone 2 - Governance and protection

- Apply cgroup v2 envelopes per service
- Add PSI thresholds and action ladder:
  - warn -> reduce batch size -> throttle ingest -> controlled drop
- Add queue bounds and drop counters

Definition of done:
- under synthetic pressure, system degrades gracefully
- no unbounded memory growth
- no deadlocks

### Milestone 3 - SLO-driven operations

- Define SLOs:
  - ingest lag
  - write latency p95
  - drop rate
  - reconnect success
  - pressure event rate
- Burn-rate alert rules on critical SLOs

Definition of done:
- actionable alerts only (low noise)
- incident triage runbook validated once

## Initial performance budgets (starting point)

- collector + normalizer + writer total CPU: <= 1 vCPU steady-state
- total RSS: <= 1.5 GB
- profiling + telemetry overhead target: <= 5% CPU, <= 200 MB RAM

Note: budgets must be tuned with real traffic and hardware.

## Observability profile for low overhead

- logs:
  - structured JSON
  - production default level `INFO` with selective `DEBUG` gates
  - retention tiers with aggressive pruning
- metrics:
  - low-cardinality only
  - no unbounded labels (`user_id`, `request_id`, etc.)
- traces:
  - sampled
  - tail sampling for error/latency paths
- profiling:
  - CPU always-on at conservative sampling
  - memory profiles canaried or scheduled

## Risks and mitigations

- Exchange burst traffic -> bounded queue + pressure actions
- Symbol explosion -> enforce symbol allowlist in MVP
- Telemetry cost drift -> weekly cardinality/retention review
- Profiling overhead regressions -> canary compare profiled vs unprofiled nodes

## Deliverables

- architecture doc
- ADRs for governance stack and language split
- runbook for incident triage and pressure response
- benchmark report: baseline vs profiling enabled
