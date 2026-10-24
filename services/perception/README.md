# Perception adapter

This service accepts derived, normalized face boxes from a local detector,
selects one deterministic attention target, and forwards only face direction
and confidence to the character runtime. Its API has no raw image field and it
does not retain media.

```bash
export MIRROR_RUNTIME_URL=http://127.0.0.1:8081
uv run uvicorn project_mirror_perception.app:app --port 8082
```

No camera or detector backend is selected yet. That choice requires measured
Thor performance, model-license review, multiple-face behavior, and explicit
sensor consent.
