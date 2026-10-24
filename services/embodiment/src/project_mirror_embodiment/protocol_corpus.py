import json


def generate_malformed_frames(count: int = 100) -> list[bytes]:
    """Build a deterministic, diverse corpus that must never become motion."""
    if count < 1:
        raise ValueError("count must be positive")

    frames: list[bytes] = []
    for index in range(count):
        sequence = index + 2
        variant = index % 10
        frame: dict[str, object]
        if variant == 0:
            frame = {"v": 1, "seq": sequence, "yaw_mdeg": 0, "pitch_mdeg": 0}
        elif variant == 1:
            frame = {
                "v": 1,
                "seq": sequence,
                "yaw_mdeg": 0,
                "pitch_mdeg": 0,
                "crc32": "00000000",
            }
        elif variant == 2:
            frame = {
                "v": 2,
                "seq": sequence,
                "yaw_mdeg": 0,
                "pitch_mdeg": 0,
                "crc32": "00000000",
            }
        elif variant == 3:
            frame = {
                "v": 1,
                "seq": sequence,
                "yaw_mdeg": 55_001,
                "pitch_mdeg": 0,
                "crc32": "00000000",
            }
        elif variant == 4:
            frame = {
                "v": 1,
                "seq": sequence,
                "yaw_mdeg": 0.5,
                "pitch_mdeg": 0,
                "crc32": "00000000",
            }
        elif variant == 5:
            frame = {
                "v": 1,
                "seq": sequence,
                "yaw_mdeg": 0,
                "pitch_mdeg": 0,
                "crc32": "00000000",
                "unknown": True,
            }
        elif variant == 6:
            frame = {"v": 1, "seq": sequence, "op": "move", "crc32": "00000000"}
        elif variant == 7:
            frames.append(b"{" + str(sequence).encode("ascii") + b"\n")
            continue
        elif variant == 8:
            frames.append(str(sequence).encode("ascii") + b"x" * 200 + b"\n")
            continue
        else:
            frame = {"v": 1, "seq": sequence, "op": "stop", "crc32": "deadbeef"}
        frames.append(json.dumps(frame, separators=(",", ":")).encode("ascii") + b"\n")
    return frames
