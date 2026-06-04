#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"

if [ ! -x "$PY" ]; then
  "$ROOT/scripts/setup_python_tools.sh"
fi

"$PY" "$ROOT/scripts/test_wad2ng_synthetic.py"
"$PY" "$ROOT/scripts/test_wad2ng_map_synthetic.py"
"$ROOT/scripts/ram_budget.py"
"$ROOT/scripts/card_atlas_budget.py" --materials 48 --cards-per-material 8 --phases 4
"$ROOT/scripts/vram_upload_budget.py" --wall-sprites 40 --thing-sprites 24 --wall-card-change-frac 0.25
