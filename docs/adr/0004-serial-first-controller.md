# ADR 0004: Start with a USB serial motor link

- Status: accepted
- Date: 2026-10-24

## Context

Wireless control adds pairing, authentication, interference, and availability
failure modes before physical safety has been demonstrated.

## Decision

The first controller uses USB serial with newline-delimited, versioned commands,
monotonic sequence numbers, bounded values, and a firmware heartbeat timeout.

## Consequences

- Bench behavior is observable with standard tools.
- Power and data remain conceptually separate even when USB carries data.
- A future wireless transport must preserve the same safety semantics and add
  authentication before it can replace serial.
