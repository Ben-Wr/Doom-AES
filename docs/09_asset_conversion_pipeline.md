# Asset Conversion Pipeline

The asset pipeline is a host-side bulk converter. The Neo Geo runtime should consume already-packed, already-budgeted banks.

Concrete recipe (lump formats, ZDBSP, planar tile encoding, end-to-end commands): [13_wad_porting_guide.md](13_wad_porting_guide.md). Output spec: [04_asset_pipeline.md](04_asset_pipeline.md).

## Current Scaffold

The first tool is `tools/wad2ng`.

It can:

```text
inspect a WAD directory
find maps and graphic namespaces
read PLAYPAL
decode Doom patch-format graphics
export sprite/patch PNGs in bulk
optionally pre-upscale graphics to a target max height
optionally split graphics into 16 px vertical strips
emit JSON metadata with strip/tile/byte estimates
```

It does not yet:

```text
compose wall textures from TEXTURE1/PNAMES
quantize to Neo Geo 15-color palettes
write final C-ROM planar tile data
pack P/C/V/M/S ROM banks
```

Those are the next stages.

## Setup

```sh
scripts/setup_python_tools.sh
```

## Bulk Extract

Keep IWADs local and ignored:

```text
iwads/DOOM1.WAD
```

Run:

```sh
scripts/wad2ng_bulk_extract.sh iwads/DOOM1.WAD build/wad2ng/doom1 --upscale-to-height 192
```

Output:

```text
build/wad2ng/doom1/png/                  raw rendered sprites/patches
build/wad2ng/doom1/png_upscaled/         optional pre-upscaled art
build/wad2ng/doom1/strips/               16 px vertical strip PNGs
build/wad2ng/doom1/manifests/            JSON metadata and budgets
```

## Target Final Stages

### 1. IWAD Ingest

```text
read WAD directory
classify maps, sprites, patches, flats, palettes, sounds, music
validate legal/source provenance
```

### 2. Map Compile

```text
run or consume ZDBSP/glBSP output
emit compact vertices/linedefs/sectors/nodes/subsectors
emit per-map texture and thing usage
emit simplification report
```

### 3. Wall Texture Compose

```text
read TEXTURE1/TEXTURE2/PNAMES
compose patch-based wall textures
reduce to material palettes
slice into max-height 16 px wall cards
generate vertical phase variants
```

### 4. Sprite/Weapon Compile

```text
decode patch-format frames
pre-upscale to max visible size
split into 16 px vertical strips
generate distance LODs
quantize to 15 visible colors plus transparency
```

### 5. Neo Geo Encode

```text
convert 16x16 indexed tiles to Neo Geo sprite format
pack C-ROM tile streams
emit P-ROM metadata tables
emit palette banks
```

Prefer ngdevkit's graphics tools for final C/S ROM packing where possible. Add custom encoders only when the SDK cannot express the Doom-specific packing.

### 6. Reports

Every bulk conversion should emit:

```text
asset counts
strip counts
tile counts
C-ROM bytes
palette usage
required source max sizes
shrink-only violations
SCB1 tilemap write estimates
per-map texture/sprite dependency lists
```

## Proper Runtime Files

The intended final build products are:

```text
P-ROM data:
    compact map banks
    sprite animation metadata
    wall-card lookup tables
    palette/light tables

C-ROM data:
    wall cards
    monster/item/projectile strips
    weapon strips
    static screens/HUD sprites

S-ROM data:
    fix-layer font/HUD tiles

V-ROM data:
    ADPCM samples

M1/Z80 data:
    sound driver
```

