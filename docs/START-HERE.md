# START HERE - Build First

This repo is implementation-first.

If you are a new agent, your default behavior is:
1. implement the next vertical slice,
2. run/verify,
3. update only the minimal mapping docs.

Do not create extra planning docs unless explicitly requested.

## Read only these files first

1. `docs/system_mapping/index.md`
2. `docs/system_mapping/branches/` (relevant subsystem only)
3. `docs/system_mapping/contracts/` (only affected interfaces)
4. `docs/planning/mvp/mvp-build-sequence-from-handover.md`
5. `docs/NEXT-IMPLEMENTATION-STEPS.md`

Ignore everything else unless blocked.

## Current MVP baseline

- symbols: `BTC_USDT`, `ETH_USDT`, `SOL_USDT`
- first channels: `push.deal`, `push.kline`
- first interval: `Min1`
- writes: append-only
- queues: bounded, drop-on-full at boundaries

## Documentation policy (strict)

- No new doc files by default.
- Update docs only when code changes architecture/contract behavior.
- Max doc changes per feature:
  - one branch map update,
  - one contract update (if interface changed).

## Definition of done for each task

1. code implemented,
2. behavior verified by run/test/replay,
3. mapping docs updated only if needed.
