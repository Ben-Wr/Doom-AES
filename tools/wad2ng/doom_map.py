from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import math
import re
import struct

from .wad import MAP_LUMPS, Lump, Wad


MAP_BANK_MAGIC = b"NGM2MAP1"
MAP_BANK_VERSION = 2
MAP_HEADER_FORMAT = ">8sHHHHHHHHHHhhhhhhh"
MAP_HEADER_BYTES = struct.calcsize(MAP_HEADER_FORMAT)
VERTEX_BYTES = struct.calcsize(">ii")
SECTOR_BYTES = struct.calcsize(">hhHHH")
SIDEDEF_BYTES = struct.calcsize(">hhHHHh")
LINEDEF_BYTES = struct.calcsize(">HHHHHhh")
SEG_BYTES = struct.calcsize(">HHhHhhH")
SUBSECTOR_BYTES = struct.calcsize(">HH")
NODE_BYTES = struct.calcsize(">hhhhhhhhhhhhHH")
THING_BYTES = struct.calcsize(">hhHHH")
TEXTURE_NAME_BYTES = 8


@dataclass(frozen=True)
class Thing:
    x: int
    y: int
    angle: int
    type: int
    flags: int


@dataclass(frozen=True)
class Vertex:
    x: int
    y: int


@dataclass(frozen=True)
class Linedef:
    v1: int
    v2: int
    flags: int
    special: int
    tag: int
    right_sidedef: int
    left_sidedef: int


@dataclass(frozen=True)
class Sidedef:
    x_offset: int
    y_offset: int
    upper: str
    lower: str
    middle: str
    sector: int


@dataclass(frozen=True)
class Sector:
    floor_height: int
    ceiling_height: int
    floor_flat: str
    ceiling_flat: str
    light: int
    special: int
    tag: int


@dataclass(frozen=True)
class Seg:
    v1: int
    v2: int
    angle: int
    linedef: int
    side: int
    offset: int


@dataclass(frozen=True)
class Subsector:
    seg_count: int
    first_seg: int


@dataclass(frozen=True)
class Node:
    x: int
    y: int
    dx: int
    dy: int
    bbox: tuple[tuple[int, int, int, int], tuple[int, int, int, int]]
    child: tuple[int, int]


@dataclass(frozen=True)
class DoomMap:
    name: str
    things: list[Thing]
    vertices: list[Vertex]
    linedefs: list[Linedef]
    sidedefs: list[Sidedef]
    sectors: list[Sector]
    segs: list[Seg]
    subsectors: list[Subsector]
    nodes: list[Node]
    reject_size: int
    blockmap_size: int


def _read_name(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("ascii", errors="replace").upper()


def _signed_short_table(data: bytes, record_size: int, fields: int, lump_name: str) -> list[tuple[int, ...]]:
    if len(data) % record_size:
        raise ValueError(f"{lump_name} size {len(data)} is not a multiple of {record_size}")
    records = []
    fmt = "<" + ("h" * fields)
    for offset in range(0, len(data), record_size):
        records.append(struct.unpack_from(fmt, data, offset))
    return records


def _map_lump_dict(wad: Wad, map_name: str) -> dict[str, Lump]:
    wanted = map_name.upper()
    marker_index = None
    map_pattern = re.compile(r"^(E[1-9]M[1-9]|MAP[0-9][0-9])$")
    for index, lump in enumerate(wad.lumps):
        if lump.name == wanted:
            marker_index = index
            break
    if marker_index is None:
        raise ValueError(f"map marker {wanted!r} not found")

    selected: dict[str, Lump] = {}
    for lump in wad.lumps[marker_index + 1 :]:
        if map_pattern.match(lump.name):
            break
        if lump.name in MAP_LUMPS:
            selected[lump.name] = lump
    return selected


def _require_lump(lumps: dict[str, Lump], name: str) -> Lump:
    try:
        return lumps[name]
    except KeyError as exc:
        raise ValueError(f"required map lump {name} not found") from exc


def _parse_things(data: bytes) -> list[Thing]:
    return [Thing(*record) for record in _signed_short_table(data, 10, 5, "THINGS")]


def _parse_vertices(data: bytes) -> list[Vertex]:
    return [Vertex(*record) for record in _signed_short_table(data, 4, 2, "VERTEXES")]


def _parse_linedefs(data: bytes) -> list[Linedef]:
    return [Linedef(*record) for record in _signed_short_table(data, 14, 7, "LINEDEFS")]


def _parse_sidedefs(data: bytes) -> list[Sidedef]:
    if len(data) % 30:
        raise ValueError(f"SIDEDEFS size {len(data)} is not a multiple of 30")
    sidedefs = []
    for offset in range(0, len(data), 30):
        xoff, yoff, upper, lower, middle, sector = struct.unpack_from("<hh8s8s8sh", data, offset)
        sidedefs.append(
            Sidedef(
                x_offset=xoff,
                y_offset=yoff,
                upper=_read_name(upper),
                lower=_read_name(lower),
                middle=_read_name(middle),
                sector=sector,
            )
        )
    return sidedefs


def _parse_sectors(data: bytes) -> list[Sector]:
    if len(data) % 26:
        raise ValueError(f"SECTORS size {len(data)} is not a multiple of 26")
    sectors = []
    for offset in range(0, len(data), 26):
        floor, ceil, floor_flat, ceil_flat, light, special, tag = struct.unpack_from("<hh8s8shhh", data, offset)
        sectors.append(
            Sector(
                floor_height=floor,
                ceiling_height=ceil,
                floor_flat=_read_name(floor_flat),
                ceiling_flat=_read_name(ceil_flat),
                light=light,
                special=special,
                tag=tag,
            )
        )
    return sectors


def _parse_segs(data: bytes) -> list[Seg]:
    return [Seg(*record) for record in _signed_short_table(data, 12, 6, "SEGS")]


def _parse_subsectors(data: bytes) -> list[Subsector]:
    if len(data) % 4:
        raise ValueError(f"SSECTORS size {len(data)} is not a multiple of 4")
    return [Subsector(*struct.unpack_from("<HH", data, offset)) for offset in range(0, len(data), 4)]


def _parse_nodes(data: bytes) -> list[Node]:
    if len(data) % 28:
        raise ValueError(f"NODES size {len(data)} is not a multiple of 28")
    nodes = []
    for offset in range(0, len(data), 28):
        values = struct.unpack_from("<hhhhhhhhhhhhHH", data, offset)
        bbox0 = values[4:8]
        bbox1 = values[8:12]
        nodes.append(
            Node(
                x=values[0],
                y=values[1],
                dx=values[2],
                dy=values[3],
                bbox=(bbox0, bbox1),
                child=(values[12], values[13]),
            )
        )
    return nodes


def _check_index(errors: list[str], label: str, value: int, count: int, allow_minus_one: bool = False) -> None:
    if allow_minus_one and value == -1:
        return
    if value < 0 or value >= count:
        errors.append(f"{label} index {value} outside 0..{max(0, count - 1)}")


def _validate_map(doom_map: DoomMap) -> None:
    errors: list[str] = []

    if not doom_map.vertices:
        errors.append("VERTEXES is empty")
    if not doom_map.linedefs:
        errors.append("LINEDEFS is empty")
    if not doom_map.sidedefs:
        errors.append("SIDEDEFS is empty")
    if not doom_map.sectors:
        errors.append("SECTORS is empty")
    if not doom_map.segs:
        errors.append("SEGS is empty")
    if not doom_map.subsectors:
        errors.append("SSECTORS is empty")

    for index, line in enumerate(doom_map.linedefs):
        _check_index(errors, f"LINEDEFS[{index}].v1", line.v1, len(doom_map.vertices))
        _check_index(errors, f"LINEDEFS[{index}].v2", line.v2, len(doom_map.vertices))
        _check_index(errors, f"LINEDEFS[{index}].right_sidedef", line.right_sidedef, len(doom_map.sidedefs))
        _check_index(errors, f"LINEDEFS[{index}].left_sidedef", line.left_sidedef, len(doom_map.sidedefs), allow_minus_one=True)

    for index, side in enumerate(doom_map.sidedefs):
        _check_index(errors, f"SIDEDEFS[{index}].sector", side.sector, len(doom_map.sectors))

    for index, seg in enumerate(doom_map.segs):
        _check_index(errors, f"SEGS[{index}].v1", seg.v1, len(doom_map.vertices))
        _check_index(errors, f"SEGS[{index}].v2", seg.v2, len(doom_map.vertices))
        _check_index(errors, f"SEGS[{index}].linedef", seg.linedef, len(doom_map.linedefs))
        if seg.side not in (0, 1):
            errors.append(f"SEGS[{index}].side value {seg.side} is not 0 or 1")
        elif 0 <= seg.linedef < len(doom_map.linedefs):
            line = doom_map.linedefs[seg.linedef]
            front_side = line.right_sidedef if seg.side == 0 else line.left_sidedef
            _check_index(errors, f"SEGS[{index}] front sidedef", front_side, len(doom_map.sidedefs))

    for index, subsector in enumerate(doom_map.subsectors):
        if subsector.seg_count == 0:
            errors.append(f"SSECTORS[{index}].seg_count is zero")
        if subsector.first_seg > len(doom_map.segs) or subsector.first_seg + subsector.seg_count > len(doom_map.segs):
            errors.append(
                f"SSECTORS[{index}] seg range {subsector.first_seg}..{subsector.first_seg + subsector.seg_count} exceeds {len(doom_map.segs)} segs"
            )

    for index, node in enumerate(doom_map.nodes):
        for child_index, child in enumerate(node.child):
            if child & 0x8000:
                _check_index(errors, f"NODES[{index}].child[{child_index}] subsector", child & 0x7FFF, len(doom_map.subsectors))
            else:
                _check_index(errors, f"NODES[{index}].child[{child_index}] node", child, len(doom_map.nodes))

    if errors:
        detail = "\n  - ".join(errors)
        raise ValueError(f"{doom_map.name} validation failed:\n  - {detail}")


def read_map(wad: Wad, map_name: str) -> DoomMap:
    lumps = _map_lump_dict(wad, map_name)
    doom_map = DoomMap(
        name=map_name.upper(),
        things=_parse_things(wad.read_lump(_require_lump(lumps, "THINGS"))),
        vertices=_parse_vertices(wad.read_lump(_require_lump(lumps, "VERTEXES"))),
        linedefs=_parse_linedefs(wad.read_lump(_require_lump(lumps, "LINEDEFS"))),
        sidedefs=_parse_sidedefs(wad.read_lump(_require_lump(lumps, "SIDEDEFS"))),
        sectors=_parse_sectors(wad.read_lump(_require_lump(lumps, "SECTORS"))),
        segs=_parse_segs(wad.read_lump(_require_lump(lumps, "SEGS"))),
        subsectors=_parse_subsectors(wad.read_lump(_require_lump(lumps, "SSECTORS"))),
        nodes=_parse_nodes(wad.read_lump(_require_lump(lumps, "NODES"))),
        reject_size=lumps.get("REJECT").size if lumps.get("REJECT") else 0,
        blockmap_size=lumps.get("BLOCKMAP").size if lumps.get("BLOCKMAP") else 0,
    )
    _validate_map(doom_map)
    return doom_map


def texture_table(doom_map: DoomMap) -> list[str]:
    seen: dict[str, None] = {}
    for side in doom_map.sidedefs:
        for texture in (side.upper, side.lower, side.middle):
            if texture and texture != "-":
                seen.setdefault(texture, None)
    return list(seen.keys())


def thing_type_counts(doom_map: DoomMap) -> dict[str, int]:
    counts: dict[str, int] = {}
    for thing in doom_map.things:
        key = str(thing.type)
        counts[key] = counts.get(key, 0) + 1
    return counts


def player_starts(doom_map: DoomMap) -> list[Thing]:
    return [thing for thing in doom_map.things if thing.type in {1, 2, 3, 4}]


def map_bounds(doom_map: DoomMap) -> dict[str, int]:
    xs = [vertex.x for vertex in doom_map.vertices]
    ys = [vertex.y for vertex in doom_map.vertices]
    return {
        "min_x": min(xs),
        "max_x": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
    }


def compile_report(wad: Wad, doom_map: DoomMap) -> dict:
    textures = texture_table(doom_map)
    starts = player_starts(doom_map)
    bounds = map_bounds(doom_map)
    counts = {
        "things": len(doom_map.things),
        "vertices": len(doom_map.vertices),
        "linedefs": len(doom_map.linedefs),
        "sidedefs": len(doom_map.sidedefs),
        "sectors": len(doom_map.sectors),
        "segs": len(doom_map.segs),
        "subsectors": len(doom_map.subsectors),
        "nodes": len(doom_map.nodes),
        "textures": len(textures),
    }
    bank_bytes = estimate_bank_bytes(doom_map)
    return {
        "source": {
            "wad": str(wad.path),
            "magic": wad.magic,
            "map": doom_map.name,
            "provenance": "local user-provided WAD; do not commit WAD or generated banks",
        },
        "counts": counts,
        "bounds": bounds,
        "player_starts": [asdict(start) for start in starts],
        "textures": textures,
        "thing_type_counts": thing_type_counts(doom_map),
        "raw_lump_bytes": {
            "reject": doom_map.reject_size,
            "blockmap": doom_map.blockmap_size,
        },
        "estimated_bank_bytes": bank_bytes,
        "simplifications": [],
        "notes": [
            "multi-byte bank output is big-endian for 68000 consumption",
            "vertices are emitted as 16.16 fixed point",
            "texture ids are per-map dependency ids; wall card composition is a later M2 stage",
        ],
    }


def fixed16(value: int) -> int:
    return value << 16


def _seg_length(doom_map: DoomMap, seg: Seg) -> int:
    v0 = doom_map.vertices[seg.v1]
    v1 = doom_map.vertices[seg.v2]
    return max(1, int(round(math.hypot(v1.x - v0.x, v1.y - v0.y))))


def _signed_sidedef_index(value: int) -> int:
    return value if value >= 0 else -1


def _texture_id_lookup(doom_map: DoomMap) -> dict[str, int]:
    return {name: index + 1 for index, name in enumerate(texture_table(doom_map))}


def _texture_id(texture: str, lookup: dict[str, int]) -> int:
    if not texture or texture == "-":
        return 0
    return lookup[texture]


def estimate_bank_bytes(doom_map: DoomMap) -> int:
    return (
        MAP_HEADER_BYTES
        + len(doom_map.vertices) * VERTEX_BYTES
        + len(doom_map.sectors) * SECTOR_BYTES
        + len(doom_map.sidedefs) * SIDEDEF_BYTES
        + len(doom_map.linedefs) * LINEDEF_BYTES
        + len(doom_map.segs) * SEG_BYTES
        + len(doom_map.subsectors) * SUBSECTOR_BYTES
        + len(doom_map.nodes) * NODE_BYTES
        + len(doom_map.things) * THING_BYTES
        + len(texture_table(doom_map)) * TEXTURE_NAME_BYTES
    )


def write_binary_bank(doom_map: DoomMap, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    textures = texture_table(doom_map)
    lookup = _texture_id_lookup(doom_map)
    bounds = map_bounds(doom_map)
    starts = player_starts(doom_map)
    player = starts[0] if starts else Thing(0, 0, 0, 1, 0)

    chunks: list[bytes] = []
    chunks.append(
        struct.pack(
            MAP_HEADER_FORMAT,
            MAP_BANK_MAGIC,
            MAP_BANK_VERSION,
            len(doom_map.vertices),
            len(doom_map.sectors),
            len(doom_map.sidedefs),
            len(doom_map.linedefs),
            len(doom_map.segs),
            len(doom_map.subsectors),
            len(doom_map.nodes),
            len(doom_map.things),
            len(textures),
            bounds["min_x"],
            bounds["max_x"],
            bounds["min_y"],
            bounds["max_y"],
            player.x,
            player.y,
            player.angle,
        )
    )

    for vertex in doom_map.vertices:
        chunks.append(struct.pack(">ii", fixed16(vertex.x), fixed16(vertex.y)))
    for sector in doom_map.sectors:
        chunks.append(
            struct.pack(
                ">hhHHH",
                sector.floor_height,
                sector.ceiling_height,
                sector.light & 0xFFFF,
                sector.special & 0xFFFF,
                sector.tag & 0xFFFF,
            )
        )
    for side in doom_map.sidedefs:
        chunks.append(
            struct.pack(
                ">hhHHHh",
                side.x_offset,
                side.y_offset,
                _texture_id(side.upper, lookup),
                _texture_id(side.lower, lookup),
                _texture_id(side.middle, lookup),
                side.sector,
            )
        )
    for line in doom_map.linedefs:
        chunks.append(
            struct.pack(
                ">HHHHHhh",
                line.v1 & 0xFFFF,
                line.v2 & 0xFFFF,
                line.flags & 0xFFFF,
                line.special & 0xFFFF,
                line.tag & 0xFFFF,
                _signed_sidedef_index(line.right_sidedef),
                _signed_sidedef_index(line.left_sidedef),
            )
        )
    for seg in doom_map.segs:
        chunks.append(
            struct.pack(
                ">HHhHhhH",
                seg.v1 & 0xFFFF,
                seg.v2 & 0xFFFF,
                seg.angle,
                seg.linedef & 0xFFFF,
                seg.side,
                seg.offset,
                _seg_length(doom_map, seg),
            )
        )
    for subsector in doom_map.subsectors:
        chunks.append(struct.pack(">HH", subsector.seg_count, subsector.first_seg))
    for node in doom_map.nodes:
        chunks.append(struct.pack(">hhhh", node.x, node.y, node.dx, node.dy))
        chunks.append(struct.pack(">hhhh", *node.bbox[0]))
        chunks.append(struct.pack(">hhhh", *node.bbox[1]))
        chunks.append(struct.pack(">HH", *node.child))
    for thing in doom_map.things:
        chunks.append(struct.pack(">hhHHH", thing.x, thing.y, thing.angle & 0xFFFF, thing.type & 0xFFFF, thing.flags & 0xFFFF))
    for texture in textures:
        chunks.append(texture.encode("ascii", errors="replace")[:8].ljust(8, b"\0"))

    path.write_bytes(b"".join(chunks))


def _c_array(name: str, rows: list[str]) -> str:
    if not rows:
        return f"static const uint16_t {name}[1] = {{ 0 }};\n"
    body = "\n".join(f"    {row}," for row in rows)
    return f"static const uint16_t {name}[] = {{\n{body}\n}};\n"


def write_c_header(doom_map: DoomMap, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    textures = texture_table(doom_map)
    lookup = _texture_id_lookup(doom_map)
    bounds = map_bounds(doom_map)
    starts = player_starts(doom_map)
    player = starts[0] if starts else Thing(0, 0, 0, 1, 0)

    lines: list[str] = [
        "/* Generated by tools.wad2ng.cli compile-map. Do not commit WAD-derived generated output. */",
        "#ifndef DOOM_AES_M2_MAP_DATA_H",
        "#define DOOM_AES_M2_MAP_DATA_H",
        "",
        "#include <stdint.h>",
        "",
        f"#define M2_MAP_NAME \"{doom_map.name}\"",
        f"#define M2_VERTEX_COUNT {len(doom_map.vertices)}u",
        f"#define M2_SECTOR_COUNT {len(doom_map.sectors)}u",
        f"#define M2_SIDEDEF_COUNT {len(doom_map.sidedefs)}u",
        f"#define M2_LINEDEF_COUNT {len(doom_map.linedefs)}u",
        f"#define M2_SEG_COUNT {len(doom_map.segs)}u",
        f"#define M2_SUBSECTOR_COUNT {len(doom_map.subsectors)}u",
        f"#define M2_NODE_COUNT {len(doom_map.nodes)}u",
        f"#define M2_THING_COUNT {len(doom_map.things)}u",
        f"#define M2_TEXTURE_COUNT {len(textures)}u",
        f"#define M2_BOUNDS_MIN_X {bounds['min_x']}",
        f"#define M2_BOUNDS_MAX_X {bounds['max_x']}",
        f"#define M2_BOUNDS_MIN_Y {bounds['min_y']}",
        f"#define M2_BOUNDS_MAX_Y {bounds['max_y']}",
        f"#define M2_PLAYER_START_X {player.x}",
        f"#define M2_PLAYER_START_Y {player.y}",
        f"#define M2_PLAYER_START_ANGLE {player.angle}",
        "",
        "typedef struct { int32_t x; int32_t y; } m2_vertex_t;",
        "typedef struct { int16_t floor; int16_t ceil; uint16_t light; uint16_t special; uint16_t tag; } m2_sector_t;",
        "typedef struct { int16_t xoff; int16_t yoff; uint16_t upper; uint16_t lower; uint16_t middle; int16_t sector; } m2_sidedef_t;",
        "typedef struct { uint16_t v1; uint16_t v2; uint16_t flags; uint16_t special; uint16_t tag; int16_t right; int16_t left; } m2_linedef_t;",
        "typedef struct { uint16_t v1; uint16_t v2; int16_t angle; uint16_t linedef; int16_t side; int16_t offset; uint16_t length; } m2_seg_t;",
        "typedef struct { uint16_t seg_count; uint16_t first_seg; } m2_subsector_t;",
        "typedef struct { int16_t x; int16_t y; int16_t dx; int16_t dy; int16_t bbox[2][4]; uint16_t child[2]; } m2_node_t;",
        "",
        "static const m2_vertex_t m2_vertices[] = {",
    ]
    lines.extend(f"    {{ {fixed16(vertex.x)}, {fixed16(vertex.y)} }}," for vertex in doom_map.vertices)
    lines.append("};")
    lines.append("")
    lines.append("static const m2_sector_t m2_sectors[] = {")
    lines.extend(
        f"    {{ {sector.floor_height}, {sector.ceiling_height}, {sector.light}u, {sector.special}u, {sector.tag}u }},"
        for sector in doom_map.sectors
    )
    lines.append("};")
    lines.append("")
    lines.append("static const m2_sidedef_t m2_sidedefs[] = {")
    lines.extend(
        "    {{ {xoff}, {yoff}, {upper}u, {lower}u, {middle}u, {sector} }},".format(
            xoff=side.x_offset,
            yoff=side.y_offset,
            upper=_texture_id(side.upper, lookup),
            lower=_texture_id(side.lower, lookup),
            middle=_texture_id(side.middle, lookup),
            sector=side.sector,
        )
        for side in doom_map.sidedefs
    )
    lines.append("};")
    lines.append("")
    lines.append("static const m2_linedef_t m2_linedefs[] = {")
    lines.extend(
        "    {{ {v1}u, {v2}u, {flags}u, {special}u, {tag}u, {right}, {left} }},".format(
            v1=line.v1,
            v2=line.v2,
            flags=line.flags,
            special=line.special,
            tag=line.tag,
            right=_signed_sidedef_index(line.right_sidedef),
            left=_signed_sidedef_index(line.left_sidedef),
        )
        for line in doom_map.linedefs
    )
    lines.append("};")
    lines.append("")
    lines.append("static const m2_seg_t m2_segs[] = {")
    lines.extend(
        f"    {{ {seg.v1}u, {seg.v2}u, {seg.angle}, {seg.linedef}u, {seg.side}, {seg.offset}, {_seg_length(doom_map, seg)}u }},"
        for seg in doom_map.segs
    )
    lines.append("};")
    lines.append("")
    lines.append("static const m2_subsector_t m2_subsectors[] = {")
    lines.extend(f"    {{ {sub.seg_count}u, {sub.first_seg}u }}," for sub in doom_map.subsectors)
    lines.append("};")
    lines.append("")
    lines.append("static const m2_node_t m2_nodes[] = {")
    lines.extend(
        "    {{ {x}, {y}, {dx}, {dy}, {{ {{ {b00}, {b01}, {b02}, {b03} }}, {{ {b10}, {b11}, {b12}, {b13} }} }}, {{ {c0}u, {c1}u }} }},".format(
            x=node.x,
            y=node.y,
            dx=node.dx,
            dy=node.dy,
            b00=node.bbox[0][0],
            b01=node.bbox[0][1],
            b02=node.bbox[0][2],
            b03=node.bbox[0][3],
            b10=node.bbox[1][0],
            b11=node.bbox[1][1],
            b12=node.bbox[1][2],
            b13=node.bbox[1][3],
            c0=node.child[0],
            c1=node.child[1],
        )
        for node in doom_map.nodes
    )
    lines.append("};")
    lines.append("")
    lines.append("#endif")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_svg_preview(doom_map: DoomMap, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bounds = map_bounds(doom_map)
    map_w = max(1, bounds["max_x"] - bounds["min_x"])
    map_h = max(1, bounds["max_y"] - bounds["min_y"])
    margin = 32
    max_canvas = 1200
    scale = min((max_canvas - margin * 2) / map_w, (max_canvas - margin * 2) / map_h)
    width = int(map_w * scale + margin * 2)
    height = int(map_h * scale + margin * 2)

    def sx(x: int) -> float:
        return margin + (x - bounds["min_x"]) * scale

    def sy(y: int) -> float:
        return margin + (bounds["max_y"] - y) * scale

    elements = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#080808"/>',
        f'<text x="16" y="24" fill="#f2f2f2" font-family="monospace" font-size="14">{doom_map.name} walls: '
        f'{len(doom_map.linedefs)} lines, {len(doom_map.sectors)} sectors, {len(texture_table(doom_map))} textures</text>',
    ]
    for line in doom_map.linedefs:
        a = doom_map.vertices[line.v1]
        b = doom_map.vertices[line.v2]
        two_sided = line.left_sidedef >= 0
        special = line.special != 0
        color = "#6bb8ff" if two_sided else "#f0f0f0"
        if special:
            color = "#ffd166"
        stroke_width = "1.2" if two_sided else "2.0"
        elements.append(
            '<line x1="{:.2f}" y1="{:.2f}" x2="{:.2f}" y2="{:.2f}" stroke="{}" stroke-width="{}" '
            'stroke-linecap="round"/>'.format(sx(a.x), sy(a.y), sx(b.x), sy(b.y), color, stroke_width)
        )
    for start in player_starts(doom_map):
        angle_rad = start.angle * math.pi / 180.0
        x0 = sx(start.x)
        y0 = sy(start.y)
        x1 = x0 + 22.0 * math.cos(angle_rad)
        y1 = y0 - 22.0 * math.sin(angle_rad)
        elements.append(f'<circle cx="{x0:.2f}" cy="{y0:.2f}" r="7" fill="#ff4d6d"/>')
        elements.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="#ff4d6d" stroke-width="3"/>')
    elements.append("</svg>")
    path.write_text("\n".join(elements), encoding="utf-8")


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
