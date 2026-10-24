from time import time_ns

from fastapi.testclient import TestClient

from project_mirror_embodiment.app import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_pose_endpoint_clamps_values() -> None:
    now_ms = time_ns() // 1_000_000
    response = client.post(
        "/v1/pose",
        json={
            "version": 1,
            "sequence": 100,
            "issued_at_ms": now_ms,
            "ttl_ms": 500,
            "yaw_deg": -120,
            "pitch_deg": 70,
        },
    )

    assert response.status_code == 200
    assert -55 <= response.json()["yaw_deg"] <= 55
    assert -25 <= response.json()["pitch_deg"] <= 25


def test_metrics_endpoint() -> None:
    response = client.get("/v1/metrics")

    assert response.status_code == 200
    assert response.json()["accepted_commands"] >= 1


def test_stop_requires_explicit_arm_before_pose() -> None:
    client.post("/v1/stop")
    now_ms = time_ns() // 1_000_000
    blocked = client.post(
        "/v1/pose",
        json={
            "version": 1,
            "sequence": 101,
            "issued_at_ms": now_ms,
            "ttl_ms": 500,
            "yaw_deg": 0,
            "pitch_deg": 0,
        },
    )

    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "operator stop is latched"
    assert client.post("/v1/arm").status_code == 200
    assert (
        client.post(
            "/v1/pose",
            json={
                "version": 1,
                "sequence": 101,
                "issued_at_ms": time_ns() // 1_000_000,
                "ttl_ms": 500,
                "yaw_deg": 0,
                "pitch_deg": 0,
            },
        ).status_code
        == 200
    )
