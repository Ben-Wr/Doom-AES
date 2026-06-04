# Milestones (Hardcoded)

These are contracts, not aspirations. A milestone is **passed** only when every line in its **Gate** is demonstrated in a cycle-accurate emulator (MAME `neogeo`) with the per-frame profile overlay visible — host-side estimates and screenshots are necessary but never sufficient. If a **Kill** line trips and cannot be bought back within the milestone's own scope, stop and escalate to the fallback in [00_problem_decomposition.md](00_problem_decomposition.md), do not paper over it.

Ordering is deliberate: the two things most likely to kill the project (shrink-down quality and VRAM upload bandwidth) are proven in M0, before any Doom code exists.

## Definition Of Done (applies to EVERY milestone)

```text
[ ] Builds from `make` with the pinned ngdevkit toolchain (see 11_toolchain_and_build.md).
[ ] Runs in MAME neogeo (cycle-accurate) without VRAM "snow" or sprite corruption.
[ ] Per-frame profile overlay (fix layer) shows: fps, peak sprites/line, SCB words
    written, RAM high-water, degrade mode.
[ ] No metric exceeds its hard limit at ANY point during a scripted demo run.
[ ] `scripts/run_host_tests.sh` is green.
[ ] No commercial IWAD / BIOS / ROM data committed.
[ ] A short RESULT.md in the experiment dir records measured numbers vs the gate.
```

## Global Kill Criteria

The PRIMARY sprite-BSP renderer is in danger if any of these hold after honest optimization:

```text
- M0B cannot stream ~1,500+ SCB words per vblank without artifacts.
- M0B cannot fit ~40 wall chunks + ~24 thing strips per frame even WITH tilemap
  caching and active-display spreading.
- M1 cannot hold 12 fps in a one-sector room.
- M1 peak sprites/line cannot stay <= 84 in a one-sector room.
- E1M1 walls-only is unreadable even with generous ROM.
- Minimal game state + renderer lists do not fit in 56 KiB with margin.
```

Only if these fail does the 4x4 pseudo-framebuffer get promoted to main renderer.

---

## M0A — Hardware Sprite Path

Dir: `experiments/milestone0_sprite_path/`. No Doom code.

Goal: prove a maximum-size wall-like card displays, shrinks down only, recolors, and moves, within budget.

Deliverables:

```text
- m0a.neo ROM.
- One 16x512 (32-tile) test card in C-ROM, authored at MAX size.
- 8+ brightness/tint palettes for that card in palette RAM.
- Controls: move card X/Y; cycle Y-shrink; cycle X-shrink; cycle palette band.
- Fix-layer overlay: card height px, Y-shrink, X-shrink, palette id, sprites/line.
```

Gate (all required):

```text
[ ] Card displays at >= 8 distinct heights via Y-shrink ($FF down to a sliver).
[ ] Card displays at >= 3 distinct widths via X-shrink, with understood decimation.
[ ] Card recolors through >= 8 palettes with one SCB attribute change (no art dup).
[ ] Requesting height > source height is caught by an assert (shrink-only guard).
[ ] Peak sprites/line stays under 96 at all times.
[ ] Y position uses the 496 - top convention correctly (card lands where intended).
```

Kill:

```text
- Hardware-shrunk card art is unreadable/unacceptable at typical wall heights.
- The decimation pattern destroys texture identity beyond recognition.
```

## M0B — VRAM Upload Benchmark (the gating risk)

Dir: `harness/microbenches/vram_upload_scb/`. No Doom code.

Goal: measure the real per-vblank SCB write budget and prove the tilemap-cache path. This number sets the frame rate; get it before falling in love with the design.

Deliverables:

```text
- m0b.neo ROM that streams synthetic SCB writes via REG_VRAMMOD and counts them.
- Mode A: rewrite N full SCB1 tilemaps/frame (worst case) until artifacts appear.
- Mode B: rewrite only SCB2/3/4 for N sprites/frame (cached case).
- Mode C: mixed -- F fraction of N sprites get new tilemaps (realistic).
- On-screen report: words written this vblank, artifact flag, effective fps.
```

Gate (all required):

```text
[ ] Measured streamed-write rate recorded in cycles/word (expect ~12).
[ ] Max artifact-free streamed words/vblank measured (expect ~1,500-2,000).
[ ] Mode C proves a 40-wall (<=25% card change) + 24-thing scene fits one vblank.
[ ] Behavior of writing outside vblank characterized (where tearing starts).
[ ] `scripts/vram_upload_budget.py` re-tuned so its estimate matches measurement.
```

Kill: see Global Kill Criteria (first two lines).

## M1 — One Doom-Like Room

Dir: `experiments/milestone1_one_room/`. First Doom geometry.

Goal: walk freely in one tiny hand-authored Doom room built from real Doom data structures (vertices/linedefs/sectors/segs/subsectors), rendered as scaled sprites.

Deliverables:

```text
- m1.neo ROM.
- Hand-authored: 1-2 sectors, >= 3 walls, 1 height change (step), 1 working door.
- Fixed-point player move + rotate + strafe; collision against the linedefs.
- BSP/seg project -> chunk subdivide -> emit middle + at least one upper/lower wall.
- Door = dynamic sector height -> sprite Y-extent + role updates per frame.
- Fixed-horizon floor/ceiling (v1 single backdrop color is acceptable).
- SCB caching live (only changed cards rewrite SCB1).
```

Gate (all required, HARD numbers):

```text
[ ] 12 fps floor sustained while moving and turning in the room.
[ ] Peak sprites/line <= 84 at all times.
[ ] SCB words/vblank <= 1,664 practical at all times (overlay-verified).
[ ] RAM high-water <= 56 KiB.
[ ] Door open/close shows correct upper/lower wall roles and Y-extents.
[ ] No runtime WAD parsing; geometry is compiled-in static data.
```

Kill: cannot hold 12 fps OR cannot keep <= 84 sprites/line in a ONE-sector room.

## M2 — E1M1 Walls Only

Dir: `experiments/milestone2_e1m1_walls/`. Real BSP at scale.

Goal: compile E1M1 geometry + wall textures from a user-supplied DOOM1.WAD and walk it. Recognizable as E1M1, walls only.

Deliverables:

```text
- m2.neo ROM + the offline map/texture compile that produced its banks.
- Full BSP traversal, seg projection, chunk LOD by distance/pressure.
- Upper/middle/lower wall emission across the whole map.
- The deterministic degrade ladder WIRED IN (merge far chunks, widen, etc.).
- Worst-case-scene regression suite seeded with E1M1's nastiest sightlines.
```

Gate (all required):

```text
[ ] A first-time player recognizes E1M1 (start room, courtyard, zigzag, exit).
[ ] Peak sprites/line NEVER exceeds 96 -- degrade ladder engages before overflow.
[ ] >= 10 fps in ordinary rooms; >= 6 fps in the worst sightline.
[ ] Degradation is deterministic: same view -> same drops, every time.
[ ] Map data is banked P-ROM; no runtime WAD parsing; no zone allocator.
[ ] Worst-case suite logged (fps, peak sprites/line, SCB words, RAM) per scene.
```

Kill: E1M1 unreadable with generous ROM, OR overflow cannot be prevented deterministically.

## M3 — Things And Weapons

Goal: make it Doom combat.

Deliverables:

```text
- Pre-upscaled, strip-built billboards: zombieman, imp, barrel, 1 pickup, 1 projectile.
- Player weapon as frontmost foreground sprites + muzzle-flash card.
- Per-strip occlusion (drop strips behind nearer walls).
- Hitscan + projectile + barrel chain; damage loop; health/ammo on the HUD.
- Active-object cap enforced per map.
```

Gate (all required):

```text
[ ] Weapon sprites never push peak sprites/line over budget (weapon has its own reserve).
[ ] Per-strip occlusion is correct enough to fight around pillars (16px popping OK).
[ ] Thing LOD: near = full strips, far = 1-2 strips, with no shrink-only violation.
[ ] Active-object cap enforced; spawning past it is handled deterministically.
[ ] Playable: a player can clear the M1/M2 room of monsters and read the fight.
```

Kill: combat is unreadable, OR things cannot be occluded well enough to aim.

## M4 — Shareware Loop

Goal: a playable shareware-style episode loop, end to end.

Deliverables:

```text
- Title + menu (static sprite/fix compositions, NOT the pseudo-framebuffer).
- Doom status bar (fix layer + a few sprites for the face).
- E1M1..E1M8 (+ E1M9 secret) progression, simplified per-map as needed with reports.
- SFX as ADPCM (V-ROM); music as YM2610 FM/PSG arrangements.
- Intermission, death/restart, difficulty settings.
```

Gate (all required):

```text
[ ] No commercial data committed; build consumes a user-supplied DOOM1.WAD locally.
[ ] Every map compiles and produces a simplification + budget report.
[ ] Worst rooms in every map degrade deterministically and never overflow.
[ ] Full loop is completable start to finish without crash or budget breach.
```

Kill: a shareware map exists that cannot be made to fit the budgets even after simplification.

## M5 — Quality Pass

Only after M4 works. No quality work earns time before the loop is real.

```text
better palettes; more wall-card variants; mip/coverage cards where decimation shimmers;
more monster rotations; optional scrolling sky; optional per-sector floor color;
auto-animation for animated textures; improved strip occlusion; asm hot paths;
real MVS/AES hardware testing via flashcart; registered Doom / Doom II from user WAD.
```

Gate: each quality feature passes the same budget overlay it touches, and the worst-case regression suite shows no fps/RAM/sprite regression.
