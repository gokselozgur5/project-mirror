#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python_bin="$project_root/.venv/bin/python"

if [[ ! -x "$python_bin" ]]; then
  echo "missing .venv; run 'make bootstrap' first" >&2
  exit 1
fi

cd "$project_root"
mkdir -p runtime

"$python_bin" -m uvicorn project_mirror_embodiment.app:app \
  --host 127.0.0.1 --port 8080 >runtime/dev-gateway.log 2>&1 &
gateway_pid=$!

MIRROR_GATEWAY_URL=http://127.0.0.1:8080 \
  "$python_bin" -m uvicorn project_mirror_runtime.app:app \
  --host 127.0.0.1 --port 8081 >runtime/dev-runtime.log 2>&1 &
runtime_pid=$!

MIRROR_RUNTIME_URL=http://127.0.0.1:8081 \
  "$python_bin" -m uvicorn project_mirror_perception.app:app \
  --host 127.0.0.1 --port 8082 >runtime/dev-perception.log 2>&1 &
perception_pid=$!

npm run dev --workspace @project-mirror/operator-web -- --host 127.0.0.1 \
  >runtime/dev-web.log 2>&1 &
web_pid=$!

cleanup() {
  kill "$web_pid" "$perception_pid" "$runtime_pid" "$gateway_pid" 2>/dev/null || true
  wait "$web_pid" "$perception_pid" "$runtime_pid" "$gateway_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 0' INT TERM

for _ in {1..100}; do
  if ! kill -0 "$gateway_pid" 2>/dev/null || ! kill -0 "$runtime_pid" 2>/dev/null || \
    ! kill -0 "$perception_pid" 2>/dev/null || ! kill -0 "$web_pid" 2>/dev/null; then
    break
  fi
  if curl --fail --silent http://127.0.0.1:8080/health >/dev/null && \
    curl --fail --silent http://127.0.0.1:8081/health >/dev/null && \
    curl --fail --silent http://127.0.0.1:8082/health >/dev/null && \
    curl --fail --silent http://127.0.0.1:5173/ >/dev/null; then
    echo "Project Mirror simulation is ready at http://127.0.0.1:5173"
    echo "Logs are under $project_root/runtime; press Ctrl-C to stop."
    while kill -0 "$gateway_pid" 2>/dev/null && kill -0 "$runtime_pid" 2>/dev/null && \
      kill -0 "$perception_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do
      sleep 1
    done
    break
  fi
  sleep 0.1
done

echo "development stack stopped or failed to become ready" >&2
for log in runtime/dev-gateway.log runtime/dev-runtime.log runtime/dev-perception.log runtime/dev-web.log; do
  echo "--- $log" >&2
  tail -n 20 "$log" >&2 || true
done
exit 1
