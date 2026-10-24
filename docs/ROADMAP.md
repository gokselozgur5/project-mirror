# Delivery roadmap

Each phase has an observable exit condition. A demo is not complete because a
component started once.

## Phase 0 — foundation

- Versioned contracts and repository boundaries.
- Architecture, safety model, hardware plan, and decision records.
- Continuous checks that reject secrets and private media.

Exit: clean checkout passes all repository checks without hardware.

## Phase 1 — simulated gaze

Status: accepted in simulation. See the
[measured evidence](evidence/phase1-simulation.md).

- Synthetic face-direction source.
- Character runtime session state.
- Bounded embodiment gateway.
- Browser avatar and simulated head consuming one pose stream.
- Latency and stale-command telemetry.

Exit: a five-minute simulation stays bounded and does not accumulate latency.

## Phase 2 — physical gaze

- ESP32 serial protocol and heartbeat.
- Pan-tilt assembly with calibrated soft limits.
- Emergency stop and neutral pose.
- Local face-direction adapter on Thor.

Exit: 100 malformed-command tests cannot exceed limits, and unplugging the host
causes a safe stop within the configured timeout.

## Phase 3 — conversation

- Local VAD and streaming STT.
- Replaceable text-brain adapter.
- TTS-only voice adapter.
- Barge-in that cancels generation, synthesis, and playback.

Exit: ten scripted conversations preserve character state and interruption
without the voice layer authoring text.

## Phase 4 — shared memory

- User-approved memory write path.
- Relevance-based retrieval with provenance.
- Inspection, correction, export, and deletion UI.
- Retention and per-user isolation tests.

Exit: every recalled fact is attributable and removable; no raw media is stored.

## Phase 5 — expressive embodiment

- Authored avatar rig with gaze, blink, jaw, and bounded expressions.
- Lip synchronization from final speech audio.
- Physical micro-gestures derived from the same expression intent.

Exit: a five-minute session remains synchronized and visually stable.

## Phase 6 — product hardening

- First-run calibration and consent flow.
- Signed firmware update path.
- Resource budgets, watchdogs, logs, and recovery.
- Deployment and enclosure documentation.

Exit: a new operator can assemble, calibrate, run, stop, and recover the system
using only published documentation.
