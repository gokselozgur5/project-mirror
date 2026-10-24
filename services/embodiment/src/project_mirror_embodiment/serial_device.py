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
        written: int | None = self._port.write(data)
        if written is None:
            return 0
        return written

    def close(self) -> None:
        self._port.close()
