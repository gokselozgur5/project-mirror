import random

import pytest

from project_mirror_embodiment.gateway import CommandRejected, EmbodimentGateway, MotionLimits
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


@pytest.mark.parametrize(
    "overrides",
    [
        {"yaw_min_deg": 1.0},
        {"pitch_max_deg": -1.0},
        {"yaw_min_deg": 0.0, "yaw_max_deg": 0.0},
        {"pitch_rate_deg_s": 0.0},
        {"yaw_acceleration_deg_s2": -1.0},
        {"max_clock_skew_ms": -1},
    ],
)
def test_rejects_unsafe_motion_limit_configuration(
    overrides: dict[str, float | int],
) -> None:
    with pytest.raises(ValueError):
        MotionLimits(**overrides)


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


def test_abrupt_reversal_at_limit_cannot_cross_mechanical_bounds() -> None:
    clock = FakeClock()
    gateway = EmbodimentGateway(clock=clock)
    clock.now_ms = 2_000
    at_limit = gateway.submit(
        target(issued_at_ms=2_000, yaw_deg=55, pitch_deg=25)
    )
    clock.now_ms = 2_100

    reversed_state = gateway.submit(
        target(
            sequence=2,
            issued_at_ms=2_100,
            yaw_deg=-55,
            pitch_deg=-25,
        )
    )

    assert at_limit.yaw_deg == 55
    assert at_limit.pitch_deg == 25
    assert reversed_state.yaw_deg == 55
    assert -55 <= reversed_state.yaw_deg <= 55
    assert -25 <= reversed_state.pitch_deg <= 25

    clock.now_ms = 2_200
    recovering = gateway.submit(
        target(
            sequence=3,
            issued_at_ms=2_200,
            yaw_deg=-55,
            pitch_deg=-25,
        )
    )
    assert recovering.yaw_deg < 55


def test_deterministic_motion_fuzz_stays_inside_mechanical_bounds() -> None:
    random_source = random.Random(20261024)
    clock = FakeClock()
    gateway = EmbodimentGateway(clock=clock)

    for sequence in range(1, 1_001):
        clock.now_ms += random_source.randint(1, 200)
        state = gateway.submit(
            target(
                sequence=sequence,
                issued_at_ms=clock.now_ms,
                yaw_deg=random_source.uniform(-180, 180),
                pitch_deg=random_source.uniform(-90, 90),
            )
        )
        assert -55 <= state.yaw_deg <= 55
        assert -25 <= state.pitch_deg <= 25


def test_motion_fuzz_obeys_rate_and_acceleration_away_from_hard_limits() -> None:
    random_source = random.Random(20261025)
    clock = FakeClock()
    gateway = EmbodimentGateway(clock=clock)
    previous_yaw = 0.0
    previous_velocity = 0.0

    for sequence in range(1, 1_001):
        elapsed_ms = random_source.randint(20, 100)
        clock.now_ms += elapsed_ms
        state = gateway.submit(
            target(
                sequence=sequence,
                issued_at_ms=clock.now_ms,
                yaw_deg=random_source.uniform(-40, 40),
                pitch_deg=0,
            )
        )
        elapsed_s = elapsed_ms / 1_000
        velocity = (state.yaw_deg - previous_yaw) / elapsed_s
        assert abs(velocity) <= 120 + 1e-9
        if abs(state.yaw_deg) < 54.999 and abs(previous_yaw) < 54.999:
            acceleration = abs(velocity - previous_velocity) / elapsed_s
            assert acceleration <= 360 + 1e-6
        previous_yaw = state.yaw_deg
        previous_velocity = velocity


def test_constant_target_settles_without_a_limit_cycle() -> None:
    clock = FakeClock()
    gateway = EmbodimentGateway(clock=clock)

    for sequence in range(1, 101):
        clock.now_ms += 100
        state = gateway.submit(
            target(
                sequence=sequence,
                issued_at_ms=clock.now_ms,
                yaw_deg=10,
                pitch_deg=-5,
            )
        )

    assert state.yaw_deg == pytest.approx(10)
    assert state.pitch_deg == pytest.approx(-5)


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
