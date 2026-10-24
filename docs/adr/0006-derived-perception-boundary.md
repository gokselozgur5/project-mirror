# ADR 0006: Derived perception crosses the service boundary

## Status

Accepted.

## Context

The character needs face direction but does not need camera pixels. Sending raw
frames through the service graph would enlarge the privacy, memory, logging,
and network failure surface and couple the system to one detector.

## Decision

Camera capture and model inference remain inside a local detector adapter. Only
normalized face boxes, confidence, source sequence, and observation time may
enter the perception service. The service selects one attention target and
publishes the versioned observation contract containing normalized direction,
not the original boxes or frame.

The initial deterministic selection policy chooses the largest box above the
confidence threshold, using confidence and input order as tie-breakers. This is
a testable bootstrap rule, not identity tracking. A future temporal tracker may
replace it only with explicit multiple-participant behavior and without adding
biometric recognition.

## Consequences

- Runtime, gateway, logs, and event streams never require raw frames.
- Detector implementations and accelerators remain replaceable.
- The detector process still handles sensitive media and must keep processing
  local, ephemeral, visible, and consented.
- The repository can test selection and contracts without committing a camera
  recording or model weight.
- Live Thor performance, consent UI, target stability, and detector licensing
  remain Phase 2 evidence, not assumptions.
