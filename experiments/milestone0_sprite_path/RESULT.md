# M0A Result

Date: 2026-06-04

Status: **passed as an emulator smoke milestone; pending manual MAME visual signoff for final hardware-quality judgment.**

## Build

```text
make -C experiments/milestone0_sprite_path clean
make -C experiments/milestone0_sprite_path
scripts/run_host_tests.sh
make -C experiments/milestone0_sprite_path mame-bench
```

Artifacts generated under ignored `build/`:

```text
build/m0a.neo
build/rom/m0a.zip
build/neogeo.xml
build/gngeo_data.zip
build/rom/neogeo.zip
```

No IWAD, commercial BIOS, or commercial ROM data is committed.

## Observed

GnGeo visual smoke test:

```text
one 16x512 card displayed from C-ROM at full size
fix-layer overlay displayed above sprites
overlay reported HEIGHT 512PX, WIDTH 16PX, YSHR $FF, XSHR $F, PAL 1
overlay reported TOP 16 and YFIELD $1E0, matching 496 - top
overlay reported SPR/LINE 1, CTRL 3
```

MAME 0.288 smoke test:

```text
make -C experiments/milestone0_sprite_path mame-bench
Average speed: 826.66% (2 seconds)
```

MAME emitted checksum warnings because the local run uses ngdevkit's generated
open replacement `neogeo.zip`, not a commercial MAME BIOS set. The ROM still
loaded and ran through the timed MAME bench.

## Gate

```text
[x] Card displays at >= 8 distinct heights via Y-shrink.
    ROM exposes 10 steps: $FF, $DF, $BF, $9F, $7F, $5F, $3F, $1F, $07, $00.

[x] Card displays at >= 3 distinct widths via X-shrink.
    ROM exposes 5 widths: $F, $B, $7, $3, $0. This is hardware decimation,
    not arbitrary texture-U coverage.

[x] Card recolors through >= 8 palettes with no art duplication.
    ROM loads 8 sprite palettes in palette RAM. C cycles them by rewriting the
    32 SCB1 attribute words for the 32-tile card.

[x] Requesting height > source height is caught by an assert.
    D deliberately requests 513px against a 512px source and sets GUARD ASSERT.

[x] Peak sprites/line stays under 96.
    Overlay reports SPR/LINE 1 for the single-card proof.

[x] Y position uses the 496 - top convention correctly.
    Example observed: TOP 16 -> YFIELD $1E0.
```

## Caveats

M0A is not a VRAM upload-budget proof. Palette cycling rewrites 32 SCB1
attribute words because Neo Geo stores the palette field per tile row. The next
milestone, M0B, must measure how many SCB words can be streamed safely in MAME.
