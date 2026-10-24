# Project Mirror

[![CI](https://github.com/gokselozgur5/project-mirror/actions/workflows/ci.yml/badge.svg)](https://github.com/gokselozgur5/project-mirror/actions/workflows/ci.yml)
[![Dependency audit](https://github.com/gokselozgur5/project-mirror/actions/workflows/security.yml/badge.svg)](https://github.com/gokselozgur5/project-mirror/actions/workflows/security.yml)

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
apps/operator-web/        Browser avatar and operator console
services/runtime/         Character state and orchestration
services/perception/      Derived face-box selection and tracking adapter
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

Phase 1 is accepted as a hardware-free vertical slice. Synthetic face boxes
pass through the perception adapter, character runtime, bounded embodiment
gateway, and browser operator view. Phase 2's host and ESP32-S3 protocol path is
implemented and fake-tested, including CRC32 frames, reconnect synchronization,
controller telemetry, startup stop, arm acknowledgement, heartbeat detach, and
fail-closed link handling. Firmware compiles, but none of this has been proven
on a physical board or servo.

## Quick start

Prerequisites are Python 3.11 or newer, uv 0.11.8, Node.js 22 or newer, and
`curl`. The repository includes `.python-version` and `.nvmrc` hints matching
CI's baseline runtimes.

```bash
make bootstrap
make check
make audit
```

`make audit` checks the locked Python and npm dependency graphs against their
current vulnerability advisories; the same audit also runs on a weekly schedule.

Start the gateway, runtime, optional derived-perception adapter, and web
operator in separate terminals:

```bash
make run-gateway
make run-runtime
make run-perception
npm run dev:web
```

Or start the complete simulation with one foreground command:

```bash
make dev
```

It prints the local operator URL, keeps logs under ignored `runtime/`, and stops
all four processes on `Ctrl-C`.

The perception service currently accepts derived boxes from tests or a future
local detector; it does not open a camera.

With the stack running, `make simulate` drives the complete derived-perception
path until `Ctrl-C`.

Run the automated five-minute Phase 1 acceptance test with:

```bash
make phase1-soak
```

See [the operator runbook](docs/RUNBOOK.md) for health checks, stop and recovery
behavior, telemetry, and troubleshooting. The latest measured Phase 1 result is
recorded in [the simulation evidence](docs/evidence/phase1-simulation.md). Start
future development sessions with [the current status](docs/STATUS.md).
Physical work must follow [the gated bench plan](docs/BENCH_PLAN.md).
The controller-only Gate 1 protocol sequence is automated by
`scripts/run-controller-gate-one.py`; its mandatory confirmation flag is not
permission to connect a servo.

## Safety boundary

Project Mirror is designed for a consensual desktop interaction. It must not be
used for covert surveillance, impersonation, biometric identification, or
unattended safety-critical control. Read [SAFETY.md](docs/SAFETY.md) before
connecting actuators.

## License

MIT for original source in this repository. Models, voices, assets, and hardware
SDKs keep their own licenses.
