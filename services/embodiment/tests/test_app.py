import json
import zlib
from threading import Thread
from time import sleep, time_ns

import pytest
from fastapi.testclient import TestClient

from project_mirror_embodiment.app import (
    accept_controller_telemetry,
    app,
    gateway,
    mark_controller_telemetry_stale,
    poll_controller_status_if_due,
)
from project_mirror_embodiment.models import ControllerLinkState, ControllerStatus, MotionMode
from project_mirror_embodiment.serial_protocol import (
    decode_control_command,
    decode_pose_command,
)
from project_mirror_embodiment.serial_transport import HeadControllerTransport

client = TestClient(app)
PHYSICAL_TOKEN = "test-control-token-with-32-characters"


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
                b'"mode":"stopped","reason":"startup","armed":false,'
                b'"crc32":"F961637E"}\n'
            )
        if len(self.frames) == 2:
            return (
                b'{"v":1,"seq":1,"yaw_mdeg":0,"pitch_mdeg":0,'
                b'"mode":"stopped","reason":"operator_stop","armed":false,'
                b'"crc32":"0B82AC3C"}\n'
            )
        sleep(0.01)
        return b""


class InvalidHandshakeStream(ClosableMemoryStream):
    def read_frame(self) -> bytes:
        return b"damaged\n"


class WrongStartupStopStream(ClosableMemoryStream):
    def read_frame(self) -> bytes:
        if not self.handshake_sent:
            self.handshake_sent = True
            return telemetry_frame(0, 0, 0, "stopped", "startup", False)
        return telemetry_frame(1, 0, 0, "stopped", "startup", False)


def telemetry_frame(
    sequence: int,
    yaw_mdeg: int,
    pitch_mdeg: int,
    mode: str,
    reason: str,
    armed: bool,
) -> bytes:
    armed_value = 1 if armed else 0
    payload = (
        f"1,telemetry,{sequence},{yaw_mdeg},{pitch_mdeg},{mode},{reason},{armed_value}"
    )
    frame = {
        "v": 1,
        "seq": sequence,
        "yaw_mdeg": yaw_mdeg,
        "pitch_mdeg": pitch_mdeg,
        "mode": mode,
        "reason": reason,
        "armed": armed,
        "crc32": f"{zlib.crc32(payload.encode('ascii')):08X}",
    }
    return json.dumps(frame, separators=(",", ":")).encode("ascii") + b"\n"


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["controller"] == "simulated"
    assert client.get("/v1/controller").json()["link_state"] == "simulated"


def test_serial_device_is_opt_in_and_closed_on_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    device = ClosableMemoryStream()
    monkeypatch.setenv("MIRROR_SERIAL_PORT", "/dev/test-controller")
    monkeypatch.setenv("MIRROR_CONTROL_TOKEN", PHYSICAL_TOKEN)
    monkeypatch.setattr(
        "project_mirror_embodiment.app.SerialDevice",
        lambda port: device,
    )

    with TestClient(app) as configured_client:
        assert configured_client.get("/health").json()["controller"] == "serial"
        assert configured_client.get("/v1/controller").json()["last_sequence"] == 1
        assert configured_client.get("/v1/state").json()["mode"] == "stopped"

    assert decode_control_command(device.frames[0]).op == "status"
    assert decode_control_command(device.frames[1]).op == "stop"
    assert device.closed is True
    assert app.state.controller is None
    gateway.arm()


def test_serial_mode_refuses_to_start_without_control_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MIRROR_SERIAL_PORT", "/dev/test-controller")
    monkeypatch.delenv("MIRROR_CONTROL_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="MIRROR_CONTROL_TOKEN"), TestClient(app):
        pass


def test_serial_mode_refuses_short_control_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIRROR_SERIAL_PORT", "/dev/test-controller")
    monkeypatch.setenv("MIRROR_CONTROL_TOKEN", "too-short")

    with pytest.raises(RuntimeError, match="at least 32"), TestClient(app):
        pass


def test_serial_mode_closes_device_after_invalid_handshake(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = InvalidHandshakeStream()
    monkeypatch.setenv("MIRROR_SERIAL_PORT", "/dev/test-controller")
    monkeypatch.setenv("MIRROR_CONTROL_TOKEN", PHYSICAL_TOKEN)
    monkeypatch.setattr(
        "project_mirror_embodiment.app.SerialDevice",
        lambda port: device,
    )

    with pytest.raises(RuntimeError, match="invalid status handshake"), TestClient(app):
        pass

    assert device.closed is True


def test_serial_mode_rejects_wrong_startup_stop_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = WrongStartupStopStream()
    monkeypatch.setenv("MIRROR_SERIAL_PORT", "/dev/test-controller")
    monkeypatch.setenv("MIRROR_CONTROL_TOKEN", PHYSICAL_TOKEN)
    monkeypatch.setattr(
        "project_mirror_embodiment.app.SerialDevice",
        lambda port: device,
    )

    with pytest.raises(RuntimeError, match="stopped startup state"), TestClient(app):
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


def test_physical_arm_is_blocked_while_telemetry_is_not_online() -> None:
    app.state.controller = HeadControllerTransport(MemoryStream())
    app.state.controller_status = ControllerStatus(
        configured=True,
        link_state=ControllerLinkState.STALE,
    )
    try:
        response = client.post("/v1/arm")
    finally:
        app.state.controller = None
        app.state.controller_status = ControllerStatus(
            configured=False,
            link_state=ControllerLinkState.SIMULATED,
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "physical controller telemetry is not online"


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


def test_configured_controller_receives_pose_and_stop() -> None:
    stream = MemoryStream()
    transport = HeadControllerTransport(stream)
    app.state.controller = transport
    app.state.controller_status = ControllerStatus(
        configured=True,
        link_state=ControllerLinkState.ONLINE,
    )
    gateway.arm()
    next_sequence = gateway.state().sequence + 1

    def acknowledge_pose() -> None:
        while not stream.frames:
            sleep(0.001)
        command = decode_pose_command(stream.frames[0])
        transport.accept_telemetry(
            telemetry_frame(
                command.seq,
                command.yaw_mdeg,
                command.pitch_mdeg,
                "tracking",
                "pose",
                True,
            )
        )

    acknowledgement = Thread(target=acknowledge_pose)
    acknowledgement.start()

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
        acknowledgement.join(timeout=1)
        app.state.controller = None
        app.state.controller_status = ControllerStatus(
            configured=False,
            link_state=ControllerLinkState.SIMULATED,
        )

    assert pose.status_code == 200
    assert stopped.status_code == 200
    assert not acknowledgement.is_alive()
    assert decode_pose_command(stream.frames[0]).seq == 1
    assert decode_control_command(stream.frames[1]).op == "stop"
    gateway.arm()


def test_physical_pose_fails_closed_without_controller_acknowledgement() -> None:
    stream = MemoryStream()
    app.state.controller = HeadControllerTransport(stream)
    app.state.controller_status = ControllerStatus(
        configured=True,
        link_state=ControllerLinkState.ONLINE,
    )
    gateway.arm()

    try:
        response = client.post(
            "/v1/pose",
            json={
                "version": 1,
                "sequence": gateway.state().sequence + 1,
                "issued_at_ms": time_ns() // 1_000_000,
                "ttl_ms": 750,
                "yaw_deg": 5,
                "pitch_deg": 0,
            },
        )
    finally:
        app.state.controller = None
        app.state.controller_status = ControllerStatus(
            configured=False,
            link_state=ControllerLinkState.SIMULATED,
        )

    assert response.status_code == 503
    assert gateway.state().mode == "stopped"
    assert gateway.state().reason == "controller_pose_failed"
    assert decode_pose_command(stream.frames[0]).seq == 1
    assert decode_control_command(stream.frames[1]).op == "stop"
    gateway.arm()


def test_physical_arm_waits_for_matching_controller_acknowledgement() -> None:
    stream = MemoryStream()
    transport = HeadControllerTransport(stream)
    app.state.controller = transport
    app.state.controller_status = ControllerStatus(
        configured=True,
        link_state=ControllerLinkState.ONLINE,
    )

    def acknowledge() -> None:
        while not stream.frames:
            sleep(0.001)
        transport.accept_telemetry(
            b'{"v":1,"seq":1,"yaw_mdeg":0,"pitch_mdeg":0,'
            b'"mode":"neutral","reason":"operator_arm","armed":false,'
            b'"crc32":"BCAEB397"}\n'
        )

    acknowledgement = Thread(target=acknowledge)
    acknowledgement.start()
    try:
        response = client.post("/v1/arm")
    finally:
        acknowledgement.join(timeout=1)
        app.state.controller = None
        app.state.controller_status = ControllerStatus(
            configured=False,
            link_state=ControllerLinkState.SIMULATED,
        )

    assert response.status_code == 200
    assert not acknowledgement.is_alive()
    assert decode_control_command(stream.frames[0]).op == "arm"
    assert gateway.state().reason == "operator_arm"


def test_controller_write_failure_latches_gateway_stop() -> None:
    app.state.controller = HeadControllerTransport(ShortWriteStream())
    app.state.controller_status = ControllerStatus(
        configured=True,
        link_state=ControllerLinkState.ONLINE,
    )
    try:
        response = client.post("/v1/arm")
    finally:
        app.state.controller = None
        app.state.controller_status = ControllerStatus(
            configured=False,
            link_state=ControllerLinkState.SIMULATED,
        )

    assert response.status_code == 503
    assert gateway.state().mode == "stopped"
    assert gateway.state().reason == "controller_arm_failed"
    client.post("/v1/arm")


def test_controller_telemetry_updates_link_status_and_counts_invalid_frames() -> None:
    stream = MemoryStream()
    transport = HeadControllerTransport(stream)
    gateway.arm()
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
    assert app.state.controller_status.outputs_armed is True

    accept_controller_telemetry(app, transport, b"damaged\n")
    assert app.state.controller_status.link_state == "invalid_telemetry"
    assert app.state.controller_status.invalid_frames == 1
    assert app.state.controller_status.outputs_armed is None
    assert gateway.state().mode == "stopped"
    assert gateway.state().reason == "invalid_controller_telemetry"
    assert decode_control_command(stream.frames[-1]).op == "stop"

    app.state.controller_status = ControllerStatus(
        configured=False,
        link_state=ControllerLinkState.SIMULATED,
    )
    gateway.arm()


def test_controller_fault_reasserts_physical_stop_when_host_is_already_stopped() -> None:
    stream = MemoryStream()
    transport = HeadControllerTransport(stream)
    gateway.stop(reason="preexisting_stop")
    app.state.controller_status = ControllerStatus(
        configured=True,
        link_state=ControllerLinkState.ONLINE,
    )

    accept_controller_telemetry(app, transport, b"damaged\n")

    assert gateway.state().reason == "preexisting_stop"
    assert decode_control_command(stream.frames[-1]).op == "stop"

    app.state.controller_status = ControllerStatus(
        configured=False,
        link_state=ControllerLinkState.SIMULATED,
    )
    gateway.arm()


def test_silent_controller_becomes_stale_and_health_degrades() -> None:
    stream = MemoryStream()
    transport = HeadControllerTransport(stream)
    gateway.arm()
    app.state.controller_status = ControllerStatus(
        configured=True,
        link_state=ControllerLinkState.ONLINE,
        last_sequence=4,
        last_received_at_ms=1_000,
    )

    mark_controller_telemetry_stale(app, transport, now_ms=2_001)

    assert client.get("/v1/controller").json()["link_state"] == "stale"
    assert client.get("/v1/controller").json()["outputs_armed"] is None
    assert client.get("/health").json()["status"] == "degraded"
    assert gateway.state().mode == "stopped"
    assert gateway.state().reason == "stale_controller_telemetry"
    assert decode_control_command(stream.frames[-1]).op == "stop"
    app.state.controller_status = ControllerStatus(
        configured=False,
        link_state=ControllerLinkState.SIMULATED,
    )
    gateway.arm()


def test_idle_online_controller_is_polled_without_advancing_sequence() -> None:
    stream = MemoryStream()
    transport = HeadControllerTransport(stream, initial_sequence=4)
    app.state.controller_status = ControllerStatus(
        configured=True,
        link_state=ControllerLinkState.ONLINE,
        last_sequence=4,
        last_received_at_ms=1_000,
    )

    last_poll = poll_controller_status_if_due(
        app,
        transport,
        now_ms=1_501,
        last_poll_at_ms=1_000,
    )

    assert last_poll == 1_501
    assert decode_control_command(stream.frames[-1]).op == "status"
    assert transport.sequence == 4

    app.state.controller_status = ControllerStatus(
        configured=False,
        link_state=ControllerLinkState.SIMULATED,
    )


def test_failed_controller_poll_degrades_health_and_stops() -> None:
    transport = HeadControllerTransport(ShortWriteStream(), initial_sequence=4)
    gateway.arm()
    app.state.controller_status = ControllerStatus(
        configured=True,
        link_state=ControllerLinkState.ONLINE,
        last_sequence=4,
        last_received_at_ms=1_000,
        outputs_armed=True,
    )

    poll_controller_status_if_due(
        app,
        transport,
        now_ms=1_501,
        last_poll_at_ms=1_000,
    )

    assert app.state.controller_status.link_state is ControllerLinkState.STALE
    assert app.state.controller_status.outputs_armed is None
    assert gateway.state().mode is MotionMode.STOPPED
    assert gateway.state().reason == "controller_status_poll_failed"

    app.state.controller_status = ControllerStatus(
        configured=False,
        link_state=ControllerLinkState.SIMULATED,
    )
    gateway.arm()
