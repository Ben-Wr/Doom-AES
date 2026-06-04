#!/usr/bin/env bash
set -euo pipefail

if ! command -v brew >/dev/null 2>&1; then
  printf "Homebrew is required for this helper.\n" >&2
  exit 1
fi

brew install m68k-elf-binutils m68k-elf-gcc sdcc

printf "\nOptional emulator install, large and slower:\n"
printf "  brew install mame\n"
printf "\nFor ngdevkit, see external/ngdevkit after running scripts/fetch_references.sh.\n"

