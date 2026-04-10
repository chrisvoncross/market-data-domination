# Contract: Aggregation -> Lance

## Parties

- Producer: `BR-AGG`
- Consumer: `BR-LANCE`

## Required fields (feature rows)

- `row_id` (`symbol:interval:minute_time`)
- `symbol`
- `interval`
- `minute_time`
- `open`, `high`, `low`, `close`, `volume`, `trade_count`
- `decision_kind`, `is_mismatch`
- schema metadata (`schema_version`, `source_contract_version`)

## Delivery semantics

- append-only writes in MVP
- at-least-once delivery possible at boundary; consumers dedupe by semantic key if required

## Idempotence guidance

Recommended consumer key:
- `(row_id, schema_version)`

## Versioning

- contract_version: `v1`
- migration strategy: add new nullable columns first, then promote

## Current Lance tables

- `raw_events`
- `Min1`, `Min5`, `Min15`, `Min60`, ...
- `audit_mismatch`

## Current validation outputs

- live run summary includes `lance.raw_rows`, `lance.feature_rows`, `lance.mismatch_rows`
- latest live run wrote interval tables: `Min1`, `Min5`, `Min15`, `Min60`
