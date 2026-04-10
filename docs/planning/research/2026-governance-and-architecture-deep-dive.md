# 2026 Deep Dive: Governance and Architecture

## Scope

This document answers two questions:

1. What is the best-practice 2026 stack for low-overhead CPU/RAM governance with high analytics quality?
2. What architecture and language split is used in high-scale systems for control plane vs data plane?

## Executive takeaways

- There is no universal "single best" stack, but there is a practical top tier for Linux production:
  - cgroup v2 hard budgets and isolation
  - PSI pressure metrics for contention-aware governance
  - always-on sampling profiling (Parca and/or Pyroscope)
  - OTel-based logs/metrics/traces pipeline
  - SLO burn-rate alerting
- "100% Python for control plane and native data plane" is not a universal rule.
  - The common pattern is polyglot:
    - control plane: Python and/or Go and/or Java
    - data plane / hot paths: C++, Rust, JVM native profilers, kernel/eBPF
  - In latency-sensitive finance systems, C++ remains dominant in critical paths.

---

## Part A - Governance for low hardware usage + strong analytics

### A1) Kernel-native resource governance baseline

For low-overhead runtime governance on Linux, the strongest baseline is:

- cgroup v2 limits and throttles (`memory.high`, `memory.max`, `cpu.max`, etc.)
- PSI pressure signals (`/proc/pressure/*`, cgroup `*.pressure`)
- pressure-triggered automation (load shedding, backpressure, controlled degradation)

Why this is strong:
- Measures contention and stall time, not just coarse utilization.
- Supports proactive protection before OOM or hard failure.
- Implemented in-kernel with low overhead.

Primary sources:
- Linux PSI docs: <https://docs.kernel.org/accounting/psi.html>
- cgroup2 PSI operational guide (Meta microsite): <https://facebookmicrosites.github.io/cgroup2/docs/pressure-metrics.html>

### A2) Continuous profiling state of the art

For always-on production profiling in 2026:

- Parca: eBPF-based, infrastructure-wide profiling with reported low overhead.
- Pyroscope: production-friendly sampling profiling with practical cost/perf guidance.

Important nuance:
- Overhead varies by workload and sampling settings.
- Claims must be validated with your own canary measurements.

Primary sources:
- Parca FAQ (observed overhead): <https://parca.dev/docs/faq/>
- Grafana/Pyroscope production overhead discussion: <https://grafana.com/blog/continuous-profiling-in-production-a-real-world-example-to-measure-benefits-and-costs/>

### A3) OTel maturity and limits

- OTel logs/metrics/traces are mature and standard for vendor-neutral telemetry.
- OTel profiles signal entered Alpha in 2026; useful for adoption planning, but not as sole critical-production anchor yet.

Primary sources:
- OTel Profiles concept (Alpha): <https://opentelemetry.io/docs/concepts/signals/profiles/>
- OTel Profiles Alpha announcement: <https://opentelemetry.io/blog/2026/profiles-alpha/>
- OTel Logs data model: <https://opentelemetry.io/docs/specs/otel/logs/data-model/>

### A4) "Big player" operational principles (public guidance)

- Google SRE:
  - prioritize actionable, low-noise alerting
  - monitor golden signals
  - keep paging logic simple
- AWS:
  - separate control plane and data plane
  - static stability: system continues on data plane when control plane is impaired
  - cost-governed telemetry (collect only what matters, control cardinality/sampling/retention)
- Netflix:
  - avoid "store all raw logs forever" economics
  - stream/filter/transform/persist selectively

Primary sources:
- Google SRE monitoring: <https://sre.google/sre-book/monitoring-distributed-systems/>
- Google SRE SLO alerting: <https://sre.google/workbook/alerting-on-slos/>
- AWS control vs data plane: <https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/control-plane-and-data-plane.html>
- AWS static stability: <https://aws.amazon.com/builders-library/static-stability-using-availability-zones/>
- AWS telemetry cost optimization: <https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-observability.html>
- Netflix observability lessons: <https://netflixtechblog.com/lessons-from-building-observability-tools-at-netflix-7cfafed6ab17>

### A5) Practical "top-tier" governance stack for this project

Recommended stack for MEXC -> Lance pipeline:

1. Runtime governance
   - cgroup v2 envelopes for each service
   - PSI watchers with thresholds and backpressure actions
2. Observability
   - OTel Collector with strict drop/filter and cardinality budget
   - structured logs with trace correlation
3. Profiling
   - always-on CPU sampling first
   - memory/allocation profiling on canary or time-boxed windows
4. SLOs
   - ingest lag, drop rate, write latency, reconnect success, pressure events
   - burn-rate alerts

---

## Part B - Architecture and language split in 2026

### B1) Is "100% Python control plane + native data plane" universal?

No.

Common production pattern is polyglot by path criticality:

- Control plane:
  - Python where iteration speed and ecosystem matter
  - Go/Java where infra and high-concurrency service patterns dominate
- Data plane / hot path:
  - C++ and Rust (or highly optimized JVM/native stacks) for deterministic performance
  - kernel/eBPF for low-overhead host visibility

### B2) Public evidence for polyglot and control/data-plane separation

- AWS explicit control-plane/data-plane separation and static stability guidance.
- BlackRock describes large-scale asynchronous messaging and multi-language service ecosystem.
- Citadel Securities publicly emphasizes C++26 async, deterministic behavior, and microsecond latency concerns.

Primary sources:
- AWS control/data plane: <https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/control-plane-and-data-plane.html>
- AWS static stability: <https://aws.amazon.com/builders-library/static-stability-using-availability-zones/>
- BlackRock messaging architecture: <https://engineering.blackrock.com/the-blackrock-messaging-system-aeae461e4211>
- BlackRock eventual consistency/Kafka Streams: <https://engineering.blackrock.com/delivering-eventual-consistency-with-kafka-streams-c013a217b9b9>
- Citadel async/C++26 spotlight: <https://www.citadelsecurities.com/careers/career-perspectives/technical-spotlight-async-programming-with-sender-receiver/>

### B3) Performance architecture that actually works in 2026

For this project class, "blazing fast and operable" design means:

- hard split between configuration/policy plane and execution plane
- immutable, versioned contracts from control plane to data plane
- bounded queues and backpressure at every boundary
- append-oriented storage writes in micro-batches
- explicit degradation modes when pressure rises
- canary-first rollout for config and sampling changes

This matches public high-scale design principles better than a language-first dogma.

---

## Confidence and caveats

- Confidence is high for Linux governance primitives (cgroup v2 + PSI) and control/data-plane separation principles.
- Confidence is medium for firm-specific internals where only public blog disclosures exist.
- No public source can prove a single universal "best stack" across all companies and workloads.

The right operating position is:
- adopt proven primitives
- benchmark in your own workload
- keep observability overhead budgeted and audited continuously

---

## Part C - First-pass architecture package (what to add now)

This is the implementation-oriented first pass for this project:

### C1) Plane split for this repository

- Control plane (Python):
  - runtime config loading and validation
  - symbol/timeframe registry management
  - policy and governance actions (threshold ladder)
  - operator APIs/CLI and health endpoints
- Data plane (native/hot path):
  - websocket frame ingestion loop
  - parse/normalize hot path
  - interval aggregation/finalize engine
  - Lance micro-batch writer path

Design rule:
- Control plane can change frequently.
- Data plane must be deterministic, bounded, and regression-tested with replay fixtures.

### C2) What to add in round 1 (must-have)

1. Dynamic timeframe registry with identical aggregation contract across intervals.
2. Hardcoded symbol scope (3-10 symbols) from config.
3. Ingest path for `push.deal` and `push.kline` first.
4. Single interval production path first (`Min1`) to Lance.
5. Runtime governance signals and action ladder:
   - queue pressure
   - write lag
   - process CPU quota %
   - RSS ratio
6. Mismatch evidence and raw retention for forensics.
7. Deterministic replay test using `farmer-sample-events.ndjson`.

### C3) What to defer (explicitly not round 1)

- 700 symbol target
- full symbol catalog service
- multi-exchange abstraction
- upsert and historical rewrite paths
- broad profiling matrix before baseline stability

### C4) Acceptance gate for round 1

- 6h soak with no crash
- no duplicate close for `(symbol, interval, minute_ms)`
- bounded queues under burst
- write lag and drop metrics exposed
- clear degraded behavior under pressure (no deadlock, no unbounded growth)

### C5) Recommended next docs (linked)

- target architecture spec: `docs/planning/architecture/target-architecture-v1.md`
- first pass checklist: `docs/planning/architecture/first-pass-build-checklist.md`
