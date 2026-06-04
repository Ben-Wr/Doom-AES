#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  printf "usage: %s path/to/DOOM1.WAD build/wad2ng/doom1 [extra wad2ng args]\n" "$0" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WAD="$1"
OUT="$2"
shift 2

PY="$ROOT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  PY="python3"
fi

"$PY" -m tools.wad2ng.cli inspect "$WAD"
"$PY" -m tools.wad2ng.cli extract-graphics "$WAD" --out "$OUT" --namespace all --split-strips "$@"

