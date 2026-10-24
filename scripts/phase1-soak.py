#!/usr/bin/env python3
import argparse
import asyncio
import json
import math
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx
import websockets


@dataclass(frozen=True, slots=True)
class SoakReport:
    duration_s: float
    publish_hz: float
    commands_sent: int
    commands_accepted: int
    stream_samples: int
    failures: int
    sequence_lag_max: int
    request_latency_ms_p50: float
    request_latency_ms_p95: float
    request_latency_ms_max: float
    state_age_ms_p50: float
    state_age_ms_p95: float
    state_age_ms_max: float
    gateway_rss_start_bytes: int | None
    gateway_rss_end_bytes: int | None
    gateway_rss_growth_bytes: int | None
    timeout_mode: str
    timeout_reason: str | None
    gateway_metrics: dict[str, Any]
    passed: bool


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, math.ceil(percentile_value * len(ordered)) - 1)
    return ordered[max(0, index)]


async def run(args: argparse.Namespace) -> SoakReport:
    request_latencies: list[float] = []
    state_ages: list[float] = []
    failures = 0
    sent = 0
    accepted = 0
    stream_samples = 0
    latest_sent_sequence = 0
    sequence_lag_max = 0
    stop_at = time.monotonic() + args.duration
    rss_start = process_rss_bytes(args.gateway_pid)

    async with httpx.AsyncClient(base_url=args.gateway_http, timeout=2.0) as client:
        initial_metrics = (await client.get("/v1/metrics")).json()
        sequence = int(initial_metrics["last_sequence"]) + 1

        async def publish() -> None:
            nonlocal accepted, failures, latest_sent_sequence, sent, sequence
            interval = 1.0 / args.publish_hz
            started = time.monotonic()
            tick = 0
            while time.monotonic() < stop_at:
                target_time = started + tick * interval
                await asyncio.sleep(max(0.0, target_time - time.monotonic()))
                elapsed = time.monotonic() - started
                timestamp_ms = time.time_ns() // 1_000_000
                direction_x = math.sin(elapsed * 0.7) * 0.96
                direction_y = math.sin(elapsed * 1.1) * 0.90
                if args.perception_http:
                    center_x = (direction_x + 1) / 2
                    center_y = (direction_y + 1) / 2
                    endpoint = f"{args.perception_http}/v1/detections"
                    payload = {
                        "version": 1,
                        "sequence": sequence,
                        "observed_at_ms": timestamp_ms,
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
                elif args.runtime_http:
                    endpoint = f"{args.runtime_http}/v1/observation"
                    payload = {
                        "version": 1,
                        "sequence": sequence,
                        "observed_at_ms": timestamp_ms,
                        "face": {
                            "x": direction_x,
                            "y": direction_y,
                            "confidence": 0.95,
                        },
                    }
                else:
                    endpoint = "/v1/pose"
                    payload = {
                        "version": 1,
                        "sequence": sequence,
                        "issued_at_ms": timestamp_ms,
                        "ttl_ms": args.ttl_ms,
                        "yaw_deg": math.sin(elapsed * 0.7) * 48,
                        "pitch_deg": math.sin(elapsed * 1.1) * 18,
                    }
                sent += 1
                latest_sent_sequence = sequence
                sequence += 1
                before = time.perf_counter_ns()
                try:
                    response = await client.post(endpoint, json=payload)
                    response.raise_for_status()
                    accepted += 1
                except (httpx.HTTPError, httpx.TimeoutException):
                    failures += 1
                else:
                    request_latencies.append(
                        (time.perf_counter_ns() - before) / 1_000_000
                    )
                tick += 1

        async def consume() -> None:
            nonlocal failures, sequence_lag_max, stream_samples
            try:
                async with websockets.connect(
                    args.gateway_ws, open_timeout=2.0
                ) as socket:
                    while time.monotonic() < stop_at:
                        raw = await asyncio.wait_for(socket.recv(), timeout=2.0)
                        state = json.loads(raw)
                        stream_samples += 1
                        state_ages.append(
                            max(
                                0.0, time.time_ns() / 1_000_000 - state["updated_at_ms"]
                            )
                        )
                        sequence_lag_max = max(
                            sequence_lag_max,
                            max(0, latest_sent_sequence - int(state["sequence"])),
                        )
            except (TimeoutError, OSError, websockets.WebSocketException):
                failures += 1

        await asyncio.gather(publish(), consume())
        await asyncio.sleep((args.ttl_ms + 100) / 1_000)
        timeout_state = (await client.get("/v1/state")).json()
        gateway_metrics = (await client.get("/v1/metrics")).json()

    rss_end = process_rss_bytes(args.gateway_pid)
    rss_growth = None if rss_start is None or rss_end is None else rss_end - rss_start

    passed = (
        failures == 0
        and sent == accepted
        and stream_samples >= args.duration * 10
        and sequence_lag_max <= 2
        and percentile(request_latencies, 0.95) <= args.max_p95_ms
        and percentile(state_ages, 0.95) <= args.max_state_age_ms
        and (rss_growth is None or rss_growth <= args.max_rss_growth_bytes)
        and timeout_state["mode"] == "neutral"
        and timeout_state["reason"] == "heartbeat_timeout"
    )
    return SoakReport(
        duration_s=args.duration,
        publish_hz=args.publish_hz,
        commands_sent=sent,
        commands_accepted=accepted,
        stream_samples=stream_samples,
        failures=failures,
        sequence_lag_max=sequence_lag_max,
        request_latency_ms_p50=statistics.median(request_latencies),
        request_latency_ms_p95=percentile(request_latencies, 0.95),
        request_latency_ms_max=max(request_latencies, default=0.0),
        state_age_ms_p50=statistics.median(state_ages),
        state_age_ms_p95=percentile(state_ages, 0.95),
        state_age_ms_max=max(state_ages, default=0.0),
        gateway_rss_start_bytes=rss_start,
        gateway_rss_end_bytes=rss_end,
        gateway_rss_growth_bytes=rss_growth,
        timeout_mode=timeout_state["mode"],
        timeout_reason=timeout_state["reason"],
        gateway_metrics=gateway_metrics,
        passed=passed,
    )


def process_rss_bytes(pid: int | None) -> int | None:
    if pid is None:
        return None
    try:
        output = subprocess.check_output(
            ["ps", "-o", "rss=", "-p", str(pid)],
            text=True,
            timeout=2,
        )
        return int(output.strip()) * 1024
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure the Phase 1 simulated gaze pipeline"
    )
    parser.add_argument("--gateway-http", default="http://127.0.0.1:8080")
    parser.add_argument("--gateway-ws", default="ws://127.0.0.1:8080/v1/stream")
    parser.add_argument("--runtime-http")
    parser.add_argument("--perception-http")
    parser.add_argument("--duration", type=float, default=300.0)
    parser.add_argument("--publish-hz", type=float, default=10.0)
    parser.add_argument("--ttl-ms", type=int, default=500)
    parser.add_argument("--max-p95-ms", type=float, default=50.0)
    parser.add_argument("--max-state-age-ms", type=float, default=250.0)
    parser.add_argument("--gateway-pid", type=int)
    parser.add_argument("--max-rss-growth-bytes", type=int, default=32 * 1024 * 1024)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.duration <= 0 or args.publish_hz <= 0:
        parser.error("duration and publish-hz must be positive")

    report = asyncio.run(run(args))
    serialized = json.dumps(asdict(report), indent=2, sort_keys=True)
    print(serialized)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    raise SystemExit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
