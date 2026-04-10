#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f "$HOME/.cargo/env" ]]; then
  source "$HOME/.cargo/env"
fi

mkdir -p .artifacts

echo "[validate] control-plane contract bootstrap"
PYTHONPATH=src "$ROOT_DIR/.venv/bin/python" -m control_plane.main \
  --config docs/handover/farmer-config.json \
  --runtime-contract docs/handover/mvp_runtime_contract.json \
  > .artifacts/control_plane_bootstrap.json

echo "[validate] native build"
cargo build --manifest-path native/data_plane/Cargo.toml >/dev/null

echo "[validate] native run + resource profile"
TIME_BIN=""
if command -v /usr/bin/time >/dev/null 2>&1; then
  TIME_BIN="/usr/bin/time"
elif command -v /bin/time >/dev/null 2>&1; then
  TIME_BIN="/bin/time"
fi

if [[ -n "$TIME_BIN" ]]; then
  "$TIME_BIN" -f "elapsed_s=%e max_rss_kb=%M user_s=%U sys_s=%S" \
    -o .artifacts/native_resource_profile.txt \
    cargo run --quiet --manifest-path native/data_plane/Cargo.toml \
    < docs/handover/farmer-sample-events.ndjson \
    > .artifacts/native_out.ndjson
else
  # Fallback profiler via Python resource accounting.
  "$ROOT_DIR/.venv/bin/python" - <<'PY'
import resource
import subprocess
import time
from pathlib import Path

start = time.time()
with open("docs/handover/farmer-sample-events.ndjson", "rb") as fin, open(".artifacts/native_out.ndjson", "wb") as fout:
    subprocess.run(
        ["cargo", "run", "--quiet", "--manifest-path", "native/data_plane/Cargo.toml"],
        stdin=fin,
        stdout=fout,
        check=True,
    )
elapsed = time.time() - start
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
Path(".artifacts/native_resource_profile.txt").write_text(
    f"elapsed_s={elapsed:.3f} max_rss_kb={int(ru.ru_maxrss)} user_s={ru.ru_utime:.3f} sys_s={ru.ru_stime:.3f}\n",
    encoding="utf-8",
)
PY
fi

echo "[validate] invariants"
"$ROOT_DIR/.venv/bin/python" - <<'PY'
import json
from collections import defaultdict
from pathlib import Path

out = Path(".artifacts/native_out.ndjson").read_text(encoding="utf-8").splitlines()
events = [json.loads(x) for x in out if x.strip()]

finals = [e for e in events if e.get("event_type") == "final_candle"]
keys = [(e["symbol"], e["interval"], e["minute_ms"]) for e in finals]
dups = len(keys) - len(set(keys))

if dups != 0:
    raise SystemExit(f"FAIL duplicate final keys: {dups}")

if not finals:
    raise SystemExit("FAIL no final_candle events emitted")

by_symbol = defaultdict(int)
for e in finals:
    by_symbol[e["symbol"]] += 1

print(json.dumps({
    "status": "ok",
    "final_candles": len(finals),
    "symbols_with_finals": dict(by_symbol),
    "duplicate_final_keys": dups,
}, indent=2))
PY

echo "[validate] resource profile:"
cat .artifacts/native_resource_profile.txt
