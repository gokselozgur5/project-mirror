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
    assert response.json()["yaw_deg"] == -55
    assert response.json()["pitch_deg"] == 25
