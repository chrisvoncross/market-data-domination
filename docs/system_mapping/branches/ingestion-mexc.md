# BR-INGEST-MEXC - MEXC Ingestion

## Metadata

- branch_id: BR-INGEST-MEXC
- owner: TODO
- status: active
- last_updated: 2026-04-10
- last_verified: 2026-04-10
- verification_method: official docs + runtime code path check

## Mission

Continuously ingest MEXC futures market events for scoped symbols/channels with bounded loss behavior.

## Scope

In scope:
- WS connect/subscription for selected symbols/channels
- frame parsing and channel routing
- bounded ingress queueing

Out of scope:
- historical backfill
- cross-exchange normalization

## Config snapshot (current)

- symbols: `BTC_USDT`, `ETH_USDT`, `SOL_USDT`
- channels:
  - `push.deal`
  - `push.kline`
  - `push.depth.full` (runtime naming; official docs list `push.depth`)
  - `push.ticker`
  - `push.funding.rate`
  - `push.index.price`
  - `push.fair.price`

## Core invariants

1. Only `push.*` market frames are treated as market events.
2. Ingress queues remain bounded.
3. Invalid payloads do not crash ingest loops.

## Inputs and outputs

Inputs:
- MEXC WS frames (`wss://contract.mexc.com/edge`)

Outputs:
- raw channel records
- normalized events for aggregation path
- per-channel coverage counters in live summary

## Code locations

- control-plane live ingestion: `src/control_plane/live_run.py`
- resilience slot planning/runtime: `src/control_plane/resilience_runtime.py`
- config/interval registry: `src/control_plane/config.py`, `src/control_plane/registry.py`, `src/control_plane/plan.py`
- native routing seam: `native/data_plane/src/main.rs`

## Run commands

- `PYTHONPATH=src .venv/bin/python -m control_plane.main --config docs/handover/farmer-config.json --runtime-contract docs/handover/mvp_runtime_contract.json`
- `PYTHONPATH=src .venv/bin/python -m control_plane.live_run --duration-sec 120`
- `scripts/validate_resilience.sh 120 300`
- `scripts/validate_first_pass.sh`

## SLO seeds

- reconnect success under endpoint turbulence
- ingress drop rate at queue boundary
- ingest lag

## Last live check

- command: `scripts/validate_resilience.sh 60 120`
- result:
  - normal run routed frames: `5384`
  - stress run routed frames: `12124`
  - all required channels observed (`missing_channels_observed=[]`)
  - parse errors: `0`
  - slot metrics included in summary

## Risks / TODO

- explicit gap detector module is not yet implemented
- depth channel naming parity (`push.depth` vs `push.depth.full`) requires explicit adapter note in runtime contract
