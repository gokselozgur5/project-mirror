# Phase 1 simulation evidence

## Result

Phase 1 passed its five-minute full-stack simulation gate on 2026-10-24. This
proves the synthetic derived-detection, perception policy, character runtime,
embodiment gateway, and state-stream path under the measured conditions below.
It does not prove camera inference, firmware behavior on a board, or physical
actuator safety.

## Reproduction

- Source revision: `c44354e8cba7b42b515e2277c720efd601aab23c`
- Host: macOS development machine
- Python: 3.11
- Duration: 300 seconds
- Publication rate: 10 Hz
- Runner: `./scripts/run-phase1-stack-soak.sh 300`

The test started isolated perception, runtime, and gateway processes, published
normalized synthetic face boxes through the full chain, observed the gateway
WebSocket stream, stopped the publisher, and verified the expiry transition.

## Measurements

| Measure | Result |
| --- | ---: |
| Commands sent / accepted | 3,001 / 3,001 |
| Failures / gateway rejections | 0 / 0 |
| Request latency p50 / p95 / max | 17.36 / 26.18 / 112.92 ms |
| State age p50 / p95 / max | 51.68 / 98.58 / 401.91 ms |
| Maximum sequence lag | 1 |
| WebSocket state samples | 5,880 |
| Gateway RSS start / end / growth | 54,755,328 / 30,703,616 / -24,051,712 bytes |
| Runtime RSS start / end / growth | 55,312,384 / 45,613,056 / -9,699,328 bytes |
| Perception RSS start / end / growth | 55,459,840 / 46,301,184 / -9,158,656 bytes |
| Heartbeat timeout count | 1 |
| Final mode / reason | `neutral` / `heartbeat_timeout` |

All three isolated service processes ended with less resident memory than they
had at the start of publication, so this run showed no accumulating service
memory trend.
The maximum state age includes startup before the first accepted command; the
p95 value represents the sustained stream acceptance gate.

## Continuous verification

GitHub Actions run
[`40099968161`](https://github.com/gokselozgur5/project-mirror/actions/runs/40099968161)
passed repository privacy checks, Python lint/type/test checks, a short
perception-to-gateway stack soak, the web lint/type/production build, native C++
protocol vectors, and the pinned ESP32 firmware compile for the same source
revision.

## Remaining boundary

Phase 2 must validate the independent firmware clamp, malformed serial frames,
calibrated soft limits, heartbeat loss, emergency stop, power integrity, and
actual mechanics on a current-limited bench. No servo should be attached based
on this simulation result alone.
