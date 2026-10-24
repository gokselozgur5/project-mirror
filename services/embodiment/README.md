# Embodiment gateway

The gateway is the only host service allowed to address physical embodiment
adapters. It validates freshness and sequence, clamps pose, rate-limits motion,
and returns to neutral after command expiry.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e 'services/embodiment[dev]'
uvicorn project_mirror_embodiment.app:app --reload --port 8080
```

Send a pose target:

```bash
curl -X POST http://127.0.0.1:8080/v1/pose \
  -H 'content-type: application/json' \
  -d '{"version":1,"sequence":1,"issued_at_ms":0,"ttl_ms":500,"yaw_deg":15,"pitch_deg":-5}'
```

Use a real current Unix millisecond timestamp for normal clients. Timestamp `0`
is only accepted in tests that inject their own clock.
