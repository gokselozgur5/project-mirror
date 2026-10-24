#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
duration=${1:-300}
report=${2:-$project_root/runtime/phase1-stack-soak.json}
gateway_port=${MIRROR_SOAK_PORT:-18080}
runtime_port=$((gateway_port + 1))

cd "$project_root"
mkdir -p "$(dirname "$report")"

"$project_root/.venv/bin/uvicorn" project_mirror_embodiment.app:app \
  --host 127.0.0.1 --port "$gateway_port" \
  >"$project_root/runtime/phase1-gateway.log" 2>&1 &
gateway_pid=$!

MIRROR_GATEWAY_URL="http://127.0.0.1:$gateway_port" \
  "$project_root/.venv/bin/uvicorn" project_mirror_runtime.app:app \
  --host 127.0.0.1 --port "$runtime_port" \
  >"$project_root/runtime/phase1-runtime.log" 2>&1 &
runtime_pid=$!

cleanup() {
  kill "$runtime_pid" "$gateway_pid" 2>/dev/null || true
  wait "$runtime_pid" "$gateway_pid" 2>/dev/null || true
}
trap cleanup EXIT

for _ in {1..50}; do
  if curl --fail --silent "http://127.0.0.1:$gateway_port/health" >/dev/null && \
    curl --fail --silent "http://127.0.0.1:$runtime_port/health" >/dev/null; then
    break
  fi
  sleep 0.1
done
curl --fail --silent "http://127.0.0.1:$gateway_port/health" >/dev/null
curl --fail --silent "http://127.0.0.1:$runtime_port/health" >/dev/null

"$project_root/.venv/bin/python" "$project_root/scripts/phase1-soak.py" \
  --gateway-http "http://127.0.0.1:$gateway_port" \
  --gateway-ws "ws://127.0.0.1:$gateway_port/v1/stream" \
  --runtime-http "http://127.0.0.1:$runtime_port" \
  --gateway-pid "$gateway_pid" \
  --duration "$duration" \
  --output "$report"
