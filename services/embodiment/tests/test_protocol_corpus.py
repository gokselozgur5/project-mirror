import pytest

from project_mirror_embodiment.protocol_corpus import generate_malformed_frames
from project_mirror_embodiment.serial_protocol import (
    SerialProtocolError,
    decode_control_command,
    decode_pose_command,
)


def test_hundred_frame_corpus_contains_no_accepted_command() -> None:
    frames = generate_malformed_frames()

    assert len(frames) == 100
    assert len(set(frames)) == 100
    for frame in frames:
        with pytest.raises(SerialProtocolError):
            decode_pose_command(frame)
        with pytest.raises(SerialProtocolError):
            decode_control_command(frame)


def test_corpus_size_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        generate_malformed_frames(0)
