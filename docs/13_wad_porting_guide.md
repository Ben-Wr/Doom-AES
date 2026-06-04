# WAD Porting Guide (Concrete)

This is the step-by-step recipe for turning a user-supplied IWAD into Neo Geo
banks. It is the "how", paired with [04_asset_pipeline.md](04_asset_pipeline.md)
(the "what the compiler outputs") and [09_asset_conversion_pipeline.md](09_asset_conversion_pipeline.md)
(the tool stages). Legal boundary: the tool reads a **local** WAD; the repo never
commits IWAD data. DOOM1.WAD shareware is freely redistributable as an input you
ask the user to supply; registered DOOM.WAD / Doom II only from the user's own copy.

## 0. The data you start from

A WAD is a header + lump directory + lump blobs. `tools/wad2ng/wad.py` already
parses this:

```text
header:  4s magic ("IWAD"/"PWAD"), int32 lumpcount, int32 dir offset   (little-endian)
dir[i]:  int32 file offset, int32 size, 8s name
```

Maps are a marker lump (`E1M1`, `MAPxx`) followed by its data lumps. Graphics
live between namespace markers (`S_START`/`S_END` sprites, `P_*` patches,
`F_*` flats). All Doom integers are little-endian; the Neo Geo 68000 is
big-endian, so **every multi-byte field must be byte-swapped on output** — make
the encoder write big-endian and add a test that round-trips a known value.

## 1. Geometry: lumps -> banked map tables

Per map, read these lumps (formats: doomwiki.org/wiki/WAD; fields below are the
vanilla layouts):

```text
VERTEXES  int16 x, int16 y                              (map units)
LINEDEFS  v1,v2, flags, special, tag, rightSD, leftSD   (int16 each; -1 = no side)
SIDEDEFS  xoff,yoff, upper[8], lower[8], middle[8], sector
SECTORS   floorH, ceilH, floorFlat[8], ceilFlat[8], light, special, tag
THINGS    x, y, angle, type, flags
SEGS      v1,v2, angle, linedef, side, offset
SSECTORS  segcount, firstseg
NODES     x,y,dx,dy, bbox[2][4], child[2]               (BSP; child MSB = leaf)
BLOCKMAP  collision acceleration grid
REJECT    sector-pair visibility bitmap (optional cull hint)
```

Do not write a nodebuilder. Run **ZDBSP** offline to (re)build NODES/SSECTORS/SEGS
(it is robust and handles modern maps; glBSP is the fallback). Then emit
big-endian, compact, **read-only** tables straight into P-ROM banks:

```text
- vertices as 16.16 fixed point (see section 4)
- linedefs/sidedefs with material ids resolved (not name strings)
- sector table with floor/ceil heights as fixed point
- BSP node + subsector + seg tables, prebuilt
- thing spawn table (Neo Geo mobj type ids)
- blockmap (collision); reject (optional cull)
- per-map texture-use and sprite-use lists (drives which C-ROM banks load)
```

Bank layout note: code + dispatch live in the fixed region `$000000-$1FFFFF`;
page per-map data through the `$200000-$2FFFFF` window (see
[08](08_load_bearing_hardware_truths.md) section 12). One map's tables should fit
one bank.

## 2. Wall textures: TEXTURE1/PNAMES -> 16px cards

Doom wall textures are composites: `TEXTURE1`/`TEXTURE2` describe how named
patches (indexed via `PNAMES`) stack into a final texture. Offline:

```text
1. Compose each used texture from its patches into one indexed image.
2. Quantize to a 15-color material palette (+ index 0 transparent). See section 3.
3. Tile the composed texture VERTICALLY to 512px (32 tiles) -- the max card height.
4. Slice into 16px-wide vertical "U cards". Each card = one 16px horizontal window.
5. Generate a few vertical-phase variants (pegging quantized to 4/8/16px).
6. Generate brightness palettes (8-16 bands) -- palette data, not pixel data.
7. Encode tiles to Neo Geo planar (section 5); write the card table to P-ROM.
```

You do NOT pre-bake every distance. Hardware Y/X shrink covers scaling; mip/
coverage cards are a later shimmer fix only (see [08](08_load_bearing_hardware_truths.md) section 9).

## 3. Palette reduction

Doom art is 256-color indexed via `PLAYPAL` (14 palettes; index 0 is normal).
`COLORMAP` is the 34 light levels (32 fades + invuln + 1). Neo Geo gives 15
colors per palette, 16-bit RGB (4 bits/channel after the Neo Geo's format). So:

```text
- Read PLAYPAL[0] as the base RGB palette (wad2ng.read_playpal already does this).
- For each material, pick a 15-color sub-palette (median-cut / k-means over the
  texture's used colors), remap pixels to it.
- Build brightness bands by darkening that sub-palette (mimic COLORMAP fades) ->
  one Neo Geo palette per band. Lighting at runtime = pick the band, not new art.
- Global tints (berserk red, radsuit green, item flash) = whole-palette writes.
```

Budget: 256 palettes total on the active bank. Spend them deliberately
(materials x bands + monster families + weapon + HUD). Track palette pressure in
the compiler report.

## 4. Coordinates, angles, fixed point

Keep Doom's math; it was built for portability and maps onto the 68000:

```text
- Positions/distances: 16.16 signed fixed point. 68000 has 32-bit regs and a
  16x16->32 multiply; emulate 32x32 where needed.
- Angles: BAM (binary angle, 0..$FFFFFFFF around the circle). Precompute sine/
  cosine/tangent and reciprocal/scale tables into ROM; never compute trig live.
- The per-column scale divide is the cost center (68000 divide ~140 cycles).
  At ~40 columns instead of 320 you do far fewer; replace with ROM scale tables
  keyed by distance where possible.
```

## 5. Neo Geo planar tile encoding (the error-prone step)

A sprite tile is 16x16, 4bpp, 128 bytes, stored as four 8x8 blocks, each row's
bitplanes stored **backwards**, split across odd/even C-ROMs
(Sprite_graphics_format). The verified layout:

```text
- Tile = blocks t1..t4. Block pixel offsets when decoding:
    block0 -> x+8,y+0   block1 -> x+8,y+8   block2 -> x+0,y+0   block3 -> x+0,y+8
- Odd C-ROM (C1,C3..) holds bitplanes 0,1; even C-ROM (C2,C4..) holds bitplanes 2,3.
- Per row, two bytes per ROM: [t,r,bp0],[t,r,bp1] (odd) / [t,r,bp2],[t,r,bp3] (even).
```

Do not hand-roll this blind. Prefer ngdevkit's graphics tools for final C/S-ROM
packing; only write a custom encoder for Doom-specific packing the SDK can't
express, and validate it by decoding your output back to a PNG and diffing
against the source tile (golden test — see [10](10_test_harness_and_profiling.md)).

## 6. Sprites, weapons, sounds

```text
Monsters/items (S_* lumps, patch format -> wad2ng renders them):
  - pre-UPSCALE to the largest on-screen size each will reach (shrink-only!),
  - split into 16px vertical strips, generate near/med/far LODs,
  - mirror rotations where acceptable, quantize to a family palette.
Weapons: author at largest foreground size, best palette, separate muzzle cards.
SFX (DS* lumps, 11025/22050 Hz PCM) -> ADPCM-A/B in V-ROM.
Music (MUS lumps) -> YM2610 FM/PSG arrangement, or sampled approximation.
```

## 7. The compiler must emit a report per build

Non-negotiable (consumed by CI and the budget scripts):

```text
geometry counts; texture/card usage; thing usage; estimated ROM per region;
RAM overlay estimate; SCB1 tilemap + SCB2/3/4 control write estimates;
worst-case sprite-pressure hint per map; list of simplifications applied;
shrink-only violations (must be zero); source/legal provenance.
```

## 8. Minimal end-to-end recipe

```sh
# 0. user supplies their WAD locally (never committed)
scripts/setup_python_tools.sh

# 1. inspect
python3 -m tools.wad2ng.cli inspect iwads/DOOM1.WAD

# 2. bulk-extract graphics, pre-upscaled and strip-split, with manifests
scripts/wad2ng_bulk_extract.sh iwads/DOOM1.WAD build/wad2ng/doom1 --upscale-to-height 192

# 3. (to build) run ZDBSP on the map, emit big-endian map banks  [tool: TODO]
# 4. (to build) compose TEXTURE1 -> cards -> planar tiles         [tool: TODO]
# 5. (to build) pack P/C/V/S/M ROM regions via ngdevkit           [tool: TODO]
```

Steps 3-5 are the unbuilt stages; `tools/wad2ng` currently covers 1-2. Build them
in M2's offline pipeline, gated by the golden tests in
[10_test_harness_and_profiling.md](10_test_harness_and_profiling.md).
