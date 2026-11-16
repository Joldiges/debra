---
title: DWEII 701715519671 is 31 x 28.2 x 15.3 mm, not 44 x 28 x 15
date: 2026-11-16
type: project-learning
status: unreviewed
task: none
author: OpenCode agent
author_model: openrouter/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - James, 2026-11-16, with four seller images of the DWEII module listing
  - https://www.amazon.com/dp/B0B4D1BN4F (listing dimension drawing)
  - models/components/dweii-speakers/build-script.json (superseded 44 mm parameters)
  - docs/notes/2026-11-15-housed-speaker-module-survey.md (the earlier 31 vs 44 contradiction)
supersedes: []
---

## Summary

The v17 speaker is the DWEII `701715519671` (ASIN `B0B4D1BN4F`), confirmed by
James on 2026-11-16 with the seller's images. Those images include the listing's
own dimension drawing: a **28.2 mm square body, 31 mm across the two mounting
tabs, 15.3 mm thick**. The 44 x 28 x 15 mm envelope this repository has been
modelling since 2026-11-15 came from a third-party `manuals.plus` spec sheet and
is superseded. Nothing has been measured with a caliper; the drawing is better
evidence than the sheet, not proof.

The consequence is geometric and immediate: every pocket cut to the 44 mm
envelope is 13 mm too long in the module's long axis.

## Claims and evidence

| Kind | Claim | Source / date / hardware-version scope | Verification and limits |
| --- | --- | --- | --- |
| user-statement | The v17 speaker is `701715519671` from `https://www.amazon.com/dp/B0B4D1BN4F` | James, 2026-11-16 | Direct statement; resolves the "which of the three" question for v17 |
| upstream-documented | Body 28.2 mm square, 31 mm across the mounting tabs, 15.3 mm thick | The listing's dimension drawing, supplied as seller images, 2026-11-16 | Read off the drawing, not measured; the drawing is the seller's own, not a third-party sheet |
| upstream-documented | The module is sold as "Size: 3W 4Ω", 4 pieces, with a JST-PH 2.0 plug | Same images | Listing copy on the same page says both "4 ohms" and "8 ohms"; unresolved (below) |
| observed | The previous 44 x 28 x 15 mm figure came from a `manuals.plus` spec sheet, not from this listing | `docs/notes/2026-11-15-housed-speaker-module-survey.md` records the contradiction; the component README attributes 44 mm to `manuals.plus` | The sheet does not match the drawing and no listing page repeats 44 mm |
| observed | The 44 mm envelope was deliberately the larger of the two conflicting sizes, so one pocket would fit either | `models/components/dweii-speakers/build-script.json` parameter comments, 2026-11-15 | That reasoning was sound for an unknown module and is now moot: the module is known |
| hypothesis | A 31 mm envelope still leaves the four-screw v17 interface unresolved | `docs/design/rpispeaker-v17-speaker-mount-options.md` | The drawing shows two ears with holes, not four screws; hole diameter and position are unpublished |
| open-question | Is the module 4 Ω or 8 Ω? | Listing drawing says 4 Ω for the 3 W variant; listing copy says both; this repository previously recorded 8 Ω | A multimeter settles it: ~3.2-3.8 Ω reads 4 Ω, ~6.5-7.5 Ω reads 8 Ω. It affects the amplifier load, not the case |

## Verification

- Exact safe commands/procedure and working directory:
  - `cd models/components/dweii-speakers && solidcraft-cli run build-script.json --save dweii-speakers.sc --results`
  - `solidcraft-cli eval --in dweii-speakers.sc` and read each body's `bbox`
  - `solidcraft-cli snapshot --in dweii-speakers.sc --out assets/iso.png --camera '{"target":[125,10,22],"yaw":0.7,"pitch":0.32,"distance":300}' --no-grid --no-axes`
- Observed results: pass. The rebuilt bodies report bboxes of X 0->31.0, Y 0->15.3, Z 0->28.2 for both 671 and 664; the 462 is unchanged at 100 x 21 x 45.
- Not tested: no module has been measured. No pocket has been reprinted or fit-tested against the new envelope. The resistance is unmeasured.
- Sanitized artifact references: `models/components/dweii-speakers/assets/iso.png`, `assets/front.png`.

## Handoff and correction links

- Current state: the component envelope and its README are corrected; the parts manifest names the 671 as the v17 speaker.
- Concrete next action and prerequisites: rebuild the parts cut to the old envelope from the new one — `models/parts/dweii-671-carrier` (45.6 x 29.6 x 15 mm pocket), `models/parts/dweii-671-case`, and the assemblies `debra-compact`, `zero2w-dweii-compact`, `zero-square-demo`. Then measure a real module and, if possible, read its resistance.
- Authorization needed; do not treat this suggestion as permission: printing or fit-testing any part.
- Earlier claim superseded: the 44 x 28 x 15 mm 671/664 envelope in `models/components/dweii-speakers/build-script.json` and its README table, recorded 2026-11-15.
- Reviewed report/decision that later adopts this finding: none yet.
