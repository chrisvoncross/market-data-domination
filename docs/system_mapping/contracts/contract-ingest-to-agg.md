# Contract: Ingestion -> Aggregation

## Parties

- Producer: `BR-INGEST-MEXC`
- Consumer: `BR-AGG`

## Required fields

- `symbol`
- `channel`
- `recv_ts_ms`
- event payload with event-time field (`t`/`timestamp_ms`) when available
- required channel set (runtime baseline):
  - `push.deal`
  - `push.kline`
  - `push.depth.full`
  - `push.ticker`
  - `push.funding.rate`
  - `push.index.price`
  - `push.fair.price`

## Semantics

- event-time is primary for aggregation timelines
- ingest-time is retained for audit and fallback only
- malformed payloads are skipped, not fatal
- direct exchange kline is authoritative for final candle values per interval
- local Min1 reconstruction is validation-only when mismatch auditing is enabled

## Idempotence and ordering

- deal dedupe key: `(symbol, minute_ms, trade_id)` when `trade_id > 0`
- finalize duplicate guard key: `(symbol, interval_code, minute_ms)`
- late/out-of-order events are accepted within configured finalize window
- tie-break order basis: `ts`, `has_trade_id`, `trade_id/order_key`
- no timeframe-specific branch logic: one handler for all configured intervals

Primary runtime source:
- `docs/handover/mvp_runtime_contract.json`

## Versioning

- contract_version: `v1`
- backward compatibility: additive fields only in v1 line

## Current validation outputs

- routed events: `event_type=routed_event`
- finalized minute rows: `event_type=final_candle`
- snapshot divergence audit: `event_type=mismatch_event`
- live dry-run summary: `.artifacts/live/live_summary.json`
- live data-plane output: `.artifacts/live/live_dp_out.ndjson`
- all-channel observation check: `missing_channels_observed` in live summary must be empty
- latest check status: `missing_channels_observed=[]` on 240s live run
