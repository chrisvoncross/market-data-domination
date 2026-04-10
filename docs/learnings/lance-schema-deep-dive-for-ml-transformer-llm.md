# Lance Schema Deep Dive for ML / Transformer / LLM

## Scope

This document defines a production-oriented Lance schema strategy for market-data storage
that is optimized for:

- model training correctness (point-in-time safe),
- low-latency feature serving handoff,
- human and LLM readability without sacrificing typed rigor.

It is designed for adoption on the downstream trading server with minimal translation.

## High-confidence source facts

### Lance / LanceDB facts

- Lance schema is Arrow-compatible and strongly typed.
- Field IDs and schema evolution support safe add/alter/drop operations.
- Timestamp precision/timezone and fixed-size vectors are first-class logical types.
- Schema changes are ACID/versioned; drop/rename are metadata-first where possible.

Sources:
- [Lance Schema Format Specification](https://lance.org/format/table/schema/)
- [LanceDB Schema and Data Evolution](https://docs.lancedb.com/tables/schema)

### Arrow facts

- Columnar layout and dictionary encoding are core primitives for efficient analytics.
- Partitioning schemes (directory/hive/filename) are explicit and typed.
- Typed schemas are immutable contracts for batch/stream interoperability.

Sources:
- [Apache Arrow Columnar Format](https://arrow.apache.org/docs/format/Columnar.html)
- [PyArrow dataset partitioning](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.partitioning.html)

### Feature-store consistency facts

- Point-in-time correctness requires event-time-aligned historical joins.
- TTL is evaluated relative to each entity row timestamp (not query runtime).

Source:
- [Feast Point-in-time joins](https://docs.feast.dev/getting-started/concepts/point-in-time-joins)

## Recommended target schema (v1)

Use three Lance datasets with strict contracts:

1) `raw_events` (append-only, immutable exchange record)  
2) `candles_features` (typed interval features for training/serving parity)  
3) `audit_mismatch` (semantic divergence evidence and forensics)

### 1) `raw_events`

Required columns:

- `event_id` (`string`) - deterministic idempotency key
- `exchange` (`string`) - e.g. `MEXC`
- `symbol` (`string`)
- `channel` (`string`) - normalized channel name
- `event_time` (`timestamp:us:UTC`) - exchange event time (primary timeline)
- `recv_time` (`timestamp:us:UTC`) - local receive time (diagnostic)
- `capture_slot` (`int32`) - resilience slot id
- `payload_json` (`large_string`) - canonical raw payload snapshot
- `schema_version` (`int32`)

Partition keys:

- `date_utc` (derived from `event_time`)
- `symbol`
- `channel`

Rationale:

- preserves exact replayability and auditability;
- keeps ingestion idempotent and append-only;
- supports rapid backtesting/reconstruction without loss.

### 2) `candles_features`

Required identity + temporal columns:

- `row_id` (`string`) - deterministic `(symbol, interval, minute_ms)` key
- `symbol` (`string`)
- `interval` (`string`) - `Min1`, `Min5`, `Min15`, `Min60`, ...
- `minute_time` (`timestamp:ms:UTC`)
- `event_time_close` (`timestamp:us:UTC`)
- `ingest_time_close` (`timestamp:us:UTC`)

Required numeric columns (core):

- `open`, `high`, `low`, `close` (`double`)
- `volume`, `amount` (`double`)
- `trade_count` (`int64`)

Quality / parity columns:

- `decision_kind` (`string`) - e.g. direct exchange truth / override modes
- `is_mismatch` (`bool`)
- `mismatch_reason` (`string`, nullable)
- `source_contract_version` (`string`)
- `schema_version` (`int32`)

Optional ML-ready columns (typed, minimal):

- `spread_bps`, `imbalance`, `oi_pct_change`, `cvd_pct` (`double`, nullable)
- `feature_valid_mask` (`uint32`) - bitmask for missingness/readiness

Partition keys:

- `date_utc` (from `minute_time`)
- `interval`
- `symbol`

Rationale:

- fixed temporal/identity keys guarantee point-in-time training parity;
- quality flags avoid silent leakage;
- trading server can consume the exact typed contract for online/offline consistency.

### 3) `audit_mismatch`

Required columns:

- `audit_id` (`string`)
- `symbol` (`string`)
- `interval` (`string`)
- `minute_time` (`timestamp:ms:UTC`)
- `expected_source` (`string`)
- `observed_source` (`string`)
- `reason` (`string`)
- `created_at` (`timestamp:us:UTC`)
- `context_json` (`large_string`)

Partition keys:

- `date_utc`
- `interval`

Rationale:

- keeps semantic incidents queryable without polluting feature tables;
- enables SLO-style monitoring for semantic correctness.

## LLM readability without degrading schema quality

For LLM workflows, do **not** replace typed tables with free-form text.  
Instead, add deterministic text projections (derived views/materializations):

- `candles_features_text_view`:
  - `row_id`, `symbol`, `interval`, `minute_time`,
  - `summary_text` (stable template from typed columns),
  - `json_compact` (canonical compact JSON string)

This keeps primary truth strongly typed and still gives LLM-friendly representations.

## Non-negotiable design rules

- Event-time is always primary timeline.
- Append-only for raw ingest.
- Deterministic idempotency keys for every table.
- Explicit schema versioning on every row family.
- No nullable ambiguity for key columns.
- No training/serving skew: same feature definitions and keys across both planes.

## Practical “best-known” conclusion

For this project, a three-dataset Lance design (`raw_events`, `candles_features`, `audit_mismatch`)
with strict event-time keys and typed quality flags is the strongest practical schema baseline:

- high-performance for model pipelines,
- safe for point-in-time ML semantics,
- readable for humans and LLM systems through derived text views,
- evolvable without destructive rewrites.
