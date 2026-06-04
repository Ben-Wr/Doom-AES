#!/usr/bin/env python3
from dataclasses import dataclass


@dataclass
class Item:
    name: str
    kib: float


items = [
    Item("player/game globals", 4),
    Item("active mobj pool", 10),
    Item("thinker/event state", 4),
    Item("dynamic sector/line state", 4),
    Item("collision/block scratch", 4),
    Item("renderer clip arrays", 4),
    Item("visible command lists", 8),
    Item("sprite-control shadow", 6),
    Item("stack/audio/scratch", 6),
    Item("reserve", 4),
]

total = sum(item.kib for item in items)

print("Runtime RAM ledger target")
for item in items:
    print(f"  {item.name:28s} {item.kib:5.1f} KiB")
print(f"  {'TOTAL':28s} {total:5.1f} KiB")
print("")
if total > 64:
    print("FAIL: above 64 KiB. This ledger must shrink.")
elif total > 56:
    print("WARN: above 56 KiB working target. Keep shrinking.")
else:
    print("OK: under 56 KiB working target.")
