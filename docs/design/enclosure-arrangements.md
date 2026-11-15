# Enclosure arrangements: why the stack looked wrong, and what to do instead

James, 2026-11-15, on the first reference assembly: *"ugly and awful … the
speaker could be on top of a sideways pi0 instead of the side of it. Basically
making an upsidedown T instead of a straight line."*

He is right, and the useful part is that the complaint is about a **layout
decision, not a part**. The parts were fine; the arrangement was a plank.

**This is design reasoning, not a built or tested design.** The only model is
[the upright reference assembly](../../models/assemblies/zero2w-respeaker-upright/README.md),
and it is parts in space.

## Two corrections from the speakers James actually chose

The three speakers in the [main README](../../README.md#speakers) are DWEII
**enclosed modules**, not bare drivers: each has its own plastic housing and its
own internal chamber. They are modelled in
[dweii-speakers](../../models/components/dweii-speakers/README.md).

That changes the reasoning above in two ways:

1. **A case does not need to provide a back volume.** The Ø40 bare-driver model
   was the reason the upright arrangement wanted a big sealed body. With a
   module, the case only has to *carry* it — and it must **not** seal it, because
   the module may have its own vents. A compact case is therefore viable, and the
   tall inverted T is no longer the only answer.
2. **The right shape to design around is a rectangle.** The
   [speaker-candidates](../../models/components/speaker-candidates/README.md)
   envelopes are cylinders, which is the cone and not the housing. A pocket cut
   to a cylinder does not fit a rectangular module.

The arrangement question is therefore **open again**, and it is now bounded by a
fact rather than a guess: the HAT's microphones are **top-port**, so its
component side must face open air. See below.

## How a case is actually built from these models

James asked whether the component models become the negative for a case. They
should, and that is the intended pipeline:

| Step | Artifact | Exists? |
| --- | --- | --- |
| 1. Component envelope | `models/components/*` — the space each part occupies | yes; the HAT's positions are now **sourced from Seeed's board file**, not estimated |
| 2. Carrier / cavity part | a printable part whose pocket is the envelope plus clearance | yes: the [DWEII carrier](../../models/parts/dweii-671-carrier/README.md) |
| 3. Case shell | walls, baffle, openings, cable exits | yes: the [DWEII 671 case](../../models/parts/dweii-671-case/README.md), a tub and lid |
| 4. Product assembly | case parts + components in one file, showing the finished device | yes: [debra-compact](../../models/assemblies/debra-compact/README.md), with the case and the HAT linked |

Step 2 is where the envelope earns its keep: the pocket is derived from the
envelope, not guessed, so correcting a component dimension changes the part. The
carrier's pocket is `MOD_L + 2*CLEAR` wide for exactly that reason. The first part
built this way is the
[DWEII carrier](../../models/parts/dweii-671-carrier/README.md).

The case turned out **not** to use that carrier: it is 41.6 mm tall and the case
interior is 28.4 mm, so the pocket is built into the tub and the carrier stays a
fit-test coupon for the module on its own. That is worth knowing about step 2 —
a carrier designed in isolation gets ears and margins that a case cannot afford.

## What was actually wrong

| The old layout | Why it reads as wrong |
| --- | --- |
| Boards at one end, driver beside them | 105 × 40 mm footprint, 21 mm tall: a plank |
| Everything on one axis | no front, no top, no mass at the base — nothing tells you which way up it goes |
| The driver looks like an afterthought | it is the largest single object and it is stuck on the side |

A voice satellite on a nightstand is seen from the front and from above. A
105 mm plank is the worst of both: from above it is a long strip, from the front
it is a low fence.

## The constraint that decides everything

Before choosing an arrangement, one fact sets the rules:

> **The microphones are on a long edge of the HAT, and the HAT covers the whole
> Pi.**

That produces a chain:

1. The microphones need clear air, so that edge must be exposed.
2. The HAT occupies the entire board outline, so **nothing can sit on top of it**
   — no driver, no lid, no decor.
3. Therefore the driver must be **beyond** the boards: beside them in plan, or
   above them with a gap.

Point 2 is why "speaker on top of the Pi" cannot mean "resting on the HAT". It
means "above the stack, on something". That something is the case, and it is the
missing part in every arrangement below.

There is a second, softer constraint: **the microphone axis should stay
horizontal.** A two-mic array with its axis vertical cannot tell left from right.
Standing the boards on their *long* edge keeps the mic edge horizontal; standing
them on the *short* edge turns the array vertical. That is what forces the
65 mm dimension to be the width in the upright layout, and it is why the driver
(Ø40) ends up narrower than the body rather than wider.

## Three arrangements

| Arrangement | Footprint | Height | Good | Bad |
| --- | --- | --- | --- | --- |
| **A. Flat plank** (the old model) | 105 × 40 | 21 | lowest; mics optimal; simplest tray; prints with no supports | reads as a prototype; no front; nothing to look at |
| **B. Upright, driver above** (the new model) | 75 × 40 | 78 | a real front and top; driver at head height; small footprint; the inverted T James asked for | the driver needs a neck the model does not have; the LEDs end up under the driver; a 78 mm tall object on a 40 mm base needs a weighted foot |
| **C. Speaker as the base** | 65 × 45 | ~55 | lowest centre of mass; the driver gets a big sealed chamber in the plinth; nothing can tip it | sound fires down or forward from near the table; the mic edge is at the top, close to the driver; looks like a hockey puck |

**Recommendation: B, with the driver on a neck and a heavier foot.** It is the
only one that produces a front, a top and a base, which is what "not a plank"
means. It is also the only one where the driver is at a sensible height for
speech that is aimed at a person standing or sitting nearby.

C is the safest and the dullest; it is the right answer if the device is meant
to disappear into a shelf. A is still the right answer for a bare board that
gets tucked behind something.

## What B forces you to accept

| Forced by B | Consequence |
| --- | --- |
| Driver above the boards | the case must bridge from the boards to the driver: a neck, 15 mm deep and 40 mm wide |
| Driver is 21 mm deep, boards are 14 mm deep | the driver overhangs the stem front and back; the neck has to be the widest part of the stem |
| Driver needs back volume | the volume behind it has to be *sealed and inside* the case, not the open space around the boards |
| Boards stand on their long edge | the base must be deep enough not to tip: at 78 mm tall, 40 mm deep is the minimum, and a steel plate or a battery in the base is better |
| LEDs under the driver | a light pipe, or move the LEDs to a hole in the front face |
| Microphones at the bottom front | they must not be blocked by the base lip, and the port must not face into a corner |

## Design rules for this lane

Written down so the next model does not have to relitigate them:

1. **Give it a front.** One face carries the driver and the microphone ports;
   everything else is plain. Two decorated faces is how a design looks homemade.
2. **Wide base, narrow stem, round head.** The inverted T is the whole idea; do
   not widen the stem to match the driver or the shape collapses back into a box.
3. **No visible fasteners on the front.** Screws go in the back or the base.
4. **One cable.** USB-C enters at the back near the base, and nothing else
   leaves the case except the driver's lead, which stays inside.
5. **The driver is the only circle.** Do not add round corners, round buttons and
   a round grille as well; pick one.
6. **Nothing decorative that is not also structural** — a grille is a hole
   pattern that stiffens the panel, a plinth is weight and cable room.

## What used to block this, and no longer does

**The microphones are top-port.** Their ports face out of the HAT's component
side, Ø0.325 mm, on a 1.1 mm package. This was the open question; it is now
sourced from the MEMSensing datasheet and the V2.0 schematic —
[see the research note](../research/2026-11-15-respeaker-microphone.md).

That converts a guess into a rule, and it is a demanding one:

- The HAT's component side must face **open air**. Not a case wall, not a lid,
  not a driver, not another board.
- The HAT must therefore be the **front** board of the stack, with the Pi behind
  it. The "HAT behind the Pi" variant is dead.
- The 11 mm gap to the Pi is **not** an acoustic path, so it does not need to stay
  open for sound — only for the header and for cooling.
- Anything over the microphones is directly in the acoustic path. A grille or
  cloth has to be tested, not assumed transparent.

That is why the upright arrangement puts the HAT in front with its microphones low
and clear, and why the LEDs lost their place to them.

## What still blocks a real case

The HAT's component **positions** are still estimates — the mics are known to be
at opposite ends, but not their coordinates — so a hole cannot be cut for
anything yet. Nothing here has been printed or fit-tested. See
[the enclosure lane](enclosures.md) for the rest.

