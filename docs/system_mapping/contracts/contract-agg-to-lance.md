# Contract: Aggregation -> Lance

## Parties

- Producer: `BR-AGG`
- Consumer: `BR-LANCE`

## Required fields (feature rows)

- `symbol`
- `interval`
- `timestamp_ms`
- schema and compute metadata (`schema_version`, `compute_version`)

## Delivery semantics

- append-only writes in MVP
- at-least-once delivery possible at boundary; consumers dedupe by semantic key if required

## Idempotence guidance

Recommended consumer key:
- `(symbol, interval, timestamp_ms, schema_version, compute_version)`

## Versioning

- contract_version: `v1`
- migration strategy: add new nullable columns first, then promote
