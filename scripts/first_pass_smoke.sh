#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f "$HOME/.cargo/env" ]]; then
  # Ensure cargo is available for native data-plane checks.
  source "$HOME/.cargo/env"
fi

echo "[1/3] Control-plane first-pass plan"
PYTHONPATH=src "$ROOT_DIR/.venv/bin/python" -m control_plane.main --config docs/handover/farmer-config.json

echo "[2/3] Native data-plane build"
cargo build --manifest-path native/data_plane/Cargo.toml

echo "[3/3] Native data-plane route smoke"
cargo run --quiet --manifest-path native/data_plane/Cargo.toml < docs/handover/farmer-sample-events.ndjson | head -n 10
