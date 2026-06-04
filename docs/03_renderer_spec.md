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
8. Emit upper/middle/lower wall sprite commands.
9. Project visible things.
10. Sort or bucket things by depth.
11. Emit thing billboard strips with distance LOD.
12. Emit weapon/HUD/fix updates.
13. Validate scanline, frame, shrink-only, and upload budgets.
14. Write SCB/fix/palette updates.
```

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

Version 1 floor/ceiling is a fixed horizon split:

```text
top half:    solid ceiling color or static sky color
bottom half: solid floor color
```

No pitch means this can be stable and effectively free. Scrolling sky and per-sector floor color are later experiments.

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
