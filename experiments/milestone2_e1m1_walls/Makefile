# M2: compile E1M1 map data from a local, ignored user-supplied IWAD.

ROOT := ../..
PYTHON ?= $(ROOT)/.venv/bin/python
WAD ?= $(ROOT)/iwads/DOOM1.WAD
MAP ?= E1M1
BUILDDIR := build
GENERATED := $(BUILDDIR)/generated

all: compile-map

compile-map:
	test -f "$(WAD)"
	PYTHONPATH=$(ROOT) $(PYTHON) -m tools.wad2ng.cli compile-map "$(WAD)" \
		--map $(MAP) --out $(GENERATED) --emit-header --emit-svg

clean:
	rm -rf $(BUILDDIR)

.PHONY: all compile-map clean
