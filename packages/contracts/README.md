# Contracts

These JSON Schemas are the language-neutral boundary between services. Additive
changes keep the current version; incompatible changes require a new schema
version and an explicit migration.

- `observation.v1.json`: minimal derived perception state.
- `pose-target.v1.json`: high-level pose request sent to the safe gateway.
- `embodiment-state.v1.json`: bounded state published to all embodiments.

Raw camera and microphone data do not belong in these messages.
