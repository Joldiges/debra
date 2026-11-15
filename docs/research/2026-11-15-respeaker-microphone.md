# The ReSpeaker HAT's microphones are top-port, and that decides the enclosure

**Research result from vendor documentation, not a device measurement, 2026-11-15.**
Answers the question that was blocking every enclosure arrangement: which way the
HAT's microphones face.

## The finding

The ReSpeaker 2-Mics Pi HAT V2.0 uses **two MSM321A3729H9BP analog MEMS
microphones**, and that part is **top-ported**:

> "MSM321A3729H9BP is an omnidirectional, **Top-ported**, analog output MEMS
> microphone … available in a thin 3.76 mm × 2.95 mm × 1.1 mm proprietary OCLGA
> package."
> — MEMSensing datasheet V1.1, 2018-12-29

The acoustic port is **Ø0.325 mm**, on the top of the package, 1.1 mm above the
PCB. The part number is visible in the V2.0 schematic as `MSM321A3729H9BP`
against both `MIC1` and `MIC2`, with pins VDD / GND / GND / OUT.

| Fact | Value | Source |
| --- | --- | --- |
| Microphone part | MSM321A3729H9BP | V2.0 schematic (KiCad, 2024-11-15) |
| Port | **top**, Ø0.325 mm | MEMSensing datasheet |
| Package | 3.76 × 2.95 × 1.1 mm | datasheet |
| Sensitivity | −32 dBV/Pa, ±1 dB | datasheet |
| SNR | 65 dB | datasheet |
| Board overall | **65 × 30 × 15 mm** | Seeed product page and datasheet |
| Microphones | 2, analog, at opposite ends | Seeed product page |

## Why it matters

**Sound enters through the top of the HAT, not through the board and not through
the 11 mm gap to the Pi.** That single fact decides the whole mechanical
arrangement:

1. **The HAT's component side must face open air.** It cannot be the board
   against the case, and it cannot be the board under a driver, a lid, or another
   PCB. Any of those puts a wall 0.325 mm from the port.
2. **The HAT must be the front board of the stack.** The Pi goes behind it. This
   rules out the "HAT behind the Pi, connectors at the bottom" variant that was
   tried first in the upright assembly.
3. **The 11 mm board gap is not an acoustic path**, so it does not need to be
   kept open for sound. It only needs enough room for the header and for cooling.
4. **A grille or fabric over the HAT is a real acoustic element.** The port is
   Ø0.325 mm; anything covering it is directly in the sound path and has to be
   tested, not assumed transparent.

This also explains why the HAT works lying flat on a Pi: the mics point at the
ceiling, which is the normal orientation for a voice assistant on a shelf.

## Where the ports are: the board layout

The schematic does not carry coordinates, but Seeed publish the **V1.0 Eagle board
file** (`ReSpeaker 2-Mics Pi HAT_PCB.zip`, 2017-08-16), and their own
hardware-revision page states:

> "The PCB layout of v1 and v2 remains basically the same, but additional circuits
> are added."
> — Seeed wiki, *How to Distinguish ReSpeaker 2-Mics Pi HAT Hardware Revisions*, 2024-12-11

That makes the V1 file a usable source for the V2 board, with one caveat below.
Parsed from the `.brd` (Eagle XML), in a board frame whose origin is the board's
lower-left corner, X along the 65 mm length and **+Y the 40-pin header edge**:

| Feature | Value | How it was read |
| --- | --- | --- |
| Board | 65.02 × 29.97 mm, ~3 mm corner chamfers | dimension layer, 8 wires |
| Mounting holes | (3.5, 3.5), (61.5, 3.5), (3.5, 26.5), (61.5, 26.5), Ø2.75 | the Pi Zero's 58 × 23 pattern |
| 40-pin header | rows y = 25.23 and 27.77, x 8.37…56.63 | 40 through-hole pads |
| **MIC1 acoustic port** | **(3.05, 21.34)** | element at (2.67, 21.34), `R270`, plus the package's Ø0.762 silk port marker at local (0, 0.381) |
| **MIC2 acoustic port** | **(61.98, 21.34)** | element at (62.36, 21.34), `R90`, same marker mirrored |
| Port spacing | **58.93 mm** | difference of the two |
| 3.5 mm jack mouth | (54.74, −1.52), facing −Y | `R90`, body 14.5 mm extending +Y |
| Micro-USB power | mouth facing −X, 0.89 mm proud of the edge | `R270` |
| Grove ×2 | mouths facing −Y at x = 12.95 and 26.67 | `R180` |
| JST speaker | mouth facing +Y at (38.10, 4.95) | 2.0 mm right-angle |

Two independent checks that the parse is right: the two ports come out
**symmetric about the board centre to within 0.03 mm**, and the header's 40 pads
land exactly 2.54 mm apart across 48.26 mm. A wrong rotation or a wrong origin
would not produce either.

The port offset matters: the port is **not** at the package centre. It is
0.381 mm inboard, from the Ø0.762 mm silk circle the package draws over it. For a
case hole that is a small correction; for a 3.76 mm package it is a tenth of the
part.

### The one caveat

**This is the V1.0 layout.** V1 used a WM8960 codec and V2 uses a
TLV320AIC3104; the revision page says additional circuits were added. The
microphones sit at the extreme corners of an unchanged outline and are the
safest positions on the board. The codec and its passives are the least safe. A
case that cuts holes only for the microphone ports, the micro-USB and the jack is
relying on the corner geometry, which is the part most likely to have survived.

**Cheapest confirmation available:** a ruler on the real board — each port is
3.0 mm from a short edge and 8.66 mm from the header edge, to the centre.

## What it does not tell us

- **Whether the port is recessed or flush** with the package top, which decides
  how much clearance a case must leave above it.
- **How much the HAT's own board shadows the ports** at grazing angles. The
  header socket is 5 mm from each port in Y and the board is 1.6 mm thick, so
  there is a real baffle behind them.
- **Whether the V2 board kept every position.** See the caveat above.

## Cross-check against the models

| Model | Value | Published | Verdict |
| --- | --- | --- | --- |
| `respeaker-2mic-hat` board | 65 × 30 × 1.6 | 65 × 30 × 15 overall | outline agrees; the 15 mm is board **plus socket** |
| `zero2w-respeaker-stack` top of HAT | Z 14.2 mm | 15 mm | within 0.8 mm — the assumed `STACK_GAP` of 11 mm is plausible |
| `respeaker-2mic-hat` mic envelope | 4 × 3 × 1.2 | 3.76 × 2.95 × 1.1 | close enough for a case; the position is the weak part |

## Sources

- MEMSensing, *MSM321A3729H9BP Analog output MEMS microphone*, datasheet V1.1,
  2018-12-29 — https://files.seeedstudio.com/products/107990055/MicSpecification.pdf
- Seeed Studio, *ReSpeaker 2-Mics Pi HAT V2.0* schematic, KiCad, rev 2024-11-15 —
  https://files.seeedstudio.com/wiki/ReSpeaker_2_Mics_Pi_HAT/202004059_ReSpeaker-2-Mics-Pi-HAT-V2.0_SCH_PDF_241121.pdf
- Seeed Studio, *reSpeaker 2-Mics Pi HAT V2.0* product page (SKU 107100001) —
  https://www.seeedstudio.com/ReSpeaker-2-Mics-Pi-HAT.html
- Seeed Studio wiki, *ReSpeaker 2-Mics Pi HAT* —
  https://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT

The schematic text was extracted with `pdftotext`; the part number appears against
`MIC1` and `MIC2` in the audio sheet. No claim here rests on a product photo.
