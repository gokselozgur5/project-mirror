# Phase 1 simulation evidence

## Result

Phase 1 passed its five-minute full-stack simulation gate on 2026-10-24. This
proves the synthetic observation, character runtime, embodiment gateway, and
state-stream path under the measured conditions below. It does not prove camera
perception, firmware behavior on a board, or physical actuator safety.

## Reproduction

- Source revision: `2f9cc591789d385748ca87ae96271240c9c5a68a`
- Host: macOS development machine
- Python: 3.11
- Duration: 300 seconds
- Publication rate: 10 Hz
- Runner: `./scripts/run-phase1-stack-soak.sh 300`

The test started isolated runtime and gateway processes, published normalized
synthetic face observations through the runtime, observed the gateway WebSocket
stream, stopped the publisher, and verified the expiry transition.

## Measurements

| Measure | Result |
| --- | ---: |
| Commands sent / accepted | 3,001 / 3,001 |
| Failures / gateway rejections | 0 / 0 |
| Request latency p50 / p95 / max | 9.61 / 20.84 / 48.36 ms |
| State age p50 / p95 / max | 51.51 / 97.63 / 263.70 ms |
| Maximum sequence lag | 1 |
| WebSocket state samples | 5,892 |
| Gateway RSS start / end | 52,215,808 / 29,966,336 bytes |
| Gateway RSS growth | -22,249,472 bytes |
| Heartbeat timeout count | 1 |
| Final mode / reason | `neutral` / `heartbeat_timeout` |

The isolated gateway process ended with less resident memory than it had at the
start of publication, so this run showed no accumulating gateway-memory trend.
The maximum state age includes startup before the first accepted command; the
p95 value represents the sustained stream acceptance gate.

## Continuous verification

GitHub Actions run
[`40097588326`](https://github.com/gokselozgur5/project-mirror/actions/runs/40097588326)
passed repository privacy checks, Python lint/type/test checks, a short
full-stack soak, the web lint/type/production build, and the pinned ESP32
firmware compile for the same source revision.

## Remaining boundary

Phase 2 must validate the independent firmware clamp, malformed serial frames,
calibrated soft limits, heartbeat loss, emergency stop, power integrity, and
actual mechanics on a current-limited bench. No servo should be attached based
on this simulation result alone.
