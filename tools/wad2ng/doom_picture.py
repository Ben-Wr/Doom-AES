from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import struct


@dataclass(frozen=True)
class PictureInfo:
    width: int
    height: int
    left_offset: int
    top_offset: int


def read_playpal(data: bytes, palette_index: int = 0) -> list[tuple[int, int, int]]:
    start = palette_index * 256 * 3
    end = start + 256 * 3
    if len(data) < end:
        raise ValueError("PLAYPAL does not contain requested palette")
    palette = []
    for i in range(256):
        r, g, b = data[start + i * 3 : start + i * 3 + 3]
        palette.append((r, g, b))
    return palette


def picture_info(data: bytes) -> PictureInfo:
    if len(data) < 8:
        raise ValueError("picture lump too small")
    width, height, left, top = struct.unpack_from("<hhhh", data, 0)
    if width <= 0 or height <= 0 or width > 2048 or height > 2048:
        raise ValueError("picture dimensions out of range")
    table_end = 8 + width * 4
    if table_end > len(data):
        raise ValueError("picture column table extends past lump")
    return PictureInfo(width=width, height=height, left_offset=left, top_offset=top)


def looks_like_picture(data: bytes) -> bool:
    try:
        info = picture_info(data)
    except ValueError:
        return False
    table_end = 8 + info.width * 4
    offsets = struct.unpack_from(f"<{info.width}I", data, 8)
    return all(table_end <= offset < len(data) for offset in offsets)


def render_picture(data: bytes, palette: list[tuple[int, int, int]]):
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required. Run scripts/setup_python_tools.sh") from exc

    info = picture_info(data)
    image = Image.new("RGBA", (info.width, info.height), (0, 0, 0, 0))
    pixels = image.load()
    offsets = struct.unpack_from(f"<{info.width}I", data, 8)

    for x, column_offset in enumerate(offsets):
        pos = column_offset
        while pos < len(data):
            top_delta = data[pos]
            pos += 1
            if top_delta == 0xFF:
                break
            if pos + 2 > len(data):
                raise ValueError("truncated picture post header")
            length = data[pos]
            pos += 1
            pos += 1
            if pos + length + 1 > len(data):
                raise ValueError("truncated picture post pixels")
            for y_offset in range(length):
                y = top_delta + y_offset
                if 0 <= y < info.height:
                    color_index = data[pos + y_offset]
                    r, g, b = palette[color_index]
                    pixels[x, y] = (r, g, b, 255)
            pos += length
            pos += 1

    return image, info


def upscale_to_height(image, target_height: int):
    if target_height <= 0 or image.height >= target_height:
        return image, 1.0
    scale = target_height / image.height
    width = max(1, int(math.ceil(image.width * scale)))
    resized = image.resize((width, target_height), resample=0)
    return resized, scale


def split_vertical_strips(image, strip_width: int = 16):
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required. Run scripts/setup_python_tools.sh") from exc

    strips = []
    count = int(math.ceil(image.width / strip_width))
    for index in range(count):
        left = index * strip_width
        box = (left, 0, min(left + strip_width, image.width), image.height)
        cropped = image.crop(box)
        if cropped.width < strip_width:
            padded = Image.new("RGBA", (strip_width, image.height), (0, 0, 0, 0))
            padded.paste(cropped, (0, 0))
            cropped = padded
        strips.append((index, cropped))
    return strips


def tile_count_for_strip(height: int) -> int:
    return int(math.ceil(height / 16))

