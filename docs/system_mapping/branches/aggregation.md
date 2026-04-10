# BR-AGG - Aggregation Engine

## Metadata

- branch_id: BR-AGG
- owner: TODO
- status: active
- last_updated: 2026-04-10
- last_verified: 2026-04-10
- verification_method: handover review + sample event pass

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

- dynamic interval registry expected (`Min1`, `Min5`, `Min15`, `Min60`)
- all intervals should share same aggregation contract in MVP

## Core invariants

1. No duplicate minute close for `(symbol, interval, minute_ms)`.
2. Event-time remains primary timeline.
3. Mismatch evidence is retained when decision indicates mismatch.

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

- TODO: set concrete runtime paths for due-state engine binding, finalize decision logic, and feature row emission.

## Run commands

- TODO: add replay test commands using `docs/handover/farmer-sample-events.ndjson`.

## TODO gaps

- explicit dedupe key disclosure from native layer
- final production lateness thresholds per deployment
