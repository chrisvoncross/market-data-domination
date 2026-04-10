# Contracts

Store cross-branch contracts here. A contract must define:

- producer and consumer branches
- schema keys and required fields
- ordering and idempotence expectations
- failure semantics (retry/drop/poison)
- versioning and migration notes

Initial contract docs:

- `contract-ingest-to-agg.md`
- `contract-agg-to-lance.md`
- `contract-gov-signals.md`
