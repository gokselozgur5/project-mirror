# Current status

This is the development handoff, not a release claim. Read the architecture,
safety model, relevant ADRs, and linked issue before changing a boundary.

## Verified checkpoint

- Last updated: 2026-10-24
- Implementation revision at checkpoint: `7818ee496e66fdc5c83fda179f524dd4dde414ee`
- Phase 1: accepted in hardware-free simulation
- Phase 2: software protocol path complete; hardware validation has not started

Public CI covers repository privacy rules, Python lint, strict types and tests,
a short full-stack soak, web lint/types/tests/build, native protocol vectors, and
an ESP32 firmware compile. The local five-minute result and its limits are
recorded in `docs/evidence/phase1-simulation.md`.

## Implemented and verified in software

- Versioned observation, pose, embodiment-state, controller-health, serial
  command, and serial telemetry contracts.
- Privacy-preserving perception adapter that deterministically selects a target
  from derived face boxes. The service does not accept or persist raw media.
- End-to-end synthetic perception-to-runtime-to-gateway-to-browser path.
- Bounded gateway with stale, future, and sequence rejection; velocity and
  acceleration limits; metrics; a latched stop; explicit arm; and heartbeat
  neutral behavior.
- Browser operator view consuming canonical gateway state and surfacing
  controller health. Motion and arm controls are disabled when a configured
  controller is unhealthy; stop remains available.
- Reproducible short and five-minute full-stack soak runners. The five-minute
  acceptance run completed 3,001 of 3,001 requests without a failure.
- ESP32-S3 firmware scaffold with independent angle clamps, monotonic sequence
  enforcement, versioned CRC32 frames, oversized-frame discard, explicit
  status/stop/arm commands, checksummed telemetry, and heartbeat detach.
- Host serial transport with complete-write enforcement, reconnect sequence
  synchronization, continuous telemetry validation, and fail-closed handling
  for invalid, stale, missing, or backwards telemetry.
- Physical startup stop latch: opening the serial port synchronizes controller
  state, sends stop, and requires matching telemetry before startup succeeds.
- Physical arm acknowledgement gate: host arm stays latched until the exact
  command sequence is acknowledged with the expected controller transition.
- Bearer authorization for physical pose and arm calls. Emergency stop is
  intentionally unauthenticated.
- Deterministic 100-frame malformed protocol corpus. Offline host and native
  firmware protocol tests reject malformed input and share golden CRC vectors.
- Exact Python, frontend, and firmware dependency locks plus scheduled public
  dependency audits.

## Not implemented or not proven

- No camera or detector backend. Phase 1 observations are synthetic; the
  perception boundary accepts only already-derived boxes.
- Serial behavior is fake-tested and compile-tested, not tested on an ESP32-S3.
- Pin numbers, pulse widths, soft limits, servo selection, mechanism geometry,
  and power design are placeholders pending measured hardware.
- No controller, servo, or mechanism has been authorized for powered movement.
- No VAD, STT, language model, TTS, interruption pipeline, conversation state,
  persistent memory, user isolation, or avatar lip sync.
- Broader user and session authentication is not implemented.

## Next safe slice

Continue [issue 2](https://github.com/gokselozgur5/project-mirror/issues/2)
with the controller-only bench plan in `docs/HARDWARE.md`:

1. Record the exact board revision, USB device, firmware revision, and wiring;
   keep servos and external motion power disconnected.
2. Flash the pinned firmware and prove status synchronization, startup stop,
   arm acknowledgement, and monotonic sequence behavior over the real link.
3. Send the 100-frame malformed corpus and prove that none produces motion or
   an unsafe state transition.
4. Prove heartbeat timeout and USB disconnect return the controller to detached,
   stopped behavior.
5. Attach the evidence to issue 2. Do not close it on compile results alone.

Only after that gate should issue 3 add and profile a real detector backend.

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
