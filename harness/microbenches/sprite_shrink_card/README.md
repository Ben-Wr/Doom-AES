# Sprite Shrink Card Benchmark

Question:

```text
Does a maximum-size wall-card-like sprite shrink cleanly across the heights/widths the Doom renderer will request?
```

Test:

```text
one 16 px wide max-height card
cycle Y shrink values
cycle X shrink values
move X/Y
swap 8 light palettes
assert no request enlarges source art
```

