import pytest
import serial

from project_mirror_embodiment.serial_device import SerialDevice, SerialDeviceError


def test_open_failure_uses_stable_device_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_open(**_kwargs: object) -> None:
        raise serial.SerialException("device missing")

    monkeypatch.setattr("project_mirror_embodiment.serial_device.serial.Serial", fail_open)

    with pytest.raises(SerialDeviceError, match="/dev/missing"):
        SerialDevice("/dev/missing")
