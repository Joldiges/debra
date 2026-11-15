# RPiSpeaker v17: closing the second bay and carrying a speaker

The existing second-bay pilots do not reach the pocket, so neither a front screw nor a screw passed through the back can attach the provisional lid without opening the intervening material. A separate outside clamp or a bolt through the existing central hole could instead retain a new speaker-carrying plate without drilling the body, but neither is proven to fit or hold a load. The first test proposed here is a small coupon for an outside clamp that bears against the front and back of the body, not a snap that relies on the thin pocket wall. This is an unreviewed design study: nothing has been printed or fitted, and no original body or device was contacted.

## Options

Dimensions are in mm; X is across the bays, Z along them, and +Y is toward the front. The [corrected measurements](../notes/2026-11-15-rpispeaker-v17-second-bay-corrections.md), [body reference](../../models/components/rpispeaker-v17/README.md), [lid concept](../../models/parts/rpispeaker-v17-lid/README.md), and [speaker-mount study](rpispeaker-v17-speaker-mount-options.md) are the sources, read on 2026-11-15 at repository revision `b266b46`. These are reported STEP dimensions, not new physical measurements. The earlier 31.85 mm bay width in parts of the mount study is superseded by 31.10 mm.

Common reference: the body envelope is X -17.15 to 49.00, Y -0.60 to 15.50 and Z -37.65 to 37.65. Only the Pi bay has a front face at Y 15.50, across X -17.15 to 17.15. The second bay spans X 17.15 to 48.25 and Z -33 to 33, with floor Y 8.50 and a 7 mm depth. Two Ø2.18 pilots at (X, Z) = (32.5, ±18.25) enter from Y -0.60 and end at Y 7.29. The Ø10 through hole and Ø18 counterbore are at (31.625, 0). There is no four-screw square speaker mount in this body. **ASSUMED:** the selected flat back or front contact areas, the floor at each pilot, and sufficient access for each proposed part actually exist; the references do not establish all of those details.

Each option needs a *separate speaker-to-plate retainer*, sized for the actual speaker frame or module. It must not press the cone, surround, terminals or vents. A plate closing the bay is not automatically an airtight acoustic chamber: the central through hole, wiring, perimeter and other openings need a separate sealing decision. A housed module may have vents that must not be sealed. The actual speaker, its mass and fastening pattern are unknown; the Ø28 × 10 bare driver in the lid study is **ASSUMED**, not the required square speaker.

### A. Front screws into the two existing pilots

| Decisive number | Result |
| --- | --- |
| Web | 8.50 - 7.29 = 1.21 between the floor and each existing pilot |
| Proposed drill | Ø2.2, from the pocket floor, centered on each pilot; **ASSUMED** 2 mm tip depth from that floor reaches 0.79 into the existing pilot |
| **ASSUMED** lid and screw | Lid head-bearing surface Y 15.50 with pads bearing at Y 8.50; M2.5 × 12 pan-head screw, length measured under the head |
| Nominal reach | Tip at Y 3.50: 7 mm through the lid, then 4.79 in the body, including 1.21 in the newly drilled web and 3.79 in the old pilot; 4.10 remains to the back plane |

**Conditional.** This permanently modifies the original body. The screws can be removed for service, but the new holes cannot be undone. The lid holes must be clearance holes, not the provisional lid's Ø2 threaded pilots: **ASSUMED** Ø2.7 clearance for M2.5, subject to the actual screw and print. The floor and pad positions need checking before choosing this length. The indicated body reach is only geometric engagement, not a guarantee of 4.79 mm of full-strength thread: the screw point, existing hole condition, plastic, alignment and actual thread profile matter. The Ø2.18 hole is described as an M2.5 pilot, not a verified thread; use a screw appropriate to the measured plastic and pilot, not a presumed machine thread.

Use a guided drill and a depth stop measured from the floor; deliberately entering the old pilot is the intended breakthrough. Check that the actual drill point at the proposed stopped depth opens the full web to its required diameter, rather than leaving a constriction. An overshoot or off-axis drill can damage the pilot, boss or back face, and swarf can enter the bay or existing opening. Remove and protect electronics and collect debris before any separately authorized work. Tightening or repeated service can split or strip the limited plastic; there is no spare original thread once it is stripped. A repair insert or larger screw would require a further body modification and suitable surrounding material, neither established. This method cannot provide four original-body speaker screws or guarantee a seal.

### B. Outside bezel or clamp

| Decisive number | Result |
| --- | --- |
| Outer depth | 15.50 - (-0.60) = 16.10, between the nominal front and back planes |
| Narrow wall | 49.00 - 48.25 = 0.75 in X at the outer side of the pocket; not a measured continuous lip or wall thickness everywhere |
| Corner rounds | R11 reported; this is a radius, not a measured undercut or snap-hook ledge |
| Driver clearance example | **ASSUMED** a 10 mm-deep driver entirely ahead of Y 15.50 reaches Y 25.50; a strap bearing there and against the nominal back spans 26.10 before its own thickness and clearance |

**Conditional; no body holes or new threads.** A friction-only sleeve has no demonstrated pull-off resistance, and rounded corners do not by themselves form a positive catch. A hook relying on a 0.75-wide front edge risks bending or splitting it; neither that wall nor R11 establishes enough bearing area or an undercut. The corner shape, contact surface and clear route around the body must be measured.

The more promising version is a two-part frame: a broad front baffle carries and independently retains the driver; a rear crosspiece or hooks bear on verified back areas; side arms with screws and captured nuts in the *new frame* pull those parts together across the body. The fasteners do not enter the original. They need a route around the outside and must not obstruct plugs, microSD access, microphones, cooling or wall mounting. A clip around the speaker bay alone cannot assume the divider is an accessible outside edge. A driver projecting 10 mm does not hold the lid on: the frame must restrain the baffle against a force toward +Y, and the baffle's own retainer must restrain the speaker. A strap over a module must bear on its housing or frame, never its cone or openings.

The clamp is removable for service if its parts and screws remain accessible, but is not demonstrably damage-free or secure until tested. It cannot establish a seal, speaker fit, adequate friction, or the original four-screw arrangement. Its actual grip length and force depend on where sound, connectors and rear edges allow contact; 16.10 is an envelope span, not a measured local grip.

### C. Adhesive or gasket only

| Decisive number | Result |
| --- | --- |
| Bond area | Available uninterrupted contact area on the pocket rim is unknown; the X-side wall difference is only 0.75 |
| Gap | 7 from pocket floor to nominal front plane; a flush lid needs its own supports or edge contact |
| Driver | **ASSUMED** 10 mm projects ahead of a flush reference plane; adhesive strength and lever load are unknown |

**Conditional for adhesive; no for an uncompressed gasket alone.** A suitable adhesive or double-sided tape might attach a light lid and its speaker if the actual surfaces, preparation, adhesive and load are validated. A loose gasket seals only when something else compresses it; it is not a fastener. Adhesion and compressibility can change with heat, cooling cycles, age, creep, contamination and surface finish; the material and temperatures here are unknown. A gasket also cannot seal the through hole or cable route by itself.

No hole is drilled, but adhesive can leave residue, mark or damage the body on removal, and repeated opening can require new tape or gasket. Permanent adhesive is a poor service choice. This option cannot promise safe speaker retention, a durable seal, clean removal, or access for repairs without a product-specific test.

### D. Back screw passes through the pilot into a lid boss

| Decisive number | Result |
| --- | --- |
| Existing pilot | 7.29 - (-0.60) = 7.89 deep from the back; it ends 1.21 before the floor |
| Distance to lid | 8.50 - (-0.60) = 9.10 from the nominal back bearing plane to a pad at the floor |
| **ASSUMED** clearance preparation | Open the 1.21 web and make the entire body path Ø2.7 clearance for an M2.5 screw; check actual screw, wall and boss before drilling |
| **ASSUMED** M2.5 × 14 | Under-head length from Y -0.60 reaches Y 13.40, nominally 4.90 into a pad starting at Y 8.50, with 2.10 remaining to Y 15.50 |

**No on the unmodified body; conditional after modification.** No screw that stays in the existing blind hole can reach a lid at the floor: the tip meets the 1.21 web. A rear-inserted screw can reach a lid boss only if that web is opened. To clamp the lid rather than merely bind in the body, the existing Ø2.18 path also needs clearance for the chosen screw; otherwise it threads into the body first. This permanently changes both pilot paths and removes their original screw-holding material. Check that the local Ø4.50 bosses and remaining material can survive it, and keep swarf away from electronics.

The 14 mm example assumes the screw head bears exactly at Y -0.60, with no bracket or washer thickness, and a suitably drilled blind lid boss with room for the screw tip. It is not a verified screw choice. The provisional lid's Ø2 holes pass through its pads and plate, so a blind, appropriately sized boss or another separate nut arrangement must be designed; the stated 2.10 is not proof of a closed front. Actual threaded length is less than the nominal 4.90 if the screw tip is tapered or the thread does not start at the boss entrance. An insert also needs a sized boss and installation clearance; it cannot cross the intact web by itself. Screws are removable, but the body changes are not. This method cannot restore stripped body pilots or avoid drilling, and it does not independently retain the speaker.

### E. External front plate, supported by Pi-bay fasteners or an outer shell

| Decisive number | Result |
| --- | --- |
| Pocket behind plate | Nominally the full 7 remains between Y 8.50 and a plate's underside at Y 15.50, less local bosses, intrusions and wiring |
| **ASSUMED** plate | 1.6 thick, from Y 15.50 to Y 17.10; gasket thickness and compression are not included |
| **ASSUMED** driver entirely on plate | 10 deep from Y 17.10 to 27.10, or 11.60 beyond Y 15.50; mounting flange and grille may add more |
| Pi pilots | (±11.5, ±29), 23 × 58 pattern; attachment direction, available engagement and sharing with the Pi are unverified |

**Conditional.** Unlike an inset lid, an external plate does not consume the pocket's 7 mm simply by sitting on the front plane. A rearward-projecting driver, its terminals, a gasket or plate supports do consume that space. For comparison, **ASSUMED** a 10 mm-deep driver seated at the floor reaches Y 18.50, 3 mm beyond the front plane; an external plate must have an opening or be raised to avoid it. The seller-reported 44 × 28 × 15 module, **ASSUMED** seated at the floor, projects 8 mm beyond the plane and also needs an opening and its own retainer. Rounded corners and module tabs may still prevent fit.

An external shell can grip the body as in B without drilling it, and a new baffle can carry the actual square speaker with its own mounting features. The four Pi pilots are not front lid bosses and are already associated with Pi mounting. A bracket sharing them would need confirmed access, screw direction, engagement, Pi clearance and an assembly sequence; forming new threads changes the pilots. Do not assume a front screw can reach them through the closed face. If existing verified threads can be reused without alteration, that variant may avoid body modification; otherwise it modifies the body or is not feasible. Shell screws in new parts are removable; shared Pi fasteners may require removing the Pi. Neither support proves that the pocket is sealed, or that the plate clears the HAT, microphones and connectors.

### F. Through-bolt in the central opening

| Decisive number | Result |
| --- | --- |
| Existing passage | Ø10 through hole, with Ø18 counterbore opening toward +Y; counterbore depth and local bearing surfaces are unknown |
| Position | X 31.625, Z 0, only 0.875 in X from the pilot line at X 32.5 |
| Nominal reach | Back plane to floor is 9.10; back plane to front reference is 16.10, before plate, washers, nut and any clearances |

**Conditional; no drilling or threading of the body.** A bolt and back washer through the existing passage could pull a new plate or stand-off toward the body, with its nut or insert in the new plate. Size and length depend on the measured counterbore, bearing areas, actual plate and washer thickness, and nut engagement; no bolt length is established. Provide a bearing or spacer that does not crush the counterbore edge and locating features that prevent a single central attachment from rotating. Do not tighten against unsupported plastic. The screw and plate are removable, subject to access and avoiding damage.

This fastener occupies the center of the proposed speaker location and may collide with a magnet, rear vent or terminals. It also competes with any cable using the same Ø10 passage, and a washer or bolt can obstruct an acoustic opening. A single bolt alone does not establish a stable four-corner baffle, a speaker retainer, or an airtight chamber.

### G. Rear bracket screwed into the two existing pilots

| Decisive number | Result |
| --- | --- |
| Pilot path | Ø2.18, 7.89 deep, 36.50 center-to-center |
| **ASSUMED** screw reach | A screw extending 6 mm beyond its bracket into a pilot stops 1.89 before the nominal end; actual full-thread engagement is less if its tip is tapered |
| Arm reach | From nominal back Y -0.60 to a baffle at Y 15.50 is 16.10 before bracket and baffle thickness; clearance around the outside is unknown |

**Conditional.** A rear bracket can be retained by those pilots and carry arms around the outside to a separate front baffle, without drilling through the floor. It avoids relying on friction or the 0.75 wall, but loads the two small bosses and must clear ports and wall mounting. The screw length depends on bracket and washer thickness, the real bearing surface, point shape and pilot depth; do not bottom out. **ASSUMED** the existing pilots can take suitable screws without splitting. Forming threads in an unthreaded pilot is a permanent alteration of the body, even without drilling; the source does not establish that the pilots are already threaded. Reusing existing undamaged threads would avoid that alteration, if verified. The bracket is removable, but repeated service may strip the pilots. It cannot use the pilots as front through-holes or promise four original-body mounts, fit, or a seal.

## Recommendation

For a first physical investigation, try **B: a mechanically closed outside clamp with a separate baffle**, not a friction-only sleeve or a hook on the thin bay wall. Put the clamp screws and nuts in the new frame and provide a separate speaker retainer. This preserves the original holes and allows adjustment and disassembly, while leaving the original square speaker and its unknown mounting pattern open. It is a test candidate, not a proven design: the available outer contact patches and routes around connectors are not established. If those patches do not exist, do not force the frame; reconsider the central-hole or rear-bracket options. Do not drill the original for A or D merely to make the existing lid work.

## What would settle this

The cheapest initial test is a small printed pair: a representative body-edge scrap including the 0.75 pocket-side wall, the proposed front and rear bearing surfaces, and the local R11 profile, plus one short adjustable clamp segment. **ASSUMED:** the scrap uses the intended body material, print orientation and local dimensions; these must be measured or selected before printing. It is a contact-and-strength coupon, not a whole enclosure or a guarantee that the entire frame clears the body. Use no actual speaker and do not load an original body during this screening.

Measure the intended complete supported assembly's weight first. Hold the scrap and pull the clamp in the +Y opening direction with a force gauge, recording the first visible slip, deformation or failure and the peak force reached. **ASSUMED:** for an initial screening target only, use twice the measured complete assembly weight expressed as force, to allow for more than static self-weight; this factor is not a safety certification. Stop at that target if there is no slip or damage: report the result as at least that force, not an unmeasured ultimate strength. A failure below the target rejects this coupon; a pass only justifies trying a full frame after separately authorized fit and load checks in all intended orientations, including wall mounting, vibration, heat, repeated service and connector clearance.

The single deciding measurement for this first candidate is **the coupon's +Y pull-off force at first slip or damage, or the verified no-slip force reached if stopped at the target**. A clear photo of the original assembled speaker and what its four screws enter would instead help reconstruct the historical mounting, but would not prove the new clamp's strength. No coupon, frame, lid or speaker has been printed or fitted for this study. Physical printing and testing require separate authorization.
