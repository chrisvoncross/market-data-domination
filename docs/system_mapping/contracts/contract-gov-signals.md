# Contract: Runtime Governance Signals

## Parties

- Producer: `BR-GOV`
- Consumers: operations, alerting, tuning workflows

## Required metrics

- `cpu_pct`
- `rss_kb`
- `queue_depth`
- `write_lag_ms`
- dropped counters by boundary (`drops_total`, per-slot queue drops)
- PSI signals (`cpu_some_avg10`, `memory_some_avg10`, `io_some_avg10`)
- incident rollup (`incident_count`, incident artifacts path)
- spike rollup (`spike_count`, spikes artifact path)
- stage transition rollup (`stage_transition_count`, stage transition artifact path)
- distribution stats (`cpu_p95/p99`, `rss_p95/p99`, `queue_p95/p99`)

## Action ladder

1. warn
2. throttle/finalize sleep increase
3. compaction skip under pressure
4. bounded drop on full queue

## Evidence requirements

Every pressure incident must be logged with:
- trigger metric
- threshold
- action taken
- timestamp

Minimum incident row fields:
- `incident_id`
- `trigger_time`
- `trigger_kind`
- `psi_cpu_some`, `psi_mem_some`, `psi_io_some`
- `rss_kb`, `cpu_pct`, `queue_depth`, `write_lag_ms`
- `top_stage`, `action_taken`, `confidence`, `context_json`

Minimum spike row fields:
- `ts`
- `kind` (`cpu_spike`, `queue_spike`, `rss_step_spike`)
- `value`
- `stage`

Minimum stage transition row fields:
- `ts`
- `kind` (`stage_transition`)
- `from_stage`
- `to_stage`
- `elapsed_sec`

## Versioning

- contract_version: `v2`
