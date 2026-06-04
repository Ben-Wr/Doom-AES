# M2 Result

Date: 2026-06-04

Status: **M2 offline map compile started; E1M1 bank output works. Runtime M2 ROM still pending.**

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
[ ] M2 ROM consumes the generated map bank.
[ ] Full BSP traversal is running on the Neo Geo side.
[ ] Degrade ladder and worst-case scene suite are wired into the runtime.
[ ] Recognizable E1M1 walls-only gate captured in MAME.
```
