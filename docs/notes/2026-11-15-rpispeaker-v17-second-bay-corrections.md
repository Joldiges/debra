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

## Summary

Two numbers in the extraction note were wrong or incomplete, and both were found
by workers doing arithmetic on the same coordinates. The original note is
preserved; this note supersedes the two claims below.

| Claim as published | Correct value | Why |
| --- | --- | --- |
| Second bay is "a 31.85 x 66 mm pocket" | **31.10 x 66 mm** | The measured inner faces are X 17.15 and X 48.25. 48.25 - 17.15 = 31.10. The 31.85 came from using the envelope's outer X 49.00 instead of the inner face, which counts the 0.75 mm outer wall as bay. |
| Pilots reach the pocket | **They stop 1.21 mm short** | The pilots are drilled from the back face (Y -0.60) to Y 7.29; the pocket floor is Y 8.50. 8.50 - 7.29 = 1.21 mm of material between the end of each pilot and the pocket. |

Neither changes the envelope, the Pi bay, the connector cut-outs, or the absence
of a four-screw square mount. Both change what a lid or speaker carrier can rely
on.

## What the 1.21 mm web means

A lid that sits in the 7 mm pocket cannot be pulled onto the body with a screw
entering from the front: the screw reaches the floor at Y 8.50, then meets
1.21 mm of unthreaded material before the pilot begins at Y 7.29. Fastening in
that direction needs that web opened with a Ø2.2 mm drill, which is a
modification of the original body.

The reverse direction is no better without a change: a screw inserted from the
back face follows the existing pilot and its tip stops at Y 7.29, still behind
the pocket floor, so it never reaches a lid in the pocket.

This is consistent with the pilots being for something mounted on or into the
back of the bay rather than for a front lid. It does not prove that, because the
original assembled part has not been seen. The extraction note already recorded
the pilot depth; what was missing was the subtraction.

## What still stands

- The body contains no four-screw square speaker mount.
- The second bay is the only place a speaker could sit, and it is 31.10 mm wide,
  so a 40 mm square driver cannot sit inside it in any orientation.
- The central Ø10 hole with a Ø18 counterbore opening toward +Y is unchanged.
- The 44 x 28 x 15 mm module still does not fit the 7 mm pocket depth; it
  protrudes.

## What would settle the mount question

A photograph of the assembled original with its cover lifted, showing the
speaker, all four screws, and the material each screw enters. Failing that, the
missing part file, or a measurement of the pilot depth on a physical specimen.

Until one of those exists, any v17 lid is a concept and every fastening claim is
conditional. The [lid study](../../models/parts/rpispeaker-v17-lid/README.md)
says so, and the [mount options](../design/rpispeaker-v17-speaker-mount-options.md)
note now points at it.

## Handoff

- Model READMEs were corrected in place from 31.85 to 31.10; they are living
  documents, not dated notes.
- This note is unreviewed. It corrects arithmetic from coordinates already in
  the record; it adds no new measurement.
