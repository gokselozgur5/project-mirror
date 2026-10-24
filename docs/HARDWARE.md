# Hardware plan

## Prototype bill of materials

| Part | Initial choice | Reason |
| --- | --- | --- |
| Edge computer | Jetson AGX Thor | Existing local AI host |
| Motor controller | ESP32-S3 development board | USB serial, watchdog, wide ecosystem |
| Pan and tilt | Two metal-gear digital servos | Repeatable position control |
| Servo power | Dedicated regulated 5–6 V supply | Isolates motor transients from logic |
| Camera | Existing UVC webcam | Standard local capture |
| Audio | Existing USB microphone/speaker | Keeps phase one inexpensive |
| Emergency stop | Latching inline servo-power switch | Hardware stop independent of software |
| Frame | Off-the-shelf pan-tilt bracket | Fast calibration and replacement |

Exact parts are selected only after measuring payload mass, center of gravity,
required angular speed, stall current, noise, and available enclosure space.

## Electrical rules

- Never power servos from the ESP32 regulator or USB rail.
- Join logic and servo grounds at the intended common point.
- Size the supply for measured simultaneous stall current plus margin.
- Add bulk capacitance near the servo power input.
- Route power away from microphone and camera cables.
- Use a physical power cut for actuators during development.

## Mechanical rules

- Establish hard geometry limits before energizing a servo.
- Configure narrower software limits than the mechanical range.
- Start without an attached payload and at reduced velocity.
- Provide strain relief and avoid cable paths through pinch points.
- Treat every startup pose as unknown until calibration completes.

## Bench sequence

1. Validate the controller with no servos connected.
2. Validate one unloaded servo with a current-limited supply.
3. Measure direction, neutral pulse, and safe endpoints.
4. Add the second axis and verify combined stall current.
5. Attach the lightest prototype payload.
6. Run heartbeat-loss and emergency-stop tests.
7. Only then connect perception-driven commands.

Use the [physical bench plan](BENCH_PLAN.md) for gated measurements, evidence,
and explicit stop conditions.
