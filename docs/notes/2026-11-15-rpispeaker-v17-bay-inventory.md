---
title: RPiSpeaker v17 speaker-side geometry inventory and corrections
date: 2026-11-15
type: project-learning
status: unreviewed
task: V17 bay inventory
author: OpenCode subagent
author_model: openrouter/openai/gpt-6.1-terra
author_variant: unknown
sources:
  - /home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step
  - tools/cad/step_inspect.py
  - models/components/speaker-candidates/README.md
  - models/components/dweii-speakers/README.md
  - docs/notes/2026-11-15-rpispeaker-v17-second-bay-corrections.md
supersedes:
  - docs/notes/2026-11-15-rpispeaker-v17-second-bay-corrections.md
---

# RPiSpeaker v17 speaker-side geometry inventory

## Result and important corrections

The STEP has **no four-hole square pattern** on any face. It has two
speaker-side threaded, **through** holes with front countersinks, plus one
central stepped through-opening. The earlier claim that the two holes are blind
and stop 1.21 mm short is **wrong**: a Ø2 mm cylinder passes each entire axis
from behind the back to in front of the Ø4.5 countersink, with no intersection.
The plane at Y 7.28775 is a partial thread-termination face, not a cap across
the hole. Do not drill a supposed web on the strength of that earlier note.

The earlier **31.10 × 66 × 7 mm pocket** description is also wrong. The 31.10
is a useful speaker-side X span, but its X 17.15 boundary is not a continuous
wall across the central opening. At the lower level, the end walls are at
Z ±14.0625, not ±33, and the central floor is Y 2.5, not 8.5. The Y 8.5 plane
is the raised material outside the central recess, with the two countersinks.
The Z ±33 points belong to the outer outline of that raised material, not the
length of a rectangular pocket. This note supersedes those specific claims in
the [previous correction](2026-11-15-rpispeaker-v17-second-bay-corrections.md)
and the corresponding claims in the
[extraction](2026-11-15-rpispeaker-v17-extraction.md); other claims have not
been reviewed here. It does not change the prior correct arithmetic 48.25 −
17.15 = 31.10 or the negative square-pattern finding.

**Source and frame:** the sole enclosure geometry source is the original
`RPiSpeaker_v17.step`, SHA-256
`fa617a4d0e4afdb1c00c804519718ba6cefeaf8b7c07af65e7c43177ccb66991`, read
2026-11-15. One closed imported body. Coordinates below are **STEP world
coordinates in mm**, not a rotated or re-centred frame: X across, Z along the
case, +Y toward the open/front side. Y 15.5 is the existing Pi-side front
reference plane, **not** a front wall over the entire speaker side. STEP nominal
dimensions are not physical measurements or printing tolerances. SolidCraft
warns that three imported edges deviate from their surfaces by up to 0.01014 mm;
the quoted extra digits describe the file, not physical precision.

## Complete speaker-side feature inventory

There are **three distinct hole axes**, not five: the different diameters on
each axis are stages of the same opening. All axes are parallel to Y.

| Feature | Centre (X, Z) | Geometry, depth and open faces |
| --- | --- | --- |
| Threaded hole A | (32.500, −18.250) | Opens on back Y −0.60 and on raised +Y face Y 8.50; total axial span **9.10**. Modelled helical thread has approximately Ø2.1755 minor and Ø2.68 major limits and approximately 0.45 mm pitch. The 90° included countersink goes from Ø2.1755 at Y 7.33775 to **Ø4.50 at Y 8.50**, axial depth **1.16225**. The remaining **0.05** between Y 7.28775 and 7.33775 is a cylindrical continuation of the open core, not solid web. |
| Threaded hole B | (32.500, +18.250) | Same as A; centres are **36.50** apart. Both are through despite the thread terminating near Y 7.28775. |
| Central stepped opening | (31.625, 0) | At back Y −0.60: **Ø10** through to Y 0, length **0.60**. From Y 0 to 1.50: **Ø18**, depth **1.50**, with annular shoulder at Y 0. From Y 1.50 to the central floor Y 2.50: conical flare Ø18→**Ø20**, axial depth **1.00**, 90° included. Total through-material span is **3.10**. Opens toward +Y at the central floor and toward −Y at the back. No modelled thread. |

The thread diameters and approximate pitch are measured from the cylindrical
and spline geometry and repeated vertices; `M2.5` is the earlier *intended-use
label*, not a verified standard designation. In particular, the modelled
Ø2.68 outer thread limit is not nominal Ø2.50. The STEP does not prove a
physical fastener fit, thread class, hand, printed thread quality, or intended
hardware. Approximate 0.45 mm is the repeated vertex spacing, not a formally
verified thread callout.

**Other features of this side:** the central opening/recess is bounded on its
outer side by the X 48.25 wall from Y 2.5 to 8.5 and by end walls Z ±14.0625
over that height. It joins the neighbouring Pi-side opening toward −X, rather
than being a separate fully walled box. Outside the central recess, the Y 8.5
raised surface carries the two countersinks. Its outer outline has R11 curves
centred at (X, Z) = (28.15, ±33) and (38, ±11); these are exterior rounds,
**not additional holes**. At the central recess the outer wall thickness is
49.00 − 48.25 = **0.75**. The central bore's X centre is 0.875 mm to the −X
side of the pilot centreline. There is no separate physical speaker, cover or
other component in this one-body STEP.

## Search for a square pattern

**Definite negative for the supplied STEP body:** no four-hole square pattern,
at any pitch or rotation, is present on any face. The scripted audit below:

1. Enumerated all **262** advanced faces, including all 154 cylindrical, 9
   conical, 76 planar and 23 spline faces. All spline-face boundary vertices
   group around the six threaded pilot axes, with none elsewhere. All cylindrical
   axes, in both Y and Z directions, are listed in the output; there are no
   X-axis cylinders.
2. Enumerated every inner loop of every planar face, including both X faces.
   The X faces each have the **same three rectangular connector openings**, not
   four; the two Z-axis Ø8 circular patches are ends of one rounded slot at the
   case edge, not independent circular fastener holes. Other apparent axes are
   outer rounds or concentric stages of existing openings. This also considers
   noncircular closed loops, not just circles.
3. On the common rear face there are seven hole centres: four at (±11.5, ±29)
   for the Pi, two at (32.5, ±18.25), and the central one at (31.625, 0).
   Exhaustively tested **all 35 four-centre combinations** using the four equal
   sides and two equal √2 diagonals criterion, including mixed diameters and
   rotated squares. **Zero** matched within 0.01 mm² squared-distance
   tolerance. The Pi pattern is **23 × 58**, not a square. Other faces have
   subsets of these Y-axis centres or the three X-face slots, so cannot add a
   four-centre pattern. This is a geometry finding, not a claim about an
   unexported cover, assembly or different revision.

## Pilot purpose — inference, not a design fact

The symmetric 36.50 mm spacing, location on the two raised end areas, Ø4.5
front countersinks and continuous threaded paths are consistent with a
**two-point fastening interface**, perhaps for a cover or a separate piece
attached on either side. The front cones could receive countersunk screw heads.
Nothing in this STEP identifies the original mating piece, screw direction,
length, or whether these holes actually secured the speaker. In particular,
the former inference of a rear-only bracket because of a 1.21 mm web is not
supported. A front lid must still be designed around the actual raised surfaces,
hole geometry and engagement; no attachment has been physically tested.

## Driver sizes and available depth

For a **full rectangular envelope confined to the conservative speaker-side
span**, X 17.15–48.25 and Z −14.0625–14.0625, from the Y 2.5 central floor
to the Y 15.5 reference plane, the nominal box is **31.10 × 28.125 × 13.00**
mm (X × Z × Y). It is open to the neighbouring bay at its −X side and has no
wall above Y 8.5 at the outer side or ends. Thus this is a useful bounded
*inside-footprint* comparison, not an assertion that all possible overhanging
or partially recessed speakers are impossible.

* A square with its full depth below Y 8.5 is limited by Z to **28.125 mm**:
  `min(31.10, 28.125) = 28.125`. A rotation does not improve this for a square:
  each axis-aligned projection is `s × (|cos θ| + |sin θ|) ≥ s`. At exactly
  28.125 there is no Z clearance; with 0.20 mm clearance at each end the limit
  is **27.725 mm**. An axis-aligned 28 × 28 square has 0.0625 mm Z clearance
  per end and 1.55 mm X clearance per side if centred. The headless geometry
  test below clears 28 × 28 × 12.9 mm and finds an intersection for
  28.2 × 28.2 × 12.9 mm. These boxes exclude terminals, mounting tabs,
  tolerances and mounting hardware. The central Ø18/Ø20 recess may accommodate
  an appropriately shaped deeper magnet; it does not grant extra depth to a
  full rectangular driver.
* The formerly reported 7 mm is the gap `15.5 − 8.5` **above the raised
  shoulders**, not central-pocket depth. A flat component resting on those
  shoulders may span them but would be above the central lower recess, may
  overhang the body, and has only 7 mm before the Pi-side reference plane. A
  square 40 mm footprint exceeds 31.10 by **8.90** and 28.125 by **11.875**;
  it cannot be entirely inside the defined speaker-side lower footprint. This
  does **not** exclude a 40 mm driver with a smaller rear body, or a larger
  driver mounted outside/on a separate baffle.
* The [ten catalog envelopes](../../models/components/speaker-candidates/README.md)
  are in `models/components/`, not actual drivers in `models/parts/`. None fits
  the full confined box: the round models are Ø40, Ø50, Ø64, Ø68 and Ø78;
  the two square models are 58.5 and 66.5; and the three enclosed Adafruit
  modules are 70 × 30/31 × 17. Each exceeds the 28.125 mm Z span and/or
  13 mm depth. The catalogue's cylinders are simplified envelopes and vendor
  dimensions, not physical fit measurements.
* The [DWEII module envelopes](../../models/components/dweii-speakers/README.md),
  carried by designs in `models/parts/`, are 44 × 28 × 15 for 671 and the
  inherited 664 assumption, and 100 × 45 × 21 for 462. None fits the full
  confined box. For 44 × 28, even the plan areas demonstrate impossibility
  within that footprint at any rotation: `44 × 28 = 1232 > 31.10 × 28.125 =
  874.6875 mm²`; its full 15 mm depth also exceeds 13 by 2 mm. The seller's
  **conflicting** 31 × 28 × 15 alternative for 671 has nominal plan clearance
  only 0.10 and 0.125 mm total, and still exceeds depth by 2 mm; the test box
  31 × 28 × 12.9 clears, but this is not a fit claim for the actual module.
  The 664 size is inherited, not measured; 462 exceeds both plan and depth.
* The lid's **hypothetical** Ø28 × 10 bare driver in
  [the lid concept](../../models/parts/rpispeaker-v17-lid/README.md) fits the
  central *bounding dimensions* with 0.125 mm total Z clearance and 3 mm depth
  to spare; it is not an identified real square candidate and the existing lid
  actually places it outside the body. No retention, wiring or fit is proven.

## What a photograph would settle

A clear photograph of the assembled original **with the cover off**, showing
the whole speaker, its four screws, their heads and what each screw enters,
would distinguish speaker-frame screws from cover or case screws; reveal the
actual speaker position/orientation, any separate carrier, lid, tabs or nuts,
and whether and how the two existing holes are used. The single STEP body
cannot establish those missing parts or the as-built arrangement. A scale or
measurements of the speaker and screw pitch would help; a photo alone may not
resolve exact dimensions or hidden thread engagement.

## Reproduction and observed output

Commands below ran on 2026-11-15 from `/home/james/Projects/debra`. They read
the OneDrive STEP only. The CLI scripts use Linux anonymous `memfd` files; no
script or model is saved and no MCP or open SolidCraft window is contacted.
The output shown for the interference tests is exactly what the Python commands
print; the latter deliberately reports only the first line of a long kernel
failure. The failed checks are **unchecked**, not passes. No physical fit,
printing, or hardware operation was performed.

### Source and digest

```sh
test -f /home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step && ls -lh /home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step
sha256sum /home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step
```

```text
-rw-r--r--. 1 james james 1.7M May 18  2025 /home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step
fa617a4d0e4afdb1c00c804519718ba6cefeaf8b7c07af65e7c43177ccb66991  /home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step
```

### Headless import and warning

```sh
solidcraft-cli eval --in /home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step | python3 -B -c 'import json,sys; d=json.load(sys.stdin); print("body_count:",d["body_count"],"closed:",d["bodies"][0]["closed"],"volume_mm3:",d["total"]["volume_mm3"]); print("import warning:",d["timeline"][0]["warning"])'
```

```text
body_count: 1 closed: True volume_mm3: 15282.410497647837
import warning: solid 'Body45': 3 edges lie off their faces' surfaces by more than 0.01 mm: their tolerances are the gaps they have (up to 1.014e-2 mm)
```

### Exhaustive cylindrical axes, planar inner loops and square search

```sh
python3 -B - <<'PY'
from tools.cad.step_inspect import Step
from collections import Counter,defaultdict
from itertools import combinations
s=Step('/home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step');v=s.vertices()
faces=[(i,s.refs(b)) for i,(t,b) in s.ents.items() if t=='ADVANCED_FACE']
print('STEP solids:',len(s.solids()),'advanced faces:',len(faces),'surface types:',dict(Counter(s.ents[r[-1]][0] for _,r in faces)))
axes=defaultdict(set); loops=Counter(); rear=[]; splines=Counter()
for fi,r in faces:
 typ,b=s.ents[r[-1]]
 if typ=='CYLINDRICAL_SURFACE':
  p,n=s.axis(s.refs(b)[0]);k=max(range(3),key=lambda j:abs(n[j]));axes[('XYZ'[k],)+tuple(round(p[j],3) for j in range(3) if j!=k)].add(round(2*s.nums(b)[-1],4))
 if typ=='B_SPLINE_SURFACE_WITH_KNOTS':
  pts=[]
  for bd in r[:-1]:
   for oe in s.refs(s.ents[s.refs(s.ents[bd][1])[0]][1]):
    ec=s.refs(s.ents[oe][1])[-1];pts.extend(v[q] for q in s.refs(s.ents[ec][1])[:2])
  label='bay threads' if all(31.1<=p[0]<=33.9 and 16.8<=abs(p[2])<=19.7 for p in pts) else 'Pi threads' if all(10.1<=abs(p[0])<=12.9 and 27.6<=abs(p[2])<=30.4 for p in pts) else 'other'
  splines[label]+=1
 if typ!='PLANE':continue
 p,n=s.axis(s.refs(b)[0]);k=max(range(3),key=lambda j:abs(n[j]))
 for bd in r[:-1]:
  if s.ents[bd][0]!='FACE_BOUND':continue
  curves=[];circle_centres=set()
  for oe in s.refs(s.ents[s.refs(s.ents[bd][1])[0]][1]):
   ec=s.refs(s.ents[oe][1])[-1];ct,cb=s.ents[s.refs(s.ents[ec][1])[2]];curves.append(ct)
   if ct=='CIRCLE':
    q,ax=s.axis(s.refs(cb)[0]);circle_centres.add((round(q[0],3),round(q[2],3)))
  loops[('XYZ'[k],round(p[k],3),'circular/threaded' if circle_centres else 'noncircular')]+=1
  if k==1 and abs(p[1]+.6)<1e-5:
   assert len(circle_centres)==1
   rear.extend(circle_centres)
print('All cylindrical surface axes and diameters (axis, transverse centre):')
for key,ds in sorted(axes.items()):print(' ',key,sorted(ds))
print('Spline face boundary groups:',dict(splines))
print('All planar inner-loop counts (normal axis, offset, type):')
for k,count in sorted(loops.items()):print(' ',k,count)
print('Back face hole centres (X,Z):',sorted(rear))
squares=[]
for g in combinations(rear,4):
 d=sorted((a[0]-b[0])**2+(a[1]-b[1])**2 for a,b in combinations(g,2))
 if d[0]>0 and max(abs(x-d[0]) for x in d[:4])<.01 and abs(d[4]-2*d[0])<.01 and abs(d[5]-2*d[0])<.01:squares.append(g)
print('Rear face 4-centre combinations:',len(list(combinations(rear,4))),'squares:',squares,'(squared-distance tolerance 0.01 mm²)')
for fi in [4922,4923,4925,4928,4930,4998,5000,5001,5002,5014,5016,5017,5019,5047]:
 typ,b=s.ents[s.refs(s.ents[fi][1])[-1]];p,n=s.axis(s.refs(b)[0]); print('Face',fi,typ,'origin',tuple(round(x,5) for x in p),'axis',tuple(round(x,3) for x in n))
PY
```

```text
STEP solids: 1 advanced faces: 262 surface types: {'CYLINDRICAL_SURFACE': 154, 'PLANE': 76, 'B_SPLINE_SURFACE_WITH_KNOTS': 23, 'CONICAL_SURFACE': 9}
All cylindrical surface axes and diameters (axis, transverse centre):
  ('Y', -11.5, -29.0) [2.0755, 2.1755, 2.58, 2.68, 7.0]
  ('Y', -11.5, 29.0) [2.0755, 2.1755, 2.58, 2.68, 7.0]
  ('Y', 11.5, -29.0) [2.1755, 2.68]
  ('Y', 11.5, 29.0) [2.1755, 2.68, 7.0]
  ('Y', 13.15, -33.65) [8.0]
  ('Y', 13.15, 33.65) [8.0]
  ('Y', 28.15, -33.0) [22.0]
  ('Y', 28.15, 33.0) [22.0]
  ('Y', 31.625, -0.0) [10.0, 18.0]
  ('Y', 32.5, -18.25) [2.1755, 2.68]
  ('Y', 32.5, 18.25) [2.1755, 2.68]
  ('Y', 38.0, -11.0) [22.0]
  ('Y', 38.0, 11.0) [22.0]
  ('Z', -0.85, 4.5) [8.0]
  ('Z', 3.65, 4.5) [8.0]
Spline face boundary groups: {'bay threads': 4, 'Pi threads': 19}
All planar inner-loop counts (normal axis, offset, type):
  ('X', -17.15, 'noncircular') 3
  ('X', -15.75, 'noncircular') 3
  ('Y', -0.6, 'circular/threaded') 7
  ('Y', 0.0, 'circular/threaded') 1
  ('Y', 2.5, 'circular/threaded') 5
  ('Y', 8.5, 'circular/threaded') 2
  ('Y', 15.5, 'circular/threaded') 2
Back face hole centres (X,Z): [(-11.5, -29.0), (-11.5, 29.0), (11.5, -29.0), (11.5, 29.0), (31.625, -0.0), (32.5, -18.25), (32.5, 18.25)]
Rear face 4-centre combinations: 35 squares: [] (squared-distance tolerance 0.01 mm²)
Face 4922 CYLINDRICAL_SURFACE origin (32.5, 0.0, 18.25) axis (0.0, 1.0, 0.0)
Face 4923 PLANE origin (32.5, 7.28775, 18.25) axis (0.0, 1.0, 0.0)
Face 4925 CONICAL_SURFACE origin (32.5, 8.0, 18.25) axis (0.0, 1.0, 0.0)
Face 4928 PLANE origin (32.5, 7.28775, -18.25) axis (0.0, 1.0, 0.0)
Face 4930 CONICAL_SURFACE origin (32.5, 8.0, -18.25) axis (0.0, 1.0, 0.0)
Face 4998 PLANE origin (32.375, 8.5, -0.0) axis (0.0, 1.0, 0.0)
Face 5000 CONICAL_SURFACE origin (31.625, 2.0, -0.0) axis (0.0, 1.0, 0.0)
Face 5001 PLANE origin (-16.45, 2.5, -4.675) axis (0.0, 1.0, 0.0)
Face 5002 CYLINDRICAL_SURFACE origin (31.625, 0.0, -0.0) axis (0.0, 1.0, 0.0)
Face 5014 PLANE origin (-16.45, 0.0, -4.675) axis (0.0, 1.0, 0.0)
Face 5016 CYLINDRICAL_SURFACE origin (31.625, 0.0, -0.0) axis (0.0, -1.0, 0.0)
Face 5017 PLANE origin (48.25, 2.5, -14.0625) axis (-1.0, 0.0, 0.0)
Face 5019 PLANE origin (15.75, 2.5, -14.0625) axis (0.0, 0.0, 1.0)
Face 5047 PLANE origin (17.15, 2.5, 14.0625) axis (-0.0, 0.0, -1.0)
```

The remaining nine conical faces have no additional axes:

```sh
python3 -B - <<'PY'
from tools.cad.step_inspect import Step
from collections import defaultdict
s=Step('/home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step'); g=defaultdict(list)
for i,(t,b) in s.ents.items():
 if t!='ADVANCED_FACE':continue
 r=s.refs(b);typ,body=s.ents[r[-1]]
 if typ!='CONICAL_SURFACE':continue
 p,n=s.axis(s.refs(body)[0]);k=max(range(3),key=lambda j:abs(n[j]));g[('XYZ'[k],)+tuple(round(p[j],3) for j in range(3) if j!=k)].append(i)
print('All conical axes (axis, transverse centre) and face IDs:')
for k,ids in sorted(g.items()): print(' ',k,ids)
PY
```

```text
All conical axes (axis, transverse centre) and face IDs:
  ('Y', -11.5, -29.0) [4939, 5008]
  ('Y', -11.5, 29.0) [5009, 5011]
  ('Y', 11.5, -29.0) [4952]
  ('Y', 11.5, 29.0) [5013]
  ('Y', 31.625, -0.0) [5000]
  ('Y', 32.5, -18.25) [4930]
  ('Y', 32.5, 18.25) [4925]
```

### Selected face boundary geometry

The face numbers are STEP entity IDs. A circle on an outer boundary may be a
round, not a hole; `FACE_BOUND` identifies the inner loops. The Y 7.28775
partial faces have mixed arc/spline boundaries; the independent full-axis probes
below resolve whether they cap the holes.

```sh
python3 -B - <<'PY'
from tools.cad.step_inspect import Step
s=Step('/home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step'); v=s.vertices()
for fi in [4922,4923,4925,4928,4930,4998,5000,5001,5002,5014,5016,5017,5019,5047]:
 r=s.refs(s.ents[fi][1]);typ,b=s.ents[r[-1]];print('face',fi,typ)
 for bd in r[:-1]:
  circles=[]; lines=[]
  for oe in s.refs(s.ents[s.refs(s.ents[bd][1])[0]][1]):
   ec=s.refs(s.ents[oe][1])[-1];q=s.refs(s.ents[ec][1]);ct,cb=s.ents[q[2]]
   if ct=='CIRCLE':
    p,n=s.axis(s.refs(cb)[0]);circles.append((tuple(round(x,5) for x in p),round(s.nums(cb)[-1]*2,5)))
   elif ct=='LINE' and fi in [5017,5019,5047]:lines.append(tuple(tuple(round(x,5) for x in v[w]) for w in q[:2]))
  if circles:print(' ',s.ents[bd][0],'circles',circles)
  if lines:print(' ',s.ents[bd][0],'lines',lines)
PY
```

```text
face 4922 CYLINDRICAL_SURFACE
  FACE_OUTER_BOUND circles [((32.5, 7.33775, 18.25), 2.1755), ((32.5, 7.28775, 18.25), 2.1755), ((32.5, 7.28775, 18.25), 2.1755)]
face 4923 PLANE
  FACE_OUTER_BOUND circles [((32.5, 7.28775, 18.25), 2.1755), ((32.5, 7.28775, 18.25), 2.1755), ((32.5, 7.28775, 18.25), 2.68)]
face 4925 CONICAL_SURFACE
  FACE_OUTER_BOUND circles [((32.5, 8.5, 18.25), 4.5), ((32.5, 7.33775, 18.25), 2.1755)]
face 4928 PLANE
  FACE_OUTER_BOUND circles [((32.5, 7.28775, -18.25), 2.1755), ((32.5, 7.28775, -18.25), 2.1755), ((32.5, 7.28775, -18.25), 2.68)]
face 4930 CONICAL_SURFACE
  FACE_OUTER_BOUND circles [((32.5, 8.5, -18.25), 4.5), ((32.5, 7.33775, -18.25), 2.1755)]
face 4998 PLANE
  FACE_OUTER_BOUND circles [((38.0, 8.5, 11.0), 22.0), ((38.0, 8.5, -11.0), 22.0), ((28.15, 8.5, -33.0), 22.0), ((28.15, 8.5, 33.0), 22.0)]
  FACE_BOUND circles [((32.5, 8.5, -18.25), 4.5)]
  FACE_BOUND circles [((32.5, 8.5, 18.25), 4.5)]
face 5000 CONICAL_SURFACE
  FACE_OUTER_BOUND circles [((31.625, 2.5, -0.0), 20.0), ((31.625, 1.5, -0.0), 18.0)]
face 5001 PLANE
  FACE_OUTER_BOUND circles [((11.5, 2.5, 29.0), 7.0)]
  FACE_BOUND circles [((-11.5, 2.5, -29.0), 4.75)]
  FACE_BOUND circles [((11.5, 2.5, -29.0), 4.75)]
  FACE_BOUND circles [((11.5, 2.5, 29.0), 4.75)]
  FACE_BOUND circles [((31.625, 2.5, -0.0), 20.0)]
face 5002 CYLINDRICAL_SURFACE
  FACE_OUTER_BOUND circles [((31.625, 1.5, -0.0), 18.0), ((31.625, 0.0, -0.0), 18.0)]
face 5014 PLANE
  FACE_OUTER_BOUND circles [((31.625, 0.0, -0.0), 18.0)]
  FACE_BOUND circles [((31.625, 0.0, -0.0), 10.0)]
face 5016 CYLINDRICAL_SURFACE
  FACE_OUTER_BOUND circles [((31.625, -0.6, -0.0), 10.0), ((31.625, 0.0, -0.0), 10.0)]
face 5017 PLANE
  FACE_OUTER_BOUND lines [((48.25, 2.5, 14.0625), (48.25, 2.5, -14.0625)), ((48.25, 2.5, 14.0625), (48.25, 8.5, 14.0625)), ((48.25, 8.5, -14.0625), (48.25, 8.5, 14.0625)), ((48.25, 2.5, -14.0625), (48.25, 8.5, -14.0625))]
face 5019 PLANE
  FACE_OUTER_BOUND lines [((17.15, 8.5, -14.0625), (17.15, 15.5, -14.0625)), ((15.75, 15.5, -14.0625), (17.15, 15.5, -14.0625)), ((15.75, 2.5, -14.0625), (15.75, 15.5, -14.0625)), ((48.25, 2.5, -14.0625), (15.75, 2.5, -14.0625)), ((48.25, 2.5, -14.0625), (48.25, 8.5, -14.0625)), ((17.15, 8.5, -14.0625), (48.25, 8.5, -14.0625))]
face 5047 PLANE
  FACE_OUTER_BOUND lines [((15.75, 2.5, 14.0625), (15.75, 15.5, 14.0625)), ((17.15, 15.5, 14.0625), (15.75, 15.5, 14.0625)), ((17.15, 8.5, 14.0625), (17.15, 15.5, 14.0625)), ((48.25, 8.5, 14.0625), (17.15, 8.5, 14.0625)), ((48.25, 2.5, 14.0625), (48.25, 8.5, 14.0625)), ((15.75, 2.5, 14.0625), (48.25, 2.5, 14.0625))]
```

### Independent full-axis probes

```sh
python3 -B - <<'PY'
import os,subprocess,json
p='/home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step'
names=[('ProbeMinus',32.5,-18.25),('ProbePlus',32.5,18.25),('Control',37.5,18.25)]
steps=[{'command':'solid.cylinder','params':{'diameter':2,'height':9.3,'base':[x,-.7,z],'axis':'Y','operation':'new','name':n,'body_name':n}} for n,x,z in names]
steps.append({'command':'inspect.interference','params':{'bodies':['RPiSpeaker v17']+[n for n,_,_ in names]}})
fd=os.memfd_create('audit.json',0);os.write(fd,json.dumps(steps).encode())
r=subprocess.run(['solidcraft-cli','run',f'/proc/self/fd/{fd}','--in',p,'--results'],close_fds=False,text=True,capture_output=True,check=True);q=json.loads(r.stdout)[-1]
print('Probe cylinders Ø2.0 mm from Y=-0.7 to 8.6 at pilot axes; control at X=37.5 Z=18.25')
print('checked:',q['checked'],'overlaps:',q['count'],'unchecked:',len(q['unchecked']),'truncated:',q['truncated'],'pairs_cleared:',q['pairs_cleared'])
for a in q['unchecked']:print('unchecked pair:',a['a'],a['b'],'reason:',a['reason'].splitlines()[0])
for h in q['interferences']:print('overlap:',h['a'],h['b'],'volume_mm3:',round(h['volume_mm3'],6))
PY
```

```text
Probe cylinders Ø2.0 mm from Y=-0.7 to 8.6 at pilot axes; control at X=37.5 Z=18.25
checked: 4 overlaps: 1 unchecked: 0 truncated: False pairs_cleared: 2
overlap: RPiSpeaker v17 Control volume_mm3: 28.588493
```

Both pilot probes were cleared by the CLI's mesh pruning, and the separate
control was boolean-intersected. This supports the boundary analysis; it is not
a physical drilling or a fit test. The model import warns about edge tolerances.

### Repeated thread vertices

```sh
python3 -B - <<'PY'
from tools.cad.step_inspect import Step
from collections import defaultdict,Counter
s=Step('/home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step'); v=s.vertices(); groups=defaultdict(set)
for x,y,z in v.values():
 if (x-32.5)**2+(z-18.25)**2<1.35**2 and -0.6001<=y<=7.338:
  groups[(round(x,3),round(z,3))].add(round(y,4))
c=Counter()
for p,ys in groups.items():
 if len(ys)>1:
  ys=sorted(ys)
  for a,b in zip(ys,ys[1:]):
   if b-a>.1:c[round(b-a,3)]+=1
print('Recurrent same-(X,Z) vertex vertical spacings mm:',c.most_common(10))
print('Example repeated vertex levels:')
for p,ys in groups.items():
 if len(ys)>=5:
  print(p,sorted(ys)); break
PY
```

```text
Recurrent same-(X,Z) vertex vertical spacings mm: [(0.354, 9), (0.387, 7), (0.45, 4), (1.8, 4), (4.95, 3), (4.05, 1), (0.996, 1), (3.504, 1), (6.75, 1), (1.35, 1)]
Example repeated vertex levels:
(32.5, 16.91) [0.8147, 1.8103, 2.2603, 2.6147, 2.7103, 3.0647, 3.1603, 3.5147, 3.6103, 4.0603, 4.4147, 4.5103, 4.8647, 4.9603, 5.3147, 5.4103, 5.7647]
```

### Envelope collision tests

```sh
python3 -B - <<'PY'
import os,subprocess,json
p='/home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step'
tests=[('Square28',28,28),('Square28_2',28.2,28.2),('Module31x28',31,28),('Module28x44',28,44),('Square40',40,40)]
steps=[]
for name,x,z in tests:
 steps.extend([{'command':'solid.box','params':{'length':x,'width':12.9,'height':z,'center':[32.7,9,0],'operation':'new','name':name,'body_name':name}},{'command':'inspect.interference','params':{'bodies':['RPiSpeaker v17',name]}}])
fd=os.memfd_create('audit.json',0);os.write(fd,json.dumps(steps).encode())
r=subprocess.run(['solidcraft-cli','run',f'/proc/self/fd/{fd}','--in',p,'--results'],close_fds=False,text=True,capture_output=True,check=True)
results=json.loads(r.stdout)
for i,(name,x,z) in enumerate(tests):
 a=results[2*i+1];print(name,'X,Y,Z=',(x,12.9,z),'center=(32.7,9,0)','intersections=',a['count'],'unchecked=',len(a['unchecked']),'overlap_mm3=',[round(v['volume_mm3'],5) for v in a['interferences']])
 for u in a['unchecked']:print('  unchecked reason:',u['reason'].splitlines()[0])
PY
```

```text
Square28 X,Y,Z= (28, 12.9, 28) center=(32.7,9,0) intersections= 0 unchecked= 0 overlap_mm3= []
Square28_2 X,Y,Z= (28.2, 12.9, 28.2) center=(32.7,9,0) intersections= 1 unchecked= 0 overlap_mm3= [12.58425]
Module31x28 X,Y,Z= (31, 12.9, 28) center=(32.7,9,0) intersections= 0 unchecked= 0 overlap_mm3= []
Module28x44 X,Y,Z= (28, 12.9, 44) center=(32.7,9,0) intersections= 0 unchecked= 1 overlap_mm3= []
  unchecked reason: the operation failed: SMLib boolean: SMLib's check refuses the result (the first operand already fails it): 44 failed tests:
Square40 X,Y,Z= (40, 12.9, 40) center=(32.7,9,0) intersections= 0 unchecked= 1 overlap_mm3= []
  unchecked reason: the operation failed: SMLib boolean: SMLib's check refuses the result (the first operand already fails it): 44 failed tests:
```

The two unchecked results do not establish clearance or collision; their
inside-footprint exclusions above follow from the measured boundaries and
arithmetic, not from those failed booleans.

### Documentation tests

```sh
python3 -B -m unittest tests.test_docs -v
```

```text
test_committed_images_are_referenced (tests.test_docs.AssetTests.test_committed_images_are_referenced)
No orphan renders: an asset folder is for pictures a page shows. ... ok
test_every_referenced_image_exists (tests.test_docs.AssetTests.test_every_referenced_image_exists) ... ok
test_model_folder_links_resolve (tests.test_docs.AssetTests.test_model_folder_links_resolve) ... ok
test_entrypoint_links_and_heading_fragments_resolve (tests.test_docs.FrontDoorTests.test_entrypoint_links_and_heading_fragments_resolve) ... ok
test_historical_readme_section_is_preserved (tests.test_docs.FrontDoorTests.test_historical_readme_section_is_preserved) ... ok
test_readme_routes_to_getting_started_and_preserved_history (tests.test_docs.FrontDoorTests.test_readme_routes_to_getting_started_and_preserved_history) ... ok
test_local_markdown_links_resolve (tests.test_docs.RelativeLinkTests.test_local_markdown_links_resolve) ... ok
test_every_cited_key_is_defined (tests.test_docs.SourceRegisterTests.test_every_cited_key_is_defined) ... ok
test_every_register_entry_has_a_url_and_a_date (tests.test_docs.SourceRegisterTests.test_every_register_entry_has_a_url_and_a_date) ... ok
test_register_keys_are_unique (tests.test_docs.SourceRegisterTests.test_register_keys_are_unique) ... ok
test_sources_page_exists_and_has_rows (tests.test_docs.SourceRegisterTests.test_sources_page_exists_and_has_rows) ... ok

----------------------------------------------------------------------
Ran 11 tests in 0.040s

OK
```

## Handoff

Review this correction against the STEP and the original assembly before using
it for manufacture. Existing design pages and the lid concept still contain
the superseded 66 × 7 and blind-pilot assumptions; updating them is outside
this worker's scope. Request the cover-off photograph and actual driver
measurements before settling attachment, clearance or screw selection. No
render was produced and no commit or push was made.
