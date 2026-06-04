# Constraints And Tests

These are the numbers and gates to keep in mind on every design decision. Re-check the mirrored NeoGeoDev docs in `references/neogeodev/md/` after running `scripts/fetch_references.sh`.

## Hard Hardware Constraints

All cross-checked against `references/neogeodev/md/`. Full derivations and the SCB/VRAM detail live in [08_load_bearing_hardware_truths.md](08_load_bearing_hardware_truths.md).

```text
CPU:                    68HC000 @ 12 MHz (+ Z80A @ 4 MHz for sound)
Work RAM:               64 KiB
VRAM:                   68 KiB (64 lower + 4 upper); holds attributes/maps, NOT graphics
Display:                320x224 visible, NTSC ~59.18 Hz
Sprite tile:            16x16 px, 4 bpp, 128 bytes
Sprite strip:           16 px wide, up to 32 tiles / 512 px tall
Sprite shrink:          shrink only, never enlarge
  vertical shrink:      8-bit (256 steps), $FF full
  horizontal shrink:    4-bit (16 widths only), $F full, fixed decimation pattern
Horizontal shrink note: still consumes one 16 px sprite entry (1..16px on-screen width)
Sprite scanline limit:  96 sprites (hard); >96 dropped by SCB-index priority
Visible sprite limit:   381 displayable per frame (448 VRAM slots)
Sprite address space:   20-bit tile id, ~128 MiB C-ROM before graphics bank tricks
Palettes:               2 banks of 256 x 16 (1 active); color 0 transparent; 3840 colors max
Fix-layer palettes:     first 16 palettes only; fix ALWAYS draws on top of sprites
Depth order:            SCB index order only (no Z, no priority field). Emit back-to-front.
VRAM access:            via REG_VRAMADDR/RW/MOD ($3C0000-4); >=12 cycles/streamed word
VBlank budget:          ~40 scanlines ~= 2.56 ms ~= 30,720 cycles ~= ~1,664 practical words
Occlusion:              sprite priority only, no Z-buffer or stencil (strip-drop monsters)
Alpha:                  color 0 transparency only, no blending
Pitch:                  none in the design, fixed horizon at screen center
```

## Working Budgets

These are not hardware laws. They are project safety rails.

```text
Viewport:                   304x160 or 320x160 first
Wall chunk width:            16 px default, 8 px only where budget allows
Centerline wall chunks:      target <= 40 (count scales with VISIBLE SEGS, not screen width;
                             every wall, near or far, crosses the center line)
Thing strips on centerline:  reserve 16-24
Safety reserve:              8-12 (keep peak <= 84 of the 96 hard limit)
Visible sprite commands:     target <= 340, hard stop before 381
SCB words / vblank:          <= ~1,664 practical (see vram_upload_budget.py); cache tilemaps
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

A 512 px wall-card sprite implies up to 64 SCB1 tilemap/attribute words before SCB2/3/4 control words. Rewriting every visible wall tilemap every frame overruns vblank by ~2x. The renderer must cache SCB1 tilemaps and rewrite them only when a sprite's card id changes; SCB2/3/4 (3 words/sprite) are rewritten every frame.

Use (the `--wall-card-change-frac` knob models the caching that makes this fit):

```sh
scripts/vram_upload_budget.py --wall-sprites 40 --thing-sprites 24 --wall-card-change-frac 0.25
scripts/vram_upload_budget.py --wall-card-change-frac 1.0   # worst case: fast spin, every card changes
```

The script is an estimator. Milestone 0B must replace estimates with measured writes in emulator/hardware. The upload clock, not the 96/line limit, most likely sets the real frame rate.

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

The hardcoded, numeric pass/fail gate for each milestone (and its kill criteria) lives in [05_milestones.md](05_milestones.md). That file is the authority; do not duplicate thresholds here. The one rule that outranks all gates:

```text
A milestone is NOT passed until its gate is met IN A CYCLE-ACCURATE EMULATOR
(MAME neogeo) with the per-frame profile overlay visible. Screenshots and
host-side estimates are necessary but never sufficient.
```
