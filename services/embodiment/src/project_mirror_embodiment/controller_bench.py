from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import asdict, dataclass
from time import monotonic
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
    heartbeat_elapsed_ms: int
    final_sequence: int
    passed: bool

    def as_dict(self) -> dict[str, int | bool]:
        return asdict(self)


def run_gate_one(
    device: BenchDevice,
    malformed_frames: Iterable[bytes],
    *,
    heartbeat_deadline_s: float = 0.8,
    monotonic_fn: Callable[[], float] = monotonic,
) -> GateOneReport:
    """Exercise the unpowered controller protocol and fail on any mismatch."""
    if heartbeat_deadline_s < 0.5:
        raise ValueError("heartbeat deadline must cover the 500 ms firmware timeout")

    transport = HeadControllerTransport(device)
    try:
        return _exercise_gate_one(
            device,
            transport,
            malformed_frames,
            heartbeat_deadline_s=heartbeat_deadline_s,
            monotonic_fn=monotonic_fn,
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
    heartbeat_deadline_s: float,
    monotonic_fn: Callable[[], float],
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

    heartbeat_started_at = monotonic_fn()
    heartbeat = _read_heartbeat(
        device,
        transport,
        deadline=heartbeat_started_at + heartbeat_deadline_s,
        monotonic_fn=monotonic_fn,
    )
    heartbeat_elapsed_ms = round((monotonic_fn() - heartbeat_started_at) * 1_000)
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
        heartbeat_elapsed_ms=heartbeat_elapsed_ms,
        final_sequence=final_sequence,
        passed=True,
    )


def _read_required(device: BenchDevice, step: str) -> bytes:
    frame = device.read_frame()
    if not frame:
        raise SerialTransportError(f"controller did not answer {step}")
    return frame


def _read_heartbeat(
    device: BenchDevice,
    transport: HeadControllerTransport,
    *,
    deadline: float,
    monotonic_fn: Callable[[], float],
) -> WireTelemetry:
    while monotonic_fn() <= deadline:
        frame = device.read_frame()
        observed_at = monotonic_fn()
        if frame:
            if observed_at > deadline:
                raise SerialTransportError("heartbeat detach exceeded the bench deadline")
            return transport.accept_telemetry(frame)
    raise SerialTransportError("controller did not report heartbeat detach before the deadline")


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
