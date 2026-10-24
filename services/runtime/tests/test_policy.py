from project_mirror_runtime.models import FaceObservation, Observation
from project_mirror_runtime.policy import AttentionPolicy


def observation(face: FaceObservation | None) -> Observation:
    return Observation(version=1, sequence=7, observed_at_ms=1_000, face=face)


def test_maps_normalized_face_direction_to_pose() -> None:
    decision = AttentionPolicy().decide(observation(FaceObservation(x=0.5, y=-0.5, confidence=0.9)))

    assert decision.accepted is True
    assert decision.pose is not None
    assert decision.pose.yaw_deg == 25
    assert decision.pose.pitch_deg == 10


def test_applies_dead_zone() -> None:
    decision = AttentionPolicy().decide(
        observation(FaceObservation(x=0.04, y=-0.03, confidence=0.9))
    )

    assert decision.pose is not None
    assert decision.pose.yaw_deg == 0
    assert decision.pose.pitch_deg == 0


def test_ignores_missing_face() -> None:
    decision = AttentionPolicy().decide(observation(None))

    assert decision.accepted is False
    assert decision.reason == "no_face"
    assert decision.pose is None


def test_ignores_low_confidence_face() -> None:
    decision = AttentionPolicy().decide(observation(FaceObservation(x=0.5, y=0.5, confidence=0.59)))

    assert decision.accepted is False
    assert decision.reason == "low_confidence"
