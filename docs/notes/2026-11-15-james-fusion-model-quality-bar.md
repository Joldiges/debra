---
title: James's own Fusion 360 model sets the enclosure quality bar, and it is a different product form
date: 2026-11-15
type: project-learning
status: unreviewed
task: none
author: OpenCode coordinator
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - "James's message 2026-11-15 pointing at /home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360 (his words: \"this should give some indication on quality wanted\")"
  - RPiSpeaker_v17.step, FILE_NAME time_stamp 2026-11-01T21:16:21-05:00, AUTOMOTIVE_DESIGN, Autodesk Translation Framework v15.17.0.0
  - RPiSpeaker_v17.f3d, Previews/small.png and Breps blob, file date 2025-05-18
  - "Geometry read with a local STEP parser and rendered in SolidCraft; see the note's Method section"
supersedes: []
---

# James's own model of this device

## Summary

James has a Fusion 360 design of the same product, `RPiSpeaker v17`, and pointed
at it as the standard of finish he expects. It is **not a box**: it is a slim
back plate, 66.15 × 75.30 × 16.10 mm, one solid, 262 faces, whose outline is a
rectangle blended into a round speaker pod with r = 11 mm tangent arcs, every edge
filleted at 1.0–1.34 mm, with a Pi Zero pocket and a Ø18 speaker opening.

That is a wall-plate product. Debra's current case is a 71 × 54 × 33 mm box,
because it holds a 44 × 28 × 15 mm DWEII speaker module. The two forms cannot be
the same object, and that is a product decision, not a modelling problem.

## Claims and evidence

| Kind | Claim | Source | Verification and limits |
| --- | --- | --- | --- |
| user-requirement | The finish of this model is the quality wanted for Debra's enclosure | James, 2026-11-15 | His words, not a specification. No statement about which of its features he values |
| observed | Overall 66.15 × 75.30 × 16.10 mm; one `MANIFOLD_SOLID_BREP`, 262 `ADVANCED_FACE` (76 plane, 154 cylindrical, 23 B-spline, 9 conical) | STEP file, parsed | Bounding box from all 513 `VERTEX_POINT`s |
| observed | Pi Zero pocket: four Ø8 posts with Ø2.68 holes on a 58 × 23 mm pattern | `CYLINDRICAL_SURFACE` radii 4.0 (×4) and 1.34 (×64) with axis positions | 58 × 23 is exactly the Pi Zero's mounting-hole spacing, so this is a Zero, not a Pi 4/5 |
| observed | Speaker: Ø18 opening over a Ø10 inner ring, concentric, at (31.63, 0) on the plate | radii 9.00 and 5.00, same axis | Small driver — this is not a 40 mm speaker |
| observed | Four Ø7 features at the plate's outer face (y = 15.5) | radii 3.50 ×4 | Read as lid bosses; nothing else in the file uses them |
| observed | Edge fillets at r 1.04–1.34 throughout (125 faces) | radii 1.09 ×61, 1.34 ×64, 1.29 ×8, 1.04 ×7 | Counts are consistent with a uniform ~1.2 mm fillet on every edge of a shell |
| observed | The outline's lobes are r = 11 mm arcs, not holes | radii 11.00 ×4, at (28.15, 0, ±33) with Y axes | This is what makes the silhouette organic |
| hypothesis | The front cover is a separate part that is not in this file | Only one solid exists; the Ø7 features imply a lid | Not verified — v17 may be a work in progress, and later versions may exist |
| open-question | Whether James wants the wall-plate form for Debra | — | A Ø18 driver in a 16 mm plate is a very different product from a 44 × 28 × 15 mm module. This needs asking, not assuming |

## What was done with it

The case at [models/parts/dweii-671-case](../../models/parts/dweii-671-case/README.md)
now carries the edge treatment: 5 mm rounds on the four vertical corners, a 2 mm
round on the base, 1.2 mm on the lid's top edge, a 0.6 mm chamfer under the lid
for a shadow line, and the grille stepped to Ø28 × 1 mm.

The organic outline could not carry over, and the reason is arithmetic rather
than taste: the case is 33 mm tall and the Ø26 grille is 26 mm of that, so the
front face has 2.5 mm above and below the opening. No pod, bezel or inset panel
fits. Reaching that form needs a different speaker, which is a decision.

## Method, because it will be needed again

No CAD program is installed on this host. Two routes worked:

- A ~250-line pure-Python STEP parser (`CARTESIAN_POINT`, `VERTEX_POINT`,
  `EDGE_CURVE` with `LINE`/`CIRCLE`, `EDGE_LOOP` → `FACE_OUTER_BOUND` →
  `ADVANCED_FACE`) rendered with PIL, enough to get the bounding box, the cylinder
  radii and a shaded view. B-spline and ellipse edges were drawn as chords.
- **SolidCraft opens STEP directly** (`doc.open`/`open`), which is the better
  route: same renderer as our own parts, so the comparison is fair. The file has
  to be inside a folder the SolidCraft MCP may use, so it was copied to the
  git-ignored `.local/scratch/` first.

The `.f3d` is a ZIP; `FusionAssetName[Active]/Previews/small.png` inside it is a
Fusion render of the design and is the fastest way to see what a `.f3d` contains.

## Verification

- Commands: `python3 /tmp/opencode/stepview.py <step> <out.png>`;
  `open({path: ".local/scratch/rpispeaker-v17.step"})` in SolidCraft.
- Observed: the STEP imported with one warning (three edges 0.01 mm off their
  faces), 1 body, and rendered consistently from six angles.
- Not tested: whether v17 is James's final intent, whether a lid exists, and how
  any of it printed.
- The `.step` and `.f3d` are James's own files in OneDrive and are **not** copied
  into this repository; `.local/scratch/rpispeaker-v17.step` is a local copy and
  is git-ignored.
