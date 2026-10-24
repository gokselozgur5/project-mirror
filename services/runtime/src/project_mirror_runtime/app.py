import os

import httpx
from fastapi import FastAPI, HTTPException, status

from .models import Observation, RuntimeDecision
from .policy import AttentionPolicy

app = FastAPI(title="Project Mirror Character Runtime", version="0.1.0")
policy = AttentionPolicy()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/observation", response_model=RuntimeDecision)
async def observe(observation: Observation) -> RuntimeDecision:
    decision = policy.decide(observation)
    if decision.pose is None:
        return decision

    gateway_url = os.getenv("MIRROR_GATEWAY_URL", "http://127.0.0.1:8080")
    try:
        async with httpx.AsyncClient(base_url=gateway_url, timeout=1.0) as client:
            response = await client.post("/v1/pose", json=decision.pose.model_dump())
            response.raise_for_status()
    except httpx.HTTPStatusError as error:
        detail = error.response.json().get("detail", "gateway rejected pose")
        raise HTTPException(status_code=error.response.status_code, detail=detail) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="embodiment gateway unavailable",
        ) from error
    return decision
