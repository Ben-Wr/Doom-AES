# Milestone 2: E1M1 Walls

Purpose:

```text
Compile E1M1 geometry + wall textures from a user-provided DOOM1.WAD and walk
it at scale. Recognizable as E1M1, walls only, with the degrade ladder wired in.
```

The hardcoded deliverables, gate (recognizable E1M1, never >96 sprites/line via
deterministic degrade, >=10 fps ordinary / >=6 fps worst, banked P-ROM, no
runtime WAD parsing), and kill criteria are in
[docs/05_milestones.md](../../docs/05_milestones.md) under **M2**.

Offline pipeline: [docs/04_asset_pipeline.md](../../docs/04_asset_pipeline.md) and
[docs/09_asset_conversion_pipeline.md](../../docs/09_asset_conversion_pipeline.md).

Work log:

```text
host WAD reader (tools/wad2ng) + ZDBSP/glBSP nodes
map lump extraction -> compact banked map output
wall texture composition (TEXTURE1/PNAMES) -> 16px U cards + phases + light palettes
full BSP traversal + seg projection + chunk LOD by distance/pressure
upper/middle/lower wall emission; doors/stairs/windows
deterministic degrade ladder (merge far chunks, widen, drop optional features)
worst-case-scene regression suite seeded from E1M1's nastiest sightlines
budget reports per scene (fps, peak sprites/line, SCB words, RAM)
```

No commercial IWAD data is committed here. Record results in `RESULT.md`.
