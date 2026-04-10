# BR-LANCE - Lance Storage

## Metadata

- branch_id: BR-LANCE
- owner: TODO
- status: active
- last_updated: 2026-04-10
- last_verified: 2026-04-10
- verification_method: handover review (`farmer-principles.md`)

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

- raw: `data/lance/raw/<channel>`
- features: `data/lance/features/<interval>`

## Write profile (current)

- feature batch target: up to `5000` rows or cycle threshold
- raw batch target: up to `2000` rows or cycle threshold
- mode: append

## Core invariants

1. Hot path cannot block on compaction.
2. Dataset errors do not crash main loops.
3. Write lag remains observable and actionable.

## Observability focus

- write lag
- flush duration
- compact skip count under pressure
- write error rate

## Code locations

- TODO: set concrete runtime paths for raw/features Lance writers, batching policy, cleanup, and compaction.

## Run commands

- TODO: add dataset smoke-check and write-latency benchmark commands.
