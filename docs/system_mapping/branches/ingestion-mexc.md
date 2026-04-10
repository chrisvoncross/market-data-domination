# BR-INGEST-MEXC - MEXC Ingestion

## Metadata

- branch_id: BR-INGEST-MEXC
- owner: TODO
- status: active
- last_updated: 2026-04-10
- last_verified: 2026-04-10
- verification_method: handover review (`docs/handover/*`)

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
  - `push.depth.full`
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

## Code locations

- TODO: set concrete runtime paths for WS client, parser, and channel router modules.

## Run commands

- TODO: add exact local start/test/soak commands for ingestion-only pipeline validation.

## SLO seeds

- reconnect success under endpoint turbulence
- ingress drop rate at queue boundary
- ingest lag

## Risks / TODO

- explicit gap detector module is not yet implemented
- exact native dedupe keys not yet documented in Python layer
