# Problem Decomposition

## Up-Front Verdict

Attachment 2 is the better core renderer. Attachment 1 is a clever proof of escape, but it should not be an early dependency.

The main game should be:

```text
Doom BSP -> projected segs/things -> Neo Geo sprite command list
```

The fallback display, only if it earns its keep, is:

```text
Tiny RAM framebuffer -> 4x4 block encoder -> ROM mask-tile dictionary
```

The reason is simple: the Neo Geo is bad at arbitrary pixels, but excellent at vertical sprite strips fetched from cartridge C-ROM. Doom's visible wall renderer is also column/strip-shaped once the BSP front-end has projected map geometry. That overlap is the crack in the wall.

The dominant correction:

```text
Neo Geo scaling only shrinks.
It never enlarges.
```

Every wall card, monster strip, and weapon frame must be authored at the largest on-screen size it may ever need, then shrunk down. "Requested size larger than source size" is a hard renderer bug.

## What The Port Must Mean

This is a Doom port if these survive:

```text
Real Doom-derived maps, compiled offline
Real Doom-like collision and 2.5D movement
Free rotation, forward/back, strafing
Sectors, linedefs, heights, doors, stairs, lifts, switches
Doom monsters, weapons, pickups, projectiles, damage, secrets
Episode progression and recognizable level flow
```

This does not need to survive:

```text
The PC framebuffer renderer
320x200 visual fidelity
Textured floors and ceilings
Exact colormap lighting
Runtime WAD parsing
Exact demo sync
35 fps
Uncapped Doom II chaos
```

## Problems To Sort

### 1. Display

The Neo Geo has no bitmap mode. The CPU cannot draw a normal framebuffer to display memory. The project must never assume random pixel writes are available.

Primary answer:

```text
Emit sprite control data for precomputed C-ROM wall cards and thing strips.
```

Secondary answer:

```text
Keep the 4x4 mask dictionary as a research escape hatch.
```

Most menu/title/intermission content is known at compile time and can be static sprite/fix composition. Even Doom's screen wipe is naturally a vertical sprite-column effect. Do not build the pseudo-framebuffer until a runtime-unknown bitmap need survives review.

### 2. Geometry

Doom geometry survives because it is not a raycaster problem. Use Doom's BSP, segs, subsectors, sector heights, and clipping logic as the semantic source.

The Neo Geo renderer should consume:

```text
projected wall segment endpoints
screen x range
screen top/bottom
texture material id
approximate U coverage
sector light band
upper/middle/lower wall role
```

### 3. Texture Mapping

The CPU cannot sample C-ROM texture pixels. Wall textures must be compiled offline into C-ROM cards.

Runtime chooses:

```text
material
u slice
vertical phase
palette/light band
```

Runtime does not sample texels.

The baseline atlas should use hardware X/Y shrink as the first mip/scale tool. Precomputed coverage variants are a later shimmer-reduction pass, not the minimum viable atlas.

### 4. Angled Walls

Angled walls are not impossible. They are budgeted.

```text
Near or important wall: smaller chunks, more sprites, better perspective.
Normal wall: 16 px chunks.
Far or busy wall: wider chunks, fewer sprites, more affine warp.
```

Perspective correction happens at chunk boundaries, not per pixel.

### 5. Floors And Ceilings

Textured flats are cut first.

Version 1:

```text
fixed horizon split
solid ceiling or sky color above center
solid floor color below center
no visplanes
no floor texture sampling
no ceiling texture sampling
```

Because there is no pitch, the horizon is stable. Solid floor/ceiling can be effectively free through backdrop/fix-layer strategy. Scrolling sky or per-sector floor color is a later feature.

### 6. Monsters And Objects

Things are scaled billboards made from 16-pixel vertical sprite strips.

They need:

```text
offline pre-upscaled source art
depth bucket or sort
per-strip wall occlusion/drop
LOD by distance and sprite pressure
palette-light selection
active thinker caps
```

### 7. Weapons

Weapons should be foreground Neo Geo sprites, not tiny pseudo-framebuffer art, once the primary sprite renderer exists.

The weapon silhouette is one of the highest-value Doom identity signals. Spend ROM there. Author the weapon at the largest foreground size it will ever display.

### 8. RAM

64 KiB work RAM kills normal Doom data structures.

Kill:

```text
zone allocator
runtime WAD cache
visplanes
full PC mobj structs
full patch compositing at runtime
large resident maps
```

Keep:

```text
compact active mobj pool
dynamic sector/line overlays
renderer scratch and clip arrays
sprite command shadow list
small game state
stack
```

### 9. ROM

Cartridge ROM is the lever, but practical board/flashcart limits beat theoretical maximums.

Put in ROM:

```text
map geometry banks
node/subsector tables
texture metadata
wall-card atlas
pre-upscaled sprite strips and LODs
weapon strips
brightness palettes
trig/projection/reciprocal tables
ADPCM samples
```

### 10. CPU, VBL, And SCB Upload

The 68000 should do game logic, BSP traversal, projection, clipping, list construction, and budget decisions. It should not draw pixels.

Every prototype must measure:

```text
visible seg count
wall chunks emitted
thing strips emitted
per-scanline sprite count
SCB1 tilemap words written
SCB2/3/4 control words written
frame time
```

The first benchmark should not be a Doom renderer. It should be raw VRAM upload: how many wall-like sprite entries, including tilemaps and position/shrink words, can be rewritten in the safe update window without visual damage?

### 11. Content And Legal

No commercial IWAD data ships in the repo or cart image unless the legal distribution story is solved.

Correct pipeline:

```text
user-owned IWAD, shareware IWAD, or licensed free IWAD
PC-side compiler
Neo Geo ROM banks
```

### 12. Sound

Sound is not the blocker. SFX can become ADPCM samples. Music needs FM/PSG arrangement or sample-based adaptation.

## The Core Bet

The project lives or dies on this question:

```text
Can one real Doom room be walked freely while projected wall/thing chunks are emitted as Neo Geo sprites under the scanline, RAM, CPU, and SCB upload budgets?
```

If yes, the rest is asset pipeline and discipline. If no, the port retreats to a different display experiment.
