#!/usr/bin/env python3
from pathlib import Path
import json
import shutil
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.wad2ng.cli import command_compile_map, command_compile_wall_atlas
from tools.wad2ng.doom_map import MAP_BANK_MAGIC, MAP_BANK_VERSION, MAP_HEADER_FORMAT
from tools.wad2ng.wad import Wad


class Args:
    wad = ""
    map = "E1M1"
    out = ""
    emit_header = True
    emit_svg = True
    palette = 0


def patch_lump() -> bytes:
    width = 2
    height = 2
    header = struct.pack("<hhhh", width, height, 0, 0)
    table_offset = 8 + width * 4
    col0 = bytes([0, 2, 0, 1, 2, 0, 255])
    col1 = bytes([0, 2, 0, 3, 4, 0, 255])
    offsets = struct.pack("<II", table_offset, table_offset + len(col0))
    return header + offsets + col0 + col1


def playpal_lump() -> bytes:
    playpal = bytearray()
    for i in range(256):
        playpal.extend((i, i, i))
    return bytes(playpal)


def pnames_lump() -> bytes:
    return struct.pack("<i8s", 1, b"PATCHA\0\0")


def texture1_lump(patch_index: int = 0) -> bytes:
    texture_offset = 8
    header = struct.pack("<iI", 1, texture_offset)
    texture = struct.pack("<8sihhiH", b"STARTAN3", 0, 64, 64, 0, 1)
    patch = struct.pack("<hhhhh", 0, 0, patch_index, 0, 0)
    return header + texture + patch


def sector_lump() -> bytes:
    return struct.pack("<hh8s8shhh", 0, 128, b"FLOOR0_1", b"CEIL1_1\0", 160, 0, 0)


def sidedef_lump(sector: int = 0) -> bytes:
    return struct.pack("<hh8s8s8sh", 0, 0, b"-\0", b"-\0", b"STARTAN3", sector)


def make_wad(path: Path, texture_patch_index: int = 0) -> None:
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
        ("PLAYPAL", playpal_lump()),
        ("PNAMES", pnames_lump()),
        ("TEXTURE1", texture1_lump(texture_patch_index)),
        ("P_START", b""),
        ("PATCHA", patch_lump()),
        ("P_END", b""),
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
    command_compile_wall_atlas(args)

    report = json.loads((out / "e1m1_map_report.json").read_text())
    assert report["counts"]["vertices"] == 4
    assert report["counts"]["linedefs"] == 4
    assert report["counts"]["textures"] == 1
    assert report["player_starts"][0]["x"] == 128

    bank = (out / "e1m1_map_bank.bin").read_bytes()
    header_size = struct.calcsize(MAP_HEADER_FORMAT)
    header = struct.unpack_from(MAP_HEADER_FORMAT, bank, 0)
    assert header[0] == MAP_BANK_MAGIC
    assert header[1] == MAP_BANK_VERSION
    assert header[2] == 4
    assert header[15] == 128
    assert header[16] == 64
    assert header[17] == 90
    assert report["estimated_bank_bytes"] == report["actual_bank_bytes"] == len(bank)
    first_vertex = struct.unpack_from(">ii", bank, header_size)
    second_vertex = struct.unpack_from(">ii", bank, header_size + 8)
    assert first_vertex == (0, 0)
    assert second_vertex == (128 << 16, 0)

    header_text = (out / "e1m1_map_data.h").read_text()
    assert "#define M2_PLAYER_START_X 128" in header_text
    assert (out / "e1m1_map_preview.svg").exists()
    atlas_report = json.loads((out / "e1m1_wall_atlas_report.json").read_text())
    assert atlas_report["texture_count"] == 1
    assert atlas_report["cards"] == 4
    assert atlas_report["textures"][0]["card_count"] == 4
    assert atlas_report["missing_textures"] == []
    assert (out / "e1m1_wall_cards.gif").exists()
    wall_header_text = (out / "e1m1_wall_cards.h").read_text()
    assert "#define M2_WALL_CARD_COUNT 4u" in wall_header_text

    bad_wad_path = root / "BAD_PATCH.WAD"
    bad_out = root / "bad_out"
    make_wad(bad_wad_path, texture_patch_index=7)
    bad_args = Args()
    bad_args.wad = str(bad_wad_path)
    bad_args.out = str(bad_out)
    try:
        command_compile_wall_atlas(bad_args)
    except ValueError as exc:
        assert "invalid PNAMES index 7" in str(exc)
    else:
        raise AssertionError("invalid texture patch index did not fail wall atlas compilation")

    print("synthetic wad2ng map compile test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
