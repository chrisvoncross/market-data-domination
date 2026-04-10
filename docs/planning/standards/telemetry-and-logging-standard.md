# Telemetry and Logging Standard (MVP)

## Goals

- keep telemetry overhead bounded
- preserve fast incident debugging
- align with public SRE/OTel guidance

## Rules

1. Structured logs only (JSON).
2. Include trace correlation IDs where available.
3. No unbounded metric labels (for example request IDs, user IDs, wallet IDs).
4. Sample traces by default; keep error and high-latency traces.
5. Keep metric set minimal and SLO-driven.
6. Enforce retention tiers by data class.

## Logging levels

- prod default: `INFO`
- elevated debug windows: time-boxed only
- noisy subsystems must provide independent level controls

## Minimum metrics

- ingest events/sec
- ingest lag seconds
- queue depth
- dropped events total
- Lance write latency seconds
- process RSS bytes
- process CPU seconds total
- PSI memory and CPU pressure (some/full where available)

## References

- <https://opentelemetry.io/docs/specs/otel/logs/data-model/>
- <https://www.w3.org/TR/trace-context/>
- <https://prometheus.io/docs/practices/naming/>
- <https://sre.google/sre-book/monitoring-distributed-systems/>
- <https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-observability.html>
