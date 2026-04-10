# Picows Optimization Plan (MVP -> Hardening)

## Why

`picows` is the selected websocket runtime for the control-plane live ingress path.
The goal is to keep MVP minimal, then unlock additional built-in capabilities in measured steps.

## Current usage (implemented)

- `ws_connect`
- `WSListener` callbacks
- auto-ping/auto-pong
- text frame handling
- subscription writes through `WSTransport.send`

## Planned upgrades (post-MVP stabilization)

### Phase 1: Transport observability

- RTT sampling via `WSTransport.measure_roundtrip_time`
- per-slot connection state counters
- close/reconnect reason classification

### Phase 2: Resilience controls

- custom ping behavior tuning beyond default idle strategy
- close-code specific recovery behavior
- optional proxy/socket factory wiring for controlled network paths

### Phase 3: Performance tuning

- read buffer sizing experiments
- frame size limit tuning by channel mix
- optional `aiofastnet` policy tuning with baseline comparisons

## Guardrails

- No optimization rollout without before/after metrics.
- No feature activation that increases drop risk in hot path.
- Keep runtime contract values authoritative for heartbeat/reconnect defaults.

## Validation checklist before enabling a new picows feature

1. Soak run with no deadlock or reconnect storm.
2. No increase in parse errors or silent drops.
3. CPU/RAM impact measured and accepted.
4. Branch/contract mapping updated only where behavior changed.
