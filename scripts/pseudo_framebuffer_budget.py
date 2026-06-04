#!/usr/bin/env python3
import argparse


def mib(value: int) -> float:
    return value / (1024 * 1024)


parser = argparse.ArgumentParser(description="Estimate the 4x4 ROM-backed pseudo-framebuffer dictionary.")
parser.add_argument("--logical-width", type=int, default=80)
parser.add_argument("--logical-height", type=int, default=56)
parser.add_argument("--block", type=int, default=4)
parser.add_argument("--tile-bytes", type=int, default=128)
parser.add_argument("--mask-bits", type=int, default=16)
args = parser.parse_args()

blocks_x = args.logical_width // args.block
blocks_y = args.logical_height // args.block
visible_tiles = blocks_x * blocks_y
masks = 2 ** args.mask_bits
dictionary = masks * args.tile_bytes

print("ROM-backed pseudo-framebuffer estimate")
print(f"  logical view:       {args.logical_width}x{args.logical_height}")
print(f"  logical block:      {args.block}x{args.block}")
print(f"  visible tiles:      {blocks_x}x{blocks_y} = {visible_tiles}")
print(f"  mask dictionary:    {masks:,} tiles")
print(f"  tile bytes:         {args.tile_bytes}")
print(f"  C-ROM dictionary:   {dictionary:,} bytes ({mib(dictionary):.2f} MiB)")
print(f"  scanline sprites:   {blocks_x} vertical strips")

