from threading import Lock
from typing import Literal, Protocol

from .models import EmbodimentState
from .serial_protocol import (
    WireTelemetry,
    decode_telemetry,
    encode_control_command,
    encode_pose_command,
)


class WritableStream(Protocol):
    def write(self, data: bytes) -> int: ...


class SerialTransportError(RuntimeError):
    """Raised when a complete controller frame cannot be published."""


class HeadControllerTransport:
    """Serialize controller writes and own their independent monotonic sequence."""

    def __init__(
        self,
        stream: WritableStream,
        *,
        initial_sequence: int = 0,
    ) -> None:
        if not 0 <= initial_sequence < 4_294_967_295:
            raise ValueError("initial sequence is outside the v1 range")
        self._stream = stream
        self._sequence = initial_sequence
        self._last_telemetry_sequence = 0
        self._lock = Lock()

    @property
    def sequence(self) -> int:
        with self._lock:
            return self._sequence

    def publish_pose(self, state: EmbodimentState) -> int:
        with self._lock:
            sequence = self._next_sequence()
            self._write_complete(encode_pose_command(state, wire_sequence=sequence))
            self._sequence = sequence
            return sequence

    def publish_control(self, operation: Literal["stop", "arm"]) -> int:
        with self._lock:
            sequence = self._next_sequence()
            self._write_complete(encode_control_command(operation, sequence))
            self._sequence = sequence
            return sequence

    def request_status(self) -> None:
        with self._lock:
            if self._sequence != 0:
                raise SerialTransportError("status handshake is only valid before publication")
            self._write_complete(encode_control_command("status", 0))

    def synchronize(self, frame: bytes) -> WireTelemetry:
        telemetry = decode_telemetry(frame)
        with self._lock:
            if self._sequence != 0:
                raise SerialTransportError("transport has already published a command")
            self._sequence = telemetry.seq
            self._last_telemetry_sequence = telemetry.seq
            return telemetry

    def accept_telemetry(self, frame: bytes) -> WireTelemetry:
        telemetry = decode_telemetry(frame)
        with self._lock:
            if telemetry.seq > self._sequence:
                raise SerialTransportError("telemetry sequence was never published by this host")
            if telemetry.seq < self._last_telemetry_sequence:
                raise SerialTransportError("telemetry sequence moved backwards")
            self._last_telemetry_sequence = telemetry.seq
            return telemetry

    def _next_sequence(self) -> int:
        if self._sequence == 4_294_967_295:
            raise SerialTransportError("wire sequence exhausted; controller restart required")
        return self._sequence + 1

    def _write_complete(self, frame: bytes) -> None:
        written = self._stream.write(frame)
        if written != len(frame):
            raise SerialTransportError(
                f"incomplete serial write: expected {len(frame)} bytes, wrote {written}"
            )
