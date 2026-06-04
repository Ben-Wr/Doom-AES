# Milestone 0A: Sprite Path

Purpose:

```text
Prove one max-size wall card can be displayed, shrunk DOWN only, recolored,
and moved freely -- the bedrock hardware path, before any Doom code.
```

The hardcoded deliverables, gate, and kill criteria are in
[docs/05_milestones.md](../../docs/05_milestones.md) under **M0A**. That file is
the authority; do not restate thresholds here.

Build/run/debug: [docs/11_toolchain_and_build.md](../../docs/11_toolchain_and_build.md).
Hardware facts you will need: [docs/08_load_bearing_hardware_truths.md](../../docs/08_load_bearing_hardware_truths.md)
sections 1 (shrink granularity), 2 (SCB layout), 7 (auto-anim / palette banks).

Work log:

```text
[x] choose SDK/toolchain path (ngdevkit), build a minimal ROM
[x] author one 16x512 (32-tile) card at MAX size in C-ROM
[x] write SCB1 tilemap + SCB2 shrink + SCB3 Y/size + SCB4 X
[x] cycle Y-shrink (8-bit), X-shrink (4-bit), palette band; move X/Y
[x] fix-layer overlay: card px height, shrink values, palette id, sprites/line
[x] shrink-only assert: requested size must never exceed source size
```

Build:

```sh
make -C experiments/milestone0_sprite_path
```

Outputs:

```text
build/m0a.neo                 milestone-named cartridge zip copy
build/rom/m0a.zip             ROM zip for MAME/GnGeo-style launchers
build/rom/neogeo.zip          generated ngdevkit null BIOS copy for local GnGeo
build/m0a.xml                 generated MAME software-list entry
build/gngeo_data.zip          generated GnGeo driver data with the m0a entry
```

Controls:

```text
D-pad    move the card
A        cycle Y-shrink through 10 values, $FF down to $00
B        cycle X-shrink through 5 values, $F down to $0
C        cycle 8 palette bands
D        deliberately requests 513px height to trip the shrink-only guard
START    reset position/shrink/palette/guard
```

Palette caveat: the milestone says "one SCB attribute change", but SCB1 stores
the palette in every tile-row attribute word. This ROM rewrites the 32 SCB1
attribute words for the 32-tile card when `C` changes palettes. The C-ROM card
art is not duplicated.

When the M0A gate is met in MAME neogeo, record measured numbers in `RESULT.md`.
No Doom renderer belongs here.
