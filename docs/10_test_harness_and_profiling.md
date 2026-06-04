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

### 5. Host-Compilable Renderer Logic (the highest-leverage test choice)

Split the renderer so the **decisions** are host-portable and the **hardware pokes** are target-only:

```text
pure / host-compilable:  BSP traversal, projection, clipping, chunk subdivision,
                         card+palette selection, thing LOD, budget/degrade logic.
                         Output = an array of ng_sprite_cmd_t (the SCB shadow).
target-only:             turning that array into REG_VRAMADDR/RW/MOD writes.
```

Compile the pure half for the host (x86) too. Then the sprite command list for a
fixed (map, player pose) is produced and tested **without an emulator**, in
milliseconds, in CI. This is what lets an agent prove the renderer is right
before any ROM boots. Do not entangle game/render decisions with VRAM writes.

### 6. Golden-File Tests (catch the silent, plausible-but-wrong bugs)

```text
planar round-trip:  PNG tile -> Neo Geo planar -> decode -> must equal source.
                    (The encoding in 13 section 5 is the #1 place to be wrong.)
endianness:         map-bank field -> bytes -> reparse -> must equal value.
scene -> list:      fixed (map, pose) -> ng_sprite_cmd_t[] -> diff vs committed
                    golden (sprite count, indices, shrink, palette, role).
```

Regenerate goldens only on purpose, and review the diff — a changed golden is a
changed renderer, and should be explained in the commit.

### 7. Determinism / Replay Harness

Drop PC demo-sync, but keep your own:

```text
- record an input stream (per-tick buttons + RNG seed).
- run the host build, hash game state each tick.
- replay must reproduce identical hashes (host) and the same on target.
```

This gives regression demos for free and a topology A/B against PC Doom: from
identical coordinates, geometry must match even where fidelity does not.

### 8. MAME Hardware-In-The-Loop (turn "runs in emulator" into a CI assertion)

The per-frame profile struct (layer 4) lives at a known RAM address. A MAME Lua
script reads it headlessly while replaying a recorded input demo and asserts the
milestone gate:

```text
for each frame: read fps, peak sprites/line, SCB words, RAM HWM, degrade mode
fail the run if peak sprites/line > 96 ever, or fps < gate, or RAM > 56 KiB,
or VRAM "snow"/corruption heuristics trip.
```

Emulator-only fps lies about VRAM timing; promote to real MVS/AES via flashcart
at M2 and again at M4.

## CI Gate (`scripts/run_host_tests.sh` should enforce)

```text
[ ] all budget scripts exit OK on every committed golden scene
[ ] shrink-only guard: no ng_sprite_cmd_t requests size > source
[ ] RAM ledger sums under target (ram_budget.py)
[ ] planar + endianness round-trips pass
[ ] scene->list goldens match
[ ] determinism replay reproduces state hashes
[ ] legal guard: no IWAD/BIOS/ROM staged for commit
```

The MAME hardware-in-the-loop run is the per-milestone gate, run before declaring
any milestone passed.

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

