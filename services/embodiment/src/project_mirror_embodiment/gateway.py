from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from time import time_ns

from .models import EmbodimentState, GatewayMetrics, MotionMode, PoseTarget

Clock = Callable[[], int]


def unix_ms() -> int:
    return time_ns() // 1_000_000


@dataclass(frozen=True, slots=True)
class MotionLimits:
    yaw_min_deg: float = -55.0
    yaw_max_deg: float = 55.0
    pitch_min_deg: float = -25.0
    pitch_max_deg: float = 25.0
    yaw_rate_deg_s: float = 120.0
    pitch_rate_deg_s: float = 90.0
    yaw_acceleration_deg_s2: float = 360.0
    pitch_acceleration_deg_s2: float = 270.0
    max_clock_skew_ms: int = 250


class CommandRejected(ValueError):
    """Raised when a command violates a runtime safety invariant."""


class EmbodimentGateway:
    def __init__(self, limits: MotionLimits | None = None, clock: Clock = unix_ms) -> None:
        self._limits = limits or MotionLimits()
        self._clock = clock
        now = clock()
        self._state = EmbodimentState(
            sequence=0,
            updated_at_ms=now,
            yaw_deg=0.0,
            pitch_deg=0.0,
            mode=MotionMode.NEUTRAL,
            reason="startup",
        )
        self._expires_at_ms = now
        self._started_at_ms = now
        self._accepted_commands = 0
        self._rejected_commands = 0
        self._heartbeat_timeouts = 0
        self._stop_count = 0
        self._last_source_age_ms: int | None = None
        self._stop_latched = False
        self._yaw_velocity_deg_s = 0.0
        self._pitch_velocity_deg_s = 0.0
        self._lock = Lock()

    def submit(self, target: PoseTarget) -> EmbodimentState:
        now = self._clock()
        with self._lock:
            if self._stop_latched:
                self._reject("operator stop is latched")
            if target.sequence <= self._state.sequence:
                self._reject("sequence must increase")
            if target.issued_at_ms > now + self._limits.max_clock_skew_ms:
                self._reject("command timestamp is in the future")
            if now > target.issued_at_ms + target.ttl_ms:
                self._reject("command has expired")

            self._accepted_commands += 1
            self._last_source_age_ms = max(0, now - target.issued_at_ms)
            elapsed_s = max(0.0, (now - self._state.updated_at_ms) / 1_000)
            bounded_yaw = _clamp(target.yaw_deg, self._limits.yaw_min_deg, self._limits.yaw_max_deg)
            bounded_pitch = _clamp(
                target.pitch_deg,
                self._limits.pitch_min_deg,
                self._limits.pitch_max_deg,
            )
            yaw, self._yaw_velocity_deg_s = _advance_axis(
                current=self._state.yaw_deg,
                target=bounded_yaw,
                velocity=self._yaw_velocity_deg_s,
                elapsed_s=elapsed_s,
                max_rate=self._limits.yaw_rate_deg_s,
                max_acceleration=self._limits.yaw_acceleration_deg_s2,
            )
            applied_yaw = _clamp(
                yaw,
                self._limits.yaw_min_deg,
                self._limits.yaw_max_deg,
            )
            if applied_yaw != yaw:
                self._yaw_velocity_deg_s = 0.0
            yaw = applied_yaw
            pitch, self._pitch_velocity_deg_s = _advance_axis(
                current=self._state.pitch_deg,
                target=bounded_pitch,
                velocity=self._pitch_velocity_deg_s,
                elapsed_s=elapsed_s,
                max_rate=self._limits.pitch_rate_deg_s,
                max_acceleration=self._limits.pitch_acceleration_deg_s2,
            )
            applied_pitch = _clamp(
                pitch,
                self._limits.pitch_min_deg,
                self._limits.pitch_max_deg,
            )
            if applied_pitch != pitch:
                self._pitch_velocity_deg_s = 0.0
            pitch = applied_pitch
            self._state = EmbodimentState(
                sequence=target.sequence,
                updated_at_ms=now,
                yaw_deg=yaw,
                pitch_deg=pitch,
                mode=MotionMode.TRACKING,
            )
            self._expires_at_ms = target.issued_at_ms + target.ttl_ms
            return self._state

    def state(self) -> EmbodimentState:
        now = self._clock()
        with self._lock:
            if self._state.mode is MotionMode.TRACKING and now > self._expires_at_ms:
                self._heartbeat_timeouts += 1
                self._yaw_velocity_deg_s = 0.0
                self._pitch_velocity_deg_s = 0.0
                self._state = EmbodimentState(
                    sequence=self._state.sequence,
                    updated_at_ms=now,
                    yaw_deg=0.0,
                    pitch_deg=0.0,
                    mode=MotionMode.NEUTRAL,
                    reason="heartbeat_timeout",
                )
            return self._state

    def stop(self, reason: str = "operator_stop") -> EmbodimentState:
        now = self._clock()
        with self._lock:
            self._stop_count += 1
            self._yaw_velocity_deg_s = 0.0
            self._pitch_velocity_deg_s = 0.0
            self._state = EmbodimentState(
                sequence=self._state.sequence,
                updated_at_ms=now,
                yaw_deg=0.0,
                pitch_deg=0.0,
                mode=MotionMode.STOPPED,
                reason=reason,
            )
            self._expires_at_ms = now
            self._stop_latched = True
            return self._state

    def arm(self) -> EmbodimentState:
        now = self._clock()
        with self._lock:
            self._stop_latched = False
            self._yaw_velocity_deg_s = 0.0
            self._pitch_velocity_deg_s = 0.0
            self._state = EmbodimentState(
                sequence=self._state.sequence,
                updated_at_ms=now,
                yaw_deg=0.0,
                pitch_deg=0.0,
                mode=MotionMode.NEUTRAL,
                reason="operator_arm",
            )
            self._expires_at_ms = now
            return self._state

    def metrics(self) -> GatewayMetrics:
        now = self._clock()
        with self._lock:
            return GatewayMetrics(
                uptime_ms=max(0, now - self._started_at_ms),
                accepted_commands=self._accepted_commands,
                rejected_commands=self._rejected_commands,
                heartbeat_timeouts=self._heartbeat_timeouts,
                stop_count=self._stop_count,
                last_sequence=self._state.sequence,
                last_source_age_ms=self._last_source_age_ms,
            )

    def _reject(self, reason: str) -> None:
        self._rejected_commands += 1
        raise CommandRejected(reason)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _advance_axis(
    *,
    current: float,
    target: float,
    velocity: float,
    elapsed_s: float,
    max_rate: float,
    max_acceleration: float,
) -> tuple[float, float]:
    if elapsed_s <= 0:
        return current, velocity

    distance = target - current
    desired_velocity = _clamp(distance / elapsed_s, -max_rate, max_rate)
    max_velocity_delta = max_acceleration * elapsed_s
    velocity_delta = _clamp(
        desired_velocity - velocity,
        -max_velocity_delta,
        max_velocity_delta,
    )
    next_velocity = _clamp(velocity + velocity_delta, -max_rate, max_rate)
    next_position = current + next_velocity * elapsed_s
    crosses_target = (distance > 0 and next_position > target) or (
        distance < 0 and next_position < target
    )
    if crosses_target:
        arrival_velocity = distance / elapsed_s
        can_arrive = abs(arrival_velocity - velocity) <= max_velocity_delta
        can_stop_next_step = abs(arrival_velocity) <= max_velocity_delta
        if can_arrive and can_stop_next_step:
            return target, arrival_velocity
    return next_position, next_velocity
