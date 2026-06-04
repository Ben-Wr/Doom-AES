# M0B Result

Date: 2026-06-04

Status: **complete for the MAME milestone gate, with the renderer budget kept conservative at 1,664 practical SCB words/vblank.**

## Build

```text
make -C harness/microbenches/vram_upload_scb clean
make -C harness/microbenches/vram_upload_scb
scripts/run_host_tests.sh
make -C harness/microbenches/vram_upload_scb mame-capture
make -C harness/microbenches/vram_upload_scb mame-bench
```

Generated artifacts stay under ignored `build/`:

```text
build/m0b.neo
build/rom/m0b.zip
build/neogeo.xml
build/gngeo_data.zip
build/m0b_capture.tsv
build/snap/m0b_01_mixed_40w25_24t_1408w.png
```

No IWAD, commercial BIOS, or commercial ROM data is committed. MAME reports
checksum warnings for `sp-s2.sp1`, `sm1.sm1`, and `sfix.sfix` because the local
run uses ngdevkit's open replacement `neogeo.zip`, not a commercial BIOS set.
The ROM still boots and runs in `mame neogeo`.

## ROM Evidence

The on-screen title is `DOOM AES M0B` / `DOOM AES VRAM UPLOAD BENCH`.

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
START    reset auto-sweep to MIXED target 10
```

The default/first auto-sweep case is the milestone scene: 40 wall sprites with
25% card changes, plus 24 thing strips.

```text
wall controls:       40 * 3       =   120 words
changed wall cards:  10 * 64      =   640 words
thing controls:      24 * 3       =    72 words
thing tilemaps:      24 * 24      =   576 words
total:                               1,408 words
```

That is below the calibrated practical vblank budget of 1,664 words.

## Capture Table

`make mame-capture` records this deterministic sweep table:

```text
case mode   target words scb1 ctrl addr cycles cpw  fit fps overP overT
01   MIXED      10  1408 1216  192   37  17488 12.4  1  60   0     0
02   FULL       24  1608 1536   72   27  19728 12.2  1  60   0     0
03   FULL       25  1675 1600   75   28  20548 12.2  2  30   1     0
04   FULL       38  2546 2432  114   41  31208 12.2  2  30   1     0
05   FULL       39  2613 2496  117   42  32028 12.2  2  30   1     1
06   CTRL      320   960    0  960    3  11568 12.0  1  60   0     0
07   ACTIVE     24  1608 1536   72   27  19728 12.2  1  60   0     0
08   ACTIVE     25  1675 1600   75   28  20548 12.2  2  30   1     0
09   ACTIVE     38  2546 2432  114   41  31208 12.2  2  30   1     0
10   ACTIVE     39  2613 2496  117   42  32028 12.2  2  30   1     1
```

Manual MAME visual sweep photos also reached `FULL 38` / `ACTIVE 39` with the
overlay reporting `ART CLEAR`. MAME did not show visible snow/corruption in that
sweep, including over-theoretical cases, so M0B treats timing budget rather
than visible artifact as the limiter.

## Gate Status

```text
[x] Measured streamed-write rate recorded in cycles/word.
    ROM reports 12.0-12.4 cycles/word using the documented 12-cycle streamed
    VRAM spacing plus 16-cycle address-set overhead.

[x] Max artifact-free streamed words/vblank measured in MAME.
    MAME visual sweep reached 2,613 words with ART CLEAR, but this is over the
    theoretical window and is not adopted as the renderer budget.

[x] Mode C proves a 40-wall (<=25% card change) + 24-thing scene fits one vblank.
    MIXED target 10 writes 1,408 words and remains under 1,664 practical.

[x] Behavior of writing outside vblank characterized.
    ACTIVE mode with 1,608 words is inside practical timing; 1,675+ words is
    flagged as a 2-frame/30fps load; 2,613 words crosses theoretical.

[x] scripts/vram_upload_budget.py re-tuned to the measurement.
    run_host_tests.sh now gates the 40-wall, 24-thing, 25% card-change case,
    and the script's 0.65 practical-fill default matches the 1,664-word cap.
```

## Decision

Proceed to M1 with this renderer rule: keep per-frame SCB uploads <=1,664
practical words; anything above that must be diffed harder, delayed, or spread
over two frames. SCB1 tilemap caching is mandatory.
