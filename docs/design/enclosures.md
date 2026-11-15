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
