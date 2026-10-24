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
    clock = FakeClock()
    gateway = EmbodimentGateway(clock=clock)
    clock.now_ms = 2_000

    state = gateway.submit(target(issued_at_ms=2_000, yaw_deg=170, pitch_deg=-80))

    assert state.yaw_deg == 55
    assert state.pitch_deg == -25
    assert state.mode is MotionMode.TRACKING


def test_limits_velocity_and_acceleration() -> None:
    clock = FakeClock()
    gateway = EmbodimentGateway(clock=clock)

    clock.now_ms = 1_100
    first = gateway.submit(target(issued_at_ms=1_100, yaw_deg=55, pitch_deg=25))
    clock.now_ms = 1_200
    second = gateway.submit(target(sequence=2, issued_at_ms=1_200, yaw_deg=55, pitch_deg=25))

    assert first.yaw_deg == pytest.approx(3.6)
    assert first.pitch_deg == pytest.approx(2.7)
    assert second.yaw_deg == pytest.approx(10.8)
    assert second.pitch_deg == pytest.approx(8.1)


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


def test_stop_latches_until_explicit_arm() -> None:
    clock = FakeClock()
    gateway = EmbodimentGateway(clock=clock)
    gateway.submit(target())

    first = gateway.stop()
    second = gateway.stop()

    assert first.mode is MotionMode.STOPPED
    assert second == first
    with pytest.raises(CommandRejected, match="latched"):
        gateway.submit(target(sequence=2))

    armed = gateway.arm()
    resumed = gateway.submit(target(sequence=2))

    assert armed.mode is MotionMode.NEUTRAL
    assert armed.reason == "operator_arm"
    assert resumed.mode is MotionMode.TRACKING


def test_metrics_count_acceptance_rejection_timeout_and_stop() -> None:
    clock = FakeClock()
    gateway = EmbodimentGateway(clock=clock)
    gateway.submit(target())
    with pytest.raises(CommandRejected):
        gateway.submit(target())

    clock.now_ms = 1_501
    gateway.state()
    gateway.stop()
    gateway.arm()
    metrics = gateway.metrics()

    assert metrics.accepted_commands == 1
    assert metrics.rejected_commands == 1
    assert metrics.heartbeat_timeouts == 1
    assert metrics.stop_count == 1
    assert metrics.last_sequence == 1
    assert metrics.last_source_age_ms == 0
    assert metrics.uptime_ms == 501
