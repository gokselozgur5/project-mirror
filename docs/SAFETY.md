# Safety and privacy

## Safety invariants

1. Models express intent; deterministic code controls actuators.
2. Position, velocity, and acceleration are clamped at the gateway and firmware.
3. Motion requires a fresh heartbeat and a calibrated controller.
4. Loss of communication moves to neutral or removes servo torque.
5. A physical actuator-power stop remains reachable.
6. Startup never assumes the previous physical pose and remains stop-latched
   until an explicit authenticated arm reaches both host and controller.

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
