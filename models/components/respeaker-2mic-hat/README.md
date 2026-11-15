# ReSpeaker 2-Mics Pi HAT v2.0 reference envelope

**Component envelope only. The HAT outline and mounting holes follow the Pi HAT
form factor; every component position and height on it is an estimate. Not
print-ready, not fit-tested.**

Editable SolidCraft source: [`respeaker-2mic-hat.sc`](respeaker-2mic-hat.sc).

This is the HAT that is actually on the lab Pi. Upstream publishes a schematic
and a wiki page, not a mechanical drawing, so the board is dimension-sourced and
everything on it is approximate. That distinction is the whole point of the
file: it is good enough to plan space around, not good enough to cut a hole for
the jack.

## What the envelope looks like

![Isometric view of the ReSpeaker HAT: a 65 by 30 mm board with a long socket block underneath, a jack block protruding from the right edge, two small microphone boxes along the far edge, three LED boxes along the near edge, a speaker connector and a button on the left](assets/iso.png)

*Isometric, seen from above. The block **under** the board is the 2 × 20 female
socket that plugs into the Pi's header — it is the reason the HAT floats about
11 mm above the Pi. The block on the right edge is the 3.5 mm jack; the small
boxes are two MEMS microphones (far edge), three APA102 LEDs (near edge), the
JST speaker connector and the button (left).*

![Top view of the HAT: board outline with four holes, socket hidden underneath, jack on the right, microphones top, LEDs bottom](assets/top.png)

*Top. 65 × 30 mm with the same 58 × 23 mm hole pattern as the Pi, so the same
standoffs can hold both boards. The socket is underneath and does not appear.*

## What matters for a case

| Item | Value here | Reality |
| --- | --- | --- |
| Board | 65 × 30 × 1.6 mm | HAT form factor, matches the Pi |
| Socket below | 50.8 × 5.08 × 8.5 mm | standard 2 × 20 female header |
| Board-to-board gap | ~11 mm with a male header on the Pi | see the stack assembly; the gap is assumed |
| Jack | 12 × 6 × 5 mm body on the +X edge | the opening is Ø6 mm and needs a hole, not a slot |
| Speaker out | 2-pin JST, 7.4 × 4.5 × 5 mm | **connector type unconfirmed**; see the gaps |
| Microphones | 2 × 4 × 3 mm on the +Y edge | **part now identified**: MSM321A3729H9BP, 3.76 × 2.95 × 1.1 mm, **top-port Ø0.325 mm** — sound enters through the component side, not the board. Positions are still invented. See [the research note](../../../docs/research/2026-11-15-respeaker-microphone.md) |
| LEDs | 3 × 5 × 5 mm on the −Y edge | need a diffuser or window, or they are invisible |
| Button | 6 × 6 × 5 mm on the −X edge | needs a cap or a hole; it is not a power switch |

## Parameters

| Parameter | Value | Status |
| --- | --- | --- |
| `PCB_L`, `PCB_W`, `PCB_T` | 65 × 30 × 1.6 mm | outline from the HAT spec, thickness assumed |
| `HOLE_D`, `HOLE_SPAN_X`, `HOLE_SPAN_Y` | 2.75 mm, 58 × 23 mm | matches the Pi |
| `HDR_L`, `HDR_W`, `HDR_H` | 50.8 × 5.08 × 8.5 mm | socket, below the board |
| `JACK_W`, `JACK_D`, `JACK_H` | 12 × 6 × 5 mm | **approximate** |
| `JST_W`, `JST_D`, `JST_H` | 7.4 × 4.5 × 5 mm | **approximate** |
| `MIC_L`, `MIC_W`, `MIC_H` | 4 × 3 × 1.2 mm | **approximate** |
| `LED`, `LED_H` | 5 × 5 × 1.6 mm | 5050 package, height typical |
| `BTN`, `BTN_H` | 6 × 6 × 5 mm | **approximate** |

## Known gaps

- **Positions are invented, heights are typical.** The two microphones, three
  LEDs, button, jack and JST connector are placed to be plausible and to not
  overlap. Before cutting any opening, measure the real board: the jack is the
  one that will be wrong first.
- The audio jack's **opening** is not modelled, only its body.
- Whether the speaker connector is JST-PH 2.0 is a hypothesis. Adafruit's
  enclosed 3 W modules use JST-PH 2 mm, which would fit, but the pinout and
  polarity are undocumented. Check with a meter before plugging a driver in.
- The codec, the amplifier and the GPIO header pins are not modelled.
- Nothing here is measured against the physical HAT.

## Regenerate

```
screenshot({ source: "model", grid: true, axes: false, width: 1400, height: 800,
             camera: { target: [0,0,3], yaw: 0.85, pitch: 0.5, distance: 135 },
             path: ".../assets/iso.png" })
screenshot({ source: "model", grid: true, axes: false, width: 1400, height: 800,
             camera: { target: [0,0,0], yaw: 0, pitch: 1.5, distance: 110 },
             path: ".../assets/top.png" })
```
