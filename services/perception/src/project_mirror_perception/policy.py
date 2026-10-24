from .models import FaceCandidate, FaceDirection, FrameDetections, Observation


class FaceDirectionPolicy:
    def __init__(self, *, minimum_confidence: float = 0.6) -> None:
        if not 0 <= minimum_confidence <= 1:
            raise ValueError("minimum confidence must be normalized")
        self._minimum_confidence = minimum_confidence

    def observe(self, detections: FrameDetections) -> Observation:
        eligible = [
            (index, face)
            for index, face in enumerate(detections.faces)
            if face.confidence >= self._minimum_confidence
        ]
        selected = self._select(eligible)
        direction = self._direction(selected) if selected is not None else None
        return Observation(
            sequence=detections.sequence,
            observed_at_ms=detections.observed_at_ms,
            face=direction,
        )

    @staticmethod
    def _select(candidates: list[tuple[int, FaceCandidate]]) -> FaceCandidate | None:
        if not candidates:
            return None
        _, selected = max(
            candidates,
            key=lambda item: (item[1].area, item[1].confidence, -item[0]),
        )
        return selected

    @staticmethod
    def _direction(face: FaceCandidate) -> FaceDirection:
        center_x = (face.left + face.right) / 2
        center_y = (face.top + face.bottom) / 2
        return FaceDirection(
            x=center_x * 2 - 1,
            y=center_y * 2 - 1,
            confidence=face.confidence,
        )
