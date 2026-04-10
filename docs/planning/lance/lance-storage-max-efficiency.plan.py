---
name: v4-lance-storage-upgrade
overview: Upgrade Lance from 2.0.1-era usage to 4.0 best practices -- format 2.2, auto-cleanup, zero-compaction-cron, native compression -- achieving maximum storage efficiency and minimum IO overhead for append-heavy minute-candle ingestion.
todos:
  - id: audit-current-lance-usage
    content: Audit current LanceSink and verify_run1_contracts for all write_dataset / LanceDataset calls, document current behavior and fragment accumulation pattern.
    status: pending
  - id: upgrade-write-path-format-2-2
    content: Switch write_dataset to data_storage_version="2.2" with LZ4 dict compression for all new datasets.
    status: pending
  - id: add-auto-cleanup-hook
    content: Wire auto_cleanup into LanceSink so old versions are pruned automatically on every Nth commit without a separate cron.
    status: pending
  - id: periodic-compact-files
    content: Add lightweight periodic compact_files call (every N minutes, bounded source fragments) to merge small fragments without IO burst.
    status: pending
  - id: migrate-existing-datasets
    content: Write one-shot migration script to convert existing 2.0 datasets to format 2.2 and clean legacy versions.
    status: pending
  - id: benchmark-before-after
    content: Measure storage size, write latency, and scan speed before and after upgrade on a real 1-hour candle dataset.
    status: pending
  - id: acceptance-overnight
    content: Run overnight with new settings, verify no fragment explosion, stable memory, and no data loss.
    status: pending
  - id: no-downgrade-guardrails
    content: Add explicit no-downgrade guardrails (read latency, append p99, CPU, memory) and enforce rollback-on-regression policy.
    status: pending
  - id: wp6-schema-encoding-finetune
    content: Add optional low-risk schema/encoding/batching optimizations with A/B validation and strict promotion gates.
    status: pending
  - id: wp0-upgrade-pylance
    content: "Blocker: upgrade pylance from 3.0.1 to 4.0.0 -- format 2.2 requires pylance 4.0+."
    status: pending
  - id: wp7-column-encoding-ohlcv
    content: OHLCV-specific column encoding trials (zstd dict for symbol, BSS for price floats, delta-friendly pre-sort for minute_ms).
    status: pending
  - id: wp8-format-2-3-evaluation
    content: Evaluate Lance format 2.3 once stable (adaptive encoding selection) -- track upstream stability, A/B when ready.
    status: pending
isProject: false
---

# V4 Lance Storage Upgrade Plan (Format 2.2 + Zero-Cron Compaction)

## Problem Statement

The current `LanceSink` uses `write_dataset(table, path, mode="append")` with no further configuration:
- No `data_storage_version` specified (defaults to legacy format).
- No `compact_files()` -- every append creates a new fragment file. Over hours of 700+ symbol ingestion this produces thousands of tiny fragment files.
- No `cleanup_old_versions()` -- every append creates a new version manifest. Version metadata accumulates unbounded.
- No compression tuning -- legacy format uses default encoding, missing LZ4 dictionary compression and all-null compression from format 2.2.

Result: storage bloat, degraded scan performance over time, and the need for a manual compaction cron that creates IO bursts during live ingestion.

## Decisions Locked

- Upgrade to **Lance format 2.2** (`data_storage_version="2.2"`) for all new writes.
- Use **auto-cleanup** to keep only 2 versions (current + 1 safety buffer). No cron.
- Use **periodic bounded compaction** (every 5 minutes, max 32 source fragments per pass) to merge small files without IO burst. Runs on the existing LanceSink worker thread.
- Keep all Lance operations in `io_adapters/lance_sink.py` (control-plane Python). No Lance calls on the native hot path.
- Existing datasets: one-shot migration script, not automatic background migration.

## No-Downgrade Guardrails (Hard Requirement)

All optimizations in this plan are **upgrade-only** and must be **non-regressive**. Any candidate change is disabled or rolled back if it violates guardrails.

- **Data correctness:** zero row loss, deterministic ordering contract unchanged.
- **Write latency:** append p99 must not regress beyond noise budget (target <= +5% vs baseline).
- **Read latency:** full-scan / verify path must not regress beyond noise budget (target <= +5% vs baseline).
- **CPU:** average process CPU must remain within existing operating band (7-10% target, <= +1% absolute regression budget).
- **Memory:** RSS must not increase materially (<= +5% regression budget).
- **Storage:** promoted only if storage footprint improves or stays neutral.

If any guardrail is violated in A/B or overnight run: keep previous setting and mark candidate as rejected.

## WP0: Upgrade pylance to 4.0.0 (BLOCKER)

**This must happen before anything else.** Format 2.2 requires pylance 4.0+.

```
Current:  pylance 3.0.1 (installed) -- does NOT support data_storage_version="2.2"
Target:   pylance 4.0.0 (available, already declared in pyproject.toml as >=4.0.0)
```

```bash
pip install --upgrade pylance==4.0.0
```

Verify: `python -c "import lance; print(lance.__version__)"` must show 4.0.0+.

**Risk:** None. pylance 4.0 is backward-compatible for reads. Existing datasets
remain readable. The only behavioral change is *new* writes can now use format 2.2.

## Current State (Baseline)

```
io_adapters/lance_sink.py:
  - write_dataset(table, str(path), mode="append")  # no format, no options
  - No compact_files, no cleanup_old_versions
  - No storage_options

scripts/verify_run1_contracts.py:
  - LanceDataset(str(path)) for reads
  - to_table(columns=[...]) for scans
  - count_rows() for counts

pyproject.toml:
  - pylance>=4.0.0 (declared but 3.0.1 actually installed -- must upgrade)
```

## Target Architecture

```mermaid
flowchart TD
  orchestrator[Orchestrator] -->|enqueue| sink[LanceSink Worker]

  subgraph LanceSink
    sink -->|"write_dataset(..., data_storage_version='2.2')"| lance_ds[Lance Dataset v2.2]
    sink -->|"every 5 min"| compact[compact_files bounded=32]
    sink -->|"auto_cleanup hook"| cleanup[cleanup_old_versions num=2]
  end

  lance_ds --> disk[Local Filesystem]
  compact --> disk
  cleanup --> disk

  verify[verify_run1_contracts.py] -->|"LanceDataset(path)"| lance_ds
```

## What Changes

### WP1: Format 2.2 Write Path

**File:** `io_adapters/lance_sink.py` -- `_append_batch()`

Current:
```python
write_dataset(table, str(path), mode=mode)
```

Target:
```python
write_dataset(
    table,
    str(path),
    mode=mode,
    data_storage_version="2.2",
)
```

**Why format 2.2:**
- ~50% smaller storage via LZ4 dictionary compression (default in 2.2).
- Complex all-null compression (candle fields like `correction_version` that are null 99% of the time).
- 300% faster full-scan reads via parallel structural-decode batches.
- Shortcut for full-page reads (our primary read pattern: scan all rows for a time range).
- No behavioral change -- same Arrow schema, same append semantics.

### WP2: Auto-Cleanup (Zero-Cron Version Pruning)

**File:** `io_adapters/lance_sink.py` -- `_append_batch()`

After each successful `write_dataset`, call:
```python
import lance
from datetime import timedelta

ds = lance.dataset(str(path))
ds.cleanup_old_versions(
    older_than=timedelta(seconds=0),
    num_versions=2,
)
```

**Why `num_versions=2`:**
- `1` is risky: a concurrent read during cleanup could hit a half-deleted version.
- `2` keeps current + previous -- minimal overhead (~1 extra manifest, typically <1 KB).
- Still eliminates unbounded version accumulation.

**Frequency:** Every commit (piggyback on `_append_batch`). Cleanup is cheap (~1ms metadata scan) when there are only 2-3 versions.

**Alternative (if cleanup per-commit is measurably slow):**
Use the built-in auto-cleanup hook:
```python
write_dataset(
    table,
    str(path),
    mode=mode,
    data_storage_version="2.2",
    storage_options={
        "lance.auto_cleanup.interval": "5",
        "lance.auto_cleanup.older_than": "0s",
    },
)
```
This triggers cleanup every 5 commits automatically inside Lance's commit path.

### WP3: Periodic Bounded Compaction

**File:** `io_adapters/lance_sink.py` -- new method + `_worker()` integration

```python
def _maybe_compact(self) -> None:
    now = time.monotonic()
    if now - self._last_compact < 300:  # 5 minutes
        return
    self._last_compact = now
    for interval_dir in self._root_path.iterdir():
        if not interval_dir.is_dir():
            continue
        try:
            ds = lance.dataset(str(interval_dir))
            ds.compact_files(
                target_rows_per_fragment=1_048_576,
                max_bytes_per_file=256 * 1024 * 1024,
            )
        except Exception as exc:
            logger.warning("LANCE COMPACT | interval=%s error=%s", interval_dir.name, exc)
```

**Why 5 minutes, not per-commit:**
- Compaction rewrites data files -- expensive compared to cleanup.
- 5-minute cadence at 700+ symbols means ~3500 appends between compactions.
- Bounded `max_bytes_per_file` prevents creating giant files that slow future appends.
- `target_rows_per_fragment=1M` matches Lance's sweet spot for columnar scan efficiency.

**Integration:** Called at the end of `_worker()` main loop iteration, after append.

### WP4: Migration Script

**File:** `scripts/migrate_lance_to_v2_2.py` (new, one-shot)

```python
"""One-shot migration: rewrite existing Lance datasets to format 2.2."""
import lance
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/lance/candles")

for interval_dir in sorted(root.iterdir()):
    if not interval_dir.is_dir():
        continue
    ds = lance.dataset(str(interval_dir))
    old_count = ds.count_rows()
    # Compact rewrites all fragments in new format
    ds.compact_files(target_rows_per_fragment=1_048_576)
    ds.cleanup_old_versions(older_than=timedelta(seconds=0), num_versions=1)
    new_count = ds.count_rows()
    assert old_count == new_count, f"Row count mismatch: {old_count} vs {new_count}"
    print(f"Migrated {interval_dir.name}: {old_count} rows")
```

**Safety:** Row count assertion before/after. Run manually, not automated.

### WP5: Benchmark

Measure on a real 1-hour dataset (60 minutes x 700+ symbols = ~42,000 rows):

| Metric | Before (legacy) | After (2.2 + compact) | Target |
|--------|-----------------|----------------------|--------|
| Storage size (MB) | measure | measure | <50% of before |
| Fragment count | measure | measure | <10 per interval |
| Full scan time (ms) | measure | measure | <50% of before |
| Append latency p99 (ms) | measure | measure | <10ms |
| Memory RSS (MB) | measure | measure | no increase |

Promotion rule for each tuning candidate:
- Must pass all no-downgrade guardrails.
- Must show either storage reduction or operational simplification.
- If trade-off exists, storage gain must be significant enough to justify it and explicitly approved.

### WP6: Optional No-Downgrade Fine-Tuning (A/B Gated)

These are **optional** optimizations applied only after WP1-WP5 is stable. Each item is feature-flagged and benchmarked before promotion.

1. **Schema trimming (no behavior change):**
   - Remove physically redundant columns where derivable from path/context (example: `interval` if one dataset per interval).
   - Keep logical compatibility via read adapters if needed.
   - Expected impact: less disk + less decode bandwidth.

2. **Batching tuning on append path:**
   - Increase effective append batch size (for example 256 -> 1024/2048) to reduce tiny fragment churn before compaction.
   - Bound queue/flush latency to avoid backpressure side-effects.
   - Expected impact: fewer fragments, less metadata overhead, better compaction efficiency.

3. **Deterministic pre-sort before write:**
   - Stable sort within batch by `(symbol_id, minute_ms)` (or equivalent monotonic keys).
   - Expected impact: better local value locality for dictionary/RLE decisions, possible better compression.

4. **Field-level encoding trials (opt-in, conservative):**
   - Evaluate field metadata for selected columns:
     - `lance-encoding:compression` (`lz4` or `zstd`),
     - `lance-encoding:dict-values-compression`,
     - optional BSS-assisted paths where appropriate.
   - Default stays conservative unless A/B proves no-downgrade.

5. **Read-path memory hardening for verification tools:**
   - Prefer `to_batches()` for very large scans in verification scripts to avoid full materialization spikes.
   - Expected impact: reduced peak RSS and smoother overnight validation.

WP6 acceptance:
- At least one candidate promoted with measurable benefit.
- No candidate introduced correctness, latency, CPU, or memory regressions beyond guardrails.

### WP7: OHLCV-Specific Column Encoding (A/B Gated)

Concrete encoding recommendations for our exact schema, based on the data
distribution of financial time-series candle data. Each applied only if A/B
benchmark confirms no-downgrade.

| Column | Data profile | Recommended encoding | Expected gain |
|--------|-------------|---------------------|---------------|
| `symbol` | string, ~500-700 unique values, repeated every minute | Dictionary (default in 2.2). Trial `zstd` for dict-values via `lance-encoding:dict-values-compression=zstd` | 10-15% smaller than LZ4 dict |
| `minute_ms` | int64, monotonically increasing, delta=60000 between rows when sorted | Delta encoding benefits massively from pre-sorted input (WP6.3). Lance 2.2 auto-detects monotonic runs. | Up to 90% smaller for sorted data |
| `open/high/low/close` | float64, low variance within symbol, high correlation between adjacent candles | Byte-Stream-Split (BSS) via `lance-encoding:bss=true`. BSS transposes float bytes so mantissa bytes cluster, yielding much better LZ4/zstd ratios. | 20-40% smaller for correlated floats |
| `volume` | float64, high variance, no clear pattern | Standard LZ4 block compression (default). BSS is unlikely to help. | Baseline -- no change needed |
| `emitted_at_ms` | int64, monotonic within ingest order | Same as `minute_ms` -- delta encoding via sorted input. | Up to 90% smaller |
| Sparse/nullable columns (`correction_version` etc.) | >99% null | All-null compression (automatic in 2.2). | Near-zero storage |

**How to apply column-level encoding in Lance 2.2:**

```python
import pyarrow as pa

schema = pa.schema([
    pa.field("symbol", pa.utf8()),
    pa.field("minute_ms", pa.int64()),
    pa.field("open", pa.float64(), metadata={
        b"lance-encoding:bss": b"true",
    }),
    pa.field("high", pa.float64(), metadata={
        b"lance-encoding:bss": b"true",
    }),
    pa.field("low", pa.float64(), metadata={
        b"lance-encoding:bss": b"true",
    }),
    pa.field("close", pa.float64(), metadata={
        b"lance-encoding:bss": b"true",
    }),
    pa.field("volume", pa.float64()),
    # ... other fields
])
```

BSS is a no-downgrade optimization: it changes physical encoding only, not
logical values. Reads return identical float64 values. If A/B shows no storage
improvement (possible for very low-cardinality symbols), we skip it.

**Dependency:** WP6.3 (deterministic pre-sort) should be applied first, as
sorted input is a prerequisite for delta encoding benefits on `minute_ms`.

### WP8: Lance Format 2.3 Evaluation (Future)

Lance format 2.3 was introduced in March 2026 (PR #6088: "mark 2.2 as stable
and add 2.3 as next file format version").

**Current status:** 2.3 is the "next" version. 2.2 is marked "stable".

**What 2.3 may bring:**
- Adaptive encoding selection: automatic column-level encoding tuning based on
  data sampling at write time (could supersede manual BSS/zstd tuning in WP7).
- Potential further compression improvements for nested types.

**Action plan:**
1. Do NOT use 2.3 now -- it is not yet marked stable.
2. Track upstream: watch `lance-format/lance` releases for "2.3 stable" announcement.
3. When stable: run A/B benchmark (2.2 vs 2.3) on a real 1-hour dataset.
4. Promote to 2.3 only if all no-downgrade guardrails pass.

**Why wait:** Format version downgrades are not possible -- once a dataset is
written in 2.3, older pylance versions cannot read it. We need the format to be
stable and well-tested upstream before adopting.

## What Does NOT Change

- **Native data-plane**: zero Lance calls in C++ hot path. Lance is purely IO-adapter (control-plane Python).
- **Schema**: same Arrow schema (`symbol`, `interval`, `minute_ms`, `open`, `high`, `low`, `close`, `volume`, `emitted_at_ms`, ...).
- **API surface**: `LanceSink.enqueue()`, `LanceSink.start()`, `LanceSink.stop()` unchanged.
- **Read path**: `LanceDataset(path)` in verify scripts works identically with format 2.2 (backward-compatible reads).
- **Sync/Healing plan**: Lance remains a "materialized view" derived from the event log. This upgrade makes that view cheaper and faster.

## CPU Impact Assessment

Current farmer CPU at 7-10% for 700+ symbols with 4 timeframes. Lance append is already offloaded to `asyncio.to_thread` (thread pool, not event loop). Adding:

- **Cleanup** (~1ms metadata): negligible -- <0.01% CPU added.
- **Compact** (every 5 min, bounded): ~100-500ms burst every 5 min = <0.2% average CPU.
- **Format 2.2 encoding**: LZ4 dict compression is ~5-10% faster than legacy encoding due to smaller buffers.

**Conclusion:** CPU stays at 7-10%. No measurable regression.

## Storage Efficiency Analysis

For our workload (append-only OHLCV candles, 700+ symbols, 4 intervals):

### Without upgrade (current):
- ~42,000 rows/hour
- Each `write_dataset` append: 1 new fragment + 1 new manifest version
- After 24h: ~1,008,000 rows across potentially thousands of tiny fragments
- Version manifests accumulate: ~60 versions/hour × 24h = 1,440 manifests per interval

### With upgrade (format 2.2 + auto-cleanup + periodic compact):
- Same row volume
- Fragments: merged to <10 per interval (1M rows per fragment target)
- Versions: max 2 at any time (auto-cleanup)
- Compression: ~50% reduction in data file size (LZ4 dict + all-null)
- Net: **>80% reduction in storage overhead** (manifests + fragments + compression)

## Lance 4.0 Features We Use

| Feature | How we use it | Impact |
|---------|--------------|--------|
| Format 2.2 (`data_storage_version="2.2"`) | All new writes | ~50% smaller files |
| LZ4 dict compression (default in 2.2) | Automatic | Better compression for repetitive symbol strings |
| All-null compression (2.2) | Automatic | Near-zero cost for sparse columns |
| `cleanup_old_versions(num_versions=N)` | After each append | Zero version bloat |
| `compact_files()` with bounded fragments | Every 5 min | <10 fragments per interval |
| Rate-limited cleanup (`RemovalStats`) | Implicit | No IO burst during live ingest |
| `defer_index_remap` | N/A (no indices) | Not needed for our workload |

## Lance 4.0 Features We Do NOT Need

| Feature | Why not |
|---------|---------|
| Vector indices (IVF_PQ, HNSW) | We do equality/range scans, not similarity search |
| Full-text search | Not applicable to numeric candle data |
| Blob V2 storage | No binary blobs in candle schema |
| Multi-base layout | Single local filesystem, not multi-bucket |
| Namespace manifest | Single dataset per interval, not multi-table |
| Scalar indices (BTree) | Scans are faster than index lookups for our row counts |

## Migration Sequence

0. **Upgrade pylance**: `pip install pylance==4.0.0` -- blocker for everything else.
1. **Update `lance_sink.py`**: add `data_storage_version="2.2"` to `write_dataset` call.
2. **Add cleanup**: `cleanup_old_versions(num_versions=2)` after each append.
3. **Add periodic compact**: `_maybe_compact()` in worker loop.
4. **Test**: 1-hour run, verify storage size, fragment count, scan speed.
5. **Migrate existing**: run `migrate_lance_to_v2_2.py` on existing datasets.
6. **Overnight**: verify 8-hour run with stable storage and zero fragment explosion.
7. **Column encoding**: A/B test BSS for price floats, zstd for symbol dict-values (WP7).
8. **Pre-sort**: enable deterministic sort by `(symbol, minute_ms)` before write (WP6.3 + WP7).
9. **Format 2.3**: evaluate when upstream marks it stable (WP8).

## Already Implemented: CPU Spike Elimination (2026-04-10)

The following optimizations were implemented outside this plan's WP sequence to
eliminate severe CPU spikes (50%+ proc_cpu) caused by Lance compaction during
live ingestion.  They supersede the simpler WP2/WP3 designs above.

### What was wrong

Original `_append_batch` wrote one fragment per `_worker` drain cycle (every
queue drain).  With 700 symbols across 4 intervals, this created ~180
fragments/hour for Min1 alone.  Compaction then had to merge hundreds of tiny
files, causing massive CPU bursts on the single-threaded event loop.

### Fixes applied (all in `io_adapters/lance_sink.py`)

1. **Timer-batched writes** (`_LANCE_FLUSH_INTERVAL_SEC = 60s`,
   `_LANCE_FLUSH_MAX_BUFFER = 5000`):  Worker accumulates records in a buffer
   and writes one fragment per interval per 60-second flush, reducing fragment
   creation rate by ~3x.  Backpressure cap triggers early flush if buffer
   exceeds 5000 records.

2. **Decoupled maintenance loop** (`_LANCE_MAINTENANCE_INTERVAL_SEC = 900s`):
   Compaction and version cleanup run in a dedicated background task via
   `asyncio.to_thread`, completely off the append hot path.  Never blocks
   ingestion.

3. **`force_binary_copy` compaction mode**:  Eliminates CPU-intensive
   decode/re-encode during compaction.  Since our schema is stable append-only,
   binary copy is safe and reduces compaction CPU from ~50% spike to <5% over
   baseline.

4. **Pressure-gated compaction** (`_LANCE_COMPACT_PRESSURE_CEILING = 0.30`):
   Compaction is skipped when system pressure exceeds 30%, preventing compaction
   from competing with ingestion during high load.

5. **Single-threaded compaction** (`num_threads=1`, `batch_size=8192`):
   Prevents compaction from saturating CPU cores.

6. **Explicit handle release** (`del ds` after every `lance.dataset` operation):
   Prevents Lance dataset handles from retaining Arrow buffers beyond their
   maintenance window.

### Result

- CPU spikes from compaction: **eliminated** (50%+ down to undetectable)
- Fragment creation rate: ~60/h for Min1 (was ~180/h)
- Remaining ~18% avg proc_cpu is pure ingestion baseline, not Lance

### Relationship to plan WPs

- **WP2 (auto-cleanup)**: superseded by the decoupled maintenance loop which
  calls `cleanup_old_versions` on a 15-minute cadence instead of per-commit.
- **WP3 (periodic compact)**: superseded by the maintenance loop with
  `force_binary_copy`, pressure-gating, and single-threaded execution.
- **WP1, WP4-WP8**: unaffected, still pending per original plan.

See devlogs:
- `docs/devlogs/2026-04-10_lance_maintenance_decoupling_jemalloc.md`
- `docs/devlogs/2026-04-10_lance_timer_batched_writes_force_binary_copy.md`

## Acceptance Criteria

- Zero data loss: row counts match before and after migration.
- Storage size <50% of legacy format for equivalent data volume.
- Fragment count <10 per interval after compaction.
- Version count <=2 at any point in time.
- Append latency p99 <10ms (no regression from current).
- CPU usage remains at 7-10% for 700+ symbols.
- `verify_run1_contracts.py` passes unchanged (backward-compatible reads).
- No manual compaction cron needed -- LanceSink is fully self-managing.
- No promoted optimization violates no-downgrade guardrails.

## Relevant References

- [Lance 4.0 Release Notes](https://github.com/lance-format/lance/releases/tag/v4.0.0)
- [Lance Format 2.2 Benchmarks: Half the Storage](https://www.lancedb.com/blog/lance-format-v2-2-benchmarks-half-the-storage-none-of-the-slowdown)
- [Lance Format 2.2: Taming Complex Data](https://lancedb.com/blog/lance-file-format-2-2-taming-complex-data)
- [Lance Format Encoding Specification](https://lance.org/format/file/encoding/)
- [Lance auto_cleanup PR](https://github.com/lancedb/lance/pull/3572)
- [Lance num_versions retention PR](https://github.com/lancedb/lance/pull/4614)
- [Lance format 2.3 introduction PR #6088](https://github.com/lance-format/lance/pull/6088)
- [Byte-Stream Split in columnar formats](https://parquet.apache.org/docs/file-format/data-pages/encodings/#byte-stream-split-byte_stream_split--9)
- [Current LanceSink](io_adapters/lance_sink.py)
- [Current verify script](scripts/verify_run1_contracts.py)
- [V3 Sync/Healing Architecture](docs/plans/v3-sync-healing-architecture_99c7e0c2.plan.md)
