#!/usr/bin/env python3
import argparse


parser = argparse.ArgumentParser(
    description="Estimate representative Neo Geo VRAM/SCB upload pressure."
)
parser.add_argument("--cpu-mhz", type=float, default=12.0)
parser.add_argument("--vblank-ms", type=float, default=2.5)
parser.add_argument("--cycles-per-word", type=int, default=16)
parser.add_argument("--practical-fill", type=float, default=0.65, help="fraction of theoretical writes to trust")
parser.add_argument("--wall-sprites", type=int, default=20)
parser.add_argument("--thing-sprites", type=int, default=24)
parser.add_argument("--wall-height-tiles", type=int, default=32)
parser.add_argument("--thing-height-tiles", type=int, default=12)
parser.add_argument("--control-words-per-sprite", type=int, default=3, help="SCB2/3/4 rough words")
args = parser.parse_args()

cycles = args.cpu_mhz * 1_000_000 * (args.vblank_ms / 1000.0)
theoretical_words = cycles / args.cycles_per_word
practical_words = theoretical_words * args.practical_fill

wall_words_each = args.wall_height_tiles * 2 + args.control_words_per_sprite
thing_words_each = args.thing_height_tiles * 2 + args.control_words_per_sprite
scene_words = args.wall_sprites * wall_words_each + args.thing_sprites * thing_words_each

print("VRAM/SCB upload estimate")
print(f"  cpu:                     {args.cpu_mhz:.2f} MHz")
print(f"  update window:           {args.vblank_ms:.2f} ms")
print(f"  cycles/word estimate:    {args.cycles_per_word}")
print(f"  theoretical words:       {theoretical_words:,.0f}")
print(f"  practical words:         {practical_words:,.0f}")
print("")
print(f"  wall sprites:            {args.wall_sprites}")
print(f"  wall words each:         {wall_words_each}")
print(f"  thing sprites:           {args.thing_sprites}")
print(f"  thing words each:        {thing_words_each}")
print(f"  scene words:             {scene_words:,}")
print("")
if scene_words > practical_words:
    print("WARN: estimated scene exceeds practical upload budget.")
else:
    print("OK: estimated scene fits practical upload budget.")
print("")
print("This is only a planning estimate. Milestone 0B must measure real SCB writes.")
