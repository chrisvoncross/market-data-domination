# BR-NET-RES - Network Resilience

## Metadata

- branch_id: BR-NET-RES
- owner: TODO
- status: active
- last_updated: 2026-04-10
- last_verified: 2026-04-10
- verification_method: handover review (`farmer-principles.md`)

## Mission

Maintain market stream continuity through endpoint/network failures with predictable reconnection behavior.

## Strategy

- reconnect with exponential backoff (`1s` to `10s`)
- heartbeat ping/pong supervision (`15s` idle ping, `10s` reply timeout)
- slot reconnect on missed heartbeat
- dynamic DNS resolution and IPv4 slot pinning

## Core invariants

1. Slot failure cannot stall all slots permanently.
2. Heartbeat timeout always leads to explicit reconnect action.
3. No hardcoded sensitive network inventory in docs or logs.

## Failure examples

- connect timeout -> retry loop
- heartbeat timeout -> disconnect/reconnect
- queue full under burst -> bounded drop behavior

## Observability focus

- reconnect count
- channel throughput dips
- queue pressure
- ingest lag

## Code locations

- TODO: set concrete runtime paths for reconnect policy, heartbeat supervisor, and DNS/IP slot management.

## Run commands

- TODO: add chaos/reconnect test commands and heartbeat timeout simulation commands.

## TODO gaps

- jitter and cooldown policy are currently unset
- formal reconnect SLO thresholds still deployment-specific
