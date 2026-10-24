import pytest

from project_mirror_perception.models import FaceCandidate, FrameDetections
from project_mirror_perception.policy import FaceDirectionPolicy


def frame(*faces: FaceCandidate) -> FrameDetections:
    return FrameDetections(sequence=7, observed_at_ms=1_000, faces=list(faces))


def test_maps_box_center_to_normalized_direction() -> None:
    observation = FaceDirectionPolicy().observe(
        frame(FaceCandidate(left=0.5, top=0.0, right=1.0, bottom=0.5, confidence=0.9))
    )

    assert observation.face is not None
    assert observation.face.x == 0.5
    assert observation.face.y == -0.5


def test_selects_largest_eligible_face_deterministically() -> None:
    observation = FaceDirectionPolicy().observe(
        frame(
            FaceCandidate(left=0.0, top=0.0, right=0.2, bottom=0.2, confidence=0.99),
            FaceCandidate(left=0.4, top=0.4, right=0.9, bottom=0.9, confidence=0.8),
        )
    )

    assert observation.face is not None
    assert observation.face.x == pytest.approx(0.3)


def test_low_confidence_or_missing_faces_produce_explicit_none() -> None:
    low = FaceCandidate(left=0.1, top=0.1, right=0.9, bottom=0.9, confidence=0.59)

    assert FaceDirectionPolicy().observe(frame(low)).face is None
    assert FaceDirectionPolicy().observe(frame()).face is None


def test_rejects_invalid_boxes() -> None:
    with pytest.raises(ValueError, match="positive area"):
        FaceCandidate(left=0.5, top=0.1, right=0.5, bottom=0.9, confidence=0.9)
