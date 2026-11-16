---
title: A 40 mm driver cannot go in the v17 body's bay, so the lid carries the frame
date: 2026-11-16
type: project-learning
status: unreviewed
task: enclosure
author: OpenCode coordinator
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - "docs/notes/2026-11-15-rpispeaker-v17-bay-inventory.md (speaker-side footprint 31.10 x 28.125)"
  - "models/components/speaker-candidates/README.md (Adafruit 3968: Ø40 x 21, no fastener holes)"
  - "models/parts/rpispeaker-v17-lid/rpispeaker-v17-lid.sc (existing 28 mm sleeve and its parameters)"
  - "models/parts/rpispeaker-v17-body/rpispeaker-v17-body.sc (reconstruction, central Ø10 opening)"
  - "James, 2026-11-16: wants the 40 mm driver in the case, and expected the lid to carry the frame"
supersedes: []
---

## Summary

James asked for a 40 mm driver in the case and expected the lid to carry its
frame. The repository's own measurements say he is right, and for a reason
stronger than preference: **the v17 body's speaker-side footprint is
31.10 × 28.125 mm, and a Ø40 driver is 40 mm across, so it cannot be contained in
that bay in either axis.** Widening the Ø10 central opening to the ~36 mm a
40 mm driver needs would not help, because what is too small is the bay, not the
hole. "Modify the body" therefore means rebuilding the body around a larger bay,
not enlarging an opening.

The only 40 mm driver the repository has dimensions for is the Adafruit 3968,
**Ø40 × 21 mm with no fastener holes at all**, so whatever holds it must clamp
it rather than screw into it.

A first CAD concept is built and measured at
[`models/parts/v17-40mm-driver-frame/`](../../models/parts/v17-40mm-driver-frame/README.md):
a Ø58 baffle with a Ø36 opening and a Ø41 seat, and a separate clamp retainer with
four bosses. Two closed bodies, 5461 mm³ and 6517 mm³, both matching a hand
calculation to within 20 mm³, with 1.5 mm between the retainer bosses and the
driver's edge.

## Claims and evidence

| Kind | Claim | Source / date / hardware-version scope | Verification and limits |
| --- | --- | --- | --- |
| observed | The body's speaker-side lower footprint is 31.10 mm (X) × 28.125 mm (Z) | bay inventory note, from the v17 STEP | Measured from the STEP in a previous session; the X 17.15 boundary is not a continuous wall, and the region is a bounded comparison area, not a closed pocket |
| observed | A Ø40 driver needs a 40 mm circle of space, which exceeds 31.10 and 28.125 | arithmetic from the two figures above | Does not depend on CAD; holds for any round driver of Ø40 |
| observed | The Adafruit 3968 is Ø40 × 21 mm with no fastener holes and "needs a clamp or printed retainer" | speaker-candidates README, vendor-published | Vendor dimensions, not measured; the driver's rim and cone geometry are unknown |
| observed | The existing lid serves a Ø28 driver in an external sleeve, not a 40 mm one | `rpispeaker-v17-lid.sc` parameters `DRIVER_D` 28, `POCKET_D`, `BACK_OPEN_D` 24.8 | Reading the saved parameters, not a fit test |
| observed | The frame and retainer are two separate closed bodies with the measured volumes | SolidCraft `measure` on `v17-40mm-driver-frame.sc`, 2026-11-16 | CAD geometry only; the first build fused them because the bosses started inside the plate, which was corrected to a 0.2 mm gap |
| hypothesis | Four M3 screws from the front of the baffle into retainer bosses will clamp a driver that has no holes | design reasoning | Untested; screw length, pilot grip in printed plastic and the rim thickness it must grip are all unsettled |
| open-question | Which driver is actually intended | James said "try both", and separately described "my square speaker and its four screws" | A 40 mm driver with a square four-screw flange needs a different pattern entirely; the v17 STEP's two holes 36.5 mm apart are not that pattern either. A photograph or a model number would settle it |

## Verification

- Ground truth: the bay footprint and driver envelopes are repository
  measurements and vendor data; the arithmetic above uses no CAD.
- CAD: `models/parts/v17-40mm-driver-frame/v17-40mm-driver-frame.sc` measured
  with SolidCraft. Baffle 5461 mm³, Ø58 × 4; retainer 6517 mm³, Z 4.2–25;
  hand calculations 5460 and 6536 mm³.
- Not run: any print, slice, fit test, screw test, or acoustic measurement.
  No interference check against the v17 body was performed, because the frame is
  not yet cut into the lid.

## Handoff and correction links

- Where the concept lives: [the part README](../../models/parts/v17-40mm-driver-frame/README.md).
- Next action: confirm the driver, then cut the Ø58 frame opening into the lid's
  face so the two parts are one printable lid plus a retainer.
- Do not treat this note as a decision that the 40 mm driver is the right
  choice; it establishes only where it can go.
