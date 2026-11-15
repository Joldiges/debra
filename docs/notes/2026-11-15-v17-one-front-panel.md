---
title: One front panel for v17, not a cover and a lid
date: 2026-11-15
type: project-learning
status: unreviewed
task: V17 speaker mount decision
author: OpenCode agent
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - James, in conversation 2026-11-15: "isn't the cover and lid all in one? I'll let you figure out what to do smartly"
  - docs/notes/2026-11-15-v17-cover-lid-conflict.md — the 785.083645226661 mm³ interference measurement
  - docs/notes/2026-11-15-rpispeaker-v17-bay-inventory.md — bay endpoints, floor and raised surfaces
  - models/parts/rpispeaker-v17-lid/README.md and build-script.json
  - models/parts/rpispeaker-v17-cover/README.md and build-script.json
  - models/assemblies/rpispeaker-v17-body-lid/README.md — 0 mm³ body/lid fit
---

# One front panel for v17, not a cover and a lid

## What was decided

James asked why the cover and the lid are separate parts at all. They should not
be. The second bay has **one** front plate, and this repository had grown two
attempts at it:

- [the lid](../../models/parts/rpispeaker-v17-lid/README.md) — an inset plate flush with the
  body's Y 15.50 front, two rear pads on the body's measured pilots, a Ø28
  driver in a sleeve protruding 10 mm, and a connector slot; and
- [the cover](../../models/parts/rpispeaker-v17-cover/README.md) — a raised bridge with an
  assumed 32 mm square four-screw speaker pattern, carried on two Ø8 feet at the
  same pilot axes.

They intersect by **785.083645226661 mm³** when both are installed, because each
occupies the same space in front of the same bay. That measurement is what
forced the question, and the answer is the obvious one: **the lid is the front
panel.** The cover is retired.

## Why the cover is the one that goes

The cover's only contribution the lid lacks is the four-screw speaker pattern,
and that pattern cannot go on the lid:

- The lid plate spans **X 17.45–47.95**, which is **30.50 mm** wide.
- A 32 mm square pitch puts its X holes at ±16 mm from the driver centre, so
  they fall **outside** the plate on both sides.

So the pattern is not "missing from the lid" — it does not fit the part it was
meant to be merged into. Keeping the cover alive to carry it would preserve a
second front plate whose speaker mounting is an assumption (`SQ_PITCH` was never
measured) and two of whose holes sit 2 mm above the Pi-side divider, where a
fastener can collide with it. That is not a part worth carrying.

## What this changes

- `models/parts/rpispeaker-v17-cover/` is **retired, not deleted**. Its source,
  build script, renders and measurements stay where they are, because the
  interference result and the divider collision are evidence, and the project
  does not delete files. Its README now says it is superseded.
- `models/parts/rpispeaker-v17-lid/` is the single front panel. No geometry
  changed in this decision: the change is which part is the design.
- The [body-and-lid assembly](../../models/assemblies/rpispeaker-v17-body-lid/README.md)
  is already the right assembly for the one-panel design, and its 0 mm³ result
  is the fit evidence.

## What is still missing, and why no new holes were added

Nothing here is a validated speaker mount. The open measurements, in the order
they block work:

1. **The actual driver.** Diameter, overall depth, frame or flange outline, and
   the mounting-hole pitch and thread. `SQ_PITCH` = 32 mm and `DRIVER_DEPTH` =
   10 mm are both assumptions. Until they are measured, any hole pattern is a
   guess, and a guessed pattern in a printed part is a wasted print.
2. **The driver's height in the bay.** The lid's plate underside is at Y 13.90
   and the bay's raised surfaces are at Y 8.50, so **5.40 mm** separates them;
   the shelf floor is at Y 2.50. The lid's 10 mm sleeve protrudes forward
   because a 10 mm driver cannot sit between those surfaces. Whether the real
   driver fits in the bay, needs the sleeve, or needs a different plate plane is
   the decision that follows from measurement 1.
3. **Retention.** The sleeve has 0.2 mm radial clearance and does not retain
   anything. A retainer, a clamp ring or a flanged driver are all open, and the
   choice depends on the frame that measurement 1 produces.

Two candidate mountings are therefore recorded rather than built:

- **Protruding sleeve** (today's lid): the driver sits inside the sleeve in
  front of the plate. Works with a deep driver; the sleeve is the visible
  feature and is open at the front.
- **Flat plate with a rear clamp**: the driver sits behind the plate in the bay,
  pressed against the plate by a ring or bracket. Keeps the front flat, and needs
  a driver shallow enough to fit in 5.40 mm or a plate moved forward.

## What is not claimed

No geometry was rebuilt for this note. Nothing was printed, sliced or
fit-tested, and no speaker has been identified. The 785.08 mm³ interference is a
CAD result between two models, and the 0 mm³ body/lid result is a CAD result
between two other models; neither is a physical fit. The retirement of the cover
is a design decision, not an engineering validation of the lid.
