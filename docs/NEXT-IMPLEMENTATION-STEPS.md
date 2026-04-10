# Next Implementation Steps

This is the only operational checklist new agents should execute first.

## Step 1 - Ingest minimal vertical slice

- Implement/verify `push.deal` + `push.kline` ingest path.
- Symbols: `BTC_USDT`, `ETH_USDT`, `SOL_USDT`.
- Ensure bounded ingress queues and reconnect/heartbeat behavior.

Done when:
- stream runs stable,
- no crashes,
- queue bounds enforced.

## Step 2 - Aggregate and emit direct-TF candles

- Implement/verify direct kline finalize for all configured intervals (`Min1`, `Min5`, `Min15`, `Min60`, ...).
- Keep one unified timeframe handler (no TF-specific hot path branches).
- Enforce no duplicate close for `(symbol, interval, minute_ms)`.
- Emit mismatch evidence when Min1 local reconstruction diverges from direct exchange kline.

Done when:
- replay file passes,
- duplicate-close invariant holds.

## Step 3 - Write to Lance

- Append raw + feature rows to Lance.
- Keep write path micro-batched and bounded.
- Expose write lag and write error counters.

Done when:
- writes succeed under normal load,
- write lag is observable.

## Step 4 - Governance baseline

- Emit: queue pressure, process CPU quota %, RSS ratio, write lag.
- Apply action ladder under pressure:
  - warn -> throttle -> skip compact -> drop on full queue.

Done when:
- degradation is controlled,
- no unbounded memory growth.

## Step 5 - Soak gate

- Run 6h soak test.
- Track drops, lag, CPU/RAM pressure behavior.

Gate:
- no crash,
- no deadlock,
- no unbounded queues.
