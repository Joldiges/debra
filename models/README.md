# Models

Parametric SolidCraft sources for Debra's physical parts, with renders beside
them. Every folder here holds:

```
<name>/
  README.md     what it is, its parameters, what is assumed, what is missing
  <name>.sc     the editable source; the model is rebuilt from this
  assets/       renders of that source, shown in the README
```

A part is only useful if someone can see it and rebuild it. The README states
which numbers are dimension-sourced and which are assumed, and the renders show
what the model actually is — including the parts it does not have yet.

## Current contents

| Folder | What it is | Status |
| --- | --- | --- |
| [components/pi5-5-model-b](components/pi5-5-model-b/README.md) | Raspberry Pi 5 Model B envelope: 85 × 56 mm board, four mounting holes, 2×20 header | Outline and holes dimension-sourced; thickness and header height assumed; **no ports, no components** |

## Planned, not started

The ReSpeaker 2-Mics Pi HAT v2.0 envelope needs a measured board (only a
schematic exists upstream), and the Pi + HAT tray that the enclosure
requirements call for needs the HAT first. Port cut-outs stay provisional until
the board is measured with calipers; see
[enclosure requirements](../docs/design/enclosures.md).

## Regenerating renders

SolidCraft's `screenshot` command with `source: "model"`, `grid`, `axes`,
`camera` and `path` writes a PNG straight into a folder. Each part README lists
the exact calls it used, so a render is reproducible rather than a one-off
screenshot of somebody's viewport.
