# Physical bench plan

This plan starts only after the simulator is green. It is evidence collection,
not permission to attach a mechanism. Stop at the first failed gate.

## Required equipment

- ESP32-S3 board with a data-capable USB cable.
- Current-limited, regulated servo supply with visible voltage and current.
- Multimeter and, preferably, an oscilloscope or logic analyzer.
- Latching actuator-power switch reachable without software.
- One unloaded servo, then a second servo, then the lightest test payload.
- Fixed camera or ruler for repeatable angle measurements.

Never power a servo from USB or the ESP32 regulator. Keep servo horns and the
mechanism disconnected through Gate 1.

## Evidence header

Record this before every powered run:

```text
date/time:
operator:
git revision:
firmware environment:
board and USB identity:
servo model and quantity:
supply model, voltage, and current limit:
mechanism/payload state:
configured pin, pulse, position, velocity, acceleration, and timeout limits:
physical stop verified reachable: yes/no
```

Photographs and recordings may contain private material. Keep them outside Git
and reference only a private evidence identifier in public results.

## Gate 1 — controller only

No servos or mechanism connected.

1. Build native protocol tests and firmware with `make firmware`.
2. Flash the exact recorded revision.
3. Confirm startup leaves servo outputs detached.
4. Run the guarded protocol harness, substituting the exact serial path:

   ```sh
   .venv/bin/python scripts/run-controller-gate-one.py \
     --port /dev/cu.usbmodem-EXACT \
     --confirm-servos-disconnected
   ```

   It verifies status synchronization, valid stop, rejection of all 100
   malformed frames, parser recovery, arm acknowledgement, a neutral pose,
   heartbeat detach within the 800 ms bench deadline, and final stop. It prints
   the measured heartbeat observation time in a machine-readable JSON result
   and attempts a final stop if the run aborts.
5. Independently confirm that no malformed frame activated an output using the
   attached logic analyzer; a lack of telemetry alone is not physical proof.
6. Disconnect USB during traffic and verify outputs become inactive.

Exit: no malformed input activates outputs; stop is latched; heartbeat and USB
loss detach within the configured bound; Python and captured board telemetry
agree on CRC vectors.

## Gate 2 — one unloaded servo

Remove the horn. Set a conservative supply current limit.

1. Verify common ground and actuator-power stop with logic power present.
2. Measure actual neutral pulse before connecting the servo signal.
3. Connect one axis and command neutral only.
4. Establish direction and safe pulse endpoints in small increments.
5. Measure idle, motion, reversal, and stall current without holding a stall.
6. Trigger software stop, heartbeat loss, USB loss, and physical power stop.

Exit: measured direction, neutral, endpoints, current, temperature, noise, and
stop behavior are recorded. Firmware placeholders are not changed until these
measurements exist.

## Gate 3 — two unloaded axes

1. Repeat Gate 2 for the second axis independently.
2. Exercise simultaneous starts and reversals.
3. Measure supply droop, controller resets, USB errors, and combined peak
   current.
4. Verify cable travel and strain relief across the full conservative envelope.

Exit: the supply remains stable with margin and every failure path stops both
axes without exceeding limits.

## Gate 4 — lightest mechanism

1. Attach the lightest non-private test payload with actuator power removed.
2. Recalculate center of gravity, required torque, and pinch/cable hazards.
3. Reduce limits before the first powered movement.
4. Calibrate software limits inside measured mechanical clearance.
5. Run scripted motion, stop, timeout, restart, and disconnect cases.

Exit: one hundred malformed cases, repeated disconnects, and a five-minute
bounded tracking session produce no limit violation, reset, thermal issue, or
uncontrolled movement.

## Stop conditions

Cut actuator power immediately for unexpected direction, chatter, heat, supply
droop, controller reset, cable snag, checksum disagreement, stale telemetry, or
any motion after stop/timeout. Preserve only non-private diagnostic metadata,
correct the cause, and restart from the previous gate.
