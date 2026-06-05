# Renderer Spec

## Primary Renderer

The primary renderer is a sprite-list compiler.

```text
Input:
    compact Doom map state
    player position/angle
    active sectors/lines/things
    material metadata

Output:
    Neo Geo sprite commands
```

## Frame Flow

```text
1. Read controls.
2. Run game tick or partial visual tick.
3. Traverse BSP front-to-back.
4. Project visible segs.
5. Clip segs against already-filled screen buckets.
6. Split wall ranges into budgeted chunks, defaulting coarse.
7. Select C-ROM wall cards and palettes.
8. Emit upper/middle/lower wall sprite commands into the command list.
9. Project visible things.
10. Sort or bucket things by depth.
11. Emit thing billboard strips with distance LOD.
12. Emit weapon/HUD/fix updates.
13. Assign SCB indices back-to-front (depth order IS index order).
14. Validate scanline, frame, shrink-only, and upload budgets.
15. Diff against last frame's SCB shadow: rewrite SCB1 tilemaps ONLY for slots
    whose card id changed; always stream SCB2/3/4 control words.
16. Push the diffed SCB/fix/palette writes during vblank (REG_VRAMMOD streaming).
```

Steps 13, 15, 16 are not optional bookkeeping. Index order is the only depth mechanism the hardware has, and the SCB1 diff is what keeps the per-frame upload under the ~1,664-word vblank budget (see [08](08_load_bearing_hardware_truths.md) section 3).

## Wall Chunk Command

Conceptual host-side command:

```c
typedef struct {
    uint32_t tile_base;
    int16_t  x;
    int16_t  y;
    uint8_t  source_w;
    uint16_t source_h;
    uint8_t  requested_w;
    uint16_t requested_h;
    uint8_t  x_shrink;
    uint8_t  y_shrink;
    uint8_t  height_tiles;
    uint8_t  palette;
    uint8_t  priority;
    uint8_t  role;       /* middle, upper, lower, sky, debug */
    uint8_t  budget_tag; /* wall, enemy, pickup, effect */
} ng_sprite_cmd_t;
```

The real hardware layout must follow Neo Geo SCB rules. This struct is a renderer-side shadow format. `requested_w/h` must never exceed `source_w/h`.

## Wall Card Selection

Runtime picks a card by:

```text
material id
16 px U slice
vertical phase
wall role
```

Runtime picks a palette by:

```text
sector light
distance band
special tint
```

Runtime does not sample C-ROM pixels.

### What X-shrink does and does not do

The horizontal texture *content* of a chunk comes entirely from the card you selected (its baked U slice). X-shrink is a 4-bit value that only sets the card's on-screen *width* (1..16 px) via a fixed decimation pattern — it cannot remap an arbitrary U range across the chunk. So:

```text
need a different U window  -> choose a different card (offline-baked U slice)
need a narrower on-screen chunk (edge of wall, 8px chunk) -> lower X-shrink
near wall, full 16px chunk  -> X-shrink = $F (full)
```

There are only 16 horizontal widths. Treat chunk width as quantized.

### Vertical: window vs shrink

A sprite has a tile-height "window" (size, 1..32) and a separate 8-bit Y-shrink that scales the graphics *inside* that window. Pick one convention and assert it:

```text
window (size in tiles) ~= ceil(projected_wall_px / 16)
y_shrink               = scales the 512px card down to projected_wall_px
guard                  = keep the card's bottom line transparent so the
                         hardware "last-line repeat" smear is invisible
```

**DECISION (was previously unpinned — pin it):** use the dynamic-window convention above
(`size_tiles = clamp(ceil(projected_wall_px / 16), 1, CARD_TILE_COUNT)`), **and** bake a
transparent guard line into every wall card as a belt-and-suspenders against sub-tile
rounding leftovers. Do both, not one. Milestone 1 already implements the dynamic window
correctly; the emitter for every later milestone must match it.

> **Known regression (M2, 2026-06-04):** `experiments/milestone2_e1m1_walls/main.c` sets
> `size_tiles = CARD_TILE_COUNT` (a fixed 256px window) for *every* wall and varies only
> `y_shrink`. Per the hardware (`references/.../Sprite_shrinking.md`: window taller than
> shrunk graphics → last-line-repeat smear), and because `texture_card()` does not emit a
> transparent guard line, this produces the "green/white vertical garbage" on short/far/steep
> walls. This is THE corruption bug, not a cosmetic LOD artifact. See
> [14_renderer_diagnosis_and_optimal_path.md](14_renderer_diagnosis_and_optimal_path.md) §2.

Vertical texture phase/pegging is quantized to the few precomputed phase variants. Expect minor swimming on moving doors/lifts; that is accepted.

## Chunk Width Rules

Start with:

```text
16 px chunks for normal walls
8 px chunks only for near/important walls with spare budget
24-32 px chunks for far/panic walls
```

Chunking can vary per seg. The goal is not uniform resolution. The goal is stable sprite pressure and readable rooms.

## Upper/Middle/Lower Walls

Doom sidedef output becomes:

```text
middle texture -> solid wall chunk
upper texture  -> ceiling/lintel wall chunk
lower texture  -> floor/step wall chunk
```

Doors, lifts, windows, and stairs all reduce to changing screen top/bottom plus which wall roles are emitted.

## Floor And Ceiling

No pitch means the horizon is fixed at screen center, so floor/ceiling is a background fill, not a renderer. It must sit *behind* the walls.

The fix layer cannot do this — it always draws on top of sprites and would cover the walls. The correct path:

```text
v1   single backdrop color (last color of palette bank) -> 0 sprites, 0 IRQ.
     Recognizable enough to ship Milestone 1 with.
v1.5 two-band split: a timer interrupt at the horizon scanline rewrites the
     backdrop / shared palette entry during hblank. Ceiling color above,
     floor color below. ~1 IRQ/frame, 0 sprites. Validate "snow"-free in M1.
later per-sector floor color and scrolling sky -> region fills / extra raster
     splits, or sprites in the top band only. Stretch goals, off in heavy scenes.
```

Do not build a full-width sprite backplane (20 sprites/line) for floor/ceiling. The timer-IRQ split is the intended technique.

## Thing Rendering

Things are billboards split into 16-pixel vertical strips.

All thing art must be pre-upscaled offline to the largest on-screen size it can reach, because hardware shrinking cannot enlarge a native Doom-sized sprite.

LOD table:

```text
near:    full strip count, best frames
medium:  half/detail-reduced strips
far:     1-2 strips or simplified card
panic:   omit decorations, simplify pickups, keep threats
```

Thing clipping should be strip-based from the beginning:

```text
screen x bucket
nearest blocking wall depth per bucket
drop 16 px strips behind blocker
```

Fine per-pixel occlusion is out of scope. Popping at 16 px granularity is expected.

## Weapon Rendering

Weapons are foreground sprites with strict priority.

They should not consume the same panic budget as world walls. If a weapon frame is too expensive, simplify weapon art offline. Author weapon art at the largest foreground size it will display.

## Fallback Pseudo-Framebuffer

Maybe use for:

```text
debug views
fallback far composite experiments
runtime-unknown bitmap experiments
```

Static menus, title screens, intermissions, and screen wipes should be sprite/fix compositions first. Do not use the pseudo-framebuffer as the main renderer until the sprite-BSP route has failed an actual Milestone 1 test.

## Budget Manager

Budget degradation order:

```text
1. Merge far wall chunks.
2. Remove optional scrolling sky or special backdrop.
3. Drop decorative things.
4. Reduce far thing strip counts.
5. Clamp distant upper/lower wall detail.
6. Flicker or simplify low-priority pickups/effects.
7. In panic, widen all non-critical distant wall chunks.
```

Never drop critical walls first. Never allow accidental scanline overflow.

## Sprite Slots, Depth, And SCB Caching

The 381 sprite slots are a pool. Draw order is the slot index — there is no Z value (see [08](08_load_bearing_hardware_truths.md) section 6). The renderer assigns indices back-to-front so nearer sprites overwrite farther ones, and so the hardware's >96/line eviction keeps the sprites that matter.

A workable allocation:

```text
slots 0..N-1    wall chunks, ordered far -> near
slots N..M-1    things, ordered far -> near, interleaved with walls by depth
slots M..top    weapon (frontmost), then HUD sprites
unused slots    parked off-screen / Y out of range, not deleted
```

SCB caching is the survival mechanism for the upload clock. Keep a host-side shadow of each slot's last-written `(card_id, palette, x, y, shrink)`:

```text
card_id unchanged  -> skip SCB1 entirely (64 words saved), write only SCB2/3/4 if moved
card_id changed    -> rewrite that slot's SCB1 tilemap (<=64 words) + control words
nothing changed    -> write nothing
```

Because the view changes little between frames, most wall slots keep their card; only edges and newly-revealed segs churn. That temporal coherence is what turns a 3,300-word worst case into a ~1,400-word typical frame.

## Upload Accounting

Renderer counters must distinguish:

```text
SCB1 tilemap/attribute words
SCB2 shrink words
SCB3 height words
SCB4 position/link words
fix-layer words
palette words
```

Changing a sprite position is cheap compared with changing a full-height card's tilemap. The upload benchmark decides how much dynamic tile assignment the renderer can afford.
