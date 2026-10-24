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
- Bounded gateway with stale/future/sequence rejection, velocity and
  acceleration limits, telemetry, latched stop, explicit arm, and heartbeat
  neutral behavior.
- Browser avatar/operator view consuming canonical gateway state.
- Reproducible short and five-minute full-stack soak runners.
- ESP32 scaffold with independent angle clamp, stale-sequence rejection,
  checksummed integer commands, oversized-frame discard, and heartbeat detach.
- Exact frontend and firmware dependency pins plus public CI.

## Not implemented or not proven

- No camera adapter; Phase 1 observations are synthetic.
- No host serial writer connects gateway state to an ESP32 yet.
- Firmware checksum handling is compile-verified, not board-tested.
- Pin numbers, pulse widths, soft limits, servo selection, and power design are
  placeholders pending measured hardware.
- No firmware stop/arm wire command or checksummed telemetry contract yet.
- No VAD, STT, text model, TTS, interruption pipeline, or conversation state.
- No persistent memory, user isolation, avatar lip sync, or physical rig.
- Browser-to-gateway authorization described in the threat model is not built.
- No servo or mechanism has been authorized for connection.

## Next safe slice

Continue [issue 2](https://github.com/gokselozgur5/project-mirror/issues/2):

1. Define versioned, checksummed telemetry and explicit stop/arm frames.
2. Give the physical transport its own monotonic wire sequence; source pose
   sequence cannot represent stop or timeout transitions by itself.
3. Build a host serial adapter against an in-memory fake before opening a port.
4. Add native or on-board golden-vector tests proving Python and firmware CRC
   implementations agree.
5. Only then perform the controller-only bench sequence in `docs/HARDWARE.md`.

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
