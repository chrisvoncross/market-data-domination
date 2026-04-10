# Farmer Failure Cases

| name | trigger | expected behavior | metric/alert impacted | recovery steps |
|---|---|---|---|---|
| WS connect timeout | MEXC endpoint unreachable or TCP stall | slot reconnect loop starts with exponential backoff (1s->10s) | reconnect_count, ingest_lag | keep retrying; verify DNS/egress/network ACL |
| Heartbeat timeout | pong not received within reply timeout | disconnect slot and reconnect | reconnect_count, channel throughput dip | auto reconnect; inspect RTT and provider health |
| Queue full at ingress frame queue | burst > per-slot queue capacity | drop event and increment dropped counters | drop_count, queue_pressure | reduce symbols/channels or increase capacity carefully |
| Queue full at raw sink | raw writer cannot drain quickly enough | drop enqueue attempt at sink boundary | raw_drop_rate, write_lag_ms | improve disk IO, lower event rate, tune batch sizing |
| Queue full at feature sink | finalize output exceeds write throughput | drop enqueue attempt at feature sink | feature_drop_rate, write_lag_ms | reduce scope, increase IO throughput, tune batching |
| Malformed payload | invalid JSON or unexpected structure | skip parse for that payload; continue loop | parse_error_count (TODO if metric added) | keep raw evidence where possible; add parser guards/tests |
| Duplicate deal across capture feeds | same deal arrives from feed0/feed1 | semantic dedupe by native path (TODO key details) | mismatch or duplicate_close risk | verify native dedupe keys; add replay test fixture |
| Out-of-order deal timestamps | older event arrives after newer in same minute | event-time minute bucketing + finalize policy handles order | late_event_count (TODO if metric added) | keep finalize window; validate no duplicate minute close |
| Missing exchange snapshot by finalize deadline | no qualifying snapshot before deadline | finalize with allow-missing policy; emit with decision kind | mismatch_detected | inspect upstream snapshot quality; preserve mismatch audit |
| Symbol routing removal while active | symbol removed from qualified set | ingress/native update symbols and prune caches safely | symbol_routing_updated, active_symbols | confirm cache prune + native remove_symbols works in soak |
| High pressure blocks compaction | pressure >= threshold | skip compaction, keep hot path responsive | pressure, compaction_skip_count | restore headroom then run maintenance later |
| CPU quota saturation | process_cpu_quota_pct above target | adaptive finalize sleep increases to reduce pressure | process_cpu_quota_pct, write_lag_ms | reduce symbol scope/channels, tune polling bounds |
| Memory limit pressure | rss_limit_ratio near limit | classify as rss_limit_pressure, adaptive sleep impact | rss_limit_ratio, pressure_cause | reduce caches/symbols, investigate allocator and leaks |
| Lance dataset unavailable/corrupt | write/read dataset operation fails | writer keeps loop alive; errors logged; continue attempts | write_error_rate, write_lag_ms | isolate bad dataset path, repair/recreate dataset directory |

TODOs that remain explicit (must not be guessed):
- Exact native dedupe key fields and tie-break ordering from C++ layer.
- Explicit dedicated gap-detector rule module (not present in current ingress Python layer).
- Final production SLO thresholds per deployment tier.
