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


class ControllerLinkState(StrEnum):
    SIMULATED = "simulated"
    AWAITING_TELEMETRY = "awaiting_telemetry"
    ONLINE = "online"
    INVALID_TELEMETRY = "invalid_telemetry"
    STALE = "stale"


class EmbodimentState(StrictModel):
    version: int = 1
    sequence: int = Field(ge=0)
    updated_at_ms: int = Field(ge=0)
    yaw_deg: float = Field(ge=-55, le=55)
    pitch_deg: float = Field(ge=-25, le=25)
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


class ControllerStatus(StrictModel):
    configured: bool
    link_state: ControllerLinkState
    last_sequence: int | None = Field(default=None, ge=0)
    last_mode: MotionMode | None = None
    last_reason: str | None = None
    last_received_at_ms: int | None = Field(default=None, ge=0)
    invalid_frames: int = Field(default=0, ge=0)
