import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from project_mirror_embodiment.models import EmbodimentState, MotionMode, PoseTarget
from project_mirror_embodiment.serial_protocol import (
    decode_control_command,
    decode_pose_command,
    decode_telemetry,
    encode_control_command,
    encode_pose_command,
)

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


def test_serial_command_model_matches_public_contract() -> None:
    state = EmbodimentState(
        sequence=9,
        updated_at_ms=1_001,
        yaw_deg=12.5,
        pitch_deg=-4.0,
        mode=MotionMode.TRACKING,
    )
    command = decode_pose_command(encode_pose_command(state))

    Draft202012Validator(load_schema("serial-pose-command.v1.json")).validate(
        command.model_dump()
    )


def test_serial_control_model_matches_public_contract() -> None:
    command = decode_control_command(encode_control_command("stop", 10))

    Draft202012Validator(load_schema("serial-control-command.v1.json")).validate(
        command.model_dump()
    )


def test_serial_telemetry_model_matches_public_contract() -> None:
    telemetry = decode_telemetry(
        b'{"v":1,"seq":42,"yaw_mdeg":12500,"pitch_mdeg":-4000,'
        b'"mode":"tracking","reason":"pose","armed":true,"crc32":"844925C8"}\n'
    )

    Draft202012Validator(load_schema("serial-telemetry.v1.json")).validate(
        telemetry.model_dump()
    )
