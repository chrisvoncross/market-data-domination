# Lance Storage Efficiency Deep Dive (2026)

## Scope

Evaluate whether the current Lance efficiency plan can maximize storage efficiency
without adding hardware cost and without harming ML readability.

Input reviewed:
- `docs/planning/lance/lance-storage-max-efficiency.plan.py`
- current code path: `src/control_plane/lance_sink.py`
- official Lance/LanceDB docs and release material (sources below)

## Executive conclusion

The plan direction is strong, but not implementation-ready as written for this repo.

Why:
- It uses the right themes (format upgrade, cleanup, compaction, guardrails, A/B gates).
- But parts are stale/mismatched with the actual code and current LanceDB API surface.

With corrections listed below, the plan can deliver major storage gains while preserving
ML readability and keeping compute overhead bounded.

## What is correct in the plan

1. **File-format upgrade is high leverage**
   - Format 2.2 is stable and designed to improve compression/performance.
   - Data storage version should be explicitly controlled for new tables.

2. **Lifecycle management is mandatory**
   - Append-heavy workloads need compaction + old-version cleanup.
   - Otherwise fragmentation and manifest/version accumulation degrade storage and scans.

3. **Guardrails and A/B promotion are correct**
   - No-downgrade gates on p99 append latency, scan latency, CPU, RAM, correctness are the right professional approach.

4. **Field-level encoding trials are valid**
   - Dictionary-value compression controls and BSS-capable paths exist.
   - Must remain opt-in and benchmark-gated.

## Critical corrections needed

1. **Path/API mismatch with repo reality**
   - Plan targets `io_adapters/lance_sink.py`, but this repo writes via `src/control_plane/lance_sink.py`.
   - Plan snippets use `lance.write_dataset(...)`, while current code uses `lancedb` table APIs (`table.add(...)`).
   - Action: translate design to current API surface before implementation.

2. **`data_storage_version` usage is outdated in LanceDB table creation**
   - LanceDB Python docs mark `create_table(..., data_storage_version=...)` as deprecated.
   - Preferred control is `storage_options["new_table_data_storage_version"]`.
   - Action: set storage options at connect/create layer, not legacy argument paths.

3. **Version retention policy is too aggressive by default**
   - "Keep only 2 versions always" can reduce rollback/time-travel safety and may conflict with longer-running readers.
   - Action: start with a safer retention window/policy, then tighten after operational evidence.

4. **Per-commit cleanup/compaction can add avoidable write-path overhead**
   - Compaction is rewrite-heavy; per-commit execution is not suitable for high-ingest loops.
   - Action: run maintenance periodically and bounded (background/off hot path), with pressure gates.

5. **Compression expectations should be workload-specific**
   - 50%+ reductions are documented for many multimodal/text-heavy cases.
   - For mostly numeric OHLCV candles, gains may be lower; benchmark, do not assume.

6. **Plan references stale "already implemented" sections**
   - It references non-present paths/devlogs in this repo.
   - Action: remove stale assertions and replace with current measurable state.

## No-extra-hardware-cost strategy (recommended)

1. **Keep write path simple and low-CPU first**
   - Use stable format defaults and LZ4-first posture.
   - Avoid globally forcing slower compression until A/B proves net benefit.

2. **Batch appends to reduce small-file churn**
   - Larger micro-batches reduce fragment explosion and metadata overhead.

3. **Run bounded maintenance outside critical ingestion sections**
   - Periodic compaction + cleanup with rate/fragment limits and pressure gates.

4. **Separate storage concerns by value**
   - Raw payload retention and feature retention should have different policies.
   - High-cardinality raw payload JSON is often the largest long-run disk driver.

5. **Preserve ML readability**
   - Keep logical schema stable (`symbol`, `interval`, `minute_time`, OHLCV fields).
   - Physical encoding/compression changes should be transparent to readers.

## Important practical finding for overnight runs

Disk pressure is currently not only a Lance-format problem:
- In this project, `.artifacts/live_*` raw outputs can exceed Lance dataset size during long runs.
- Example observed:
  - 60m Lance data: ~790 MB
  - 60m run artifacts directory: ~1.2 GB

So, for overnight drift studies, disable or rotate heavy raw artifacts; otherwise
artifact logs can dominate disk growth even if Lance is optimized.

## Recommended rollout order

1. Align plan with current `src/control_plane/lance_sink.py` API.
2. Set new-table format policy using current LanceDB storage options.
3. Add bounded background maintenance (compact + cleanup) with governance gates.
4. Run 1h/8h A/B with guardrails and storage accounting.
5. Promote optional column-level encoding only if non-regressive.

## Verdict on the plan

The plan is strategically strong but operationally mixed:
- **Keep:** format/lifecycle/guardrails/A-B philosophy.
- **Fix:** API assumptions, retention aggressiveness, stale implementation references.

After these fixes, yes: it can likely deliver substantial storage efficiency
without extra hardware and without harming ML readability.

## Sources

- [Lance v4.0.0 release notes](https://github.com/lance-format/lance/releases/tag/v4.0.0)
- [Lance format v2.2 benchmarks](https://www.lancedb.com/blog/lance-format-v2-2-benchmarks-half-the-storage-none-of-the-slowdown)
- [Lance format 2.2 deep dive](https://lancedb.com/blog/lance-file-format-2-2-taming-complex-data)
- [Lance encoding specification](https://lance.org/format/file/encoding/)
- [LanceDB Python API (`cleanup_old_versions`, `compact_files`, `optimize`)](https://lancedb.github.io/lancedb/python/python/)
- [LanceDB storage configuration (`new_table_data_storage_version`)](https://docs.lancedb.com/storage/configuration)
- [Parquet BYTE_STREAM_SPLIT reference](https://parquet.apache.org/docs/file-format/data-pages/encodings/#byte-stream-split-byte_stream_split--9)
- [Lance auto cleanup PR](https://github.com/lance-format/lance/pull/3572)
- [Lance retain latest N versions PR](https://github.com/lance-format/lance/pull/4614)
- [Lance format 2.3 introduction PR](https://github.com/lance-format/lance/pull/6088)
