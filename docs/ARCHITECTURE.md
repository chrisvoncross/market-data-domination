# ARCHITECTURE

This document is the single, operational architecture baseline for this project.

## 1) Architecture style (binding)

- **Control plane in Python**
  - config loading/validation
  - policy/governance decisions
  - orchestration and diagnostics
- **Data plane loops native**
  - hot-path ingest/parse/apply/finalize
  - deterministic, bounded, low-latency execution
- **Direct exchange timeframe truth**
  - ingest `push.kline` directly for all configured intervals (for example Min1/5/15/60)
  - no timeframe-specific code branches in the hot path
  - exchange kline is final truth for candle close values
- **Contract-first runtime**
  - behavior is driven by runtime contract, not ad-hoc code assumptions
- **Append-first storage**
  - micro-batched persistence, no row-by-row hot-path writes
- **Bounded-by-default**
  - bounded queues, explicit drop policy, visible counters

## 2) Hard invariants (binding)

1. Event-time is primary for semantic aggregation.
2. No duplicate final candle for the same `(symbol, interval, minute_ms)`.
3. No hot-path blocking due to maintenance.
4. No unbounded memory/queue growth in production path.
5. No silent drops; every drop must be observable.
6. No schema drift without version increment.
7. No secrets or sensitive infra inventories in docs/logs.
8. Exchange direct kline values are authoritative at finalize time.
9. Heavy feature engineering is out-of-scope for farmer hot path.

## 3) Source-of-truth precedence (binding)

If sources conflict, use this order:

1. `docs/handover/mvp_runtime_contract.json` (runtime semantics)
2. `docs/system_mapping/contracts/*` (interface contracts)
3. `docs/system_mapping/branches/*` (subsystem behavior map)
4. `docs/handover/*` prose and examples
5. research/planning notes

## 4) Required subsystem surfaces

- **Ingestion & resilience**
  - sharded WS connections
  - heartbeat + reconnect policy
  - path diversity
  - ingest required channels:
    - `push.deal`
    - `push.kline` (all configured intervals)
    - `push.depth`/runtime depth equivalent
    - `push.funding.rate`
    - `push.index.price`
    - `push.fair.price`
    - `push.ticker`
- **Semantics & finalize**
  - dedupe keys and tie-break rules
  - finalize window/deadline policy
  - mismatch audit events
  - direct kline override when local reconstruction deviates
- **Storage**
  - raw/features separation
  - append-first, micro-batch
  - pressure-gated maintenance
- **Governance**
  - CPU/RAM/queue/write-lag signals
  - action ladder under pressure
  - SLO/Budget enforcement
- **Derived-minimal in farmer**
  - only essential integrity and quality metrics
  - heavy model/feature transforms belong downstream

## 5) Agent edit rules (binding)

- Build-first: implement -> validate -> map update.
- Do not create new docs unless explicitly required.
- For architecture-impacting changes, update only:
  - affected branch map(s)
  - affected contract(s)
- No commit without explicit user GO.

## 6) Validation gates before "works" claims

Minimum pass criteria:

- contract bootstrap validation passes
- replay/invariant validation passes
- no duplicate final keys
- runtime counters emitted (drops/lag/pressure)
- resource profile captured during validation run

Reference command:
- `scripts/validate_first_pass.sh`

## 7) Positioning statement

For this project class (single-team, high-performance market data MVP), this structure is a **professional and efficient 2026 baseline** aligned with publicly known high-scale patterns:

- control/data plane separation
- contract-driven behavior
- low-overhead governance
- docs-as-code with minimal but strict architecture maps

It is not a universal proof of absolute optimality for every workload, but it is a strong practical target that avoids common failure modes while preserving delivery speed.

## 8) Factual references

- MEXC sourceability baseline: `docs/learnings/mexc-data-sourcing-facts.md`
- Architecture principle baseline: `docs/learnings/architecture-principles-facts.md`
- picows resilience baseline: `docs/learnings/picows-resilience-deep-dive.md`
