# Planning Docs

This directory stores architecture, research, and execution planning artifacts for the market data farmer project.

The structure is inspired by public engineering practices from hyperscalers and high-scale finance platforms:
- clear split between research, architecture decisions, and execution plans
- ADR-first decision tracking
- runbook-oriented operations
- source-backed claims for non-trivial design choices

## Directory structure

- `research/`
  - external research notes, deep dives, and benchmark summaries
- `decisions/`
  - architecture decision records (ADRs)
- `architecture/`
  - target architecture, boundaries, interfaces, and contracts
- `mvp/`
  - scoped milestone plans with Definition of Done
- `runbooks/`
  - operational procedures (incident response, performance regressions, recovery)
- `standards/`
  - telemetry, logging, metric, and naming conventions

## Working model

1. Research and capture evidence in `research/`.
2. Write/refresh ADRs in `decisions/`.
3. Update design docs in `architecture/`.
4. Convert to executable slices in `mvp/`.
5. Add operational readiness in `runbooks/`.

## Document quality bar

- Every strong technical claim should cite a primary source URL.
- Every design decision should include trade-offs and rollback path.
- Every MVP milestone should include measurable acceptance criteria.
