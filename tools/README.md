# Tools

This directory is for project-specific tools that are too substantial for `scripts/`.

Expected future tools:

```text
wad2ng/             IWAD-to-Neo-Geo compiler
cardgen/            wall-card atlas generator
sprgen/             thing/weapon strip generator
rompack/            C/P/V/M/S ROM bank packer
budgetviz/          scanline and chunk-pressure visualizer
```

Keep host tools separate from Neo Geo runtime code.

Current `wad2ng` entry points:

```sh
python3 -m tools.wad2ng.cli inspect iwads/DOOM1.WAD
python3 -m tools.wad2ng.cli extract-graphics iwads/DOOM1.WAD --out build/wad2ng/doom1 --namespace all
python3 -m tools.wad2ng.cli compile-map iwads/DOOM1.WAD --map E1M1 --out build/wad2ng/e1m1 --emit-header --emit-svg
```
