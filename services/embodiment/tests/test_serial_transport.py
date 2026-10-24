import pytest

from project_mirror_embodiment.models import EmbodimentState, MotionMode
from project_mirror_embodiment.serial_protocol import (
    decode_control_command,
    decode_pose_command,
)
from project_mirror_embodiment.serial_transport import (
    HeadControllerTransport,
    SerialTransportError,
)

TRACKING_TELEMETRY = (
    b'{"v":1,"seq":1,"yaw_mdeg":12500,"pitch_mdeg":-4000,'
    b'"mode":"tracking","reason":"pose","armed":true,"crc32":"FDF9E1F0"}\n'
)
TRACKING_TELEMETRY_SEQUENCE_2 = (
    b'{"v":1,"seq":2,"yaw_mdeg":12500,"pitch_mdeg":-4000,'
    b'"mode":"tracking","reason":"pose","armed":true,"crc32":"58F18A9C"}\n'
)


class MemoryStream:
    def __init__(self) -> None:
        self.frames: list[bytes] = []

    def write(self, data: bytes) -> int:
        self.frames.append(data)
        return len(data)


class ShortWriteStream:
    def write(self, data: bytes) -> int:
        return len(data) - 1


def state(sequence: int) -> EmbodimentState:
    return EmbodimentState(
        sequence=sequence,
        updated_at_ms=1_000,
        yaw_deg=10,
        pitch_deg=-5,
        mode=MotionMode.TRACKING,
    )


def test_transport_owns_sequence_across_pose_and_control_transitions() -> None:
    stream = MemoryStream()
    transport = HeadControllerTransport(stream)

    transport.publish_pose(state(100))
    transport.publish_control("stop")
    transport.publish_control("arm")
    transport.publish_pose(state(101))

    assert decode_pose_command(stream.frames[0]).seq == 1
    assert decode_control_command(stream.frames[1]).seq == 2
    assert decode_control_command(stream.frames[2]).seq == 3
    assert decode_pose_command(stream.frames[3]).seq == 4
    assert transport.sequence == 4


def test_failed_write_does_not_advance_sequence() -> None:
    transport = HeadControllerTransport(ShortWriteStream())

    with pytest.raises(SerialTransportError, match="incomplete serial write"):
        transport.publish_control("stop")

    assert transport.sequence == 0


def test_sequence_exhaustion_requires_controller_restart() -> None:
    transport = HeadControllerTransport(MemoryStream(), initial_sequence=4_294_967_294)
    assert transport.publish_control("stop") == 4_294_967_295

    with pytest.raises(SerialTransportError, match="sequence exhausted"):
        transport.publish_control("arm")


def test_transport_accepts_telemetry_for_a_published_sequence() -> None:
    transport = HeadControllerTransport(MemoryStream())
    transport.publish_pose(state(100))

    telemetry = transport.accept_telemetry(TRACKING_TELEMETRY)

    assert telemetry.seq == 1
    assert telemetry.mode == "tracking"


def test_transport_rejects_unpublished_future_telemetry() -> None:
    transport = HeadControllerTransport(MemoryStream())

    with pytest.raises(SerialTransportError, match="never published"):
        transport.accept_telemetry(TRACKING_TELEMETRY)


def test_transport_rejects_telemetry_that_moves_backwards() -> None:
    transport = HeadControllerTransport(MemoryStream())
    transport.publish_pose(state(100))
    transport.publish_pose(state(101))
    transport.accept_telemetry(TRACKING_TELEMETRY_SEQUENCE_2)

    with pytest.raises(SerialTransportError, match="moved backwards"):
        transport.accept_telemetry(TRACKING_TELEMETRY)


def test_status_handshake_resumes_controller_sequence() -> None:
    stream = MemoryStream()
    transport = HeadControllerTransport(stream)
    telemetry = (
        b'{"v":1,"seq":42,"yaw_mdeg":0,"pitch_mdeg":0,'
        b'"mode":"stopped","reason":"startup","armed":false,"crc32":"97EF3355"}\n'
    )

    transport.request_status()

    assert decode_control_command(stream.frames[0]).op == "status"
    assert decode_control_command(stream.frames[0]).seq == 0
    assert transport.sequence == 0
    synchronized = transport.synchronize(telemetry)
    assert synchronized.seq == 42
    assert transport.publish_control("stop") == 43


def test_status_poll_does_not_advance_active_transport_sequence() -> None:
    stream = MemoryStream()
    transport = HeadControllerTransport(stream)
    assert transport.publish_control("stop") == 1

    transport.request_status()

    assert decode_control_command(stream.frames[-1]).op == "status"
    assert transport.sequence == 1


def test_transport_waits_for_exact_telemetry_acknowledgement() -> None:
    transport = HeadControllerTransport(MemoryStream())
    sequence = transport.publish_control("arm")
    transport.accept_telemetry(
        b'{"v":1,"seq":1,"yaw_mdeg":0,"pitch_mdeg":0,'
        b'"mode":"neutral","reason":"operator_arm","armed":false,'
        b'"crc32":"BCAEB397"}\n'
    )

    assert transport.wait_for_telemetry(sequence).reason == "operator_arm"


def test_transport_acknowledgement_timeout_fails_closed() -> None:
    transport = HeadControllerTransport(MemoryStream())
    sequence = transport.publish_control("arm")

    with pytest.raises(SerialTransportError, match="timed out"):
        transport.wait_for_telemetry(sequence, timeout_s=0.001)
