# VRAM Upload SCB Benchmark

Question:

```text
How many SCB1 tilemap words and SCB2/3/4 control words can be safely rewritten per update window?
```

Benchmark modes:

```text
position-only:       update SCB2/3/4 only
tilemap-small:       update 4-tile sprite SCB1 + controls
tilemap-full-wall:   update 32-tile sprite SCB1 + controls
mixed-doom:          20 wall chunks + 24 thing strips estimate
active-display:      intentionally write outside vblank to characterize artifacts
```

Outputs:

```text
words written
frames per update
visible glitch flag/manual observation
fix-layer counter
profile ring-buffer entry
```

Build:

```sh
make -C harness/microbenches/vram_upload_scb
```

Outputs:

```text
build/m0b.neo
build/rom/m0b.zip
build/neogeo.xml
build/gngeo_data.zip
```

Controls:

```text
A        cycle benchmark mode
B / C    increase / decrease the mode target
D        toggle manual artifact observed flag
START    reset to mixed Doom-like mode
```

Modes:

```text
FULL      rewrite N full 32-tile SCB1 wall cards, plus controls
CTRL      rewrite only SCB2/3/4 controls for N sprites
MIXED     40 wall controls + N changed wall cards + 24 thing tilemaps
ACTIVE    delay past vblank, then write N full cards + controls
```

The default `MIXED` target is 10 changed wall cards, i.e. 25% of 40 walls.
That writes 1,408 SCB words before fix overlay text and is the first Doom-like
cached-scene proof point.
