# Contributing

Keep pull requests small and independently verifiable. Describe the behavior
change, the evidence used to validate it, and any safety boundary affected.

## Commit convention

Use Conventional Commits with an imperative summary:

```text
feat(runtime): publish bounded pose state
fix(firmware): stop servos after heartbeat loss
docs(adr): record transport decision
```

Do not put issue numbers in source comments. Comments explain invariants and
intent; the issue tracker preserves project history.

## Definition of done

- Tests and static checks pass for every touched component.
- New external messages are versioned in `packages/contracts`.
- Hardware changes include a simulation or bench-test path.
- No private media, credentials, model weights, or generated recordings enter
  Git history.
- Safety limits remain enforced below model-controlled code.
