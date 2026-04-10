#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f "$HOME/.cargo/env" ]]; then
  source "$HOME/.cargo/env"
fi

NORMAL_DURATION="${1:-120}"
STRESS_DURATION="${2:-300}"
ARTIFACT_BASE=".artifacts/resilience"
NORMAL_OUT="$ARTIFACT_BASE/normal"
STRESS_OUT="$ARTIFACT_BASE/stress"

mkdir -p "$NORMAL_OUT" "$STRESS_OUT"

echo "[resilience] bootstrap contract validation"
PYTHONPATH=src "$ROOT_DIR/.venv/bin/python" -m control_plane.main \
  --config docs/handover/farmer-config.json \
  --runtime-contract docs/handover/mvp_runtime_contract.json \
  > "$ARTIFACT_BASE/control_plane_bootstrap.json"

echo "[resilience] unit tests"
PYTHONPATH=src "$ROOT_DIR/.venv/bin/python" -m unittest tests/test_resilience_runtime.py

echo "[resilience] normal live run (${NORMAL_DURATION}s)"
PYTHONPATH=src "$ROOT_DIR/.venv/bin/python" -m control_plane.live_run \
  --duration-sec "$NORMAL_DURATION" \
  --capture-feeds 2 \
  --tier1-dedicated \
  --feed-path-diversity \
  --out-dir "$NORMAL_OUT" \
  > "$NORMAL_OUT/summary.pretty.json"

echo "[resilience] stress live run (${STRESS_DURATION}s)"
PYTHONPATH=src "$ROOT_DIR/.venv/bin/python" -m control_plane.live_run \
  --duration-sec "$STRESS_DURATION" \
  --capture-feeds 2 \
  --tier1-dedicated \
  --feed-path-diversity \
  --out-dir "$STRESS_OUT" \
  > "$STRESS_OUT/summary.pretty.json"

echo "[resilience] verify pass/fail gates"
"$ROOT_DIR/.venv/bin/python" - <<'PY'
import json
from pathlib import Path

normal = json.loads(Path(".artifacts/resilience/normal/live_summary.json").read_text(encoding="utf-8"))
stress = json.loads(Path(".artifacts/resilience/stress/live_summary.json").read_text(encoding="utf-8"))

def assert_gate(summary: dict, label: str) -> None:
    if summary.get("status") != "ok":
        raise SystemExit(f"{label}: status != ok")
    if summary.get("missing_channels_observed"):
        raise SystemExit(f"{label}: missing channels observed: {summary.get('missing_channels_observed')}")
    if summary.get("connect_failures", 0) != 0:
        raise SystemExit(f"{label}: connect failures > 0")
    if summary.get("parse_errors", 0) != 0:
        raise SystemExit(f"{label}: parse errors > 0")
    if summary.get("slot_count", 0) < 4:
        raise SystemExit(f"{label}: slot count unexpectedly low")
    if not summary.get("slot_metrics"):
        raise SystemExit(f"{label}: missing slot metrics")

assert_gate(normal, "normal")
assert_gate(stress, "stress")

print(json.dumps({
    "status": "ok",
    "normal": {
        "elapsed_sec": normal["elapsed_sec"],
        "routed_frames": normal["routed_frames"],
        "avg_process_cpu_pct": normal["avg_process_cpu_pct"],
        "max_rss_kb": normal["max_rss_kb"],
    },
    "stress": {
        "elapsed_sec": stress["elapsed_sec"],
        "routed_frames": stress["routed_frames"],
        "avg_process_cpu_pct": stress["avg_process_cpu_pct"],
        "max_rss_kb": stress["max_rss_kb"],
    }
}, indent=2))
PY
