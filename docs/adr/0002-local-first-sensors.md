# ADR 0002: Keep raw sensors local by default

- Status: accepted
- Date: 2026-10-24

## Context

Camera and microphone streams carry more information than the character needs.
Sending or retaining raw media creates unnecessary privacy and security risk.

## Decision

Perception runs on the local edge host. Other components receive derived,
minimal observations. Raw recording is a separate, visible, opt-in operation.

## Consequences

- Basic gaze and interruption work without cloud access.
- Remote model APIs, when enabled, receive bounded text rather than raw media.
- Edge deployment and observability require more engineering.
