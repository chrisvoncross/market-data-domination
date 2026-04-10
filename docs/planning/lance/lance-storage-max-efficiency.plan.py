---
name: lance-storage-max-efficiency-v5
overview: Align Lance efficiency work to real repo paths/APIs and maximize storage efficiency with bounded maintenance, no hot-path blocking, and no additional hardware cost.
todos:
  - id: wp0-align-plan-to-repo
    content: Align plan assumptions to current code (`src/control_plane/lance_sink.py`, lancedb APIs) and remove stale path/API references.
    status: done
  - id: wp1-set-new-table-format-policy
    content: Set new-table storage format policy using LanceDB storage options (`new_table_data_storage_version`) and verify runtime compatibility.
    status: pending
  - id: wp2-bounded-maintenance-loop
    content: Add bounded periodic maintenance (compaction + cleanup) outside append hot path, with pressure gates and strict runtime budgets.
    status: pending
  - id: wp3-retention-policy-safe-defaults
    content: Introduce explicit retention policy with safe defaults (not overly aggressive version pruning) and rollback-safe behavior.
    status: pending
  - id: wp4-artifact-disk-guardrails
    content: Add overnight-run artifact retention/rotation so `.artifacts` does not dominate disk usage.
    status: pending
  - id: wp5-migration-script
    content: Add one-shot migration helper for existing tables and row-count parity checks.
    status: pending
  - id: wp6-benchmark-and-guardrails
    content: Run before/after benchmarks (1h baseline) and enforce no-downgrade guardrails.
    status: pending
  - id: wp7-optional-encoding-ab
    content: Evaluate optional per-column encoding controls (zstd dict-values, BSS) behind A/B gates.
    status: pending
  - id: wp8-overnight-acceptance
    content: Run overnight acceptance only after storage + artifact controls are active.
    status: pending
isProject: false
---

# Lance Storage Max Efficiency Plan (v5, corrected)

## Why this update

This plan is updated to match the actual codebase and current official API guidance.

Key corrections applied:
- real writer path is `src/control_plane/lance_sink.py` (not `io_adapters/...`)
- repo currently uses `lancedb` table APIs, not direct `write_dataset(...)` hot path
- LanceDB docs deprecate direct `data_storage_version` argument on table creation; use storage options (`new_table_data_storage_version`)
- aggressive "always keep only 2 versions" is not a safe default for all operations
- overnight disk pressure is currently driven heavily by `.artifacts`, not just Lance data files

## Goals

1. Maximize storage efficiency with no extra hardware.
2. Keep ingestion non-blocking.
3. Preserve ML readability (logical schema unchanged).
4. Avoid regressions in append p99, scan latency, CPU, and RSS.

## Hard guardrails (no-downgrade)

- **Correctness:** zero row loss; deterministic key semantics unchanged.
- **Write latency:** append p99 regression budget <= +5%.
- **Read latency:** validation scan regression budget <= +5%.
- **CPU:** no material increase beyond current operating band.
- **Memory:** no material RSS regression.
- **Disk:** storage must improve or remain neutral before promotion.

If any guardrail fails, candidate is disabled or rolled back.

## Current baseline facts (from recent runs)

- 60m / 750 symbols:
  - CPU normal band ~6.5% to 9.5% (p95/p99 in this band)
  - no queue drops / no parse errors
- disk footprint observation:
  - Lance data dir (60m): ~790 MB
  - `.artifacts` dir (60m): ~1.2 GB

Implication: overnight runs need both Lance optimization and artifact retention controls.

## Target architecture

```mermaid
flowchart TD
  ingest[Live ingestion] --> writer[Lance writer]
  writer --> lance[(Lance tables)]
  writer --> maint[Bounded maintenance loop]
  maint --> lance
  ingest --> obs[Observability artifacts]
  obs --> retention[Artifact retention/rotation]
```

Principles:
- append path remains cheap and non-blocking
- maintenance is periodic/bounded and pressure-aware
- retention policies prevent disk explosion during long soaks

## Work packages

### WP1: New-table format policy

**Code surface:** `src/control_plane/lance_sink.py` table creation/open flow.

Actions:
- set new-table storage version policy through supported LanceDB options (`new_table_data_storage_version`)
- ensure all environments can read chosen format before rollout

Notes:
- prefer stable format path first
- avoid undocumented or deprecated API paths in production code

### WP2: Bounded maintenance loop (compaction + cleanup)

**Code surface:** `src/control_plane/lance_sink.py`

Actions:
- run maintenance periodically (not per append)
- bound compaction work per cycle (fragment/file limits)
- skip or defer maintenance under pressure (CPU/memory/io signals)
- emit maintenance metrics in summary/observability outputs

### WP3: Safe retention defaults

Actions:
- define retention policy that balances disk reclamation with rollback/time-travel safety
- avoid hardcoding overly aggressive minimal versions as universal default
- make policy explicit and configurable

### WP4: Artifact disk guardrails (critical for overnight)

Actions:
- add retention/rotation for `.artifacts/live_*` raw outputs
- keep governance artifacts (samples/incidents/spikes/transitions) while limiting bulky raw payload artifacts
- optionally support "overnight mode" that writes lean artifacts only

### WP5: One-shot migration tooling

Actions:
- add migration helper for existing Lance tables
- validate row counts/checksums before and after
- never auto-migrate on live startup

### WP6: Benchmark and promotion gates

Run standardized A/B:
- 1h baseline (pre)
- 1h candidate (post)

Measure:
- table size on disk
- fragment/version counts
- append p99
- scan/verify latency
- CPU and RSS bands

Promote only if all guardrails pass.

### WP7: Optional encoding A/B (only after stability)

Candidates (feature-flagged):
- dictionary value compression trials (`lz4` vs `zstd`) for repetitive string columns
- BSS-oriented experiments for floating-point columns where beneficial
- deterministic pre-sort trials if they reduce file size without write-path penalty

Important:
- physical encoding changes must not alter logical schema/readability
- keep defaults conservative unless A/B proves improvement

### WP8: Overnight acceptance

Preconditions:
- WP2 + WP4 active
- no-downgrade gates green on 1h run

Acceptance:
- no queue drops
- no parse errors
- bounded disk growth
- no adverse CPU/RSS regression

## What does not change

- Native data-plane loop remains native.
- Lance remains in control-plane I/O adapter path.
- Logical ML schema remains readable and stable.

## What this plan can realistically deliver

With this corrected rollout, we should get substantial storage efficiency gains
without extra hardware and without harming ML readability.

Primary risk to overnight disk stability is currently artifact volume; this plan
explicitly addresses that alongside Lance table efficiency.

## References

- [Lance v4.0.0 release notes](https://github.com/lance-format/lance/releases/tag/v4.0.0)
- [Lance format v2.2 benchmarks](https://www.lancedb.com/blog/lance-format-v2-2-benchmarks-half-the-storage-none-of-the-slowdown)
- [Lance format 2.2 deep dive](https://lancedb.com/blog/lance-file-format-2-2-taming-complex-data)
- [Lance encoding specification](https://lance.org/format/file/encoding/)
- [LanceDB Python API](https://lancedb.github.io/lancedb/python/python/)
- [LanceDB storage configuration](https://docs.lancedb.com/storage/configuration)
- [Parquet BYTE_STREAM_SPLIT reference](https://parquet.apache.org/docs/file-format/data-pages/encodings/#byte-stream-split-byte_stream_split--9)
- [Lance auto cleanup PR](https://github.com/lance-format/lance/pull/3572)
- [Lance retain latest N versions PR](https://github.com/lance-format/lance/pull/4614)
- [Lance format 2.3 introduction PR](https://github.com/lance-format/lance/pull/6088)
