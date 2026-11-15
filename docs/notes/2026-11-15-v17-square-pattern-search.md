---
title: RPiSpeaker v17 broader square-pattern search
date: 2026-11-15
type: project-learning
status: unreviewed
task: v17 square-pattern search
author: OpenCode subagent
author_model: openrouter/openai/gpt-6.1-terra
author_variant: unknown
sources:
  - /home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step
  - docs/notes/2026-11-15-rpispeaker-v17-bay-inventory.md
---

# v17 broader square-pattern search

## Verdict: inconclusive

James reports that his original has a four-screw square speaker mount. The
earlier [bay inventory](2026-11-15-rpispeaker-v17-bay-inventory.md) did not
establish its claimed negative: its explicit combinatorial test covered only
seven hole centres on the rear face. This independent, wider **headless
SolidCraft CLI** search finds **no four equal-radius square** among the
extracted cylindrical axes or coplanar circular-edge centres at the tolerances
below. Four near-square **wall-region candidates** were found and examined;
none is a demonstrated four-screw pattern. This is not yet a complete search
of all possible slotted tabs, interrupted pockets, noncircular protrusions,
or blended surfaces, so the existence of James's mount in this file remains
**inconclusive**, not disproved. A photo is not a prerequisite for continuing
the geometry investigation.

Source: original STEP at the absolute path in the frontmatter; SHA-256
`fa617a4d0e4afdb1c00c804519718ba6cefeaf8b7c07af65e7c43177ccb66991` on
2026-11-15. It was read only; no SolidCraft window or SolidCraft MCP was used.
Coordinates are STEP world mm, X across, Z along, +Y forward. The CLI imports
one closed body, with no second body to occlude a candidate; self-occlusion by
the same body has not been comprehensively tested. Three imported edges deviate
from their surfaces by up to 0.01014 mm. CAD geometry is not a physical fit test.

## What was searched and raw counts

* `eval`: **262 kernel face patches**, **776 kernel edges**; separately the
  CLI's summary reports **143 faces**, **419 edges** after consolidation.
  Summary types: 76 planes, 35 cylinders, 9 cones, 23 other. Do not add the
  two sets of counts. Per-patch `selection.get` instead classifies 77 as plane,
  154 cylinder, 9 cone and 22 other: one patch is classified differently by
  this geometry query. All 262 were selected, in chunks; all 776 edge details
  were returned. A single `selection.get` resolves only the first 500 edge
  items here, so chunking is essential.
* All **154 cylindrical patches** produced **15 axis lines**: 13 parallel to Y
  and 2 parallel to Z; none parallel to X. Across all depths, the search tests
  four distinct parallel axes with radii differing by at most **0.25 mm**,
  including holes, outer rounds, posts and bosses without assuming polarity.
  **125** Y-axis equal-radius quartets, **0** X and **0** Z were tested; **0**
  passed the distance screen. Some quartets differ only by nearly equal thread
  radii; this is a raw combination count, not 125 distinct features.
* All **20 circular and 66 arc edges** were queried; **85** with arc sweep at
  least 5° were used for the round-edge screen. Their centres and radii were
  grouped by plane within 0.05 mm and normal within 1°, then near-duplicate
  centres within 0.03 mm and radii within 0.02 mm collapsed. The greedy grouping
  yielded 31 groups, 83 centre-radius records, and **21** same-radius quartets;
  **0** passed the square screen. Circles and arcs include outside fillets,
  recess rims and counterbores, not only holes. This grouping can split
  borderline cases and CLI arc classification can approximate a spline.
* For both screens, four sides may deviate **0.50 mm from their mean** and
  diagonals **0.70 mm from √2 times that mean**. Two derived angle checks use
  **3°** from a right angle for the coplanar-edge screen; the cylinder-axis
  screen uses only side and diagonal tests. Angles are not constrained to 0°
  or 45°: any orientation passes these distance tests. The 0.50 mm tolerance is
  intentionally wide; exact dimensions below distinguish false positives.
* Every face reported planar was inspected through its edge endpoints. **46**
  closed four-line loops were screened with those broad side/diagonal/angle
  limits; **2** were near-square. A separate screen of all endpoint quartets
  on each planar face, including disconnected edges, compares the two other
  corners to the ideal square within **0.50 mm**, any orientation and minimum
  side **2 mm**: **2** more near-square regions. These are the four candidates
  below. This endpoint test is not an exhaustive slot or pocket recognizer;
  it does not fit arbitrarily split or curved outlines.
* The prior seven rear openings are the six threaded axes plus the central
  stepped opening, **not seven new holes on each face**. This pass did not
  independently count every hole loop on all planar faces; the earlier inventory
  lists 23 planar inner loops across levels, including repeated openings on
  opposite sides. It reported three connector windows on each of two X faces,
  seven rear openings, and ten additional circular/threaded openings on
  other Y faces. Those are loop counts, not a count of independent holes.
* The nine conical faces lie on the six threaded axes and the central bore.
  For the 22 faces reported `other`, all sampled boundary endpoints, edge
  midpoints and one face point lie within **1.343 mm** of one of the six
  threaded axes. Sampling does not bound the interiors mathematically. The
  one differently classified patch and any curvature between sampled points
  remain limitations.

The following planar groups identify **all 77 query-classified planar face
patches** (numbers are zero-based `model.faces` indices, not STEP entity IDs).
They are an enumeration, not a claim that each patch is a separate pocket.
The angled entries have normals approximately `(0.342,-0.940,0)` or
`(0,-0.940,±0.342)`.

| Plane/offset, mm | Face indices |
| --- | --- |
| X −17.15; −15.75; −15 | 261; 202; 220, 227, 246, 255 |
| X −8; −4.85; 7.65; 8 | 222, 225, 249; 183; 258; 250 |
| X 15; 15.75; 17.15; 48.25; 49 | 253; 215, 243; 189, 217; 214; 259 |
| Y −0.6; 0; 1.1627; 2.5; 3.5 | 186; 211, 212; 130, 134, 139, 147; 198, 209; 234, 238, 239 |
| Y 7.2877; 7.5; 8.5; 11.9192 | 120, 125; 230, 231; 181, 195, 229; 155, 162, 172 |
| Y 12.5; 14.1628; 15.5 | 167, 223; 143, 164; 188 |
| Z −37.65; −35.5; −33.25; −32.5 | 185; 232; 201, 242; 257 |
| Z −26.1; −25.5; −22; −14.1; −14.0625 | 226, 233, 256; 228, 254; 191; 241; 216 |
| Z 4.75; 13.75; 14.0625; 17; 22 | 240; 237; 244; 236; 194 |
| Z 25.5; 26; 34; 37.65 | 219, 247, 252; 221, 235, 245; 204; 260 |
| Angled | 166, 175, 178, 200, 203 |

## Candidates and practical meaning

The **four raw near-square wall candidates** below are not four-screw mounts:
their measured points are wall corners, not four holes, posts or tabs. Their
corner diameters do not exist. No speaker dimensions, screw-head diameter or
fastener type were provided, so neither head clearance nor mounting suitability
can be certified. No added-body occlusion exists in the one-body STEP; clearance
against the body itself and screw tool paths are **not tested**. Wall thickness
at these particular patches is also **not measured**, except for the adjacent
1.40 mm outer X wall where noted; do not assume it applies everywhere.

| Candidate, plane | Exact corner coordinates (X,Y,Z), mm | Dimensions and orientation | Assessment |
| --- | --- | --- | --- |
| Face 191, Z −22 | (28.15,−0.60,−22), (38,−0.60,−22), (28.15,8.50,−22), (38,8.50,−22) | Four-edge face, **9.85 × 9.10**, sides along X/Y (0°); difference 0.75 | No circles or screw openings on this face; a solid wall between outer rounds, not a square four-screw mount. Head clearance and local thickness untested. |
| Face 194, Z +22 | (28.15,−0.60,22), (38,−0.60,22), (28.15,8.50,22), (38,8.50,22) | **9.85 × 9.10**, X/Y (0°) | Same assessment. |
| Face 202 region, X −15.75 | (−15.75,10.75,34), (−15.75,10.75,26), (−15.75,2.50,34), (−15.75,2.50,26) | **8.00 × 8.25**, Z/Y (0°) | Three boundary segments but no fourth segment between the near-square corners; part of the continuous inner side wall, not a closed pocket or four screw features. Adjacent outer wall X −17.15 gives nominal **1.40 mm** locally, not measured head clearance. |
| Face 204 region, Z +34 | (−15.75,2.50,34), (−15.75,10.75,34), (−8,10.75,34), (−8,2.50,34) | **7.75 × 8.25**, X/Y (0°) | Three boundary segments, fourth side not an edge; part of an end wall, not four screw features. Head clearance and local thickness untested. |

Other prominent four-centre sets fail even the wide screen: the four threaded
axes `(±11.5, ±29)` have **23 × 58 mm** spacing, not square; the four R11
outside-curve centres `(28.15,±33)` and `(38,±11)` are not a square. The six
threaded axes have approximately Ø2.1755 mm core; the two at `(32.5,±18.25)`
have Ø4.50 countersinks and **36.50 mm** spacing. The two by themselves do not
establish a four-point mount. Individual head clearance, engagement and speaker
fit have not been tested.

## Bays, slots and steps identified

These dimensions are directly reported from CLI planes/edges or the cited bay
inventory; they are **not a complete inventory of every small rib or valley**.
The latter requires connected-loop/face-adjacency analysis beyond the screens
above. Positions and levels are nominal, not material clearances.

| Feature | Dimensions / location |
| --- | --- |
| Pi-side bay | Reference inner walls X −15.75 to 15.75, Z −32.50 to 34.00; span **31.50 × 66.50**. Floors/steps include Y 0 and 2.5, upper reference Y 15.5; wall outlines change and this is not a uniform rectangular pocket. |
| Pi-side lower level | Main straight edge references X ±15 and Z ±25.5 at Y 0, with additional end/side steps. Approximate reference rectangle **30 × 51**; not asserted to be an uninterrupted closed pocket. |
| Speaker-side lower region | Reference X 17.15–48.25, Z ±14.0625: **31.10 × 28.125**. Floor Y 2.5, end and outer walls up to Y 8.5, reference Y 15.5. It opens toward the Pi bay; it is not a fully enclosed rectangular pocket. Outer wall locally **0.75** thick at X 48.25–49. |
| Central stepped opening | Axis `(31.625, *, 0)`: Ø10 Y −0.6–0; Ø18 Y 0–1.5; flared Ø18→Ø20 Y 1.5–2.5. |
| Three side connector windows | Through X −17.15 to −15.75: Y 3.5–8.5, Z −26.1–−14.1 (**5 × 12**); Y 3.5–7.5, Z 4.75–13.75 and 17–26 (**4 × 9** each). |
| Rounded end opening | Z −37.65 to −35.5, 12.5 mm wide: X −4.85–7.65, with two R4 arc centres `(−0.85,4.5)` and `(3.65,4.5)` in the XY plane; not two separate screw holes. |
| Raised speaker-side surface | Y 8.5, outline Z −33 to 33 with four R11 outline arcs; it is raised material, not a 66 mm-long rectangular pocket. |

## Reproduce the search

Run from the repository root. The script uses anonymous in-memory command
files and invokes `solidcraft-cli` without `--save`. It selects in chunks and
prints the plane groups and candidates, including face indices; the source
file is never written. The angle test uses sorted distances as a broad screen,
not a proof of true rectangular adjacency. A line cycle is required to have
four vertices of degree two; the endpoint screen does not require a cycle.

```sh
python3 -B - <<'PY'
import collections, itertools, json, math, os, re, subprocess
p = '/home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step'
body = 'RPiSpeaker v17'
steps = [{'command': 'model.faces', 'params': {'body': body}},
         {'command': 'model.edges', 'params': {'body': body}}]
for kind, count in [('face', 262), ('edge', 776)]:
    for start in range(0, count, 200):
        steps += [{'command': 'select.set', 'params': {'items': [
            {'type': kind, 'body': body, 'index': i}
            for i in range(start, min(count, start + 200))]}},
            {'command': 'selection.get', 'params': {'detail': True}}]
fd = os.memfd_create('v17-search', 0)
os.write(fd, json.dumps(steps).encode())
out = subprocess.run(['solidcraft-cli', 'run', f'/proc/self/fd/{fd}',
                      '--in', p, '--results'], pass_fds=(fd,), check=True,
                     capture_output=True, text=True)
r = json.loads(out.stdout)
rawfaces, rawedges = r[0]['faces'], r[1]['edges']
faces = r[3]['items'] + r[5]['items']
edges = sum((r[i]['items'] for i in (7, 9, 11, 13)), [])
print('face/edge counts:', len(faces), len(edges),
      'resolved:', sum('surface' in x for x in faces),
      sum('curve' in x for x in edges))
print('face types:', dict(collections.Counter(x['surface']['type'] for x in faces)))
print('edge types:', dict(collections.Counter(x['curve'] for x in edges)))

def sub(a, b): return [x-y for x, y in zip(a, b)]
def norm(a): return math.sqrt(sum(x*x for x in a))
def screen(points, angle=True):
    d = sorted(norm(sub(a, b)) for a, b in itertools.combinations(points, 2))
    s = sum(d[:4])/4
    if s < .5 or max(abs(x-s) for x in d[:4]) > .5: return False
    if max(abs(x-s*math.sqrt(2)) for x in d[4:]) > .7: return False
    return not angle or max(abs((d[i]**2+d[j]**2-d[k]**2)/(2*d[i]*d[j]))
                            for i,j,k in [(0,3,4),(1,2,5)]) <= math.sin(math.radians(3))

planes = collections.defaultdict(list)
for face in faces:
    s = face['surface']
    if s['type'] != 'plane': continue
    n = s['normal']; k = max(range(3), key=lambda j: abs(n[j]))
    key = ('XYZ'[k], round(s['point'][k], 4)) if abs(n[k]) > .999 else ('oblique', tuple(round(x,3) for x in n))
    planes[key].append(face['index'])
for k, v in sorted(planes.items(), key=str): print('plane', k, v)

axes = collections.defaultdict(set)
for f in rawfaces:
    c = f.get('cylinder')
    if not c: continue
    k = max(range(3), key=lambda j: abs(c['axis'][j]))
    axes[('XYZ'[k], tuple(round(c['origin'][j],3) for j in range(3) if j != k))].add(round(c['radius'],4))
print('cylinder patches:', sum(bool(f.get('cylinder')) for f in rawfaces), 'axis lines:', len(axes))
for k, v in sorted(axes.items()): print('axis', k, sorted(v))
for axis in 'XYZ':
    records = [(k[1], rad) for k, vals in axes.items() if k[0] == axis for rad in vals]
    tested = found = 0
    for q in itertools.combinations(records, 4):
        if len({x[0] for x in q}) < 4 or max(x[1] for x in q)-min(x[1] for x in q) > .25: continue
        tested += 1
        if screen([x[0] for x in q], angle=False): found += 1; print('axis candidate', q)
    print(axis, 'axis quartets:', tested, 'candidates:', found)

rounds = [e for e in edges if e['curve'] in ('circle','arc') and e.get('angle_deg',360) >= 5]
groups = []
for e in rounds:
    a = [x/norm(e['axis']) for x in e['axis']]
    k = max(range(3), key=lambda j: abs(a[j]))
    a = [x*(1 if a[k] > 0 else -1) for x in a]
    h = sum(x*y for x,y in zip(a, e['center']))
    for g in groups:
        if sum(x*y for x,y in zip(a,g['axis'])) >= math.cos(math.radians(1)) and abs(h-g['h']) <= .05: break
    else:
        g = {'axis': a, 'h': h, 'items': []}; groups.append(g)
    if not any(norm(sub(e['center'], q['center'])) < .03 and abs(e['radius']-q['radius']) < .02 for q in g['items']): g['items'].append(e)
tested = found = 0
for g in groups:
    for q in itertools.combinations(g['items'], 4):
        if max(e['radius'] for e in q)-min(e['radius'] for e in q) > .25: continue
        tested += 1
        if screen([e['center'] for e in q]): found += 1; print('round candidate', q)
print('round edges/groups/records/quartets/candidates:', len(rounds), len(groups), sum(len(g['items']) for g in groups), tested, found)

adj = collections.defaultdict(list)
for e in rawedges:
    for i in set(map(int, re.findall(r'face:(\d+)', e['name']))): adj[i].append(e)
cycles = vertices = 0
for face in faces:
    if face['surface']['type'] != 'plane': continue
    fid = face['index']
    line = [edges[e['index']] for e in adj[fid] if edges[e['index']]['curve'] == 'line']
    for q in itertools.combinations(line, 4):
        pts = []
        for e in q:
            for pt in (e['start'], e['end']):
                if not any(norm(sub(pt,p)) < .03 for p in pts): pts.append(pt)
        if len(pts) != 4: continue
        if [sum(norm(sub(p,e[k])) < .03 for e in q for k in ('start','end')) for p in pts] != [2]*4: continue
        cycles += 1
        if screen(pts): print('line candidate', fid, [e['index'] for e in q], [tuple(round(x,4) for x in p) for p in pts])
    pts = []
    for e in adj[fid]:
        for pt in (e['start'], e['end']):
            if not any(norm(sub(pt,p)) < .03 for p in pts): pts.append(pt)
    n = face['surface']['normal']; candidates = set()
    for (i,a),(j,c) in itertools.combinations(enumerate(pts),2):
        v = sub(c,a)
        if norm(v) < math.sqrt(2)*2: continue
        u = [n[1]*v[2]-n[2]*v[1], n[2]*v[0]-n[0]*v[2], n[0]*v[1]-n[1]*v[0]]
        mid = [(x+y)/2 for x,y in zip(a,c)]
        p = [x+y/2 for x,y in zip(mid,u)]; q = [x-y/2 for x,y in zip(mid,u)]
        for k in (k for k,t in enumerate(pts) if k not in (i,j) and norm(sub(t,p)) <= .5):
            for l in (l for l,t in enumerate(pts) if l not in (i,j,k) and norm(sub(t,q)) <= .5): candidates.add(tuple(sorted((i,j,k,l))))
    for ids in sorted(candidates):
        vertices += 1
        print('endpoint candidate', fid, [tuple(round(x,4) for x in pts[i]) for i in ids])
print('closed four-line loops:', cycles, 'endpoint candidates:', vertices)
PY
```

## Remaining work

Use the same headless CLI to build a connected topology inventory of **all**
rectangular/rounded slots, interrupted outlines, protrusions, channels and
recesses, including cross-face or differently elevated features, and examine the
22 non-analytic patches and the discrepant patch beyond sampled points. The
greedy plane grouping, 5° arc threshold, 2 mm endpoint minimum, and tolerance
limits can all hide features. This note does not authorize editing the source,
printing, or operating a device. No physical speaker or fasteners are in the
STEP; head clearance and self-occlusion must be tested against a specified
speaker and screw geometry rather than invented here.

## Requested verification — verbatim output

Run on 2026-11-15 from `/home/james/Projects/debra`. The evaluation times are
per-run timings, not stable geometric properties. `git diff --check` does not
check untracked files.

<details>
<summary><code>solidcraft-cli eval --in /home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step</code> — exit 0</summary>

```text
{
  "bodies": [
    {
      "area_mm2": 15129.801740996329,
      "bbox": {
        "max": [
          49.000000000064006,
          15.500000000000002,
          37.649999999888905
        ],
        "min": [
          -17.1500000000415,
          -0.6000000380049787,
          -37.6499999998879
        ]
      },
      "center_of_mass": [
        13.084342554086732,
        4.688855949527719,
        0.3255565701550977
      ],
      "closed": true,
      "density_g_cm3": 1.29,
      "edges": 419,
      "face_types": {
        "cone": 9,
        "cylinder": 35,
        "other": 23,
        "plane": 76
      },
      "faces": 143,
      "kernel": {
        "edges": 776,
        "faces": 262,
        "shells": 1,
        "vertices": 513
      },
      "mass_g": 19.71430954196571,
      "material": "Default",
      "measured_by": "smlib",
      "name": "RPiSpeaker v17",
      "notes": [],
      "vertices": 275,
      "volume_mm3": 15282.410497647837
    }
  ],
  "body_count": 1,
  "params": [],
  "sketches": [],
  "timeline": [
    {
      "error": null,
      "id": 3,
      "ms": 1.170471,
      "name": "RPiSpeaker v17",
      "rolled_back": false,
      "suppressed": false,
      "type": "BaseFeature",
      "warning": "solid 'Body45': 3 edges lie off their faces' surfaces by more than 0.01 mm: their tolerances are the gaps they have (up to 1.014e-2 mm)"
    }
  ],
  "total": {
    "area_mm2": 15129.801740996329,
    "edges": 419,
    "faces": 143,
    "mass_g": 19.71430954196571,
    "open_bodies_skipped": 0,
    "vertices": 275,
    "volume_mm3": 15282.410497647837
  }
}
```

</details>

<details>
<summary><code>solidcraft-cli eval --in models/parts/rpispeaker-v17-body/rpispeaker-v17-body.sc</code> — exit 0</summary>

```text
{
  "bodies": [
    {
      "area_mm2": 14831.369422644213,
      "bbox": {
        "max": [
          49.0,
          15.500000000000002,
          37.65
        ],
        "min": [
          -17.15,
          -0.6000000000000001,
          -37.65
        ]
      },
      "center_of_mass": [
        12.983371129895492,
        4.591425670073586,
        -1.9098071278636857
      ],
      "closed": true,
      "density_g_cm3": 1.29,
      "edges": 189,
      "face_types": {
        "cone": 7,
        "cylinder": 14,
        "plane": 45
      },
      "faces": 66,
      "kernel": {
        "edges": 192,
        "faces": 67,
        "shells": 1,
        "vertices": 128
      },
      "mass_g": 20.530855064219022,
      "material": "Default",
      "measured_by": "smlib",
      "name": "Body",
      "notes": [],
      "vertices": 126,
      "volume_mm3": 15915.391522650403
    }
  ],
  "body_count": 1,
  "params": [
    {
      "comment": "",
      "error": null,
      "expression": "-17.15 mm",
      "model": false,
      "name": "X_LEFT",
      "unit": "mm",
      "value": -17.15
    },
    {
      "comment": "",
      "error": null,
      "expression": "17.15 mm",
      "model": false,
      "name": "DIVIDER_OUT",
      "unit": "mm",
      "value": 17.15
    },
    {
      "comment": "",
      "error": null,
      "expression": "15.75 mm",
      "model": false,
      "name": "PI_IN_X",
      "unit": "mm",
      "value": 15.75
    },
    {
      "comment": "",
      "error": null,
      "expression": "-32.50 mm",
      "model": false,
      "name": "PI_Z_MIN",
      "unit": "mm",
      "value": -32.5
    },
    {
      "comment": "",
      "error": null,
      "expression": "34.00 mm",
      "model": false,
      "name": "PI_Z_MAX",
      "unit": "mm",
      "value": 34.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "37.65 mm",
      "model": false,
      "name": "OUTER_Z",
      "unit": "mm",
      "value": 37.65
    },
    {
      "comment": "",
      "error": null,
      "expression": "4 mm",
      "model": false,
      "name": "PI_ROUND",
      "unit": "mm",
      "value": 4.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "-0.60 mm",
      "model": false,
      "name": "BACK_Y",
      "unit": "mm",
      "value": -0.6
    },
    {
      "comment": "",
      "error": null,
      "expression": "2.50 mm",
      "model": false,
      "name": "FLOOR_Y",
      "unit": "mm",
      "value": 2.5
    },
    {
      "comment": "",
      "error": null,
      "expression": "8.50 mm",
      "model": false,
      "name": "RAISED_Y",
      "unit": "mm",
      "value": 8.5
    },
    {
      "comment": "",
      "error": null,
      "expression": "15.50 mm",
      "model": false,
      "name": "FRONT_Y",
      "unit": "mm",
      "value": 15.5
    },
    {
      "comment": "",
      "error": null,
      "expression": "49 mm",
      "model": false,
      "name": "SPEAKER_X_MAX",
      "unit": "mm",
      "value": 49.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "48.25 mm",
      "model": false,
      "name": "SPEAKER_IN_X",
      "unit": "mm",
      "value": 48.25
    },
    {
      "comment": "",
      "error": null,
      "expression": "14.0625 mm",
      "model": false,
      "name": "SPEAKER_END_Z",
      "unit": "mm",
      "value": 14.0625
    },
    {
      "comment": "",
      "error": null,
      "expression": "11 mm",
      "model": false,
      "name": "SPEAKER_ROUND",
      "unit": "mm",
      "value": 11.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "33 mm",
      "model": false,
      "name": "TRANSITION_Z",
      "unit": "mm",
      "value": 33.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "11 mm",
      "model": false,
      "name": "NOSE_Z",
      "unit": "mm",
      "value": 11.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "32.5 mm",
      "model": false,
      "name": "PILOT_X",
      "unit": "mm",
      "value": 32.5
    },
    {
      "comment": "",
      "error": null,
      "expression": "18.25 mm",
      "model": false,
      "name": "PILOT_Z",
      "unit": "mm",
      "value": 18.25
    },
    {
      "comment": "",
      "error": null,
      "expression": "2.1755 mm",
      "model": false,
      "name": "PILOT_D",
      "unit": "mm",
      "value": 2.1755
    },
    {
      "comment": "",
      "error": null,
      "expression": "4.5 mm",
      "model": false,
      "name": "PILOT_CS_D",
      "unit": "mm",
      "value": 4.5
    },
    {
      "comment": "",
      "error": null,
      "expression": "RAISED_Y - (PILOT_CS_D - PILOT_D)/2",
      "model": false,
      "name": "PILOT_CS_Y",
      "unit": "mm",
      "value": 7.33775
    },
    {
      "comment": "",
      "error": null,
      "expression": "31.625 mm",
      "model": false,
      "name": "CENTRE_X",
      "unit": "mm",
      "value": 31.625
    },
    {
      "comment": "",
      "error": null,
      "expression": "10 mm",
      "model": false,
      "name": "CENTRE_SMALL_D",
      "unit": "mm",
      "value": 10.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "18 mm",
      "model": false,
      "name": "CENTRE_MID_D",
      "unit": "mm",
      "value": 18.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "20 mm",
      "model": false,
      "name": "CENTRE_TOP_D",
      "unit": "mm",
      "value": 20.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "0 mm",
      "model": false,
      "name": "CENTRE_SHOULDER_Y",
      "unit": "mm",
      "value": 0.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "1.5 mm",
      "model": false,
      "name": "CENTRE_FLARE_Y",
      "unit": "mm",
      "value": 1.5
    },
    {
      "comment": "",
      "error": null,
      "expression": "11.5 mm",
      "model": false,
      "name": "PI_PILOT_X",
      "unit": "mm",
      "value": 11.5
    },
    {
      "comment": "",
      "error": null,
      "expression": "29 mm",
      "model": false,
      "name": "PI_PILOT_Z",
      "unit": "mm",
      "value": 29.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "4.75 mm",
      "model": false,
      "name": "PI_CS_D",
      "unit": "mm",
      "value": 4.75
    },
    {
      "comment": "",
      "error": null,
      "expression": "FLOOR_Y - (PI_CS_D - PILOT_D)/2",
      "model": false,
      "name": "PI_CS_Y",
      "unit": "mm",
      "value": 1.21275
    },
    {
      "comment": "Measured central Pi recess floor",
      "error": null,
      "expression": "0 mm",
      "model": false,
      "name": "PI_BASE_Y",
      "unit": "mm",
      "value": 0.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "15 mm",
      "model": false,
      "name": "PI_RECESS_X",
      "unit": "mm",
      "value": 15.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "25.5 mm",
      "model": false,
      "name": "PI_RECESS_Z",
      "unit": "mm",
      "value": 25.5
    },
    {
      "comment": "",
      "error": null,
      "expression": "8 mm",
      "model": false,
      "name": "PI_RECESS_END_X",
      "unit": "mm",
      "value": 8.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "3.5 mm",
      "model": false,
      "name": "PORT_Y",
      "unit": "mm",
      "value": 3.5
    },
    {
      "comment": "",
      "error": null,
      "expression": "-26.1 mm",
      "model": false,
      "name": "PORT_WIDE_Z",
      "unit": "mm",
      "value": -26.1
    },
    {
      "comment": "",
      "error": null,
      "expression": "5 mm",
      "model": false,
      "name": "PORT_WIDE_HEIGHT",
      "unit": "mm",
      "value": 5.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "12 mm",
      "model": false,
      "name": "PORT_WIDE_LENGTH",
      "unit": "mm",
      "value": 12.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "4 mm",
      "model": false,
      "name": "PORT_NARROW_HEIGHT",
      "unit": "mm",
      "value": 4.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "9 mm",
      "model": false,
      "name": "PORT_NARROW_LENGTH",
      "unit": "mm",
      "value": 9.0
    },
    {
      "comment": "",
      "error": null,
      "expression": "4.75 mm",
      "model": false,
      "name": "PORT_MID_Z",
      "unit": "mm",
      "value": 4.75
    },
    {
      "comment": "",
      "error": null,
      "expression": "17 mm",
      "model": false,
      "name": "PORT_POS_Z",
      "unit": "mm",
      "value": 17.0
    },
    {
      "comment": "Reference only: thread is not modelled",
      "error": null,
      "expression": "7.28775 mm",
      "model": false,
      "name": "THREAD_END_Y",
      "unit": "mm",
      "value": 7.28775
    }
  ],
  "sketches": [],
  "timeline": [
    {
      "error": null,
      "id": 1,
      "ms": 1.769516,
      "name": "Pi side main stock",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 2,
      "ms": 5.621397999999999,
      "name": "Pi side outer band",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 3,
      "ms": 16.609837,
      "name": "Pi outer round negative",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 4,
      "ms": 16.366490000000002,
      "name": "Pi outer round positive",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 5,
      "ms": 6.2561420000000005,
      "name": "Speaker transition stock",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 6,
      "ms": 7.663247,
      "name": "Speaker middle stock",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 7,
      "ms": 17.659541,
      "name": "Speaker concave transition negative",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 8,
      "ms": 18.246024,
      "name": "Speaker concave transition positive",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 9,
      "ms": 11.094328,
      "name": "Speaker outer band",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 10,
      "ms": 22.093868,
      "name": "Speaker convex round negative",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 11,
      "ms": 21.968121,
      "name": "Speaker convex round positive",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 12,
      "ms": 12.379995,
      "name": "Simplified Pi bay",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 13,
      "ms": 12.785889,
      "name": "Pi lower central floor",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 14,
      "ms": 15.003176999999999,
      "name": "Pi lower positive end",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 15,
      "ms": 17.105519,
      "name": "Pi lower connector edge",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 16,
      "ms": 17.347926,
      "name": "Open divider over central recess",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 17,
      "ms": 20.063681,
      "name": "Speaker lower recess",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 18,
      "ms": 20.730915999999997,
      "name": "Centre back bore",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 19,
      "ms": 23.462130000000002,
      "name": "Centre counterbore",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 20,
      "ms": 34.814634,
      "name": "Centre flare",
      "rolled_back": false,
      "suppressed": false,
      "type": "ConeFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 21,
      "ms": 23.24393,
      "name": "Speaker pilot negative core",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 22,
      "ms": 37.204036,
      "name": "Speaker pilot negative countersink",
      "rolled_back": false,
      "suppressed": false,
      "type": "ConeFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 23,
      "ms": 25.927184999999998,
      "name": "Speaker pilot positive core",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 24,
      "ms": 49.096244,
      "name": "Speaker pilot positive countersink",
      "rolled_back": false,
      "suppressed": false,
      "type": "ConeFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 25,
      "ms": 30.549485,
      "name": "Pi pilot left negative core",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 26,
      "ms": 42.037022,
      "name": "Pi pilot left negative countersink",
      "rolled_back": false,
      "suppressed": false,
      "type": "ConeFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 27,
      "ms": 29.794976000000002,
      "name": "Pi pilot right negative core",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 28,
      "ms": 48.753219,
      "name": "Pi pilot right negative countersink",
      "rolled_back": false,
      "suppressed": false,
      "type": "ConeFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 29,
      "ms": 34.076516,
      "name": "Pi pilot left positive core",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 30,
      "ms": 45.018787999999994,
      "name": "Pi pilot left positive countersink",
      "rolled_back": false,
      "suppressed": false,
      "type": "ConeFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 31,
      "ms": 34.864016,
      "name": "Pi pilot right positive core",
      "rolled_back": false,
      "suppressed": false,
      "type": "CylinderFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 32,
      "ms": 47.305507,
      "name": "Pi pilot right positive countersink",
      "rolled_back": false,
      "suppressed": false,
      "type": "ConeFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 33,
      "ms": 33.837517,
      "name": "Side port negative",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 34,
      "ms": 35.186943,
      "name": "Side port middle",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    },
    {
      "error": null,
      "id": 35,
      "ms": 42.757517,
      "name": "Side port positive",
      "rolled_back": false,
      "suppressed": false,
      "type": "BoxFeature",
      "warning": null
    }
  ],
  "total": {
    "area_mm2": 14831.369422644213,
    "edges": 189,
    "faces": 66,
    "mass_g": 20.530855064219022,
    "open_bodies_skipped": 0,
    "vertices": 126,
    "volume_mm3": 15915.391522650403
  }
}
```

</details>

<details>
<summary><code>python3 -B -m unittest tests.test_docs -v</code> — exit 1</summary>

```text
test_committed_images_are_referenced (tests.test_docs.AssetTests.test_committed_images_are_referenced)
No orphan renders: an asset folder is for pictures a page shows. ... FAIL
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

======================================================================
FAIL: test_committed_images_are_referenced (tests.test_docs.AssetTests.test_committed_images_are_referenced)
No orphan renders: an asset folder is for pictures a page shows.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/james/Projects/debra/tests/test_docs.py", line 192, in test_committed_images_are_referenced
    self.assertIn(
    ~~~~~~~~~~~~~^
        image.name,
        ^^^^^^^^^^^
        text,
        ^^^^^
        f"{image.relative_to(ROOT)} is committed but no page shows it",
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
AssertionError: 'iso.png' not found in '' : models/assemblies/zero-square-demo/assets/iso.png is committed but no page shows it

----------------------------------------------------------------------
Ran 11 tests in 0.041s

FAILED (failures=1)
```

</details>

<details>
<summary><code>git diff --check</code> — exit 0</summary>

```text

```

</details>

The documentation failure above is outside this assignment: at test time
`models/assemblies/zero-square-demo/assets/iso.png` was an untracked file in
an in-progress directory with no Markdown page. Despite its message saying
"committed", the test scans the working tree rather than the Git index. No
files in that directory were changed by this work. Rerun the test after its
owner finishes or otherwise resolves that work.

On the later rerun, that other directory had gained an untracked README, but
its `verification-docs.txt` link did not yet resolve. This is a different
failure in the same concurrently changing, out-of-scope work.

<details>
<summary><code>python3 -B -m unittest tests.test_docs -v</code> — later rerun, exit 1</summary>

```text
test_committed_images_are_referenced (tests.test_docs.AssetTests.test_committed_images_are_referenced)
No orphan renders: an asset folder is for pictures a page shows. ... ok
test_every_referenced_image_exists (tests.test_docs.AssetTests.test_every_referenced_image_exists) ... ok
test_model_folder_links_resolve (tests.test_docs.AssetTests.test_model_folder_links_resolve) ... FAIL
test_entrypoint_links_and_heading_fragments_resolve (tests.test_docs.FrontDoorTests.test_entrypoint_links_and_heading_fragments_resolve) ... ok
test_historical_readme_section_is_preserved (tests.test_docs.FrontDoorTests.test_historical_readme_section_is_preserved) ... ok
test_readme_routes_to_getting_started_and_preserved_history (tests.test_docs.FrontDoorTests.test_readme_routes_to_getting_started_and_preserved_history) ... ok
test_local_markdown_links_resolve (tests.test_docs.RelativeLinkTests.test_local_markdown_links_resolve) ... ok
test_every_cited_key_is_defined (tests.test_docs.SourceRegisterTests.test_every_cited_key_is_defined) ... ok
test_every_register_entry_has_a_url_and_a_date (tests.test_docs.SourceRegisterTests.test_every_register_entry_has_a_url_and_a_date) ... ok
test_register_keys_are_unique (tests.test_docs.SourceRegisterTests.test_register_keys_are_unique) ... ok
test_sources_page_exists_and_has_rows (tests.test_docs.SourceRegisterTests.test_sources_page_exists_and_has_rows) ... ok

======================================================================
FAIL: test_model_folder_links_resolve (tests.test_docs.AssetTests.test_model_folder_links_resolve)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/james/Projects/debra/tests/test_docs.py", line 179, in test_model_folder_links_resolve
    self.assertTrue(
    ~~~~~~~~~~~~~~~^
        path.exists(),
        ^^^^^^^^^^^^^^
        f"{page.relative_to(ROOT)} links to missing {target}",
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
AssertionError: False is not true : models/assemblies/zero-square-demo/README.md links to missing verification-docs.txt

----------------------------------------------------------------------
Ran 11 tests in 0.098s

FAILED (failures=1)
```

</details>
