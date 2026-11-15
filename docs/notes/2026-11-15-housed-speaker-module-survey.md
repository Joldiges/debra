---
title: Housed speaker modules 30 to 110 mm, surveyed against the DWEII envelopes
date: 2026-11-15
type: project-learning
status: unreviewed
task: none
author: OpenCode subagent
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - "[P1] https://www.adafruit.com/product/3351 — Mono Enclosed Speaker 3W 4 Ohm (2026-11-15)"
  - "[P2] https://cdn-shop.adafruit.com/product-files/3351/C5282-001_datasheet__1_.pdf — factory speaker specification and outline drawing for 3351 (2026-11-15)"
  - "[P3] https://www.adafruit.com/product/4445 — Mono Enclosed Speaker with Plain Wires 3W 4 Ohm (2026-11-15)"
  - "[P4] https://www.adafruit.com/product/1669 — Stereo Enclosed Speaker Set 3W 4 Ohm (2026-11-15)"
  - "[P5] https://www.adafruit.com/product/4227 — Mini Oval Speaker with Short Wires 8 Ohm 1 Watt (2026-11-15)"
  - "[P6] https://cdn-shop.adafruit.com/product-files/4227/C13238-001+spec+RB-2030008G-046LR-E+for+C13238-001++%281%29.pdf — Dongguan Fuxin RB-2030008G-046LR-E specification and drawing (2026-11-15)"
  - "[P7] https://www.adafruit.com/product/3369 — Mini External USB Stereo Speaker (2026-11-15)"
  - "[P8] https://www.waveshare.com/product/accessories/misc/speakers/8ohm-5w-speaker.htm — 8Ω 5W Speaker, SKU 14595 (2026-11-15)"
  - "[P9] https://www.pishop.us/product/waveshare-8-5w-speaker — Waveshare 14595, dimensions and hole spacing (2026-11-15)"
  - "[P10] https://www.waveshare.com/product/accessories/misc/speakers/8ohm-2w-speaker.htm — 2030 Cavity Speaker 8Ω 2W, SKU 27745 (2026-11-15)"
  - "[P11] https://www.waveshare.com/product/accessories/misc/speakers/8ohm-2w-speaker-b.htm — 2030 Cavity Speaker Type B, SKU 27859 (2026-11-15)"
  - "[P12] https://www.amazon.com/dp/B0B4D1BN4F — DWEII 701715519671 listing bullets, 4 pcs, JST-PH2.0, 31 × 28 × 15 mm (2026-11-15)"
  - "[P13] https://www.amazon.com/dp/B0BHST51PQ — DWEII 701715520462 listing bullets, JST-PH2.5, 100 × 45 × 21 mm (2026-11-15)"
  - "[P14] https://www.amazon.com/dp/B0B4D2Z35P — DWEII 701715519664: returned a 3.7 kB Amazon stub with no product content (2026-11-15)"
  - "[P15] https://diyables.io/products/8-ohm-5w-double-cavity-speaker-with-jst-ph-2.5mm-2-pin-connector-100x45mm-rectangular-audio-speaker-module-with-wire — second seller of the 100 × 45 × 21 double-cavity module, 92 × 36 hole spacing (2026-11-15)"
  - "[P16] models/components/dweii-speakers/README.md — the three modelled envelopes, their sources and caveats (repository, 2026-11-15)"
  - "[P17] models/parts/dweii-671-case/README.md and models/parts/dweii-462-case/README.md — pocket and grille sizes actually modelled (repository, 2026-11-15)"
  - "[P18] docs/notes/2026-11-15-parts-inventory.md — HAT and speaker price/stock context, TPA2005D1 claim for the 2-Mics v2 (repository, 2026-11-15)"
supersedes: []
---

# Housed speaker modules 30 to 110 mm, surveyed against the DWEII envelopes

## Summary

**Eight publicly sold housed speaker modules were checked against the three
DWEII envelopes this repository models.** One is a near-exact substitute for the
5 W `701715520462`: the Waveshare 14595, same 100 × 45 × 21 mm envelope, with
**92 × 36 mm mounting holes** that the DWEII listing never publishes. Three
others (two Waveshare "2030" cavity speakers and the Adafruit 4227) are a
**smaller class** — 20 × 30 × 5–7 mm — that would sit inside a 671-sized pocket
rather than fill it. The Adafruit 70 × 30 mm enclosed family is well documented
but **26 mm longer** than the 671 envelope, so it is a new baffle, not a pocket
change. **Nothing in this note is measured, and no supplier was contacted.**

The single most useful side-effect: the current Amazon listing for
`701715519671` says **31 × 28 × 15 mm**, not the 44 mm this repository models
[P12][P16]. If 31 mm is right, the model is 13 mm too long and the "smaller
class" above is nearly the same length as the owned module.

## Scope and method

- **In scope:** a plastic- or metal-housed speaker *module* whose longest
  published edge is roughly 30–110 mm, sold publicly, with a published size and
  a described way to connect it. The unit of interest is the **housing a pocket
  must accept**, not the cone.
- **Out of scope:** bare drivers with no housing (the ten catalogue drivers in
  [speaker-candidates](../../models/components/speaker-candidates/README.md)
  already cover that), phone/laptop pull-outs with no public listing, and any
  module with no published dimensions (the Seeed Grove Speaker publishes
  4.0–5.5 VDC and an LM386 amplifier but no size, so it was dropped).
- **No measurements.** Every dimension below is a **published claim** by a
  reseller, a marketplace seller, or a component factory. Nothing was bought,
  opened, calipered or played.
- **No supplier contact.** No form, e-mail, chat or quote request was sent. No
  purchase, cart or back-order was started.
- **Labels used:** `upstream-documented` = a vendor spec sheet or factory drawing
  states it; `reported` = marketplace or product-page copy states it; `hypothesis`
  = my inference; `unknown` = no usable source. Nothing here reaches `tested`.

## The three owned envelopes (baseline)

| Module | Modelled envelope | Published claim | Connector | Notes |
| --- | --- | --- | --- | --- |
| 701715519671 | 44 × 28 × 15 mm [P16] | **31 × 28 × 15 mm** on the current listing [P12]; 44 × 28 × 15 mm on the spec sheet the repo cites [P16] | JST-PH 2.0, 2-pin, 110 mm lead [P12][P16] | Sold as **4 pcs** [P12]. The listing's own copy says "4 ohms 8 ohms" — sloppy |
| 701715519664 | 44 × 28 × 15 mm, inherited [P16] | No module size published; page unreadable this session [P14] | JST-PH 2.0, 480 mm lead [P16] | Identity is an inference from the shared listing text [P16] |
| 701715520462 | 100 × 45 × 21 mm [P16] | 100 × 45 × 21 mm [P13] | JST-PH 2.5, 2-pin [P13] | Listing also says "Rated power: 3 (W)" while claiming 5 W/5.5 W in the same paragraph [P13] |

Both baselines are **seller claims**. The `701715520462` figure is the
best-sourced of the three (two statement sets agree), the `701715519664` figure is
inherited, and the `701715519671` figure is now contradicted by its own listing.

## The candidates

| Module | Type | Published dimensions | Connector | Supply | Separate amplifier? | Where the sound leaves |
| --- | --- | --- | --- | --- | --- | --- |
| **Waveshare 14595** ("8Ω 5W Speaker") [P8][P9] | Sealed plastic cavity, rectangular | **100 × 45 × 21 mm**; mounting holes on **92 × 36 mm** [P9] | **4-pin** header ("4PIN speaker header") [P8]; pitch not stated | **None** — passive | **Yes** | Front grille over the cavity. Rear face not documented [P8] |
| **Adafruit 3351** (mono enclosed 3 W 4 Ω) [P1][P2] | Moulded plastic tub, closed back | **70.1 × 30.7 × 16.5 mm** (drawing); page says 30 × 70 × 17 [P2][P1] | Page: JST-PH ≈2.0 mm. Drawing legend: "HOUSING: 2.54-2P … 51021", 28 AWG [P2] | **None** — passive | **Yes** | Front oval recessed grille; the back view is a plain panel with four corner holes, **no port drawn** [P2] |
| **Adafruit 4445** (same, plain wires) [P3] | As above | **31 × 70 × 17 mm**; holes 3.1 mm [P3] | **Bare tinned wires**, 30 cm | **None** — passive | **Yes** | As 3351; only page photos, no drawing [P3] |
| **Adafruit 1669** (stereo pair) [P4] | Two of the same module on one lead | **30 × 70 × 17 mm** each; holes 3.1 mm [P4] | One "SPK" plug, "similar/compatible with JST-PH" [P4] | **None** — passive | **Yes** | As 3351 [P4] |
| **Adafruit 4227** (mini oval 8 Ω 1 W) [P5][P6] | Stamped oval frame, perforated front | **30 × 20 × 5 mm**; drawing 20.0 × 30.0, 4.8 thick [P5][P6] | **Molex PicoBlade 1.25 mm, 2-pin**, ~10–13 mm lead [P5][P6] | **None** — passive | **Yes** | Front perforated oval cover over cloth, **front only**; frame closed behind [P6] |
| **Waveshare 27745** ("2030 Cavity Speaker") [P10] | Cavity module, 2 W 8 Ω | **20 × 30 × 5.5 mm** [P10] | **4-pin PH1.25**, 150 mm [P10] | **None** — passive | **Yes** | Front grille; "built-in sound cavity"; rear not documented [P10] |
| **Waveshare 27859** ("2030 Type B") [P11] | Cavity module, 2 W 8 Ω | **20 × 30 × 6.8 mm** [P11] | **2-pin PH1.25**, 120 mm [P11] | **None** — passive | **Yes** | Front grille; rear not documented [P11] |
| **Adafruit 3369** (USB stereo speaker) [P7] | Active bar with two drivers | **84 × 43 × 32 mm** [P7] | **USB-A**, USB 2.0 audio | **5 V over USB** [P7] | **No** — amplifier and DAC built in | Front-firing drivers per the page photo; any rear port is **unknown** [P7] |

Two cross-checks worth keeping:

- A **second seller** lists the same 100 × 45 × 21 double-cavity module with
  **92 × 36 mm hole spacing** and a **JST-PH 2.5** connector [P15], which matches
  the Waveshare 14595 envelope and hole pattern but not its connector. Same OEM
  housing with two different leads is a `hypothesis`, not a finding.
- The Waveshare 14595 page lists the **WM8960 Audio Board** among the products it
  fits [P8], and this repository's parts note records that the WM8960 HAT ships
  with **one 8 Ω 5 W speaker** [P18]. That the bundled speaker *is* the 14595 is a
  `hypothesis`; no page states it.

## Envelope comparison

Delta is candidate minus the modelled envelope; **negative means it fits inside**.

| Candidate | L × W × D | vs 671 (44 × 28 × 15) | vs 462 (100 × 45 × 21) | Verdict |
| --- | --- | --- | --- | --- |
| Waveshare 14595 | 100 × 45 × 21 | +56 / +17 / +6 | **0 / 0 / 0** | **Drop-in substitute for the 462**, if the 4-pin lead is re-terminated |
| Adafruit 3351 | 70.1 × 30.7 × 16.5 | **+26.1 / +2.7 / +1.5** | −29.9 / −14.3 / −4.5 | New baffle; would swim in a 462 pocket |
| Adafruit 4445 | 70 × 31 × 17 | +26 / +3 / +2 | −30 / −14 / −4 | Same as 3351, plus bare wires |
| Adafruit 1669 (each) | 70 × 30 × 17 | +26 / +2 / +2 | −30 / −15 / −4 | Same, but you get two |
| Adafruit 4227 | 30 × 20 × 5 | **−14 / −8 / −10** | −70 / −25 / −16 | Fits inside a 671 pocket with a holder |
| Waveshare 27745 | 30 × 20 × 5.5 | −14 / −8 / −9.5 | −70 / −25 / −15.5 | Same |
| Waveshare 27859 | 30 × 20 × 6.8 | −14 / −8 / −8.2 | −70 / −25 / −14.2 | Same |
| Adafruit 3369 | 84 × 43 × 32 | +40 / +15 / +17 | −16 / −2 / **+11** | Too deep for either; USB changes the design |

Two caveats on that table. First, **"fits inside" is not "fits"**: the modelled
671 case presents a **Ø26 mm** baffle opening [P17], and a 20 × 30 module's cone
is smaller than that, so a candidate that fits the pocket still needs a new
baffle opening and a cradle for a part with no screw holes (4227, 27745, 27859 all
have **no mounting holes at all**). Second, the 671 baseline itself is disputed:
against the **31 mm** listing figure [P12] the Adafruit 70 mm modules are +39 mm,
and the 20 × 30 family is roughly the same length but 8 mm narrower and 8–10 mm
thinner.

## Which are plausible alternatives, and why

**To the 5 W `701715520462` — yes, one.** The Waveshare 14595 is the same
100 × 45 × 21 housing with documented 92 × 36 mounting holes [P8][P9][P15]. It
needs no CAD change to the pocket, only a decision about its 4-pin lead. It is
the only candidate in this survey that is dimensionally interchangeable with an
owned module.

**To the 3 W `701715519671` / `701715519664` — no drop-in was found.** The market
clusters at two sizes: 20 × 30 × 5–7 mm (Waveshare cavity speakers, Adafruit 4227)
and 70 × 30 × 17 mm (Adafruit enclosed family). Nothing published lands on
44 × 28 × 15, and nothing lands on 31 × 28 × 15 either. So the honest options are:

1. **A smaller module plus a holder** (27859 is the neatest: 2-pin, 6.8 mm deep,
   $1.99 list [P11]). This is plausible only if 2 W and a roughly 20 mm cone are
   enough. It also shrinks the required grille, which the current Ø26 opening
   would over-expose.
2. **A longer module and a new front end** (3351/4445). The 3351 is the
   best-documented part in the survey — a real factory drawing with 63.79 × 24.11
   mounting-hole spacing [P2] — but 70 mm does not fit a 71 mm-wide case that also
   has to clear a Pi Zero, and its depth is 1.5 mm more than modelled.
3. **Not the 3369.** It is the only module here that needs no amplifier, but
   32 mm of depth and a USB host port make it a different product, not a
   substitute.

**Impedance is a separate mismatch.** All three owned modules are 8 Ω; the
Adafruit enclosed family is **4 Ω** [P1][P3][P4]. The HAT's amplifier is not
rated for 4 Ω in anything this repository has verified — the 2-Mics v2 uses a
TPA2005D1 per the parts note [P18], and the WM8960 HAT is quoted at 1 W per
channel [P18]. Substituting a 4 Ω module changes current draw and heatsink load;
that is a `hypothesis` to test, not a reason to reject the part.

## Traps

1. **A passive speaker has no supply voltage.** Two DWEII listings say the buyer
   "can choose 3.3V or 5V" [P12][P13]; that is the **amplifier's** rail, not the
   module's. Every passive row above needs an amplifier, and its rail is the
   amplifier's business. Only the 3369 takes 5 V itself [P7].
2. **The 671's size contradicts itself inside the same project.** The repository
   models 44 mm from a spec sheet [P16]; the seller's current bullets say 31 mm
   [P12]. Both are claims. A 13 mm error in the longest edge is the difference
   between "the small modules fit with room" and "they are the same class".
3. **The 3351 page and its own datasheet disagree three ways.** Weight 26.4 g on
   the page [P1] versus 50 ± 0.5 g on the factory sheet [P2]; connector JST-PH
   ≈2.0 mm on the page [P1] versus a drawing legend reading "2.54-2P … 51021"
   [P2]; depth 17 mm on the page [P1] versus 16.54 mm on the drawing [P2]. Only
   one of those can be right, and the drawing is the more specific source.
4. **The 4445 and 3351 should be the same part but publish different holes.**
   3.1 mm on a 31 × 64 mm rectangle [P3] versus 3.4 mm on a 24 × 63 mm rectangle
   [P1] — and "31 × 64" is impossible on a 31 mm-wide body. Reseller copy is not
   a drawing.
5. **"4-pin" does not tell you the pitch or the pinout.** The 14595 and the 27745
   both use a 4-pin connector [P8][P10]; neither page states a pitch for the
   14595, and neither explains why a mono speaker needs four pins. Do not order a
   mating housing from this note.
6. **No mounting holes is a design constraint, not a detail.** The 4227 has none
   — it hangs on a 13 mm lead [P6] — and neither Waveshare "2030" module
   publishes any [P10][P11]. The Adafruit enclosed family does (four holes), the
   14595 does (92 × 36) [P9].
7. **The hole pattern is the missing DWEII fact.** The repository's 462 case has
   to retain the module somehow; the 92 × 36 spacing is published for the
   Waveshare and DIYables versions of that housing [P9][P15] but never for the
   DWEII ASIN [P13]. It is a `hypothesis` that they are the same housing.
8. **Amazon served the listing pages this session, unlike the earlier attempt.**
   `B0B4D1BN4F` and `B0BHST51PQ` returned full pages; `B0B4D2Z35P` returned a
   3.7 kB stub with no product content [P14]. A blocked page is not an empty
   specification.
9. **The 462 listing contradicts its own power rating** — "5.0W / 5.5W" in one
   bullet, "Rated power: 3 (W)" in the next [P13]. Do not build a thermal or
   amplifier budget on that copy.
10. **Depth is the quiet killer.** Every candidate that fails the 671 pocket
    fails by length, but the 3369 fails by depth (32 mm), and a HAT stack plus a
    32 mm module will not close a 28.4 mm interior [P17].

## Unknowns and blocked

- **No module was measured.** Every dimension is a published claim, including
  those from factory drawings. No part was bought or handled.
- **Acoustic openings are only partly documented.** Front grille yes for all
  eight; rear ports, passive radiators and internal chamber volume are `unknown`
  for every one. The 3351 and 4227 drawings show no rear opening, which supports
  "sealed back" as a `hypothesis`, not a fact. This matters because the whole
  "carry, do not seal" assumption rests on it [P16].
- **The 664 page could not be read** [P14]; its envelope remains inherited.
- **The 671's true length is unresolved** (31 vs 44 mm) [P12][P16].
- **No amplifier rating for the 2-Mics v2 is published here.** The TPA2005D1
  attribution comes from this repository's parts note [P18], which is itself
  `reported`; its behaviour into 4 Ω is untested.
- **No price/stock comparison was made** beyond incidental list prices seen while
  reading. Deliberately: the earlier parts note owns that, and prices moved twice
  in one day there [P18].
- **The Seeed Grove Speaker was dropped for missing dimensions**; it is an active
  5 V module with an LM386, so it would have been a useful "no external amp" row
  if the size existed.
- **DFRobot's product site timed out** from this session; no DFRobot module is
  included, and none is claimed to exist or not exist.
- **Pimoroni returned HTTP 429** (rate limited); no Pimoroni module is included.

## Verification and what was not done

- **Read, not run.** Pages were fetched over HTTPS and read as text; PDFs were
  converted with `pdftotext` and drawings rendered with `pdftoppm` at 300 dpi to
  read dimensions. Working files were kept in `/tmp/opencode/debra-spk/`, not in
  the repository.
- **No measurements**, no fit test, no print, no slice, no playback, no
  electrical test. Pass/fail: **not-run** for every physical claim.
- **No CAD change.** `models/` was read, not edited.
- **No supplier was contacted** and nothing was ordered.
- **Conflict kept visible:** the 671 length contradiction is stated rather than
  resolved, because resolving it needs a caliper, not a web page.

## Handoff and correction links

- **Current state:** a source-linked size survey of eight housed modules plus
  the three owned baselines, with vendor page keys and one factory drawing per
  Adafruit enclosed/oval family. Adds no measurement and changes no model.
- **What it adds:** the 14595 as a documented 462 substitute with a known hole
  pattern, the identification of a 20 × 30 mm class that fits a 671 pocket, and a
  second independent statement that the 671 is 31 mm long.
- **Supersedes:** nothing. It corroborates and extends
  [dweii-speakers](../../models/components/dweii-speakers/README.md), which
  already flags the 31/44 mm conflict, and does not contradict
  [parts-inventory](2026-11-15-parts-inventory.md).
- **Next bounded check (one):** put calipers on the owned `701715519671` and
  record length, width, depth, hole spacing and lead length in a new dated note.
  That single measurement decides whether the 20 × 30 class is an alternative or
  a downgrade, and whether the 671 case is 13 mm too long. No purchase, no
  network, no device.
- **Then, if wanted:** ask the repository owner whether a 4-pin-to-JST lead
  adapter for the 14595 is acceptable before any 462-case revision.
- **Authorization:** none of this is permission to buy, print, wire or test
  anything.
