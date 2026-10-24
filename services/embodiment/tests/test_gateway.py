import pytest

from project_mirror_embodiment.gateway import CommandRejected, EmbodimentGateway
from project_mirror_embodiment.models import MotionMode, PoseTarget


class FakeClock:
    def __init__(self, now_ms: int = 1_000) -> None:
        self.now_ms = now_ms

    def __call__(self) -> int:
        return self.now_ms


def target(**overrides: int | float) -> PoseTarget:
    values: dict[str, int | float] = {
        "version": 1,
        "sequence": 1,
        "issued_at_ms": 1_000,
        "ttl_ms": 500,
        "yaw_deg": 10,
        "pitch_deg": -5,
    }
    values.update(overrides)
    return PoseTarget.model_validate(values)


def test_clamps_pose_to_mechanical_limits() -> None:
    gateway = EmbodimentGateway(clock=FakeClock())

    state = gateway.submit(target(yaw_deg=170, pitch_deg=-80))

    assert state.yaw_deg == 55
    assert state.pitch_deg == -25
    assert state.mode is MotionMode.TRACKING


def test_rejects_replayed_sequence() -> None:
    gateway = EmbodimentGateway(clock=FakeClock())
    gateway.submit(target())

    with pytest.raises(CommandRejected, match="sequence"):
        gateway.submit(target())


def test_rejects_expired_command() -> None:
    clock = FakeClock(now_ms=2_000)
    gateway = EmbodimentGateway(clock=clock)

    with pytest.raises(CommandRejected, match="expired"):
        gateway.submit(target())


def test_returns_to_neutral_after_heartbeat_timeout() -> None:
    clock = FakeClock()
    gateway = EmbodimentGateway(clock=clock)
    gateway.submit(target())

    clock.now_ms = 1_501
    state = gateway.state()

    assert state.mode is MotionMode.NEUTRAL
    assert state.yaw_deg == 0
    assert state.pitch_deg == 0
    assert state.reason == "heartbeat_timeout"


def test_stop_is_immediate_and_idempotent() -> None:
    clock = FakeClock()
    gateway = EmbodimentGateway(clock=clock)
    gateway.submit(target())

    first = gateway.stop()
    second = gateway.stop()

    assert first.mode is MotionMode.STOPPED
    assert second == first
