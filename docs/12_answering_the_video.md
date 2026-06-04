# Answering The Video

This project is the reply to Modern Vintage Gamer's "Why a Neo Geo port of Doom
is functionally impossible." MVG's hardware analysis is largely correct; his
**conclusion** is too narrow because it benchmarks the wrong algorithm. This doc
holds the rebuttal so the project never loses the thread. Every claim traces to
`references/neogeodev/md/` (see [08](08_load_bearing_hardware_truths.md)).

## The flip, in one sentence

The Neo Geo isn't bad at Doom — it's bad at a *framebuffer emulation* of Doom.
Doom's renderer is a scaled-vertical-strip compiler, and the Neo Geo is a
scaled-vertical-strip machine. So stop drawing pixels and compile the BSP
straight into the sprite list. **Keep Doom's brain, replace Doom's hands.**

## Two framings the "impossible" case rests on — both wrong targets

```text
Framing 1: "software renderer into a framebuffer."  Genuinely impossible (no
  bitplanes, no framebuffer, C-ROM not on the 68k bus). Correct -- so don't.
Framing 2: "it's a raycaster: one full-height strip per column."  Doom is NOT a
  raycaster. It is a BSP renderer whose back-end emits independently positioned,
  independently Y-scaled, vertically-clipped strips -- which is the verbatim spec
  of the Neo Geo sprite unit.
```

## Objection -> answer

```text
"Several independently positioned, scaled sprites per column, clipped."
   -> That is the Neo Geo sprite unit's native mode. Each SCB sprite is an
      independently positioned (X/Y), Y-shrunk 16px strip. (08 sec 2)

"Diagonal walls need per-pixel varying scale down a column."
   -> Raycaster thinking. In Doom a diagonal wall is still vertical screen columns,
      each a single constant scale (rw_scale/rw_scalestep). Subdivide a seg into
      chunks of ~constant scale, one sprite per chunk; affine per chunk, corrected
      at chunk boundaries. PS1-grade warp on grazing angles. (03 + 08 sec 1,4)

"Variable floor/ceiling heights, steps, windows, ledges."
   -> Just where each column's strip starts/stops and which textures show. Upper
      and lower textures are extra sprites in the upper/lower screen bands, clipped
      by Doom's existing clip arrays. Core competency, not weakness.

"CPU can't read C-ROM / can't sample textures."
   -> True and never needed. The CPU does BSP/projection/clip/game logic on
      geometry, never pixels. The pixel-sampling inner loops are exactly what we
      delete and hand to the LSPC. C-ROM = texture memory; LSPC = texture unit.

"Lighting varies per pixel / can't remap per pixel."
   -> Doom lighting is a per-column colormap = a palette remap. Neo Geo selects one
      of 256 palettes per sprite. Pre-bake 8-16 brightness palettes per material;
      pick by light level. ~1:1 mapping. Global tints = one palette write. (13 sec 3)

"No floating point."
   -> Doom is 16.16 fixed point with lookup tables, built for portability; fits the
      68000's 32-bit regs + 16x16->32 multiply. The per-column divide is the cost
      center, but at ~40 columns not 320, and replaceable with ROM scale tables.

"Sound."
   -> A strength. YM2610 = FM + ADPCM. SFX -> ADPCM samples; music -> FM arrangement.
```

## Factual slips in the transcript (correct them in our own heads)

```text
"84 KiB VRAM"        -> 68 KiB (64 lower + 4 upper).            (VRAM)
"340 onscreen colors"-> 3840 (256 palettes x 15).               (Palettes)
"16x6 pixel tiles"   -> 16x16 tiles, 4bpp, 128 bytes.           (Sprite_graphics_format)
```

The architecture claims in the video are right; these three are transcription
noise. We do not repeat them.

## The honest casualty list (this is still a port, not a tribute)

Given up (hard physics or accepted precedent):

```text
textured floors/ceilings (flat color + horizon split; also deletes visplanes, our
  hungriest RAM structure -- the biggest cut funds the tightest constraint);
~20-40 column horizontal resolution; single-digit-to-mid-teens fps; capped
monster counts; affine "warpy" walls; 16px-granular sprite occlusion (pop at
corners); little/no translucency; 15-color re-encoded art; no exact demo sync;
no runtime WAD loading.
```

NOT on the casualty list:

```text
full 360 movement + rotation; real sectors/heights; stairs, lifts, doors,
switches; real monster AI + physics; real weapons; the real levels.
```

## The two genuinely hard ceilings (respected, not waved away)

```text
1. 96 sprites/scanline. The horizon line is crossed by every wall chunk; coarse
   columns + deterministic degrade keep it under 96. Doom's height complexity
   actually HELPS -- ledge/pit walls sit off the horizon and spread the load.
2. VRAM upload bandwidth + 12 MHz CPU. ~1,664 practical SCB words/vblank; survived
   by tilemap caching + temporal coherence. This, not 96/line, likely sets the fps.
```

## The gauntlet

MVG: *"I don't want to say it's impossible because as soon as you say something is
impossible, the gauntlet has been thrown down."* It is physically possible on a
stock Neo Geo, with a large cartridge and no extra chip. The hardware doesn't say
no — it says give up the floor textures and most of your frame rate, and respect
the scanline. The proof obligation is [05_milestones.md](05_milestones.md) M1:
walk one real Doom room as scaled sprites, holding 12 fps under 84 sprites/line.
If that holds, the rest is grind.
