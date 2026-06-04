# M0B Result

Date: 2026-06-04

Status: **instrumented and MAME-booting; manual artifact calibration still required before M0B can be marked passed.**

## Build

```text
make -C harness/microbenches/vram_upload_scb clean
make -C harness/microbenches/vram_upload_scb
scripts/run_host_tests.sh
make -C harness/microbenches/vram_upload_scb mame-bench
```

Artifacts generated under ignored `build/`:

```text
build/m0b.neo
build/rom/m0b.zip
build/neogeo.xml
build/gngeo_data.zip
build/rom/neogeo.zip
```

No IWAD, commercial BIOS, or commercial ROM data is committed.

## ROM Modes

```text
FULL      rewrite N full 32-tile SCB1 wall cards, plus controls
CTRL      rewrite only SCB2/3/4 controls for N sprites
MIXED     40 wall controls + N changed wall cards + 24 thing tilemaps
ACTIVE    delay past vblank, then write N full cards + controls
```

Controls:

```text
A        cycle benchmark mode
B / C    increase / decrease the mode target
D        toggle manual artifact observed flag
START    reset to MIXED target 10
```

## Default Proof Point

The default mode is `MIXED` with target `10`, matching the milestone scenario:
40 wall sprites with 25% card changes, plus 24 thing strips.

```text
wall controls:       40 * 3       =   120 words
changed wall cards:  10 * 64      =   640 words
thing controls:      24 * 3       =    72 words
thing tilemaps:      24 * 24      =   576 words
total:                               1,408 words
```

That is below the current practical vblank budget of 1,664 words. The ROM
reports estimated upload cost as 12 cycles per streamed word plus 16 cycles per
address set, and mirrors `ng_profile_frame_t` at `$10E040`.

## MAME Smoke

MAME 0.288 timed boot/run:

```text
make -C harness/microbenches/vram_upload_scb mame-bench
Average speed: 1028.98% (2 seconds)
```

MAME emitted checksum warnings because the local run uses ngdevkit's generated
open replacement `neogeo.zip`, not a commercial MAME BIOS set. The ROM still
loaded and ran through the timed MAME bench.

## Gate Status

```text
[~] Measured streamed-write rate recorded in cycles/word.
    ROM reports the documented 12-cycle streamed write model plus address-set
    overhead. This is not yet hardware-verified timing.

[~] Max artifact-free streamed words/vblank measured.
    ROM can sweep above and below 1,664 practical / 2,560 theoretical words, but
    the artifact threshold still needs manual visual observation in MAME/GnGeo.

[x] Mode C proves a 40-wall (<=25% card change) + 24-thing scene fits one vblank.
    Default MIXED target writes 1,408 words before fix overlay text.

[~] Behavior of writing outside vblank characterized.
    ACTIVE mode intentionally delays before writing, but visual artifact notes
    have not been recorded yet.

[~] scripts/vram_upload_budget.py matches the 40-wall M0B scenario.
    run_host_tests.sh now exercises 40 walls, 24 things, 25% wall card changes.
    The safe limit still needs tuning from the visual artifact threshold.
```

## Next Calibration Pass

Run the ROM visually, sweep `FULL` and `ACTIVE`, and record the first target
where snow/tearing/corruption appears. Then tune `scripts/vram_upload_budget.py`
from "documented estimate" to "measured safe budget."
