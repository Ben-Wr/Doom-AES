#!/usr/bin/env python3
import argparse
import json
import sys


def load_scene(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("sprites", [])
    if isinstance(data, list):
        return data
    raise ValueError("scene must be a JSON object with sprites[] or a list")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Neo Geo per-scanline sprite pressure for a renderer scene dump."
    )
    parser.add_argument("scene", nargs="?", help="JSON scene file")
    parser.add_argument("--height", type=int, default=224)
    parser.add_argument("--warn", type=int, default=84)
    parser.add_argument("--fail", type=int, default=96)
    args = parser.parse_args()

    if not args.scene:
        print("Example scene JSON:")
        print(json.dumps({
            "sprites": [
                {"name": "wall_0", "y": 32, "h": 128, "count": 1},
                {"name": "imp_near", "y": 70, "h": 72, "count": 4}
            ]
        }, indent=2))
        return 0

    sprites = load_scene(args.scene)
    counts = [0] * args.height
    contributors = [[] for _ in range(args.height)]

    for sprite in sprites:
        name = str(sprite.get("name", "sprite"))
        y = int(sprite.get("y", 0))
        h = int(sprite.get("h", 0))
        count = int(sprite.get("count", 1))
        start = max(0, y)
        end = min(args.height, y + h)
        for row in range(start, end):
            counts[row] += count
            if len(contributors[row]) < 8:
                contributors[row].append(name)

    max_count = max(counts) if counts else 0
    max_rows = [i for i, value in enumerate(counts) if value == max_count]
    first = max_rows[0] if max_rows else 0
    last = max_rows[-1] if max_rows else 0

    print("Sprite scanline budget")
    print(f"  sprites listed:     {len(sprites)}")
    print(f"  max scanline count: {max_count}")
    print(f"  rows:               {first}-{last}")
    print(f"  sample contributors on first max row: {', '.join(contributors[first])}")

    if max_count >= args.fail:
        print(f"FAIL: {max_count} >= hard limit {args.fail}")
        return 2
    if max_count >= args.warn:
        print(f"WARN: {max_count} >= warning threshold {args.warn}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

