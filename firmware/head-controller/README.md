# Head controller firmware

This ESP32-S3 firmware is the final actuator safety boundary. It accepts
newline-delimited JSON over USB serial, clamps targets again, and detaches both
servos when the heartbeat expires.

## Bench warning

Do not connect a loaded mechanism first. Begin with servo horns removed and a
current-limited external servo supply. Never power servos from USB or the ESP32
regulator.

## Protocol

Host command:

```json
{"v":1,"seq":42,"yaw_mdeg":12500,"pitch_mdeg":-4000,"crc32":"91F71A45"}
```

Controller telemetry:

```json
{"v":1,"seq":42,"yaw_mdeg":12500,"pitch_mdeg":-4000,"mode":"tracking","reason":"pose","armed":true,"crc32":"844925C8"}
```

Explicit control command:

```json
{"v":1,"seq":43,"op":"stop","crc32":"79595F22"}
```

Messages are newline terminated and limited to 160 bytes. Angles are integer
millidegrees. The uppercase CRC-32 covers the canonical ASCII payload
`v,seq,yaw_mdeg,pitch_mdeg`; see ADR 0005 for the complete wire contract.
Control frames use the payload `v,op,seq`. Stop latches and detaches both
servos; arm clears the latch without attaching or moving them.
Commands with a stale sequence, unknown fields, invalid JSON, invalid checksum,
or out-of-range values are rejected. An oversized frame is discarded in full
until its next newline. Telemetry is also checksummed and reports the applied
mode and transition reason. No valid command for 500 ms detaches the servos and
publishes a `heartbeat_timeout` transition.

## Build

Install PlatformIO Core 6.2.0, then run:

```bash
pio run -d firmware/head-controller
```

Pins, pulse ranges, and mechanical limits are placeholders until the exact
board, servo, and linkage are measured.
