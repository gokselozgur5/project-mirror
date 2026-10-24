from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import asdict, dataclass
from time import sleep
from typing import Protocol

from .models import EmbodimentState, MotionMode
from .serial_protocol import WireTelemetry
from .serial_transport import HeadControllerTransport, SerialTransportError


class BenchDevice(Protocol):
    def write(self, data: bytes) -> int: ...

    def read_frame(self) -> bytes: ...


@dataclass(frozen=True)
class GateOneReport:
    initial_sequence: int
    malformed_frames_sent: int
    unexpected_malformed_responses: int
    heartbeat_sequence: int
    final_sequence: int
    passed: bool

    def as_dict(self) -> dict[str, int | bool]:
        return asdict(self)


def run_gate_one(
    device: BenchDevice,
    malformed_frames: Iterable[bytes],
    *,
    heartbeat_wait_s: float = 0.65,
    sleep_fn: Callable[[float], None] = sleep,
) -> GateOneReport:
    """Exercise the unpowered controller protocol and fail on any mismatch."""
    if heartbeat_wait_s < 0.5:
        raise ValueError("heartbeat wait must cover the 500 ms firmware timeout")

    transport = HeadControllerTransport(device)
    try:
        return _exercise_gate_one(
            device,
            transport,
            malformed_frames,
            heartbeat_wait_s=heartbeat_wait_s,
            sleep_fn=sleep_fn,
        )
    except BaseException:
        with suppress(SerialTransportError):
            transport.publish_control("stop")
        raise


def _exercise_gate_one(
    device: BenchDevice,
    transport: HeadControllerTransport,
    malformed_frames: Iterable[bytes],
    *,
    heartbeat_wait_s: float,
    sleep_fn: Callable[[float], None],
) -> GateOneReport:
    transport.request_status()
    status = transport.synchronize(_read_required(device, "startup status"))

    stop_sequence = transport.publish_control("stop")
    _expect(
        transport.accept_telemetry(_read_required(device, "stop acknowledgement")),
        sequence=stop_sequence,
        mode=MotionMode.STOPPED,
        reason="operator_stop",
        armed=False,
    )

    malformed_count = 0
    unexpected_responses = 0
    for frame in malformed_frames:
        malformed_count += 1
        if device.write(frame) != len(frame):
            raise SerialTransportError("incomplete malformed-corpus write")
        if device.read_frame():
            unexpected_responses += 1

    if unexpected_responses:
        raise SerialTransportError("controller responded to malformed input")

    recovery_sequence = transport.publish_control("stop")
    _expect(
        transport.accept_telemetry(_read_required(device, "recovery stop")),
        sequence=recovery_sequence,
        mode=MotionMode.STOPPED,
        reason="operator_stop",
        armed=False,
    )

    arm_sequence = transport.publish_control("arm")
    _expect(
        transport.accept_telemetry(_read_required(device, "arm acknowledgement")),
        sequence=arm_sequence,
        mode=MotionMode.NEUTRAL,
        reason="operator_arm",
        armed=False,
    )

    pose_sequence = transport.publish_pose(
        EmbodimentState(
            sequence=1,
            updated_at_ms=0,
            yaw_deg=0,
            pitch_deg=0,
            mode=MotionMode.TRACKING,
            reason="gate_one_neutral_pose",
        )
    )
    _expect(
        transport.accept_telemetry(_read_required(device, "neutral pose")),
        sequence=pose_sequence,
        mode=MotionMode.TRACKING,
        reason="pose",
        armed=True,
    )

    sleep_fn(heartbeat_wait_s)
    heartbeat = transport.accept_telemetry(_read_required(device, "heartbeat timeout"))
    _expect(
        heartbeat,
        sequence=pose_sequence,
        mode=MotionMode.NEUTRAL,
        reason="heartbeat_timeout",
        armed=False,
    )

    final_sequence = transport.publish_control("stop")
    _expect(
        transport.accept_telemetry(_read_required(device, "final stop")),
        sequence=final_sequence,
        mode=MotionMode.STOPPED,
        reason="operator_stop",
        armed=False,
    )

    return GateOneReport(
        initial_sequence=status.seq,
        malformed_frames_sent=malformed_count,
        unexpected_malformed_responses=unexpected_responses,
        heartbeat_sequence=heartbeat.seq,
        final_sequence=final_sequence,
        passed=True,
    )


def _read_required(device: BenchDevice, step: str) -> bytes:
    frame = device.read_frame()
    if not frame:
        raise SerialTransportError(f"controller did not answer {step}")
    return frame


def _expect(
    telemetry: WireTelemetry,
    *,
    sequence: int,
    mode: MotionMode,
    reason: str,
    armed: bool,
) -> None:
    actual = (telemetry.seq, telemetry.mode, telemetry.reason, telemetry.armed)
    expected = (sequence, mode, reason, armed)
    if actual != expected:
        raise SerialTransportError(
            f"unexpected controller transition: expected {expected}, received {actual}"
        )
