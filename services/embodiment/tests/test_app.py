from time import sleep, time_ns

import pytest
from fastapi.testclient import TestClient

from project_mirror_embodiment.app import (
    accept_controller_telemetry,
    app,
    gateway,
    mark_controller_telemetry_stale,
)
from project_mirror_embodiment.models import ControllerLinkState, ControllerStatus
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
        self.handshake_sent = False

    def close(self) -> None:
        self.closed = True

    def read_frame(self) -> bytes:
        if not self.handshake_sent:
            self.handshake_sent = True
            return (
                b'{"v":1,"seq":0,"yaw_mdeg":0,"pitch_mdeg":0,'
                b'"mode":"neutral","reason":"startup","armed":false,'
                b'"crc32":"5799F42D"}\n'
            )
        sleep(0.01)
        return b""


class InvalidHandshakeStream(ClosableMemoryStream):
    def read_frame(self) -> bytes:
        return b"damaged\n"


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["controller"] == "simulated"
    assert client.get("/v1/controller").json()["link_state"] == "simulated"


def test_serial_device_is_opt_in_and_closed_on_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    device = ClosableMemoryStream()
    monkeypatch.setenv("MIRROR_SERIAL_PORT", "/dev/test-controller")
    monkeypatch.setenv("MIRROR_CONTROL_TOKEN", "test-control-token")
    monkeypatch.setattr(
        "project_mirror_embodiment.app.SerialDevice",
        lambda port: device,
    )

    with TestClient(app) as configured_client:
        assert configured_client.get("/health").json()["controller"] == "serial"
        assert configured_client.get("/v1/controller").json()["last_sequence"] == 0

    assert decode_control_command(device.frames[0]).op == "status"
    assert device.closed is True
    assert app.state.controller is None


def test_serial_mode_refuses_to_start_without_control_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MIRROR_SERIAL_PORT", "/dev/test-controller")
    monkeypatch.delenv("MIRROR_CONTROL_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="MIRROR_CONTROL_TOKEN"), TestClient(app):
        pass


def test_serial_mode_closes_device_after_invalid_handshake(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = InvalidHandshakeStream()
    monkeypatch.setenv("MIRROR_SERIAL_PORT", "/dev/test-controller")
    monkeypatch.setenv("MIRROR_CONTROL_TOKEN", "test-control-token")
    monkeypatch.setattr(
        "project_mirror_embodiment.app.SerialDevice",
        lambda port: device,
    )

    with pytest.raises(RuntimeError, match="invalid status handshake"), TestClient(app):
        pass

    assert device.closed is True


def test_pose_and_arm_require_configured_bearer_but_stop_remains_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MIRROR_CONTROL_TOKEN", "test-control-token")

    assert client.post("/v1/arm").status_code == 401
    assert client.post("/v1/stop").status_code == 200
    assert (
        client.post(
            "/v1/arm",
            headers={"authorization": "Bearer test-control-token"},
        ).status_code
        == 200
    )


def test_empty_control_token_keeps_simulation_unauthenticated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MIRROR_CONTROL_TOKEN", "")

    assert client.post("/v1/arm").status_code == 200


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


def test_controller_telemetry_updates_link_status_and_counts_invalid_frames() -> None:
    stream = MemoryStream()
    transport = HeadControllerTransport(stream)
    transport.publish_pose(gateway.state().model_copy(update={"sequence": 1}))
    app.state.controller_status = ControllerStatus(
        configured=True,
        link_state=ControllerLinkState.AWAITING_TELEMETRY,
    )
    frame = (
        b'{"v":1,"seq":1,"yaw_mdeg":12500,"pitch_mdeg":-4000,'
        b'"mode":"tracking","reason":"pose","armed":true,"crc32":"FDF9E1F0"}\n'
    )

    accept_controller_telemetry(app, transport, frame)
    assert app.state.controller_status.link_state == "online"
    assert app.state.controller_status.last_sequence == 1

    accept_controller_telemetry(app, transport, b"damaged\n")
    assert app.state.controller_status.link_state == "invalid_telemetry"
    assert app.state.controller_status.invalid_frames == 1

    app.state.controller_status = ControllerStatus(
        configured=False,
        link_state=ControllerLinkState.SIMULATED,
    )


def test_silent_controller_becomes_stale_and_health_degrades() -> None:
    app.state.controller_status = ControllerStatus(
        configured=True,
        link_state=ControllerLinkState.ONLINE,
        last_sequence=4,
        last_received_at_ms=1_000,
    )

    mark_controller_telemetry_stale(app, now_ms=2_001)

    assert client.get("/v1/controller").json()["link_state"] == "stale"
    assert client.get("/health").json()["status"] == "degraded"
    app.state.controller_status = ControllerStatus(
        configured=False,
        link_state=ControllerLinkState.SIMULATED,
    )
