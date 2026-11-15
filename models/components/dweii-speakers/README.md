# DWEII speaker modules (the ones from the archived research notes)

**Component envelope only. All three modules are now modelled. Nothing here is
measured — every figure is a seller claim, and the table says which.**

Editable SolidCraft source: [`dweii-speakers.sc`](dweii-speakers.sc).

These are the three speakers James selected in the
[archived research notes](../../../docs/archive/readme-research-before-2026-11-15.md#speakers),
and they are the parts a case should be designed around. They are **housed
modules**, not bare drivers: each has its own plastic housing and its own
acoustic openings. That is the most important fact for enclosure work here,
because a case should **carry** the module rather than **seal** it — a pocket cut
tight around a module with rear vents can silence it. Whether each housing is
actually a sealed chamber is **unconfirmed** (see the caveats below), so treat
"carry, do not seal" as the working assumption, not a verified specification.

## What the envelopes look like

![Isometric view of two rectangular speaker modules, each with a shallow round grille recess on its front face](assets/iso.png)

*Isometric. Left to right: the 701715519671 and 701715519664 envelopes, both
44 × 28 × 15 mm, then the 701715520462 envelope at 100 × 45 × 21 mm. Each is
drawn as the housing a pocket has to accept, with the round recess marking the
cone/grille opening — not as the cone itself.*

![Front view of the two modules: rectangles with a circle recessed in the middle](assets/front.png)

*Front. The rectangles are the housings; the circles are where sound leaves. A
case needs a rectangular pocket for the housing and a round opening in its
baffle at the same place. The 701715520462 is visibly a different class of
part: it is longer than the Pi Zero and half again as deep.*

## What is actually known, per module

| Module | Electrical | Mechanical | Modelled? |
| --- | --- | --- | --- |
| **701715519671**<br/>[B0B4D1BN4F](https://www.amazon.com/dp/B0B4D1BN4F) | 8 Ω, 3 W, JST-PH 2.0, 110 mm lead | The `manuals.plus` spec sheet for this model number gives **44 × 28 × 15**; several seller pages give **31 × 28 × 15**. Mounting tabs exist ("mounting tabs with holes"), size and position unknown | **Yes**, at the larger 44 × 28 × 15 |
| **701715519664**<br/>[B0B4D2Z35P](https://www.amazon.com/dp/B0B4D2Z35P) | 8 Ω, 3 W, JST-PH 2.0, 480 mm lead | **Same 4-pack product family as 671** — the listing text is the same module. The only size field on the listing is "13.11 cm", which is a parcel figure, not a module. **No individual module size is published for this ASIN**, so the family size 44 × 28 × 15 is used | **Yes**, at 44 × 28 × 15 — inherited, not measured |
| **701715520462**<br/>[B0BHST51PQ](https://www.amazon.com/dp/B0BHST51PQ) | 8 Ω, **5 W** rated / 5.5 W max, **JST-PH 2.5**, 4-pack | **100 × 45 × 21** ("100 mm long, 45 mm wide, 21 mm thick"; the description says "approx. 99 × 45 × 21"). ABS, "double cavity", 40 mm internal dual-magnet driver, "entire cavity is tightly sealed" | **Yes**, at the larger 100 × 45 × 21 |

Two independent statement sets on the 701715520462 listing agree on 99–100 × 45
× 21, so that envelope is the best-sourced of the three. The 701715519671 figure
comes from a spec sheet rather than the seller's own bullet list, which is why
the conflicting 31 mm variant is kept visible.

**The "same size as the Pi Zero" note for 701715519664 is not supported by any
listing.** It came from the archived research notes, and it is the reason this
module was modelled at 65 × 30 × 15. No page for that ASIN publishes a module
size; the product is a 4-pack of the same 3 W module sold as 671. The model is
now 44 × 28 × 15 to match the family. If a module in hand measures 65 × 30, the
note was right and this table is wrong — measure it.

**Consequence for the enclosure:** the 701715520462 is 100 × 45 × 21 mm, which
does not fit any case in this repository. The existing layouts are sized around
a 44 × 28 module or a Ø40 driver. Choosing the 5 W module is therefore a new
case, not a pocket change.

## Parameters

| Parameter | Value | Status |
| --- | --- | --- |
| `S671_L`, `S671_W`, `S671_D` | 44 × 28 × 15 mm | **the larger of two conflicting seller sizes**, chosen so a pocket that fits it fits either |
| `S671_GRILLE` | 26 mm | **invented** — no published opening size |
| `S664_L`, `S664_W`, `S664_D` | 44 × 28 × 15 mm | **inherited from the 671 family**; no size is published for this ASIN |
| `S664_GRILLE` | 26 mm | **invented** |
| `S462_L`, `S462_W`, `S462_D` | 100 × 45 × 21 mm | **sourced**: two statement sets on the listing agree on 99–100 × 45 × 21 |
| `S462_GRILLE` | 40 mm | **sourced**: the listing names a 40 mm internal driver. The opening the housing actually presents is still unknown |

## Why this folder exists next to `speaker-candidates`

[speaker-candidates](../speaker-candidates/README.md) holds ten vendor catalogue
drivers modelled as **cylinders**. That is the wrong shape for enclosure work:
almost every small speaker is a rectangular module, and the housing — not the
cone — is what a case has to fit around. James pointed this out on 2026-11-15.

The catalogue envelopes are still useful for comparing cone sizes and depth. They
are not useful for cutting a pocket. Use these.

## Known gaps

- **No module has been measured.** Every dimension is a seller claim. The
  701715520462 is the best-sourced; the 701715519664 is inherited from its
  sibling and could be wrong by the whole difference between 44 mm and 65 mm.
- **The 701715519664 identity is an inference.** The ASIN, UPC and listing text
  match the 671 family, but DWEII reuses listing text across variants, so this
  is strong evidence rather than proof.
- **The acoustic openings are unknown**, so the grille recesses are placeholders.
- **Whether each module already has its own sealed chamber** is unconfirmed for
  all three. If one is an open-frame module, a case pocket must be sealed and
  that changes the part entirely.
- The 110 mm lead and its JST plug are not modelled; the lead has to go
  somewhere, and that usually decides the layout.
- No mounting holes are modelled, because none are documented.

## Regenerate

```
screenshot({ source: "model", grid: false, axes: false, width: 1200, height: 800,
             camera: { target: [62,7,15], yaw: 0.7, pitch: 0.3, distance: 230 },
             path: ".../assets/iso.png" })
screenshot({ source: "model", grid: false, axes: false, width: 1200, height: 800,
             camera: { target: [62,7,15], yaw: 0, pitch: 0.02, distance: 200 },
             path: ".../assets/front.png" })
```
