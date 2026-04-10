# SOP - System Map Maintenance

## Purpose

Keep system maps accurate, queryable, and consistent for all agents and contributors.

## Trigger conditions (update required)

Update maps when any of these happen:

1. New feature changes behavior in any branch.
2. Interface/schema/queue semantics change.
3. SLO, budget, threshold, or action ladder changes.
4. New failure mode discovered in test or production.
5. `docs/ARCHITECTURE.md` binding rules are changed/superseded.

## Mandatory update steps

1. Update the affected branch file in `branches/`.
2. Update related contract in `contracts/` (if interface changed).
3. Update `index.md` if branch status/scope changed.
4. Update `docs/ARCHITECTURE.md` if binding architecture rules changed.
5. Add dated entry in branch "Change log".

## Quality gate checklist (must pass)

- [ ] Clear mission/scope present
- [ ] Inputs/outputs and required fields listed
- [ ] Invariants listed and still valid
- [ ] Failure behavior and recovery updated
- [ ] Metrics and SLO references current
- [ ] Last verified date and method updated

## Review cadence

- Weekly: quick accuracy pass for active branches
- Monthly: full map audit (owners + platform reviewer)
- Release gate: no release if map-critical changes are undocumented

## Ownership model

- Branch owner updates branch docs.
- Interface owner updates contract docs.
- Reviewer confirms consistency across branch/contract/architecture baseline.

## Architecture baseline alignment rule

- If decision changes binding rationale/constraints, update `docs/ARCHITECTURE.md`.
- Keep change rationale concise in PR and in affected branch/contract docs.

## Incident feedback loop

After each sev incident:

1. capture new failure mode
2. patch branch map and contract if needed
3. update thresholds/SLO notes
4. update `docs/ARCHITECTURE.md` if the incident changes binding architecture rules

## Docs-as-code enforcement recommendations

- keep docs in same VCS as code
- require PR review for map changes
- use markdown lint + link check in CI
- block merge for architecture-affecting changes without map updates
