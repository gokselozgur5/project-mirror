# Current status

This is the development handoff, not a release claim. Read the architecture,
safety model, relevant ADRs, and linked issue before changing a boundary.

## Verified checkpoint

- Last updated: 2026-10-24
- Source revision at checkpoint: `d5460a948caa85134eb53d4141ea86587f628ad5`
- Phase 1: accepted in hardware-free simulation
- Phase 2: protocol work started; no hardware validation

The public CI at this checkpoint covers repository privacy rules, Python lint,
strict types and tests, a short full-stack soak, web lint/types/build, and an
ESP32 firmware compile. The local five-minute result and its limits are recorded
in `docs/evidence/phase1-simulation.md`.

## Implemented

- Versioned observation, pose, embodiment-state, and serial-command contracts.
- Face-direction policy with confidence threshold and center dead zone.
- Privacy-preserving perception adapter that selects a deterministic target
  from derived face boxes and emits the public observation contract without raw
  image fields.
- Bounded gateway with stale/future/sequence rejection, velocity and
  acceleration limits, telemetry, latched stop, explicit arm, and heartbeat
  neutral behavior.
- Browser avatar/operator view consuming canonical gateway state.
- Reproducible short and five-minute full-stack soak runners.
- ESP32 scaffold with independent angle clamp, stale-sequence rejection,
  checksummed integer commands, oversized-frame discard, and heartbeat detach.
- Host controller transport with an independent monotonic wire sequence,
  complete-write enforcement, and in-memory pose/stop/arm tests.
- Gateway-to-controller dispatch for pose, stop, and arm; incomplete writes
  return an error and latch the host gateway stopped.
- Deterministic 100-frame malformed protocol corpus for later unpowered-board
  rejection tests; offline decoders reject every frame.
- Exact frontend and firmware dependency pins plus public CI.

## Not implemented or not proven

- No camera/detector backend; Phase 1 observations are synthetic and the new
  perception boundary accepts only already-derived boxes.
- An explicit `MIRROR_SERIAL_PORT` opens a controller, dispatches writes, and
  reads validated telemetry into `/v1/controller`; this remains fake-tested,
  not board-tested.
- Firmware checksum handling is compile-verified, not board-tested.
- Pin numbers, pulse widths, soft limits, servo selection, and power design are
  placeholders pending measured hardware.
- No firmware stop/arm wire command or checksummed telemetry contract yet.
- No VAD, STT, text model, TTS, interruption pipeline, or conversation state.
- No persistent memory, user isolation, avatar lip sync, or physical rig.
- Physical pose and arm calls require a bearer control token; emergency stop is
  intentionally unauthenticated. Broader user/session authentication is not
  implemented.
- No servo or mechanism has been authorized for connection.

## Next safe slice

Continue [issue 2](https://github.com/gokselozgur5/project-mirror/issues/2):

1. Define versioned, checksummed telemetry and explicit stop/arm frames.
2. Add a configured serial port and telemetry reader around the tested host
   transport without making hardware a default runtime dependency.
3. Add native or on-board golden-vector tests proving Python and firmware CRC
   implementations agree.
4. Only then perform the controller-only bench sequence in `docs/HARDWARE.md`.

Do not close the issue on the strength of a firmware compile. Its acceptance
criteria require real disconnect and malformed-frame behavior on the board.

## Working conventions

- Keep code and repository prose in English.
- Use small Conventional Commits and preserve a green `main` branch.
- Do not put issue numbers in source comments.
- Keep private media, recordings, credentials, generated video, model weights,
  and runtime reports outside Git.
- Never let model-controlled code bypass the embodiment gateway or firmware
  clamp.
- Update this file when the verified checkpoint, known boundary, or next safe
  slice changes.
