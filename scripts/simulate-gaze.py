#!/usr/bin/env python3
import argparse
import json
import math
import time
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish synthetic gaze to the embodiment gateway"
    )
    parser.add_argument("--gateway", default="http://127.0.0.1:8080")
    parser.add_argument("--hz", type=float, default=10.0)
    args = parser.parse_args()

    sequence = int(time.time() * 1_000)
    started = time.monotonic()
    interval = 1.0 / args.hz

    print("publishing synthetic gaze; press Ctrl-C to stop")
    try:
        while True:
            elapsed = time.monotonic() - started
            payload = {
                "version": 1,
                "sequence": sequence,
                "issued_at_ms": time.time_ns() // 1_000_000,
                "ttl_ms": 500,
                "yaw_deg": math.sin(elapsed * 0.7) * 42,
                "pitch_deg": math.sin(elapsed * 1.1) * 14,
            }
            request = urllib.request.Request(
                f"{args.gateway}/v1/pose",
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
