# MVP Build Sequence from Handover

## Why this sequence

The handover already contains resilience, semantics, and aggregation principles.
So the fastest path is not a greenfield redesign, but a controlled extraction into a minimal vertical slice.

## Decisions now

- Start with hardcoded symbols in config for MVP.
- Do not start with 700 symbols.
- Implement dynamic timeframe registry early, but keep identical aggregation semantics across intervals.

## Recommended MVP scope

- symbols: 3 to 10 (start with 3)
- channels: deal + kline first, then depth/ticker/funding/index/fair
- intervals: Min1 first, then Min5/Min15/Min60 using same aggregate contract

## Phase plan

### Phase 1 - Stable ingest and one interval

- hardcode 3 symbols
- run deal + kline
- produce Min1 features to Lance
- verify no duplicate minute close invariant

Exit criteria:
- 6h run, no crash
- bounded queues respected
- write lag within initial target

### Phase 2 - Governance hardening

- enforce CPU/RAM budgets
- finalize pressure action ladder
- add deployment thresholds for SLO seeds

Exit criteria:
- controlled degradation under synthetic burst
- no unbounded memory growth

### Phase 3 - Scale envelope tests

- increase symbol count in steps (10 -> 25 -> 50)
- validate lag/drop/write p95 curves
- determine sustainable symbol budget per host profile

Exit criteria:
- capacity envelope documented
- clear trigger for horizontal scale or symbol cap

## Answers to current strategic questions

- Dynamic timeframes: yes, implement now as registry; keep same semantics for all windows in MVP.
- Symbol ID system: keep minimal and deterministic (`symbol` + optional stable integer mapping). Full catalog service is not MVP-critical.
- Hardcoded symbols for start: yes, correct for MVP.
- 700 symbols now: too aggressive for MVP and will hide correctness issues behind throughput noise.
