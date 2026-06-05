# Renderer Diagnosis And Optimal Path (M2 post-mortem)

Date: 2026-06-04. Author: analysis pass over the M2 E1M1 wall renderer, cross-checked
against the local `references/neogeodev/md/` mirror and the audited docs. This is a
**findings + strategy** doc. It does not change code; it records what is wrong and the
optimal path so the next implementation pass is aimed correctly.

The short version: there are **two different visual problems wearing one costume**, and a
**third, more expensive mistake** underneath both of them.

```text
1. "Green/white vertical garbage" in steep/far poses   -> a real, fixable bug (window size).
2. "Chunky barcode" look even when correct             -> hardware physics. Stop fighting it; style it.
3. fps was chased by DELETING walls                    -> wrong lever. The walls were never the limit.
```

---

## 1. The two visual problems, separated

The host (non-Neo-Geo) reference renderer looks like Doom: correct perspective,
recognizable wall masses, clean sky/floor split. So **geometry and projection are sound.**
Every remaining problem is in the Neo Geo mapping layer. Do not touch the BSP/projection.

The Neo Geo output is **bimodal**: face-on/simple poses render a readable room (sky band,
brick courses, brown floor); the `scan` sweep and steep angles collapse into green/white
vertical garbage. That bimodality is the tell that two independent things are happening.

---

## 2. Root cause A — the window-size bug (HIGH confidence, verified)

This is the green/white garbage, and it is the single most important finding.

**Verified hardware fact** (`references/neogeodev/md/Sprites.md`, `Sprite_shrinking.md`):

> The sprite's "size" field (height in tiles, in SCB3) is a fixed **display window**.
> Y-shrink (SCB2) shrinks the graphics *inside* that window. *"If the display window of a
> sprite is taller than the shrunk graphics, the remaining lines will be filled with
> repeats of the last line of the last tile (the bottom line of tile 15). SNK recommends
> leaving that line fully transparent if this causes problems."*

**What the M2 code does** ([main.c:633](../experiments/milestone2_e1m1_walls/main.c#L633),
[main.c:1029](../experiments/milestone2_e1m1_walls/main.c#L1029)):

```c
cmd.size_tiles = CARD_TILE_COUNT;          // ALWAYS 16 tiles = a 256px window, every wall
...
ctrl_scb3[i] = (scb3_yfield_from_top(cmd->y) << 7) | (cmd->size_tiles & 0x3f);
```

Distance is handled **only** by `y_shrink`. So a far wall that should be ~40px tall is a
**256px window** with the graphics shrunk into the top ~40px, leaving ~216px of window
that the hardware fills with the **last-line-repeat / stale-tile smear**. That smear is the
green/white vertical garbage. It gets worse exactly as walls get shorter (steeper/farther),
which is precisely the pose-dependence observed.

It is amplified because the texture cards do **not** carry a transparent guard line at the
bottom: [doom_texture.py](../tools/wad2ng/doom_texture.py) sets the bottom scanline
transparent only in `fallback_card()`, not in `texture_card()`. So the smear is opaque junk
instead of invisible.

**The decisive cross-check:** Milestone 1 does this *correctly* — it sizes the window to
`ceil(projected_height / 16)` and uses Y-shrink only to fine-tune. M2 regressed from M1's
working convention. `docs/03` §"Vertical: window vs shrink" already told us to *"pick one
convention and assert it."* M2 picked neither (fixed 16, no guard line). **The renderer
drifted from its own spec.**

Why the earlier 512px→256px card change "looked better but never fixed it": halving the
card height halved the leftover-window region (≤256 instead of ≤512), so there was simply
*less* garbage — but the mechanism was untouched. Every previous fix attempt (smaller cards,
brighter backdrop, row-major tiles, deleting walls) circled this bug without landing on it.

**The fix (one mechanism, two parts):**
1. Set `size_tiles = clamp(ceil(projected_height_px / 16), 1, CARD_TILE_COUNT)` per chunk
   (≈ what M1 does), so the window matches the graphics. Cost: one divide per chunk.
2. Belt-and-suspenders: bake a transparent bottom scanline into **every** wall card so any
   sub-tile rounding leftover is invisible. Cost: one scanline per card, negligible.

Secondary, lower-severity contributors to "missing/blank strips" (distinct from the green
smear): the `MAX_SCB1_REWRITES=40` deferral blanks late card changes
([main.c:1013-1025](../experiments/milestone2_e1m1_walls/main.c#L1013)), and
`bucket_occluded()` is a dead stub ([main.c:473](../experiments/milestone2_e1m1_walls/main.c#L473))
so nothing is culled. Both are addressed in §4.

---

## 3. Root cause B — coarse columns are physics, not a bug (embrace it)

A Neo Geo sprite is **16px wide**. 320 / 16 = **20 columns** across the screen; X-shrink can
push narrow columns to ~40 at 8px. Doom is **320 columns**. So the wall surface can never be
"smooth" the way the PC renderer is — diagonal wall edges *will* stair-step, and per-column
height steps *will* show. This is documented and accepted in `docs/08` §4 ("coarse columns
are required... they are correct, not lazy").

The mistake is treating this as a defect to optimize away. It cannot be. The correct response
is **stylization**: make the coarseness read as deliberate arcade raster art, not broken Doom
(see §6). Spend zero further effort trying to make walls high-resolution.

---

## 4. The expensive mistake — fps was chased by deleting walls

The wall budget was tuned 92 → 55 → 44 → 41 → 40 to clear the 6fps gate. But the gate's own
recorded evidence ([RESULT.md](../experiments/milestone2_e1m1_walls/RESULT.md)) shows:

```text
max sprites:        75   (limit 96, target 84)   -> NO sprite-count pressure
max SCB words:    1445   (budget 1664)           -> NO upload-bandwidth pressure
```

So neither hard limit was being hit. **Deleting walls did not relieve any measured
constraint** — it just removed the content that makes it read as Doom. The real per-frame
cost is **CPU**: a full BSP walk every frame + per-seg perspective divides + per-chunk
division on a 12 MHz 68000. And the harness **does not measure CPU cycles at all**
([mame_capture.lua](../experiments/milestone2_e1m1_walls/tools/mame_capture.lua) only counts
sprites/scanlines/SCB-words/RAM). The optimization was aimed at a variable that was never the
bottleneck, guided by a gate that can't see the real one.

**What actually reduces frame cost (cut CPU, not walls):**

| Lever | Effect | Effort |
|---|---|---|
| Implement `bucket_occluded()` (it's a stub returning 0) | far walls behind near walls stop being projected/emitted — fewer divides *and* fewer sprites in dense sightlines | low |
| Precompute per-node visible-seg lists / use the REJECT lump in `wad2ng` | kill the full O(all-nodes) walk + per-seg math every frame | high |
| Reciprocal + projection lookup tables (precompute 1/depth) | replace per-chunk 68k division with a table read | high |
| Replace the 40-rewrite **count** cap with a **word** cap on SCB1 | spread upload honestly instead of silently blanking strips | medium |
| Measure CPU per phase (BSP / project / interpolate / upload) | aim every future optimization at the proven bottleneck | high |

Once CPU is cut, the wall budget can go **back up** toward the documented ~40-48 chunk target
instead of the panic-driven 40.

---

## 5. The reframe: what "Doom on Neo Geo" should actually be

Stop trying to make the Neo Geo draw PC-Doom's walls. It physically can't, and that was never
where the "Doom feeling" lived. The Neo Geo is the best 2D sprite machine of its era. The win
is: **a clean, stylized, well-lit stage, with the budget poured into the actors and the audio.**

> Keep Doom's brain (BSP, sectors, movement, combat). Make the walls a tasteful backdrop.
> Make the *enemies, weapon, gore, lighting, and soundtrack* the show.

---

## 6. Optimal architecture

### Per-frame sprite budget (worst scanline ≤ 84, hard ≤ 96)

```text
walls (chunks)        <= 48   coarse 16px columns, 8px only near/important
thing strips          <= 24   monsters/projectiles/pickups, 16px strips, depth LOD
weapon                <=  8   dedicated foreground reserve, NEVER dropped by LOD
reserve               ~   4
HUD/status bar           0    fix layer (8x8), + 1-2 sprites for the face
floor/ceiling            0    backdrop color / timer-IRQ split, NOT sprites
```

### Walls
- **Stylize, don't reproduce.** Per material, bake a small set of flat/low-detail "material
  band" cards (base color + a couple of value bands), authored so 16px columns look
  intentional. Real Doom texture identity (STARTAN brown, tech panels, BROWN) survives at the
  *palette + silhouette* level, not the pixel level.
- **Window = projected height** (root cause A fix) + transparent guard line. Non-negotiable.
- **Free light diminishing:** split the 256 palettes into depth/sector-light bands and select
  the palette per sprite by `(base_palette + depth_band)`. This is Doom's signature falloff
  for ~2 instructions per chunk, and the sector-light values are *already compiled and
  currently unused* ([doom_map.py](../tools/wad2ng/doom_map.py) emits them;
  `select_wall_card` ignores them). This single change buys the most "Doom atmosphere" per
  unit effort of anything in the project.
- **Free animation:** author FIREBLU/computer/SLIME/light textures as auto-anim sequences and
  set the SCB1 auto-anim bits — the LSPC cycles them at zero CPU cost.

### Floors / ceilings
- No affine/mode-7, no framebuffer — **textured floors are not worth it.** (Verified: VRAM
  holds no graphics; the fix layer draws on top of sprites.)
- v1: single backdrop color. v1.5: **timer-IRQ two-band split** at the horizon (ceiling color
  above, floor color below) — ~1 IRQ/frame, 0 sprites (`docs/08` §5). Add per-sector floor
  color and a scrolling/parallax sky only as polish. A flat, distance-shaded floor reads as a
  floor; players do not miss the flat texture.

### Things, weapon, HUD, sound — where the "wow" lives (§7)

---

## 7. Where to CUT and where to DELIVER

### CUT (ruthlessly — these cost budget and buy little)
- **Wall texture fidelity at distance.** Flat material bands beat shredded detail.
- **Floor/ceiling texturing.** Flat shaded + light falloff only.
- **Horizontal wall resolution.** Accept ~20-40 columns; do not spend CPU chasing more.
- **Environmental geometry detail.** The instinct to "nuke detail except switches/doors" is
  *correct*: simplify/merge cosmetic micro-geometry offline in `wad2ng`, but preserve and
  even *highlight* the high-signal gameplay cues — **doors, switches, lifts, exits, keycards,
  teleporters** (give those dedicated high-contrast/animated cards).
- **Simultaneous enemy count.** Cap actives per map; the Neo Geo wows with a few *gorgeous*
  enemies, not a swarm of tiny ones.

### DELIVER (this is the show — ranked by wow-per-effort)

| What | Why it sells "Doom" | Effort |
|---|---|---|
| **Palette depth/sector lighting** | Doom's signature darkness/atmosphere, nearly free, data already exists | low |
| **Always-on weapon sprite** (big, foreground, dedicated reserve) | the single strongest Doom identity signal; on screen every frame | medium |
| **Fix-layer status bar + face** | instant Doom HUD identity, 0 sprite cost | low |
| **Auto-animated wall textures** (FIREBLU/computers/lights) | free motion and life on the stage | medium |
| **Big multi-angle animated enemies** (pre-upscaled, strip-built, depth LOD) | what the Neo Geo does better than any console of its era | high |
| **Projectiles / muzzle flash / gibs / blood** | the visceral feedback that *is* Doom | medium |
| **YM2610 soundtrack + ADPCM SFX** | E1M1 music + shotgun/imp/door SFX deliver enormous "feel" for the player's ears while the eyes forgive the walls | high |
| **Parallax / scrolling sky** | depth and place for the upper band | medium |

The strategic bet: a player will forgive blocky walls instantly if a detailed imp is lobbing
fireballs at them, the shotgun fills the lower screen, the room is lit like Doom, and E1M1's
music is playing. They will *not* forgive blocky walls in a silent, empty, flat-lit room —
which is exactly the current state.

---

## 8. What to do differently (ordered)

1. **Fix the window bug, not the symptoms.** Dynamic `size_tiles` + transparent guard line on
   all cards. This kills the green/white garbage at the source. (Root cause A.)
2. **Stop deleting walls to pass fps.** Restore the wall budget toward 40-48 and instead cut
   **CPU**: implement the `bucket_occluded` stub, then precompute visibility/reciprocals in
   `wad2ng`. (Root cause / §4.)
3. **Make the harness see the real bottleneck.** Add a CPU-cycle (or scanline-time) measure
   to the profile overlay and gate, and add a **visual recognizability gate** (e.g. SSIM of
   MAME capture vs host reference ≥ threshold) using the existing `visual_compare.py`. A green
   gate must mean "looks like E1M1 *and* fits budget," not just "fits budget." (§4, `docs/05`.)
4. **Turn on free atmosphere.** Wire sector-light + depth into `select_wall_card`'s palette
   choice. Biggest visual ROI in the project.
5. **Re-aim the milestones at the actors.** Bring weapon + one enemy + HUD + E1M1 music
   forward as the thing that proves "Doom feel," rather than continuing to polish walls.
6. **Adopt the style explicitly.** Flat material-band wall cards + animated special cards for
   doors/switches/exits. Document coarse columns as an intended aesthetic, not a failure.

---

## 9. Confidence and what was ruled out

- **High confidence:** the window-size bug (verified vs `Sprite_shrinking.md` + cross-checked
  against M1's correct code); coarse columns are fundamental; the fps-by-wall-deletion was
  misaimed (proven by RESULT.md showing 75/96 sprites and 1445/1664 words — no pressure).
- **Ruled out:** geometry/projection bug (host render is correct); wrong palette (colors are
  recognizable in good poses); X-shrink/width (only affects width, not vertical garbage);
  depth/index-order (would swap layers, not smear one sprite); atlas stride desync (current
  counts match; low risk, worth a build-time assert anyway).
```
