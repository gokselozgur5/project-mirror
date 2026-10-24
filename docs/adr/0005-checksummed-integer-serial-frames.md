# ADR 0005: Checksummed integer serial frames

## Status

Accepted.

## Context

USB serial is a physical control boundary. Newline-delimited floating-point JSON
is convenient to inspect, but float formatting makes an interoperable checksum
ambiguous and a damaged but parseable frame could become a valid movement.

## Decision

The host sends one compact JSON object per newline. Angles use signed integer
millidegrees. Each command includes an uppercase, eight-digit CRC-32 over the
ASCII bytes of this canonical payload:

```text
v,seq,yaw_mdeg,pitch_mdeg
```

For example, command sequence 42 at 12.5 degrees yaw and -4 degrees pitch uses
`1,42,12500,-4000` as its checksum payload. The maximum frame length is 160
bytes. Unknown fields, unsupported versions, stale sequences, out-of-range
integer angles, invalid checksums, oversized frames, and non-terminated frames
are rejected.

Explicit control frames carry `op` instead of angles. Their checksum payload is
`v,op,seq`, for example `1,stop,43`. A stop latches the controller and detaches
the servos. Arm only clears that latch; it does not attach or move a servo.
Status uses `1,status,0`, never changes motion or refreshes the heartbeat, and
returns current telemetry. A newly opened host transport must complete this
handshake and continue above the controller's reported sequence before it can
publish pose, stop, or arm.

Telemetry uses the canonical payload
`v,telemetry,seq,yaw_mdeg,pitch_mdeg,mode,reason,armed`, where `armed` is `0` or
`1`. It reports the last applied command sequence and emits explicit pose,
operator-stop, operator-arm, and heartbeat-timeout transitions.

CRC detects accidental corruption; it does not authenticate a host. Physical
access, host authorization, and a hardware actuator-power stop remain separate
controls.

## Consequences

- Python and firmware can compute identical checksums without float formatting.
- Millidegree resolution is far finer than the expected mechanical resolution.
- The firmware still applies its own position limits after parsing.
- Any wire-format change requires a new protocol version and contract.
