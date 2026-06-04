# Load-Bearing Hardware Truths

These are the facts most likely to quietly kill the project if they are not treated as design law.

## 1. Shrink Only

Neo Geo scaling only reduces. It never enlarges.

Implications:

```text
walls:    author cards at the maximum visible height, then shrink down
monsters: pre-upscale offline to the closest looming size, then shrink down
weapons:  author at final largest size
runtime:  assert no requested size exceeds source size
```

This is not a quality issue. It is physical.

## 2. Coarse Columns Are Required

Do not inherit the Wolfenstein 80-column mental model.

Doom columns stack:

```text
upper texture
lower texture
middle wall
wall visible through a gap
monster strips
projectiles/effects
```

At 80 narrow columns the center scanline budget dies before combat. Default to 16 px wall chunks and spend 8 px chunks only where the scene has budget.

## 3. VRAM Upload Is Its Own Clock

The project has at least three clocks:

```text
CPU geometry/game clock
sprite scanline/fill clock
VRAM upload clock
```

The upload clock must be benchmarked before Doom code exists.

Changing a wall card may require SCB1 tilemap writes, not just X/Y/shrink updates. A full-height 32-tile sprite uses 64 SCB1 tilemap/attribute words before SCB2/3/4 control data.

## 4. The Fixed Horizon Is A Gift

No pitch means the horizon stays fixed.

Version 1 floor/ceiling:

```text
top half: solid ceiling/sky color
bottom half: solid floor color
walls: draw over it
```

Do not spend full-height sprite columns on a floor/ceiling backplane unless a later feature earns it.

## 5. The Baseline Atlas Is Smaller Than The Fancy Atlas

Start with:

```text
texture tiled vertically to max card height
16 px U slices
a few vertical phases
palette light bands
hardware X/Y shrink for distance
```

Precomputed mip/coverage variants are a quality pass for shimmer, not a v1 requirement.

## 6. The Pseudo-Framebuffer Is Mostly A Trap

Static images do not need an arbitrary runtime bitmap path.

```text
title/menu/intermission: static sprite/fix compositions
screen wipe: vertical sprite-column trick
automap: fix/sprite drawing first, pseudo-framebuffer only if needed
```

Keep the 4x4 dictionary idea in reserve, but do not let it consume early project energy.

## 7. Occlusion Is Strip Dropping

There is no Z-buffer and no stencil.

Monster/object occlusion should be:

```text
split billboard into 16 px strips
compare each strip against wall depth/opening buckets
drop occluded strips
accept 16 px popping at corners
```

That is the honest Neo Geo version of Doom's masked-column clipping.

## 8. Board/Flashcart ROM Limits Beat Theoretical Limits

NeoGeoDev documents large sprite address space, but the actual target board or flashcart sets the practical ceiling.

Before committing to a card atlas:

```text
identify target cart/flashcart
identify C/P/V/M/S ROM limits
reserve space for tools, metadata, and alignment
prove packing fits
```

