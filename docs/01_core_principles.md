# Core Principles

## 1. Doom Semantics Beat Doom Pixels

The port is faithful to maps, rules, weapons, monsters, and spatial behavior before it is faithful to PC pixels.

Renderer fidelity is negotiable. Doom gameplay identity is not.

## 2. The CPU Must Not Draw The Main View

The 68000 may project, clip, sort, budget, and emit commands.

It must not spend the frame sampling texture pixels and writing display pixels. The primary renderer has no normal framebuffer.

## 3. Author Tall, Shrink Down

Neo Geo scaling is reduction only.

```text
wall cards:    authored at max visible height, likely 512 px
monsters:      pre-upscaled offline to their closest visible size
weapons:       authored at final largest foreground size
far objects:   same art shrunk down or LOD-replaced
```

If runtime wants a sprite larger than its source, that is a build/runtime assertion failure.

## 4. C-ROM Is Texture Memory

C-ROM pixels are for the LSPC to fetch. The CPU addresses C-ROM graphics only indirectly by tile/card id.

If a runtime algorithm says "sample this texture pixel from C-ROM," redesign it.

## 5. Spend ROM To Save RAM And CPU

Precompute everything that can be precomputed:

```text
wall cards
pre-upscaled sprite strips
LOD variants
brightness palettes
reciprocal tables
angle tables
map banks
texture-use tables
```

Neo Geo cartridges are the advantage. Treat ROM as computation that already happened.

## 6. Walls Win

When sprite pressure rises, the drop order is:

```text
decorative things
optional scrolling sky or special backdrop
far pickup detail
far monster strips
distant upper/lower texture detail
low-priority projectiles or effects
```

Walls and gameplay-readable enemies should survive longest.

## 7. Floors And Ceilings Stay Cheap Until Proven Otherwise

No textured flats in the main plan.

Flat colors and a fixed horizon split are acceptable. Doom's horizontal span renderer is the wrong workload for this machine.

## 8. Every Feature Has A Budget Test

A feature is not "working" until it passes:

```text
per-scanline sprite count
visible sprite count
RAM budget
SCB1 tilemap write budget
SCB2/3/4 control write budget
CPU frame budget
ROM budget
visual readability
```

Screenshots are not enough.

## 9. Make Degradation Deterministic

Never overflow and hope.

The renderer must have explicit LOD and panic paths:

```text
merge chunks
reduce thing strips
remove optional sky/backdrop features
drop decorations
quantize lights
clamp far windows
```

The same scene should fail the same way every time.

## 10. The Pseudo-Framebuffer Is A Last-Resort Tool

The 4x4 ROM mask dictionary may be useful for:

```text
debug visualizer
emergency far composite experiments
runtime-unknown bitmap experiments
```

It is not needed for static title/menu/intermission screens, and it should not become Milestone 1 unless the sprite-BSP route fails a measured hardware gate.

## 11. No Runtime IWAD Romanticism

The Neo Geo runtime should not parse WADs.

The PC-side compiler owns WAD reading, texture composition, node validation, simplification, palette selection, and bank layout. The cartridge owns compact compiled data.

## 12. Prove Small Before Pretty

The order is:

```text
sprite shrink path
VRAM/SCB upload benchmark
one room
E1M1 walls
things and weapons
shareware loop
quality
```

Any art-quality work that happens before the renderer is measurable must serve a test.

## 13. Watch Two Clocks And One Upload Gate

Every scene has independent ceilings:

```text
CPU geometry/game time
sprite scanline/fill pressure
VRAM/SCB upload volume
```

Profile all three for the life of the project.

## 14. Keep The Source Split Clean

Keep these concerns separate:

```text
host tools
compiled data formats
runtime game logic
runtime renderer
Neo Geo hardware abstraction
experiments
references
```

If an experiment proves something useful, promote the smallest piece of it. Do not let prototype glue become architecture.
