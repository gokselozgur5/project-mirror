import json
import zlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .models import EmbodimentState


class SerialProtocolError(ValueError):
    """Raised when a serial frame is malformed or fails integrity checks."""


class WirePoseCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v: int = Field(1, ge=1, le=1)
    seq: int = Field(ge=1, le=4_294_967_295)
    yaw_mdeg: int = Field(ge=-55_000, le=55_000)
    pitch_mdeg: int = Field(ge=-25_000, le=25_000)
    crc32: str = Field(pattern=r"^[0-9A-F]{8}$")

    @field_validator("crc32")
    @classmethod
    def uppercase_crc(cls, value: str) -> str:
        if value != value.upper():
            raise ValueError("crc32 must use uppercase hexadecimal")
        return value


class WireControlCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v: int = Field(1, ge=1, le=1)
    seq: int = Field(ge=1, le=4_294_967_295)
    op: Literal["stop", "arm"]
    crc32: str = Field(pattern=r"^[0-9A-F]{8}$")

    @field_validator("crc32")
    @classmethod
    def uppercase_crc(cls, value: str) -> str:
        if value != value.upper():
            raise ValueError("crc32 must use uppercase hexadecimal")
        return value


def encode_pose_command(state: EmbodimentState, *, wire_sequence: int | None = None) -> bytes:
    """Encode an already-bounded gateway state as one newline-delimited frame."""
    sequence = state.sequence if wire_sequence is None else wire_sequence
    if sequence < 1:
        raise SerialProtocolError("sequence must be positive")

    yaw_mdeg = round(state.yaw_deg * 1_000)
    pitch_mdeg = round(state.pitch_deg * 1_000)
    payload = _checksum_payload(1, sequence, yaw_mdeg, pitch_mdeg)
    command = WirePoseCommand(
        v=1,
        seq=sequence,
        yaw_mdeg=yaw_mdeg,
        pitch_mdeg=pitch_mdeg,
        crc32=_crc32(payload),
    )
    return (command.model_dump_json() + "\n").encode("ascii")


def encode_control_command(operation: Literal["stop", "arm"], sequence: int) -> bytes:
    payload = _control_checksum_payload(1, operation, sequence)
    command = WireControlCommand(
        v=1,
        seq=sequence,
        op=operation,
        crc32=_crc32(payload),
    )
    return (command.model_dump_json() + "\n").encode("ascii")


def decode_pose_command(frame: bytes, *, max_frame_bytes: int = 160) -> WirePoseCommand:
    """Validate one complete frame using the same rules as the controller."""
    if not frame.endswith(b"\n"):
        raise SerialProtocolError("frame is not newline terminated")
    if len(frame) > max_frame_bytes:
        raise SerialProtocolError("frame exceeds maximum length")
    try:
        raw = json.loads(frame)
        command = WirePoseCommand.model_validate(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
        raise SerialProtocolError("invalid command frame") from error

    expected = _crc32(
        _checksum_payload(
            command.v,
            command.seq,
            command.yaw_mdeg,
            command.pitch_mdeg,
        )
    )
    if command.crc32 != expected:
        raise SerialProtocolError("crc32 mismatch")
    return command


def decode_control_command(frame: bytes, *, max_frame_bytes: int = 160) -> WireControlCommand:
    if not frame.endswith(b"\n"):
        raise SerialProtocolError("frame is not newline terminated")
    if len(frame) > max_frame_bytes:
        raise SerialProtocolError("frame exceeds maximum length")
    try:
        raw = json.loads(frame)
        command = WireControlCommand.model_validate(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
        raise SerialProtocolError("invalid control frame") from error

    expected = _crc32(_control_checksum_payload(command.v, command.op, command.seq))
    if command.crc32 != expected:
        raise SerialProtocolError("crc32 mismatch")
    return command


def _checksum_payload(version: int, sequence: int, yaw_mdeg: int, pitch_mdeg: int) -> bytes:
    return f"{version},{sequence},{yaw_mdeg},{pitch_mdeg}".encode("ascii")


def _control_checksum_payload(
    version: int, operation: Literal["stop", "arm"], sequence: int
) -> bytes:
    return f"{version},{operation},{sequence}".encode("ascii")


def _crc32(payload: bytes) -> str:
    return f"{zlib.crc32(payload):08X}"
