import httpx
import pytest
from fastapi.testclient import TestClient

from project_mirror_perception.app import app

client = TestClient(app)


def test_derived_observation_is_forwarded_without_raw_media(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={})

    monkeypatch.setattr(
        "project_mirror_perception.app.create_runtime_client",
        lambda base_url: httpx.AsyncClient(
            base_url=base_url,
            transport=httpx.MockTransport(handler),
        ),
    )
    response = client.post(
        "/v1/detections",
        json={
            "version": 1,
            "sequence": 9,
            "observed_at_ms": 1_000,
            "faces": [
                {"left": 0.5, "top": 0.0, "right": 1.0, "bottom": 0.5, "confidence": 0.9}
            ],
        },
    )

    assert response.status_code == 200
    assert len(captured) == 1
    assert set(response.json()) == {"version", "sequence", "observed_at_ms", "face"}
    assert "faces" not in response.json()


def test_runtime_unavailable_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr(
        "project_mirror_perception.app.create_runtime_client",
        lambda base_url: httpx.AsyncClient(
            base_url=base_url,
            transport=httpx.MockTransport(handler),
        ),
    )

    response = client.post(
        "/v1/detections",
        json={"version": 1, "sequence": 9, "observed_at_ms": 1_000, "faces": []},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "character runtime unavailable"


def test_non_json_runtime_rejection_uses_stable_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="proxy error", request=request)

    monkeypatch.setattr(
        "project_mirror_perception.app.create_runtime_client",
        lambda base_url: httpx.AsyncClient(
            base_url=base_url,
            transport=httpx.MockTransport(handler),
        ),
    )

    response = client.post(
        "/v1/detections",
        json={"version": 1, "sequence": 9, "observed_at_ms": 1_000, "faces": []},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "runtime rejected observation"
