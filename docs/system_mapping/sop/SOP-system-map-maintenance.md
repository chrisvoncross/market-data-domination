# SOP - System Map Maintenance

## Purpose

Keep system maps accurate, queryable, and consistent for all agents and contributors.

## Trigger conditions (update required)

Update maps when any of these happen:

1. New feature changes behavior in any branch.
2. Interface/schema/queue semantics change.
3. SLO, budget, threshold, or action ladder changes.
4. New failure mode discovered in test or production.
5. ADR supersedes an existing decision.

## Mandatory update steps

1. Update the affected branch file in `branches/`.
2. Update related contract in `contracts/` (if interface changed).
3. Update `index.md` if branch status/scope changed.
4. Add or update ADR reference in planning decisions.
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
- Reviewer confirms consistency across branch/contract/ADR.

## ADR alignment rule

- If decision changes rationale/constraints, create or supersede ADR.
- Never delete historical ADR context; link superseding records.

## Incident feedback loop

After each sev incident:

1. capture new failure mode
2. patch branch map and contract if needed
3. update thresholds/SLO notes
4. record follow-up ADR if design changed

## Docs-as-code enforcement recommendations

- keep docs in same VCS as code
- require PR review for map changes
- use markdown lint + link check in CI
- block merge for architecture-affecting changes without map updates
