# Embodiment gateway

The gateway is the only host service allowed to address physical embodiment
adapters. It validates freshness and sequence, clamps pose, rate-limits motion,
and returns to neutral after command expiry.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e 'services/embodiment[dev]'
uvicorn project_mirror_embodiment.app:app --reload --port 8080
```

Send a pose target:

```bash
curl -X POST http://127.0.0.1:8080/v1/pose \
  -H 'content-type: application/json' \
  -d '{"version":1,"sequence":1,"issued_at_ms":0,"ttl_ms":500,"yaw_deg":15,"pitch_deg":-5}'
```

Use a real current Unix millisecond timestamp for normal clients. Timestamp `0`
is only accepted in tests that inject their own clock.

## Head-controller transport

`HeadControllerTransport` converts bounded states and explicit stop/arm actions
to checksummed controller frames. It owns a monotonic wire sequence independent
of the source pose sequence, because stop and timeout transitions may not
advance that source value. Its in-memory transport tests do not open a serial
port. Fake-device tests cover status synchronization, pose/stop/arm dispatch,
telemetry validation, acknowledgement timeouts, and incomplete writes. These
tests do not replace the controller-only physical bench gate. Any transport or
telemetry failure latches the host gateway stopped.

To open a controller explicitly, set the serial device before starting the
gateway:

```bash
MIRROR_CONTROL_TOKEN=replace-with-at-least-32-random-characters \
MIRROR_SERIAL_PORT=/dev/cu.usbmodem-controller \
  uvicorn project_mirror_embodiment.app:app --port 8080
```

The default is simulation and opens no device. A configured port that cannot be
opened fails service startup instead of silently falling back to simulation.
Physical mode also refuses to start without a control token. Pose and arm
require its bearer authorization; emergency stop deliberately remains
available without it.
Startup also requires a valid checksummed status handshake; the host resumes
above the controller's existing wire sequence instead of assuming the board
restarted with it.
Validated controller telemetry is exposed at `/v1/controller`; corrupt,
unpublished-future, and backwards sequence frames are counted and never
reported as an online controller state.
Arm does not release the host latch until the controller returns matching
checksummed telemetry for that exact wire sequence. Use the guarded Gate 1
harness documented in [`docs/BENCH_PLAN.md`](../../docs/BENCH_PLAN.md) before
attaching any servo.
