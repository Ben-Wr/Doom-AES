from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math
import struct

from PIL import Image

from .doom_map import read_map, texture_table
from .doom_picture import render_picture
from .wad import Wad


WALL_CARD_HEIGHT = 256
WALL_CARD_WIDTH = 16
WALL_SLICE_WIDTH = 16
WALL_CARD_SAMPLE_WIDTH = 16
WALL_OPAQUE_FILL_INDEX = 9
WALL_DETAIL_BLEND = 0.25
WALL_CARD_TILES = WALL_CARD_HEIGHT // 16
WALL_CARD_BYTES_4BPP = WALL_CARD_WIDTH * WALL_CARD_HEIGHT // 2


@dataclass(frozen=True)
class TexturePatch:
    x: int
    y: int
    patch_index: int
    stepdir: int
    colormap: int


@dataclass(frozen=True)
class WallTexture:
    name: str
    width: int
    height: int
    patches: list[TexturePatch]


def read_pnames(wad: Wad) -> list[str]:
    lump = wad.find_one("PNAMES")
    if lump is None:
        raise ValueError("PNAMES lump not found")
    data = wad.read_lump(lump)
    if len(data) < 4:
        raise ValueError("PNAMES lump is too small")
    count = struct.unpack_from("<i", data, 0)[0]
    if count < 0 or 4 + count * 8 > len(data):
        raise ValueError("PNAMES count is invalid")
    names = []
    for i in range(count):
        raw = data[4 + i * 8 : 12 + i * 8]
        names.append(raw.split(b"\0", 1)[0].decode("ascii", errors="replace").upper())
    return names


def read_texture_lump(data: bytes) -> list[WallTexture]:
    if len(data) < 4:
        raise ValueError("TEXTURE lump is too small")
    count = struct.unpack_from("<i", data, 0)[0]
    if count < 0 or 4 + count * 4 > len(data):
        raise ValueError("TEXTURE count is invalid")
    offsets = struct.unpack_from(f"<{count}i", data, 4)
    textures = []
    for offset in offsets:
        if offset < 0 or offset + 22 > len(data):
            raise ValueError("TEXTURE entry offset is invalid")
        name_raw, _masked, width, height, _coldir, patch_count = struct.unpack_from("<8sihhiH", data, offset)
        name = name_raw.split(b"\0", 1)[0].decode("ascii", errors="replace").upper()
        patch_offset = offset + 22
        patches = []
        for i in range(patch_count):
            pos = patch_offset + i * 10
            if pos + 10 > len(data):
                raise ValueError(f"TEXTURE {name} patch list is truncated")
            x, y, patch_index, stepdir, colormap = struct.unpack_from("<hhhhh", data, pos)
            patches.append(TexturePatch(x=x, y=y, patch_index=patch_index, stepdir=stepdir, colormap=colormap))
        textures.append(WallTexture(name=name, width=width, height=height, patches=patches))
    return textures


def read_textures(wad: Wad) -> dict[str, WallTexture]:
    textures: dict[str, WallTexture] = {}
    for lump_name in ("TEXTURE1", "TEXTURE2"):
        lump = wad.find_one(lump_name)
        if lump is None:
            continue
        for texture in read_texture_lump(wad.read_lump(lump)):
            textures[texture.name] = texture
    if not textures:
        raise ValueError("no TEXTURE1/TEXTURE2 lumps found")
    return textures


def patch_lump_lookup(wad: Wad) -> dict[str, bytes]:
    lookup: dict[str, bytes] = {}
    for namespace in ("patches", "patches2"):
        for lump in wad.namespace_lumps(namespace):
            if lump.size > 0:
                lookup[lump.name] = wad.read_lump(lump)
    return lookup


def alpha_composite_clipped(base: Image.Image, patch: Image.Image, x: int, y: int) -> None:
    left = max(0, x)
    top = max(0, y)
    right = min(base.width, x + patch.width)
    bottom = min(base.height, y + patch.height)
    if right <= left or bottom <= top:
        return
    crop = patch.crop((left - x, top - y, right - x, bottom - y))
    base.alpha_composite(crop, (left, top))


def compose_texture(
    texture: WallTexture,
    patch_names: list[str],
    patches: dict[str, bytes],
    palette: list[tuple[int, int, int]],
    patch_cache: dict[str, Image.Image] | None = None,
) -> Image.Image:
    image = Image.new("RGBA", (max(1, texture.width), max(1, texture.height)), (0, 0, 0, 0))
    patch_errors = []
    cache = patch_cache if patch_cache is not None else {}
    for patch in texture.patches:
        if patch.patch_index < 0 or patch.patch_index >= len(patch_names):
            patch_errors.append(f"{texture.name}: invalid PNAMES index {patch.patch_index}")
            continue
        patch_name = patch_names[patch.patch_index]
        patch_data = patches.get(patch_name)
        if patch_data is None:
            patch_errors.append(f"{texture.name}: missing patch lump {patch_name}")
            continue
        patch_image = cache.get(patch_name)
        if patch_image is None:
            patch_image, _info = render_picture(patch_data, palette)
            cache[patch_name] = patch_image
        alpha_composite_clipped(image, patch_image, patch.x, patch.y)
    if patch_errors:
        raise ValueError("texture patch composition failed: " + "; ".join(patch_errors))
    return image


def fixed_palette() -> list[tuple[int, int, int]]:
    return [
        (0, 0, 0),
        (245, 242, 228),
        (88, 92, 99),
        (190, 55, 45),
        (235, 164, 74),
        (80, 150, 105),
        (67, 128, 180),
        (112, 96, 84),
        (229, 218, 136),
        (38, 40, 48),
        (97, 62, 46),
        (136, 92, 52),
        (184, 126, 62),
        (78, 112, 88),
        (63, 112, 142),
        (246, 236, 184),
    ]


def nearest_palette_index(pixel: tuple[int, int, int, int], palette: list[tuple[int, int, int]]) -> int:
    if pixel[3] == 0:
        return 0
    best_index = 1
    best_distance = 1 << 30
    r, g, b = pixel[:3]
    for index in range(1, 16):
        pr, pg, pb = palette[index]
        distance = (r - pr) * (r - pr) + (g - pg) * (g - pg) + (b - pb) * (b - pb)
        if distance < best_distance:
            best_index = index
            best_distance = distance
    return best_index


def palette_bytes(palette: list[tuple[int, int, int]]) -> list[int]:
    out: list[int] = []
    for r, g, b in palette:
        out.extend((r, g, b))
    return out + [0] * ((256 * 3) - len(out))


def palette_image(palette: list[tuple[int, int, int]]) -> Image.Image:
    image = Image.new("P", (1, 1), 0)
    image.putpalette(palette_bytes(palette))
    return image


def palettize_texture(texture_image: Image.Image, palette: list[tuple[int, int, int]]) -> Image.Image:
    if texture_image.width <= 0 or texture_image.height <= 0:
        out = Image.new("P", (max(1, texture_image.width), max(1, texture_image.height)), WALL_OPAQUE_FILL_INDEX)
        out.putpalette(palette_bytes(palette))
        return out

    rgba = texture_image.convert("RGBA")
    alpha = rgba.getchannel("A")
    rgb = Image.new("RGB", rgba.size, palette[WALL_OPAQUE_FILL_INDEX])
    rgb.paste(rgba.convert("RGB"), mask=alpha)
    dither_none = getattr(getattr(Image, "Dither", Image), "NONE", 0)
    out = rgb.quantize(palette=palette_image(palette), dither=dither_none)
    out.putpalette(palette_bytes(palette))
    transparent = alpha.point(lambda value: 255 if value == 0 else 0)
    out.paste(WALL_OPAQUE_FILL_INDEX, mask=transparent)
    out = out.point([WALL_OPAQUE_FILL_INDEX if index == 0 else index for index in range(256)])
    out.putpalette(palette_bytes(palette))
    return out


def card_count_for_width(width: int) -> int:
    return max(1, math.ceil(max(1, width) / WALL_SLICE_WIDTH))


def texture_card(texture_image: Image.Image, palette: list[tuple[int, int, int]], u_offset: int) -> Image.Image:
    out = Image.new("P", (WALL_CARD_WIDTH, WALL_CARD_HEIGHT), 0)
    out.putpalette(palette_bytes(palette))
    if texture_image.width <= 0 or texture_image.height <= 0:
        return out

    src = texture_image if texture_image.mode == "P" else palettize_texture(texture_image, palette)
    src.putpalette(palette_bytes(palette))
    sample_width = min(max(src.width, WALL_CARD_WIDTH), WALL_CARD_SAMPLE_WIDTH)
    sample = Image.new("P", (sample_width, src.height), WALL_OPAQUE_FILL_INDEX)
    sample.putpalette(palette_bytes(palette))

    x = 0
    sx = u_offset % src.width
    while x < sample_width:
        width = min(src.width - sx, sample_width - x)
        sample.paste(src.crop((sx, 0, sx + width, src.height)), (x, 0))
        x += width
        sx = 0

    resampling = getattr(getattr(Image, "Resampling", Image), "BOX", Image.NEAREST)
    dither_none = getattr(getattr(Image, "Dither", Image), "NONE", 0)
    sample_rgb = sample.convert("RGB")
    detail_rgb = sample_rgb.resize((WALL_CARD_WIDTH, WALL_CARD_HEIGHT), resample=resampling)
    band_rgb = sample_rgb.resize((1, sample.height), resample=resampling).resize((WALL_CARD_WIDTH, WALL_CARD_HEIGHT), resample=resampling)
    rgb = Image.blend(band_rgb, detail_rgb, WALL_DETAIL_BLEND)
    out = rgb.quantize(palette=palette_image(palette), dither=dither_none)
    out = out.point([WALL_OPAQUE_FILL_INDEX if index == 0 else index for index in range(256)])
    out.putpalette(palette_bytes(palette))
    for x in range(WALL_CARD_WIDTH):
        out.putpixel((x, WALL_CARD_HEIGHT - 1), 0)
    return out


def fallback_card(texture_name: str, palette: list[tuple[int, int, int]]) -> Image.Image:
    out = Image.new("P", (WALL_CARD_WIDTH, WALL_CARD_HEIGHT), 0)
    out.putpalette(palette_bytes(palette))
    seed = sum(ord(ch) for ch in texture_name)
    pixels = []
    for y in range(WALL_CARD_HEIGHT):
        for x in range(WALL_CARD_WIDTH):
            if y == WALL_CARD_HEIGHT - 1:
                value = 0
            elif x in (0, 15) or (y + seed) % 64 in (0, 1):
                value = 15
            elif (x * 7 + y + seed) % 23 < 3:
                value = 4 + (seed % 4)
            else:
                value = 9 + ((x + y // 16 + seed) % 5)
            pixels.append(value)
    out.putdata(pixels)
    return out


def background_card(palette: list[tuple[int, int, int]]) -> Image.Image:
    out = Image.new("P", (WALL_CARD_WIDTH, WALL_CARD_HEIGHT), 0)
    out.putpalette(palette_bytes(palette))
    split = WALL_CARD_HEIGHT // 2
    pixels = []
    for y in range(WALL_CARD_HEIGHT):
        value = 14 if y < split else 12
        for _x in range(WALL_CARD_WIDTH):
            pixels.append(value)
    out.putdata(pixels)
    return out


def texture_family(texture: str) -> str:
    if texture.startswith(("DOOR", "BIGDOOR", "EXITDOOR")):
        return "DOOR"
    if texture.startswith(("SW", "EXIT", "SIGN")):
        return "SIGN"
    if texture.startswith(("BROWN", "BRN", "SLAD")):
        return "BROWN"
    if texture.startswith(("START", "STAR")):
        return "STARTAN"
    if texture.startswith(("COMP", "LITE", "PLANET")):
        return "COMPUTER"
    if texture.startswith("TEK"):
        return "TEK"
    if texture.startswith(("STEP", "SUPPORT", "DOORTRAK", "NUKE")):
        return "TRIM"
    return texture[:4]


def wall_card_header(report: dict) -> str:
    records = report["textures"]
    base_cards = [record["base_card"] for record in records]
    card_counts = [record["card_count"] for record in records]
    family_cards = [record["family_card"] for record in records]

    def array_u16(name: str, values: list[int]) -> str:
        body = "\n".join(f"    {value}u," for value in values) or "    0u,"
        return f"static const uint16_t {name}[] = {{\n{body}\n}};\n"

    def array_u8(name: str, values: list[int]) -> str:
        body = "\n".join(f"    {value}u," for value in values) or "    0u,"
        return f"static const uint8_t {name}[] = {{\n{body}\n}};\n"

    return "\n".join(
        [
            "/* Generated by tools.wad2ng.cli compile-wall-atlas. Do not commit WAD-derived generated output. */",
            "#ifndef DOOM_AES_M2_WALL_CARDS_H",
            "#define DOOM_AES_M2_WALL_CARDS_H",
            "",
            "#include <stdint.h>",
            "",
            f"#define M2_WALL_TEXTURE_COUNT {report['texture_count']}u",
            f"#define M2_WALL_CARD_COUNT {report['cards']}u",
            f"#define M2_WALL_SLICE_WIDTH {report['slice_width']}u",
            "",
            array_u16("m2_texture_card_base", base_cards),
            array_u8("m2_texture_card_count", card_counts),
            array_u16("m2_texture_family_card", family_cards),
            "#endif",
            "",
        ]
    )


def build_wall_atlas(wad: Wad, map_name: str, palette_index: int = 0) -> tuple[Image.Image, dict]:
    playpal = wad.find_one("PLAYPAL")
    if playpal is None:
        raise ValueError("PLAYPAL not found")
    doom_palette_data = wad.read_lump(playpal)
    doom_palette = []
    start = palette_index * 256 * 3
    if start < 0 or start + 256 * 3 > len(doom_palette_data):
        raise ValueError(f"PLAYPAL palette {palette_index} is out of range")
    for i in range(256):
        doom_palette.append(tuple(doom_palette_data[start + i * 3 : start + i * 3 + 3]))

    doom_map = read_map(wad, map_name)
    used_textures = texture_table(doom_map)
    textures = read_textures(wad)
    patch_names = read_pnames(wad)
    patches = patch_lump_lookup(wad)
    card_palette = fixed_palette()
    rendered_patch_cache: dict[str, Image.Image] = {}

    prepared = []
    total_cards = 1
    for name in used_textures:
        texture = textures.get(name)
        if texture is None:
            card_count = 1
            prepared.append((name, None, None, card_count))
        else:
            composed = compose_texture(texture, patch_names, patches, doom_palette, rendered_patch_cache)
            paletted = palettize_texture(composed, card_palette)
            card_count = card_count_for_width(texture.width)
            prepared.append((name, texture, paletted, card_count))
        total_cards += card_count

    atlas = Image.new("P", (max(1, total_cards) * WALL_CARD_WIDTH, WALL_CARD_HEIGHT), 0)
    atlas.putpalette(palette_bytes(card_palette))
    records = []
    missing = []
    family_base: dict[str, int] = {}
    card_cursor = 1
    atlas.paste(background_card(card_palette), (0, 0))
    for index, (name, texture, composed, card_count) in enumerate(prepared):
        base_card = card_cursor
        family_card = family_base.setdefault(texture_family(name), base_card)
        if texture is None:
            card = fallback_card(name, card_palette)
            atlas.paste(card, (base_card * WALL_CARD_WIDTH, 0))
            missing.append(name)
            width = 0
            height = 0
            patch_count = 0
        else:
            width = texture.width
            height = texture.height
            patch_count = len(texture.patches)
            assert composed is not None
            for slice_index in range(card_count):
                card = texture_card(composed, card_palette, slice_index * WALL_SLICE_WIDTH)
                atlas.paste(card, ((base_card + slice_index) * WALL_CARD_WIDTH, 0))
        records.append(
            {
                "id": index + 1,
                "base_card": base_card,
                "card_count": card_count,
                "family_card": family_card,
                "name": name,
                "source_width": width,
                "source_height": height,
                "patches": patch_count,
                "tiles": card_count * WALL_CARD_TILES,
                "bytes_4bpp": card_count * WALL_CARD_BYTES_4BPP,
            }
        )
        card_cursor += card_count

    report = {
        "map": doom_map.name,
        "textures": records,
        "texture_count": len(records),
        "missing_textures": missing,
        "cards": total_cards,
        "background_card": 0,
        "card_width": WALL_CARD_WIDTH,
        "card_height": WALL_CARD_HEIGHT,
        "slice_width": WALL_SLICE_WIDTH,
        "tiles": total_cards * WALL_CARD_TILES,
        "bytes_4bpp": total_cards * WALL_CARD_BYTES_4BPP,
        "notes": [
            "M2 atlas composes Doom TEXTURE patches into 16px U-slice wall cards",
            "material palette is a first fixed 15-color reduction; per-material palettes are next",
        ],
    }
    return atlas, report


def write_wall_atlas(wad: Wad, map_name: str, atlas_path: Path, report_path: Path, header_path: Path, palette_index: int = 0) -> None:
    atlas_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    header_path.parent.mkdir(parents=True, exist_ok=True)
    atlas, report = build_wall_atlas(wad, map_name, palette_index)
    atlas.save(atlas_path)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    header_path.write_text(wall_card_header(report), encoding="utf-8")
