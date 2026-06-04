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
- choose SDK/toolchain path (ngdevkit), build a minimal ROM
- author one 16x512 (32-tile) card at MAX size in C-ROM
- write SCB1 tilemap + SCB2 shrink + SCB3 Y/size + SCB4 X
- cycle Y-shrink (8-bit), X-shrink (4-bit), palette band; move X/Y
- fix-layer overlay: card px height, shrink values, palette id, sprites/line
- shrink-only assert: requested size must never exceed source size
```

When the M0A gate is met in MAME neogeo, record measured numbers in `RESULT.md`.
No Doom renderer belongs here.
