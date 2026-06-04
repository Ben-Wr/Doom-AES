# Load-Bearing Hardware Truths

These are the facts most likely to quietly kill the project if they are not treated as design law. Every number here is cross-checked against the mirrored NeoGeoDev pages in `references/neogeodev/md/`. The source page is named in parentheses. If you change a number, re-derive it from the reference, not from memory.

## 0. Verified Base Numbers

```text
CPU:                 68HC000 @ 12 MHz, Z80A @ 4 MHz        (General_specifications)
Work RAM:            64 KiB                                 (General_specifications)
VRAM:                64 KiB lower + 4 KiB upper = 68 KiB    (VRAM)
                     VRAM holds NO graphics: only sprite
                     attributes, fix map, sprite lists.
Active display:      320 x 224, NTSC ~59.18 Hz             (Display_timing)
Colors on screen:    3840 max (256 palettes x 15)          (Palettes)
Palette store:       2 banks of 256 x 16 entries,
                     1 bank active at a time.               (Palettes)
P-ROM (code):        2 MiB without bankswitching            (General_specifications)
Sprite C-ROM:        128 MiB addressable (2^20 tiles)       (Sprites)
Sprite tile:         16x16, 4bpp, 128 bytes                 (Sprite_graphics_format)
Sprite:              1 tile wide (16px), up to 32 tiles
                     (512px) tall.                          (Sprites)
Sprites per line:    96 hard max                            (Sprites)
Sprites per frame:   381 displayable (448 VRAM slots)       (Sprites)
Sound:               YM2610: 4 FM + 7 ADPCM + 3 PSG         (General_specifications)
```

The MVG video's stray numbers are wrong and worth correcting in our own heads: VRAM is 68 KiB not "84 KiB"; on-screen colors are 3840 not "340"; tiles are 16x16 not "16x6". The architecture facts in the video are right; those three figures are transcription noise. See [12_answering_the_video.md](12_answering_the_video.md).

## 1. Shrink Only — And At Known Granularity

Neo Geo scaling only reduces. It never enlarges. *"Contrary to common belief sprites can't be zoomed, they can only be shrunk. Graphics for sprites have to be stored at the biggest size needed."* (Sprites)

Granularity is not infinite, and the two axes differ (Sprite_shrinking):

```text
Vertical shrink:   8-bit, $00..$FF ($FF = full).  256 steps.
                   Uses a lookup table in L0 ROM. Subsampling, no smoothing.
                   Propagates to chained (sticky) sprites.
Horizontal shrink: 4-bit, $0..$F ($F = full, $0 = 1px wide).  Only 16 widths.
                   Fixed decimation pattern (documented per value).
                   Does NOT propagate to chained sprites.
```

Implications, all mandatory:

```text
walls:    author cards at max visible height (512px / 32 tiles), shrink down.
monsters: pre-upscale offline to closest looming size, then shrink down.
weapons:  author at final largest foreground size.
runtime:  assert no requested size exceeds source size (shrink-only guard).
chunks:   on-screen chunk width is one of 16 discrete pixel widths, not arbitrary.
```

The horizontal-shrink subtlety the early design glossed: X-shrink does **not** map an arbitrary texture-U range across a chunk. It subsamples one 16px-wide card down to 1..16 px using a fixed skip pattern. Different U coverage = a different precomputed card. X-shrink only sets the on-screen *width* of the card you already chose.

## 2. The SCB Is The Real Output Format

Everything the renderer "draws" is four Sprite Control Blocks in VRAM (Sprites, VRAM). VRAM addresses are **word** addresses, not bytes.

```text
SCB1  $0000-$6FFF  tilemap + attributes. 64 words/sprite (32 tiles x 2 words).
                   word[even]: tile number LSBs
                   word[odd] : palette(8) | tile MSBs(4) | auto-anim(2) | Vflip | Hflip
(fix) $7000-$7FFF  fix layer map (not a sprite SCB)
SCB2  $8000-$81FF  shrink: low byte = Vshrink($FF full), hi nibble = Hshrink($F full)
SCB3  $8200-$83FF  Y position(9b) | sticky bit | size in tiles(6b). Screen top = 496 - Yfield.
SCB4  $8400-$85FF  X position(9b), from left border.
      $8600-$86FF  per-line sprite lists (even/odd), GPU-managed
```

Writing Y must preserve the low 7 bits (sticky + size) of the SCB3 word — read-modify-write (Moving_sprites). Sprites wrap on a 512px X/Y boundary.

## 3. VRAM Upload Is Its Own Clock — And The Tightest One

VRAM is not in the 68k address space. It is reached only through three registers (VRAM):

```text
REG_VRAMADDR  $3C0000  set target word address
REG_VRAMRW    $3C0002  read/write data word
REG_VRAMMOD   $3C0004  signed value auto-added to address after each write
```

REG_VRAMMOD is the lever: set the address once, then **stream** a sprite's contiguous SCB table without re-addressing per word. SNK's minimum spacings (VRAM):

```text
after writing data, next write:        >= 12 CPU cycles  (streamed case)
after writing address, next read:      >= 16 CPU cycles
after writing data, set new address:   >= 16 CPU cycles
cannot auto-increment across the $7FFF/$8000 zone boundary; re-address instead.
```

Derived budget (Display_timing): NTSC vblank ~= 40 scanlines x 1536 mclk = ~61,440 mclk = ~2.56 ms = **~30,720 CPU cycles** at 12 MHz. At ~12 cycles/word that is **~2,560 word-writes/vblank theoretical, ~1,664 practical** (loop overhead, address sets, zone crossings).

Now the killer arithmetic:

```text
A full 512px wall sprite tilemap (SCB1) = 64 words.
40 wall chunks x 64 = 2,560 words = the ENTIRE vblank, walls alone, things excluded.
```

So you **cannot** rewrite every wall tilemap every frame. The renderer survives only by:

```text
1. Caching SCB1 tilemaps. Rewrite a sprite's tilemap ONLY when its card id changes.
2. Exploiting temporal coherence: a small view change keeps most columns on the same card.
3. Updating SCB2/3/4 (3 words/sprite) every frame; those are cheap.
4. If still over: spread non-critical writes across active display, or drop a frame's worth
   of card changes (accept brief texture lag on fast spins) rather than overrun vblank.
```

`scripts/vram_upload_budget.py --wall-card-change-frac F` models exactly this. Milestone 0B must replace the estimate with measured writes. This clock, not the 96/line limit, is the most likely thing to set your real frame rate.

## 4. Coarse Columns Are Required — And It Is Per-Seg, Not Per-Screen-Width

Do not inherit the Wolfenstein 80-column model. The binding count is **visible wall chunks**, and the center scanline is crossed by *every* wall sprite, near and far (a distant wall is a short strip that still straddles the horizon). Chunk count scales with **visible seg count**, not with screen width — a techbase room with 60 short segs is 60+ center-line sprites before a single monster.

```text
center-line sprites  ~=  visible wall chunks + thing strips + reserve
budget               =   96 hard, target <= 84
default chunk width  =   16 px; spend 8 px only where the scene has headroom
degrade              =   merge far/narrow segs into wider chunks first
```

Per-screen-column, a Doom view also stacks: upper texture, lower texture, the wall through a two-sided gap, plus thing strips. Coarse chunks are what make that vertical stacking expressible under 96/line — they are correct, not lazy.

## 5. The Fixed Horizon Is A Gift — But Not Via The Fix Layer

No pitch means the horizon sits permanently at screen center. That makes floor/ceiling a background fill, not a per-pixel renderer. **But the fix layer cannot be that fill: the fix layer always draws on top of sprites** (Fix_layer), so it would cover the walls.

Correct background strategies, behind the walls:

```text
v1   single backdrop color  -> free. Backdrop = last color of palette bank (Palettes).
                               One color for the whole back layer.
v1.5 two-band split         -> timer interrupt at the horizon scanline rewrites the
                               backdrop color (or a shared palette entry) during hblank:
                               ceiling color above, floor color below. ~1 IRQ, 0 sprites.
                               Palette writes during active display cause "snow"; do the
                               swap in hblank (Palettes).
later per-sector floor color -> hard. Needs region fills / many raster splits. Stretch goal.
```

Do **not** spend full-height sprite columns on a floor/ceiling backplane unless a later feature truly earns it (20 full-width sprites = 20/line on every floor line). The fix layer's real jobs are the status bar, HUD numbers, the face, and debug text — and it only reaches the first 16 palettes (Fix_layer, Palettes).

## 6. Depth Is List Order, Not A Priority Field

There is no per-sprite Z or priority value. Draw/overlap order is the sprite's **index in the SCB** (Sprites notes "priority: 1 is in the back"). Consequences:

```text
emit sprites back-to-front by SCB index: far walls / far things at low indices,
near things and the weapon at high indices.
when >96 cross a line, the hardware drops by this priority -- so the surviving
sprites must be the ones you care about (walls, threats). Verify the exact eviction
order empirically in Milestone 0B's scanline_limit bench before trusting it.
```

## 7. Free Hardware You Should Exploit

```text
Auto-animation (Sprites): a 2-bit/4-frame and 3-bit/8-frame field in the SCB1
  attribute word cycles a sprite's tiles with zero CPU. Use for animated wall
  textures (FIREBLU, computer screens, lava) and idle monster anim for free.
Sticky bit / sprite chaining (Moving_sprites): chained sprites move as one block
  from the driver's position; Vshrink propagates down the chain (Hshrink does not).
  Useful for multi-column monster billboards -- fewer position writes.
Two palette banks (Palettes): build next frame's light palettes in the inactive
  bank, flip with one register write. Avoids mid-frame "snow".
Backdrop color (Palettes): a free, full-screen back color with no sprite cost.
```

## 8. Vertical Mapping Caveats That Cause Texture Garbage

Two SCB facts bite wall cards directly (Sprite_shrinking):

```text
Window vs shrink: the sprite "size" (height in tiles) is a fixed window. Vshrink
  shrinks the graphics INSIDE that window; it does not change the window. If the
  window is taller than the shrunk graphics, you see garbage from stale tiles.
Last-line repeat: when the window exceeds the shrunk graphics height, the leftover
  lines repeat the bottom line of tile 15. SNK's fix: keep that line transparent.
```

For walls: either size the window in whole tiles to match the projected height and Vshrink to fine-tune, or set the window to max and keep a transparent guard line. Vertical texture pegging/phase is quantized to a few precomputed card variants; expect minor swimming on moving doors/lifts. Document the chosen convention before writing the emitter.

## 9. The Baseline Atlas Is Smaller Than The Fancy Atlas

```text
v1 per material: texture tiled vertically to 512px, sliced to 16px U cards,
                 a few vertical phases, palette light bands. Lean on hardware
                 X/Y shrink for distance.
later:           precomputed mip/coverage cards, added ONLY where decimation
                 shimmers. Not a v1 requirement.
```

`scripts/card_atlas_budget.py` with a realistic v1 set (48 materials, 8 cards, 4 phases) is ~6.6 MiB, not tens of MiB. Confirm it against your real target board, not the 128 MiB theoretical ceiling.

## 10. The Pseudo-Framebuffer Is Mostly A Trap

Static images do not need a runtime arbitrary-bitmap path.

```text
title/menu/intermission:  static sprite/fix compositions
screen wipe:              vertical sprite-column slide (it already is one)
automap:                  fix/sprite line drawing first
```

Keep the 4x4 mask-dictionary idea in reserve as proof the "no framebuffer" objection has escape hatches. Do not let it consume early energy or become Milestone 1.

## 11. Occlusion Is Strip Dropping

No Z-buffer, no stencil. Monster/object occlusion = split the billboard into its 16px strips, compare each strip's screen-x bucket against the nearest blocking wall depth, drop occluded strips. Accept 16px popping at corners. That is the honest Neo Geo form of Doom's masked-column clipping. Build thing rendering strip-wise from day one.

## 12. ROM Is Banked, Not Infinite

```text
P-ROM > 2 MiB: bankswitch via a byte write in $200000-$2FFFFF (Bankswitching).
  $000000-$1FFFFF is the fixed region (vectors + hot code live here).
  Page per-map geometry/metadata banks through the $200000 window.
C-ROM (sprite art): 128 MiB addressable before graphics bankswitch -- ample, but
  real flashcarts (NeoSD, Darksoft) and board layouts cap below the theoretical max.
Before committing an atlas: identify the target cart, list C/P/V/M/S limits,
reserve tool/metadata/alignment space, and prove packing fits.
```
