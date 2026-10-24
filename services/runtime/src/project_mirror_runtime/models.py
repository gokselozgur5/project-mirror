from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FaceObservation(StrictModel):
    x: float = Field(ge=-1, le=1)
    y: float = Field(ge=-1, le=1)
    confidence: float = Field(ge=0, le=1)


class Observation(StrictModel):
    version: int = Field(1, ge=1, le=1)
    sequence: int = Field(ge=0)
    observed_at_ms: int = Field(ge=0)
    face: FaceObservation | None


class PoseIntent(StrictModel):
    version: int = 1
    sequence: int = Field(ge=0)
    issued_at_ms: int = Field(ge=0)
    ttl_ms: int = Field(ge=50, le=2_000)
    yaw_deg: float
    pitch_deg: float


class RuntimeDecision(StrictModel):
    accepted: bool
    reason: str
    pose: PoseIntent | None = None
