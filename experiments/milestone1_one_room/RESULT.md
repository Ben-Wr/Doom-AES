# M1 Result

Date: 2026-06-04

Status: **first M1 ROM pass booting in MAME; full movement/door gate sweep still pending.**

## Implemented

```text
m1.neo ngdevkit ROM
compiled-in two-sector room
fixed-point movement/turn/strafe
linedef collision, including a blocking door until it opens
middle/upper/lower wall sprite roles
dynamic door ceiling changing upper-wall Y extent
viewport-sized sprite windows to avoid 512px Y-wrap over the overlay
SCB1 cache shadow: unchanged card ids skip tilemap rewrites
fix-layer profile overlay with sprites/line, SCB words, RAM, fps budget
```

The room is hand-authored static data in `main.c`; no WAD parsing runs in the
ROM. Placeholder 16x512 wall cards are used for all wall roles.

## Controls

```text
DPAD up/down      move forward/back
DPAD left/right   rotate
A / B             strafe
C                 toggle door open/closed
D or START        reset
```

## MAME Smoke

Command:

```text
make -C experiments/milestone1_one_room mame-capture
```

Native screenshot:

```text
build/snap/m1_smoke.png
```

Observed overlay in the smoke pose:

```text
sprites emitted:       24
peak sprites/line:     18
SCB words/vblank:     160
RAM high-water:      5376 bytes
FPS budget:            60, MIN12 OK
degrade flags:      $0000
```

MAME still reports the expected ngdevkit open-BIOS checksum warnings if the
local rompath contains the generated replacement `neogeo.zip`. A private local
commercial BIOS may suppress that warning, but must stay untracked.

## Gate Notes

The first pass boots and exercises the real hardware sprite path. The next M1
calibration pass should record overlay numbers while moving through the room and
toggling the door, then update this file with the hard gate status:

```text
[~] 12 fps floor sustained while moving and turning.
[~] Peak sprites/line <= 84.
[~] SCB words/vblank <= 1,664.
[x] RAM high-water <= 56 KiB in smoke pose.
[~] Door open/close shows correct upper/lower wall roles and Y-extents.
[x] No runtime WAD parsing.
```
