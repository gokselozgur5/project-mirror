#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
duration=${1:-300}
report=${2:-$project_root/runtime/phase1-soak.json}
port=${MIRROR_SOAK_PORT:-18080}
if [[ -n "${MIRROR_PYTHON:-}" ]]; then
  python_bin=$MIRROR_PYTHON
elif [[ -x "$project_root/.venv/bin/python" ]]; then
  python_bin="$project_root/.venv/bin/python"
else
  python_bin=python3
fi

cd "$project_root"
mkdir -p "$(dirname "$report")"

"$python_bin" -m uvicorn project_mirror_embodiment.app:app \
  --host 127.0.0.1 --port "$port" \
  >"$project_root/runtime/phase1-gateway.log" 2>&1 &
gateway_pid=$!
trap 'kill "$gateway_pid" 2>/dev/null || true; wait "$gateway_pid" 2>/dev/null || true' EXIT

for _ in {1..50}; do
  if ! kill -0 "$gateway_pid" 2>/dev/null; then
    cat "$project_root/runtime/phase1-gateway.log" >&2
    exit 1
  fi
  if curl --fail --silent "http://127.0.0.1:$port/health" >/dev/null; then
    break
  fi
  sleep 0.1
done
if ! curl --fail --silent "http://127.0.0.1:$port/health" >/dev/null; then
  cat "$project_root/runtime/phase1-gateway.log" >&2
  exit 1
fi

"$python_bin" "$project_root/scripts/phase1-soak.py" \
  --gateway-http "http://127.0.0.1:$port" \
  --gateway-ws "ws://127.0.0.1:$port/v1/stream" \
  --gateway-pid "$gateway_pid" \
  --duration "$duration" \
  --output "$report"
