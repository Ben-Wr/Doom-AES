# M2 Result

Date: 2026-06-04

Status: **M2 runtime first pass boots in MAME and consumes generated E1M1 map data. Full recognizability gate still pending.**

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
synthetic host test for map parsing and big-endian output
M2 Makefile target for local ignored DOOM1.WAD input
m2.neo ngdevkit ROM generated from local E1M1 header
real E1M1 BSP traversal, subsector walk, and seg projection
real upper/middle/lower wall role emission from E1M1 sectors/sidedefs
deterministic merge/degrade pass targeting sprite headroom below the 96-sprite hard line
fix-layer overlay for BSP/seg/sprite/SCB/degrade metrics
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
bank bytes:  37030 actual
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
[~] Deterministic first-pass degrade ladder is wired into the runtime.
[ ] Wall texture composition/card selection is wired.
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
position:            1066, -3616
angle:               24
LOD pass:             4
bucket size:         64 px
nodes visited:      236
subsectors visited: 237
segs visited:       732
sprites emitted:     82
peak sprites/line:   45
SCB words/vblank:   246
max sprites:         82
max peak:            45
max SCB words:      246
min FPS budget:      60
degrade flags:    $0001 (merged wall buckets only)
RAM high-water:   55296 bytes
```

This first runtime pass uses one preloaded placeholder wall card, so it proves
real E1M1 geometry traversal and deterministic pressure management, not final
wall-art recognizability.

MAME bench:

```text
Average speed: 1582.91% (2 seconds)
```
