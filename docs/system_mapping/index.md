# System Map Index (Yellow Pages)

## Purpose

Fast lookup for all critical system branches.

Companion entry points:
- root onboarding: `START-HERE.md`
- terminology: `docs/system_mapping/glossary.md`

## Branch registry

| branch_id | branch_name | mission | primary docs | owner | status |
|---|---|---|---|---|---|
| BR-INGEST-MEXC | MEXC Ingestion | Ingest and validate market stream events | `branches/ingestion-mexc.md` | TODO | active |
| BR-NET-RES | Network Resilience | Keep stream alive under network/exchange faults | `branches/network-resilience.md` | TODO | active |
| BR-AGG | Aggregation Engine | Build interval candles/features with deterministic semantics | `branches/aggregation.md` | TODO | active |
| BR-LANCE | Lance Storage | Durable append storage for raw and features | `branches/storage-lance.md` | TODO | active |
| BR-GOV | Runtime Governance | Bound CPU/RAM impact and enforce safe degradation | `branches/governance.md` | TODO | active |

## C4-level pointers

- L1 System Context: `docs/planning/architecture/` (to be expanded)
- L2 Container View: each branch map "Container Boundaries" section
- L3 Component View: each branch map "Core Components" section

## Map health checklist

- [ ] Each branch has current owner
- [ ] Each branch has SLOs
- [ ] Each branch has failure matrix
- [ ] Interfaces are linked in `contracts/`
- [ ] Last verification date <= 30 days
