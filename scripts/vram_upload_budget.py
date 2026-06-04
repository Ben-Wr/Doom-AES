#!/usr/bin/env python3
"""Estimate representative Neo Geo VRAM/SCB upload pressure per frame.

Grounded in references/neogeodev/md/VRAM.md and Display_timing.md:

  - VRAM is reached only through REG_VRAMADDR/REG_VRAMRW/REG_VRAMMOD ($3C0000-4).
    REG_VRAMMOD auto-increments the address after each write, so a sprite's
    contiguous SCB table streams without re-setting the address per word.
  - SNK's documented minimum spacing between two successive VRAM data writes is
    12 CPU cycles (>=24 mclk). Setting a fresh address costs >=16 CPU cycles.
    So streamed writes are bound by ~12 cycles/word; isolated writes by ~16.
  - NTSC vblank is ~40 scanlines (8 vsync + 16 top + 16 bottom border) of 1536
    mclk each = ~61,440 mclk = ~2.56 ms = ~30,720 CPU cycles at 12 MHz.

The load-bearing fact this script exists to make obvious: an SCB1 tilemap is up
to 64 words per sprite (32 tiles * 2 words). Rewriting every wall sprite's
tilemap every frame does NOT fit in vblank. The renderer survives only by
caching tilemaps and rewriting SCB1 ONLY for sprites whose card id changed this
frame (--wall-card-change-frac). Unchanged sprites pay just control words.
"""
import argparse
import sys


parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--cpu-mhz", type=float, default=12.0)
parser.add_argument("--vblank-ms", type=float, default=2.56, help="NTSC vblank ~= 40 scanlines")
parser.add_argument("--cycles-per-word", type=int, default=12, help="streamed write spacing (>=12); use 16 for isolated address-set writes")
parser.add_argument("--practical-fill", type=float, default=0.65, help="M0B-calibrated fraction of theoretical writes to trust (loop overhead, address sets, zone crossings)")
parser.add_argument("--wall-sprites", type=int, default=40, help="visible wall chunks crossing the center scanline")
parser.add_argument("--thing-sprites", type=int, default=24, help="thing/weapon strips crossing center")
parser.add_argument("--wall-height-tiles", type=int, default=32, help="SCB1 tilemap words = 2 * this when a card changes")
parser.add_argument("--thing-height-tiles", type=int, default=12)
parser.add_argument("--control-words-per-sprite", type=int, default=3, help="SCB2 shrink + SCB3 Y/size + SCB4 X")
parser.add_argument("--wall-card-change-frac", type=float, default=0.25,
                    help="fraction of wall sprites needing a full SCB1 tilemap rewrite this frame (temporal coherence: small view change => small fraction)")
parser.add_argument("--thing-card-change-frac", type=float, default=1.0,
                    help="things move/animate, so usually need fresh tilemaps")
args = parser.parse_args()

cycles = args.cpu_mhz * 1_000_000 * (args.vblank_ms / 1000.0)
theoretical_words = cycles / args.cycles_per_word
practical_words = theoretical_words * args.practical_fill

scb1_wall = 2 * args.wall_height_tiles
scb1_thing = 2 * args.thing_height_tiles

# Every sprite that stays visible pays control words. Only the fraction whose
# card id changed this frame also pays the SCB1 tilemap rewrite.
wall_changed = round(args.wall_sprites * args.wall_card_change_frac)
thing_changed = round(args.thing_sprites * args.thing_card_change_frac)

wall_words = args.wall_sprites * args.control_words_per_sprite + wall_changed * scb1_wall
thing_words = args.thing_sprites * args.control_words_per_sprite + thing_changed * scb1_thing
scene_words = wall_words + thing_words

worst_case = (args.wall_sprites * (scb1_wall + args.control_words_per_sprite)
              + args.thing_sprites * (scb1_thing + args.control_words_per_sprite))

print("VRAM/SCB upload estimate")
print(f"  cpu:                     {args.cpu_mhz:.2f} MHz")
print(f"  vblank window:           {args.vblank_ms:.2f} ms (~{cycles:,.0f} CPU cycles)")
print(f"  cycles/word:             {args.cycles_per_word} (12=streamed, 16=isolated)")
print(f"  theoretical words:       {theoretical_words:,.0f}")
print(f"  practical words:         {practical_words:,.0f}")
print("")
print(f"  wall sprites:            {args.wall_sprites} ({wall_changed} need new tilemap @ {scb1_wall}w)")
print(f"  thing sprites:           {args.thing_sprites} ({thing_changed} need new tilemap @ {scb1_thing}w)")
print(f"  wall words:              {wall_words:,}")
print(f"  thing words:             {thing_words:,}")
print(f"  scene words (cached):    {scene_words:,}")
print(f"  scene words (worst case):{worst_case:,}  <- all tilemaps rewritten, never do this in vblank")
print("")
if scene_words > practical_words:
    deficit = scene_words - practical_words
    print(f"WARN: cached scene exceeds vblank budget by {deficit:,.0f} words.")
    print("      -> lower --wall-card-change-frac (more caching), fewer sprites,")
    print("         spread writes across active display, or accept lower fps.")
else:
    print("OK: cached scene fits the vblank upload budget.")
if worst_case > practical_words:
    print(f"NOTE: worst case ({worst_case:,}) is {worst_case / practical_words:.1f}x the budget.")
    print("      This is why SCB1 tilemap caching is mandatory, not optional.")
print("")
print("M0B-calibrated planning estimate. Re-run M0B if the practical upload cap changes.")

# Exit non-zero when the cached scene busts the budget, so CI / run_host_tests.sh
# can treat this as a real gate rather than advisory text.
if scene_words > practical_words:
    sys.exit(1)
