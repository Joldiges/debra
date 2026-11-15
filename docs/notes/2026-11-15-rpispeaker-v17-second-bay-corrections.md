---
title: RPiSpeaker v17 second-bay width and pilot depth corrected
date: 2026-11-15
type: project-learning
status: unreviewed
task: V17
author: OpenCode coordinator
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - docs/notes/2026-11-15-rpispeaker-v17-extraction.md (the note corrected here)
  - docs/design/rpispeaker-v17-speaker-mount-options.md (flagged the width conflict)
  - models/parts/rpispeaker-v17-lid/README.md (found the pilot depth)
  - models/components/rpispeaker-v17/README.md (measured faces)
  - /home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step (the sole geometric source)
supersedes:
  - docs/notes/2026-11-15-rpispeaker-v17-extraction.md
---

# RPiSpeaker v17 second-bay width and pilot depth corrected

> **Correction, 2026-11-15:** the 1.21 mm web does not exist; the front
> countersinks open the threaded through holes. The 31.10 × 66 × 7 mm pocket
> description is also withdrawn: X 17.15 is not a continuous wall, and the
> lower comparison box is 31.10 × 28.125 × 13.00 mm, not a fully walled pocket.
> See [the bay inventory](2026-11-15-rpispeaker-v17-bay-inventory.md).
> Editorial correction: OpenCode, `openrouter/openai/gpt-6.1-terra`, variant unknown.

## Summary

This correction initially proposed a 31.10 × 66 mm pocket and a 1.21 mm web
from arithmetic on the extraction coordinates. The later bay inventory withdrew
both geometric interpretations; the earlier 31.10 mm subtraction remains valid
as a span, not as the width of a fully walled pocket.

| Claim as published | Correct value | Why |
| --- | --- | --- |
| Second bay is "a 31.85 x 66 mm pocket" | **31.10 × 28.125 × 13.00 mm nominal comparison box**, not a pocket | X 48.25 − 17.15 = 31.10, but X 17.15 is not a continuous wall; Z ±14.0625 and Y 2.5–15.5 bound the lower comparison box. The prior 66 mm describes the raised material's outer outline, not a pocket. |
| Pilots reach the pocket | **Two threaded through holes, 36.5 mm apart**, with front countersinks | The Y 7.28775 face terminates part of the thread, not the hole; the core continues through the countersink to Y 8.50. A nominal Ø2 mm probe cleared each axis in the [bay inventory](2026-11-15-rpispeaker-v17-bay-inventory.md). |

The later inventory did not withdraw the envelope, Pi bay, connector cut-outs,
or absence of a four-screw square mount in the supplied STEP. It changes what a
lid or speaker carrier can rely on.

## What the through holes mean

The subtraction 8.50 − 7.29 is approximately 1.21 mm, but those planes do not
bound a solid web: the front countersinks and open core connect to the threaded
paths. Do not drill a supposed web based on this note. Front or back attachment
is a possibility, not an established use; lid clearance, screw fit and
engagement have not been physically tested.

## What still stands

- The body contains no four-screw square speaker mount.
- A 40 mm square driver cannot be fully confined to the lower 31.10 × 28.125 mm
  footprint, but an external, overhanging or partially recessed mount is not
  ruled out.
- The central stepped through-opening is Ø10 at the back, Ø18 in its middle
  and flares to Ø20 at the Y 2.5 central floor.
- The 44 × 28 × 15 mm module does not fit wholly in the nominal comparison
  box: its plan area exceeds the footprint and its depth exceeds 13 mm by 2 mm.

## What would settle the mount question

A photograph of the assembled original with its cover lifted, showing the
speaker, all four screws, and the material each screw enters. Failing that, the
missing part file, or a measurement of the pilot depth on a physical specimen.

Until one of those exists, any v17 lid is a concept and every fastening claim is
conditional. The [lid study](../../models/parts/rpispeaker-v17-lid/README.md)
says so, and the [mount options](../design/rpispeaker-v17-speaker-mount-options.md)
note now points at it.

## Handoff

- The original width-only correction in model READMEs did not establish the
  bay shape; use the linked later inventory for the geometry.
- This note is unreviewed. The corrected geometry above comes from the later
  inventory; this note adds no new measurement.
