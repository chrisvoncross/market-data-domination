# Contract: Runtime Governance Signals

## Parties

- Producer: `BR-GOV`
- Consumers: operations, alerting, tuning workflows

## Required metrics

- `process_cpu_quota_pct`
- `rss_limit_ratio`
- `queue_pressure`
- `write_lag_ms`
- dropped counters by boundary

## Action ladder

1. warn
2. throttle/finalize sleep increase
3. compaction skip under pressure
4. bounded drop on full queue

## Evidence requirements

Every action state change must be logged with:
- trigger metric
- threshold
- action taken
- timestamp

## Versioning

- contract_version: `v1`
