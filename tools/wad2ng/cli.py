from __future__ import annotations

import argparse
import json
from pathlib import Path

from .doom_picture import (
    looks_like_picture,
    read_playpal,
    render_picture,
    split_vertical_strips,
    tile_count_for_strip,
    upscale_to_height,
)
from .wad import Lump, Wad


def safe_name(lump: Lump) -> str:
    return f"{lump.index:05d}_{lump.name}"


def command_inspect(args: argparse.Namespace) -> int:
    wad = Wad(Path(args.wad))
    print(json.dumps(wad.summary(), indent=2))
    return 0


def selected_graphic_lumps(wad: Wad, namespace: str) -> list[tuple[str, Lump]]:
    selected: list[tuple[str, Lump]] = []
    namespaces = ["sprites", "patches", "patches2"] if namespace == "all" else [namespace]
    for ns in namespaces:
        for lump in wad.namespace_lumps(ns):
            data = wad.read_lump(lump)
            if looks_like_picture(data):
                selected.append((ns, lump))
    return selected


def command_extract_graphics(args: argparse.Namespace) -> int:
    wad = Wad(Path(args.wad))
    out = Path(args.out)
    png_dir = out / "png"
    upscaled_dir = out / "png_upscaled"
    strips_dir = out / "strips"
    manifests_dir = out / "manifests"
    for directory in (png_dir, upscaled_dir, strips_dir, manifests_dir):
        directory.mkdir(parents=True, exist_ok=True)

    playpal = wad.find_one("PLAYPAL")
    if playpal is None:
        raise SystemExit("PLAYPAL not found; cannot render Doom indexed graphics")
    palette = read_playpal(wad.read_lump(playpal), args.palette)

    graphics = selected_graphic_lumps(wad, args.namespace)
    if args.limit:
        graphics = graphics[: args.limit]

    manifest = {
        "wad": str(Path(args.wad)),
        "palette": args.palette,
        "namespace": args.namespace,
        "upscale_to_height": args.upscale_to_height,
        "strip_width": 16,
        "assets": [],
    }

    for namespace, lump in graphics:
        data = wad.read_lump(lump)
        image, info = render_picture(data, palette)
        base = safe_name(lump)
        png_path = png_dir / namespace / f"{base}.png"
        png_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(png_path)

        output_image = image
        scale = 1.0
        upscaled_path = None
        if args.upscale_to_height:
            output_image, scale = upscale_to_height(image, args.upscale_to_height)
            upscaled_path = upscaled_dir / namespace / f"{base}.png"
            upscaled_path.parent.mkdir(parents=True, exist_ok=True)
            output_image.save(upscaled_path)

        strip_records = []
        if args.split_strips:
            for strip_index, strip in split_vertical_strips(output_image, 16):
                strip_path = strips_dir / namespace / base / f"strip_{strip_index:02d}.png"
                strip_path.parent.mkdir(parents=True, exist_ok=True)
                strip.save(strip_path)
                strip_records.append(
                    {
                        "index": strip_index,
                        "path": str(strip_path.relative_to(out)),
                        "width": strip.width,
                        "height": strip.height,
                        "tiles": tile_count_for_strip(strip.height),
                        "bytes_4bpp": tile_count_for_strip(strip.height) * 128,
                    }
                )

        manifest["assets"].append(
            {
                "name": lump.name,
                "lump_index": lump.index,
                "namespace": namespace,
                "source": {
                    "width": info.width,
                    "height": info.height,
                    "left_offset": info.left_offset,
                    "top_offset": info.top_offset,
                    "path": str(png_path.relative_to(out)),
                },
                "planned": {
                    "scale": scale,
                    "width": output_image.width,
                    "height": output_image.height,
                    "upscaled_path": str(upscaled_path.relative_to(out)) if upscaled_path else None,
                    "strip_count": len(strip_records) if args.split_strips else None,
                    "tile_count": sum(item["tiles"] for item in strip_records) if args.split_strips else None,
                    "bytes_4bpp": sum(item["bytes_4bpp"] for item in strip_records) if args.split_strips else None,
                },
                "strips": strip_records,
            }
        )

    manifest_path = manifests_dir / "graphics_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"assets": len(manifest["assets"]), "manifest": str(manifest_path)}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Doom WAD to Neo Geo asset pipeline helper")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect = sub.add_parser("inspect", help="Inspect a WAD and print maps/namespaces")
    inspect.add_argument("wad")
    inspect.set_defaults(func=command_inspect)

    extract = sub.add_parser("extract-graphics", help="Bulk-render Doom patch/sprite graphics to PNG and metadata")
    extract.add_argument("wad")
    extract.add_argument("--out", required=True)
    extract.add_argument("--namespace", choices=["sprites", "patches", "patches2", "all"], default="sprites")
    extract.add_argument("--palette", type=int, default=0)
    extract.add_argument("--limit", type=int, default=0)
    extract.add_argument("--upscale-to-height", type=int, default=0)
    extract.add_argument("--split-strips", action="store_true")
    extract.set_defaults(func=command_extract_graphics)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

