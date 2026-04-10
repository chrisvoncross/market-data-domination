# BR-LANCE - Lance Storage

## Metadata

- branch_id: BR-LANCE
- owner: TODO
- status: active
- last_updated: 2026-04-10
- last_verified: 2026-04-10
- verification_method: live run + Lance table row count verification

## Mission

Provide durable append storage for raw market records and interval features with bounded write latency.

## Scope

In scope:
- append-only writes
- micro-batch flush
- cleanup/compaction under pressure guardrails

Out of scope:
- upsert semantics in MVP
- historical rewrite jobs

## Dataset layout (current)

- root: `data/lance/`
- raw events table: `raw_events`
- feature tables by interval: `Min1`, `Min5`, `Min15`, `Min60`, ...
- mismatch audit table: `audit_mismatch`

## Write profile (current)

- mode: append-only table adds
- cadence: per `mdf-live` run output flush
- table creation: lazy create on first write

## Core invariants

1. Hot path cannot block on compaction.
2. Dataset errors do not crash main loops.
3. Write lag remains observable and actionable.
4. Feature rows are keyed by `(symbol, interval, minute_time)` semantics.

## Observability focus

- write lag
- flush duration
- compact skip count under pressure
- write error rate

## Code locations

- live writer implementation: `src/control_plane/lance_sink.py`
- live runtime integration: `src/control_plane/live_run.py`
- schema guidance: `docs/learnings/lance-schema-deep-dive-for-ml-transformer-llm.md`

## Run commands

- `PYTHONPATH=src .venv/bin/python -m control_plane.live_run --duration-sec 120 --lance-root data/lance`
- `PYTHONPATH=src .venv/bin/python -c "import lancedb; db=lancedb.connect('data/lance'); print(db.list_tables())"`

## Last live check

- command: `PYTHONPATH=src .venv/bin/python -m control_plane.live_run --duration-sec 180 --lance-root data/lance`
- result:
  - raw rows written: `25621`
  - feature rows written: `26`
  - mismatch rows written: `11`
  - interval tables written: `Min1`, `Min5`, `Min15`, `Min60`
