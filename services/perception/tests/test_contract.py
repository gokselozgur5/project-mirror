import json
from pathlib import Path

from jsonschema import Draft202012Validator

from project_mirror_perception.models import FaceCandidate, FrameDetections
from project_mirror_perception.policy import FaceDirectionPolicy

CONTRACT = Path(__file__).parents[3] / "packages" / "contracts" / "observation.v1.json"


def test_derived_observation_matches_public_contract() -> None:
    observation = FaceDirectionPolicy().observe(
        FrameDetections(
            sequence=7,
            observed_at_ms=1_000,
            faces=[
                FaceCandidate(left=0.5, top=0.0, right=1.0, bottom=0.5, confidence=0.9)
            ],
        )
    )
    schema = json.loads(CONTRACT.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(observation.model_dump())
