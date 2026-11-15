# RPiSpeaker v17 speaker mount options

The supplied v17 body has a recessed speaker side and two threaded through
holes, but no square four-screw speaker pattern or dedicated four-screw lid
bosses. A 44 x 28 x
15 mm DWEII 671 housing cannot fit wholly within the lower speaker-side footprint;
seated on the raised surfaces it would project 8 mm beyond the front reference
plane and need a separate retainer. A 40 mm square driver cannot fit wholly inside
that lower footprint, and a direct four-screw mount on the existing front face is
not established. A separate
lid and support frame could carry it, but those parts and their attachments are
proposals, not evidence of the original assembly. These are dimensional
assessments, not validated designs. None of the arrangements below has been
printed or fit-tested.

## Options

All dimensions are in mm. X runs across the bays, Z along them, and Y is depth;
the second bay opens toward +Y. The body dimensions and holes are the supplied
extraction measurements, not measurements repeated for this note. See the
[v17 reference](../../models/components/rpispeaker-v17/README.md) and its
[extraction record](../notes/2026-11-15-rpispeaker-v17-extraction.md). The
[DWEII record](../../models/components/dweii-speakers/README.md) says 44 x 28 x
15 is a seller-sourced 671 envelope, not a measured module, and records a
conflicting 31 mm length. The ~40 x 40 x 5-8 bare driver below is a hypothetical
envelope, not an identified or measured original speaker.

The lower speaker-side X span is **31.10 mm**: the measured bounds are X 17.15 and X 48.25,
and 48.25 - 17.15 = 31.10. An earlier 31.85 figure came from using the envelope's
outer X 49.00 instead of the inner face, which counts the 0.75 mm outer wall as
bay. See the [correction note](../notes/2026-11-15-rpispeaker-v17-second-bay-corrections.md).
The later [bay inventory](../notes/2026-11-15-rpispeaker-v17-bay-inventory.md)
also corrected the former 31.10 × 66 × 7 rectangular-pocket premise: the lower
speaker-side footprint is 31.10 × 28.125, its central floor is Y 2.50, and
Y 8.50 is the raised surface outside the central recess. Z ±33 describes its
outer outline, not a 66 mm rectangular pocket. Rounded corners, tabs, leads,
tolerances and local obstructions still need checking; a positive rectangular
clearance is not a complete fit check.

### A. DWEII 671 in the second bay

**Conditional:** the nominal housing does not fit wholly within the lower
footprint; a placement above the raised surfaces and a retainer remain unverified.
The earlier plan-fit conclusion used the incorrect 66 mm pocket length.

| Decisive dimension | Arithmetic or result |
| --- | --- |
| Lower footprint versus housing | 31.10 x 28.125 versus 28 x 44, with 28 along X and 44 along Z; 44 exceeds the lower Z span by 15.875 |
| Plan clearance | 31.10 - 28 = 3.10 total in X, or 1.55 per side if centred; the housing's 44 x 28 area exceeds the lower footprint even when rotated |
| Other orientation | 44 across X exceeds the 31.10 width by 12.90, so it cannot sit wholly inside that width |
| Depth and reach | If seated on the raised Y = 8.50 surfaces, 15 - 7 = 8 beyond the Y = 15.50 reference plane; the housing reaches Y = 23.50. Seating and contact remain unverified |
| Existing pilots | X = 32.5, Z = +/-18.25, spacing 36.5; open through from Y = -0.60 to 8.50, with thread ending at Y = 7.29 and a 90° countersink from Ø2.1755 at Y = 7.33775 to Ø4.50 at Y = 8.50 |
| Centred housing and pilots | With its 44 mm length centred at Z = 0, the housing ends at Z = +/-22; the pilot centres are 3.75 inside each end, not beyond the housing |

The former objection that a 1.21 mm web prevents a front screw reaching the
pilots was wrong: the countersinks remove that material, and a 0.05 mm open
cylindrical core connects each countersink to the thread. A front screw can
reach the existing thread without modifying the body; actual screw fit and
engagement are untested. Nor does the 36.5 spacing prove alignment with the
module: its tab positions and hole sizes are unknown. If tabs sit beyond both ends of the centred 44 mm housing,
their centres are more than 44 apart, not 36.5. Other tab geometry is unknown.

One possible retention concept is a separate rear bracket screwed into the two
pilots, with arms passing around the body to a front strap over the housing. The
strap must grip the housing, not the cone or acoustic openings, and allow lead
and service clearance. It would have to reach from the back plane at Y = -0.60
to the housing's outer plane at Y = 23.50, a 24.10 span before bracket thickness
or clearance. Whether those arms can clear the actual walls and connectors is
unknown. Alternatively, a separate carrier could use the existing front openings
or different fasteners; its fit and attachment remain to be designed.
Do not assume the module is sealed or block its unknown openings.

### B. Square bare driver on the outside of the second bay

**Impossible** to put the full 40 mm square inside the lower footprint. **No** direct
existing four-screw mount is present. An outside mount is **conditional** on a
new support or changed body and the actual driver dimensions.

| Decisive dimension | Arithmetic or result |
| --- | --- |
| Square versus lower footprint | 40 across X exceeds 31.10 by 8.90; 40 across Z exceeds 28.125 by 11.875. It cannot sit wholly inside that footprint |
| Centred outside footprint | Centred between X = 17.15 and 48.25, the square spans X = 12.70 to 52.70; the body envelope ends at X = 49.00, so it overhangs by 3.70 |
| Existing front face | At Y = 15.50 the face covers X = -17.15 to 17.15 only. In that centred example, just 4.45 of the 40 mm width lies over that face; the remaining 35.55 does not |
| Raised surface below reference plane | The raised surface is 7 below Y = 15.50. If a screw head starts 5-8 above that plane, it must span 12-15 to reach that surface, before engagement; the actual driver flange thickness is unknown |
| Existing fasteners | No square four-screw pattern exists in the body; the two second-bay holes are threaded through holes with front Ø4.50 countersinks at Y = 8.50 |

The overhang example is not a proof that every possible shifted placement or
every possible four-hole pattern misses material. The actual frame shape and
hole centres are unknown, as are the exact wall surfaces and usable material
around the rounded ends. But the open bay has no front mounting face under most
of the centred square, and the two rear pilots do not supply four front
attachments. A bridging baffle, stand-offs and new fastener locations, or a
changed body, would be needed for a practical four-screw concept; their reach,
engagement, Pi clearance and acoustic opening must be designed and checked.
Shifting the driver toward the Pi also risks covering its front and HAT.

### C. Speaker on the back over the Pi bay

**Conditional:** a rear carrier could use the Pi pattern, but the four pilots
are not a direct 40 mm square speaker pattern and are already needed for the Pi.

| Decisive dimension | Arithmetic or result |
| --- | --- |
| Pi bay versus square | The bay is 31.50 wide; a 40 mm square is 8.50 wider |
| Pi pilot pattern | X = +/-11.5, Z = +/-29: 23 x 58, not a square |
| Centred 40 mm driver versus pilots | Driver Z = -20 to 20; each pilot at Z = +/-29 is 9 beyond its nearest end. A carrier or extended tabs must reach those positions |
| Overhang on connector side | A square centred at X = 0 runs to X = -20, 2.85 beyond the X = -17.15 wall |
| Connector cut-outs | Two 4 x 9 and one 5 x 12 in that wall; the speaker or carrier must not prevent access along the wall |

Using the four Pi pilots for a rear carrier competes with the Pi mounting. It
could require shared fasteners, stand-offs, a different fastening arrangement or
new mounting points. The pilot directions, engagement and space for the Pi and
carrier must be checked before choosing one; do not assume that both parts can
simply be screwed into the same holes independently. The 40 mm example
overhangs the connector-side wall, so check the USB and HDMI plug bodies and
their insertion and removal paths. The overhang alone does not prove the
cut-outs are blocked: the driver's Y position, carrier shape and plug clearance
are not known. A rear-facing speaker also changes the intended forward sound
direction.

### D. Separate front lid carries the speaker

**Conditional:** a lid and new supports can be designed, but the supplied v17
solid does not itself provide four dedicated lid bosses.

| Decisive dimension | Arithmetic or result |
| --- | --- |
| Opening to bridge | Lower speaker-side footprint: 31.10 x 28.125; raised surfaces are at Y = 8.50, 7 below the front reference plane, and the central floor is Y = 2.50 |
| Driver | A ~40 square needs a baffle at least large enough to carry its actual frame and mounting features; 40 exceeds the lower footprint |
| Existing patterns | Four Pi pilots on 23 x 58 and two through bay holes on 36.5; neither is a dedicated four-corner lid pattern |
| Bay pilot reach | A front screw can reach the existing thread through the Ø4.50 countersink without modifying the body; screw and lid fit remain untested |

If the remembered four screws are **case-assembly** screws, they need to thread
into bosses, inserts or captured nuts on another support, not into nonexistent
v17 lid bosses. One proposed support is a separate rear frame retained by the
two existing back-entry pilots, with arms around the body and four new bosses or
nut pockets for the front lid. The lid would retain the speaker separately,
for example with a clamp, unless the actual speaker has a suitable independent
mount. The four lid screws would thread into the **new frame**, not into the
original body. The arms, screw access, engagement, load on the two pilots,
connector access and overhang all need design and checking. The driver's rear
depth and shape must also clear the pocket floor and walls; a 40 mm frame does
not reveal the size of the part behind it. Alternatively, a revised body could
add bosses, but it would no longer be the original geometry. No missing lid or
frame is established by the STEP alone.

### E. Rear carrier on the second-bay pilots

**Conditional:** the two rear-entry pilots provide a possible attachment for a
separate bracket carrying a speaker on the back, without occupying the Pi
pilots. The bracket and speaker fit remain unverified.

| Decisive dimension | Arithmetic or result |
| --- | --- |
| Available pilot pattern | X = 32.5, Z = +/-18.25, 36.5 apart; thread runs from Y = -0.60 to about Y = 7.29, 7.89 from the back, and the opening continues to Y = 8.50 |
| Example 671 carrier footprint | A 44 mm housing centred at Z = 0 reaches Z = +/-22, so each pilot lies 3.75 inside an end. A bracket can span the pilots and extend around the housing; the housing's own tabs remain unknown |
| Rear projection | A 15 mm housing placed against Y = -0.60 reaches Y = -15.60; total front-to-back envelope becomes at least 16.10 + 15 = 31.10, excluding the carrier |
| Wire route candidate | The through hole is diameter 10 at (X, Z) = (31.625, 0), 0.875 in X from the pilot centreline; wire and plug sizes are unknown |

The screws would enter from the back and hold the **bracket to the body**, not
pass through the floor into the speaker. The bracket must restrain the housing
without blocking sound openings and leave enough pilot engagement without
bottoming out. Verify local back-face contact, screw heads, bracket clearance,
and whether the lead or its plug passes the hole. This turns the speaker toward
the back if its sound opening faces outward, and can interfere with wall use. It
does not explain a four-screw square mount.

## Recommendation

For the reconstruction, pursue **D, a separate front lid with a separate support
frame**, as a provisional concept. Keep the original body geometry as a
reference, and preserve the possibility of the existing square speaker and four
screws rather than substituting a DWEII module as a requirement. The proposed
four case screws would engage new frame bosses or captured nuts; speaker
retention would be a separate interface until the real hardware is identified.
If the original four screws hold the speaker instead, retain that interface in
the reconstruction rather than assuming this lid-screw interpretation.
This is a proposed way to assemble the parts, not a claim that the original
worked that way. Do not finalise the layout, fasteners or print from these
dimensions alone. Check the actual speaker and frame, microphone and connector
access, acoustic openings, wiring, wall mounting, tolerances and assembly order.

A first concept of D was built and measured; its earlier fastening objection
assumed a 1.21 mm web. The [bay inventory](../notes/2026-11-15-rpispeaker-v17-bay-inventory.md)
shows that premise was wrong: the holes open through front countersinks, so a
front screw can reach the existing thread without body modification. The
modelled Ø2.1755–2.68 thread limits and ~0.45 mm pitch are consistent with
M2.5 but do not prove it. The [lid README](../../models/parts/rpispeaker-v17-lid/README.md)
remains provisional because screw, lid and body fit have not been tested.
See the [enclosure requirements](enclosures.md) and
[arrangement notes](enclosure-arrangements.md).

## What would settle this

The single most useful evidence is **a clear photo of the assembled original
with the cover removed, showing the square speaker, all four screws and what
they enter**. That would distinguish speaker screws from case-assembly screws
and show whether another part supports them. A missing original part file or
measurements of the actual speaker and fastener locations could also resolve
the interface. None is currently established by this one-body STEP.
