import os

import httpx
from fastapi import FastAPI, HTTPException, status

from .models import FrameDetections, Observation
from .policy import FaceDirectionPolicy

app = FastAPI(title="Project Mirror Perception Adapter", version="0.1.0")
policy = FaceDirectionPolicy()


def create_runtime_client(base_url: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=base_url, timeout=1.0)


def upstream_detail(response: httpx.Response, fallback: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        return fallback
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, str):
        return detail
    return fallback


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "media": "not_retained"}


@app.post("/v1/detections", response_model=Observation)
async def detections(frame: FrameDetections) -> Observation:
    observation = policy.observe(frame)
    runtime_url = os.getenv("MIRROR_RUNTIME_URL", "http://127.0.0.1:8081")
    try:
        async with create_runtime_client(runtime_url) as client:
            response = await client.post("/v1/observation", json=observation.model_dump())
            response.raise_for_status()
    except httpx.HTTPStatusError as error:
        detail = upstream_detail(error.response, "runtime rejected observation")
        raise HTTPException(status_code=error.response.status_code, detail=detail) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="character runtime unavailable",
        ) from error
    return observation
