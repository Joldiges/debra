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

## Components

| Folder | What it is | Status |
| --- | --- | --- |
| [pi5-5-model-b](components/pi5-5-model-b/README.md) | Raspberry Pi 5 Model B envelope: 85 × 56 mm board, asymmetric hole pattern, 2×20 header, USB-C, 2× micro-HDMI, 2× USB-A, Ethernet, microSD | Outline, holes and which edge each port is on are dimension-sourced; **connector sizes, heights and along-edge offsets are typical values, not measured** |
| [pi-zero-family](components/pi-zero-family/README.md) | Pi Zero v1.3, Zero W and Zero 2 W in one design: 65 × 30 mm board, 58 × 23 hole pattern, header, connectors, wireless can per variant | Outline, holes and header sourced; **connector positions, can heights and thickness approximate** |
| [respeaker-2mic-hat](components/respeaker-2mic-hat/README.md) | ReSpeaker 2-Mics Pi HAT v2.0: board, socket underneath, jack, JST speaker, 2 mics, 3 LEDs, button | Board and holes from the HAT form factor; **every component position and height is an estimate** |
| [dweii-speakers](components/dweii-speakers/README.md) | The three DWEII modules from the main README, as rectangular housings with a grille recess: 44 × 28 × 15 and 65 × 30 × 15 | **Seller claims, not measurements**; the third module is not modelled because no dimensions exist |
| [speaker-candidates](components/speaker-candidates/README.md) | Ten driver envelopes (Adafruit, Visaton, Dayton) with bolt circles where published | Vendor dimensions only, **not measured**; two drivers have no fastener holes at all. Modelled as cylinders, so **not usable for cutting a pocket** |

## Assemblies

| Folder | What it is | Status |
| --- | --- | --- |
| [zero2w-respeaker-stack](assemblies/zero2w-respeaker-stack/README.md) | Pi Zero 2 W + ReSpeaker HAT stacked on a header, with a 40 mm driver beside them | **Reference assembly, CAD-only**: proves the stack clears itself and is ~21 mm tall; no tray, no case. **This is the flat layout James called ugly; it is kept as the height reference** |
| [zero2w-respeaker-upright](assemblies/zero2w-respeaker-upright/README.md) | The same parts standing up, driver above the boards, on a rounded base — the inverted-T arrangement | **Reference assembly, CAD-only**: 75 × 40 × 78 mm. The driver is unsupported and the microphones' direction is assumed |

## Parts

Printable parts, as opposed to the reference envelopes above. A part here is
something you could slice.

| Folder | What it is | Status |
| --- | --- | --- |
| [zero2w-hat-tray](parts/zero2w-hat-tray/README.md) | Base plate, locating lip and four screw standoffs for the Zero 2 W + HAT stack | **Not printed, not fit-tested**; no lid, no speaker chamber |
| [dweii-671-carrier](parts/dweii-671-carrier/README.md) | Baffle and rear pocket for the DWEII 701715519671 module: 45.6 × 29.6 × 15 mm pocket, Ø26 mm grille, 4 × M2.5 | **Not printed, not fit-tested**; pocket sized to the larger of two conflicting seller dimensions |

## Not modelled yet

- A lid or a case around the tray, and a speaker chamber with a grille. The tray
  is the base; the acoustic half does not exist.
- The ReSpeaker Lite, Satellite1 HAT and the other comparison devices.
- Speaker cut-outs and recesses; only outer envelopes exist.
- Cable routing, gaskets and grille retention.

## Regenerating renders

SolidCraft's `screenshot` command with `source: "model"`, `grid`, `axes`,
`camera` and `path` writes a PNG straight into a folder. Each README lists the
exact calls it used, so a render is reproducible rather than a one-off
screenshot of somebody's viewport. Committed renders are palette-quantised to
keep them small; re-shoot at 1200–1500 px wide and quantise again if you replace
one.
