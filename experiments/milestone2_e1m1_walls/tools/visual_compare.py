#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from tools.wad2ng.doom_map import read_map, texture_table
from tools.wad2ng.doom_texture import (
    compose_texture,
    fixed_palette,
    palettize_texture,
    patch_lump_lookup,
    read_pnames,
    read_textures,
)
from tools.wad2ng.wad import Wad


SCREEN_W = 320
SCREEN_H = 224
VIEW_TOP = 16
VIEW_BOTTOM = 176
HORIZON_Y = 96
FOCAL = 184
PROJ_SCALE = 220
NEAR_Z = 28
PLAYER_EYE = 41
STRIP_W = 16
TARGET_WALLS = 53

SIN_Q8 = [
    0,
    25,
    50,
    74,
    98,
    121,
    142,
    162,
    181,
    198,
    213,
    226,
    237,
    245,
    251,
    255,
    256,
    255,
    251,
    245,
    237,
    226,
    213,
    198,
    181,
    162,
    142,
    121,
    98,
    74,
    50,
    25,
    0,
    -25,
    -50,
    -74,
    -98,
    -121,
    -142,
    -162,
    -181,
    -198,
    -213,
    -226,
    -237,
    -245,
    -251,
    -255,
    -256,
    -255,
    -251,
    -245,
    -237,
    -226,
    -213,
    -198,
    -181,
    -162,
    -142,
    -121,
    -98,
    -74,
    -50,
    -25,
]


def sin_q8(angle: int) -> int:
    return SIN_Q8[angle & 63]


def cos_q8(angle: int) -> int:
    return SIN_Q8[(angle + 16) & 63]


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], label: str) -> None:
    draw.text(xy, label, fill=(238, 238, 220))


def resample_nearest() -> int:
    return getattr(getattr(Image, "Resampling", Image), "NEAREST", Image.NEAREST)


def doom_palette(wad: Wad) -> list[tuple[int, int, int]]:
    lump = wad.find_one("PLAYPAL")
    if lump is None:
        raise ValueError("PLAYPAL not found")
    data = wad.read_lump(lump)
    return [tuple(data[i * 3 : i * 3 + 3]) for i in range(256)]


def source_texture_sheet(wad: Wad, map_name: str, out_path: Path) -> None:
    doom_map = read_map(wad, map_name)
    used = texture_table(doom_map)
    textures = read_textures(wad)
    patch_names = read_pnames(wad)
    patches = patch_lump_lookup(wad)
    palette = doom_palette(wad)
    card_palette = fixed_palette()
    cache: dict[str, Image.Image] = {}
    thumbs: list[tuple[str, Image.Image]] = []

    for name in used:
        texture = textures.get(name)
        if texture is None:
            continue
        composed = compose_texture(texture, patch_names, patches, palette, cache)
        image = palettize_texture(composed, card_palette).convert("RGB")
        scale = min(1.0, 96.0 / max(image.width, image.height))
        thumb = image.resize((max(8, int(image.width * scale)), max(8, int(image.height * scale))), resample_nearest())
        thumbs.append((name, thumb))

    cols = 8
    cell_w = 128
    cell_h = 124
    rows = max(1, math.ceil(len(thumbs) / cols))
    out = Image.new("RGB", (cols * cell_w, rows * cell_h), (30, 32, 38))
    draw = ImageDraw.Draw(out)
    for index, (name, image) in enumerate(thumbs):
        x = (index % cols) * cell_w
        y = (index // cols) * cell_h
        out.paste(image, (x + (cell_w - image.width) // 2, y + 8))
        text(draw, (x + 4, y + cell_h - 18), name)
    out.save(out_path)


def atlas_group_sheet(atlas_path: Path, report_path: Path, out_path: Path) -> None:
    atlas = Image.open(atlas_path).convert("RGB")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    records = report["textures"]
    card_height = report.get("card_height", 256)
    cols = 4
    cell_w = 240
    cell_h = 156
    rows = max(1, math.ceil(len(records) / cols))
    out = Image.new("RGB", (cols * cell_w, rows * cell_h), (30, 32, 38))
    draw = ImageDraw.Draw(out)

    for index, record in enumerate(records):
        x = (index % cols) * cell_w
        y = (index // cols) * cell_h
        base = record["base_card"]
        count = record["card_count"]
        crop = atlas.crop((base * STRIP_W, 0, (base + count) * STRIP_W, card_height))
        source_w = max(1, record["source_width"] or crop.width)
        source_h = max(1, record["source_height"] or 128)
        reconstructed = crop.resize((source_w, source_h), resample_nearest())
        scale = min(1.0, (cell_w - 16) / max(1, reconstructed.width), 100 / max(1, reconstructed.height))
        preview = reconstructed.resize(
            (max(1, int(reconstructed.width * scale)), max(1, int(reconstructed.height * scale))),
            resample_nearest(),
        )
        out.paste(preview, (x + 8, y + 8))
        text(draw, (x + 8, y + cell_h - 32), f"{record['name']} cards {base}..{base + count - 1}")
        text(draw, (x + 8, y + cell_h - 16), f"{record['source_width']}x{record['source_height']} -> {count} strips")
    out.save(out_path)


class HostRenderer:
    def __init__(self, wad: Wad, map_name: str, atlas_path: Path, report_path: Path):
        self.map = read_map(wad, map_name)
        self.textures = texture_table(self.map)
        self.texture_ids = {name: index for index, name in enumerate(self.textures)}
        self.atlas = Image.open(atlas_path).convert("P")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.card_height = report.get("card_height", 256)
        self.card_base = [record["base_card"] for record in report["textures"]]
        self.card_count = [record["card_count"] for record in report["textures"]]
        starts = [thing for thing in self.map.things if thing.type == 1]
        if not starts:
            raise ValueError(f"{map_name} has no player 1 start")
        self.start = starts[0]

    def wall_roles(self):
        for seg in self.map.segs:
            line = self.map.linedefs[seg.linedef]
            front_side = line.right_sidedef if seg.side == 0 else line.left_sidedef
            back_side = line.left_sidedef if seg.side == 0 else line.right_sidedef
            if front_side < 0:
                continue
            front = self.map.sidedefs[front_side]
            front_sector = self.map.sectors[front.sector]
            v0 = self.map.vertices[seg.v1]
            v1 = self.map.vertices[seg.v2]
            length = int(math.hypot(v1.x - v0.x, v1.y - v0.y)) or 1
            if back_side < 0:
                yield seg, front.middle, front.x_offset, seg.offset, length, front_sector.floor_height, front_sector.ceiling_height
                continue
            back = self.map.sidedefs[back_side]
            back_sector = self.map.sectors[back.sector]
            if front.middle and front.middle != "-":
                yield seg, front.middle, front.x_offset, seg.offset, length, front_sector.floor_height, front_sector.ceiling_height
            if back_sector.ceiling_height < front_sector.ceiling_height and front.upper and front.upper != "-":
                yield seg, front.upper, front.x_offset, seg.offset, length, back_sector.ceiling_height, front_sector.ceiling_height
            if back_sector.floor_height > front_sector.floor_height and front.lower and front.lower != "-":
                yield seg, front.lower, front.x_offset, seg.offset, length, front_sector.floor_height, back_sector.floor_height

    def card_for(self, texture: str, u_offset: int) -> int:
        texture_id = self.texture_ids.get(texture, 0)
        base = self.card_base[texture_id]
        count = max(1, self.card_count[texture_id])
        return base + (((u_offset >> 4)) % count)

    def projected(self, angle: int, target: int, occlusion: bool) -> Image.Image:
        view_cos = cos_q8(angle)
        view_sin = sin_q8(angle)
        right_x = -view_sin
        right_y = view_cos
        commands: list[tuple[int, int, int, int, int, int]] = []
        bucket_depth = [999999] * 32
        bucket_filled = [False] * 32

        def bucket_for(x: int) -> int:
            return clamp(x, 0, SCREEN_W - 1) // 16

        def is_occluded(x: int, depth: int) -> bool:
            if not occlusion:
                return False
            bucket = bucket_for(x)
            return bucket_filled[bucket] and depth > bucket_depth[bucket] + 16

        def mark(x: int, depth: int) -> None:
            bucket = bucket_for(x)
            if not bucket_filled[bucket] or depth < bucket_depth[bucket]:
                bucket_filled[bucket] = True
                bucket_depth[bucket] = depth

        def add(command: tuple[int, int, int, int, int, int]) -> bool:
            if len(commands) < target:
                commands.append(command)
                mark(command[1], command[0])
                return True
            farthest = max(range(len(commands)), key=lambda index: commands[index][0])
            if command[0] < commands[farthest][0]:
                commands[farthest] = command
                mark(command[1], command[0])
                return True
            return False

        for seg, texture, xoff, seg_offset, length, floor, ceil in self.wall_roles():
            v0 = self.map.vertices[seg.v1]
            v1 = self.map.vertices[seg.v2]
            projected = []
            for vertex in (v0, v1):
                dx = vertex.x - self.start.x
                dy = vertex.y - self.start.y
                z = (dx * view_cos + dy * view_sin) // 256
                side = (dx * right_x + dy * right_y) // 256
                projected.append((side, z))
            (side0, z0), (side1, z1) = projected
            if z0 <= NEAR_Z or z1 <= NEAR_Z:
                continue
            x0 = SCREEN_W // 2 + (side0 * FOCAL) // z0
            x1 = SCREEN_W // 2 + (side1 * FOCAL) // z1
            if x0 == x1:
                continue
            u_base = (xoff + seg_offset) << 8
            if x0 < x1:
                raw_left, raw_right = x0, x1
                z_left, z_right = z0, z1
                u_left, u_right = u_base, u_base + (length << 8)
            else:
                raw_left, raw_right = x1, x0
                z_left, z_right = z1, z0
                u_left, u_right = u_base + (length << 8), u_base
            if raw_right < 0 or raw_left >= SCREEN_W:
                continue
            left = clamp(raw_left, 0, SCREEN_W - 1)
            right = clamp(raw_right, 0, SCREEN_W)
            span = raw_right - raw_left
            if right <= left or span <= 0:
                continue
            u_step = (u_right - u_left) // span
            u_acc = u_left + u_step * (left - raw_left)
            z_span = z_right - z_left
            for x in range(left, right, STRIP_W):
                width = min(STRIP_W, right - x)
                center = x + width // 2 - raw_left
                depth = clamp(z_left + (z_span * center) // span, NEAR_Z, 65535)
                top = HORIZON_Y - (((ceil - PLAYER_EYE) * PROJ_SCALE) // depth)
                bottom = HORIZON_Y - (((floor - PLAYER_EYE) * PROJ_SCALE) // depth)
                top = max(VIEW_TOP, top)
                bottom = min(VIEW_BOTTOM, bottom)
                if bottom > top + 1 and not is_occluded(x, depth):
                    accepted = add((depth, x, top, width, bottom, self.card_for(texture, u_acc >> 8)))
                else:
                    accepted = True
                if len(commands) >= target:
                    break
                u_acc += u_step * width

        image = Image.new("RGB", (SCREEN_W, SCREEN_H), (67, 113, 140))
        bg = self.atlas.crop((0, 0, STRIP_W, self.card_height)).resize((STRIP_W, SCREEN_H), resample_nearest())
        bg_mask = bg.point(lambda value: 0 if value == 0 else 255, "L")
        for x in range(0, SCREEN_W, STRIP_W):
            image.paste(bg.convert("RGB"), (x, 0), bg_mask)
        draw = ImageDraw.Draw(image)
        for depth, x, top, width, bottom, card in sorted(commands, reverse=True):
            if width <= 0 or bottom <= top:
                continue
            crop = self.atlas.crop((card * STRIP_W, 0, card * STRIP_W + STRIP_W, self.card_height))
            resized = crop.resize((width, bottom - top), resample_nearest())
            mask = resized.point(lambda value: 0 if value == 0 else 255, "L")
            image.paste(resized.convert("RGB"), (x, top), mask)
        text(draw, (4, 4), f"ang {angle:02d} target {target:02d} occ {int(occlusion)} cmds {len(commands):02d}")
        return image

    def command_sheet(self, out_path: Path) -> None:
        angle = (self.start.angle * 64) // 360
        cases = [
            (angle, TARGET_WALLS, True),
            (angle, TARGET_WALLS, False),
            (angle, 64, False),
            ((angle + 6) & 63, TARGET_WALLS, True),
            ((angle + 6) & 63, TARGET_WALLS, False),
            ((angle + 6) & 63, 64, False),
        ]
        images = [self.projected(case_angle, target, occlusion) for case_angle, target, occlusion in cases]
        out = Image.new("RGB", (SCREEN_W * 3, SCREEN_H * 2), (0, 0, 0))
        for index, image in enumerate(images):
            out.paste(image, ((index % 3) * SCREEN_W, (index // 3) * SCREEN_H))
        out.save(out_path)


def mame_contact_sheet(snap_dir: Path, out_path: Path) -> None:
    names = [
        "m2_e1m1_turn_gate.png",
        "m2_e1m1_move_gate.png",
        "m2_e1m1_strafe_gate.png",
        "m2_e1m1_back_gate.png",
        "m2_e1m1_scan_gate.png",
    ]
    images = [Image.open(snap_dir / name).convert("RGB") for name in names if (snap_dir / name).exists()]
    if not images:
        return
    out = Image.new("RGB", (SCREEN_W * len(images), SCREEN_H), (0, 0, 0))
    for index, image in enumerate(images):
        out.paste(image, (index * SCREEN_W, 0))
    out.save(out_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate visual comparison artifacts for M2 wall rendering.")
    parser.add_argument("--wad", required=True, type=Path)
    parser.add_argument("--map", default="E1M1")
    parser.add_argument("--generated", required=True, type=Path)
    parser.add_argument("--snap", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    map_lower = args.map.lower()
    wad = Wad(args.wad)
    atlas_path = args.generated / f"{map_lower}_wall_cards.gif"
    report_path = args.generated / f"{map_lower}_wall_atlas_report.json"

    source_texture_sheet(wad, args.map, args.out / f"{map_lower}_source_textures.png")
    atlas_group_sheet(atlas_path, report_path, args.out / f"{map_lower}_atlas_groups.png")
    HostRenderer(wad, args.map, atlas_path, report_path).command_sheet(args.out / f"{map_lower}_host_command_compare.png")
    if args.snap is not None:
        mame_contact_sheet(args.snap, args.out / f"{map_lower}_mame_contact_sheet.png")

    print(json.dumps({"visual_dir": str(args.out), "map": args.map}, indent=2))


if __name__ == "__main__":
    main()
