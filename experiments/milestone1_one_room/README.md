# Milestone 1: One Room

Purpose:

```text
Walk freely through one hand-authored Doom-shaped room rendered as scaled
sprites: BSP project -> chunk subdivide -> emit walls, with a working door.
```

The hardcoded deliverables, gate (12 fps floor, <=84 sprites/line, <=1,664 SCB
words/vblank, <=56 KiB RAM), and kill criteria are in
[docs/05_milestones.md](../../docs/05_milestones.md) under **M1**. That file is
the authority.

See [docs/03_renderer_spec.md](../../docs/03_renderer_spec.md) for the frame flow,
SCB caching, and the fixed-horizon floor/ceiling technique.

Work log:

```text
- fixed-point player move / rotate / strafe + linedef collision
- hand-authored vertices/linedefs/sectors/segs/subsectors (compiled-in, static)
- project wall endpoints; subdivide into coarse chunks; pick cards + palettes
- emit middle wall + at least one upper/lower case
- door = dynamic sector height -> sprite Y-extent + role updates
- fixed-horizon floor/ceiling (v1 single backdrop color OK)
- SCB caching: only rewrite SCB1 for chunks whose card id changed
- per-frame profile overlay on the fix layer
```

This experiment may use placeholder wall cards. Record results in `RESULT.md`.

Build and smoke:

```sh
make -C experiments/milestone1_one_room
make -C experiments/milestone1_one_room mame-capture
make -C experiments/milestone1_one_room mame-bench
```

`mame-capture` lets the built-in auto-demo exercise move/turn/strafe and the
door, then saves a native MAME screenshot under `build/snap/neogeo/0000.png`.
