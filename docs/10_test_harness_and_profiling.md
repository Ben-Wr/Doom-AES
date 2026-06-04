# Test Harness And Profiling

ngdevkit gives us the base toolkit: C/ASM build support, Neo Geo headers, examples, and GDB/GnGeo debugging hooks. It does not give us a Doom-specific renderer profiler. We need to add that ourselves.

## Harness Layers

### 1. Host-Side Budget Tests

Already scaffolded:

```text
scripts/sprite_scanline_budget.py
scripts/vram_upload_budget.py
scripts/ram_budget.py
scripts/card_atlas_budget.py
```

These run without an emulator and should be used in CI/regression checks.

### 2. Asset Pipeline Reports

`tools/wad2ng` emits JSON manifests. These should become build inputs for:

```text
strip/tile counts
C-ROM estimates
shrink-only safety
palette pressure
per-map dependency lists
```

### 3. Neo Geo Microbench ROMs

Create one ROM per hardware question:

```text
sprite_shrink_card:    prove max-size card shrink and palette bands
vram_upload_scb:       measure SCB1/2/3/4 words per safe update window
scanline_limit:        deliberately approach 96 sprites/line and observe behavior
fixed_horizon:         prove free floor/ceiling split
strip_occlusion:       prove per-strip monster dropping
palette_bands:         prove light/tint palette swaps
memory_watermark:      prove RAM high-water tracking
```

These live under `harness/microbenches/`.

### 4. Runtime Profiling Contract

Every frame should be able to report:

```text
frame id
game tick cost
BSP/project/clip cost
sprites emitted
max sprites on a scanline
SCB1 tilemap words
SCB2/3/4 control words
fix/palette words
RAM high-water mark
degrade mode entered
```

Early output can be fix-layer text. Later output can be a ring buffer dumped through emulator/debugger.

## Is Memory Profiling Already Possible?

Partly.

ngdevkit and GDB help inspect symbols and memory while debugging. They do not automatically know this project's RAM pools, command buffers, or frame budgets.

So the project should add:

```text
static pool allocators with high-water counters
renderer command-list counters
SCB write counters
per-frame profile struct
debug overlay on fix layer
optional emulator-readable profile ring buffer
```

## First Harness Target

Milestone 0B should answer:

```text
How many full-height wall-like sprites can we rewrite when SCB1 tilemaps change?
How many can we update when only SCB2/3/4 position/shrink changes?
How many visible artifacts appear if we write outside vblank?
What command mix is safe for 15 fps, 12 fps, 10 fps?
```

