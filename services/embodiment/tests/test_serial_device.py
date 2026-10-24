import os
import pty

import pytest
import serial

from project_mirror_embodiment.serial_device import SerialDevice, SerialDeviceError


def test_open_failure_uses_stable_device_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_open(**_kwargs: object) -> None:
        raise serial.SerialException("device missing")

    monkeypatch.setattr("project_mirror_embodiment.serial_device.serial.Serial", fail_open)

    with pytest.raises(SerialDeviceError, match="/dev/missing"):
        SerialDevice("/dev/missing")


def test_serial_device_transfers_complete_frames_over_pseudo_terminal() -> None:
    master_fd, slave_fd = pty.openpty()
    device: SerialDevice | None = None
    try:
        device = SerialDevice(os.ttyname(slave_fd), timeout_s=0.1)
        outbound = b'{"v":1,"seq":0,"op":"status","crc32":"E0C2D5D9"}\n'

        assert device.write(outbound) == len(outbound)
        assert os.read(master_fd, len(outbound)) == outbound

        inbound = b'{"status":"test"}\n'
        assert os.write(master_fd, inbound) == len(inbound)
        assert device.read_frame() == inbound
    finally:
        if device is not None:
            device.close()
        os.close(master_fd)
        os.close(slave_fd)
