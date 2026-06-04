from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import struct


MAP_LUMPS = {
    "THINGS",
    "LINEDEFS",
    "SIDEDEFS",
    "VERTEXES",
    "SEGS",
    "SSECTORS",
    "NODES",
    "SECTORS",
    "REJECT",
    "BLOCKMAP",
}


@dataclass(frozen=True)
class Lump:
    index: int
    name: str
    offset: int
    size: int


class Wad:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        if len(self.data) < 12:
            raise ValueError("file is too small to be a WAD")
        magic, lump_count, directory_offset = struct.unpack_from("<4sii", self.data, 0)
        self.magic = magic.decode("ascii", errors="replace")
        if self.magic not in {"IWAD", "PWAD"}:
            raise ValueError(f"unsupported WAD magic {self.magic!r}")
        if lump_count < 0:
            raise ValueError("WAD lump count is negative")
        if directory_offset < 0:
            raise ValueError("WAD directory offset is negative")
        if directory_offset + lump_count * 16 > len(self.data):
            raise ValueError("WAD directory extends past end of file")
        self.lump_count = lump_count
        self.directory_offset = directory_offset
        self.lumps = self._read_directory()

    def _read_directory(self) -> list[Lump]:
        lumps: list[Lump] = []
        for index in range(self.lump_count):
            pos = self.directory_offset + index * 16
            if pos + 16 > len(self.data):
                raise ValueError("WAD directory extends past end of file")
            offset, size, raw_name = struct.unpack_from("<ii8s", self.data, pos)
            name = raw_name.split(b"\0", 1)[0].decode("ascii", errors="replace").upper()
            if offset < 0:
                raise ValueError(f"lump {name or index!r} has negative offset")
            if size < 0:
                raise ValueError(f"lump {name or index!r} has negative size")
            if offset > len(self.data) or offset + size > len(self.data):
                raise ValueError(f"lump {name or index!r} extends past end of file")
            lumps.append(Lump(index=index, name=name, offset=offset, size=size))
        return lumps

    def read_lump(self, lump: Lump) -> bytes:
        if lump.offset < 0 or lump.size < 0 or lump.offset + lump.size > len(self.data):
            raise ValueError(f"lump {lump.name!r} extends past end of file")
        return self.data[lump.offset : lump.offset + lump.size]

    def find_one(self, name: str) -> Lump | None:
        wanted = name.upper()
        for lump in self.lumps:
            if lump.name == wanted:
                return lump
        return None

    def namespace_lumps(self, namespace: str) -> list[Lump]:
        markers = {
            "sprites": ("S_START", "S_END"),
            "patches": ("P_START", "P_END"),
            "patches2": ("PP_START", "PP_END"),
            "flats": ("F_START", "F_END"),
        }
        if namespace not in markers:
            raise ValueError(f"unknown namespace {namespace!r}")
        start, end = markers[namespace]
        active = False
        selected: list[Lump] = []
        for lump in self.lumps:
            if lump.name == start:
                active = True
                continue
            if lump.name == end:
                active = False
                continue
            if active and lump.size > 0:
                selected.append(lump)
        return selected

    def map_markers(self) -> list[str]:
        markers: list[str] = []
        pattern = re.compile(r"^(E[1-9]M[1-9]|MAP[0-9][0-9])$")
        for i, lump in enumerate(self.lumps):
            if not pattern.match(lump.name):
                continue
            following = {item.name for item in self.lumps[i + 1 : i + 12]}
            if MAP_LUMPS.intersection(following):
                markers.append(lump.name)
        return markers

    def summary(self) -> dict:
        namespaces = {}
        for name in ("sprites", "patches", "patches2", "flats"):
            try:
                namespaces[name] = len(self.namespace_lumps(name))
            except ValueError:
                namespaces[name] = 0
        return {
            "path": str(self.path),
            "magic": self.magic,
            "lump_count": self.lump_count,
            "maps": self.map_markers(),
            "namespaces": namespaces,
            "has_playpal": self.find_one("PLAYPAL") is not None,
        }
