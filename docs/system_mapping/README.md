# System Mapping

This directory is the project "yellow pages" for architecture and operations.
It is designed so any agent can quickly answer:

- what this subsystem does
- why it exists
- where it is implemented
- how it is operated
- which constraints and SLOs apply

## Mapping standards used

This mapping approach combines practical and formal standards:

- ISO/IEC/IEEE 42010 principles (stakeholders, concerns, views/viewpoints)
- C4 model hierarchy (context, containers, components)
- arc42 sectioning discipline for architecture communication
- ADR-driven decision history
- Docs-as-Code workflow

References:
- <https://c4model.com/>
- <https://arc42.org/overview>
- <https://adr.github.io/>
- <https://docs.cloud.google.com/architecture/architecture-decision-records>
- <https://www.writethedocs.org/guide/docs-as-code/>
- <https://aws.amazon.com/blogs/architecture/master-architecture-decision-records-adrs-best-practices-for-effective-decision-making/>

## Directory structure

- `index.md`
  - system map registry (entry point for agents)
- `branches/`
  - one map per subsystem branch
- `contracts/`
  - cross-branch interfaces and data contracts
- `sop/`
  - update and governance procedures
- `templates/`
  - required templates for branch maps and updates

## Rules

1. Every branch map must include owner, scope, inputs/outputs, invariants, metrics, and failure handling.
2. Every branch map must include `code locations` and `run commands` sections.
3. Every architecture-affecting change must update:
   - relevant branch map
   - related contract (if interface changed)
   - ADR reference if decision changed
4. No map update without "last verified date" and "verification method".
