import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from project_mirror_embodiment.models import EmbodimentState, MotionMode, PoseTarget

CONTRACTS = Path(__file__).parents[3] / "packages" / "contracts"


def load_schema(name: str) -> dict[str, Any]:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def test_all_contracts_are_valid_draft_2020_12_schemas() -> None:
    for path in CONTRACTS.glob("*.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_pose_model_matches_public_contract() -> None:
    pose = PoseTarget(
        version=1,
        sequence=7,
        issued_at_ms=1_000,
        ttl_ms=500,
        yaw_deg=12.5,
        pitch_deg=-4.0,
    )

    Draft202012Validator(load_schema("pose-target.v1.json")).validate(pose.model_dump())


def test_embodiment_model_matches_public_contract() -> None:
    state = EmbodimentState(
        version=1,
        sequence=7,
        updated_at_ms=1_001,
        yaw_deg=12.5,
        pitch_deg=-4.0,
        mode=MotionMode.TRACKING,
    )

    Draft202012Validator(load_schema("embodiment-state.v1.json")).validate(
        state.model_dump(mode="json")
    )


def test_observation_example_matches_public_contract() -> None:
    observation = {
        "version": 1,
        "sequence": 3,
        "observed_at_ms": 1_000,
        "face": {"x": 0.25, "y": -0.1, "confidence": 0.92},
    }

    Draft202012Validator(load_schema("observation.v1.json")).validate(observation)
