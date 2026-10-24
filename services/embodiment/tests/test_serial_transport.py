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
