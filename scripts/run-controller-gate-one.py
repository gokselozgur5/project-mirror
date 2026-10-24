#!/usr/bin/env python3
import argparse
import json
import sys

from project_mirror_embodiment.controller_bench import run_gate_one
from project_mirror_embodiment.protocol_corpus import generate_malformed_frames
from project_mirror_embodiment.serial_device import SerialDevice
from project_mirror_embodiment.serial_transport import SerialTransportError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the controller-only Gate 1 protocol bench with no servos connected"
    )
    parser.add_argument(
        "--port", required=True, help="Exact ESP32-S3 serial device path"
    )
    parser.add_argument(
        "--count", type=int, default=100, help="Malformed corpus frame count"
    )
    parser.add_argument(
        "--confirm-servos-disconnected",
        action="store_true",
        help="Required acknowledgement that no servo or mechanism is connected",
    )
    args = parser.parse_args()

    if not args.confirm_servos_disconnected:
        parser.error("refusing to run without --confirm-servos-disconnected")

    device = SerialDevice(args.port, timeout_s=0.05)
    try:
        report = run_gate_one(device, generate_malformed_frames(args.count))
    except SerialTransportError as error:
        print(json.dumps({"passed": False, "error": str(error)}), file=sys.stderr)
        return 1
    finally:
        device.close()

    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
