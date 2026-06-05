#!/usr/bin/env python3
import argparse


def mib(value: int) -> float:
    return value / (1024 * 1024)


parser = argparse.ArgumentParser(description="Estimate Neo Geo wall-card atlas C-ROM size.")
parser.add_argument("--materials", type=int, default=48)
parser.add_argument("--cards-per-material", type=int, default=8)
parser.add_argument("--phases", type=int, default=4)
parser.add_argument("--bytes-per-card", type=int, default=2048)
parser.add_argument("--extra-percent", type=float, default=10.0, help="metadata/alignment/special-card padding")
args = parser.parse_args()

cards = args.materials * args.cards_per_material * args.phases
raw = cards * args.bytes_per_card
total = int(raw * (1 + args.extra_percent / 100.0))

print("Wall-card atlas estimate")
print(f"  materials:          {args.materials}")
print(f"  cards/material:     {args.cards_per_material}")
print(f"  vertical phases:    {args.phases}")
print(f"  cards total:        {cards:,}")
print(f"  bytes/card:         {args.bytes_per_card:,}")
print(f"  raw C-ROM:          {raw:,} bytes ({mib(raw):.2f} MiB)")
print(f"  with padding:       {total:,} bytes ({mib(total):.2f} MiB)")
