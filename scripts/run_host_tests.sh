#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
M2_DIR="$ROOT/experiments/milestone2_e1m1_walls"
M2_WAD="${M2_WAD:-$ROOT/iwads/DOOM1.WAD}"

if [ ! -x "$PY" ]; then
  "$ROOT/scripts/setup_python_tools.sh"
fi

"$ROOT/scripts/check_env.sh"

staged_legal=$(
  git -C "$ROOT" diff --cached --name-only |
    grep -E '(^iwads/|^bios/|^roms/|(^|/)[^/]*\.(wad|WAD|rom|ROM|neo|NEO|p1|P1|m1|M1|v1|V1|s1|S1|c1|C1|c2|C2|chd|CHD)$|(^|/)neogeo\.zip$)' || true
)
if [ -n "$staged_legal" ]; then
  printf "Refusing to run: proprietary or generated ROM data is staged:\n%s\n" "$staged_legal" >&2
  exit 1
fi

"$PY" "$ROOT/scripts/test_wad2ng_synthetic.py"
"$PY" "$ROOT/scripts/test_wad2ng_map_synthetic.py"
"$ROOT/scripts/ram_budget.py"
"$ROOT/scripts/card_atlas_budget.py" --materials 48 --cards-per-material 8 --phases 4
"$ROOT/scripts/vram_upload_budget.py" --wall-sprites 53 --thing-sprites 0 --wall-height-tiles 16 --wall-card-change-frac 0.73
"$ROOT/scripts/vram_upload_budget.py" --wall-sprites 53 --thing-sprites 24 --wall-height-tiles 16 --wall-card-change-frac 0.25

if [ ! -f "$M2_WAD" ]; then
  printf "M2 WAD is required for the full host gate: %s\n" "$M2_WAD" >&2
  exit 1
fi

make -C "$M2_DIR" clean all WAD="$M2_WAD"
make -C "$M2_DIR" clean all WAD="$M2_WAD" CFLAGS_EXTRA="-Werror"
make -C "$M2_DIR" mame-capture WAD="$M2_WAD" CFLAGS_EXTRA="-Werror"
