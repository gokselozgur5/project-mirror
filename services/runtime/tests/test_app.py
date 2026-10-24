import httpx
import pytest
from fastapi.testclient import TestClient

from project_mirror_runtime.app import app

client = TestClient(app)


def observation() -> dict[str, object]:
    return {
        "version": 1,
        "sequence": 7,
        "observed_at_ms": 1_000,
        "face": {"x": 0.5, "y": -0.5, "confidence": 0.9},
    }


def install_gateway(
    monkeypatch: pytest.MonkeyPatch,
    handler: httpx.MockTransport,
) -> None:
    monkeypatch.setattr(
        "project_mirror_runtime.app.create_gateway_client",
        lambda base_url: httpx.AsyncClient(base_url=base_url, transport=handler),
    )


def test_observation_forwards_pose_and_control_token(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={})

    install_gateway(monkeypatch, httpx.MockTransport(handler))
    monkeypatch.setenv("MIRROR_GATEWAY_TOKEN", "test-control-token")

    response = client.post("/v1/observation", json=observation())

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert len(captured) == 1
    assert captured[0].headers["authorization"] == "Bearer test-control-token"
    assert captured[0].url.path == "/v1/pose"


def test_gateway_rejection_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={"detail": "operator stop is latched"},
            request=request,
        )

    install_gateway(monkeypatch, httpx.MockTransport(handler))

    response = client.post("/v1/observation", json=observation())

    assert response.status_code == 409
    assert response.json()["detail"] == "operator stop is latched"


def test_gateway_connection_failure_becomes_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    install_gateway(monkeypatch, httpx.MockTransport(handler))

    response = client.post("/v1/observation", json=observation())

    assert response.status_code == 503
    assert response.json()["detail"] == "embodiment gateway unavailable"


def test_non_json_gateway_rejection_uses_stable_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="proxy error", request=request)

    install_gateway(monkeypatch, httpx.MockTransport(handler))

    response = client.post("/v1/observation", json=observation())

    assert response.status_code == 502
    assert response.json()["detail"] == "gateway rejected pose"


def test_ignored_observation_does_not_call_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"unexpected gateway request: {request.url}")

    install_gateway(monkeypatch, httpx.MockTransport(handler))
    payload = observation()
    payload["face"] = None

    response = client.post("/v1/observation", json=payload)

    assert response.status_code == 200
    assert response.json() == {"accepted": False, "reason": "no_face", "pose": None}
