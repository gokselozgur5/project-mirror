#!/usr/bin/env python3
import argparse
import sys

from project_mirror_embodiment.protocol_corpus import generate_malformed_frames


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write deterministic malformed controller frames to standard output"
    )
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()
    for frame in generate_malformed_frames(args.count):
        sys.stdout.buffer.write(frame)


if __name__ == "__main__":
    main()
