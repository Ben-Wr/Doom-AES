#!/usr/bin/env python3
from pathlib import Path
import json
import shutil
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.wad2ng.cli import command_extract_graphics
from tools.wad2ng.wad import Wad


class Args:
    wad = ""
    out = ""
    namespace = "sprites"
    palette = 0
    limit = 0
    upscale_to_height = 8
    split_strips = True


def patch_lump() -> bytes:
    width = 2
    height = 2
    header = struct.pack("<hhhh", width, height, 0, 0)
    table_offset = 8 + width * 4
    col0 = bytes([0, 2, 0, 1, 2, 0, 255])
    col1 = bytes([0, 2, 0, 3, 4, 0, 255])
    offsets = struct.pack("<II", table_offset, table_offset + len(col0))
    return header + offsets + col0 + col1


def make_wad(path: Path) -> None:
    playpal = bytearray()
    for i in range(256):
        playpal.extend((i, i, i))

    lumps = [
        ("PLAYPAL", bytes(playpal)),
        ("S_START", b""),
        ("TROOA1", patch_lump()),
        ("S_END", b""),
    ]

    data = bytearray()
    directory = []
    for name, payload in lumps:
        offset = 12 + len(data)
        data.extend(payload)
        directory.append((offset, len(payload), name.encode("ascii").ljust(8, b"\0")))

    directory_offset = 12 + len(data)
    header = struct.pack("<4sii", b"IWAD", len(lumps), directory_offset)
    with path.open("wb") as f:
        f.write(header)
        f.write(data)
        for entry in directory:
            f.write(struct.pack("<ii8s", *entry))


def make_bad_bounds_wad(path: Path) -> None:
    header = struct.pack("<4sii", b"IWAD", 1, 12)
    directory = struct.pack("<ii8s", 4096, 4, b"BROKEN\0\0")
    path.write_bytes(header + directory)


def main() -> int:
    root = Path("tmp/wad2ng_synthetic")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    wad_path = root / "SYNTH.WAD"
    out = root / "out"
    make_wad(wad_path)

    wad = Wad(wad_path)
    summary = wad.summary()
    assert summary["magic"] == "IWAD"
    assert summary["namespaces"]["sprites"] == 1

    args = Args()
    args.wad = str(wad_path)
    args.out = str(out)
    command_extract_graphics(args)

    manifest = json.loads((out / "manifests" / "graphics_manifest.json").read_text())
    assert len(manifest["assets"]) == 1
    assert manifest["assets"][0]["planned"]["strip_count"] == 1

    bad_wad_path = root / "BAD_BOUNDS.WAD"
    make_bad_bounds_wad(bad_wad_path)
    try:
        Wad(bad_wad_path)
    except ValueError as exc:
        assert "extends past end of file" in str(exc)
    else:
        raise AssertionError("out-of-bounds lump did not fail WAD validation")

    print("synthetic wad2ng test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
