from dataclasses import dataclass

from .models import Observation, PoseIntent, RuntimeDecision


@dataclass(frozen=True, slots=True)
class AttentionPolicy:
    minimum_confidence: float = 0.60
    dead_zone: float = 0.05
    yaw_range_deg: float = 50.0
    pitch_range_deg: float = 20.0
    ttl_ms: int = 500

    def decide(self, observation: Observation) -> RuntimeDecision:
        face = observation.face
        if face is None:
            return RuntimeDecision(accepted=False, reason="no_face")
        if face.confidence < self.minimum_confidence:
            return RuntimeDecision(accepted=False, reason="low_confidence")

        x = 0.0 if abs(face.x) < self.dead_zone else face.x
        y = 0.0 if abs(face.y) < self.dead_zone else face.y
        pose = PoseIntent(
            sequence=observation.sequence,
            issued_at_ms=observation.observed_at_ms,
            ttl_ms=self.ttl_ms,
            yaw_deg=x * self.yaw_range_deg,
            pitch_deg=-y * self.pitch_range_deg,
        )
        return RuntimeDecision(accepted=True, reason="tracking", pose=pose)
