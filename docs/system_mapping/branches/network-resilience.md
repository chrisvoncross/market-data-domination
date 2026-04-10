# BR-NET-RES - Network Resilience

## Metadata

- branch_id: BR-NET-RES
- owner: TODO
- status: active
- last_updated: 2026-04-10
- last_verified: 2026-04-10
- verification_method: runtime contract + live reconnect loop execution

## Mission

Maintain market stream continuity through endpoint/network failures with predictable reconnection behavior.

## Strategy

- reconnect with exponential backoff (`1s` to `10s`)
- heartbeat ping/pong supervision (`15s` idle ping, `10s` reply timeout)
- slot reconnect on missed heartbeat
- dynamic DNS resolution and IPv4 slot pinning
- primary runtime source: `docs/handover/mvp_runtime_contract.json`

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

- contract validation path: `src/control_plane/runtime_contract.py`
- plan enforcement path: `src/control_plane/plan.py`
- live reconnect/heartbeat loop: `src/control_plane/live_run.py`

## Run commands

- `PYTHONPATH=src .venv/bin/python -m control_plane.main --runtime-contract docs/handover/mvp_runtime_contract.json`
- `PYTHONPATH=src .venv/bin/python -m control_plane.live_run --duration-sec 30`

## Remaining gaps

- multi-slot sharded ingress worker (single-loop reconnect is implemented; slot fanout path remains future expansion)

## Last live check

- command: `PYTHONPATH=src .venv/bin/python -m control_plane.live_run --duration-sec 240`
- result:
  - connect attempts: `4`
  - connect success: `4`
  - reconnect count: `3`
  - connect failures: `0`
  - avg process CPU: `1.141%`
  - max RSS: `30536 kb`
