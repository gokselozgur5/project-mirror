import json
import zlib

import pytest

from project_mirror_embodiment.controller_bench import run_gate_one
from project_mirror_embodiment.protocol_corpus import generate_malformed_frames
from project_mirror_embodiment.serial_protocol import (
    SerialProtocolError,
    decode_control_command,
    decode_pose_command,
)
from project_mirror_embodiment.serial_transport import SerialTransportError


class FakeController:
    def __init__(self) -> None:
        self.sequence = 0
        self.responses: list[bytes] = []
        self.armed = False

    def write(self, data: bytes) -> int:
        try:
            control = decode_control_command(data)
        except SerialProtocolError:
            control = None
        if control is not None:
            if control.op == "status":
                self.responses.append(telemetry(self.sequence, "stopped", "startup", False))
            elif control.seq > self.sequence:
                self.sequence = control.seq
                if control.op == "stop":
                    self.armed = False
                    self.responses.append(
                        telemetry(self.sequence, "stopped", "operator_stop", False)
                    )
                else:
                    self.responses.append(
                        telemetry(self.sequence, "neutral", "operator_arm", False)
                    )
            return len(data)

        try:
            pose = decode_pose_command(data)
        except SerialProtocolError:
            return len(data)
        if pose.seq > self.sequence:
            self.sequence = pose.seq
            self.armed = True
            self.responses.append(telemetry(self.sequence, "tracking", "pose", True))
        return len(data)

    def read_frame(self) -> bytes:
        if not self.responses and self.armed:
            self.armed = False
            return telemetry(self.sequence, "neutral", "heartbeat_timeout", False)
        if not self.responses:
            return b""
        return self.responses.pop(0)


class UnexpectedResponseController(FakeController):
    def write(self, data: bytes) -> int:
        result = super().write(data)
        if data.startswith(b"{") and b'"crc32"' not in data:
            self.responses.append(b"unexpected\n")
        return result


class SilentAfterPoseController(FakeController):
    def read_frame(self) -> bytes:
        if not self.responses:
            return b""
        return self.responses.pop(0)


class AdvancingClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        self.now += 0.1
        return self.now


def telemetry(sequence: int, mode: str, reason: str, armed: bool) -> bytes:
    armed_value = 1 if armed else 0
    payload = f"1,telemetry,{sequence},0,0,{mode},{reason},{armed_value}"
    frame = {
        "v": 1,
        "seq": sequence,
        "yaw_mdeg": 0,
        "pitch_mdeg": 0,
        "mode": mode,
        "reason": reason,
        "armed": armed,
        "crc32": f"{zlib.crc32(payload.encode('ascii')):08X}",
    }
    return json.dumps(frame, separators=(",", ":")).encode("ascii") + b"\n"


def test_gate_one_proves_protocol_recovery_and_timeout() -> None:
    controller = FakeController()

    report = run_gate_one(
        controller,
        generate_malformed_frames(100),
    )

    assert report.passed
    assert report.initial_sequence == 0
    assert report.malformed_frames_sent == 100
    assert report.unexpected_malformed_responses == 0
    assert report.heartbeat_sequence == 4
    assert report.heartbeat_elapsed_ms >= 0
    assert report.final_sequence == 5


def test_gate_one_fails_on_malformed_input_response() -> None:
    controller = UnexpectedResponseController()

    with pytest.raises(SerialTransportError, match="responded to malformed"):
        run_gate_one(
            controller,
            generate_malformed_frames(1),
        )


def test_gate_one_rejects_short_heartbeat_wait() -> None:
    with pytest.raises(ValueError, match="500 ms"):
        run_gate_one(FakeController(), [], heartbeat_deadline_s=0.49)


def test_gate_one_fails_closed_when_heartbeat_detach_is_missing() -> None:
    controller = SilentAfterPoseController()

    with pytest.raises(SerialTransportError, match="heartbeat detach"):
        run_gate_one(
            controller,
            [],
            heartbeat_deadline_s=0.5,
            monotonic_fn=AdvancingClock(),
        )

    assert controller.armed is False
