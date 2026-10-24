#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
duration=${1:-300}
report=${2:-$project_root/runtime/phase1-stack-soak.json}
gateway_port=${MIRROR_SOAK_PORT:-18080}
runtime_port=$((gateway_port + 1))
perception_port=$((gateway_port + 2))
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
  --host 127.0.0.1 --port "$gateway_port" \
  >"$project_root/runtime/phase1-gateway.log" 2>&1 &
gateway_pid=$!

MIRROR_GATEWAY_URL="http://127.0.0.1:$gateway_port" \
  "$python_bin" -m uvicorn project_mirror_runtime.app:app \
  --host 127.0.0.1 --port "$runtime_port" \
  >"$project_root/runtime/phase1-runtime.log" 2>&1 &
runtime_pid=$!

MIRROR_RUNTIME_URL="http://127.0.0.1:$runtime_port" \
  "$python_bin" -m uvicorn project_mirror_perception.app:app \
  --host 127.0.0.1 --port "$perception_port" \
  >"$project_root/runtime/phase1-perception.log" 2>&1 &
perception_pid=$!

cleanup() {
  kill "$perception_pid" "$runtime_pid" "$gateway_pid" 2>/dev/null || true
  wait "$perception_pid" "$runtime_pid" "$gateway_pid" 2>/dev/null || true
}
trap cleanup EXIT

for _ in {1..50}; do
  if ! kill -0 "$gateway_pid" 2>/dev/null || ! kill -0 "$runtime_pid" 2>/dev/null || \
    ! kill -0 "$perception_pid" 2>/dev/null; then
    cat "$project_root/runtime/phase1-gateway.log" >&2
    cat "$project_root/runtime/phase1-runtime.log" >&2
    cat "$project_root/runtime/phase1-perception.log" >&2
    exit 1
  fi
  if curl --fail --silent "http://127.0.0.1:$gateway_port/health" >/dev/null && \
    curl --fail --silent "http://127.0.0.1:$runtime_port/health" >/dev/null && \
    curl --fail --silent "http://127.0.0.1:$perception_port/health" >/dev/null; then
    break
  fi
  sleep 0.1
done
if ! curl --fail --silent "http://127.0.0.1:$gateway_port/health" >/dev/null || \
  ! curl --fail --silent "http://127.0.0.1:$runtime_port/health" >/dev/null || \
  ! curl --fail --silent "http://127.0.0.1:$perception_port/health" >/dev/null; then
  cat "$project_root/runtime/phase1-gateway.log" >&2
  cat "$project_root/runtime/phase1-runtime.log" >&2
  cat "$project_root/runtime/phase1-perception.log" >&2
  exit 1
fi

"$python_bin" "$project_root/scripts/phase1-soak.py" \
  --gateway-http "http://127.0.0.1:$gateway_port" \
  --gateway-ws "ws://127.0.0.1:$gateway_port/v1/stream" \
  --runtime-http "http://127.0.0.1:$runtime_port" \
  --perception-http "http://127.0.0.1:$perception_port" \
  --gateway-pid "$gateway_pid" \
  --duration "$duration" \
  --output "$report"
