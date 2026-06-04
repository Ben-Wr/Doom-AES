# Toolchain And Build

This is the "how do I actually build a ROM and poke the hardware" doc. Exact SDK
symbol names should be confirmed against `external/ngdevkit/`,
`references/neogeodev/md/Development_tools.md`, and `Hello_world_tutorial.md`;
the addresses below are the hardware truth and will not change.

## Toolchain

The spine is **ngdevkit** (dciabrin). On macOS:

```sh
scripts/install_macos_tools.sh    # brew tap dciabrin/ngdevkit; installs ngdevkit + deps
scripts/check_env.sh              # verifies the tools below resolve
```

What it provides (mirrored by `check_env.sh`):

```text
m68k-neogeo-elf-gcc / -gdb   68000 C/ASM compiler + debugger (the main CPU)
sdcc                         Z80 compiler (sound driver on the YM2610 side)
ngdevkit-gngeo               patched gngeo emulator, fast iteration + gdb stub
mame                         cycle-accurate `neogeo` driver -> the gate emulator
<ngdevkit/neogeo.h>          memory-mapped register + SCB definitions
<ngdevkit/ng-fix.h>          fix-layer text helpers (profile overlay)
graphics/rom tools           tile/sprite conversion + P/C/S/V/M ROM packing
```

## Build / Run / Debug Loop

```sh
make                 # build the experiment's .neo (and per-region P/C/S/V/M ROMs)
make gngeo           # fast run in ngdevkit-gngeo for iteration
mame neogeo -cart <rom>   # cycle-accurate run; this is what milestone gates use
m68k-neogeo-elf-gdb  # attach to gngeo's gdb stub for breakpoints/memory
```

Iterate in gngeo; **gate in MAME**. Emulator-only fps (especially gngeo) lies
about VRAM timing — confirm M2/M4 on real MVS/AES via a NeoSD/Darksoft flashcart.

## The Hardware Pokes You Will Live In

VRAM is not in the 68k address space; reach it through three registers (see
[08](08_load_bearing_hardware_truths.md) sections 2-3). Canonical addresses:

```text
REG_VRAMADDR  $3C0000   set word address
REG_VRAMRW    $3C0002   data read/write
REG_VRAMMOD   $3C0004   signed auto-increment added after each write
palette RAM   $400000   256x16 entries (active bank); backdrop = last entry
P-ROM bank    $2FFFFx   byte write selects the $200000-$2FFFFF bank
```

Streaming a sprite's contiguous SCB table (the only way to hit the budget):

```c
/* set address once, set the stride, then stream -- no per-word re-addressing */
*REG_VRAMADDR = SCB1_BASE + (sprite * 64);   /* SCB1 tilemap for this sprite */
*REG_VRAMMOD  = 1;                            /* auto-increment by 1 word */
for (int i = 0; i < words; i++)
    *REG_VRAMRW = tilemap[i];                 /* >=12 CPU cycles apart, per VRAM.md */
```

```text
- Cannot auto-increment across the $7FFF/$8000 zone boundary: re-address instead.
- SCB2/3/4 are per-sprite single words at $8000+n, $8200+n, $8400+n. Update them
  in batched streaming passes (all shrink, then all Y, then all X), not per-sprite.
- Writing Y (SCB3) must preserve the low 7 bits (sticky+size): read-modify-write.
- Screen top = 496 - Yfield. Place a sprite top at screen y T with field (496 - T).
- Heavy writes go in vblank; spreading across active display risks tearing on the
  lines being drawn.
```

## Fixed-Horizon Floor/Ceiling Via Timer IRQ (v1.5)

```text
- Program the LSPC timer interrupt to fire at the horizon scanline (screen center).
- In that handler, during hblank, rewrite the backdrop color (or a shared palette
  entry): ceiling color above the split, floor color below. ~1 IRQ, 0 sprites.
- Palette writes during ACTIVE display cause "snow"; do the swap in hblank.
```

v1 can skip this entirely and use one static backdrop color.

## Profile Overlay

Reuse the committed struct in `experiments/common/ng_profile.h`
(`ng_profile_frame_t`: frame_id, game/render/upload ticks, sprites_emitted,
max_sprites_scanline, scb1_words, scb_control_words, fix/palette words,
ram_high_water_bytes, degrade_flags). Render it as fix-layer text with
`<ngdevkit/ng-fix.h>`, and mirror it to a fixed RAM address so the MAME Lua
hardware-in-the-loop harness (see [10](10_test_harness_and_profiling.md) layer 8)
can read and assert it headlessly.

## Host Build For Tests

The render/game **decision** code must also compile for the host (x86) so golden
and determinism tests run in CI without an emulator (see
[10](10_test_harness_and_profiling.md) layers 5-7). Keep the VRAM-poke layer
behind a thin interface so the host build links a stub that records
`ng_sprite_cmd_t[]` instead of writing VRAM.
