# M2 Result

Date: 2026-06-04

Status: **M2 runtime boots in MAME with real E1M1 geometry, WAD-derived wall cards, and a
hardened (numeric) capture gate. NOT passing the M2 readability bar.** A 2026-06-04 analysis
pass (see [docs/14](../../docs/14_renderer_diagnosis_and_optimal_path.md)) identified the
"garbled vertical" corruption as a real, unfixed bug — a fixed SCB3 window size — and found
that the wall budget was reduced (92→40) to chase the fps floor even though no sprite/SCB
limit was being hit. The numeric gate is green; the readability gate is not yet defined or met.

## Implemented

```text
wad2ng compile-map command
real Doom map lump parsing: THINGS, VERTEXES, LINEDEFS, SIDEDEFS, SECTORS, SEGS, SSECTORS, NODES
per-map wall texture dependency table
player starts, bounds, thing counts, raw REJECT/BLOCKMAP sizes
big-endian compact map bank for 68000-side consumption
16.16 fixed-point vertex output
generated C header for ROM-side renderer experiments
generated SVG map preview for visual inspection
wall texture compiler: TEXTURE1/TEXTURE2 + PNAMES patch composition with cached patch rendering
opaque M2 wall cards: no pen-0 wall holes, blended texture/detail cards for fallback readability
195-card E1M1 wall atlas from 32 used textures plus one reserved background card, stored as 16px x 256px U-slice cards
generated wall-card lookup header: texture base card, slice count, family fallback
synthetic host test for map parsing and big-endian output
central WAD cross-reference validation before C/header output
M2 Makefile target for local ignored DOOM1.WAD input
m2.neo ngdevkit ROM generated from local E1M1 header
real E1M1 BSP traversal, subsector walk, and seg projection
cached vertex coordinates and per-pass trigonometry for faster runtime projection
precomputed seg lengths for steadier runtime U-slice selection
conservative BSP branch culling from node bounding boxes
real upper/middle/lower wall role emission from E1M1 sectors/sidedefs
deterministic merge/degrade pass targeting sprite headroom below the 96-sprite hard line, with panic degrade forbidden by the gate
SCB1 texture tilemap rewrite cap with deferred card changes for vblank safety
row-major wall-card tilemap indexing for generated C-ROM atlas cards
static sky/floor backdrop sprites to remove the all-black void in sparse fallback views
55-wall fallback target with 40 per-frame 16-tile card rewrites; deferred card changes are hidden instead of drawing stale texture data
256px wall-card convention avoids the 32-tile vertical-shrink repeat that caused lower-half stripe corruption
per-strip depth/top-bottom projection for less rectangular wall silhouettes
visual comparison artifacts for source textures, atlas reconstruction, host command projection, and MAME captures
fix-layer overlay for BSP/seg/sprite/SCB/degrade/texture-rewrite metrics
hardened MAME Lua gate for profile liveness, frame progression, SCB/RAM/sprite budgets, panic flags, and named captures
```

## Local E1M1 Compile

Command:

```sh
make -C experiments/milestone2_e1m1_walls WAD=../../iwads/DOOM1.WAD compile-map
```

Generated, ignored outputs:

```text
build/generated/e1m1_map_report.json
build/generated/e1m1_map_bank.bin
build/generated/e1m1_map_data.h
build/generated/e1m1_map_preview.svg
build/generated/e1m1_wall_cards.gif
build/generated/e1m1_wall_cards.h
build/generated/e1m1_wall_atlas_report.json
```

Observed E1M1 counts from the local WAD:

```text
things:        138
vertices:      467
linedefs:      475
sidedefs:      648
sectors:        85
segs:          732
subsectors:    237
nodes:         236
wall textures: 32
wall cards:   195
atlas tiles:  3120
atlas bytes:  399360 raw 4bpp (0.38 MiB)
bank bytes:  38494 actual
```

Player 1 start:

```text
x 1056, y -3616, angle 90
```

## Gate Notes

```text
[x] Local user-provided WAD is consumed offline only.
[x] Multi-byte map output is big-endian.
[x] Map bank/header outputs are generated under ignored build paths.
[x] M2 ROM consumes the generated E1M1 map header.
[x] Full BSP traversal is running on the Neo Geo side.
[x] WAD-derived wall texture composition/card selection is wired.
[x] Conservative BSP branch culling is wired and visible in overlay.
[x] Deterministic first-pass degrade ladder is wired into the runtime.
[x] Panic degrade now fails MAME capture.
[x] Worst-case auto-demo scene suite is wired, named, captured, and logged.
[~] Coarse merged-wall fallback is captured in MAME; final readability quality pass is still pending.
```

## MAME Runtime Capture

Command:

```sh
make -C experiments/milestone2_e1m1_walls WAD=../../iwads/DOOM1.WAD mame-capture
```

Named screenshots:

```text
build/snap/m2_e1m1_turn_gate.png
build/snap/m2_e1m1_move_gate.png
build/snap/m2_e1m1_strafe_gate.png
build/snap/m2_e1m1_back_gate.png
build/snap/m2_e1m1_scan_gate.png
build/visual/e1m1_source_textures.png
build/visual/e1m1_atlas_groups.png
build/visual/e1m1_host_command_compare.png
build/visual/e1m1_mame_contact_sheet.png
```

Observed hardened gate summary:

```text
profile samples:       1080
frame progressions:     108
max sprites:             75
max peak sprites/line:   75
max SCB words:         1445
max RAM high-water:    4808 bytes
degrade flags:       $0001 (merged wall buckets only)
panic degrade:       absent
captures:                5
```

This pass proves real E1M1 geometry traversal, real WAD-derived wall materials,
runtime card selection, 16-tile SCB1 rewrite limiting, and conservative branch culling.
It also proves the capture harness now rejects panic frames, stale profile
fields, missing frame progression, missing captures, and budget overruns.
It does **not** yet prove wall readability.

## Diagnosis (2026-06-04 analysis pass — see docs/14)

The 512px→256px card change *reduced* the stripe corruption but did **not** fix it; it only
halved the affected window region. The actual cause is still live:

```text
ROOT CAUSE A (corruption): main.c sets size_tiles = CARD_TILE_COUNT (a fixed 256px window)
  for every wall and varies only y_shrink. When the shrunk graphics are shorter than the
  256px window (all far/steep walls), the hardware fills the leftover window with the
  last-line-repeat smear (Sprite_shrinking.md), and texture_card() emits no transparent
  guard line -> the green/white vertical garbage. FIX: dynamic window (ceil(h/16), as M1
  already does) + transparent guard line on every card. Not a cosmetic LOD issue.

ROOT CAUSE B (chunky look): 16px sprite columns cap horizontal resolution at ~20 (40 at
  8px) vs Doom's 320. Fundamental; stylize it, do not optimize it.

MISDIAGNOSIS (fps): walls were cut 92->55->40 to pass the 6fps floor, but this run shows
  max sprites 75/96 and max SCB 1445/1664 -- neither limit was hit. The real per-frame cost
  is CPU (full BSP walk + per-seg/per-chunk divides), which the gate does not measure, and
  bucket_occluded() is a dead stub. FIX: cut CPU (occlusion, precomputed visibility,
  reciprocal tables); restore the wall budget; add a CPU + recognizability (SSIM) gate.
```

floor/ceiling fill is also still a placeholder backdrop (the timer-IRQ two-band split and
palette depth-lighting are not yet wired). Next pass should target the above in order.

MAME bench:

```text
Average speed: 491.19% (latest full host-test MAME gate)
```
