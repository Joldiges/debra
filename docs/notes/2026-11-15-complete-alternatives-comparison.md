---
title: Complete alternatives compared with building Debra
date: 2026-11-15
type: project-learning
status: unreviewed
task: R02
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - https://www.home-assistant.io/voice-pe/ (read 2026-11-15)
  - https://support.nabucasa.com/hc/en-us/articles/25918770371229 (getting started, Voice PE; page last updated 2026-02-09)
  - https://esphome.io/projects/?type=voice (read 2026-11-15)
  - https://ameridroid.com/products/home-assistant-voice-preview-edition/ (read 2026-11-15)
  - https://cloudfree.shop/product/home-assistant-voice-preview-edition/ (read 2026-11-15)
  - https://www.seeedstudio.com/Home-Assistant-Voice-p-6998.html (read 2026-11-15)
  - https://shop.m5stack.com/products/atom-echos3r-smart-speaker-dev-kit (read 2026-11-15)
  - https://www.seeedstudio.com/ReSpeaker-2-Mics-Pi-HAT.html (read 2026-11-15)
  - https://thepihut.com/products/raspberry-pi-zero-2-w (read 2026-11-15)
  - https://www.apple.com/shop/buy-homepod/homepod-mini (read 2026-11-15)
  - https://www.nabucasa.com/link/ (read 2026-11-15)
  - https://www.home-assistant.io/green/ (read 2026-11-15)
  - https://www.music-assistant.io/player-support/sendspin/ (read 2026-11-15)
  - https://www.music-assistant.io/player-support/alexa/ (read 2026-11-15)
  - https://www.music-assistant.io/player-support/airplay/ (read 2026-11-15)
  - https://www.home-assistant.io/integrations/alexa_devices/ (read 2026-11-15)
  - https://github.com/music-assistant/support/issues/4921 (2026-02-08)
  - https://github.com/music-assistant/support/issues/6643 (2026-10-05)
  - https://github.com/esphome/home-assistant-voice-pe/issues/455 (2025-09-29)
  - https://community.home-assistant.io/t/voice-pe-distorted-audio/966203 (2025-12-24)
  - https://community.home-assistant.io/t/basics-of-adding-a-better-speaker/959325 (2025-12-06)
  - https://community.home-assistant.io/t/ha-voice-preview-edition-slow-to-play-audio/819069 (2024-12-30)
  - https://blog.ceard.tech/2025/01/ha-voice-pe (2025-01-06)
  - https://heywillow.io/ (read 2026-11-15; site content dated 2023)
  - https://github.com/HeyWillow/willow (read 2026-11-15)
  - https://www.engadget.com/2197748/google-has-discontinued-the-nest-home-mini-and-nest-audio (2026-06-18)
  - https://www.pcmag.com/reviews/amazon-echo-dot-5th-gen (2026-06-16)
  - docs/comparisons/devices.md, docs/comparisons/music-playback.md, docs/comparisons/sources.md (2026-11-15)
  - docs/project-brief.md, docs/roadmap.md, docs/evidence.md, docs/work/cards/R02.md
supersedes: []
---

## Summary

Six buyable alternatives were compared against building Debra, plus one open
project that is not buyable in any useful sense. The honest result:

**Buy the Home Assistant Voice Preview Edition and a powered speaker.** At a
$59 street price from a US distributor it is the cheapest way to get a working,
first-party, local-wake-word Home Assistant satellite, and nothing Debra will
ship can beat that on effort, support or time. It is not a music player on its
own: the built-in speaker is documented as voice feedback only, so music needs a
3.5 mm speaker, which is an extra purchase and an extra box.

**If music matters as much as voice, the FutureProofHomes Satellite1 Smart
Speaker ($133–135) is the only buyable box that does both from vendor firmware**
— Sendspin to Music Assistant out of the box, one power supply, one enclosure,
one vendor. It costs roughly what a Voice PE plus a decent powered speaker costs,
and it is a much bigger, louder device with a 25 W amplifier.

**Nothing in this table does what Debra intends to do.** No buyable device offers
browser-based reconfiguration of the satellite itself, an SSH/TUI maintenance
path, a printed enclosure you control, or the original Pi Zero W (ARMv6) as a
supported target. Those are the only reasons to build. Two of them are also the
weakest claims in this project: browser-first operation is a design, not a
working tool, and ARMv6 support is an open investigation, not a capability.

**What this note does not do:** it does not test anything. Every row is vendor
documentation or a third-party report. There is no listening test, no latency
measurement and no multiroom sync measurement for any alternative — and none for
Debra either.

## How to read this

Evidence labels are per [evidence.md](../evidence.md): `D` upstream-documented,
`R` reported, `H` hypothesis, `U` unknown, `T` tested by Debra. Hardware detail
for each row is **not** repeated here — it lives in the
[master device table](../comparisons/devices.md), the transport detail in
[music-playback.md](../comparisons/music-playback.md) and the numbered source
register in [sources.md](../comparisons/sources.md). This note adds what those
pages deliberately do not hold: what else you must own, who owns updates, what
users report after buying, and where buying beats building.

Prices are USD, US market, read **2026-11-15**, from the seller named in the
cell. GBP prices are quoted as GBP and **not converted**. Every price here is a
snapshot.

## The comparison

| Alternative | What it actually is | Voice: wake / STT / TTS | Music path | Price, seller, 2026-11-15 | You must already own | Updates owned by | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **HA Voice Preview Edition** | first-party ESP32-S3 satellite, assembled | microWakeWord on-device (Okay Nabu / Hey Jarvis / Hey Mycroft); STT/TTS on the HA host or HA Cloud | **Sendspin** since firmware 25.12.0; needs an external speaker on the 3.5 mm jack | $58.95 ameriDroid (**pre-order, no restock date**) and $58.95 CloudFree (**sold out**); $59.00 Seeed (max 2/account); MSRP $69 / €59 | HA server, 2.4 GHz Wi-Fi, USB-C PSU + cable (**not in box**), powered speaker for music | Nabu Casa + ESPHome upstream; HA updates it in place | `D` [PE][PEG][PEA][PEC][PES][MUS] |
| **M5Stack ATOM Voice (C008-C)**, the "Atom Echo" | $13.50 ESP32 puck with a 0.8 W amp | on-board **or** HA-server wake word, selectable | **none documented** — no Sendspin/media pipeline in the official YAML | $13.50 M5Stack direct, "10+ in stock" | as above, plus you flash it yourself | ESPHome upstream; you own the YAML | `D` [S4][S5] in [sources.md](../comparisons/sources.md) |
| **M5Stack Atom VoiceS3R (C126-ECHO)** | $14.50 ESP32-S3 puck, one MEMS mic, 1 W | "Okay Nabu" via ESPHome ≥ 2026.1.0 (vendor prose) | **Sendspin exists only in the vendor YAML**, not in the vendor's documented feature list | $14.50 M5Stack direct (**stock read both "10+ in stock" and "Out Of Stock" the same day**); $34.99 Amazon; £13 Pi Hut | as above, plus you flash it | M5Stack publishes YAML; ESPHome upstream; you own the config | `D` [M5V][S6][S7][S22] |
| **Satellite1.1 Smart Speaker** | $133–135 assembled speaker: 25 W amp, 2-way drivers, printed enclosure | microWakeWord on-device (Okay Nabu / Hey Jarvis) | **Sendspin, out of the box, no server-side provider setup**; stereo pairs and multiroom groups | $132.99 (EU/UK SKUs) / $134.99 US, FutureProofHomes direct | HA + Music Assistant, 2.4 GHz Wi-Fi, 30 W USB-C supply | FutureProofHomes, two firmwares (ESPHome + XMOS); XMOS had no stable release between 2025-08 and 2026-11 | `D` [S13][S15][S17][S18][S19] |
| **Amazon Echo Dot (5th gen)** | mass-market Alexa speaker | Alexa cloud STT, conversation agent and TTS; **no local path** | not natively; only via a self-hosted Alexa skill prototype | $79.99 list (PCMag, 2026-06); a new Echo Dot at $99.99 (Oct 2026, secondary reporting) | Amazon account; **Alexa+ is $19.99/mo without Prime** (reported) | Amazon, unilaterally, forever | `D` [HAX][MAX]; price `R` [PCM][ECH] |
| **Apple HomePod mini 2** | $149 Siri speaker | Siri; **cannot act as an HA voice satellite at all** | AirPlay 2 target for Music Assistant | $149.00 Apple, all colours | Apple ID, HomeKit home, iPhone/iPad to set up | Apple | `D` [APL][MAA] |
| **Google Home Speaker** | $99.99 Gemini-for-Home speaker; replaced Nest Mini/Audio, both discontinued 2026-06 | Gemini for Home; **no HA voice path** | Google Cast target for Music Assistant (Cast provider), not Sendspin | $99.99 (reported by launch coverage) | Google account | Google | `R` [ENG]; provider `D` [MUS] |
| **Willow** (open, not a product you can buy new) | ESP-IDF firmware for ESP32-S3-BOX hardware | on-device wake word + on-device commands, or a self-hosted inference server | **no music path documented** — `U` | "approximately $50 hardware" (project's own 2023 figure); BOX-3 availability separate | BOX-3 hardware, a server for WIS | a small volunteer project; docs dated 2023 | `D` [WIL][WILG] |
| **Building Debra** (baseline) | Pi Zero-class board + audio HAT + your software | planned; **lab Pi 5 only** has run wake→STT→intent→TTS | Sendspin client on the host; **lab-verified on Pi 5 + 2-Mics HAT only** | Pi Zero 2 W £14.40 (Pi Hut, incl. VAT); 2-Mics HAT V2.0 $12.90 (Seeed); PSU ~£7.70; SD card; printed enclosure | HA server, and everything above | **you** | `T` for the lab Pi 5; `H`/`U` for everything else |

## Practical limits, as reported by people who bought them

Kept separate from the vendor claims above on purpose. These are forum and issue
reports, not measurements, and each one has a context that may not apply to you.

| Device | Report | Source / date | What it probably means |
| --- | --- | --- | --- |
| Voice PE | Built-in speaker "is horrible… worse than my 2nd gen Echo Dots. It's garbled and extremely hard to hear even at 100% volume" | `R` community thread, 2025-12-06 [SPK] | Vendor already says it is feedback-only; this is what that sounds like |
| Voice PE | Heavy clipping from the 3.5 mm jack into a powered speaker, "AliExpress cheap Chinese no-name brand level of distortion"; user hypothesises the jack is headphone-amped rather than line-level | `R` community thread, 2025-12-24 [DST] | **Unresolved.** One report, one hypothesis, no vendor response found. Test before trusting this jack for music |
| Voice PE | Music stuttered badly after firmware 25.9.0/25.10.0; fixed by 25.11 pre-release | `R` ESPHome issue #455, 2025-09→11 [ISS455] | Firmware regressions reach users; you are on the vendor's release train |
| Voice PE | Sendspin playback dropped every 10–60 s (`close_code=1006`); **root cause was the access point**, not MA | `R` MA issue #6643, 2026-10-05 [MA6643] | 2.4 GHz-only devices fail on bad Wi-Fi; expect to debug your network, not the device |
| Voice PE | Long-playback skipping blamed on cheap unshielded speakers sitting next to the unit | `R` MA issue #4921, 2026-02-08 [MA4921] | Analogue output next to a switching amp is a real trap |
| Voice PE | "It doesn't always hear you… sometimes even when clearly spoken directly at it it'll still miss" | `R` blog, 2025-01-06 [CEA] | Wake-word reliability is the most common complaint class in every row |
| Voice PE | 20–50 s delay before response audio played | `R` community, 2024-12-30 [SLOW] | **Historical**, launch firmware. Kept because it shows the failure mode: pipeline latency is host-bound |
| VoiceS3R | "Single mic, limited far-field range" | `R` aggregator page, notes last checked 2026-06-02 [AGG] | Matches the hardware: one MEMS mic, 65 dB SNR, no array |
| Atom Echo (C008-C) | "Kind of quiet" | `R` shop review quoted in [S4] | 0.8 W into a tiny cavity; fine for a desk, not a room |
| Satellite1 | Vendor's own caveat: "at full volume the wake word may not be heard perfectly" | `D` vendor docs [S19] | A loud speaker and a listening microphone fight each other |
| Satellite1 | One user traced recurring cutouts on a multi-speaker Satellite1 house to a neighbour's Wi-Fi channel changes | `R` MA issue #4921 comment, 2026-02-12 [MA4921] | Multiroom sync is only as good as the 2.4 GHz band |
| Echo Dot | "It's an always-listening device tied to your Amazon account… There's no offline mode and no way to avoid the account requirement" | `R` review, 2026 [ECH] | Accurate description of the category, not a defect |

## What each one cannot do that Debra intends to do

Debra's intended capabilities are taken from the [project brief](../project-brief.md).
Where the brief and the older roadmap wording disagree, the brief wins: **James
refined the user journey to browser-first on 2026-11-15, so the "SSH maintenance
TUI" is no longer the everyday interface** — SSH/CLI/TUI are developer and
recovery paths. Comparing competitors against a TUI-first design would be
comparing against something already superseded.

| Debra intent | Voice PE | Atom Echo / VoiceS3R | Satellite1 | Echo / HomePod / Google |
| --- | --- | --- | --- | --- |
| Native speaker volume control | **has it, better than planned**: physical rotary dial + LED ring | none (no dial) | physical buttons + LEDs | physical buttons; works, but inside their ecosystem |
| Browser configuration of the satellite itself | **no** — config is ESPHome YAML, adopted into the ESPHome dashboard; "editing the ESPHome config require[s] taking ownership of the config and compiling it" (user, 2026-06) | **no** — you own the YAML | **no** — ESPHome dashboard / vendor app | **no** — vendor app only |
| SSH maintenance TUI | no shell at all | no shell | no shell | no shell |
| Pi Zero W (ARMv6) as a supported target | n/a — ESP32 | n/a — ESP32 | n/a — ESP32 | n/a |
| Printable enclosure you control | **partly**: 3D files published for components; case is injection-moulded | case is a moulded puck | **enclosure published as 3MF/STL/STEP** and remixable — but it is their design, not yours | none |
| Hardware-derived identity / `debra-<id>` hostname | mDNS ESPHome name, assigned by the wizard | same | same | vendor cloud identity |
| Duck/pause/resume as a user setting during voice | ESPHome/LVA behaviour, not a user-facing setting | same | vendor behaviour; vendor documents limits on voice-controlling music | not applicable |
| Multiple installed music stacks (Sendspin *and* Snapcast) | one at a time, firmware-dependent | no | Sendspin now; Snapcast was removed at v0.2.0 | none |
| External speaker on a 3.5 mm output | yes (that is the music path) | no jack | yes, plus a 25 W amp | no jack on Echo Dot 5 / HomePod mini |
| Physical mute | **yes** — switch physically cuts mic power | no | yes (one hardware mute button of four) | Echo: mic-off button; HomePod/Google: software |

## Cost, honestly

**Voice PE, complete, music included (US, 2026-11-15):**

| Item | Price | Note |
| --- | --- | --- |
| Voice PE | $58.95–$59.00 | street, not $69 MSRP; two of three US sellers were out of stock when read |
| USB-C PSU + cable | ~$10–20 | **not included**, per vendor |
| Powered speaker | ~$25–60 | any 3.5 mm powered speaker; the built-in one is feedback-only |
| HA server | **$199** (HA Green MSRP) if you do not have one | you need this for every row, including Debra |
| HA Link / Cloud, optional | $6.50/mo or $65/yr | only if your host is too weak for local STT; the vendor says N100-class for local Whisper |
| **Total, assuming HA already runs** | **~$95–140** | |

**Satellite1 Smart Speaker, complete:** $132.99–$134.99 + a 30 W USB-C supply
(the vendor asks for one) + HA. No separate speaker, no separate amp.

**Echo Dot, complete:** $79.99 list, plus $19.99/mo for Alexa+ if you want the
2026 feature set without Prime (`R`), plus your Amazon account, plus a
hand-built skill service with a public HTTPS endpoint and an Amazon developer
account before Music Assistant can send it anything (`D`). The cheap sticker is
the least honest number in this note.

**Building Debra, complete, for the honest cheap case:** Pi Zero 2 W £14.40 +
2-Mics HAT $12.90 + PSU ~£7.70 + microSD + printed enclosure + **your time**.
The parts are cheaper than any buyable device. The time is not free and has no
number attached yet.

## Where buying wins

1. **Time to a working satellite.** The Voice PE is unbox → wizard → "turn on
   the light" in minutes, with a phone app doing Wi-Fi onboarding. Debra's
   onboarding is a design document. This is not close.
2. **Wake-word quality.** microWakeWord models on a dual-mic array with an XMOS
   XU316 doing echo cancellation, noise removal and AGC is a solved, shipped
   problem. Debra's Pi path uses a codec on a HAT and whatever wake engine the
   host can afford — the lab unit works, but nothing about it has been measured
   against the Voice PE.
3. **Recovery.** A bricked Voice PE is reflashed from a browser with the official
   installer. A bricked Debra image is a support conversation that does not exist
   yet.
4. **Someone else owns the bugs.** Firmware regressions happen (see #455), but
   Nabu Casa and the ESPHome community ship the fix and you install it. In Debra,
   you are the fix.
5. **Physical controls you would otherwise have to invent.** Rotary volume,
   LED ring, hardware mute that cuts microphone power, Grove expansion. Debra's
   brief asks for "native speaker volume" as a *browser* feature; the Voice PE
   gives you a knob.
6. **Music without writing a receiver.** Satellite1 ships Sendspin to Music
   Assistant with no provider setup, stereo pairs and multiroom groups. On a Pi
   you are installing and pinning a client, and the Pi side is the least
   demonstrated part of the whole Sendspin story.
7. **A second unit is a purchase, not a project.** Multiroom only becomes
   interesting at 3+ rooms. Buying three Voice PEs is $180 and an afternoon.
   Building three Debras is three times the bring-up.

## Where building wins

Only where the requirement is genuinely not for sale. Ranked by how defensible
each one is today:

1. **One box, no second speaker, and you own the stack.** The Voice PE cannot
   play music without an external speaker; the Satellite1 can, but it is a
   closed vendor firmware pair (ESPHome + XMOS) with its own release cadence and
   a 2026 breaking change from Snapcast to Sendspin. A Pi with a 25 W HAT and a
   host-side receiver has no vendor in the middle. **This is the strongest
   argument for building and it is a real one.**
2. **Reconfiguration of the device itself from a browser.** Nobody sells this.
   ESPHome YAML is the closest thing and it is a developer workflow, not a
   beginner one. If browser-first configuration is the product, it cannot be
   bought. **But it does not exist yet**, so today it is a plan, not an advantage.
3. **Pi Zero W / ARMv6 as a target.** Not buyable at any price, because no vendor
   will ship it. Whether it *should* be a target is an open engineering question
   ([Z01](../../docs/roadmap.md)); buying nothing solves it, and neither does
   building until the wheels exist.
4. **The enclosure.** A printed tray you designed is yours to change. Satellite1
   publishes STEP files, which is close, but you are remixing their design.
5. **Mixed-protocol coexistence.** Sendspin *and* Snapcast installed, with a
   documented rule about who owns the sound card. No vendor offers this because
   no vendor wants the support burden.
6. **Cost at volume, if your time is free.** Parts are ~$30–50 for a Zero-class
   unit. If you are building five for a family and you enjoy it, that is real.

## Traps

- **MSRP is not the price.** Voice PE lists at $69/€59 and sold for $58.95–$59.
  Two of three US sellers I checked were out of stock with no restock date. A
  distributor list is not availability.
- **"Works with Music Assistant" is doing heavy lifting.** For the Voice PE it
  means a Sendspin client in firmware since 25.12.0, *plus* a speaker you buy.
  For the VoiceS3R it means a config file in the vendor's repo that the vendor's
  own documentation does not mention. For the Echo it means an experimental,
  self-hosted Alexa skill with no multiroom sync. For the HomePod it means
  AirPlay, which is a different protocol with its own HomeKit precondition.
- **A voice satellite is not a music player.** Only the Satellite1 is both, out
  of the box. Everything else is voice, or music, or two boxes.
- **Sendspin is a technical preview**, stated by Music Assistant itself. It
  replaced Snapcast on Satellite1 with a breaking migration (old players must be
  deleted, not upgraded). Do not treat any current Sendspin behaviour as stable.
- **2.4 GHz Wi-Fi is the real failure mode**, not the device. At least two
  independent Voice PE dropout reports ended at the access point, not the
  firmware.
- **Local-only is a host question.** Every device here needs a Home Assistant
  server. "Fully local" means an N100-class host running Whisper, or a focused
  local model limited to home-control sentences. Buying the device does not buy
  the privacy; the server does.
- **Timers are not alarms.** Every vendor demos timers. Persistent alarms with a
  wake-up path are a different feature and are not established for any row.
- **Echo, HomePod and Google are not satellites.** They cannot take a wake word
  for Home Assistant. The HA Alexa integration is Cloud Polling with mandatory
  MFA, and its own documentation says you "will not be able to play music this
  way".
- **Two vendor firmware trains are worse than one.** Satellite1 needs ESPHome
  *and* XMOS firmware kept in step; the XMOS side had no stable release for
  about fifteen months.
- **A price with no date is not evidence.** Every number above is a 2026-11-15
  snapshot and several moved during this session alone (VoiceS3R stock flipped
  within the hour).
- **The Atom Echo name is a trap.** M5Stack's shop slug still says "atom-echo"
  for the C008-C while the newer C126-ECHO is a different chip, different codec
  and a different microphone count. Buying the wrong one is easy.

## Not verified / open questions

- **No listening test, latency measurement, or sync measurement exists for any
  row**, including Debra's. "Sounds fine" is not in this note because nobody
  measured it.
- **The Voice PE 3.5 mm clipping report is unresolved.** One user, one
  hypothesis (headphone-level output rather than line level), no vendor answer
  found. Anyone planning music through that jack should test it first.
- **Voice PE availability is a snapshot.** ameriDroid showed pre-order with no
  restock date; CloudFree showed sold out; Seeed showed a price with a two-per-
  account limit but I did not confirm a stock status line. Re-check before
  relying on it.
- **Echo Dot and Alexa+ pricing** comes from secondary coverage and a review, not
  from an Amazon page I read directly. Amazon blocked or was not fetched.
- **Google Home Speaker** price and Gemini-for-Home behaviour come from launch
  coverage, not from Google's own store page. Whether Music Assistant's Cast
  provider treats it as a normal player is `H`, not verified.
- **HomePod mini 2 at $149** is what Apple's store showed; the previous
  generation was widely sold at $99. The price step is real in this snapshot and
  I did not investigate why.
- **Willow's current state is unknown.** The docs site still reads as 2023, the
  repo has 3.1k stars and Apache-2.0, and I did not establish last-commit
  activity or whether BOX-3 hardware is the only supported target. Treat it as
  "a project to read", not "a thing to buy".
- **Whether any of these can run the Debra browser interface** is not a question
  anyone has asked of them; all are ESP32 firmware with no shell.
- **Debra's own build cost is unpriced.** The parts are known; the labour, the
  support burden and the probability of a beginner succeeding are not.
- **`T` for the lab Pi 5 covers exactly one claim**: wake→STT→intent→TTS ran end
  to end, and Music Assistant streamed FLAC to the HAT. It does not cover sound
  quality, latency, multiroom, or the Zero W.

## Handoff and correction links

- **Bottom line for a beginner reading this later:** buy a Voice PE and a
  powered speaker, or a Satellite1 if you want one box that plays music. Build
  Debra only if you specifically want browser-first reconfiguration, the Zero W
  path, or the enclosure — and understand that the first two are not finished.
- **Current state:** this is a documentation note from vendor and third-party
  sources read 2026-11-15. No device was touched, no purchase made, no firmware
  flashed.
- **Concrete next action, if someone wants to settle the biggest unknown cheaply:**
  measure one thing — put the Voice PE's 3.5 mm output into a powered speaker,
  play 60 s from Music Assistant, and record whether the clipping report
  reproduces at default volume. That is the single claim most likely to change a
  buying decision, and it is not answered anywhere in the sources above.
- **Authorization:** none of this is permission to buy, flash, or operate
  anything. Prices and stock move; re-check before acting.
- **Does not supersede** [devices.md](../comparisons/devices.md) or
  [music-playback.md](../comparisons/music-playback.md). This note adds cost,
  ownership and buying-advice framing; those pages remain the hardware and
  transport record. Where they disagree with this note, they win on hardware
  detail and this note wins on nothing.

## Local source keys

Short keys keep the tables readable. Each key below is also a clickable
reference in the text above; the same URLs appear with read dates in the
frontmatter of this note and, for hardware rows, in
[sources.md](../comparisons/sources.md).

| Key | Source | Read |
| --- | --- | --- |
| `PE` | https://www.home-assistant.io/voice-pe/ | 2026-11-15 |
| `PEG` | https://support.nabucasa.com/hc/en-us/articles/25918770371229 | 2026-11-15 |
| `PEA` | https://ameridroid.com/products/home-assistant-voice-preview-edition/ | 2026-11-15 |
| `PEC` | https://cloudfree.shop/product/home-assistant-voice-preview-edition/ | 2026-11-15 |
| `PES` | https://www.seeedstudio.com/Home-Assistant-Voice-p-6998.html | 2026-11-15 |
| `MUS` | https://www.music-assistant.io/player-support/sendspin/ | 2026-11-15 |
| `MAA` | https://www.music-assistant.io/player-support/airplay/ | 2026-11-15 |
| `MAX` | https://www.music-assistant.io/player-support/alexa/ | 2026-11-15 |
| `HAX` | https://www.home-assistant.io/integrations/alexa_devices/ | 2026-11-15 |
| `M5V` | https://shop.m5stack.com/products/atom-echos3r-smart-speaker-dev-kit | 2026-11-15 |
| `APL` | https://www.apple.com/shop/buy-homepod/homepod-mini | 2026-11-15 |
| `WIL` | https://heywillow.io/ | 2026-11-15 |
| `WILG` | https://github.com/HeyWillow/willow | 2026-11-15 |
| `ENG` | https://www.engadget.com/2197748/google-has-discontinued-the-nest-home-mini-and-nest-audio | 2026-06-18 |
| `PCM` | https://www.pcmag.com/reviews/amazon-echo-dot-5th-gen | 2026-06-16 |
| `ECH` | https://easygoingnerd.com/review/amazon-echo-dot-5-review | 2026-11-15 |
| `ISS455` | https://github.com/esphome/home-assistant-voice-pe/issues/455 | 2025-09-29 |
| `MA6643` | https://github.com/music-assistant/support/issues/6643 | 2026-10-05 |
| `MA4921` | https://github.com/music-assistant/support/issues/4921 | 2026-02-08 |
| `SPK` | https://community.home-assistant.io/t/basics-of-adding-a-better-speaker/959325 | 2025-12-06 |
| `DST` | https://community.home-assistant.io/t/voice-pe-distorted-audio/966203 | 2025-12-24 |
| `SLOW` | https://community.home-assistant.io/t/ha-voice-preview-edition-slow-to-play-audio/819069 | 2024-12-30 |
| `CEA` | https://blog.ceard.tech/2025/01/ha-voice-pe | 2025-01-06 |
| `AGG` | https://localsmarthomeguide.com/products/m5stack-atom-echo-s3r | 2026-11-15 |

[PE]: https://www.home-assistant.io/voice-pe/
[PEG]: https://support.nabucasa.com/hc/en-us/articles/25918770371229
[PEA]: https://ameridroid.com/products/home-assistant-voice-preview-edition/
[PEC]: https://cloudfree.shop/product/home-assistant-voice-preview-edition/
[PES]: https://www.seeedstudio.com/Home-Assistant-Voice-p-6998.html
[MUS]: https://www.music-assistant.io/player-support/sendspin/
[MAA]: https://www.music-assistant.io/player-support/airplay/
[MAX]: https://www.music-assistant.io/player-support/alexa/
[HAX]: https://www.home-assistant.io/integrations/alexa_devices/
[M5V]: https://shop.m5stack.com/products/atom-echos3r-smart-speaker-dev-kit
[APL]: https://www.apple.com/shop/buy-homepod/homepod-mini
[WIL]: https://heywillow.io/
[WILG]: https://github.com/HeyWillow/willow
[ENG]: https://www.engadget.com/2197748/google-has-discontinued-the-nest-home-mini-and-nest-audio
[PCM]: https://www.pcmag.com/reviews/amazon-echo-dot-5th-gen
[ECH]: https://easygoingnerd.com/review/amazon-echo-dot-5-review
[ISS455]: https://github.com/esphome/home-assistant-voice-pe/issues/455
[MA6643]: https://github.com/music-assistant/support/issues/6643
[MA4921]: https://github.com/music-assistant/support/issues/4921
[SPK]: https://community.home-assistant.io/t/basics-of-adding-a-better-speaker/959325
[DST]: https://community.home-assistant.io/t/voice-pe-distorted-audio/966203
[SLOW]: https://community.home-assistant.io/t/ha-voice-preview-edition-slow-to-play-audio/819069
[CEA]: https://blog.ceard.tech/2025/01/ha-voice-pe
[AGG]: https://localsmarthomeguide.com/products/m5stack-atom-echo-s3r
