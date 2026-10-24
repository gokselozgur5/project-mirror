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
{"v":1,"seq":42,"yaw":12.5,"pitch":-4.0}
```

Controller telemetry:

```json
{"v":1,"seq":42,"yaw":12.5,"pitch":-4.0,"armed":true}
```

Messages are newline terminated. Commands with a stale sequence, unknown
fields, invalid JSON, or non-finite values are rejected. No valid command for
500 ms detaches the servos.

## Build

Install PlatformIO Core 6.2.0, then run:

```bash
pio run -d firmware/head-controller
```

Pins, pulse ranges, and mechanical limits are placeholders until the exact
board, servo, and linkage are measured.
