# START HERE - Market Data Domination

## 5-minute onboarding

1. Read `docs/system_mapping/index.md` for the subsystem registry.
2. Open branch maps in `docs/system_mapping/branches/`.
3. Confirm interface expectations in `docs/system_mapping/contracts/`.
4. Follow update process in `docs/system_mapping/sop/SOP-system-map-maintenance.md`.
5. Review current MVP execution sequence in `docs/planning/mvp/mvp-build-sequence-from-handover.md`.

## If you are a new agent

- Start with `BR-INGEST-MEXC`, `BR-AGG`, and `BR-GOV`.
- Never change architecture-significant behavior without updating:
  - branch map
  - contract
  - ADR reference

## Current MVP defaults

- symbols: start with `BTC_USDT`, `ETH_USDT`, `SOL_USDT`
- intervals: `Min1` first, then `Min5/Min15/Min60`
- write mode: append-only
- queues: bounded; drop-on-full policy at boundaries

## Glossary

- canonical glossary: `docs/system_mapping/glossary.md`

## Source of truth priority

1. runtime code behavior
2. contracts in `docs/system_mapping/contracts/`
3. subsystem maps in `docs/system_mapping/branches/`
4. planning docs and handover notes
