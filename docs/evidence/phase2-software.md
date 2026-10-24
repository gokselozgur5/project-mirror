# Phase 2 software evidence

This checkpoint proves the host/controller protocol path without claiming a
physical controller, servo, power system, or mechanism result.

## Checkpoint

- Date: 2026-10-24
- Implementation revision: `156d7df9415d47274f6cb7774c794774277bf340`
- Public CI: [run 40103615936](https://github.com/gokselozgur5/project-mirror/actions/runs/40103615936)
- Platform tested locally: Apple Silicon macOS
- Firmware target compiled: ESP32-S3 DevKitC-1 N8

## Local verification

`make check` completed with:

- Repository history privacy and credential checks: passed.
- Shell syntax, Ruff format/lint, strict mypy, TypeScript, and ESLint: passed.
- Repository policy tests: 6 passed.
- Embodiment tests: 87 passed.
- Runtime tests: 9 passed.
- Perception tests: 8 passed.
- Operator web tests: 14 passed and production build completed.

`make firmware` completed with six native C++ CRC golden vectors and an ESP32-S3
release build. The build reported 19,048 bytes RAM (5.8%) and 290,425 bytes flash
(8.7%). These figures are compiler output, not live-board memory measurements.

`make audit` found no known dependency vulnerabilities. The three local Python
workspace packages were skipped as unpublished projects; their locked external
dependencies were audited. npm reported zero vulnerabilities.

## Runtime smoke

A post-motion-change 10-second full-stack run exercised synthetic boxes through
perception, runtime, gateway, and WebSocket state:

- Commands: 101 sent, 101 accepted, 0 failures.
- Request latency: 18.10 ms p50, 29.71 ms p95, 56.14 ms maximum.
- State age: 52.23 ms p50, 102.80 ms p95, 423.23 ms maximum.
- Maximum sequence lag: 1.
- Final transition after publisher stop: `neutral / heartbeat_timeout`.

This smoke supplements rather than replaces the accepted five-minute Phase 1
run in `phase1-simulation.md`.

## Software safety evidence

- Python and native C++ share checksummed golden protocol vectors.
- A deterministic 100-frame malformed corpus is rejected offline.
- Startup synchronizes controller sequence, reasserts stop, and validates the
  exact stopped acknowledgement before serving traffic.
- Physical arm and pose responses require exact matching controller telemetry;
  missing or inconsistent acknowledgements fail closed and emit stop.
- Idle links use sequence-neutral status polling; missing telemetry degrades
  health and reasserts physical stop.
- Host pose integration is hard-clamped after velocity/acceleration planning.
  Deterministic 1,000-step fuzz tests cover bounds and motion rates.
- Motion integration uses monotonic time, and a fresh pose after heartbeat
  silence expires the old trajectory before restarting from neutral.
- The operator sees link and output-armed state and cannot pose or arm an
  unhealthy configured controller. Emergency stop remains available.
- A pseudo-terminal test crosses the operating-system serial boundary. The
  guarded Gate 1 harness exercises protocol recovery and measures heartbeat
  detach in fake-device tests.

## Explicit limits

- No ESP32-S3 was flashed or queried for this checkpoint.
- No servo, actuator power, emergency-stop switch, or mechanism was connected.
- Firmware parsing, output detach, malformed-frame rejection, and timing remain
  compile-tested or simulated until Gate 1 is run on a real board.
- Pins, pulses, limits, geometry, current, thermal behavior, and direction are
  placeholders, not calibration evidence.
- No camera or detector backend was used. All visual observations were
  synthetic derived data.

The next accepted evidence must come from the unpowered controller-only Gate 1
procedure in `docs/BENCH_PLAN.md`. Do not promote this checkpoint to a physical
safety claim.
