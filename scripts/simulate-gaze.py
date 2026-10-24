#!/usr/bin/env python3
import argparse
import json
import math
import time
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish synthetic derived face boxes through the perception service"
    )
    parser.add_argument("--perception", default="http://127.0.0.1:8082")
    parser.add_argument("--hz", type=float, default=10.0)
    args = parser.parse_args()

    sequence = int(time.time() * 1_000)
    started = time.monotonic()
    interval = 1.0 / args.hz

    print("publishing synthetic gaze; press Ctrl-C to stop")
    try:
        while True:
            elapsed = time.monotonic() - started
            direction_x = math.sin(elapsed * 0.7) * 0.96
            direction_y = math.sin(elapsed * 1.1) * 0.90
            center_x = (direction_x + 1) / 2
            center_y = (direction_y + 1) / 2
            payload = {
                "version": 1,
                "sequence": sequence,
                "observed_at_ms": time.time_ns() // 1_000_000,
                "faces": [
                    {
                        "left": center_x - 0.02,
                        "top": center_y - 0.02,
                        "right": center_x + 0.02,
                        "bottom": center_y + 0.02,
                        "confidence": 0.95,
                    }
                ],
            }
            request = urllib.request.Request(
                f"{args.perception}/v1/detections",
                data=json.dumps(payload).encode(),
                headers={"content-type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=1) as response:
                response.read()
            sequence += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        print("stopped")


if __name__ == "__main__":
    main()
