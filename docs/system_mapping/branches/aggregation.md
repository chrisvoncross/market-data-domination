# BR-AGG - Aggregation Engine

## Metadata

- branch_id: BR-AGG
- owner: TODO
- status: active
- last_updated: 2026-04-10
- last_verified: 2026-04-10
- verification_method: contract + smoke replay

## Mission

Produce deterministic interval feature rows from event-time market data with controlled late/out-of-order handling.

## Scope

In scope:
- interval aggregation over configured windows
- event-time priority with ingest-time audit fields
- finalize decisions and mismatch evidence emission

Out of scope:
- custom per-interval formula divergence (MVP keeps identical semantics across windows)

## Window model

- dynamic interval registry is runtime-driven (`Min1`, `Min5`, `Min15`, `Min60`, ...)
- all intervals use one unified handler (no timeframe-specific hot-path branch logic)
- direct exchange kline values are authoritative for each interval finalize
- primary runtime source: `docs/handover/mvp_runtime_contract.json`

## Core invariants

1. No duplicate minute close for `(symbol, interval, minute_ms)`.
2. Event-time remains primary timeline.
3. Min1 local reconstruction can emit mismatch evidence, but final values come from direct exchange kline.

## Inputs and outputs

Inputs:
- normalized deal/kline/depth/ticker/funding/index/fair events

Outputs:
- Gold feature rows
- mismatch events

## Observability focus

- finalize wait and deadline behavior
- late event handling counts
- duplicate prevention counters

## Code locations

- native seam (current): `native/data_plane/src/main.rs`
- control-plane validation: `src/control_plane/runtime_contract.py`, `src/control_plane/plan.py`
- validation harness: `scripts/validate_first_pass.sh`

## Run commands

- `scripts/first_pass_smoke.sh`
- `scripts/validate_first_pass.sh`
- `PYTHONPATH=src .venv/bin/python -m control_plane.live_run --duration-sec 30`

## Contract-locked semantics

- dedupe key (deal ingest): `(symbol, minute_ms, trade_id)` when `trade_id > 0`
- finalize duplicate guard key: `(symbol, interval_code, minute_ms)`
- tie-break anchor: `ts`, `has_trade_id`, `trade_id/order_key`
- direct-TF finalization source: exchange kline by interval

## Remaining gaps

- full production-grade finalize state machine parity with legacy native engine

## Last live check

- command: `PYTHONPATH=src .venv/bin/python -m control_plane.live_run --duration-sec 240`
- result:
  - routed frames: `11339`
  - kline frames: `6373`
  - final candles: `24`
  - mismatch events (Min1 local-vs-direct audit): `15`
  - parse errors: `0`
