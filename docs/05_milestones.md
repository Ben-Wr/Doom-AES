# Milestones

## Milestone 0A: Hardware Sprite Path

Goal:

```text
Render one maximum-size wall-card-like sprite through Neo Geo sprites.
```

Acceptance:

```text
free X/Y positioning
Y shrink visible
X shrink visible
palette band switching visible
shrink-only guard understood
scanline count measured
```

No Doom code yet.

## Milestone 0B: VRAM Upload Benchmark

Goal:

```text
Measure how much representative sprite-control data can be rewritten in vblank or the chosen safe update window.
```

Acceptance:

```text
SCB1 tilemap write benchmark
SCB2/3/4 control write benchmark
representative wall+thing command mix
visible tearing/glitch check
measured words/frame budget
```

This benchmark partly sets the renderer's real sprite budget and frame cadence.

## Milestone 1: One Doom-Like Room

Goal:

```text
Walk freely in one tiny Doom-shaped room.
```

Content:

```text
one sector
two or more walls
one height change
one door or moving vertical extent
fixed horizon split floor/ceiling
no monsters
```

Acceptance:

```text
free movement and rotation
projected wall chunks stable
upper/lower/middle wall roles demonstrated
budget counters visible
around 12 fps target in the simple room
```

## Milestone 2: E1M1 Walls Only

Goal:

```text
Compile E1M1 geometry and wall textures, then walk it.
```

Content:

```text
BSP traversal
seg projection
chunk subdivision
wall-card selection
doors/stairs/windows
fixed horizon split
no monsters required
```

Acceptance:

```text
E1M1 recognizable
ordinary rooms under sprite/upload/CPU limits
budget manager merges chunks under pressure
no runtime WAD parsing
worst-case-scene regression suite begins here
```

## Milestone 3: Things And Weapons

Goal:

```text
Make it feel like Doom combat.
```

Content:

```text
weapon foreground sprites
pre-upscaled zombieman
pre-upscaled imp
barrel
pickup
fireball/projectile
hitscan
damage loop
health/ammo
```

Acceptance:

```text
per-strip occlusion playable
thing LOD works
weapon never destabilizes world budget
active object cap enforced
```

## Milestone 4: Shareware Loop

Goal:

```text
Playable shareware-style episode loop.
```

Content:

```text
title/menu as static sprite/fix compositions
status bar
E1M1-E1M8/E1M9 progression, reduced if needed
SFX
music approximation
difficulty settings
intermission
death/restart
```

Acceptance:

```text
no commercial data committed
all maps compile with reports
worst rooms degrade deterministically
```

## Milestone 5: Quality Pass

Only after the loop works:

```text
better palettes
more wall-card variants
more monster rotations
mip/coverage cards where decimation shimmers
optional scrolling sky
optional per-sector floor color
improved strip occlusion
asm hot paths
real hardware testing
```

## Kill Criteria

The primary renderer is in danger if:

```text
Milestone 0B cannot update representative sprite control data at a usable cadence
Milestone 1 cannot stay under scanline budget in a simple room
Milestone 1 cannot hold around 12 fps in a simple room
E1M1 walls-only is unreadable even with generous ROM
RAM cannot hold minimal game state plus renderer lists
```

Only after those fail should the project promote the 4x4 pseudo-framebuffer to main renderer.
