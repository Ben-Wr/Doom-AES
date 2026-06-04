# M2 Result

Date: 2026-06-04

Status: **M2 runtime boots in MAME with real E1M1 geometry and WAD-derived wall-card art. Full recognizability gate still pending.**

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
wall texture compiler: TEXTURE1/TEXTURE2 + PNAMES patch composition
194-card E1M1 wall atlas from 32 used textures, stored as 16px U-slice cards
generated wall-card lookup header: texture base card, slice count, family fallback
synthetic host test for map parsing and big-endian output
M2 Makefile target for local ignored DOOM1.WAD input
m2.neo ngdevkit ROM generated from local E1M1 header
real E1M1 BSP traversal, subsector walk, and seg projection
precomputed seg lengths for steadier runtime U-slice selection
conservative BSP branch culling from node bounding boxes
real upper/middle/lower wall role emission from E1M1 sectors/sidedefs
deterministic merge/degrade pass targeting sprite headroom below the 96-sprite hard line
SCB1 texture tilemap rewrite cap with deferred card changes for vblank safety
fix-layer overlay for BSP/seg/sprite/SCB/degrade/texture-rewrite metrics
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
wall cards:   194
atlas tiles:  6208
atlas bytes:  794624 raw 4bpp (0.76 MiB)
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
[~] Deterministic first-pass degrade ladder is wired into the runtime.
[ ] Worst-case scene suite is wired and logged.
[ ] Recognizable E1M1 walls-only gate captured in MAME.
```

## MAME Runtime Capture

Command:

```sh
make -C experiments/milestone2_e1m1_walls WAD=../../iwads/DOOM1.WAD mame-capture
```

Native screenshot:

```text
build/snap/neogeo/0000.png
```

Observed overlay in the captured auto-demo view:

```text
position:            1056, -3616
angle:               22
LOD pass:             4
bucket size:         64 px
nodes visited:      134
nodes culled:        10
subsectors visited: 125
segs visited:       384
sprites emitted:     77
peak sprites/line:   35
SCB words/vblank:  1383
max sprites:         92
max peak:            45
max SCB words:     1556
min FPS budget:      60
texture rewrites:    18 current, 20 max
texture defers:       0 current, 72 max
degrade flags:    $0001 (merged wall buckets only)
RAM high-water:   55296 bytes
```

This pass proves real E1M1 geometry traversal, real WAD-derived wall materials,
runtime card selection, SCB1 rewrite limiting, and conservative branch culling.
It does **not** yet prove final wall readability: columns are still coarse and
texture continuity across chunks is approximate.

MAME bench:

```text
Average speed: 482.11% (60-second capture, conservative BSP culling enabled)
Average speed: 2125.33% (2-second MAME bench)
```
