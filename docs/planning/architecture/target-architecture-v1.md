# Target Architecture v1

## Objective

Build a minimal high-performance market data farmer with:
- Python control plane,
- native/hot-path data plane,
- low-overhead governance and observability.

## L1 - System context

External:
- MEXC futures websocket feeds

Internal:
- ingestion, aggregation, storage, governance, operator control

Outputs:
- raw and feature datasets in Lance
- runtime telemetry for alerts and tuning

## L2 - Container view

1. `control-plane` (Python)
   - config, policy, registry, orchestration, diagnostics
2. `data-plane-ingest` (native/hot path)
   - websocket slots, frame parsing, channel fanout
3. `data-plane-agg` (native/hot path)
   - event-time aggregation and finalize decisions
4. `data-plane-write` (native/hot path or optimized writer)
   - bounded micro-batch append to Lance
5. `governor` (Python + kernel metrics)
   - pressure classification and action ladder
6. `telemetry-pipeline` (OTel-compatible)
   - logs/metrics/traces export with cardinality controls

## L3 - Key contracts

- ingest -> agg:
  - required: symbol, channel, recv_ts_ms, payload event-time where available
  - semantics: event-time primary
- agg -> write:
  - required: symbol, interval, timestamp_ms, schema/compute version
  - semantics: append, semantic dedupe key on read side if needed
- gov -> all:
  - required metrics and actions are explicit and observable

See:
- `docs/system_mapping/contracts/contract-ingest-to-agg.md`
- `docs/system_mapping/contracts/contract-agg-to-lance.md`
- `docs/system_mapping/contracts/contract-gov-signals.md`

## Round 1 build set

Must include:

1. Dynamic timeframe registry.
2. Hardcoded 3-symbol start (`BTC_USDT`, `ETH_USDT`, `SOL_USDT`).
3. Channels: `push.deal` + `push.kline` first.
4. `Min1` interval path to Lance.
5. Bounded queues and drop-on-full behavior.
6. Governance metrics and action ladder.
7. Replay test with handover fixtures.

Must exclude:

- 700 symbol startup target
- full symbol catalog and ID service
- multi-exchange abstraction
- non-essential profile types before stability

## Non-negotiable invariants

1. No duplicate `(symbol, interval, minute_ms)` close records.
2. No unbounded queue growth.
3. No hot-path blocking on maintenance operations.
4. No loss of mismatch evidence when produced.
5. No silent contract drift.

## Performance and safety gates

- 6h soak pass
- bounded queue pressure under burst
- measurable lag/drop/write signals
- deterministic degraded behavior under pressure

## Evolution path after round 1

1. Add depth/ticker/funding/index/fair channels.
2. Enable `Min5/Min15/Min60` via same contract.
3. Scale symbols in controlled steps (10 -> 25 -> 50).
4. Tune profiling rollout by canary measurements.
