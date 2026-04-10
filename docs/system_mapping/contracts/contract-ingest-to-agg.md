# Contract: Ingestion -> Aggregation

## Parties

- Producer: `BR-INGEST-MEXC`
- Consumer: `BR-AGG`

## Required fields

- `symbol`
- `channel`
- `recv_ts_ms`
- event payload with event-time field (`t`/`timestamp_ms`) when available

## Semantics

- event-time is primary for aggregation timelines
- ingest-time is retained for audit and fallback only
- malformed payloads are skipped, not fatal

## Idempotence and ordering

- native dedupe applies downstream (exact key details pending documentation)
- late/out-of-order events are accepted within configured finalize window

## Versioning

- contract_version: `v1`
- backward compatibility: additive fields only in v1 line
