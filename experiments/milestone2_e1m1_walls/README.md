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
[x] host WAD reader (tools/wad2ng)
[x] map lump extraction -> compact big-endian map bank output
[x] generated C header for ROM-side experiments
[x] generated SVG map preview for visual inspection
[ ] ZDBSP/glBSP node rebuild integration
[x] placeholder-wall ROM consumes generated E1M1 map header
[x] BSP traversal + seg projection + chunk LOD by distance/pressure
[x] upper/middle/lower wall emission from real E1M1 sectors/sidedefs
[x] deterministic first-pass degrade ladder (bucket merge before sprite overflow)
wall texture composition (TEXTURE1/PNAMES) -> 16px U cards + phases + light palettes
worst-case-scene regression suite seeded from E1M1's nastiest sightlines
budget reports per scene (fps, peak sprites/line, SCB words, RAM)
```

No commercial IWAD data is committed here. Record results in `RESULT.md`.

Compile the local ignored IWAD:

```sh
make -C experiments/milestone2_e1m1_walls WAD=../../iwads/DOOM1.WAD compile-map
make -C experiments/milestone2_e1m1_walls WAD=../../iwads/DOOM1.WAD
make -C experiments/milestone2_e1m1_walls WAD=../../iwads/DOOM1.WAD mame-capture
```

Generated WAD-derived outputs stay under `build/` and must not be committed.
