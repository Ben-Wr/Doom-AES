# M1: one Doom-like room, built directly with ngdevkit.

GAMEROM := m1
LONG_NAME := Doom AES M1 One Room
YEAR := 2026
PUBLISHER := Doom AES

BUILDDIR := build
ASSETDIR := $(BUILDDIR)/assets
ROMDIR := $(BUILDDIR)/rom

PROMSIZE := 524288
SROMSIZE := 131072
MROMSIZE := 131072
VROMSIZE := 524288
CROMSIZE := 1048576
CROM_BIOS_TILE_BYTES := 16384

PKG_CONFIG ?= pkg-config
PYTHON ?= python3
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
ROMTOOL_CMD := PYTHONPATH=$(ROMTOOL_PYTHONPATH) $(PYTHON) $(ROMTOOL_REAL)
GNGEO_DATA_ORIG := $(shell dirname "$$(which $(GNGEO))")/../share/ngdevkit-gngeo/gngeo_data.zip
ASSET_TOOL := ../milestone0_sprite_path/tools/make_assets.py

CFLAGS := -std=c99 -fomit-frame-pointer -O2 -g -I../common
LDFLAGS :=

ELF := $(BUILDDIR)/rom.elf
OBJ := $(BUILDDIR)/main.o
FIX_GIF := $(ASSETDIR)/m1_fix.gif
CARD_GIF := $(ASSETDIR)/m1_card_16x512.gif
SROM_BIN := $(ASSETDIR)/m1_fix.fix
CARD_C1 := $(ASSETDIR)/m1_card.c1
CARD_C2 := $(ASSETDIR)/m1_card.c2

PROM1 := $(ROMDIR)/m1-p1.p1
MROM1 := $(ROMDIR)/m1-m1.m1
VROM1 := $(ROMDIR)/m1-v1.v1
SROM1 := $(ROMDIR)/m1-s1.s1
CROM1 := $(ROMDIR)/m1-c1.c1
CROM2 := $(ROMDIR)/m1-c2.c2
CART := $(ROMDIR)/$(GAMEROM).zip
NEO := $(BUILDDIR)/$(GAMEROM).neo
MAME_HASH := $(BUILDDIR)/neogeo.xml
GNGEO_DATA := $(BUILDDIR)/gngeo_data.zip
BIOS := $(ROMDIR)/neogeo.zip

all: $(NEO) $(MAME_HASH) $(GNGEO_DATA) $(BIOS)

$(BUILDDIR) $(ASSETDIR) $(ROMDIR):
	mkdir -p $@

$(FIX_GIF) $(CARD_GIF): $(ASSET_TOOL) | $(ASSETDIR)
	$(PYTHON) $(ASSET_TOOL) --fix $(FIX_GIF) --card $(CARD_GIF)

$(SROM_BIN): $(FIX_GIF) | $(ASSETDIR)
	$(TILETOOL) --fix -c $< -o $@

$(CARD_C1) $(CARD_C2): $(CARD_GIF) | $(ASSETDIR)
	$(TILETOOL) --sprite -c $< -o $(CARD_C1) $(CARD_C2)

$(OBJ): main.c ../common/ng_profile.h | $(BUILDDIR)
	$(M68KGCC) $(NGCFLAGS) $(CFLAGS) -c $< -o $@

$(ELF): $(OBJ)
	$(M68KGCC) -o $@ $^ $(NGLDFLAGS) $(LDFLAGS)

$(PROM1): $(ELF) | $(ROMDIR)
	$(M68KOBJCOPY) -O binary -S -R .text2 --gap-fill 0xff --pad-to $(PROMSIZE) $< $@
	dd if=$@ of=$@ conv=notrunc,swab status=none

$(SROM1): $(SROM_BIN) | $(ROMDIR)
	cp $< $@
	$(PYTHON) -c 'import sys; open(sys.argv[1], "ab").truncate(int(sys.argv[2]))' $@ $(SROMSIZE)

$(CROM1): $(CARD_C1) | $(ROMDIR)
	(dd if=/dev/zero bs=$(CROM_BIOS_TILE_BYTES) count=1 status=none; cat $<) > $@
	$(PYTHON) -c 'import sys; open(sys.argv[1], "ab").truncate(int(sys.argv[2]))' $@ $(CROMSIZE)

$(CROM2): $(CARD_C2) | $(ROMDIR)
	(dd if=/dev/zero bs=$(CROM_BIOS_TILE_BYTES) count=1 status=none; cat $<) > $@
	$(PYTHON) -c 'import sys; open(sys.argv[1], "ab").truncate(int(sys.argv[2]))' $@ $(CROMSIZE)

$(MROM1): $(NGSHAREDIR)/nullsound_driver.ihx | $(ROMDIR)
	$(Z80SDOBJCOPY) -I ihex -O binary $< $@
	$(PYTHON) -c 'import sys; open(sys.argv[1], "ab").truncate(int(sys.argv[2]))' $@ $(MROMSIZE)

$(VROM1): | $(ROMDIR)
	$(PYTHON) -c 'import sys; open(sys.argv[1], "wb").truncate(int(sys.argv[2]))' $@ $(VROMSIZE)

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
		-seconds_to_run 30 -autoboot_script tools/mame_capture.lua

clean:
	rm -rf $(BUILDDIR)

.PHONY: all gngeo mame mame-bench mame-capture clean
