# Farmer Principles Handover

## A) Ingestion/Resilience
- Exchange: MEXC
- WS base URL: `wss://contract.mexc.com/edge`
- Streams/channels used:
  - `push.deal`
  - `push.kline`
  - `push.depth.full`
  - `push.ticker`
  - `push.funding.rate`
  - `push.index.price`
  - `push.fair.price`
- Subscription methods used:
  - `sub.deal`
  - `sub.kline`
  - `sub.depth.full`
  - `sub.ticker`
  - `sub.funding.rate`
  - `sub.index.price`
  - `sub.fair.price`
- Reconnect strategy:
  - base backoff: `1000 ms`
  - max backoff: `10000 ms`
  - jitter: `none in current code` (`TODO` if required)
  - retries: `unbounded while running`
  - cooldown: `none explicit` (`TODO` if required)
- Heartbeat rules:
  - client ping payload: `{"method":"ping"}`
  - auto ping idle timeout: `15000 ms`
  - pong reply timeout: `10000 ms`
  - missed-heartbeat policy: disconnect and reconnect slot
- Gap detection rules:
  - explicit ingress gap detector: `not implemented as dedicated module` (`TODO`)
  - runtime protection currently via finalize/mismatch path and raw retention
  - resync strategy: reconnect + continue ingest; forensics via raw + mismatch
- Multi-IP/connection strategy:
  - resolve WS host A-records dynamically (`getaddrinfo`)
  - pin each connection slot to a resolved IPv4 (round-robin assignment)
  - no hardcoded IPs in code
  - load split by channel plan:
    - tier1 dedicated mixed slots (`BTC_USDT`, `ETH_USDT`, `SOL_USDT`) when enabled
    - separate deal slots
    - separate kline slots
    - optional aux slot
  - multi-feed duplication via `capture_feeds`

## B) Semantik/Ordering
- Event ordering:
  - parsing metadata from native boundary: `extract_frame_meta(payload)`
  - candle timeline uses `timestamp_ms`/minute buckets (event-time)
  - fallback for missing/invalid: receive time (`recv_ts_ms`) in deal aggregation path
- Dedupe rules:
  - dedupe is handled by native finalize/apply engine (`TODO`: exact key fields from native module docs)
- Event time vs ingest time:
  - event-time has priority for aggregation/finalization
  - ingest-time retained as audit (`recv_ts_ms`)
- Late/out-of-order policy:
  - pending finalization window with deadline (`due_mono`, `deadline_mono`)
  - finalize decision can allow missing snapshot after timeout
  - out-of-order/late behavior resolved in native `finalize_decision`
- Idempotenzregeln:
  - raw is append-only (idempotence not guaranteed in raw layer)
  - finalized candle emission guarded by `(symbol, interval, minute_ms)` + last emitted minute map
  - sink write mode is append, consumers should use semantic keys for dedupe if needed

## C) Aggregation
- Supported windows:
  - enabled intervals config-driven (`Min1` default)
  - supported registry default: `Min1, Min5, Min15, Min60`
- Aggregation logic:
  - `push.deal` contributes trade aggregates (buy/sell qty, amount, position/liquidation flags)
  - aux channels enrich depth/ticker/funding/index/fair caches
  - native due states provide core OHLCV/trade_count state rows
  - feature emission composes Gold row from native + aux caches + deal aggregates
- Watermark/close condition:
  - native `next_due_ms` drives due polling
  - pending final records wait until due; deadline allows missing snapshot policy
- Correction rules for late events:
  - native finalize may override local OHLCV from exchange snapshot compare
  - mismatch record emitted when decision indicates mismatch
- Final fields in Lance (Schema v1 in current implementation):
  - Gold row uses the agreed Gold39 field set
  - includes 39 numeric feature fields + nullable text/sentiment placeholders
  - includes audit/version fields (`schema_version`, `compute_version`, `capture_feed`, `recv_ts_ms`, `emitted_at_ms`, `symbol`, `interval`)

## D) Lance Storage
- Partitioning:
  - raw: per-channel dataset directory (`data/lance/raw/<channel_name_with_underscores>`)
  - features: per-interval dataset directory (`data/lance/features/<interval_lower>`)
- Write mode:
  - append-only
  - raw micro-batch target up to `2000` events / worker cycle
  - feature micro-batch target up to `5000` events / worker cycle
  - data storage version: `2.2`
- Upsert/append policy:
  - append only in both sinks
  - no upsert in current MVP code
- Retention/compaction ideas currently in code:
  - cleanup old versions (`older_than=10min`, retain last 2)
  - pressure-gated compaction
  - compaction mode: `force_binary_copy`
  - single-thread bounded compaction params

## E) Governance/SLO
- CPU/RAM budgets:
  - budget values are config/policy-level (`TODO` final target by deployment)
  - runtime metrics emitted:
    - `cpu_pct`
    - `process_cpu_pct`
    - `process_cpu_host_pct`
    - `process_cpu_quota_pct`
    - `cpu_quota_cores`
    - `rss_mb`
    - `memory_limit_mb`
    - `rss_limit_ratio`
    - queue pressure, write lag
- Hard thresholds + actions:
  - compaction allowed only when pressure < `pressure_compact_threshold` (default `0.30`)
  - adaptive finalize sleep increases when quota CPU or RSS pressure crosses configured targets
  - drop policy on queue full: drop newest enqueue attempt for sink/frame queues
- Key metrics:
  - lag: `write_lag_ms`
  - drops: ingress dropped counters + sink queue full behavior
  - queue depth/pressure: ingress + raw sink + feature sink backlog ratios
  - write latency: flush/compact elapsed logs
- SLO/alerts:
  - explicit thresholds are deployment policy (`TODO` set per environment)
  - recommended tracked p95s: `process_cpu_quota_pct`, `queue_pressure`, `write_lag_ms`

## F) Non-negotiable Invariants
1. Never process non-`push.*` frames as market events.
2. Never emit Gold rows without `symbol`, `interval`, `timestamp_ms`.
3. Never emit duplicate minute close for same `(symbol, interval, minute_ms)`.
4. Never block hot path on compaction/cleanup.
5. Never run without bounded queues for ingress/sinks.
6. Never silently mutate symbol-id mapping non-monotonically.
7. Never drop mismatch evidence once mismatch decision is produced.
8. Never write secrets/keys/IP inventories into handover docs/log payloads.
9. Never treat ingest-time as primary event-time for candle semantics.
10. Never disable runtime telemetry stream in production soak runs.
