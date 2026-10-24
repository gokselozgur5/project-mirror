from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PoseTarget(StrictModel):
    version: int = Field(1, ge=1, le=1)
    sequence: int = Field(ge=0)
    issued_at_ms: int = Field(ge=0)
    ttl_ms: int = Field(ge=50, le=2_000)
    yaw_deg: float = Field(ge=-180, le=180)
    pitch_deg: float = Field(ge=-90, le=90)


class MotionMode(StrEnum):
    TRACKING = "tracking"
    NEUTRAL = "neutral"
    STOPPED = "stopped"


class EmbodimentState(StrictModel):
    version: int = 1
    sequence: int = Field(ge=0)
    updated_at_ms: int = Field(ge=0)
    yaw_deg: float
    pitch_deg: float
    mode: MotionMode
    reason: str | None = None


class Health(StrictModel):
    status: str
    mode: MotionMode
    controller: str


class GatewayMetrics(StrictModel):
    uptime_ms: int = Field(ge=0)
    accepted_commands: int = Field(ge=0)
    rejected_commands: int = Field(ge=0)
    heartbeat_timeouts: int = Field(ge=0)
    stop_count: int = Field(ge=0)
    last_sequence: int = Field(ge=0)
    last_source_age_ms: int | None = Field(default=None, ge=0)
