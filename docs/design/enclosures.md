# Modular SolidCraft enclosures

James expanded this requirement on 2026-11-14: a dedicated enclosure subagent
should inventory the candidate components, capture their dimensions, model
reusable parts, and combine them into a variety of sensible printable devices.
Pi version and speaker are the main visible choices; the exact HAT, connectors,
controls, cooling and mounting hardware also determine whether a case fits.

**Requirements and proposed workflow, not existing models or verified fit.**
The [D01–D03 packets](../roadmap.md#long-term-3d-models-and-enclosures) retain
their prerequisites. This lane runs alongside software work rather than waiting
for a finished appliance, but mechanical fit does not establish software support.

## Inventory every candidate; build a bounded useful set

Maintain a coverage table for the concrete candidates in
[R01](../work/cards/R01.md), the hardware inventory and the historical README.
Include additional selected parts as research progresses. A listing identity,
an exact purchased revision and a supported combination are different things.
Do not silently equate them or promise every possible board/speaker permutation.

Each component record needs:

- Exact manufacturer/model/revision and source or specimen identification.
- Overall envelope, coordinate origin/orientation, mounting plane, hole centres
  and diameters, component heights and protrusions on both sides.
- Header/stack heights; connector positions, plug bodies, mating/unplugging
  directions, cable exits and bend/service space; microSD insertion/removal path.
- Speaker frame/magnet/rear envelope, moving-part clearance, mounting and acoustic
  openings; microphone ports, buttons, indicators and other no-obstruction zones.
- Direct dated dimensional drawing/CAD source or attributed measurement, units,
  uncertainty, source revision, reuse licence and any unresolved dimensions.

Use sourced dimensions where available; request measurements only for actual
gaps. Never derive fit-critical numbers from an unscaled photograph or substitute
a similarly named speaker. Mark candidate coverage as researched, missing data,
component modeled, assembly modeled, or physically checked, with exact revision.

## Reusable parts and assemblies

Use **SolidCraft** for the editable parametric models. Prefer shared interfaces
and parameter-driven layouts over unrelated copies. Separate non-printing
component envelopes/keep-outs from printable parts so a reference board or dummy
speaker cannot accidentally appear in a print export.

The intended reusable set is:

- Pi/HAT electronics tray with appropriate mounting and stack clearance.
- Speaker-specific carrier or replaceable baffle; gasket allowance where needed.
- Outer base/shell with deliberate wiring space, restraints and service access.
- Removable top/lid, connector panels and optional button caps or blank covers.
- Removable speaker grille and an optional cloth/mesh retaining frame.
- Shared fasteners, spacers and adapters only where their interfaces truly match.

Prioritize a small initial assembly matrix after D01's dimensional/provenance
review: for example a compact Zero-family mono case, a roomier desktop version
for a larger speaker, and a stereo or separate-speaker-pod arrangement where the
selected hardware warrants it. These are proposed families, not selected builds.
Carry forward useful validated interfaces; check each advertised combination.

## Clearance and usability requirements

| Area | Required design treatment and verification |
| --- | --- |
| Wiring | Budget for the actual plug, cable exit/bend and assembly/service slack, not just wire diameter. Route away from moving speaker parts, sharp edges, fasteners and lid pinch points. Include appropriate restraint. |
| Power | Keep the chosen connector reachable and reserve plug/bend space. Do not call a printed button a power switch unless its electrical/software function exists. |
| microSD | Permit safe, powered-off card insertion/removal without dismantling the speaker assembly. Show finger/tool and card travel space, not just a slot in the wall. |
| Lid and controls | Provide a removable top or service cover and tool access. Add button caps, indicator windows or blanks appropriate to the exact HAT; do not press controls accidentally or imply unimplemented mute/power behavior. |
| Speaker protection | Keep the cone/surround and intended acoustic openings clear. Support the frame or module housing without crushing it. Keep a grille or cloth away from moving parts and make it replaceable. |
| Cloth/mesh | Provide a separate retaining frame/cassette or equivalent serviceable attachment. Record material/thickness assumptions and clearances; test the acoustic effect rather than assuming transparency. |
| Microphones | Preserve the exact microphone sound path and avoid obstructing ports with the lid, cloth, wiring or bosses. Evaluate speaker-to-microphone leakage during physical testing. |
| Cooling | Separate electronics ventilation from any intentionally sealed speaker chamber. Reserve the actual heatsink/fan space if selected; CAD alone does not prove safe temperature. |
| Assembly | Show fastener lengths, nut/insert capture, tool access, part removal order and connector extraction. Service should not require damaging a grille or repeatedly bending soldered wires. |

"A little room" becomes named, independently adjustable parameters for cable
space, plug clearance, service travel, print fit, gasket compression and lid gap.
Record initial values as design assumptions until checked. Use small fit coupons
before a full print; there is no universal printer/material clearance.

Do not promise tuned bass, a ported volume or acoustic improvement without the
required driver data and measurements. An enclosed speaker module may need a
protective carrier, not a second sealed box over its intended openings.

## Candidate speakers with sourced dimensions

Every row below is **vendor-published data read on 2026-11-15, not measured**.
Status is "researched, not modelled" for all of them: nothing here is in
SolidCraft yet. Sizes are the driver's own envelope, so a baffle also needs the
recess and the mounting-hole pattern, and the depth figure is the rear-most
drawn point — it does not include a magnet clearance allowance.

| Driver | Size and mounting | Depth | Power / impedance | Fastening | Notes |
| --- | --- | --- | --- | --- | --- |
| Adafruit 1314, 3" | frame Ø78, 4 oblong holes 5 × 4 mm on a Ø84 bolt circle (≈59.4 mm adjacent) | 25–26 mm | 3 W rated, 5 W max, 4 Ω | 4 screws | magnet Ø32 × 8; solder terminals. Supplier drawing labels the depth "Ø25" and the page says 25.49 mm, outside its own ±0.5 — budget 26 mm |
| Adafruit 3968, 40 mm | Ø40.0 ± 0.2 overall, Ø36.5 ± 0.2 body, magnet Ø23.3 | 21 ± 0.5 mm | 5 W, 6 W max, 4 Ω | **none** | bare ~9 cm wires; needs a clamp or a printed retainer |
| Adafruit 3351, mono enclosed | 30 × 70 × 17, 3.4 mm holes, 24 × 63 hole rectangle | 17 mm | 3 W, 4 Ω | 4 screws | JST-PH 2 mm connector; Adafruit warns hole diameter may vary 20 % |
| Adafruit 1669, stereo pair | 30 × 70 × 17, 3.1 mm holes, 24 × 64 rectangle | 17 mm | 3 W, 4 Ω | 4 screws | no datasheet, page data only |
| Adafruit 4445, enclosed | 31 × 70 × 17, 3.1 mm holes, 31 × 64 rectangle | 17 mm | 3 W, 4 Ω | 4 screws | plain wires; footprint conflicts with the other two enclosed modules |
| Visaton FR 58-8 | 58.5 mm square, 4 × Ø5.5 on a Ø64.5 bolt circle | 28 mm | 10 W (12 W music), 8 Ω | 4 screws | lugs 5.2 × 0.5 and 2.8 × 0.5; cut-out 57 mm (data) vs 56 mm (drawing) |
| Visaton FRS 5 X-8 | 68 mm across the lugs, hole centres 60 mm apart, 2 × Ø4.2, recess Ø50 | 33.5 mm | 5 W (8 W), 8 Ω | 2 screws | cut-out quoted 46 mm; the recess matters as much as the hole |
| Visaton K 50-4 | Ø50 | 17 mm | 2 W, 4 Ω | **none** | IP65 front; needs a clamp or snap retention |
| Visaton FRS 7 W-8 | 66.5 mm square, 4 × Ø4.6 on a Ø75.6 bolt circle | 34.8 mm | 8 W (15 W), 8 Ω | 4 screws | cut-out 61 mm (data) vs Ø60 (drawing) |
| Dayton ND65-4, 2-1/2" | OD 64, cut-out 52, 4 holes | 48 mm | 15 W RMS / 30 W max, 4 Ω | 4 screws | **hole diameter, spacing and terminals unknown**; the dated spec PDF has no outline drawing |
| Seeed reSpeaker Sound Base | **not published** | — | 5 W, 4 Ω | — | accessory of the 44 mm XVF3800 array, not of the 2-Mics HAT |

Two facts about the HAT itself matter more than the driver list:

- The ReSpeaker 2-Mics Pi HAT ships **no speaker** and publishes **no amplifier
  power rating**. It has a JST 2.0 speaker output and a 3.5 mm jack, so the safe
  assumption is a small driver, and the real limit is unmeasured.
- The HAT's JST output looks like JST-PH 2 mm, which would match the Adafruit 3351
  module — but the pinout and polarity are undocumented. Treat that as a
  hypothesis to check with a meter before plugging anything in.

Sources, all read 2026-11-15: Adafruit product pages and their
`cdn-shop.adafruit.com` datasheets for 1314, 3968, 3351, 1669 and 4445; Visaton
`visaton.de/sites/default/files/dd_product/` datasheets for FR 58, FRS 5 X, K 50
and FRS 7 W; `daytonaudio.com/product/63/nd65-4` (dimensions on the page only);
`seeedstudio.com/ReSpeaker-2-Mics-Pi-HAT-p-2874.html` and
`wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT/`; the Sound Base page at
`wiki.seeedstudio.com/respeaker_44mm_introduction/`.

## Reference: what a published enclosure did

FutureProofHomes publishes the printed enclosure for its Satellite1 speaker as
3MF/STL/STEP, which makes it the most useful public reference for Debra's own
case work — not a design to copy, a baseline to beat or learn from:

| Choice | Their published value | Why it is worth knowing |
| --- | --- | --- |
| Material and profile | PETG, 0.4 mm nozzle | Debra's material is not chosen; this is a working data point for a speaker box |
| Walls and infill | 3 perimeters; 30 % infill front/back chamber, 15 % top and diffuser | Rigid chamber, lighter lid |
| Supports | none | Their geometry is designed to print without them |
| Fasteners | 24 × M3 × 10 mm | A whole enclosure on one screw size |
| Drivers | 3" woofer 15 W RMS / 20 W peak 4 Ω + 1.2" neo tweeter + passive 2-way crossover, JST-XH to the board | Debra's HAT cannot drive this; it is the ceiling for a bigger build |
| Power | 30 W USB-C PD supply | Amplifier headroom drives the supply, not the SoC |
| Service | LED diffuser snaps out, top piece lifts on ball joints, boards on four posts | Service access without tools on the visible parts |
| Acoustic caveat | "At full volume, the wake word may not be heard perfectly" | Vendor's own admission that speaker and microphone in one box is a real problem |

Their enclosure files are at
`github.com/FutureProofHomes/Satellite1-Enclosures` and their assembly steps at
`docs.futureproofhomes.net/satellite1-smart-speaker/`, read 2026-11-15. Licence
for reuse has not been checked, so nothing from it may be copied into Debra's
models until it is.

## Deliverables and acceptance

Proposed organization, created as deliverables exist:

```text
models/
  components/<part-id>/       # editable reference envelopes + dimension sources
  shared/<interface-id>/      # reusable printable parts + interface parameters
  <assembly-id>/
    models/                  # editable SolidCraft source + parameter set
    exports/                 # explicitly selected printable parts
    docs/                    # BOM, sources, assembly, print and test record
```

Keep source attribution/licensing alongside any reused CAD; do not treat freely
downloadable CAD as automatically redistributable. Raw/private source captures
belong in ignored `.local/`, not the public model bundle.

For each delivered assembly:

1. Name the exact component revisions, source dimensions, remaining assumptions,
   complete bill of materials, fasteners and any cloth/mesh/gasket material.
2. Provide editable sources, reproducible parameter values, separately printable
   exports, orientations/support assumptions and an illustrated assembly order.
3. Verify geometry, dimensions, collisions and clearances; exercise representative
   parameter changes. Record actual checks and failures, not only screenshots or
   a CAD tool's success flag.
4. Label component geometry **dimension-sourced** or **provisional** as appropriate;
   independently label assembly maturity **CAD-only**, **printed**, **fit-tested**,
   **thermally tested** and **acoustically tested**. No stage implies another.
5. Record physical fit, wiring, card/power access, buttons, grille retention,
   temperature and microphone/playback results only after those tests occur.
   Printing and device operations need separately agreed targets and scope.

Assign one CAD operator at a time to a shared SolidCraft design session; research
can run in parallel. Inspect and preserve any unrelated open user design before
starting a separate Debra file. Editing agents still need a bounded assignment,
owned workspace, effective tool policy and separate capable review under the
[AI workflow](../ai-workflow.md).
