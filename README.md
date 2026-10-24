# Project Mirror

Project Mirror is an open, local-first embodied character platform. One
character can inhabit a browser avatar and a small pan-tilt desktop robot while
sharing perception, conversation state, memory, and behavior.

The first public milestone is intentionally small: a camera detects a person,
a simulated head turns toward them, and the browser renders the same pose. The
same bounded command contract will later drive two physical servos.

```text
camera / microphone
        |
        v
 perception ----> event bus ----> character runtime ----> speech
                         |                |
                         |                +----> memory
                         v
                embodiment gateway
                   /           \
          browser avatar     ESP32 head
```

## Principles

- Local perception by default; raw camera and microphone streams are not
  uploaded or retained.
- One character state, multiple embodiments.
- The robot is safe when the network, model, or application fails.
- Every actuator command is bounded below the hardware layer.
- Models are adapters, not the architecture.
- Simulation comes before physical motion.

## Repository map

```text
apps/avatar-web/          Browser avatar and operator console
services/runtime/         Character state and orchestration
services/perception/      Camera, voice activity, and tracking adapters
services/embodiment/      Safe motion gateway for simulated and physical heads
firmware/head-controller/ ESP32 servo controller
packages/contracts/       Versioned cross-process messages
docs/                     Architecture, hardware, safety, and delivery gates
```

## Delivery phases

1. Simulated gaze: one command moves both the virtual and simulated heads.
2. Physical gaze: an ESP32 pan-tilt head follows a consenting participant.
3. Conversation: separate STT, text brain, and TTS components with interruption.
4. Shared memory: explicit, inspectable, and deletable memories.
5. Live character: synchronized avatar expression, speech, and physical motion.

See [the roadmap](docs/ROADMAP.md) for measurable exit conditions.

## Current status

The repository begins with architecture and contracts. The first implementation
target is a hardware-free simulator so control semantics can be tested before a
servo is powered.

## Safety boundary

Project Mirror is designed for a consensual desktop interaction. It must not be
used for covert surveillance, impersonation, biometric identification, or
unattended safety-critical control. Read [SAFETY.md](docs/SAFETY.md) before
connecting actuators.

## License

MIT for original source in this repository. Models, voices, assets, and hardware
SDKs keep their own licenses.
