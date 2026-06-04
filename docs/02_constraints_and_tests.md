# Constraints And Tests

These are the numbers and gates to keep in mind on every design decision. Re-check the mirrored NeoGeoDev docs in `references/neogeodev/md/` after running `scripts/fetch_references.sh`.

## Hard Hardware Constraints

```text
CPU:                    Motorola 68000 around 12 MHz
Work RAM:               64 KiB
Display:                320x224 visible target
Sprite tile:            16x16 px, 4 bpp, 128 bytes
Sprite strip:           16 px wide, up to 32 tiles / 512 px tall
Sprite shrink:          shrink only, no enlargement, ever
Horizontal shrink:      still consumes one 16 px sprite entry
Sprite scanline limit:  96 sprites
Visible sprite limit:   about 381 sprites per frame
Sprite address space:   20-bit tile id, about 128 MiB C-ROM graphics before graphics bank tricks
Palettes:               256 sprite palettes, 16 entries each, color 0 transparent
Fix layer:              suitable for text/HUD/status support
VRAM access:            CPU-pushed through LSPC ports, timing-sensitive
Occlusion:              sprite priority only, no Z-buffer or stencil
Alpha:                  color 0 transparency only, no blending
Pitch:                  none in the design, fixed horizon
```

## Working Budgets

These are not hardware laws. They are project safety rails.

```text
Viewport:                   304x160 or 320x160 first
Wall chunk width:            16 px default, 8 px only where budget allows
Centerline wall chunks:      target around 20-40 before stacking
Thing strips on centerline:  reserve 16-24
Safety reserve:              8-12
Visible sprite commands:     target <= 340, hard stop before 381
RAM runtime target:          <= 56 KiB allocated, leave stack/scratch reserve
Frame target:                10-15 fps ordinary rooms, lower in heavy scenes
```

## Always-Run Tests

### 1. Scanline Sprite Pressure

For every emitted scene:

```text
for y in viewport:
    count sprites crossing y
    assert count < 96
    warn if count > 84
```

Use:

```sh
scripts/sprite_scanline_budget.py path/to/scene.json
```

### 2. Visible Sprite Count

Track:

```text
wall chunks
upper wall chunks
lower wall chunks
thing strips
weapon strips
effects
optional scrolling sky/backdrop sprites
```

Warn above 340. Fail before 381.

### 3. RAM Budget

Every new runtime structure must be added to the RAM ledger.

Use:

```sh
scripts/ram_budget.py
```

The initial target ledger:

```text
player/game globals:          4 KiB
active mobj pool:            10 KiB
thinker/event state:          4 KiB
dynamic sector/line state:    4 KiB
collision/block scratch:      4 KiB
renderer clip arrays:         4 KiB
visible command lists:        8 KiB
sprite-control shadow:        6 KiB
stack/audio/scratch:          6 KiB
reserve:                      4 KiB
```

That target leaves margin under 64 KiB. Any real structure expansion has to pay for itself.

### 4. ROM Budget

Wall card budgets get scary quickly. Estimate before generating.

Use:

```sh
scripts/card_atlas_budget.py --materials 48 --cards-per-material 8 --phases 4
scripts/pseudo_framebuffer_budget.py
```

Remember: baseline wall cards should lean on hardware X/Y shrink first. Precomputed mip/coverage cards are a shimmer-reduction quality pass, not an initial requirement.

### 5. VRAM Upload Budget

Benchmark raw SCB writes before Doom code exists.

Track at least:

```text
SCB1 tilemap words
SCB2 shrink words
SCB3 height/control words
SCB4 position/link words
palette writes
fix-layer writes
```

A 512 px wall-card sprite can imply up to 64 SCB1 tilemap/attribute words before SCB2/3/4 control words. That cost can dominate if every visible wall chunk changes tile assignment every frame.

Use:

```sh
scripts/vram_upload_budget.py --wall-sprites 20 --thing-sprites 24
```

The script is an estimator. Milestone 0B must replace estimates with measured writes in emulator/hardware.

### 6. CPU/Frame Budget

Instrumentation should count:

```text
BSP nodes visited
segs projected
divides/multiplies
chunks emitted
things projected
sort/bucket cost
SCB1 tilemap words written
SCB2/3/4 control words written
```

Prototype code should expose these counters even before graphics look good.

### 7. Shrink-Only Guard

Every sprite/card request must assert:

```text
requested_screen_width  <= source_width
requested_screen_height <= source_height
```

For monsters and weapons, this requires pre-upscaled source art in the asset compiler.

### 8. Visual Readability

The gate is not "does it look like PC Doom?"

The gate is:

```text
Can a player recognize the room?
Can a player read doors, stairs, windows, monsters, and projectiles?
Can a player make combat decisions?
Can E1M1 be recognized walls-only?
```

### 9. Legal Hygiene

Fail the build if commercial IWADs, BIOS files, or ROM sets are staged for commit.

The repo may contain:

```text
source code
tool code
compiled formats
metadata schemas
free placeholder art
docs
```

The repo must not contain:

```text
commercial IWADs
Neo Geo BIOS files
commercial ROMs
generated assets derived from commercial IWADs unless the distribution story is solved
```

## Prototype Acceptance Gates

### Milestone 0A Gate

```text
Can place one or more maximum-size wall cards.
Can update X/Y/shrink/palette.
Can prove shrink-down-only display path.
No scanline overflow.
Frame/update counter visible.
```

### Milestone 0B Gate

```text
Can rewrite representative SCB1/2/3/4 data inside the chosen update window.
Can measure words/frame.
Can detect visible tearing/glitching.
Can report max safe command mix.
```

### Milestone 1 Gate

```text
One Doom-like room.
Free movement and rotation.
At least one step or door-height change.
Fixed horizon split floor/ceiling.
Wall chunks under budget.
Around 12 fps target in the simple room.
```

### Milestone 2 Gate

```text
E1M1 walls-only is recognizable.
No monsters required.
Budget manager can merge chunks under pressure.
Worst-case-scene suite begins here.
```

### Milestone 3 Gate

```text
Weapon foreground sprites.
At least zombieman, imp, barrel, pickup, projectile.
Per-strip occlusion good enough for gameplay.
```
