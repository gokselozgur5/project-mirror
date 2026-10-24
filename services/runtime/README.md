# Character runtime

The Phase 1 runtime turns minimal perception observations into high-level pose
intent. It does not own mechanical limits and cannot address firmware directly.
Every accepted intent passes through the embodiment gateway.

```bash
export MIRROR_GATEWAY_URL=http://127.0.0.1:8080
export MIRROR_GATEWAY_TOKEN=replace-with-the-control-token # physical controller only
uvicorn project_mirror_runtime.app:app --port 8081
```

Leave `MIRROR_GATEWAY_TOKEN` unset in the default simulation. When the gateway
has a physical controller, it requires the token and the runtime sends it only
as an authorization header.

The initial policy tracks one normalized face direction above a confidence
threshold. Missing or weak observations are ignored so the gateway heartbeat
returns the embodiments to neutral.
