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

## What it does not tell us

- **Where on the board the mics sit.** The schematic shows two mics at opposite
  ends; the exact X/Y coordinates are still not extracted, so the component
  model's positions remain invented.
- **Whether the port is recessed or flush** with the package top, which decides
  how much clearance a case must leave above it.
- **How much the HAT's own board shadows the ports** at grazing angles.
- **Whether the V1 board uses the same part.** V1 used a WM8960 and a different
  microphone; do not carry this finding across revisions without checking.

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
