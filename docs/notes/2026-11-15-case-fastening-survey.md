---
title: Case fastening survey — thread-forming screws, heat-set inserts, snap fits
date: 2026-11-15
type: project-learning
status: unreviewed
task: none (ad-hoc enclosure research for the D01–D03 lane)
author: OpenCode agent, unattended run
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown (host reported no variant)
sources:
  - S1–S14, full URLs and access date in the source register below
  - Repository: models/parts/dweii-462-case, models/parts/dweii-671-case, docs/design/enclosures.md (read only)
supersedes: []
---

## Summary

Four ways to close a printed case were checked against published manufacturer
data rather than maker convention. The useful results:

- The hole for a heat-set insert is fixed by the **insert's outside diameter**,
  which varies by family, not by the thread size. For M3 the published values
  run from 3.99 mm (SPIROL straight, 4.62 mm insert) to 5.23 mm (E-Z LOK
  tapered, 5.59 mm insert). A single "M3 = 4.0 mm" rule is a habit, not a
  dimension.
- SPIROL's boss rule is **2–3 × insert diameter** and its minimum hole depth is
  **insert length + 2 thread pitches** [S1, S2]. Tappex's worked M3 example is a
  7.70 mm boss with a 1.65 mm wall [S3].
- EJOT's published rule for thread-forming screws in thermoplastics is
  **hole = 0.80 × d**, **boss OD = 2.00 × d**, **engagement = 2.00 × d**, with a
  0.75/1.85/1.70 row for PET [S6]. There is no PLA or PETG row; that gap is the
  main unknown.
- Snap fits have no boss or hole: the governing dimensions are beam thickness,
  beam length and undercut, limited by allowable strain. Bayer publishes 2.0–4 %
  allowable short-term strain for its PC/PC-blend resins and says to use **about
  60 % of that for frequent separation** [S8]. No manufacturer publishes a PLA or
  PETG snap strain limit.

Recommendation for a case opened often: **M3 brass heat-set inserts in PETG**,
four screws, 8 mm bosses, 4.0 mm modelled holes verified on a coupon. Snap fits
are demoted to alignment and to parts opened rarely. Reasoning in "Recommendation".

Everything here is a document study. Nothing was printed, fitted or measured
apart from the ruthex STEP file noted below.

## Scope and method

Pages and PDFs were fetched on **2026-11-15**; PDF tables were extracted with
`pdftotext -layout` so the numbers below are the manufacturers' printed columns,
not summaries. `derived` in a table means arithmetic on the sourced input in the
same row (for example wall = (boss OD − hole)/2); it is not a separate
manufacturer statement and inherits the source's limits. Labels are the
project's own: `upstream-documented`, `reported`, `hypothesis`, `unknown`.

## 1. Thread-forming ("self-tapping") screws straight into printed bosses

The best-documented system is EJOT PT — a screw geometry designed for plastics,
not a wood or sheet-metal screw. Its design table is the reference here because
it is per-material and includes the boss and engagement depth [S6]:

| Screw d | Hole Ø 0.80·d | Boss OD 2.00·d | Engagement 2.00·d | Wall (derived) | Label |
| --- | --- | --- | --- | --- | --- |
| M2 | 1.6 mm | 4.0 mm | 4.0 mm | 1.2 mm | upstream-documented (ABS/ABS-PC/PS/PVC rows) |
| M2.5 | 2.0 mm | 5.0 mm | 5.0 mm | 1.5 mm | as above |
| M3 | 2.4 mm | 6.0 mm | 6.0 mm | 1.8 mm | as above |
| M4 | 3.2 mm | 8.0 mm | 8.0 mm | 2.4 mm | as above |

For PET the same brochure prints 0.75·d hole, 1.85·d boss, 1.70·d engagement
[derived for M3: 2.25 mm hole, 5.55 mm boss, 1.65 mm wall]. ASA is 0.78/2.00.
Filled and high-strength grades move the hole **up** to 0.88·d, and the DELTA PT
brochure repeats **0.8·d ± 0.05 mm** with a maximum 1° core-hole draft [S7].

Assumptions for printed parts:

- **The table is for moulded thermoplastics.** Printing adds layer seams, a
  chosen infill and a hole that prints undersized; none of that is in the table.
  `hypothesis`: a printed boss behaves like the moulded row only if the boss
  wall is printed solid (perimeters, not infill) — Prusa's own material page says
  "the majority of a 3D print strength comes from its outer shell" [S14].
- **PETG**: use the PET row as a starting point, not a qualification.
- **PLA**: `unknown`. No manufacturer table found.
- Hole shrinkage: a printed hole comes out smaller than the CAD value, so the
  CAD hole is usually made a little larger than the target [S12, reported].

Tooling [S6]: the correct pilot drill, a driver limited to **≤ 500 min⁻¹** (EJOT:
higher speeds damage the plastic), and a clutch or torque setting. EJOT warns
that excessive clamp load causes relaxation or stress cracks and that the
tightening torque must be kept as low as possible.

Failure modes:

- Stripped thread after repeated cycles. Forming a thread permanently deforms
  the plastic; repeated removal and re-insertion wears it. `reported` — a ruthex
  customer review describes exactly this after about five cycles [S11 review
  text], and UltiMaker states that with inserts "weaker materials like PLA can
  end up becoming the point of failure" [S13].
- Boss splitting from hoop stress when the wall is thin or the hole is
  undersized; SPIROL's equivalent warning for inserts is that smaller holes
  "induce undesirable stresses and potential cracks" [S2].
- Loss of strip torque if the hole is too large (SPIROL: larger holes decrease
  performance) [S1].
- Screw bottoming in a blind pilot, which jack-screws the boss apart [S2,
  jack-out].

## 2. Heat-set threaded inserts

Published dimensions, one row per family. **Read the hole column against that
family's own insert OD** — that is the point of the table.

| Family | Thread | Insert OD | Published hole | Published boss / wall | Depth | Label |
| --- | --- | --- | --- | --- | --- | --- |
| SPIROL INS 19/20 straight, heat/ultrasonic | M2 (2-56) | 3.58 mm | **3.20 mm** | boss 2–3 × insert Ø | L + 2 pitches | upstream-documented [S1] |
| " | M2.5–M3 (4-40) | 4.62 mm | **3.99 mm** | as above | as above | [S1] |
| " | M3.5 (6-32) | 5.41 mm | **4.78 mm** | as above | as above | [S1] |
| " | M4 (8-32) | 6.25 mm | **5.61 mm** | as above | as above | [S1] |
| " | M5 (10-24) | 7.04 mm | **6.40 mm** | as above | as above | [S1] |
| Tappex Trisert-3 (self-tapping insert, no heat) | M3 | 4.73 mm | **4.10–4.40 mm** | **7.70 mm boss, 1.65 mm wall** | 5.80 mm | upstream-documented [S3] |
| E-Z LOK E-Z Sonic tapered, heat/ultrasonic | M3 | 5.59 mm | **5.23 mm** | min. wall 2.95 mm | 3.81 mm | upstream-documented [S5] |
| ruthex RX-M3x5.7 (the common 3D-print insert) | M3 | see measurement below | **4.0 mm recommended by the seller** | not published | 5.7 mm body | reported [S11, S12] |

Rules that hold across the families [S1, S2, S5]:

- Minimum hole depth = **insert length + 2 thread pitches**; E-Z LOK states at
  least 0.030 in (0.76 mm) deeper than the insert in a blind hole.
- The insert top should finish flush; SPIROL allows at most 0.13 mm protrusion.
- The mating part's clearance hole must be **larger than the screw but smaller
  than the insert's pilot diameter**, so the insert, not the plastic, carries
  the load and cannot be pulled through ("jack-out").
- Boss diameter 2–3 × insert diameter, with the multiplier falling as the insert
  gets bigger.

Measured check on the ruthex insert: their published STEP for RX-M3x5.7
(downloaded 2026-11-15) contains 9,108 Cartesian points. The dominant body
diameter is **≈4.1 mm**, the largest vertex radius corresponds to **4.81 mm**
(a crest or the lead-in), and the axial extent is **6.73 mm** against a nominal
5.7 mm [derived from S11 file, verified in this run]. So "the OD" of a knurled
heat-set insert is not one number, and a 4.0 mm hole is a deliberate
interference/melt fit rather than a clearance fit. This is the clearest reason
not to copy an "M3 = 4.0 mm" rule between insert brands.

Manufacturer performance data, for scale only [S1]: an M3 INS 19 long heat-set
insert in an unfilled **nylon 6/6** boss at least 2 × insert diameter, drilled
hole, reached ≈1,445 N tensile and ≈3 N·m torque. SPIROL itself says this "should
only be used as a general comparative guide". It is not PLA or PETG data.

Tooling [S3, S11, S12]: a temperature-controlled soldering iron with an
insert-sized tip (ruthex sells M2–M8 tips and adapters; Tappex sells hand tools,
and production users fit inserts with a heat/ultrasonic machine); a flat seating
tool to press the last millimetre flush; a drill and deburrer for rework; a
coupon for setting the hole. CNC Kitchen, a seller of these inserts, recommends
an iron 10–20 °C above the printing temperature (≈225 °C for PLA, ≈245 °C for
PETG) and warns that inserts creep back out if not held until the plastic
solidifies [S12, reported].

Failure modes: boss cracking from an undersized hole or thin wall [S2]; pull-out
from a short insert or poor melt; jack-out from a screw that bottoms out [S2];
insert proud of the surface; spinning/over-torqued insert; heat damage or a
glossy ring on the visible face; and creep of the surrounding plastic under
sustained screw preload when the part is warm — `hypothesis`, based on PLA's
55 °C heat-deflection temperature [S9] rather than a measured test.

## 3. Snap fits and screwless clips

There is no boss and no hole, so the dimension set is different: beam thickness
`t`, beam length `L`, undercut `y`. Bayer's guide gives, for a uniform cantilever,
strain at the root **ε = 1.5 · t · y / L²**, and 0.92 in place of 1.5 for a
tapered beam [S8].

Allowable short-term strain at 23 °C, single joining operation, from Bayer's
Table 2 [S8]:

| Resin | Allowable strain | Label |
| --- | --- | --- |
| PC (Makrolon) | 4.0 % | upstream-documented |
| PC/ABS (Bayblend) | 2.5 % | upstream-documented |
| PC blend (Makroblend) | 3.5 % | upstream-documented |
| PC + 10 % GF | 2.2 % | upstream-documented |
| PC + 20 % GF | 2.0 % | upstream-documented |

The same table's note is the important one for a development case: **"for
frequent separation and rejoining, use about 60 % of these values"** [S8].

No PLA or PETG row exists in any manufacturer guide found. Two derived starting
points, labelled `hypothesis`, using Prusa's printed elongation at yield as a
ceiling (PLA 2.9 %, PETG 5.1 % [S9, S10]) and Bayer's 60 % rule:

| Material | Derived allowable strain | Undercut at t = 1.6 mm, L = 10 mm | Label |
| --- | --- | --- | --- |
| PLA | 1.7 % | ≈0.72 mm | hypothesis |
| PETG | 3.1 % | ≈1.28 mm | hypothesis |

These are arithmetic, not tested. Elongation at yield is not the same quantity as
an allowable snap strain, and printed layer orientation is not in the model.

Failure modes: permanent set or whitening when the strain exceeds the allowable
value; loss of retention after repeated opening (creep and wear of the undercut);
brittle fracture in PLA; and delamination at the beam root if the layers run
across the bending axis — the last is `hypothesis`, not measured here.

Screwless options beyond the cantilever: Bayer also covers torsion and annular
(twist-lid) snaps [S8]. Both avoid screws entirely; both are strain-limited in
the same way, and an annular snap needs a full circumference of compliant wall,
which a rectangular electronics case usually does not have.

## 4. Material assumptions, PLA and PETG

Published values, Prusament (Prusa Polymers) technical data sheets [S9, S10]:

| Property | PLA | PETG | Method |
| --- | --- | --- | --- |
| Heat deflection temperature, 0.45 MPa | 55 °C | 68 °C | ISO 75 |
| Heat deflection temperature, 1.80 MPa | 55 °C | 68 °C | ISO 75 |
| Tensile modulus, printed horizontal | 2.3 GPa | 1.5 GPa | ISO 527-1 |
| Elongation at yield, printed | 2.9 % | 5.1 % | ISO 527-1 |
| Interlayer adhesion | 17 ± 3 MPa | 18 ± 4 MPa | Prusa method |
| Printing temperature | 210 ± 10 °C | 250 ± 10 °C | — |

What that means for fasteners:

- **PETG** is the better host for both inserts and snaps: 13 °C more heat
  resistance, twice the elongation at yield, and about a third less stiffness, so
  a boss bends before it splits. Its lower modulus is a cost for a snap beam:
  the same geometry is softer and needs more undercut for the same holding force.
- **PLA** is stiffer and holds a screw preload better at room temperature, but
  its 55 °C HDT sits inside the range a small electronics case can reach, and its
  2.9 % elongation at yield leaves little room for a snap. `hypothesis` for the
  temperature effect — no enclosure temperature was measured here.
- Both gain strength from perimeters rather than infill [S14, vendor statement].
  A boss whose wall is sparse infill is not the boss the manufacturer tables
  describe.

## 5. Recommendation for a case opened often

For a development case that is opened weekly, the joint has to survive many
cycles without losing preload. Ranked:

1. **Heat-set M3 brass inserts in PETG, four screws.** The thread is metal and
   reusable; the insert is a serviceable, replaceable part of the design; the
   assembly needs one tool and no clips that fatigue. Concrete dimensions for
   the common M3 insert, from the tables above:
   - boss OD **8.0 mm** (Tappex's M3 figure is 7.70 mm [S3]; SPIROL's 2 × a
     4.1 mm insert is 8.2 mm), wall ≈ **1.9 mm** minimum, printed solid;
   - modelled hole **4.0 mm**, but confirm on a coupon at 4.0 / 4.2 / 4.4 mm,
     because the printed hole prints small and because insert brands differ
     (section 2);
   - hole depth **≥ 6.7 mm** (5.7 mm insert + 2 × 0.5 mm pitch), blind, with a
     little material below; insert flush to +0.13 mm [S2];
   - lid clearance hole **3.2–3.4 mm**: larger than the M3 screw, smaller than
     the ~4.0 mm insert pilot, which is exactly SPIROL's anti-jack-out rule
     [S2];
   - light, consistent tightening; the manufacturer torque-out figure (≈3 N·m in
     nylon) is not a target for printed PETG.
2. **Tappex Trisert-3 self-tapping insert**, if a soldering iron is unwanted: it
   installs with a driver, is removable, and needs a 4.10–4.40 mm hole in a
   7.70 mm boss [S3]. Same boss budget, different tooling.
3. **Thread-forming screws (EJOT PT geometry) directly into the boss**, for
   prototypes and for joints opened a handful of times: 0.8 × d hole,
   2 × d boss, 2 × d engagement [S6]. Accept that the formed thread wears.
4. **Snap fits last.** Use them for alignment, for the speaker grille, and for
   covers that come off rarely. Do not make them the only joint on a lid that is
   opened every week: Bayer's own 60 % de-rating for frequent separation [S8] and
   the absence of any PLA/PETG limit make the cycle life unquantified.

A mixed design is the practical answer: two shallow spigots or a tongue-and-groove
edge for alignment and shear, plus four insert screws for clamp load. The spigots
carry alignment, the screws carry the load, and nothing depends on a plastic
spring remembering its shape.

### What this means for the two cases in the repository

Read-only comparison against `models/parts/dweii-462-case` and
`models/parts/dweii-671-case` (both are designs, not prints):

| Existing parameter | Value | Reading |
| --- | --- | --- |
| `BOSS_D` | 4.8 mm | 1.92 × M2.5 — just under EJOT's 2.00 × d, acceptable |
| `PILOT_D` | 2.2 mm | 0.88 × M2.5 — the top of EJOT's range, intended for filled/high-strength grades; 2.0 mm (0.80 × d) is the better starting point for PLA/PETG |
| `PILOT_DEPTH` | 7 mm blind | fine for a 6–8 mm screw, but the engaged length, not the hole depth, is what matters |

An M3 insert retrofit does **not** fit the current boss budget: 8.0 mm bosses
would add 1.6 mm per side. In the 671 case the cavity is 66.2 mm for 65 mm boards
and the rear bosses are already thickened into the back wall, so widening them
needs a layout change, not a parameter change. An M2.5 insert (SPIROL 4-40 row:
4.62 mm insert, 3.99 mm hole) still wants a boss near 6 mm, which is also more
than 4.8 mm. Practical conclusion: the compact case stays on thread-forming
screws, or its corners are redesigned; the inserts belong in the larger cases
first.

## Traps

- **"M3 insert = 4.0 mm hole" is brand-specific.** The same thread is sold on
  4.62 mm, 4.73 mm and 5.59 mm bodies with published holes from 3.99 to 5.23 mm.
  Pick the insert, then read its own table.
- **"OD" of a knurled insert is not one diameter.** The ruthex M3 STEP measures
  ≈4.1 mm on the body and 4.81 mm at the widest vertex.
- **Manufacturer boss rules disagree at small sizes.** SPIROL's 2–3 × rule read
  literally on a 4.62 mm insert gives 9.2–13.9 mm; Tappex publishes 7.70 mm for
  its M3. The datasheet for the actual part wins over the general rule.
- **Bayer's strain table is not a plastics-wide table.** It lists Bayer resins.
  Copying 4 % onto PLA is unsourced.
- **The manufacturers' test data is nylon or ABS.** SPIROL tested nylon 6/6
  bosses; EJOT's table has no PLA or PETG column. Neither is a prediction for a
  printed part.
- **Repeated opening is the design case, not the exception.** Both the insert
  and snap guidance changes when the joint is opened often (Bayer's 60 % note;
  thread wear in formed threads).
- **A blind pilot can jack the insert out.** SPIROL's minimum depth exists for
  this reason.

## Unknowns and blocked

- No PLA or PETG snap-fit strain limit from any resin manufacturer: `unknown`.
- No manufacturer pull-out or torque data for heat-set inserts in printed PLA or
  PETG: `unknown`. Community measurements exist but were not treated as
  manufacturer data here.
- Creep of a loaded boss at 40–60 °C in an enclosure: `unknown`.
- Printing orientation versus insert retention: no primary source found; the
  claim that perimeters dominate is a vendor statement [S14].
- No PDF page was blocked in this run. Two model-shop pages returned HTTP 429 to
  a scripted fetch and were read through the fetch tool instead; their content is
  cited from the same pages.

## Source register

All accessed **2026-11-15**.

| Key | Source | URL |
| --- | --- | --- |
| S1 | SPIROL, *Inserts for Plastics Design Guide* (PDF; dimensional tables, boss rule, performance tables) | https://www.spirol.com/assets/files/ins-threaded-inserts-design-guide-us.pdf |
| S2 | SPIROL, *How to Design the Proper Hole for Heat/Ultrasonic Inserts* (white paper, PDF) | https://www.spirol.com/assets/files/ins-wp-how-to-design-the-proper-hole-for-heat-ultrasonic-inserts-us.pdf |
| S3 | Tappex, Trisert-3 M3 product page (hole design: 7.70 mm boss, 4.10–4.40 mm hole, 1.65 mm wall) | https://tappexinserts.com/products/self-tapping-threaded-inserts-usa/trisert-3 |
| S4 | Tappex, *Threaded inserts for plastics: a ten-point guide* (PDF) | https://www.tappex.co.uk/wp-content/uploads/2017/04/10-Point-Guide.pdf |
| S5 | E-Z LOK, product brochure 2020 (PDF; ultrasonic insert tables, hole and wall columns) | https://www.ezlok.com/assets/documents/EZ-LOKBrochure2020.pdf |
| S6 | EJOT, *The EJOT PT Screw* brochure (PDF; per-material hole/boss/engagement table) | https://apexfasteners.com/fasteners/images/Brochure_EJOT_PT_02.11_en.pdf |
| S7 | EJOT, *DELTA PT* brochure (PDF; 0.8 × d hole, 2 × d depth) | https://www.ejot.pl/medias/sys_master/IND_Ulotki_PL/IND_Ulotki_PL/he2/h04/9165098123294/EJOT-DELTA-PT-EN.pdf |
| S8 | Bayer MaterialScience, *Snap-Fit Joints for Plastics — A Design Guide* (PDF, mirrored by MIT Fab Lab) | https://fab.cba.mit.edu/classes/S62.12/people/vernelle.noel/Plastic_Snap_fit_design.pdf |
| S9 | Prusa Polymers, Prusament PLA technical data sheet (PDF) | https://prusament.com/wp-content/uploads/2022/10/PLA_Prusament_TDS_2021_10_EN.pdf |
| S10 | Prusa Polymers, Prusament PETG technical data sheet (PDF) | https://storage.googleapis.com/prusa3d-content-prod-14e8-wordpress-prusament-prod/2023/10/9f8d2165-tds_prusament-petg_n_en.pdf |
| S11 | ruthex, RX-M3x5.7 product page and its published STEP file | https://www.ruthex.de/en/products/ruthex-gewindeeinsatz-m3-100-stuck-rx-m3x5-7-messing-gewindebuchsen |
| S12 | CNC Kitchen, *Tips & Tricks for Heat-Set Inserts* (seller guidance: iron temperatures, printed holes) | https://www.cnckitchen.com/blog/tips-tricks-for-heat-set-inserts |
| S13 | UltiMaker, *How to use heat set inserts to securely fasten 3D printed parts* | https://ultimaker.com/learn/how-to-use-heat-set-inserts-to-securely-fasten-3d-printed-parts |
| S14 | Prusament PETG product page (perimeters statement; 68 °C) | https://prusament.com/materials/prusament-petg/ |

## Verification

- Exact procedure: fetched the PDFs and pages above on 2026-11-15 into
  `/tmp/opencode/fastening/`, converted with `pdftotext -layout`, and read the
  dimension columns. The ruthex STEP file was parsed with a short Python script
  that collected `CARTESIAN_POINT` triples (9,108 points) and reported the
  radius distribution and axial extent.
- Observed results: document extraction pass; STEP measurement pass. Physical
  fit: **not-run** — no coupon was printed or assembled.
- Not tested / uncertainty: everything about printed-part behaviour (hole
  shrinkage, boss cracking, cycle life, creep) is a document inference. The
  numbers in section 5 are design targets to test, not validated dimensions.
- Artifacts: PDFs remain only in `/tmp/opencode/fastening/`; nothing was added
  to `models/`.

## Handoff and correction links

- State: a new unreviewed note; no model, document under `docs/design/` or test
  was changed. Nothing in this note authorises a print run or a design change.
- Next action (bounded): print one coupon with four M3 boss variants
  (hole 4.0 / 4.2 / 4.4 mm, boss 7.7 mm) in PETG, install four inserts, and
  record pull-out and 20 open/close cycles. Prerequisite: a printer and a
  torque-limited driver; not authorised by this note.
- Earlier claims: none superseded. The existing `BOSS_D`/`PILOT_D` values are
  recorded as comparisons, not corrections.
- Reviewed report that adopts this: none yet.
