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
- multi-slot reconnect supervisor (critical feeds duplicated)
- dynamic DNS resolution and optional IPv4 slot pinning (`socket_factory`)
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
- slot planner + worker runtime: `src/control_plane/resilience_runtime.py`
- live orchestration entrypoint: `src/control_plane/live_run.py`

## Run commands

- `PYTHONPATH=src .venv/bin/python -m control_plane.main --runtime-contract docs/handover/mvp_runtime_contract.json`
- `scripts/validate_resilience.sh 120 300`
- `scripts/stress_resilience.sh` (defaults: `ROUNDS=3`, `DURATION_SEC=120`)

## Remaining gaps

- forced fault-injection coverage should be expanded (current stress gate uses repeated live runs and reconnect evidence)

## Last live check

- command: `ROUNDS=3 DURATION_SEC=120 scripts/stress_resilience.sh`
- result:
  - stress report: `.artifacts/resilience/resilience_report.json`
  - rounds: `3`
  - report status: `pass`
  - connect failures: `0` in all rounds
  - parse errors: `0` in all rounds
  - all required channels observed in all rounds
  - observed max RSS: `34880 kb`
