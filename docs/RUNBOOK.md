# Operator runbook

This runbook operates the Phase 1 simulation. It does not authorize connecting
servos; physical motion requires the Phase 2 calibration and bench-safety work.

## Bootstrap and verify

From the repository root:

```bash
make bootstrap
make check
```

`make bootstrap` creates `.venv`, installs both Python services in editable
mode, and installs the pinned web dependencies. `make check` runs the privacy
gate, linters, strict Python type checks, service tests, and the production web
build.

Firmware is checked separately when PlatformIO is installed:

```bash
make firmware
```

## Start the stack

For the default simulation, `make dev` starts all services and the operator in
one foreground process. It writes only ignored local logs beneath `runtime/`
and stops the children on `Ctrl-C`.

In another terminal, `make simulate` publishes synthetic derived face boxes
through perception and runtime. Stopping it lets the gateway heartbeat return
the avatar to neutral.

Alternatively, open four terminals at the repository root.

Terminal 1 — bounded embodiment gateway:

```bash
make run-gateway
```

This opens no serial device. During controller-only Phase 2 bench work, an
explicit `MIRROR_SERIAL_PORT=/dev/...` selects the device. Never set it with
servos attached until controller, power, geometry, and stop checks are complete.
Physical mode also requires `MIRROR_CONTROL_TOKEN`; pass the same value to the
runtime as `MIRROR_GATEWAY_TOKEN` or enter it into the operator field for the
current browser session. The browser keeps it only in memory. Stop remains
unauthenticated so a missing credential cannot prevent an emergency stop.
After a physical controller handshake, both host and firmware remain
stop-latched until an authenticated explicit arm.

Terminal 2 — character runtime:

```bash
MIRROR_GATEWAY_URL=http://127.0.0.1:8080 \
  .venv/bin/uvicorn project_mirror_runtime.app:app --reload --port 8081
```

Terminal 3 — browser operator:

```bash
make run-web
```

Open the URL printed by Vite. The web application reads the gateway at
`http://127.0.0.1:8080` and its state stream at
`ws://127.0.0.1:8080/v1/stream` by default.

## Check health and telemetry

```bash
curl --fail http://127.0.0.1:8080/health
curl --fail http://127.0.0.1:8081/health
curl --fail http://127.0.0.1:8080/v1/state
curl --fail http://127.0.0.1:8080/v1/metrics
curl --fail http://127.0.0.1:8080/v1/controller
```

Gateway health reports `controller: simulated` unless an explicit serial device
was opened successfully. Failure to open a requested device aborts startup; it
does not silently fall back to simulation.
The controller endpoint distinguishes `awaiting_telemetry`, `online`, `stale`,
and `invalid_telemetry`, and preserves the last validated sequence and
transition. Gateway health reports `degraded` when an explicitly configured
controller has not produced recent valid telemetry.
Invalid or stale telemetry also latches the gateway stopped and sends a
controller stop. Pose and Arm remain rejected until validated telemetry is
online again; diagnose the link before continuing.

The operator view shows the current mode, target and applied pose, receipt age,
sequence, and last transition reason. A stale publisher must cause the applied
pose to return to neutral with `heartbeat_timeout` as the reason.

## Stop, arm, and recover

The Stop control immediately requests neutral and latches the gateway. New pose
commands are rejected while latched. Use Arm only after confirming that the
cause of the stop is understood and the simulated or physical workspace is
clear.

If either service becomes unavailable:

1. Stop the observation publisher.
2. Confirm the gateway reports neutral state.
3. Restart the failed service.
4. Check both health endpoints.
5. Arm explicitly if the stop latch is active.

Do not bypass a latch, enlarge motion limits, or extend heartbeat timeouts to
make a failing test pass.

## Phase 1 acceptance

```bash
make phase1-soak
```

The runner starts isolated runtime and gateway processes, publishes synthetic
observations for five minutes, records HTTP latency, state age, sequence lag,
failures, and gateway/runtime/perception memory growth, then stops publication
and verifies the heartbeat-neutral transition. Its JSON report is written beneath the ignored
`runtime/` directory so local operating evidence is not committed accidentally.

## Shut down

Use `Ctrl-C` in the web, runtime, and gateway terminals. Before leaving a
physical prototype unattended, disconnect actuator power. Stopping software is
not a substitute for removing actuator power.
