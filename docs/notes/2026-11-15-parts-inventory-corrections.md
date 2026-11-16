---
title: Corrections to the R01 parts inventory
date: 2026-11-15
type: project-learning
status: unreviewed
task: R01
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - docs/notes/2026-11-15-parts-inventory.md (the note under correction; read unchanged, 430 lines)
  - docs/notes/2026-11-15-research-notes-review-round-2.md (R01 findings H1-H2, M1-M6, fourteen Low)
  - docs/evidence.md; docs/work/cards/R01.md; docs/project-brief.md
  - models/components/dweii-speakers/README.md; models/parts/dweii-462-case/README.md; models/parts/dweii-671-case/README.md
  - docs/comparisons/devices.md; docs/design/audio-outputs.md; docs/design/enclosures.md
  - docs/research/2026-11-15-respeaker-microphone.md; docs/notes/2026-11-15-pi-zero-microphone-paths.md
  - docs/notes/2026-11-15-respeaker-trixie-driver.md; docs/notes/2026-11-15-audio-and-enclosure-corrections.md
  - docs/testing/results/2026-11-15-lab-pi5-silence-and-hang.md; docs/archive/readme-research-before-2026-11-15.md
  - https://www.pishop.us/product/usb-c-pd-power-supply-for-raspberry-pi-5-27w-etl-listed/ (re-read 2026-11-15)
  - https://www.pishop.us/product/raspberry-pi-zero-2-w/ and https://www.pishop.us/search.php?search_query=zero+2+w (re-read 2026-11-15)
  - https://www.seeedstudio.com/ReSpeaker-2-Mics-Pi-HAT.html (re-read 2026-11-15)
supersedes: []
---

# Correct the R01 inventory without overstating what is now known

The [parts inventory](2026-11-15-parts-inventory.md) is preserved unchanged; this
note lists what a reader must not rely on until the inventory is revised. Two
findings can misdirect a purchase: the $59.90 headline prices a speaker whose
described 2.5 mm connector probably will not mate with the HAT's speaker socket,
and the closing "Buy…" paragraph is a purchase instruction for a combination
that has never been run, in a note that elsewhere says no combination is claimed.
Six medium findings are narrower: two senses of "reused", a second-supply line
resting on the v1 board's wiki page, three uncited storage figures, a house-brand
supply labelled official, a brief-required 3.5 mm path with no part and no cost,
and value judgements presented as findings. **Until these are fixed, quote the
totals only as arithmetic, not as the price of a working unit.** Every arithmetic
total in the note reproduces (verified by hand); the defects are in what the
numbers are attached to.

| # | Severity | Current text (line) | Replacement text | What I verified |
| --- | --- | --- | --- | --- |
| H1 | High | "DWEII **701715520462**, 8 Ω **5 W** (5.5 W max), JST-PH 2.5" (153), priced into the headline total (57, 242) | "The HAT's speaker socket is not vendor-specified: Seeed's product page lists no speaker connector, and the repository's parse of Seeed's published v1 Eagle file reads a **2.0 mm** right-angle JST, which `docs/design/enclosures.md` calls 'looks like JST-PH 2 mm' — an inference, not a vendor statement. The 462 is described as **JST-PH 2.5**, a pitch JST-PH does not normally use, so its plug **probably does not mate** and must not be assumed to. The 671/664 are described as JST-PH 2.0 and are the only priced modules that plausibly mate. The 462's pitch is unconfirmed." | `dweii-speakers/README.md:39-41` (pitches), `dweii-462-case/README.md:44-49` ("PH normally denotes 2.0 mm pitch, so the 2.5 mm description needs checking"), `enclosures.md:113-115`, `respeaker-microphone.md:77` (v1 `.brd` parse). Seeed page re-read 2026-11-15: part list is "HAT x1", no connector pitch. The review says both facts are in the note's own source rows; the 2.5 pitch is, the 2.0 socket is not — it is only in the files above |
| H2 | High | "**Honest recommendation for a first unit:** do not optimise to $40. Buy the Zero 2 W **with header** (in stock as £17.30, GBP) plus the V2 HAT and a 32 GB card, and accept ~$60–70 complete." (317-321) | "**Provisional preference, not a recommendation — needs coordinator decision.** The only combination with a Debra test record is Pi 5 + 2-Mics v2 (`[T]`, devices.md:124); no Zero-class build has been run. The Zero 2 W with header is out of stock at both US sellers [P4][P6] and in stock at The Pi Hut for £17.30 incl. VAT [P7], so a UK purchase is priced in GBP and cannot be added to the USD lines in this note. The ~$60–70 figure is the USD total ($59.90, $68.35) using the US-listed board, not a total for the GBP purchase. US import duty, shipping and VAT treatment are unknown and excluded." | Note lines 91-93 forbid adding currencies; 112-113 and 325-329 record the stock; 408 says "No supported combination is claimed". `devices.md:124` marks only the Pi 5 row `[T]` |
| M1 | Medium | "The ~$40 goal is plausible only in the reused-parts sense, using historical speaker prices." (62) | "Two different reuses are meant here. **Reused parts** (table B) = the Pi too is owned, $16.40. **Reused accessories** = a new board with the PSU, microSD and printer owned; that is the brief's $40 case, and routes 1-3 reach it ($31.35-$37.15) only on historical speaker prices and none is a complete unit." | `project-brief.md:124-127`: "$40 is a goal for an economical unit when users already have some of the USB cable, power source, microSD, and access to a 3D printer". Routes at 289-296 buy a new board, contradicting "only in the reused-parts sense" |
| M2 | Medium | "Seeed's cited guidance asks for board power when using the speaker [P20]" (188); $68.35 total (58, 246-247) | "[P20] is the **v1** hardware-overview wiki page: this repository's own registers identify it as documenting the WM8960 board. Seeed's v2 product page, re-read 2026-11-15, lists no separate power input. The $68.35 line is therefore a scenario about the v1 board, not an estimate for a v2 build. Whether the v2 board needs or accepts a second 5 V supply is `unknown`; whether two supplies may sit on the same 5 V rail at once was never asked and is also `unknown`." | `pi-zero-microphone-paths.md:513` (S21: "v1 board: WM8960 … JST 2.0"), `respeaker-trixie-driver.md:429` (S12 "v1 hardware overview"), `dweii-671-case/README.md:144-149` (socket documented, back-feed untested). The review's "the v2 page documents no POWER port" is consistent with the page I re-read but absence there is not proof about the wiki |
| M3 | Medium | Rows citing "[P14]" for the 64 GB PiShop card (176), the Adafruit 64 GB card (177) and the Adafruit 8 GB SDHC (178) | Mark all three `unknown` — no citation recorded — or cite the actual seller page. [P14] covers only the SanDisk Ultra 32 GB, the official A2 32 GB and the SanDisk 32 GB with Pi OS. No total uses these rows, so no total changes. | [P14]'s own URL is a single product page, `microsd-card-32-gb-class-10-blank`, and its recorded contents (24) list only the three 32 GB items. The review counts four affected rows; from [P14]'s text I can only identify **three** |
| M4 | Medium | "Official Raspberry Pi 27 W USB-C PD PSU … PiShop **USD** $11.95 [P15]" (189), used in the $135.90 dev total (270) | "USB-C PD PSU, 27 W, ETL-listed — **PiShop house brand, SKU 492-2** — $11.95 [P15]. The official Raspberry Pi 27 W supply (SC1158/SC1153) is **$12.95** on the same site. The dev total with the official unit is $136.90." | Re-read the [P15] page 2026-11-15: brand "PiShop", SKU 492-2, $11.95, in stock; related products SC1158/SC1153 at $12.95. 135.90 + 1.00 = 136.90 |
| M5 | Medium | "The exact 3.5 mm headphone routing is unverified." (164) — and no 3.5 mm part anywhere in the note | "The brief requires external speakers through supported 3.5 mm outputs (`project-brief.md:77-78`). This inventory prices no 3.5 mm cable, adapter or powered speaker, so that requirement carries no cost line at all. The only evidence is narrow and negative: on one specimen, with nothing in the jack, the `HP` tap measured ≈ −100 dBFS against −21 dBFS on `Line`, which locates the speaker on the line tap but does not show the jack is dead. See the decision section." | `project-brief.md:77-78`; `lab-pi5-silence-and-hang.md:31-35`; `audio-outputs.md:114-118` ("the jack is untested") |
| M6 | Medium | "Cheap supplies are a false economy here, and this is not a price question." (196); "the better *value* line item" (137) | Label as judgement: "**Judgement (`hypothesis`), not a finding:** cheap supplies are a poor risk here. The single supporting record is one lab specimen whose rail sagged under load with its original supply; no supply was measured and no cheap supply was tested." Same for "better value" — a preference, with its reason stated, not a result. | `evidence.md:12-21` requires labels per claim; `lab-pi5-silence-and-hang.md:111-113` records a supply *change*, not a measurement |
| L1 | Low | "Two of the four sellers here (Seeed, Waveshare) ship from China" (88) | "Two of the six sellers here (Seeed, Waveshare) ship from China" | Sources [P1]-[P22] name Adafruit, PiShop, Seeed, Waveshare, The Pi Hut and Amazon |
| L2 | Low | Zero W at PiShop $17.25 (108) and Zero 2 W at PiShop $17.25 (109) | Keep both prices; add "max 1 per customer" to the Zero 2 W row and cite the product page rather than the search page. **The review's finding does not reproduce.** | Re-read 2026-11-15: `/product/raspberry-pi-zero-w/` is a separate live listing at $17.25, "Choose Options"; `/product/raspberry-pi-zero-2-w/` is $17.25, "Maximum Purchase: 1 unit", schema `OutOfStock`. Two real products at the same price |
| L3 | Low | "**\"Notify Me\"** — out of stock" (109) | "Out of stock (product-page schema [P5]); \"Notify Me\" appears on the PiShop search listing [P21]" | Re-read 2026-11-15: the Zero 2 W product page shows no Notify Me control and its schema says `OutOfStock`; the search results page shows "$17.25 … Notify Me". The label is real, the citation is wrong |
| L4 | Low | "Two are documented as 4-packs [P18]; the 671 is not." (386); "Two of the three DWEII modules are sold as **4-packs**" (348-349) | "All three appear in 4-pack listings [P18]: the 664 ASIN is the same 4-pack product family as the 671, and the 462 is a 4-pack. Whether any module can be bought singly is `unknown`." | `dweii-speakers/README.md:40` ("**Same 4-pack product family as 671**") and `:41` (462, "4-pack") |
| L5 | Low | "plus the HAT ($12.90) and a speaker ($2.50–3.50) lands at **$31.35–$37.15**" (64-65) | "plus the HAT ($12.90), a speaker ($2.50–$3.50) and, for a bare Zero, a 2×20 header ($0.95) lands at **$31.35–$37.15**" | 15.00 + 12.90 + 2.50 = 30.40; the quoted 31.35 only follows with the $0.95 header, which route 1 includes (291) and the prose omits |
| L6 | Low | "the \"WH\" / \"with header\" variants and the Pi 5 do not" (212-213) | "the \"WH\" / \"with header\" variants ship with the header fitted, as does the Pi 5" | Reads backwards as written. The separate "with header" SKU at a higher price supports "unpopulated by default" for the base boards; the Pi 5 header is not verified from a repository source in this pass |
| L7 | Low | "Whether the Waveshare HAT includes a mating 2×20 socket … is `unknown`" (215-216) | Ask it of both: "Whether either HAT includes a mating 2×20 socket is not stated on either package list [P10][P11] and is `unknown`." | Seeed's re-read part list is "HAT x1"; [P11]'s is "HAT + speaker + screws". The question was asked of one vendor only |
| L8 | Low | "so it needs no separate amp and no second power supply" (137-139) | "so it needs no separate amplifier. It does not follow that it needs no second supply: a 1 W/ch amplifier draws its current from the Pi's 5 V rail — the same load path Seeed warns about for the 2-Mics board [P20]. Whether the WM8960 HAT needs or accepts a separate supply is not in [P11] and is `unknown`." | Internal consistency: the note's own second-supply argument (188) is about amplifier current, which the WM8960 also has. Physics plus [P11]'s silence; not measured |
| L9 | Low | "a bought case ($4.95–$11.95) that does not fit a HAT stack anyway" (303) | "a bought case ($4.95–$11.95) that is not documented as fitting a HAT stack (§7)" | 226 says "might clear a HAT; not verified" and 228-229 says "do not assume it fits or fails". 303 asserts the negative without a source |
| L10 | Low | "A cheap \"ReSpeaker\" at $8 [P19] is a V1 or a clone." (337) | "The $8 listing [P19] is a **Keyestudio** ReSpeaker V1 — a third-party board, not a Seeed SKU. Whether it is a clone of Seeed's design or an independent WM8960 board is `unknown`, and a clone codec may enumerate differently." | `readme-research-before-2026-11-15.md:53` identifies "Keyestudio ReSpeaker … ReSpeaker V1 … $8" |
| L11 | Low | "bought Zero cases: HiPi Zero Friction $7.45 …" (31) | "Zero case listings seen: HiPi Zero Friction $7.45 …" | 377 says "No part was bought, and no cart was assembled". Source-register typo |
| L12 | Low | "Adafruit $19.80 [P4]" (240) | No number change. Add "single same-day read; not re-checked" | **The review's finding is unverified.** [P4] records $19.80 out of stock, no repository source contradicts it, and I did not fetch Adafruit. Treat as one dated read |
| L13 | Low | "Editorial correction: OpenCode, `openrouter/openai/gpt-6.1-terra`, variant unknown." (46) | "Editorial correction: OpenCode, `openai/gpt-6.1-sol`, variant unknown — the recorded author of the linked correction note" (or drop the attribution) | `2026-11-15-audio-and-enclosure-corrections.md:7-8` records author "OpenCode coordinator", author_model `openai/gpt-6.1-sol`. The provider prefix differs too |
| L14 | Low | microSD extension cable, $6.95 (179); USB-C card reader, $6.95 (208) | Add a citation for each, or mark "**no citation recorded** — price as read, seller page not captured" | Both rows carry no source key. Overlaps M3's second half |

## Decisions, not wording

### H1 — which speaker, and what connector

Corrected fact: the HAT's socket pitch is an inference (2.0 mm, from the v1
board file); the 462's is a seller claim of 2.5 mm, a pitch the JST-PH family
does not normally use. Neither end is vendor-confirmed for a v2 board.

- **A. Headline uses a 671/664 module** (described JST-PH 2.0). Cost: no change
  to $59.90; the historical $2.50 applies; the enclosure changes from the 462
  carrier to the 671 case, which already exists as an unprinted design.
- **B. Keep the 462 and price an adapter lead.** Cost: one 2-pin JST lead,
  roughly $1 but **not sourced here**, plus an unknown risk that the 2.5 mm plug
  is a different series entirely.
- **C. Defer the speaker line and mark the total incomplete.** Cost: no total can
  be quoted; the honest position becomes "HAT and board priced, speaker
  unpriced".

**needs coordinator decision.** A test with the parts in hand would settle it;
nothing here authorises buying them.

### H2 — whether R01 may recommend a first unit

Corrected fact: only Pi 5 + 2-Mics v2 has a test record; no Zero-class build has
been run; the recommended board is out of stock in the US on the stated date.

- **A. Withdraw the recommendation** and leave two estimates plus the stock
  finding. Cost: R05 gets no first-unit guidance, which is honest.
- **B. Keep it as a labelled provisional preference** with the tested
  combination named and duty/import unknown. Cost: a reader may still act on it.
- **C. Move the recommendation to the coordinator** after an independent
  re-review of R01, as the round-2 review asks.

**needs coordinator decision.** The card also says "Do not edit shared buying
recommendations" (`docs/work/cards/R01.md:24`).

### M5 — the 3.5 mm path the brief requires

Corrected fact: the brief requires supported 3.5 mm external-speaker outputs; the
inventory prices no part for it; the only evidence is that the headphone tap was
at the noise floor on one specimen with nothing plugged in, which does not prove
the jack is unusable.

- **A. Price a 3.5 mm cable and a powered speaker** and add a fourth total. Cost:
  both unpriced in every source read here — the note cannot state a figure
  without new sources.
- **B. Defer the path** until headphones are plugged in and each tap tested;
  that audible test is not currently authorised (`audio-outputs.md:114-118`).
- **C. Record the requirement as unmet** for the priced build and leave the JST
  speaker as the only costed output.

**needs coordinator decision.**

## What remains unknown

- **The 462's connector pitch.** "JST-PH 2.5" is a seller string; PH normally
  means 2.0 mm. No plug was measured and no photograph was parsed.
- **The v2 board's power input.** Whether it has one, needs one, and whether a
  second 5 V supply may share the rail. The cited page documents the v1 board.
- **The 3.5 mm jack's actual routing.** Nothing was plugged in; `HP` at the noise
  floor with an open jack proves neither routing nor function.
- **GBP prices and duty.** £17.30 board and £11.50 supply are not converted, and
  no US import duty or handling figure exists anywhere in the project.
- **All three Amazon listings.** HTTP 503 again for the review; the speaker
  prices used in every total remain undated historical values, and pack quantity
  is unknown even though all three appear in 4-pack families.
- Also unverified here: whether any bought case clears a HAT stack; whether the
  WM8960 HAT needs a second supply; the $19.80 Adafruit price; Adafruit stock.

## What I did not do

No purchase, no cart, no measurement, no device contact, no CAD or code change,
and no edit to the note under correction. Prices and stock were re-read from
three PiShop pages and one Seeed page on 2026-11-15; Adafruit, Amazon, Waveshare
and The Pi Hut were not re-read, so their rows are as the original note left
them. This note is unreviewed and is not an approval of any hash.
