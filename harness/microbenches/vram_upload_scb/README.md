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

