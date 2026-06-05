#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
missing_required=0

check_cmd() {
  name="$1"
  required="${2:-required}"
  if command -v "$name" >/dev/null 2>&1; then
    printf "OK      %s -> %s\n" "$name" "$(command -v "$name")"
  else
    if [ "$required" = "required" ]; then
      printf "MISSING %s (required)\n" "$name"
      missing_required=$((missing_required + 1))
    else
      printf "WARN    %s missing (optional)\n" "$name"
    fi
  fi
}

check_path() {
  path="$1"
  required="${2:-required}"
  if [ -e "$path" ]; then
    printf "OK      %s\n" "$path"
  else
    if [ "$required" = "required" ]; then
      printf "MISSING %s (required)\n" "$path"
      missing_required=$((missing_required + 1))
    else
      printf "WARN    %s missing (optional)\n" "$path"
    fi
  fi
}

printf "Workspace: %s\n" "$ROOT"
printf "\nHost tools:\n"
check_cmd git
check_cmd curl
check_cmd make
check_cmd cmake
check_cmd python3
check_cmd node optional
check_cmd rg
check_cmd pandoc optional
check_cmd brew optional

if [ -x "$ROOT/.venv/bin/python" ]; then
  if "$ROOT/.venv/bin/python" -c "import PIL" >/dev/null 2>&1; then
    printf "OK      Pillow -> local venv\n"
  else
    printf "MISSING Pillow in local venv (required)\n"
    missing_required=$((missing_required + 1))
  fi
else
  printf "MISSING local Python venv (%s/.venv) (required)\n" "$ROOT"
  missing_required=$((missing_required + 1))
fi

printf "\nNeo Geo / retro tools:\n"
check_cmd m68k-neogeo-elf-gcc
check_cmd m68k-neogeo-elf-gdb
check_cmd sdcc
check_cmd ngdevkit-gngeo

printf "\nEmulator tools:\n"
check_cmd mame
check_cmd gngeo optional

printf "\nReference directories:\n"
for path in \
  "$ROOT/external/id-doom" \
  "$ROOT/external/chocolate-doom" \
  "$ROOT/external/GBADoom" \
  "$ROOT/external/ngdevkit" \
  "$ROOT/references/neogeodev/md"
do
  check_path "$path" optional
done

printf "\nLegal-data guard directories are ignored if created locally:\n"
printf "  %s/iwads\n" "$ROOT"
printf "  %s/bios\n" "$ROOT"
printf "  %s/roms\n" "$ROOT"

for pattern in iwads/ bios/ roms/ "*.wad" "*.WAD"; do
  if git -C "$ROOT" check-ignore -q "$pattern"; then
    printf "OK      git ignores %s\n" "$pattern"
  else
    printf "MISSING git ignore rule for %s (required)\n" "$pattern"
    missing_required=$((missing_required + 1))
  fi
done

if [ "$missing_required" -ne 0 ]; then
  printf "\nEnvironment check failed: %d required item(s) missing.\n" "$missing_required" >&2
  exit 1
fi

printf "\nEnvironment check passed.\n"
