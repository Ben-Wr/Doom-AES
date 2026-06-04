#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL="$ROOT/external"
HTML="$ROOT/references/neogeodev/html"
MD="$ROOT/references/neogeodev/md"

mkdir -p "$EXTERNAL" "$HTML" "$MD" "$ROOT/references/doom" "$ROOT/references/ports"

clone_ref() {
  url="$1"
  dest="$2"
  if [ -d "$dest/.git" ]; then
    printf "Updating %s\n" "$dest"
    git -C "$dest" pull --ff-only --depth 1
  else
    printf "Cloning %s\n" "$url"
    git clone --depth 1 "$url" "$dest"
  fi
}

clone_optional() {
  url="$1"
  dest="$2"
  if clone_ref "$url" "$dest"; then
    return 0
  fi
  printf "WARNING: optional clone failed: %s\n" "$url"
}

clone_ref "https://github.com/id-Software/DOOM.git" "$EXTERNAL/id-doom"
clone_ref "https://github.com/chocolate-doom/chocolate-doom.git" "$EXTERNAL/chocolate-doom"
clone_ref "https://github.com/doomhack/GBADoom.git" "$EXTERNAL/GBADoom"
clone_ref "https://github.com/dciabrin/ngdevkit.git" "$EXTERNAL/ngdevkit"
clone_optional "https://github.com/dciabrin/ngdevkit-examples.git" "$EXTERNAL/ngdevkit-examples"
clone_optional "https://github.com/freem/freemlib-neogeo.git" "$EXTERNAL/freemlib-neogeo"

pages=(
  "General_specifications"
  "Sprites"
  "Sprite_shrinking"
  "Rendering_logic"
  "VRAM"
  "Fix_layer"
  "Palettes"
  "Sprite_graphics_format"
  "Bankswitching"
  "68k_memory_map"
  "Memory_mapped_registers"
  "Display_timing"
  "L0_ROM"
  "68k"
  "C_ROM"
  "P_ROM"
  "Z80"
  "Sound_driver"
  "YM2610"
  "YM2610_registers"
  "ADPCM_codecs"
  "Development_tools"
  "Hello_world_tutorial"
  "Moving_sprites"
)

for page in "${pages[@]}"; do
  url="https://wiki.neogeodev.org/index.php?title=${page}&printable=yes"
  html="$HTML/${page}.html"
  md="$MD/${page}.md"
  tmp="$md.tmp"
  printf "Fetching NeoGeoDev page %s\n" "$page"
  if ! curl -L --fail --silent --show-error "$url" -o "$html"; then
    printf "WARNING: failed to fetch %s\n" "$url"
    continue
  fi
  if command -v pandoc >/dev/null 2>&1; then
    pandoc -f html -t gfm "$html" -o "$tmp"
    {
      printf "# %s\n\n" "$page"
      printf "Source: %s\n\n" "$url"
      cat "$tmp"
    } > "$md"
    rm -f "$tmp"
  fi
done

printf "References fetched.\n"
