# Agent Workflow

This file is for future coding agents.

## First Five Minutes

1. Read `README.md`.
2. Read `docs/00_problem_decomposition.md` and `docs/08_load_bearing_hardware_truths.md`.
3. Read the gate for the milestone you are on in `docs/05_milestones.md`.
4. Run `scripts/check_env.sh`.
5. Check `git status --short`. If references are missing, run `scripts/fetch_references.sh`.

## Don't Claim, Measure

This is the first rule, because it is the one an agent breaks most.

```text
- A feature is not "working" and a milestone is not "passed" until the numeric
  gate is shown by the profile overlay / CI, not asserted in prose.
- Quote the measurement (fps, peak sprites/line, SCB words, RAM HWM) in the PR.
- If you did not run it, say so. A skipped step is reported, never implied done.
- Any hardware number you state must trace to references/neogeodev/md/, not memory.
```

## Make Your Work Testable Without Hardware

```text
- Keep render/game DECISIONS in host-compilable code that emits ng_sprite_cmd_t[];
  keep VRAM pokes in a thin target-only layer (see docs/10 layer 5).
- Add/extend a golden test when you add an encoder or a renderer decision.
- Run the determinism replay after touching game logic.
```

## Default Bias

Favor:

```text
small measurable experiments
explicit budgets
offline precomputation
generated reports
hardware-shaped data
```

Avoid:

```text
PC renderer nostalgia
runtime WAD parsing
large RAM-resident structs
unmeasured visual tricks
opaque prototype glue
```

## Before Adding A Renderer Feature

Write down:

```text
which hardware limit it touches
which budget script or counter will measure it
whether it needs SCB1 tilemap updates or only position/shrink updates
whether it respects shrink-only source sizing
which milestone it advances
what degrades first when it is too expensive
```

## Before Adding Asset Pipeline Code

Write down:

```text
input legal status
output ROM region
runtime RAM impact
maximum source display size for shrink-only safety
metadata schema
report fields
```

## No Commercial Data

Never download or commit IWADs, BIOS files, or commercial ROMs.

It is acceptable to create local ignored directories:

```text
iwads/
bios/
roms/
```

But the repo must remain clean without them.

## Reference Policy

Downloaded mirrors live under:

```text
references/
external/
```

They are for local study and should not become source dependencies without a deliberate decision.

## Promotion Rule

Prototype code graduates only when it has:

```text
clear owner module
budget instrumentation
test input
documented assumptions
```
