#!/usr/bin/env python3
from pathlib import Path
import json
import shutil
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.wad2ng.cli import command_compile_map
from tools.wad2ng.doom_map import MAP_BANK_MAGIC, MAP_BANK_VERSION
from tools.wad2ng.wad import Wad


class Args:
    wad = ""
    map = "E1M1"
    out = ""
    emit_header = True
    emit_svg = True


def sector_lump() -> bytes:
    return struct.pack("<hh8s8shhh", 0, 128, b"FLOOR0_1", b"CEIL1_1\0", 160, 0, 0)


def sidedef_lump(sector: int = 0) -> bytes:
    return struct.pack("<hh8s8s8sh", 0, 0, b"-\0", b"-\0", b"STARTAN3", sector)


def make_wad(path: Path) -> None:
    things = struct.pack("<hhhhh", 128, 64, 90, 1, 7)
    vertices = b"".join(
        struct.pack("<hh", x, y)
        for x, y in (
            (0, 0),
            (128, 0),
            (128, 128),
            (0, 128),
        )
    )
    linedefs = b"".join(
        struct.pack("<hhhhhhh", v1, v2, 0, 0, 0, side, -1)
        for side, (v1, v2) in enumerate(((0, 1), (1, 2), (2, 3), (3, 0)))
    )
    sidedefs = b"".join(sidedef_lump() for _ in range(4))
    sectors = sector_lump()
    segs = b"".join(
        struct.pack("<hhhhhh", v1, v2, 0, line, 0, 0)
        for line, (v1, v2) in enumerate(((0, 1), (1, 2), (2, 3), (3, 0)))
    )
    ssectors = struct.pack("<HH", 4, 0)

    lumps = [
        ("E1M1", b""),
        ("THINGS", things),
        ("LINEDEFS", linedefs),
        ("SIDEDEFS", sidedefs),
        ("VERTEXES", vertices),
        ("SEGS", segs),
        ("SSECTORS", ssectors),
        ("NODES", b""),
        ("SECTORS", sectors),
        ("REJECT", b""),
        ("BLOCKMAP", b""),
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


def main() -> int:
    root = Path("tmp/wad2ng_map_synthetic")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    wad_path = root / "SYNTH_MAP.WAD"
    out = root / "out"
    make_wad(wad_path)

    summary = Wad(wad_path).summary()
    assert summary["maps"] == ["E1M1"]

    args = Args()
    args.wad = str(wad_path)
    args.out = str(out)
    command_compile_map(args)

    report = json.loads((out / "e1m1_map_report.json").read_text())
    assert report["counts"]["vertices"] == 4
    assert report["counts"]["linedefs"] == 4
    assert report["counts"]["textures"] == 1
    assert report["player_starts"][0]["x"] == 128

    bank = (out / "e1m1_map_bank.bin").read_bytes()
    header_fmt = ">8sHHHHHHHHHHhhhhhhh"
    header_size = struct.calcsize(header_fmt)
    header = struct.unpack_from(header_fmt, bank, 0)
    assert header[0] == MAP_BANK_MAGIC
    assert header[1] == MAP_BANK_VERSION
    assert header[2] == 4
    assert header[15] == 128
    assert header[16] == 64
    assert header[17] == 90
    first_vertex = struct.unpack_from(">ii", bank, header_size)
    second_vertex = struct.unpack_from(">ii", bank, header_size + 8)
    assert first_vertex == (0, 0)
    assert second_vertex == (128 << 16, 0)

    header_text = (out / "e1m1_map_data.h").read_text()
    assert "#define M2_PLAYER_START_X 128" in header_text
    assert (out / "e1m1_map_preview.svg").exists()
    print("synthetic wad2ng map compile test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
