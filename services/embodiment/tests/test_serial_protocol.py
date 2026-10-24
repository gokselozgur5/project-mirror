import json

import pytest

from project_mirror_embodiment.models import EmbodimentState, MotionMode
from project_mirror_embodiment.serial_protocol import (
    SerialProtocolError,
    decode_control_command,
    decode_pose_command,
    decode_telemetry,
    encode_control_command,
    encode_pose_command,
)


def state(*, sequence: int = 42, yaw: float = 12.5, pitch: float = -4.0) -> EmbodimentState:
    return EmbodimentState(
        sequence=sequence,
        updated_at_ms=1_000,
        yaw_deg=yaw,
        pitch_deg=pitch,
        mode=MotionMode.TRACKING,
    )


def test_round_trip_uses_integer_millidegrees_and_checksum() -> None:
    frame = encode_pose_command(state())

    command = decode_pose_command(frame)

    assert command.seq == 42
    assert command.yaw_mdeg == 12_500
    assert command.pitch_mdeg == -4_000
    assert len(command.crc32) == 8


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.replace(b'"yaw_mdeg":12500', b'"yaw_mdeg":12501'),
        lambda value: value.replace(b'"seq":42', b'"seq":43'),
        lambda value: value.replace(b'"crc32":"', b'"crc32":"F'),
    ],
)
def test_tampering_is_rejected(mutation: object) -> None:
    assert callable(mutation)
    damaged = mutation(encode_pose_command(state()))

    with pytest.raises(SerialProtocolError):
        decode_pose_command(damaged)


@pytest.mark.parametrize(
    "frame",
    [
        b"{}\n",
        b"not-json\n",
        b'{"v":1,"seq":1,"yaw_mdeg":0,"pitch_mdeg":0,"crc32":"00000000"}',
        b'{"v":2,"seq":1,"yaw_mdeg":0,"pitch_mdeg":0,"crc32":"00000000"}\n',
        b'{"v":1,"seq":1,"yaw_mdeg":55001,"pitch_mdeg":0,"crc32":"00000000"}\n',
        b'{"v":1,"seq":1,"yaw_mdeg":0,"pitch_mdeg":0,"extra":1,"crc32":"00000000"}\n',
    ],
)
def test_malformed_frames_are_rejected(frame: bytes) -> None:
    with pytest.raises(SerialProtocolError):
        decode_pose_command(frame)


def test_frame_length_is_bounded_before_parsing() -> None:
    oversized = json.dumps({"padding": "x" * 200}).encode() + b"\n"

    with pytest.raises(SerialProtocolError, match="maximum length"):
        decode_pose_command(oversized)


def test_encoder_refuses_unbounded_state() -> None:
    with pytest.raises(SerialProtocolError):
        encode_pose_command(state(sequence=0))

    with pytest.raises(ValueError):
        encode_pose_command(state(yaw=55.001))


@pytest.mark.parametrize("operation", ["stop", "arm"])
def test_control_command_round_trip(operation: str) -> None:
    assert operation in ("stop", "arm")
    frame = encode_control_command(operation, 43)  # type: ignore[arg-type]

    command = decode_control_command(frame)

    assert command.op == operation
    assert command.seq == 43


def test_control_command_tampering_is_rejected() -> None:
    frame = encode_control_command("stop", 43).replace(b'"stop"', b'"arm"')

    with pytest.raises(SerialProtocolError, match="crc32 mismatch"):
        decode_control_command(frame)


def test_telemetry_golden_vector() -> None:
    frame = (
        b'{"v":1,"seq":42,"yaw_mdeg":12500,"pitch_mdeg":-4000,'
        b'"mode":"tracking","reason":"pose","armed":true,"crc32":"844925C8"}\n'
    )

    telemetry = decode_telemetry(frame)

    assert telemetry.seq == 42
    assert telemetry.mode == "tracking"
    assert telemetry.reason == "pose"
    assert telemetry.armed is True


def test_telemetry_corruption_is_rejected() -> None:
    frame = (
        b'{"v":1,"seq":42,"yaw_mdeg":12501,"pitch_mdeg":-4000,'
        b'"mode":"tracking","reason":"pose","armed":true,"crc32":"844925C8"}\n'
    )

    with pytest.raises(SerialProtocolError, match="crc32 mismatch"):
        decode_telemetry(frame)
