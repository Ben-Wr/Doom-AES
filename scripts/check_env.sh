#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

check_cmd() {
  name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    printf "OK      %s -> %s\n" "$name" "$(command -v "$name")"
  else
    printf "MISSING %s\n" "$name"
  fi
}

printf "Workspace: %s\n" "$ROOT"
printf "\nHost tools:\n"
check_cmd git
check_cmd curl
check_cmd make
check_cmd cmake
check_cmd python3
check_cmd node
check_cmd rg
check_cmd pandoc
check_cmd brew

if [ -x "$ROOT/.venv/bin/python" ]; then
  if "$ROOT/.venv/bin/python" -c "import PIL" >/dev/null 2>&1; then
    printf "OK      Pillow -> local venv\n"
  else
    printf "MISSING Pillow in local venv\n"
  fi
else
  printf "MISSING local Python venv (%s/.venv)\n" "$ROOT"
fi

printf "\nNeo Geo / retro tools:\n"
check_cmd m68k-neogeo-elf-gcc
check_cmd m68k-neogeo-elf-gdb
check_cmd sdcc
check_cmd ngdevkit-gngeo

printf "\nOptional / alternate emulator tools:\n"
check_cmd mame
check_cmd gngeo

printf "\nReference directories:\n"
for path in \
  "$ROOT/external/id-doom" \
  "$ROOT/external/chocolate-doom" \
  "$ROOT/external/GBADoom" \
  "$ROOT/external/ngdevkit" \
  "$ROOT/references/neogeodev/md"
do
  if [ -e "$path" ]; then
    printf "OK      %s\n" "$path"
  else
    printf "MISSING %s\n" "$path"
  fi
done

printf "\nLegal-data guard directories are ignored if created locally:\n"
printf "  %s/iwads\n" "$ROOT"
printf "  %s/bios\n" "$ROOT"
printf "  %s/roms\n" "$ROOT"
