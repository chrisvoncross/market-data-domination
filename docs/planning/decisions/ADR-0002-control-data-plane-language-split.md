# ADR-0002: Control Plane / Data Plane Split and Language Strategy

## Status

Accepted (initial)

## Context

The project needs high iteration speed and predictable hot-path performance.

A single-language strategy is attractive for simplicity but may degrade either:
- control-plane productivity, or
- data-plane latency determinism.

## Decision

Use a split architecture:

- Control plane:
  - orchestration, config, policy, governance, and operator APIs
  - language can be Python and/or Go depending on team velocity and infra needs
- Data plane:
  - market data ingest loops, normalization hot path, write path
  - optimized runtime (native or heavily optimized managed runtime)

This is a principle-level decision; concrete language selection is a later ADR.

## Rationale

- Public high-scale guidance consistently separates control and data planes for resilience.
- Public finance engineering material emphasizes deterministic async and low-latency constraints in critical paths.
- Polyglot is common in large systems and avoids forcing one language across conflicting requirements.

## Consequences

Positive:
- better hot-path performance options
- better operational resilience (static stability patterns)
- team can evolve each plane independently

Negative:
- additional interface contracts and build complexity
- requires strict API/schema governance between planes

## Alternatives considered

- 100% Python for all paths (rejected for hot-path determinism risk)
- 100% native for all paths (rejected for control-plane development velocity cost)

## References

- <https://docs.aws.amazon.com/wellarchitected/latest/reducing-scope-of-impact-with-cell-based-architecture/control-plane-and-data-plane.html>
- <https://aws.amazon.com/builders-library/static-stability-using-availability-zones/>
- <https://www.citadelsecurities.com/careers/career-perspectives/technical-spotlight-async-programming-with-sender-receiver/>
- <https://engineering.blackrock.com/the-blackrock-messaging-system-aeae461e4211>
