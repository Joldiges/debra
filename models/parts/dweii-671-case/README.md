# DWEII 671 case: tub and lid

**Two printable parts, modelled from the components rather than around a guess.
Not printed, not fit-tested, and two of its dimensions come from a seller
listing that contradicts itself.**

Editable SolidCraft source: [`dweii-671-case.sc`](dweii-671-case.sc).

This is step 3 of the [enclosure pipeline](../../../docs/design/enclosure-arrangements.md#how-a-case-is-actually-built-from-these-models):
the first complete case, built to hold the parts James actually selected — the
[DWEII 701715519671 module](../../components/dweii-speakers/README.md), a Pi Zero
2 W and the [ReSpeaker HAT](../../components/respeaker-2mic-hat/README.md).

| Measure | Value |
| --- | --- |
| Overall | **71.02 × 54.37 × 33.2 mm** |
| Interior | 66.22 × 49.57 × 28.4 mm |
| Tub | **26 160 mm³** (`measure`) |
| Lid | **8 986 mm³** (`measure`) |
| Walls, floor, lid | 2.4 mm |
| Screws | 4 × M2.5, Ø2.2 pilots, Ø2.7 lid clearance |
| Corners | 5 mm rounds; the wall thins to 1.3 mm on the corner diagonal |
| Edges | 2 mm round on the base, 1.2 mm on the lid's top, 0.6 mm chamfer under the lid |
| Grille | Ø26 through, stepped to Ø28 × 1 mm at the face |
| Module stop | two ribs 1.5 mm thick across the cavity at Y 15.4–16.9, 0–5 mm and 23–28.4 mm high |

## What it looks like

![Isometric view of a box with rounded vertical corners and a rounded base, a round stepped speaker opening on the front face, a small rectangular slot in the left side, and a lid with four screw holes, two tiny holes and one elongated slot](assets/iso.png)

*Isometric. The Ø26 mm grille is the speaker opening, centred on the module, with
a 1 mm step at the face so the opening reads as a machined edge rather than a
hole. The slot in the left wall is the power inlet. On the lid: four screw holes,
two Ø1.5 mm microphone ports near the back, and an 11 × 3.5 mm slot over the three
status LEDs.*

![Front view: a wide rectangle with rounded corners and a centred circular opening with a stepped rim](assets/front.png)

*Front. 71 mm wide, 33 mm tall, one centred Ø26 mm opening. The module is 44 mm
wide, so there is about 11 mm of blank baffle each side — the same space the
screw bosses use. The front face is 31 mm tall and the opening is 26 mm, which
leaves 2.5 mm above and below it: there is no room for a ring, a bezel or a
recessed panel around the speaker, so the detail has to be the step at the
opening itself.*

![Side view showing the depth, the lid, and the power slot in the wall](assets/side.png)

*Side. The front face is on the right. The power slot sits at 15.7 mm above the
interior floor, which is the height of the HAT's micro-USB socket.*

![The tub with the lid removed: four screw bosses, two ribs across the cavity, the grille opening through the front wall, and the power slot](assets/open.png)

*Interior. Two full-height bosses at the front, two short ones thickened into the
back wall. The front pair sit in the free space beside the module because the
boards are 65 mm wide in a 66.2 mm cavity, leaving no room for a boss at the back
corners. The two ribs across the cavity are the module stop: they leave a 0.4 mm
gap to the speaker module's back face so it cannot slide backwards, and the slot
between them at 5–23 mm high is where the speaker lead leaves.*

## With the device inside

![The same tub with the lid off and the device in it: the speaker module against the front grille, the Pi and HAT behind it, and the four bosses around them](assets/loaded.png)

*Loaded, lid off. The speaker module stands against the front wall with the
grille opening behind it; the Pi and the HAT lie behind the module; the two front
bosses sit in the free margin beside the speaker and the two rear ones are
thickened into the back wall. This is what the case is for.*

![The concept assembly with the lid on: a rounded box with a stepped round grille on the front and a slot in the left side](../../assemblies/debra-compact/assets/iso.png)

*Closed. The same object with the lid on — see the
[concept assembly](../../assemblies/debra-compact/README.md) for the other views.*

`loaded.png` is shot from the assembly, because this design holds the case only
and has no components to put in it.

## Why it looks like this

James's own Fusion 360 model
(`RPiSpeaker_v17.step`, OneDrive, 2026-05-18) is the reference for the finish
expected here: a slim back plate, 66.15 × 75.30 × 16.10 mm, whose outline is a
rectangle blended into a round speaker pod with r = 11 mm tangent arcs, every
edge filleted at 1.0–1.3 mm, a recessed ring around the speaker, and a Pi Zero
pocket with four posts on a 58 × 23 mm pattern.
Its speaker opening is Ø18 over a Ø10 inner ring. It has **no four-screw square
speaker mount**: the speaker side is a 31.85 × 66 × 7 mm pocket with two M2.5
pilots 36.5 mm apart and the Ø10 hole at its centre, so the square mount James
remembers is either a separate part that was never exported or a different
revision. Even the post diameter is unresolved — Ø4.76 mm in
[the extraction](../../components/rpispeaker-v17/README.md), Ø8 mm in an earlier
read of the same STEP.

What carried over is the treatment of edges: 5 mm rounds on the four vertical
corners, a 2 mm round on the base, 1.2 mm on the lid's top edge, a 0.6 mm chamfer
under the lid so the joint reads as a shadow line, and the step at the grille.
The one thing that could not carry over is the organic outline. A Ø18 speaker in
a 16 mm plate leaves room for a shaped silhouette; a 44 × 28 × 15 mm module in a
28.4 mm cavity does not — the case is 33 mm tall and the Ø26 grille is 26 mm of
that, so the front face has 2.5 mm above and below the opening and there is
nowhere to put a pod, a bezel or an inset panel. The shape is therefore a
rounded box, and the design effort goes into the edges.

Two consequences worth knowing before printing:

- The 5 mm corner rounds leave a **1.3 mm wall** on the diagonal at each corner,
  where the outer round cuts in and the inner cavity corner stays sharp. That is
  the thinnest part of the part and it is a fillet, not a flat wall, so it prints
  as three perimeters at most.
- The 2 mm round on the base and the 1.2 mm round on the lid mean the case
  **cannot stand on a sharp edge**, which is the point; it also means the base
  contact area is smaller, so it is more likely to rock on a warped bed.

## The layout it holds

Front to back, in the case's own frame (Y = 0 at the module's front face):

| Y | What |
| --- | --- |
| 0 … 15 | the DWEII module, standing on its 15 mm edge, grille against the front wall |
| 15 … 19 | 4 mm gap; the HAT's 3.5 mm jack pokes into it and is therefore **unusable** |
| 19 … 49 | the Pi Zero 2 W with the HAT on top, HAT's header edge at the back |
| 40.34 | the two microphone ports, 8.66 mm inboard of the boards' back edge |

The stack is 20.7 mm tall at its highest point (the HAT's Grove connectors), so
the 28.4 mm interior is set by the **module**, not the electronics.

## Why the boards face this way

This is the one real design decision in the file, and it is a trade:

- **The HAT's header edge goes to the back**, which puts its two microphone
  ports at the back of the lid. If it went the other way, the ports would sit
  8.66 mm behind a 28 mm tall speaker and would be shadowed by it — a source at
  conversational height 1 m away would be below the module's top edge as seen
  from the port.
- **The cost:** the Pi's own micro-USB, USB and mini-HDMI ports are on the long
  edge *opposite* its 40-pin header, so they end up facing the speaker and are
  enclosed. So are the HAT's 3.5 mm jack and both Grove connectors.

**The device is therefore expected to be powered through the HAT's micro-USB
socket**, which is on a short edge and gets the 9 × 3.6 mm slot in the left wall.
Seeed document that socket as the way to supply the amplifier's current, and it
feeds the 5 V pins of the header — but **whether it back-feeds the Pi has not
been tested**, and if it does not, this layout needs rework. That test needs a
cable and two hands.

## What is real and what is assumed

| Input | Status |
| --- | --- |
| Board outline 65.02 × 29.97, mounting holes, header position | **sourced** from the Pi and HAT published layouts |
| Microphone port positions (±29.465, 8.66 mm from the header edge) | **sourced** from the HAT's Eagle board file |
| HAT connector positions (jack, Grove, JST, micro-USB) | **sourced**, same file |
| Pi Zero 2 W outline | dimension-sourced |
| Module 44 × 15 × 28 | **a seller claim**, and the same listing also says 31 mm wide |
| Ø26 mm grille | **invented** — the module's real opening is unpublished |
| Interior height 28.4 | the module's claimed height + 0.4 mm for a foam pad |
| All component heights (Grove 6.5, button 5, jack 4) | typical values, not measured |

## What is missing

- **The module stop limits travel, it does not clamp.** Two ribs 0.4 mm behind
  the module's back face mean it can move 0.4 mm and no further, which is a
  rattle rather than a loose part. A 0.4 mm foam pad closes it; foam is not
  modelled.
- **No speaker-lead routing.** The module's 110 mm lead and its JST plug have to
  get to the HAT's JST socket at Y ≈ 20–28. The lead's exit point on the module
  is unknown.
- **No board retention.** The Pi sits on the floor with 0.6 mm clearance and no
  standoffs; nothing locates it horizontally.
- **No ventilation.** Fine for a Zero 2 W; not fine for a Pi 5.
- **No feet, no cable strain relief, no grille mesh or fabric.**
- **The lid is shown assembled, not in print orientation.** It prints flat.
- **The [DWEII carrier](../dweii-671-carrier/README.md) is not used here.** It is
  41.6 mm tall and this interior is 28.4 mm, so it cannot be a wall of this case.
  It remains useful as a fit-test coupon for the module alone. The pocket is
  built into the tub instead.
- **Not printed, not fit-tested.** Every number above could still be wrong, and
  the module's width is the most likely to be.

## Parameters worth changing first

| Parameter | Change it when |
| --- | --- |
| `MOD_L` | the module arrives and is 31 mm wide, not 44 |
| `MOD_D`, `MOD_H` | the module's depth or height is measured |
| `GRILLE` | the module's real opening is measured |
| `GAP_M2B` | the jack is to be made usable, or the speaker lead needs room |
| `MIC_X`, `MIC_Y` | a ruler check on the HAT moves the ports |

## Regenerate

```
screenshot({ source: "model", grid: false, axes: false, width: 1300, height: 850,
             camera: { target: [0,24,14], yaw: 0.75, pitch: 0.35, distance: 230 },
             path: ".../assets/iso.png" })
screenshot({ source: "model", grid: false, axes: false, width: 1300, height: 850,
             camera: { target: [0,24,14], yaw: 0, pitch: 0.05, distance: 175 },
             path: ".../assets/front.png" })
screenshot({ source: "model", grid: false, axes: false, width: 1300, height: 850,
             camera: { target: [0,24,14], yaw: 1.5708, pitch: 0.12, distance: 200 },
             path: ".../assets/side.png" })
// interior: hide the lid body, shoot, show it again
browser.visibility({ items: ["Lid"], visible: false })
screenshot({ source: "model", grid: false, axes: false, width: 1300, height: 850,
             camera: { target: [0,24,8], yaw: 0.62, pitch: 0.72, distance: 215 },
             path: ".../assets/open.png" })
browser.visibility({ items: ["Lid"], visible: true })
```

`loaded.png` cannot be shot here: it comes from
[the concept assembly](../../assemblies/debra-compact/README.md), where the lid is
a body that can be hidden:

```
// in debra-compact.sc
browser.visibility({ items: ["Lid"], visible: false })
screenshot({ source: "model", grid: false, axes: false, width: 1300, height: 850,
             camera: { target: [0,25,10], yaw: 0.7, pitch: 0.8, distance: 215 },
             path: ".../assets/loaded.png" })
browser.visibility({ items: ["Lid"], visible: true })
```
