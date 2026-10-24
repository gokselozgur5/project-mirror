from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FaceCandidate(StrictModel):
    left: float = Field(ge=0, le=1)
    top: float = Field(ge=0, le=1)
    right: float = Field(ge=0, le=1)
    bottom: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_box(self) -> "FaceCandidate":
        if self.left >= self.right or self.top >= self.bottom:
            raise ValueError("face box must have positive area")
        return self

    @property
    def area(self) -> float:
        return (self.right - self.left) * (self.bottom - self.top)


class FrameDetections(StrictModel):
    version: int = Field(1, ge=1, le=1)
    sequence: int = Field(ge=0, le=4_294_967_295)
    observed_at_ms: int = Field(ge=0)
    faces: list[FaceCandidate] = Field(max_length=32)


class FaceDirection(StrictModel):
    x: float = Field(ge=-1, le=1)
    y: float = Field(ge=-1, le=1)
    confidence: float = Field(ge=0, le=1)


class Observation(StrictModel):
    version: int = 1
    sequence: int = Field(ge=0, le=4_294_967_295)
    observed_at_ms: int = Field(ge=0)
    face: FaceDirection | None
