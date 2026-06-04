#!/usr/bin/env bash
set -euo pipefail

if ! command -v brew >/dev/null 2>&1; then
  printf "Homebrew is required for this helper.\n" >&2
  exit 1
fi

brew tap dciabrin/ngdevkit
brew install \
  ngdevkit \
  pkg-config \
  autoconf \
  automake \
  zip \
  imagemagick \
  sox

printf "\nOptional emulator installs, larger and slower:\n"
printf "  brew install ngdevkit-gngeo mame\n"
printf "\nAfter install, run:\n"
printf "  scripts/check_env.sh\n"
