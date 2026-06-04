# M1 Result

Date: 2026-06-04

Status: **M1 gate captured in MAME. Ready to proceed to M2.**

## Implemented

```text
m1.neo ngdevkit ROM
compiled-in two-sector room
compiled-in Doom-style vertices/linedefs/sectors/segs/subsectors
fixed-point movement/turn/strafe
linedef collision, including a blocking door until it opens
middle/upper/lower wall sprite roles
dynamic door ceiling changing upper-wall Y extent
viewport-sized sprite windows to avoid 512px Y-wrap over the overlay
stable preloaded placeholder wall card for every runtime sprite slot
SCB1 cache shadow: unchanged card ids skip tilemap rewrites; per-frame path updates SCB2/3/4
fix-layer profile overlay with sprites/line, SCB words, RAM, fps budget
deterministic auto-demo covering turn, move, strafe, door open, step/portal, door close
```

The room is hand-authored static data in `main.c`; no WAD parsing runs in the
ROM. Placeholder 16x512 wall cards are used for all wall roles.

## Controls

```text
Auto-demo          runs on boot and records max gate metrics
DPAD up/down      move forward/back, disables auto-demo
DPAD left/right   rotate, disables auto-demo
A / B             strafe, disables auto-demo
C                 toggle door open/closed, disables auto-demo
D or START        reset and restart auto-demo
```

## MAME Gate Capture

Command:

```text
make -C experiments/milestone1_one_room mame-capture
```

Native screenshot:

```text
build/snap/neogeo/0000.png
```

Observed overlay after the deterministic route:

```text
current sprites emitted:       16
current peak sprites/line:     16
current SCB words/vblank:      48
current SCB1 words:             0
current control words:         48
max sprites emitted:           57
max peak sprites/line:         44
max SCB words/vblank:         171
min FPS budget:                60, MIN12 OK
RAM high-water:              5376 bytes
degrade flags:              $0000
current role counts:       MID 16, UP 0, LOW 0
max upper/lower roles:        UP 2, LOW 20
```

MAME still reports the expected ngdevkit open-BIOS checksum warnings if the
local rompath contains the generated replacement `neogeo.zip`. A private local
commercial BIOS may suppress that warning, but must stay untracked.

## Gate Notes

The auto-demo is intentionally deterministic: it rotates, walks, opens the door,
continues through the raised portal/step region, closes the door, strafes, and
keeps maximum gate counters on the overlay. The placeholder wall art is one
preloaded sprite card for M1; art/card churn becomes a later texture milestone,
not this first renderer proof.

```text
[x] 12 fps floor sustained while moving and turning.
[x] Peak sprites/line <= 84.
[x] SCB words/vblank <= 1,664.
[x] RAM high-water <= 56 KiB.
[x] Door open/close shows correct upper/lower wall roles and Y-extents.
[x] No runtime WAD parsing.
```
