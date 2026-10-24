from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from time import time_ns

from .models import EmbodimentState, MotionMode, PoseTarget

Clock = Callable[[], int]


def unix_ms() -> int:
    return time_ns() // 1_000_000


@dataclass(frozen=True, slots=True)
class MotionLimits:
    yaw_min_deg: float = -55.0
    yaw_max_deg: float = 55.0
    pitch_min_deg: float = -25.0
    pitch_max_deg: float = 25.0
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
        self._lock = Lock()

    def submit(self, target: PoseTarget) -> EmbodimentState:
        now = self._clock()
        with self._lock:
            if target.sequence <= self._state.sequence:
                raise CommandRejected("sequence must increase")
            if target.issued_at_ms > now + self._limits.max_clock_skew_ms:
                raise CommandRejected("command timestamp is in the future")
            if now > target.issued_at_ms + target.ttl_ms:
                raise CommandRejected("command has expired")

            self._state = EmbodimentState(
                sequence=target.sequence,
                updated_at_ms=now,
                yaw_deg=_clamp(target.yaw_deg, self._limits.yaw_min_deg, self._limits.yaw_max_deg),
                pitch_deg=_clamp(
                    target.pitch_deg,
                    self._limits.pitch_min_deg,
                    self._limits.pitch_max_deg,
                ),
                mode=MotionMode.TRACKING,
            )
            self._expires_at_ms = target.issued_at_ms + target.ttl_ms
            return self._state

    def state(self) -> EmbodimentState:
        now = self._clock()
        with self._lock:
            if self._state.mode is MotionMode.TRACKING and now > self._expires_at_ms:
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
            self._state = EmbodimentState(
                sequence=self._state.sequence,
                updated_at_ms=now,
                yaw_deg=0.0,
                pitch_deg=0.0,
                mode=MotionMode.STOPPED,
                reason=reason,
            )
            self._expires_at_ms = now
            return self._state


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
