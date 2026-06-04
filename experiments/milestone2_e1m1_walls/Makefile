# M2: E1M1 walls-only ROM, generated from a local ignored IWAD.

ROOT := ../..
GAMEROM := m2
LONG_NAME := Doom AES M2 E1M1 Walls
YEAR := 2026
PUBLISHER := Doom AES

WAD ?= $(ROOT)/iwads/DOOM1.WAD
MAP ?= E1M1
MAP_LOWER := e1m1

BUILDDIR := build
GENERATED := $(BUILDDIR)/generated
ASSETDIR := $(BUILDDIR)/assets
ROMDIR := $(BUILDDIR)/rom

PROMSIZE := 524288
SROMSIZE := 131072
MROMSIZE := 131072
VROMSIZE := 524288
CROMSIZE := 1048576
CROM_BIOS_TILE_BYTES := 16384

PKG_CONFIG ?= pkg-config
PYTHON ?= $(ROOT)/.venv/bin/python
HOST_PYTHON ?= python3
M68KGCC ?= m68k-neogeo-elf-gcc
M68KOBJCOPY ?= m68k-neogeo-elf-objcopy
Z80SDOBJCOPY ?= z80-neogeo-ihx-sdobjcopy
TILETOOL ?= tiletool.py
GNGEO ?= ngdevkit-gngeo
MAME ?= mame

NGCFLAGS := $(shell $(PKG_CONFIG) --cflags ngdevkit)
NGLDFLAGS := $(shell $(PKG_CONFIG) --libs ngdevkit)
NGPREFIX := $(shell $(PKG_CONFIG) --variable=prefix ngdevkit)
NGSHAREDIR := $(shell $(PKG_CONFIG) --variable=sharedir ngdevkit)
ROMTOOL_REAL := $(NGPREFIX)/libexec/bin/romtool.py
ROMTOOL_PYTHONPATH := $(shell find "$(NGPREFIX)/libexec/lib" -maxdepth 2 -type d -name site-packages | head -n 1)
ROMTOOL_CMD := PYTHONPATH=$(ROMTOOL_PYTHONPATH) $(HOST_PYTHON) $(ROMTOOL_REAL)
GNGEO_DATA_ORIG := $(shell dirname "$$(which $(GNGEO))")/../share/ngdevkit-gngeo/gngeo_data.zip
ASSET_TOOL := ../milestone0_sprite_path/tools/make_assets.py

CFLAGS := -std=c99 -fomit-frame-pointer -O2 -g -I../common -I$(GENERATED)
LDFLAGS :=

MAP_HEADER := $(GENERATED)/$(MAP_LOWER)_map_data.h
MAP_REPORT := $(GENERATED)/$(MAP_LOWER)_map_report.json
MAP_BANK := $(GENERATED)/$(MAP_LOWER)_map_bank.bin
MAP_PREVIEW := $(GENERATED)/$(MAP_LOWER)_map_preview.svg
WALL_ATLAS_GIF := $(GENERATED)/$(MAP_LOWER)_wall_cards.gif
WALL_ATLAS_REPORT := $(GENERATED)/$(MAP_LOWER)_wall_atlas_report.json
WALL_ATLAS_HEADER := $(GENERATED)/$(MAP_LOWER)_wall_cards.h

ELF := $(BUILDDIR)/rom.elf
OBJ := $(BUILDDIR)/main.o
FIX_GIF := $(ASSETDIR)/m2_fix.gif
CARD_GIF := $(WALL_ATLAS_GIF)
SROM_BIN := $(ASSETDIR)/m2_fix.fix
CARD_C1 := $(ASSETDIR)/m2_card.c1
CARD_C2 := $(ASSETDIR)/m2_card.c2

PROM1 := $(ROMDIR)/m2-p1.p1
MROM1 := $(ROMDIR)/m2-m1.m1
VROM1 := $(ROMDIR)/m2-v1.v1
SROM1 := $(ROMDIR)/m2-s1.s1
CROM1 := $(ROMDIR)/m2-c1.c1
CROM2 := $(ROMDIR)/m2-c2.c2
CART := $(ROMDIR)/$(GAMEROM).zip
NEO := $(BUILDDIR)/$(GAMEROM).neo
MAME_HASH := $(BUILDDIR)/neogeo.xml
GNGEO_DATA := $(BUILDDIR)/gngeo_data.zip
BIOS := $(ROMDIR)/neogeo.zip

all: $(NEO) $(MAME_HASH) $(GNGEO_DATA) $(BIOS)

$(BUILDDIR) $(GENERATED) $(ASSETDIR) $(ROMDIR):
	mkdir -p $@

$(MAP_HEADER) $(MAP_REPORT) $(MAP_BANK) $(MAP_PREVIEW): $(WAD) $(ROOT)/tools/wad2ng/cli.py $(ROOT)/tools/wad2ng/doom_map.py | $(GENERATED)
	test -f "$(WAD)"
	PYTHONPATH=$(ROOT) $(PYTHON) -m tools.wad2ng.cli compile-map "$(WAD)" \
		--map $(MAP) --out $(GENERATED) --emit-header --emit-svg

compile-map: $(MAP_HEADER) $(MAP_REPORT) $(MAP_BANK) $(MAP_PREVIEW)

$(WALL_ATLAS_GIF) $(WALL_ATLAS_REPORT) $(WALL_ATLAS_HEADER): $(WAD) $(MAP_REPORT) $(ROOT)/tools/wad2ng/cli.py $(ROOT)/tools/wad2ng/doom_texture.py | $(GENERATED)
	PYTHONPATH=$(ROOT) $(PYTHON) -m tools.wad2ng.cli compile-wall-atlas "$(WAD)" \
		--map $(MAP) --out $(GENERATED)

compile-wall-atlas: $(WALL_ATLAS_GIF) $(WALL_ATLAS_REPORT) $(WALL_ATLAS_HEADER)

$(FIX_GIF): $(ASSET_TOOL) | $(ASSETDIR)
	$(PYTHON) $(ASSET_TOOL) --fix $(FIX_GIF) --card $(ASSETDIR)/unused_card.gif

$(SROM_BIN): $(FIX_GIF) | $(ASSETDIR)
	$(TILETOOL) --fix -c $< -o $@

$(CARD_C1) $(CARD_C2): $(CARD_GIF) | $(ASSETDIR)
	$(TILETOOL) --sprite -c $< -o $(CARD_C1) $(CARD_C2)

$(OBJ): main.c ../common/ng_profile.h $(MAP_HEADER) $(WALL_ATLAS_HEADER) | $(BUILDDIR)
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@

$(ELF): $(OBJ)
	$(M68KGCC) -o $@ $^ $(NGLDFLAGS) $(LDFLAGS)

$(PROM1): $(ELF) | $(ROMDIR)
	$(M68KOBJCOPY) -O binary -S -R .text2 --gap-fill 0xff --pad-to $(PROMSIZE) $< $@
	dd if=$@ of=$@ conv=notrunc,swab status=none

$(SROM1): $(SROM_BIN) | $(ROMDIR)
	cp $< $@
	$(HOST_PYTHON) -c 'import sys; open(sys.argv[1], "ab").truncate(int(sys.argv[2]))' $@ $(SROMSIZE)

$(CROM1): $(CARD_C1) | $(ROMDIR)
	(dd if=/dev/zero bs=$(CROM_BIOS_TILE_BYTES) count=1 status=none; cat $<) > $@
	$(HOST_PYTHON) -c 'import sys; open(sys.argv[1], "ab").truncate(int(sys.argv[2]))' $@ $(CROMSIZE)

$(CROM2): $(CARD_C2) | $(ROMDIR)
	(dd if=/dev/zero bs=$(CROM_BIOS_TILE_BYTES) count=1 status=none; cat $<) > $@
	$(HOST_PYTHON) -c 'import sys; open(sys.argv[1], "ab").truncate(int(sys.argv[2]))' $@ $(CROMSIZE)

$(MROM1): $(NGSHAREDIR)/nullsound_driver.ihx | $(ROMDIR)
	$(Z80SDOBJCOPY) -I ihex -O binary $< $@
	$(HOST_PYTHON) -c 'import sys; open(sys.argv[1], "ab").truncate(int(sys.argv[2]))' $@ $(MROMSIZE)

$(VROM1): | $(ROMDIR)
	$(HOST_PYTHON) -c 'import sys; open(sys.argv[1], "wb").truncate(int(sys.argv[2]))' $@ $(VROMSIZE)

$(BIOS): $(NGSHAREDIR)/neogeo.zip | $(ROMDIR)
	cp $< $@

$(CART): $(PROM1) $(MROM1) $(VROM1) $(SROM1) $(CROM1) $(CROM2) | $(ROMDIR)
	$(ROMTOOL_CMD) --build cartridge --format mame \
		-p $(PROM1) -m $(MROM1) -v $(VROM1) -s $(SROM1) -c $(CROM1) $(CROM2) \
		-n $(GAMEROM) -l "$(LONG_NAME)" -y $(YEAR) --publisher "$(PUBLISHER)" -o $@

$(NEO): $(CART) | $(BUILDDIR)
	cp $< $@

$(MAME_HASH): $(PROM1) $(MROM1) $(VROM1) $(SROM1) $(CROM1) $(CROM2) | $(BUILDDIR)
	$(ROMTOOL_CMD) --build hash --format mame \
		-p $(PROM1) -m $(MROM1) -v $(VROM1) -s $(SROM1) -c $(CROM1) $(CROM2) \
		-n $(GAMEROM) -l "$(LONG_NAME)" -y $(YEAR) --publisher "$(PUBLISHER)" -o $@

$(GNGEO_DATA): $(PROM1) $(MROM1) $(VROM1) $(SROM1) $(CROM1) $(CROM2) | $(BUILDDIR)
	$(ROMTOOL_CMD) --build hash --format gngeo \
		-p $(PROM1) -m $(MROM1) -v $(VROM1) -s $(SROM1) -c $(CROM1) $(CROM2) \
		-n $(GAMEROM) -l "$(LONG_NAME)" -y $(YEAR) --publisher "$(PUBLISHER)" \
		-x gngeo.data="$(GNGEO_DATA_ORIG)" -o $@

gngeo: $(CART) $(GNGEO_DATA) $(BIOS)
	$(GNGEO) -d $(GNGEO_DATA) -i $(ROMDIR) $(GAMEROM)

mame: $(CART) $(MAME_HASH) $(BIOS)
	$(MAME) -cfg_directory $(BUILDDIR)/cfg -nvram_directory $(BUILDDIR)/nvram \
		-snapshot_directory $(BUILDDIR)/snap -hashpath $(BUILDDIR) \
		-rompath $(ROMDIR) neogeo $(GAMEROM)

mame-bench: $(CART) $(MAME_HASH) $(BIOS)
	$(MAME) -cfg_directory $(BUILDDIR)/cfg -nvram_directory $(BUILDDIR)/nvram \
		-snapshot_directory $(BUILDDIR)/snap -hashpath $(BUILDDIR) \
		-rompath $(ROMDIR) neogeo $(GAMEROM) -bench 3 -skip_gameinfo

mame-capture: $(CART) $(MAME_HASH) $(BIOS)
	rm -rf $(BUILDDIR)/snap
	mkdir -p $(BUILDDIR)/snap
	$(MAME) -cfg_directory $(BUILDDIR)/cfg -nvram_directory $(BUILDDIR)/nvram \
		-snapshot_directory $(BUILDDIR)/snap -hashpath $(BUILDDIR) \
		-rompath $(ROMDIR) neogeo $(GAMEROM) -skip_gameinfo -nothrottle \
		-seconds_to_run 60 -autoboot_script tools/mame_capture.lua

clean:
	rm -rf $(BUILDDIR)

.PHONY: all compile-map compile-wall-atlas gngeo mame mame-bench mame-capture clean
