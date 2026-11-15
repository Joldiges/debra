---
title: Complete alternatives comparison, revision 2
date: 2026-11-15
type: project-learning
status: unreviewed
task: R02
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - docs/notes/2026-11-15-complete-alternatives-comparison.md (R02, the note this revises; read 2026-11-15)
  - docs/notes/2026-11-15-research-notes-review.md (findings R02-1 to R02-7; read 2026-11-15)
  - docs/notes/2026-11-15-parts-inventory.md (R01; US prices dated 2026-11-15, reused with that date)
  - docs/evidence.md; docs/templates/learning-note.md; docs/project-brief.md; docs/comparisons/devices.md; docs/comparisons/music-playback.md; docs/comparisons/sources.md (read 2026-11-15)
  - https://www.home-assistant.io/voice-pe/ (re-read 2026-11-15: $69 / 59 EUR recommended MSRP; speaker described as audio feedback; stereo 3.5 mm jack)
  - https://support.nabucasa.com/hc/en-us/articles/25918770371229 (re-read 2026-11-15; page states last updated 2026-02-09: USB-C cable and PSU not in box, HA server required, not standalone)
  - https://ameridroid.com/products/home-assistant-voice-preview-edition.js (product JSON re-read 2026-11-15: $58.95, variant available true, SKU U0231)
  - https://cloudfree.shop/products/home-assistant-voice-preview-edition.js (product JSON re-read 2026-11-15: $58.95, available false)
  - https://www.seeedstudio.com/Home-Assistant-Voice-p-6998.html (fetched 2026-11-15; price/stock are client-rendered and were not readable — R02's $59.00 and 2-per-account record reused)
  - https://github.com/esphome/home-assistant-voice-pe/releases/tag/25.12.0 (2026-11-15: published 2025-12-17, "Add support for Sendspin multi-room audio protocol (public preview, works with Music Assistant)")
  - https://community.home-assistant.io/t/ha-voice-preview-edition-slow-to-play-audio/819069 (2026-11-15: thread from 2024-12-30; 20+ s and 20–50 s reports, fast STT/TTS, one of two units affected)
  - https://github.com/esphome/home-assistant-voice-pe/issues/257 (2026-11-15: "Some devices slow to play audio", opened 2024-12-31, state open)
  - https://github.com/music-assistant/support/issues/6643 (2026-11-15: closed 2026-10-14; reporter's closing comment names the access point and a busy 2.4 GHz channel)
  - https://github.com/music-assistant/support/issues/4921 (R02 record, 2026-02-08, reused as reported evidence)
  - https://www.music-assistant.io/player-support/sendspin/ (2026-11-15: "Sendspin is still in technical preview")
  - https://www.music-assistant.io/player-support/google-cast/ (2026-11-15: full support for Cast devices including Google Nest speakers; Sendspin on Cast "experimental and off by default")
  - https://www.music-assistant.io/player-support/airplay/ (2026-11-15, provider index; AirPlay path)
  - https://www.music-assistant.io/player-support/alexa/ (R02 record 2026-11-15; experimental self-hosted Alexa skill)
  - https://www.home-assistant.io/integrations/alexa_devices/ (R02 record 2026-11-15; cloud polling, MFA, no music)
  - https://shop.m5stack.com/products/atom-echo-smart-speaker-dev-kit.js (product JSON 2026-11-15: C008-C, $13.50, available true)
  - https://shop.m5stack.com/products/atom-echos3r-smart-speaker-dev-kit.js (product JSON 2026-11-15: C126-ECHO, $14.50, available false)
  - https://docs.m5stack.com/en/homeassistant/applications/voice_assistant/atom_echos3r (2026-11-15: "ESPHome version 2026.1.0 or later"; factory YAML imported with ref main; wake word plus announcements, no music)
  - https://raw.githubusercontent.com/m5stack/esphome-yaml/main/common/atom-voices3r-satellite-base.yaml (2026-11-15: project version 2026.10.0, min_version 2026.10.0, external component github://n-IA-hane/esphome-audio-stack@v2026.11.0, sendspin media source codecs FLAC/PCM)
  - https://futureproofhomes.net/products/satellite1-smart-speaker.js (product JSON 2026-11-15: $132.99 EU/UK, $134.99 US, all six variants available)
  - https://docs.futureproofhomes.net/satellite1-streaming-music/ (2026-11-15: multi-room synchronised music via Music Assistant; page banner says docs reflect Sat1 v0.2.2-beta.0)
  - https://www.apple.com/shop/buy-homepod/homepod-mini (2026-11-15: $149.00)
  - https://www.home-assistant.io/green/ (2026-11-15: $199 / 179 EUR)
  - https://www.nabucasa.com/link/ (2026-11-15: USD $6.50 monthly, $65.00 annual, tax not included)
  - https://heywillow.io/ (R02 record 2026-11-15; site content dated 2023)
  - https://github.com/HeyWillow/willow (R02 record 2026-11-15)
  - https://www.engadget.com/2197748/google-has-discontinued-the-nest-home-mini-and-nest-audio (2026-06-18, secondary reporting)
  - https://www.pcmag.com/reviews/amazon-echo-dot-5th-gen (2026-06-16, $79.99 list)
supersedes:
  - docs/notes/2026-11-15-complete-alternatives-comparison.md
---

## Summary

Revision 2 of the complete-alternatives comparison, after the independent review's
seven R02 findings. The original note is preserved unchanged; this note restates
the comparison with corrected cost arithmetic, no market-exclusivity claims,
per-row prerequisites, pinned versions and defined citations. Nothing was bought,
flashed or measured for this revision.

**Two corrected totals for building Debra.** USD, listed prices, 2026-11-15, US
sellers, **before shipping and tax**, no currency conversion anywhere. Every line
item is reused from the dated parts inventory [r01], which carries the seller and
stock cell for each part; this note does not re-derive them:

| Total | What it covers | Amount |
| --- | --- | --- |
| **A. Complete purchase** — one unit, everything bought new, voice + music, tested-hardware route | Pi Zero 2 W with header + ReSpeaker 2-Mics V2 + 32 GB microSD + one 5 V supply + one speaker at a *historical* price | **$59.90 listed**; **$68.35** with a second supply for the HAT's own power input |
| **A′. Complete purchase, every line priced** — untested hardware combination | same, with the WM8960 HAT (onboard 1 W/ch amp, bundled 8 Ω 5 W speaker) instead of the 2-Mics HAT | **$62.49 listed** |
| **B. Reused-parts** — Pi, supply, microSD and printer already owned | ReSpeaker 2-Mics V2 + one speaker (historical price) | **$16.40 listed**; **$17.35** if the owned board needs a 2×20 header |

Total A is **not** a complete price: it excludes an unpriced speaker amplifier, an
enclosure that has never been printed, shipping, tax and all labour. Total A′ is
the only fully-priced line-item build, and it is not the combination Debra has
tested. Total B is a **marginal** cost, not a unit price, and the brief forbids
presenting it as one ([brief][brief]).

**What the corrected numbers do and do not say.** Debra's complete-purchase parts
total ($59.90) is below the Voice PE's complete music setup as estimated here
($93.95–$139.00, of which only the $58.95 device price is sourced) and below the
Satellite1.1's US device price ($134.99, plus a supply the vendor requires and
does not include). It is **above** the two M5Stack pucks' device prices ($13.50
and $14.50), which are the cheapest buyable items in the table. The claim that
Debra is cheaper than every alternative is withdrawn. No figure here includes
labour, support, tax or shipping, so none of these totals is a cost-of-ownership
comparison; the alternatives also deliver capability Debra has not built.

**What the corrected evidence does not support.** No evaluated product offers
browser-based *maintenance* of its own configuration; the Voice PE does offer
browser/phone *onboarding*, which is a different thing and is documented. The
Satellite1.1 is the only one of the **seven products evaluated here** whose vendor
documents voice and music from one box and one supply. Nothing in this note
establishes market exclusivity in either direction.

## How to read this

Evidence labels follow [evidence.md][evidence]: `upstream-documented` (vendor or
project source states it, not reproduced here), `reported` (attributed user or
third-party observation, with date and context), `hypothesis` (an inference to
test), `unknown` (insufficient evidence — not "no"), `historical` (dated figure
kept for traceability), `tested` (a Debra test record names hardware, versions and
result). Every citation is a working link or a reference defined at the end of
this note; there are no bare numeric source keys.

Prices are USD unless the cell says GBP, and **GBP is never converted**. Each
price carries its seller and the date read. Stock is a same-day snapshot; several
rows moved during 2026-11-15 itself.

## The corrected comparison

Seven buyable products, one open project that is not buyable as a product, and
the Debra baseline. "Required to use it" is the minimum for the row's stated
function; "Optional" is genuinely optional.

| Alternative (exact variant) | What it is | Voice path | Music path | Price, seller, 2026-11-15 | Required to use it | Optional services | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **HA Voice Preview Edition** | assembled ESP32-S3 satellite, first-party | microWakeWord on-device; STT/TTS on your HA host or HA Cloud | Sendspin in firmware since 25.12.0 (2025-12-17, "public preview"); music needs a powered speaker on the 3.5 mm jack | **$58.95** ameriDroid (variant `available: true` on re-check; R02 read a pre-order note with no restock date the same day); **$58.95** CloudFree (**sold out** on re-check); Seeed $59.00 with a 2-per-account limit recorded in R02, stock not readable; MSRP $69 / 59 EUR | **HA server** (vendor: "not a standalone device"); 2.4 GHz Wi-Fi; USB-C cable + PSU **not in box**; powered speaker for music | HA Cloud/Link $6.50/mo or $65/yr for off-host STT/TTS; any local pipeline instead | `upstream-documented` [pe][pegs][pea][pec][pes][pefw] |
| **M5Stack ATOM Voice (C008-C)**, the "Atom Echo" | $13.50 ESP32 puck, 0.8 W amp | on-device **or** HA-server wake word, selectable | **no documented music path**; no Sendspin/media pipeline in the upstream ESPHome config | **$13.50** M5Stack direct, available | HA + ESPHome; you flash it; USB power; you own the YAML | HA Cloud or a local pipeline | `upstream-documented` [m5atom] |
| **M5Stack Atom VoiceS3R (C126-ECHO)** | $14.50 ESP32-S3 puck, one MEMS mic, 1 W | "Okay Nabu" per vendor app docs | **Sendspin exists in the vendor's satellite YAML only** — the vendor's own HA application page documents wake word and announcements, not music | **$14.50** M5Stack direct, **out of stock** on re-check (`available: false`); $34.99 Amazon and £13 Pi Hut as recorded in R02 | HA; ESPHome **2026.1.0 or later** per vendor docs, whose import uses `ref: main`; you flash it | HA Cloud or local pipeline | `upstream-documented` for both the prose and the YAML, and they disagree — see R02-6 below [m5s3r][m5docs][m5yaml] |
| **Satellite1.1 Smart Speaker** | $132.99–$134.99 assembled speaker, 25 W amp, 2-way drivers, printed enclosure | microWakeWord on-device (Okay Nabu / Hey Jarvis) | vendor documents Sendspin to Music Assistant with "no additional provider setup", stereo pairs and multiroom groups | **$134.99** US / **$132.99** EU-UK, FutureProofHomes direct, all variants available | **HA + Music Assistant**; 2.4 GHz Wi-Fi; **30 W USB-C supply** (vendor asks for it; not included) | Spotify Connect and AirPlay operation per vendor docs; MA DSP/EQ | `upstream-documented` [satprod][satmusic] |
| **Amazon Echo Dot (5th gen)** | mass-market Alexa speaker | Alexa cloud STT, conversation agent, TTS; **no local path and no HA wake-word satellite role** | only via the experimental self-hosted Alexa skill (public HTTPS endpoint + Amazon developer account) | **$79.99** list (`reported`, PCMag 2026-06-16); a $99.99 new-unit figure and Alexa+ $19.99/mo were `reported` secondary coverage in R02 and are not re-verified | **Amazon account**; internet; Amazon's cloud | HA Alexa Devices integration (cloud polling, mandatory MFA, vendor says music will not work that way); Alexa+ subscription | `upstream-documented` for the limitations [hax][alexa]; price `reported` [pcmag] |
| **Apple HomePod mini 2** | $149.00 Siri speaker | Siri; **cannot act as an HA voice satellite** | AirPlay 2 target for Music Assistant | **$149.00** Apple, all colours | **Apple ID, HomeKit home, iPhone/iPad to set up** | HA (not required for AirPlay playback); Music Assistant AirPlay provider | `upstream-documented` [apple][airplay] |
| **Google Home Speaker** | $99.99 Gemini-for-Home speaker; Nest Mini and Nest Audio discontinued 2026-06 | Gemini for Home; **no HA voice-satellite path** | Google Cast target for Music Assistant, not Sendspin | **$99.99** `reported` by launch coverage in R02; not re-verified | **Google account**; Google Home app for groups | HA (optional); Music Assistant Google Cast provider, documented for Cast devices including "Google's own hardware like the Google Nest speakers" | price `reported` [engadget]; provider `upstream-documented` [cast]; this specific 2026 model `unknown` |
| **Willow** (open project, not buyable new) | ESP-IDF firmware for ESP32-S3-BOX-3 hardware | on-device wake word and commands, or a self-hosted inference server | **no music path documented** — `unknown` | "approximately $50 hardware" is the project's own 2023 figure, `historical`; BOX-3 availability separate | BOX-3 hardware; a server for the Willow inference server | none documented | `upstream-documented` for the project, `historical` for the cost [willow][willowgh] |
| **Building Debra** (baseline) | Pi Zero-class board + audio HAT + Debra software | planned; **only the lab Pi 5** has run wake→STT→intent→TTS | Sendspin client on the host; **lab-verified on Pi 5 + 2-Mics HAT only** | Complete purchase **$59.90–$62.49**; reused-parts **$16.40** (both above, both excluding shipping/tax/enclosure/amplifier) | HA server; board + HAT + supply + microSD + printed enclosure; your time | HA Cloud or a local pipeline | `tested` for the lab Pi 5 [lab]; `hypothesis`/`unknown` for everything else |

### Practical limits, as reported by people who bought them

Attributed reports, not measurements. Each carries its own context, and the last
column is deliberately a **hypothesis** where a cause is suggested.

| Device | Report (attributed) | Source / date | Reading |
| --- | --- | --- | --- |
| Voice PE | Built-in speaker described as garbled and hard to hear at full volume | `reported`, community thread 2025-12-06, as recorded in R02 [r02] | Consistent with the vendor describing the speaker as audio feedback rather than music output [pe]. Not a measurement |
| Voice PE | Heavy clipping from the 3.5 mm jack into a powered speaker; the reporter hypothesises headphone-level rather than line-level output | `reported`, community thread 2025-12-24, as recorded in R02 [r02] | **Unresolved.** One report, one hypothesis, no vendor answer found. Test before trusting the jack for music |
| Voice PE | Music stuttered after firmware 25.9.0/25.10.0 and was fixed in a 25.11 pre-release | `reported`, ESPHome issue #455, as recorded in R02 [r02] | Firmware regressions reach users; you are on the vendor's release train |
| Voice PE | 20+ s (one poster: 20–50 s) between "responding" and playback while STT/TTS finished in about 3 s; the same reporter's **second unit did not show it**; an issue was opened | `reported`, forum thread from 2024-12-30 and issue #257, opened 2024-12-31, **still open** [slow][peissue257] | Device-specific behaviour in at least one case. Whether buffering, firmware, hardware or host is responsible is `unknown`; "pipeline latency is host-bound" is withdrawn as an unsupported causal claim |
| Voice PE | Sendspin playback dropped every 10–60 s (`close_code=1006`); the **reporter's** closing comment says the cause was the access point, a 2.4 GHz channel about 52 % busy, and that a cleaner channel resolved it | `reported`, MA issue #6643, opened 2026-10-05, closed 2026-10-14 [ma6643] | One resolved case with a named mechanism. A maintainer had first read the same logs as device-side. Not evidence that Wi-Fi is the general cause of every dropout |
| Voice PE | Long-playback skipping blamed by the reporter on cheap unshielded speakers next to the unit | `reported`, MA issue #4921, 2026-02-08, as recorded in R02 [r02] | Plausible analogue-audio trap; one report, no measurement |
| Voice PE | Wake word missed "even when clearly spoken directly at it" | `reported`, blog 2025-01-06, as recorded in R02 [r02] | Wake-word reliability is the most common complaint class in every row. Unmeasured |
| VoiceS3R | "Single mic, limited far-field range" | `reported`, aggregator page 2026-06-02, as recorded in R02 [r02] | Consistent with one MEMS mic and no array; still a report, not a test |
| Atom Echo (C008-C) | "Kind of quiet" | `reported`, shop review quoted in R02 [r02] | 0.8 W into a tiny cavity. Wattage is a rating, not a loudness measurement |
| Satellite1 | Vendor's own caveat: "at full volume the wake word may not be heard perfectly" | `upstream-documented`, vendor docs, as recorded in R02 [r02] | A loud speaker and a listening microphone compete |
| Satellite1 | Recurring cutouts on a multi-speaker Satellite1 house traced by the reporter to a neighbour's Wi-Fi channel changes | `reported`, MA issue #4921 comment 2026-02-12, as recorded in R02 [r02] | Multiroom sync is only as good as the 2.4 GHz band |

**On the 25 W amplifier.** The Satellite1's TAS2780 is rated 25 W, and the Voice
PE has no comparable amplifier. That is a **rating difference, not a measured
loudness difference**: output depends on driver sensitivity, enclosure, DSP and
listening position, none of which was measured here. No listening test exists for
any row, including Debra's.

## Finding-by-finding changes

| Finding | What changed | Where in this note |
| --- | --- | --- |
| **R02-1** cost: mixed-currency total, missing lines, unsupported "cheaper than everything" | Replaced with dated, variant-specific US line items reused from R01 at its own date; two separate totals (complete purchase, reused-parts) plus a fully-priced variant; GBP never converted; amplifier, enclosure, shipping and tax named as excluded; the "cheaper than every alternative" and "$30–50" claims withdrawn and replaced with a per-alternative comparison that names the two cheaper pucks | Summary totals table and the paragraph under it |
| **R02-2** exclusivity: "only", "nobody", over-broad reasons to build | Exclusivity claims removed; the one surviving "only" is scoped to the seven products evaluated here; browser **onboarding** separated from browser **maintenance**; per-product evidence separated from firmware-YAML evidence for the VoiceS3R; the brief's other goals retained | Summary last paragraph; comparison table, VoiceS3R and Voice PE rows |
| **R02-3** latency/quality: anecdote used as mechanism, dropouts generalised, wattage implying loudness | Reports kept attributed with dates and issue IDs; the 20–50 s case now records that the reporter's second unit was unaffected and that #257 is still open; "host-bound latency" withdrawn as a causal claim; the Wi-Fi root cause is limited to the one resolved report; the amplifier paragraph states a rating is not a loudness measurement | "Practical limits" table and the paragraph after it |
| **R02-4** HA dependency: one universal HA/cloud requirement | Replaced with a "Required to use it" column and an "Optional services" column per row; the vendor's own cloud-or-local choice is recorded for the ESPHome rows; Echo/HomePod/Google rows state their own ecosystem prerequisite and mark HA as optional | Comparison table |
| **R02-5** three-unit price: $180 as if it were three setups | Stated as a **devices-only** subtotal ($176.85 = 3 × $58.95) that excludes three supplies, three speakers, tax and shipping; a complete three-unit band is given with its estimate status labelled; the purchase route is marked unestablished (Seeed 2-per-account record, CloudFree sold out, ameriDroid quantity limit unknown); "an afternoon" withdrawn | "Three units, honestly" |
| **R02-6** versions: prose vs YAML conflict, wrong Cast citation | Exact versions and dates pinned: Voice PE firmware 25.12.0 (2025-12-17); VoiceS3R vendor docs "2026.1.0 or later" with a `ref: main` import, against a satellite YAML declaring project 2026.10.0 / min_version 2026.10.0 and external component `@v2026.11.0`; the disagreement is recorded rather than resolved; Satellite1 docs banner pinned to v0.2.2-beta.0; the Google row now cites the Google Cast provider page, with this specific 2026 model marked `unknown` | "Versions checked" and the comparison table |
| **R02-7** count and keys: "six" products, undefined `[S#]` keys | Count corrected to seven buyable products plus Willow plus the Debra baseline; every citation is now an inline link or a reference defined at the end of this note; no bare numeric keys anywhere | Summary, comparison table, "Sources cited in this note" |

## Three units, honestly

- **What $180 buys:** 3 × $58.95 = **$176.85 of devices only**, at the ameriDroid
  price. It does not buy three working music setups.
- **What it excludes:** three USB-C supplies and cables (the vendor does not
  include them), three powered speakers (the built-in speaker is feedback, not
  music), tax, shipping, and any enclosure work.
- **Complete three-unit estimate:** **$281.85–$417.00** before tax and shipping,
  using $10–20 per supply and $25–60 per powered speaker. Those two bands are
  **estimates carried from R02, not sourced listings**; the sourced part is the
  device subtotal.
- **Can three be bought from one seller?** `unknown`. Seeed's listing carried a
  two-per-account limit as recorded in R02. CloudFree was sold out on re-check.
  ameriDroid's product JSON shows one variant marked available with no stated
  quantity cap, and R02 recorded a pre-order note on the same day. A three-unit
  purchase route is not established, and "an afternoon" of setup time per unit is
  not evidenced for any row.

## Versions checked

Exact scope of every version claim in this note. All pages were read 2026-11-15
and all of them are mutable except the tagged release.

| Claim | Pinned version / scope | Date |
| --- | --- | --- |
| Voice PE supports Sendspin | firmware release **25.12.0**, published 2025-12-17; release note: "Add support for Sendspin multi-room audio protocol (public preview, works with Music Assistant)". Later firmware not examined here | 2025-12-17 |
| Sendspin stability | MA's own Sendspin page: "Sendspin is still in technical preview. It works, but expect it to change." No version pinned by MA | page read 2026-11-15 |
| VoiceS3R ESPHome floor (prose) | vendor HA application page: "ESPHome version 2026.1.0 or later"; the documented import fetches `examples/voice_assistant/atom-echos3r.factory.yaml` with `ref: main`, i.e. no pinned revision | page read 2026-11-15 |
| VoiceS3R music config (YAML) | `common/atom-voices3r-satellite-base.yaml` on branch `main`: `project: version 2026.10.0`, `min_version: 2026.10.0`, external component `github://n-IA-hane/esphome-audio-stack@v2026.11.0`, `sendspin` media source with `codecs: [FLAC, PCM]` | file read 2026-11-15 |
| **Prose vs YAML disagreement** | The vendor's prose says 2026.1.0 or later; the vendor's satellite YAML requires 2026.10.0 and a third-party external component at a specific tag. **Both are recorded; neither is chosen.** Whether any published build works at 2026.1.0 is `unknown` | 2026-11-15 |
| Satellite1 firmware | the vendor docs banner says the docs reflect **v0.2.2-beta.0**; current stable release was not re-checked in this revision (`unknown`) | page read 2026-11-15 |
| Satellite1 music path | vendor streaming-music page: multi-room synchronised music via Music Assistant, Sendspin streaming, stereo pairs, groups | page read 2026-11-15 |
| Google Home Speaker as a Music Assistant player | MA documents "full support for Google Cast based devices… Google's own hardware like the Google Nest speakers"; Sendspin on Cast is "experimental and off by default". The 2026 Gemini-era "Google Home Speaker" is not named on that page — `unknown` | page read 2026-11-15 |
| Voice PE latency issue | forum thread opened 2024-12-30; issue **#257** opened 2024-12-31 and **still open** at read time; the original thread is launch-era firmware, so treat the report as `historical` in mechanism, `reported` in content | 2024-12-30 / 2026-11-15 |
| Voice PE Sendspin dropout case | MA issue #6643, closed 2026-10-14 with the reporter's Wi-Fi/access-point explanation; reporter's firmware at the time 26.9.0, ESPHome 2026.6.0, MA 2.10.5 | 2026-10-14 |

## What is comparable, and what is not

- **Comparable:** device prices in USD from named sellers on one date; whether a
  speaker, supply or subscription is included; whether the vendor documents a
  music path; whether Home Assistant is required.
- **Not comparable:** GBP and USD totals (no exchange rate is invented here);
  parts-only against complete purchase; device price against cost of ownership;
  amplifier wattage against loudness; any "quality" claim, because nothing was
  measured; Debra's parts cost against any alternative's *delivered* capability,
  since Debra has not shipped a device.

## Still unknown

- **Debra's speaker amplifier.** The 2-Mics HAT has no amplifier and the modelled
  DWEII modules are passive. Unpriced, so total A is a floor, not a price.
  One sentence to settle it: read the lab record for what actually drove the
  speaker in the tested unit.
- **Debra's enclosure and filament cost.** Never printed, never priced.
- **Seeed's Voice PE price and stock** on the revision date. The page renders
  price and stock client-side; R02's $59.00 and 2-per-account limit are reused
  with their date rather than re-derived.
- **ameriDroid's real availability.** Product JSON said available, R02 recorded a
  pre-order note with no restock date, the same day.
- **Whether the VoiceS3R can be bought as a working music device.** The YAML
  exists; the vendor's product documentation does not describe music, and the
  unit was out of stock on re-check.
- **Whether three Voice PEs can be bought from one seller** at one price.
- **Whether the 2026 Google Home Speaker is a normal Music Assistant Cast
  player.** The provider page is generic; the model is not named.
- **Satellite1's current stable firmware** and whether the ESPHome and XMOS
  trains are in step; the docs reflect a beta.
- **Willow's current activity**, last-commit date and supported hardware.
- **All quality, latency and multiroom claims for every row, including Debra.**
- **Debra's labour, support burden and beginner success probability.**

## What would settle it

1. **Price the amplifier** from the lab record or a sourced listing — that is the
   only way total A becomes a price instead of a floor.
2. **Read the three Amazon DWEII listings** from a session Amazon will serve, and
   record pack quantity, per-unit price and stock. This is desk work; it converts
   the weakest number in both totals into a sourced one.
3. **Add one item to a cart at each Voice PE seller** and record quantity limits,
   shipping and tax — the only way the three-unit route stops being `unknown`.
4. **Install the VoiceS3R factory YAML at ESPHome 2026.1.0** and see whether it
   builds, which resolves the prose-versus-YAML disagreement with evidence rather
   than by choosing.
5. **Measure one thing:** Voice PE 3.5 mm output into a powered speaker, 60 s from
   Music Assistant, default volume, recorded — the single claim most likely to
   change a buying decision.
6. **Read the Google Cast provider's device list** for the 2026 Google Home
   Speaker by name, or leave that row `unknown`.

## Handoff and correction links

- **Current state:** a revision note, not a test report. Branch `main` at
  `b23ed98`. Nothing purchased, flashed, printed or measured; no device contacted.
- **What this supersedes:** only
  [the original R02 note](2026-11-15-complete-alternatives-comparison.md), which
  remains in place as the record of what was claimed first. It does **not**
  supersede [devices.md][devices] (hardware) or
  [music-playback.md][musicplayback] (transport); where they disagree with this
  note, they win on hardware and transport detail.
- **What prompted it:** findings R02-1 to R02-7 in
  [the independent review](2026-11-15-research-notes-review.md).
- **Earlier claim corrected:** the original note's "~$95–140 complete" Voice PE
  band was arithmetically fine but its power and speaker lines were estimates;
  the Debra "complete" figure mixed currencies and omitted lines; both are
  restated above.
- **Authorization:** none of this is permission to buy, flash, print or operate
  anything. Prices and stock move; re-check before acting.
- **Next action for the coordinator:** decide whether R05 may quote the corrected
  totals, and note that total B is a marginal cost that must never be presented
  as a retail kit price.

## Sources cited in this note

Every short reference used above is defined here. All were read on 2026-11-15
unless the entry says otherwise.

[pe]: https://www.home-assistant.io/voice-pe/
[pegs]: https://support.nabucasa.com/hc/en-us/articles/25918770371229
[pea]: https://ameridroid.com/products/home-assistant-voice-preview-edition/
[pec]: https://cloudfree.shop/product/home-assistant-voice-preview-edition/
[pes]: https://www.seeedstudio.com/Home-Assistant-Voice-p-6998.html
[pefw]: https://github.com/esphome/home-assistant-voice-pe/releases/tag/25.12.0
[peissue257]: https://github.com/esphome/home-assistant-voice-pe/issues/257
[slow]: https://community.home-assistant.io/t/ha-voice-preview-edition-slow-to-play-audio/819069
[ma6643]: https://github.com/music-assistant/support/issues/6643
[m5atom]: https://shop.m5stack.com/products/atom-echo-smart-speaker-dev-kit
[m5s3r]: https://shop.m5stack.com/products/atom-echos3r-smart-speaker-dev-kit
[m5docs]: https://docs.m5stack.com/en/homeassistant/applications/voice_assistant/atom_echos3r
[m5yaml]: https://raw.githubusercontent.com/m5stack/esphome-yaml/main/common/atom-voices3r-satellite-base.yaml
[satprod]: https://futureproofhomes.net/products/satellite1-smart-speaker
[satmusic]: https://docs.futureproofhomes.net/satellite1-streaming-music/
[apple]: https://www.apple.com/shop/buy-homepod/homepod-mini
[airplay]: https://www.music-assistant.io/player-support/airplay/
[cast]: https://www.music-assistant.io/player-support/google-cast/
[alexa]: https://www.music-assistant.io/player-support/alexa/
[hax]: https://www.home-assistant.io/integrations/alexa_devices/
[engadget]: https://www.engadget.com/2197748/google-has-discontinued-the-nest-home-mini-and-nest-audio
[pcmag]: https://www.pcmag.com/reviews/amazon-echo-dot-5th-gen
[willow]: https://heywillow.io/
[willowgh]: https://github.com/HeyWillow/willow
[brief]: ../project-brief.md
[evidence]: ../evidence.md
[devices]: ../comparisons/devices.md
[musicplayback]: ../comparisons/music-playback.md
[r01]: 2026-11-15-parts-inventory.md
[r02]: 2026-11-15-complete-alternatives-comparison.md
[lab]: ../testing/results/2026-11-15-lab-pi5-lva-sendspin.md
