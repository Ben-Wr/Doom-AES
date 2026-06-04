# Doom AES

This workspace is a feasibility and prototype lab for a stock Neo Geo AES/MVS Doom port.

The core thesis is deliberately narrow:

```text
Do not port Doom as a framebuffer game.
Port Doom as a BSP/seg/thing-to-Neo-Geo-sprite-list compiler.
Use a ROM-heavy asset pipeline to precompute wall cards, sprites, palettes, and map tables.
Keep the tiny ROM-backed pseudo-framebuffer as a debug/fallback layer, not the main renderer.
```

## Start Here

Read these in order:

1. [Problem decomposition](docs/00_problem_decomposition.md)
2. [Core principles](docs/01_core_principles.md)
3. [Constraints and tests](docs/02_constraints_and_tests.md)
4. [Renderer spec](docs/03_renderer_spec.md)
5. [Asset pipeline](docs/04_asset_pipeline.md)
6. [Milestones](docs/05_milestones.md)
7. [Agent workflow](docs/06_agent_workflow.md)
8. [Research index](docs/07_research_index.md)
9. [Load-bearing hardware truths](docs/08_load_bearing_hardware_truths.md)
10. [Asset conversion pipeline](docs/09_asset_conversion_pipeline.md)
11. [Test harness and profiling](docs/10_test_harness_and_profiling.md)

## Workspace Layout

```text
docs/                         Design doctrine and project rules
scripts/                      Environment checks and budget calculators
experiments/milestone0_*      First Neo Geo sprite-path proof
experiments/milestone1_*      One-room Doom geometry proof
experiments/milestone2_*      E1M1 walls-only proof
harness/                      Neo Geo microbench/profiling experiments
external/                     Downloaded source/tool references, ignored by git
references/                   Mirrored docs and research notes, ignored/generated where appropriate
tools/                        Tooling notes and future custom utilities
```

## Legal Boundary

The Doom source code is open source. The commercial Doom IWAD data is not.

This repo must never commit `DOOM.WAD`, `DOOM1.WAD`, BIOS files, MAME ROM sets, or any other copyrighted game data. The asset pipeline should consume a user-provided IWAD locally and generate Neo Geo-specific outputs.

## Useful Commands

```sh
scripts/check_env.sh
scripts/setup_python_tools.sh
scripts/wad2ng_bulk_extract.sh
scripts/fetch_references.sh
scripts/card_atlas_budget.py
scripts/pseudo_framebuffer_budget.py
scripts/vram_upload_budget.py
scripts/ram_budget.py
```

## First Real Gate

Milestone 0 is not Doom. It is proving the hardware path:

```text
One 16 px wide wall card authored at maximum size.
Free X/Y positioning.
Y shrink and X shrink only.
Palette band switching.
SCB tilemap/control update timing.
VRAM writes measured against the safe update window.
```

If that is not stable in emulator and on plausible hardware constraints, nothing downstream matters.
