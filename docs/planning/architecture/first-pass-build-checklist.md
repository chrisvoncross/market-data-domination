# First-pass Build Checklist

## Goal

Track implementation readiness for the first architecture pass.

## A) Control plane (Python)

- [ ] Config schema validation on startup
- [ ] Dynamic timeframe registry loaded from config
- [ ] Hardcoded symbol allowlist loaded from config
- [ ] Governance thresholds loaded as policy object
- [ ] Health/status endpoint exposes runtime state

## B) Data plane ingest (native/hot path)

- [ ] `push.deal` subscription and parse path operational
- [ ] `push.kline` subscription and parse path operational
- [ ] bounded ingress queues enforced
- [ ] reconnect + heartbeat behavior verified

## C) Data plane aggregation (native/hot path)

- [ ] `Min1` event-time aggregation operational
- [ ] finalize window/deadline behavior operational
- [ ] mismatch event emission operational
- [ ] duplicate close prevention verified

## D) Data plane writer (Lance)

- [ ] raw append pipeline operational
- [ ] feature append pipeline operational
- [ ] micro-batch write settings applied
- [ ] write lag metric emitted

## E) Governance

- [ ] queue pressure metric emitted
- [ ] CPU quota pressure metric emitted
- [ ] RSS pressure metric emitted
- [ ] action ladder (warn/throttle/skip-compact/drop) active

## F) Test and acceptance

- [ ] replay test passes with `farmer-sample-events.ndjson`
- [ ] no crash in 6h soak
- [ ] no unbounded memory growth
- [ ] no duplicate `(symbol, interval, minute_ms)` closes
- [ ] lag/drop/write metrics visible

## G) Explicitly deferred

- [ ] 700 symbols
- [ ] full symbol catalog service
- [ ] multi-exchange abstraction
- [ ] broad profiling matrix rollout
