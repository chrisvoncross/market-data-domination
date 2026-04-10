# CI Guardrails for System Maps

## Goal

Prevent architecture-relevant changes from merging without map and contract updates.

## Recommended checks

1. Markdown lint on `docs/system_mapping/**`.
2. Link check on `docs/system_mapping/**`.
3. PR checklist enforcement:
   - if architecture behavior changed, then:
     - branch map updated
     - contract updated (if interface changed)
     - ADR linked/updated

## Lightweight implementation hint

Use a CI step that checks changed files:

- if files under runtime/data-path change
- and no files changed under `docs/system_mapping/`
- then fail with message:
  - "Architecture-impacting change requires system map update."

## Human review rule

At least one reviewer confirms:
- map accuracy
- contract consistency
- SOP compliance
