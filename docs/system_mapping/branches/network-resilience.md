# BR-NET-RES - Network Resilience

## Metadata

- branch_id: BR-NET-RES
- owner: TODO
- status: active
- last_updated: 2026-04-10
- last_verified: 2026-04-10
- verification_method: runtime contract review

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

## Run commands

- `PYTHONPATH=src .venv/bin/python -m control_plane.main --runtime-contract docs/handover/mvp_runtime_contract.json`

## Remaining gaps

- slot-level reconnect execution loop implementation (contract values already fixed)
