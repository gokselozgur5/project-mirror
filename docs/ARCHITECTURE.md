# Architecture

## Context

Project Mirror separates perception, character behavior, and embodiment. This
keeps a model failure from becoming a motor command and lets one character drive
multiple visual or physical forms.

## Runtime topology

```text
┌───────────────┐    observations    ┌───────────────────┐
│ Perception    │ ─────────────────> │ Character runtime │
│ face/VAD/STT  │                    │ policy + state     │
└───────────────┘                    └─────────┬─────────┘
                                             │ intent
                    ┌────────────────────────┼───────────────────────┐
                    v                        v                       v
             ┌────────────┐           ┌────────────┐         ┌───────────┐
             │ Speech     │           │ Memory     │         │ Embodiment│
             │ TTS only   │           │ explicit   │         │ gateway   │
             └────────────┘           └────────────┘         └─────┬─────┘
                                                                  │ bounded pose
                                                        ┌─────────┴─────────┐
                                                        v                   v
                                                 Browser avatar       ESP32 firmware
```

## Components

### Perception

Produces observations such as normalized face direction, voice activity, and
transcript segments. It does not decide how the character should behave and
does not persist raw media by default.

### Character runtime

Owns the session state machine, turn taking, interruption, expression intent,
and model adapters. Text generation is separate from speech synthesis. A voice
provider reads approved text; it does not author the response.

### Memory

Stores structured facts with provenance, scope, confidence, and retention.
Retrieval is query-relevant rather than a fixed list of recent memories. Every
record can be inspected and deleted.

### Embodiment gateway

Converts high-level intent into bounded pose targets. It owns mechanical limits,
velocity and acceleration limits, stale-command rejection, heartbeat timeout,
and emergency neutral behavior. Model output never bypasses it.

### Browser avatar

Renders the same canonical pose and expression state used by the physical head.
It is also the first operator console: connection state, latency, sensor consent,
and emergency stop remain visible.

### Head controller

An ESP32 receives already-bounded targets and applies a final independent clamp.
It returns telemetry and enters neutral/off state after heartbeat loss.

## Data planes

- Control plane: configuration, consent, session lifecycle, and health.
- Realtime plane: observations, pose targets, expressions, and interruption.
- Media plane: local camera and audio frames; never placed on the event bus.
- Memory plane: explicit structured records; isolated from raw recordings.

## Deployment

Development runs every service on one machine with simulated hardware.
The target deployment places perception and character services on Jetson AGX
Thor, the avatar in a browser, and actuator control on ESP32 over USB serial.

## Failure behavior

- Lost perception: ease toward neutral; do not search aggressively.
- Lost runtime: gateway expires the command and requests neutral.
- Lost gateway heartbeat: firmware stops or detaches servos.
- Invalid command: reject and emit a structured diagnostic.
- Model timeout: remain silent or use an authored fallback; do not fabricate a
  successful action.
