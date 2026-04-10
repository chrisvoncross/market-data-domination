#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ROUNDS="${ROUNDS:-3}"
DURATION_SEC="${DURATION_SEC:-120}"
OUT_DIR="${OUT_DIR:-.artifacts/resilience}"

mkdir -p "$OUT_DIR"

echo "[stress] rounds=$ROUNDS duration_sec=$DURATION_SEC out_dir=$OUT_DIR"

for i in $(seq 1 "$ROUNDS"); do
  run_dir="$OUT_DIR/run-$i"
  mkdir -p "$run_dir"
  echo "[stress] run $i/$ROUNDS"
  PYTHONPATH=src "$ROOT_DIR/.venv/bin/python" -m control_plane.live_run \
    --duration-sec "$DURATION_SEC" \
    --out-dir "$run_dir"
done

python - <<'PY'
import json
from pathlib import Path

root = Path(".artifacts/resilience")
runs = sorted([p for p in root.glob("run-*/live_summary.json") if p.exists()])
if not runs:
    raise SystemExit("FAIL: no resilience summaries found")

required_channels = {
    "push.deal",
    "push.kline",
    "push.depth.full",
    "push.ticker",
    "push.funding.rate",
    "push.index.price",
    "push.fair.price",
}

failures = []
rows = []
for p in runs:
    data = json.loads(p.read_text(encoding="utf-8"))
    row = {
        "path": str(p),
        "status": data.get("status"),
        "parse_errors": int(data.get("parse_errors", 0)),
        "missing_channels_observed": list(data.get("missing_channels_observed", [])),
        "connect_failures": int(data.get("connect_failures", 0)),
        "max_rss_kb": int(data.get("max_rss_kb", 0)),
        "avg_process_cpu_pct": float(data.get("avg_process_cpu_pct", 0.0)),
        "channel_counts": data.get("channel_counts", {}),
    }
    rows.append(row)

    if row["status"] != "ok":
        failures.append(f"{p}: status != ok")
    if row["parse_errors"] != 0:
        failures.append(f"{p}: parse_errors={row['parse_errors']}")
    if row["connect_failures"] != 0:
        failures.append(f"{p}: connect_failures={row['connect_failures']}")
    if row["missing_channels_observed"]:
        failures.append(f"{p}: missing_channels_observed={row['missing_channels_observed']}")

    observed = {k for k, v in row["channel_counts"].items() if isinstance(v, int) and v > 0}
    missing = sorted(required_channels - observed)
    if missing:
        failures.append(f"{p}: required channels without events: {missing}")

report = {
    "status": "pass" if not failures else "fail",
    "round_count": len(runs),
    "failures": failures,
    "runs": rows,
}

report_path = root / "resilience_report.json"
report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(report, indent=2, sort_keys=True))

if failures:
    raise SystemExit("FAIL: resilience stress gate failed")
PY
