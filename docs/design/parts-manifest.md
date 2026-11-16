# Parts in hand for design

**Owned-inventory view, 2026-11-15; unreviewed.** James directly said he has
“Pi 0, Pi 02, Pi 5, and the three speakers”, microSD cards, cables, power
supplies and 3D printers. “Pi 02” means Zero 2 W. Use those parts as the
starting point for design, not a shopping list. James is not buying hardware;
the separately sourced [R01 inventory](../notes/2026-11-15-parts-inventory.md)
and [device comparison](../comparisons/devices.md) serve the reference goal and
do not gate design work.

Quantities below are what the statement establishes, not a complete stocktake.
An envelope is a CAD reference, not proof of ownership, electrical compatibility,
or physical fit. Component README dimensions retain their own source and
uncertainty; none of these models has been physically fit-tested.

## Owned: reported by James

| Part | Quantity | Variant and design reference |
| --- | --- | --- |
| Raspberry Pi Zero (“Pi 0”) | 1 | **Zero W v1.1** (James, 2026-11-15), so it has the 2.4 GHz radio and is ARMv6. Header fit still unknown. [Zero-family envelope](../../models/components/pi-zero-family/README.md): 65 × 30 mm board, 58 × 23 mm hole pattern. |
| Raspberry Pi Zero 2 W (“Pi 02”) | 1 | Header fit unknown; the radio is 2.4 GHz only, and it is ARMv7/AArch64 rather than ARMv6. [Zero-family envelope](../../models/components/pi-zero-family/README.md): 65 × 30 mm board, 58 × 23 mm hole pattern. First card flashed 2026-11-15 with 64-bit Pi OS Lite (Trixie) — see [the card record](../testing/results/2026-11-15-zero2w-card.md). |
| Raspberry Pi 5 | At least 1; exact count unknown | Memory and revision of the owned board not specified by the statement. [Pi 5 Model B envelope](../../models/components/pi5-5-model-b/README.md): 85 × 56 mm board, asymmetric 58 × 49 mm hole pattern. A [lab result](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md) identifies one Pi 5 Model B Rev 1.0, 4 GB specimen. |
| Speakers | 3 | **Identified 2026-11-15:** the three DWEII housed modules already modelled in [dweii-speakers](../../models/components/dweii-speakers/README.md) — the ones linked from that page and selected in the archived research. Which module is which physical unit, and how many of each, is still unstated. They are housed modules, not bare drivers: a case should carry them without sealing their openings. Every dimension there is a seller claim, not a measurement. |
| ReSpeaker 2-Mics Pi HAT v2.0 | 2 | James, 2026-11-15. One is the [lab](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md) specimen on the Pi 5; the other is available for a build. [HAT envelope](../../models/components/respeaker-2mic-hat/README.md): 65.02 × 29.97 mm board; layout based on v1 evidence applied to v2, heights typical rather than measured. |
| ReSpeaker 2-Mics Pi HAT v1.0 | 3 | James, 2026-11-15. Same outline as the v2 per the envelope above; the differences between the two revisions are not established by any source in this repository, so treat a v1 board as an unmeasured variant until its layout is checked. No v1 unit has been used on a device. |
| WM8960 audio board | 1 | James, 2026-11-15, described only as "one WM8960". The exact product, revision and interface are unstated; it is not the same thing as the WM8960 codec that sits on a ReSpeaker HAT. No envelope, no pin or stack reference, and nothing tested. |
| microSD cards | Multiple; exact count unknown | Capacity, type, condition and availability for each design unknown; no component envelope. |
| Cables | Multiple; exact count unknown | Types, connectors, lengths and plug dimensions unknown; no component envelope. |
| Power supplies | Multiple; exact count unknown | Ratings, connectors and allocation unknown; no component envelope. |
| 3D printers | Multiple; exact count unknown | Manufacturing equipment, not an installed device part. Models, build volumes and materials available unknown; no component envelope. |

## Assumptions to confirm, not additional owned parts

The three DWEII modules are the owned speakers (answered 2026-11-15); what is
still unconfirmed is which physical unit is which and how many of each. The
ReSpeaker HATs also moved to the owned table on 2026-11-15, so the rows below are
conditional design references only, **not assertions that the parts are in hand
or available to a new build**. Dimensions below describe the CAD references, not
measurements of James's speakers.

| Part / possible variant | Quantity | CAD reference and limitation | Exact question to confirm |
| --- | --- | --- | --- |
| DWEII 701715519671 | Unknown | [DWEII envelope](../../models/components/dweii-speakers/README.md): 31 × 28.2 × 15.3 mm from the listing's own dimension drawing (31 mm across the mounting tabs); the earlier 44 × 28 × 15 came from a third-party sheet and is superseded ([correction](../notes/2026-11-16-dweii-671-dimensions-confirmed.md)). **This is the v17 speaker** (James, 2026-11-16). | How many modules are in hand, and what does one read across its terminals — 4 Ω or 8 Ω? |
| DWEII 701715519664 | Unknown | [DWEII envelope](../../models/components/dweii-speakers/README.md): 31 × 28.2 × 15.3 mm inherited from the 671 drawing, not published for this variant or measured. | Is 701715519664 one of the three, and how many of that exact model are in hand? |
| DWEII 701715520462 | Unknown | [DWEII envelope](../../models/components/dweii-speakers/README.md): 100 × 45 × 21 mm modelled from seller claims; not measured. | Is 701715520462 one of the three, and how many of that exact model are in hand? |
| Original v17 square speaker | **Identified: DWEII 701715519671** ([B0B4D1BN4F](https://www.amazon.com/dp/B0B4D1BN4F)), James 2026-11-16 | The [v17 mount analysis](rpispeaker-v17-speaker-mount-options.md) still treats the four-screw interface as unresolved: the drawing shows two mounting ears, not four screws, and no hole diameter is published. The square is now the [DWEII envelope](../../models/components/dweii-speakers/README.md) at 31 × 28.2 × 15.3 mm. | What do the four screws in v17 attach to, and what is the ear hole diameter? |

The ten [catalogue speaker envelopes](../../models/components/speaker-candidates/README.md)
are also references, not an inventory: their simplified cylinders are unsuitable
as pocket geometry for a rectangular housed module. They are **not** among the
three speakers James described — those are the DWEII modules above.

## Open questions and consequences

1. **Is “Pi 0” a Zero v1.3 or a Zero W, and is its header fitted?** Answered
   2026-11-15 for the board: it is a **Zero W v1.1**, so it has the radio and is
   ARMv6 — which means it can carry the ARMv6 track and the onboarding flow, but
   not a 64-bit image. Header fit is still unknown and still chooses the
   actual header/stack arrangement; the board identity does not establish
   software support.
2. **Which DWEII module is which unit, and how many of each?** The three are the
   modelled DWEII modules (answered 2026-11-15). What remains open is which
   physical module is which, the count of each, and whether the original v17
   square speaker is one of them. For v17, what do its four screws attach to?
   The answer changes the mounting interface;
   see the [mount analysis](rpispeaker-v17-speaker-mount-options.md).
3. **Which HATs and revisions are available for the intended builds, including
   whether the lab v2 can be used?** Answered 2026-11-15 for quantity: two v2,
   three v1, and one WM8960 board. What remains open is which physical unit goes
   to which build, whether a v1 board's layout matches the envelope's v1-derived
   evidence, and what the WM8960 board actually is. No v1 unit has been on a
   device yet, so its microphone/LED positions are unmeasured.
4. **How many of each Pi are available, which Pi 5 revision/memory, and is the
   Zero 2 W header fitted?** This affects parallel build allocation and exact
   stack geometry. The lab record is evidence for one specimen, not all boards.
5. **Which cards, cables and supplies are available for each build, including
   card capacity, cable/plug dimensions and supply ratings/connectors?** This
   affects card access, plug and cable clearance, and power suitability; ownership
   of generic supplies or cables does not prove a particular pairing is suitable.
6. **Which printers, build volumes and materials are available, and are the
   needed fasteners, spacers and filament already on hand?** These affect part
   segmentation and assembly; printer ownership alone does not establish those
   consumables or hardware. No fastener, spacer or filament is assumed owned.

These questions identify uncertainties, not a prohibition on developing
conditional concepts. Check the actual parts before finalizing fit; printing,
device changes and physical tests need separate authorization.
