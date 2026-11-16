# What to measure on the real speaker

**Status:** a request for five measurements, 2026-11-15. Nothing here is a
measurement. This sheet exists because the [lid's](README.md) speaker mount is the
one blocked part that a ruler can unblock: every number below is currently an
assumption, and each one changes the geometry in a specific way.

Measure the **actual driver you intend to fit**, not a listing's nominal size and
not a different model of the same family. Write the model and where it came from
beside the numbers, because "Ø28" from one seller is not "Ø28" from another.

## The five numbers that decide the mount

| # | Dimension | How to measure | What it changes |
| --- | --- | --- | --- |
| 1 | **Cone diameter** — the outermost moving part, across the widest point | Calipers across the front, with the driver face up; do not press on the cone. | The sleeve's clear bore. It is currently Ø28 with 0.2 mm radial clearance, which is an assumption. |
| 2 | **Frame / flange outline** — the rigid outer shape, and whether it is round or square | Calipers across the widest rigid points, front and back if they differ; trace the outline on paper if it is not a simple shape. | Whether the driver can sit on the 1.6 mm radial land at all, and whether a round sleeve is the right shape. |
| 3 | **Overall depth** — front face of the frame to the rearmost point, magnet included | Calipers or a rule against a flat surface, driver face down. | How far the part protrudes past Y 25.50, and whether the 10 mm sleeve depth is enough. Only **5.40 mm** separates the lid's plate underside (Y 13.90) from the bay's raised surfaces (Y 8.50), so depth is the tightest dimension. |
| 4 | **Mounting-hole pitch** — centre-to-centre, and the hole diameter | Calipers between hole centres; measure one hole's diameter. | The screw pattern. `SQ_PITCH` = 32 mm is an assumption and the lid currently carries two pilot holes, not four. |
| 5 | **Terminal side and wire exit** — which edge the tabs are on, and how far they stand proud | Look at the back; measure the tallest terminal above the frame. | The connector slot (currently an assumed 7 × 4 mm at Z 27) and whether a wire can leave without crossing the cone. |

If the driver has a **rear vent, a magnet boot, or a gasket**, say so: those are
the things a nominal diameter never mentions and they decide whether it seats
flat.

## What these numbers will not settle

- **Acoustic performance.** A sealed or open sleeve, the cavity behind the driver
  and the grille all change the sound. This sheet is mechanical fit only.
- **The Pi bay.** No Pi, HAT or header is modelled, so nothing here says whether a
  Pi-bay component fouls the lid's rear face.
- **The original body.** The v17 dimensions are the supplied ones; a printed part
  is still the only test of fit to the real housing.
- **Retention.** The sleeve does not retain the driver by itself, by design. The
  retainer is designed *after* these numbers exist.

## Where to record the answers

Add them to the table in the [lid README](README.md) as **MEASURED** rows with the
date and the model, next to the existing **ASSUMED** ones — do not overwrite an
assumption, add the measurement that supersedes it. Then the mount decision is:
protruding sleeve with the measured bore and depth, or a flat plate with a rear
clamp, and the two pilot holes either move to the measured pitch or become four.
