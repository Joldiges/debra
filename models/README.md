# Models

Parametric SolidCraft sources for Debra's physical parts, with renders beside
them. Every folder here holds:

```
<name>/
  README.md     what it is, its parameters, what is assumed, what is missing
  <name>.sc     the editable source; the model is rebuilt from this
  assets/       renders of that source, shown in the README
```

**Current direction, 2026-11-15:** reconstruct James's `RPiSpeaker_v17` with
forward speaker/microphones, desktop/wall use and an accessible topper. He asked
for his square speaker and its four screws to be retained, but **the v17 STEP body
contains no four-screw square mount**: its second bay is a 31.10 × 66 × 7 mm pocket
with two M2.5 pilots 36.5 mm apart and a central Ø10 hole, so that mount is either
a separate part that was never exported or a different revision. See
[the extraction](components/rpispeaker-v17/README.md) and
[the correction](../docs/notes/2026-11-15-audio-and-enclosure-corrections.md).
Earlier compact-box “product” and chosen-speaker labels below are historical
concepts, not an accepted final design. Nothing here has been printed or
fit-tested.

A part is only useful if someone can see it and rebuild it. The README states
which numbers are dimension-sourced and which are assumed, and the renders show
what the model actually is — including the parts it does not have yet.

## Components

| Folder | What it is | Status |
| --- | --- | --- |
| [pi5-5-model-b](components/pi5-5-model-b/README.md) | Raspberry Pi 5 Model B envelope: 85 × 56 mm board, asymmetric hole pattern, 2×20 header, USB-C, 2× micro-HDMI, 2× USB-A, Ethernet, microSD | Outline, holes and which edge each port is on are dimension-sourced; **connector sizes, heights and along-edge offsets are typical values, not measured** |
| [pi-zero-family](components/pi-zero-family/README.md) | Pi Zero v1.3, Zero W and Zero 2 W in one design: 65 × 30 mm board, 58 × 23 hole pattern, header, connectors, wireless can per variant | Outline, holes and header sourced; **connector positions, can heights and thickness approximate** |
| [respeaker-2mic-hat](components/respeaker-2mic-hat/README.md) | ReSpeaker 2-Mics Pi HAT v2.0: board, socket underneath, jack, JST speaker, 2 mics, 3 LEDs, button | Board and holes from the HAT form factor; **component X/Y from Seeed's published Eagle board file**, but **every height is an estimate** |
| [dweii-speakers](components/dweii-speakers/README.md) | The three DWEII modules from the archived research notes, as rectangular housings with a grille recess: 44 × 28 × 15 (701715519671), 44 × 28 × 15 (701715519664, inherited from the 671 family) and 100 × 45 × 21 (701715520462) | **Seller claims, not measurements**; all three are modelled, and they are not interchangeable — the 100 × 45 × 21 module fits no case in this repository |
| [speaker-candidates](components/speaker-candidates/README.md) | Ten driver envelopes (Adafruit, Visaton, Dayton) with bolt circles where published | Vendor dimensions only, **not measured**; two drivers have no fastener holes at all. Modelled as cylinders, so **not usable for cutting a pocket** |

## Assemblies

| Folder | What it is | Status |
| --- | --- | --- |
| [zero2w-respeaker-stack](assemblies/zero2w-respeaker-stack/README.md) | Pi Zero 2 W + ReSpeaker HAT stacked on a header, with a 40 mm driver beside them | **Reference assembly, CAD-only**: proves the stack clears itself and is ~21 mm tall; no tray, no case. **This is the flat layout James called ugly; it is kept as the height reference** |
| [zero2w-respeaker-upright](assemblies/zero2w-respeaker-upright/README.md) | The same parts standing up, driver above the boards, on a rounded base — the inverted-T arrangement | **Reference assembly, CAD-only**: 75 × 40 × 78 mm. The driver is unsupported. **The driver is a stand-in, not a chosen part** |
| [debra-compact](assemblies/debra-compact/README.md) | **An earlier CAD concept, not the selected design**: the DWEII 671 case (linked) with the ReSpeaker HAT (linked) plus the Pi Zero 2 W and speaker module inside | **Assembly, CAD-only**: 71.02 × 54.37 × 33.2 mm, 20 bodies. No screws, no wiring, no board retention |
| [zero2w-dweii-compact](assemblies/zero2w-dweii-compact/README.md) | The chosen DWEII 671 module facing forward, Pi and HAT flat behind it, on a concept plate | **Layout study, CAD-only**: 73 × 53 × 32 mm. No walls, no lid, no fastening; the lid is not modelled, so the microphone ports are still uncut |

## Parts

Printable parts, as opposed to the reference envelopes above. A part here is
something you could slice.

| Folder | What it is | Status |
| --- | --- | --- |
| [zero2w-hat-tray](parts/zero2w-hat-tray/README.md) | Base plate, locating lip and four screw standoffs for the Zero 2 W + HAT stack | **Not printed, not fit-tested**; no lid, no speaker chamber |
| [dweii-671-case](parts/dweii-671-case/README.md) | Tub and lid for the whole device: DWEII 671 module at the front, Pi Zero 2 W + ReSpeaker HAT behind, Ø26 grille, two microphone ports over the sourced HAT port positions, 5 mm corner rounds | **Not printed, not fit-tested**: 71.02 × 54.37 × 33.2 mm. The Pi's own ports and the HAT's jack are enclosed by design |
| [dweii-671-carrier](parts/dweii-671-carrier/README.md) | Baffle and rear pocket for the DWEII 701715519671 module: 45.6 × 29.6 × 15 mm pocket, Ø26 mm grille, 4 × M2.5 | **Not printed, not fit-tested**; pocket sized to the larger of two conflicting seller dimensions |
| [dweii-462-case](parts/dweii-462-case/README.md) | Carrier for the 100 × 45 × 21 mm 5 W module: 102 × 47 × 23 mm cavity, 1.8 mm walls, four vents, flat recessed back, 4 × Ø2.2 × 7 mm pilots | **Not printed, not fit-tested**; no keyholes, no lid, and it carries the module without securing it |
| [dweii-462-retainer](parts/dweii-462-retainer/README.md) | Frame that closes the 462 carrier's front: 101 × 46 mm opening, four holes on the carrier's pilots, tabs over assumed housing edges | **Provisional**: the frame alone does not retain the module; tabs, pads and spacers are not modelled or tested |
| [rpispeaker-v17-lid](parts/rpispeaker-v17-lid/README.md) | Front lid concept for the original v17 body: Ø28 driver in an external sleeve protruding 10 mm, 100% open aperture | **Provisional**: the body's two pilots stop 1.21 mm short of the pocket floor, so fastening needs a body modification; no retainer, cable route unresolved |

## Not modelled yet

- Anything that holds the parts in place. The [case](parts/dweii-671-case/README.md)
  traps the speaker module forward but lets it slide 0.4 mm back, gives the Pi no
  standoffs and nothing that locates it sideways, and models no speaker-lead
  route to the HAT's JST socket.
- Feet, cable strain relief, grille mesh or fabric.
- The ReSpeaker Lite, Satellite1 HAT and the other comparison devices.
- Speaker cut-outs and recesses for every candidate; only outer envelopes exist,
  and only the DWEII 671 has a case that is built around it.

## Regenerating renders

SolidCraft's `screenshot` command with `source: "model"`, `grid`, `axes`,
`camera` and `path` writes a PNG straight into a folder. Each README lists the
exact calls it used, so a render is reproducible rather than a one-off
screenshot of somebody's viewport. Committed renders are palette-quantised to
keep them small; re-shoot at 1200–1500 px wide and quantise again if you replace
one.
