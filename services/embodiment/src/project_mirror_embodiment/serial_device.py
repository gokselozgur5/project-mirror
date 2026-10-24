import serial  # type: ignore[import-untyped]


class SerialDevice:
    """Small typed boundary around pyserial for controller writes."""

    def __init__(self, port: str, *, baud_rate: int = 115_200, timeout_s: float = 0.2) -> None:
        self._port = serial.Serial(
            port=port,
            baudrate=baud_rate,
            timeout=timeout_s,
            write_timeout=timeout_s,
        )

    def write(self, data: bytes) -> int:
        try:
            written: int | None = self._port.write(data)
        except serial.SerialException:
            return 0
        if written is None:
            return 0
        return written

    def read_frame(self) -> bytes:
        try:
            frame: bytes = self._port.read_until(expected=b"\n", size=200)
            return frame
        except serial.SerialException:
            return b""

    def close(self) -> None:
        self._port.close()
