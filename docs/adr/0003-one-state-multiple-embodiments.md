# ADR 0003: Use one canonical character state

- Status: accepted
- Date: 2026-10-24

## Context

Independent logic for the browser avatar and physical head would drift, race,
and express conflicting behavior.

## Decision

The runtime publishes one canonical pose, expression, speaking, and attention
state. Each embodiment adapts that state to its capabilities without inventing
new character decisions.

## Consequences

- Virtual and physical forms remain synchronized.
- Capability negotiation is required for simpler hardware.
- Replays and simulation can use the same event stream.
