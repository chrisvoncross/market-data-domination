# ADR-0001: Governance Baseline for Low-Hardware Operation

## Status

Accepted (initial)

## Context

The project requires:

- strict CPU/RAM efficiency,
- strong observability for bottleneck attribution,
- safe degradation under pressure.

## Decision

Adopt the following baseline:

1. cgroup v2 resource envelopes for runtime hard/soft limits
2. PSI-triggered pressure governance and escalation actions
3. OTel-based logs/metrics/traces with strict cardinality controls
4. always-on sampling profiler on canary, then staged rollout
5. SLO burn-rate alerting for operator paging

## Rationale

- Kernel-level pressure signals provide better protection than utilization-only dashboards.
- Sampling profiling offers meaningful attribution with manageable overhead.
- SLO burn-rate alerts reduce noise compared to threshold-only paging.

## Consequences

Positive:
- lower failure blast radius under overload
- measurable and tunable observability cost
- faster root-cause cycles

Negative:
- added platform complexity compared to ad-hoc scripts
- requires disciplined telemetry label governance

## Alternatives considered

- utilization-only monitoring without PSI (rejected: misses stall behavior)
- logs-only debugging without profiler (rejected: insufficient attribution depth)
- full-fidelity tracing/logging everywhere (rejected: overhead and cost)

## References

- <https://docs.kernel.org/accounting/psi.html>
- <https://facebookmicrosites.github.io/cgroup2/docs/pressure-metrics.html>
- <https://parca.dev/docs/faq/>
- <https://grafana.com/blog/continuous-profiling-in-production-a-real-world-example-to-measure-benefits-and-costs/>
- <https://sre.google/workbook/alerting-on-slos/>
- <https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-observability.html>
