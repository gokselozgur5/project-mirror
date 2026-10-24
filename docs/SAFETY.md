# Safety and privacy

## Safety invariants

1. Models express intent; deterministic code controls actuators.
2. Position, velocity, and acceleration are clamped at the gateway and firmware.
3. Motion requires a fresh heartbeat and a calibrated controller.
4. Loss of communication moves to neutral or removes servo torque.
5. A physical actuator-power stop remains reachable.
6. Startup never assumes the previous physical pose and remains stop-latched
   until an explicit authenticated arm reaches both host and controller.
7. Invalid or stale controller telemetry latches a host stop and emits a
   controller stop; movement does not continue without observability.
8. Host arm remains latched until matching controller telemetry acknowledges
   the exact arm sequence and stopped-to-neutral transition.
9. A controller telemetry fault reasserts physical stop even when host state is
   already stopped; host state is not proof of controller state.
10. Physical pose acceptance requires matching controller telemetry for the
    exact sequence and applied angles; a write completing is not proof of motion.
11. An idle physical link is polled without advancing its command sequence;
    missing status telemetry still becomes stale and reasserts stop.
12. Integrated motion is clamped again at hard position limits. A hard-limit
    collision resets planned velocity; position safety takes priority over a
    smooth acceleration continuation.

## Privacy defaults

- Camera and microphone processing stays local.
- Raw media is ephemeral unless the operator explicitly records it.
- Recording state is visible to everyone in sensor range.
- Face direction is not identity; biometric recognition is outside scope.
- Memory writes require an explicit policy and remain inspectable and deletable.
- Logs contain timing and state transitions, not transcripts or media.

## Threat model

| Threat | Control |
| --- | --- |
| Malformed model output | Typed intent plus deterministic bounds |
| Compromised browser | Gateway authentication and no raw actuator access |
| Serial corruption | Framed messages, version, sequence, and checksum |
| Stale command | Monotonic sequence and expiry timestamp |
| Host crash | Firmware heartbeat timeout |
| Secret leakage | Environment injection and repository scanning |
| Private-media commit | Ignore rules and CI extension checks |
| Unannounced recording | Visible consent and recording indicators |

## Incident posture

Stop actuator power first. Preserve diagnostic metadata without copying private
media. Record the software revision, configuration, physical setup, and exact
failure transition before attempting another powered run.
