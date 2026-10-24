from time import time_ns

import pytest
from fastapi.testclient import TestClient

from project_mirror_embodiment.app import app, gateway
from project_mirror_embodiment.serial_protocol import (
    decode_control_command,
    decode_pose_command,
)
from project_mirror_embodiment.serial_transport import HeadControllerTransport

client = TestClient(app)


class MemoryStream:
    def __init__(self) -> None:
        self.frames: list[bytes] = []

    def write(self, data: bytes) -> int:
        self.frames.append(data)
        return len(data)


class ShortWriteStream:
    def write(self, data: bytes) -> int:
        return len(data) - 1


class ClosableMemoryStream(MemoryStream):
    def __init__(self) -> None:
        super().__init__()
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["controller"] == "simulated"


def test_serial_device_is_opt_in_and_closed_on_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    device = ClosableMemoryStream()
    monkeypatch.setenv("MIRROR_SERIAL_PORT", "/dev/test-controller")
    monkeypatch.setattr(
        "project_mirror_embodiment.app.SerialDevice",
        lambda port: device,
    )

    with TestClient(app) as configured_client:
        assert configured_client.get("/health").json()["controller"] == "serial"

    assert device.closed is True
    assert app.state.controller is None


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


def test_configured_controller_receives_pose_stop_and_arm() -> None:
    stream = MemoryStream()
    app.state.controller = HeadControllerTransport(stream)
    client.post("/v1/arm")
    next_sequence = gateway.state().sequence + 1

    try:
        pose = client.post(
            "/v1/pose",
            json={
                "version": 1,
                "sequence": next_sequence,
                "issued_at_ms": time_ns() // 1_000_000,
                "ttl_ms": 500,
                "yaw_deg": 10,
                "pitch_deg": -5,
            },
        )
        stopped = client.post("/v1/stop")
    finally:
        app.state.controller = None

    assert pose.status_code == 200
    assert stopped.status_code == 200
    assert decode_control_command(stream.frames[0]).op == "arm"
    assert decode_pose_command(stream.frames[1]).seq == 2
    assert decode_control_command(stream.frames[2]).op == "stop"


def test_controller_write_failure_latches_gateway_stop() -> None:
    app.state.controller = HeadControllerTransport(ShortWriteStream())
    try:
        response = client.post("/v1/arm")
    finally:
        app.state.controller = None

    assert response.status_code == 503
    assert gateway.state().mode == "stopped"
    assert gateway.state().reason == "controller_write_failure"
    client.post("/v1/arm")
