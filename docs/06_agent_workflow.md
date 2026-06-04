# Agent Workflow

This file is for future coding agents.

## First Five Minutes

1. Read `README.md`.
2. Read `docs/00_problem_decomposition.md`.
3. Run `scripts/check_env.sh`.
4. Check `git status --short`.
5. If references are missing, run `scripts/fetch_references.sh`.

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
