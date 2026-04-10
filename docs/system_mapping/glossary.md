# Glossary

- **Branch map**: subsystem-level architecture page defining mission, boundaries, invariants, and operations.
- **Contract**: interface agreement between producer and consumer branches.
- **Event-time**: timestamp from exchange payload used as primary aggregation timeline.
- **Ingest-time**: local receive timestamp used for audit/diagnostics fallback.
- **Finalize window**: time interval in which late events can still affect interval close.
- **Mismatch event**: record emitted when local aggregate differs from authoritative snapshot decision.
- **Pressure**: runtime resource stress signal (CPU/RAM/queue/write lag).
- **Action ladder**: ordered degradation actions under pressure.
- **SLO**: service-level objective with measurable target.
- **Architecture baseline**: the binding architecture rules in `docs/ARCHITECTURE.md`.
