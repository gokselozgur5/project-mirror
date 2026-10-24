# ADR 0001: Separate cognition from embodiment

- Status: accepted
- Date: 2026-10-24

## Context

A language or behavior model can be slow, unavailable, or produce malformed
output. Physical motion must remain bounded under all of those conditions.

## Decision

The character runtime emits high-level intent. A deterministic embodiment
gateway owns pose limits, dynamics, expiry, and emergency behavior. Firmware
applies an independent final clamp and heartbeat timeout.

## Consequences

- Model providers can change without changing the motor protocol.
- Browser and physical embodiments consume the same canonical state.
- Some expressive motion is intentionally rejected or softened.
- Gateway and firmware tests are safety gates, not optional unit tests.
