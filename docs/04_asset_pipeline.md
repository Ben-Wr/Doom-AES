# Asset Pipeline

The port lives or dies in the PC-side compiler.

The Neo Geo runtime should see compact, banked, already-decided data. It should not parse WADs, compose patches, choose palettes globally, or build nodes at runtime.

## Inputs

Accept:

```text
DOOM1.WAD shareware, local/user-provided unless distribution is explicitly handled
DOOM.WAD registered, user-provided
Free IWAD-compatible asset sets, if licenses permit
```

Do not commit these inputs by default.

Use an existing offline nodebuilder such as ZDBSP or glBSP. Do not spend early project time writing a nodebuilder.

## Map Compiler

Read WAD lumps:

```text
VERTEXES
LINEDEFS
SIDEDEFS
SECTORS
SEGS
SSECTORS
NODES
THINGS
BLOCKMAP
REJECT
TEXTURE1/TEXTURE2
PNAMES
```

Output Neo Geo map banks:

```text
fixed-point vertices
compact linedefs
compact sidedef references
sector table
subsector table
BSP node table
thing spawn table
collision/blockmap data
reject/visibility hints
line special table
per-map texture-use table
per-map sprite-use table
LOD hints
```

## Map Simplification Passes

Allowed if needed:

```text
merge tiny decorative sectors
snap near-collinear vertices
remove invisible micro-detail
replace rare textures
cap pathological simultaneous movers
lower monster counts in budget-breaking rooms
author per-map LOD hints
```

Do not silently change gameplay-critical layout. Keep a report for every simplification.

## Wall Texture Compiler

For each used wall material:

```text
compose Doom patches into final texture
reduce to one or more 15-color material palettes
generate brightness/tint palettes
generate max-height wall cards
generate 16 px U slices
generate vertical phase variants
write C-ROM tile data
write P-ROM metadata
```

Card dimensions:

```text
16 px wide x up to 512 px tall
32 Neo Geo tiles high
32 * 128 bytes = 4096 bytes per full-height card
```

Baseline scaling:

```text
use hardware X shrink as nearest-neighbor horizontal decimation
use hardware Y shrink as vertical decimation
```

Optional quality coverage modes, added only where shimmer is ugly:

```text
4 texels -> 16 px
8 texels -> 16 px
16 texels -> 16 px
32 texels -> 16 px
64 texels -> 16 px
```

## Sprite Compiler

For each monster/item/projectile:

```text
extract frames and rotations
pre-upscale source art to maximum on-screen size
choose mirrored rotations where acceptable
reduce to 15-color family palettes
generate brightness/tint palettes
split into 16-pixel vertical strips
generate near/medium/far LODs
write C-ROM tiles
write animation metadata
```

## Weapon Compiler

Weapons get higher priority than normal things.

```text
author at largest foreground size
preserve silhouette
use better palette allocation
pre-split into foreground strips
separate muzzle flash cards
separate firing/reload frame metadata
```

## Pseudo-Framebuffer Compiler

Generate the universal 4x4 two-color mask dictionary only if a runtime-unknown bitmap need survives review:

```text
65,536 masks
16x16 tile per mask
128 bytes per tile
8 MiB total
palette indices 1 and 2 are the two selected colors
```

The same dictionary can be recolored through sprite palette attributes.

This is not a v1 dependency. Static screens should use normal sprite/fix compositions.

## Audio Compiler

```text
SFX -> ADPCM samples in V-ROM
music -> YM2610 FM/PSG arrangement or sample-backed approximation
sound driver -> M1/Z80 ROM
```

## Reports The Compiler Must Emit

Every compiled map should produce:

```text
map geometry counts
texture/card usage
thing usage
estimated ROM size
estimated RAM overlays
estimated SCB1 tilemap writes
estimated SCB2/3/4 control writes
worst-case sprite pressure hints
lost/simplified features
legal/source asset provenance
```

## Non-Goals

```text
No runtime WAD loader
No commercial IWAD data in repo
No direct C-ROM CPU texture sampling
No true textured floor/ceiling compiler for version 1
No exact PC palette/colormap reproduction
No custom nodebuilder in the first phase
```
