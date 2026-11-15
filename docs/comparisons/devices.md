# Master device table

One row per exact variant. Cells carry `value [S# label]`; see
[README.md](README.md) for the tags and [sources.md](sources.md) for the
register. Register dates describe source access, not necessarily a re-check of
every inherited claim: for example, the Seeed price and purchase limit are from
R02 and were not readable on its revision-2 re-check [S37 R].

The `Music playback` column is a summary. [music-playback.md](music-playback.md)
carries the transport, the firmware version that enables it, the stream format
and what the server has to run, for every row.

## Buying alternatives at a glance

Snapshots from revision 2 of the unreviewed
[R02 research note](../notes/2026-11-15-complete-alternatives-comparison-revision.md),
not Debra tests. Prices are USD per device unless the cell says otherwise, read
2026-11-15, before shipping and tax; GBP is never converted and no supply, speaker
or subscription is assumed included. Stock is a same-day snapshot. Seven buyable
products are listed, plus one open project that is not buyable new.

| Alternative (exact variant) | Cost, seller, 2026-11-15 | What it does | What it cannot do | Evidence |
| --- | --- | --- | --- | --- |
| HA Voice Preview Edition | **$58.95** ameriDroid, **$58.95** CloudFree (**sold out** on re-check); Seeed $59.00 and a two-per-account limit recorded in R02, not readable on re-check; MSRP $69 / €59 [S1 D][S35 R][S36 R][S37 R] | Assembled ESP32-S3 satellite; on-device wake word; Sendspin since firmware 25.12.0 (2025-12-17, "public preview") [S1 D][S20 D] | Built-in speaker is voice feedback; music needs a powered speaker. No supply or cable in box; an HA server is required [S1 D][S51 D] | `D`; price `R` |
| M5Stack ATOM Voice (C008-C) | **$13.50** M5Stack direct, listed available [S4 D] | ESP32 puck, 0.8 W amplifier; on-device **or** HA-server wake word, selectable [S5 D] | No music path in the upstream ESPHome config `U`; you flash it and own the YAML [S5 D] | `D` |
| M5Stack Atom VoiceS3R (C126-ECHO) | **$14.50** M5Stack direct, **out of stock** on re-check; $34.99 Amazon and £13 Pi Hut as recorded in R02 [S38 R] | ESP32-S3 puck, one MEMS mic, 1 W; "Okay Nabu" per the vendor's HA page [S6 D][S7 D] | Vendor prose documents wake word and announcements, not music; Sendspin appears in the vendor YAML, which declares ESPHome 2026.10.0 [S7 D][S22 D] | `D`; stock `R` |
| Satellite1.1 Smart Speaker | **$134.99** US / **$132.99** EU-UK, FutureProofHomes direct, listed available [S13 D] | Assembled 25 W two-way speaker; vendor documents Sendspin to Music Assistant with no provider setup, stereo pairs and multiroom [S15 D] | Needs HA and MA plus a 30 W USB-C supply the vendor does not include; wake word may be missed at full volume [S13 D][S19 D] | `D` |
| Echo Dot, fifth generation | **$79.99** list, `reported`, review dated 2026-06-16, not re-verified [S39 R] | Alexa cloud voice: speech to text, conversation agent and replies `D`; Music Assistant offers an experimental self-hosted Alexa skill [S40 D] | No HA wake-word satellite role and no local path; HA's Alexa integration is cloud polling with mandatory MFA and does not deliver music [S41 D] | price `R`, limits `D` |
| HomePod mini 2 | **$149.00** Apple, all colours [S48 D] | Siri speaker; an AirPlay 2 playback target for Music Assistant [S49 D] | Cannot act as an HA voice satellite; needs an Apple ID, a HomeKit home and an iPhone/iPad for setup [S48 D] | `D` |
| Google Home Speaker | **$99.99** `reported` by launch coverage in R02 (the date-checked page is about the discontinued Nest models), not re-verified [S52 R] | Current Gemini-for-Home speaker; Nest Mini and Nest Audio were discontinued in 2026-06 [S52 R] | No HA voice-satellite path; Music Assistant documents Google Cast generally, but this 2026 model is not named on that page `U` [S57 D] | price `R`; model `U` |
| Willow (open project, not buyable new) | `U` — no buying price; the project's own "approximately $50 hardware" figure is from 2023 and `historical` [S58 R] | ESP-IDF firmware for ESP32-S3-BOX-3: on-device wake word and commands, or a self-hosted inference server [S58 R][S59 R] | No music path documented `U`; needs BOX-3 hardware, and current project activity is `U` [S58 R][S59 R] | `D` project; status `U` |

Reported `D` claims here are vendor or project statements, not Debra measurements.
The [R02 revision](../notes/2026-11-15-complete-alternatives-comparison-revision.md)
also records a user report of heavy clipping from the Voice PE's 3.5 mm jack into
a powered speaker (`R`, thread dated 2025-12-24), and a separate report of
20–50 s before playback on one of two units [S54 R]; the cause of each is `U`,
and the vendor's slowdown issue was still open on 2026-11-15 [S53 R]. See that
revision for account requirements, per-product prerequisites and the estimate
behind every non-device price.

Two cautions that belong with this table. **Amplifier wattage is a rating, not a
measured loudness**: the Satellite1's 25 W and the Voice PE's lack of a comparable
amplifier say nothing about how loud either is, and no listening test exists for
any row, including Debra's. **Three units is not three setups**: 3 × $58.95 is
$176.85 of Voice PE devices only, excluding three supplies, three powered speakers,
tax and shipping; the complete three-unit estimate is $281.85–$417.00, and whether
three can be bought from one seller at one price is `U`.

### What building Debra costs

Revision 2 of R02 keeps **two totals apart**. Both are USD listed prices from the
unreviewed [R01 parts inventory](../notes/2026-11-15-parts-inventory.md), quoted at
that inventory's own date (2026-11-15), before shipping and tax.

| Total | What it covers | Amount listed, 2026-11-15 |
| --- | --- | --- |
| **A. Complete purchase** (lab-HAT route; Zero 2 W combination untested) | Pi Zero 2 W with header, ReSpeaker 2-Mics V2, 32 GB card, one supply, one speaker at a historical price | **$59.90**; **$68.35** with a second supply for the HAT's power input |
| **A′. Fully priced, untested combination** | the same with a WM8960 HAT (onboard amplifier, bundled speaker) instead of the 2-Mics HAT | **$62.49** |
| **B. Reused parts** (Pi, supply, card and printer already owned) | ReSpeaker 2-Mics V2 plus one speaker at a historical price | **$16.40**; **$17.35** if the owned board needs a 2×20 header |

Total A is a floor, not a price: the never-printed enclosure, shipping, tax and
labour are all excluded. It is **not** missing a speaker amplifier: the 2-Mics HAT
drives its speaker through an on-board TPA2005D1 amplifier, measured on the lab
card at −21 dBFS against ≈−100 on the headphone path ([audio outputs](../design/audio-outputs.md)).
What is unverified is whether that amplifier suits a 5 W module at useful volume,
and no listening test exists. A′ is the one fully priced
line-item build and is not the combination Debra has tested. Total B is a
**marginal** cost, and the project brief forbids presenting it as a unit price.
R01's figures still rest on historical, unverified speaker prices.

The earlier claim that Debra is cheaper than every alternative is withdrawn.
$59.90 is below the Voice PE's estimated complete music setup ($93.95–$139.00, of
which just the $58.95 device price is sourced) and below the Satellite1.1's US device
price, and above the two M5Stack pucks ($13.50, $14.50). None of these is a
cost-of-ownership comparison, and the alternatives deliver capability Debra has not
built.

## Non-Raspberry-Pi host boards: 2-Mics HAT screen

Revision 2 of the [R07 screen](../notes/2026-11-15-alternative-board-screen-revision.md)
is unreviewed documentation research, checked 2026-11-15. No board was bought,
imaged, powered or contacted, and no schematic, device tree or overlay was opened.
An empty cell is never "no". Header alignment alone does not establish electrical,
driver, OS or Debra compatibility: matching pin labels on a vendor table is a lead.

Outcome, stated as evidence: **ROCK 3C**, **ZERO 3W** and **Orange Pi 3B** survive
with a decisive unknown each (the 3B's pin table is image-only and unread);
**Orange Pi Zero 2W** and **Le Potato** are **"not demonstrated"**, which is not
"not usable"; **Orange Pi Zero 3** has no 40-pin header. None is a shortlist for
purchase. No board here has `config.txt`, a Pi firmware overlay loader or a HAT ID
bus, so any candidate needs a hand-written overlay — a Debra task not attempted.
Board-native audio and USB audio were not evaluated as replacements.

Pi-side positions for reference: 12/35/38/40 are the I2S PCM pins, 13 is a plain
GPIO on a Pi (no clock), 3/5 are I2C1 and 27/28 the HAT ID EEPROM bus [S64 R].

| Exact board | HAT screen, 2026-11-15 | Decisive unknown (one check) | Price, seller, date |
| --- | --- | --- | --- |
| Radxa ROCK 3C V1.3/V1.4 | I2S documented at 12/35/38/40, SoC MCLK at 13, and I2C3 at 3/5 — a documented starting point, not a demonstration [S46 D] | Does an overlay binding `i2s3_8ch` to the HAT's TLV320AIC3104 on `i2c3` boot, play and capture on a V1.4 board? `U` | `U` — no price published; Radxa sells through its "Approved Partners" network [S60 D] |
| Radxa ZERO 3W V1.11/V1.12 | I2S and MCLK documented at the four Pi positions and pin 13; pins 3/5 are UART3, with I2C4 at 27/28 [S45 D] | Can the HAT's codec be reached with its two I2C wires moved to 27/28, via a tested overlay? `U` | **$20.00** page price, Arace Tech (HK), variant not rendered; all 12 listed combinations sold out [S62 R] |
| Orange Pi 3B (RK3566) | 40-pin header; the pin table is published as three PNG images and was not read [S44 D] | Which functions does the vendor assign to 12/35/38/40 and 3/5 — via the images, the schematic or a kernel DTS? `U` | `U` — no seller page read |
| Orange Pi Zero 2W V1.1 (H618) | 40-pin header, I2C documented at 3/5; **no I2S function in the vendor's pin table** [S42 D]. Whether pins are soldered by default is `U` | Do H618 I2S nets reach any 40-pin pad, and does the vendor kernel expose them? `U` | **53,00 €** incl. VAT, 1 GB, Amazon.de marketplace listing (price widget 2026-11-11; article 2026-11-08), "few left" [S63 R] |
| Orange Pi Zero 3 (H618) | **No 40-pin header** — a 26-pin and a 13-pin connector; no direct HAT fit, and a 2×20 HAT cannot be fully seated [S43 D] | None for direct fit; a jumper harness would need the Zero 3 schematic `U` | `U` — no seller page read |
| Libre Computer Le Potato AML-S905X-CC | **Not demonstrated either way**: the vendor index says I2S/PCM "please request if needed", and one user reports the signals are absent from the header [S47 R][S61 R] | Do I2S/PCM reach the 40-pin header, and is a maintained codec overlay published? `U` | `U` — no seller page read |

No price here is a complete purchase total, and none is comparable across markets,
sellers, variants or dates: no exchange rate is assumed and no ranking is implied.
R07 revision 2 also records "ab rund 86 €" for higher-RAM Zero 2W variants and a
historical "rund 13 Dollar" launch recollection; neither is a current buying price.
Radxa image and kernel versions are not established by the register `U`; whether
any Armbian image clears LVA's Python floor is also unconfirmed `U`.

## Complete devices and near-complete kits

| Device (exact variant) | SoC / audio silicon | Microphone topology | Speaker output | On-device wake word | Home Assistant path | Music playback | Architecture | Price, market, date | Availability | Maintenance burden | Weakest cell |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Home Assistant Voice PE** (official) | ESP32-S3, 16 MB flash, 8 MB octal PSRAM; XMOS XU316 for audio; AIC3204 DAC [S1 D] | dual microphones, 48 kHz [S1 D]; array geometry `U` | built-in speaker is **voice feedback, not music**; music needs a 3.5 mm external speaker [S1 D] | microWakeWord on-device; "Okay Nabu", "Hey Jarvis", "Hey Mycroft" [S1 D] | first-party: HA Voice Assistant, ESPHome firmware [S1 D] | listed as a Sendspin player target in ESPHome's ready-made projects [S2 D]; Sendspin in firmware 25.12.0 (2025-12-17, public preview) [S20 D]; playback not demonstrated here `U` | ESP32-S3 (Xtensa) [S1 D] | $69 MSRP USD excl. tax; €59 [S1 D] | distributor list incl. EU/UK/US [S1 D]; ameriDroid listed available, CloudFree sold out, Seeed stock unreadable on 2026-11-15 [S35 R][S36 R][S37 R] | first-party hardware and firmware [S1 D] | music: release note, not a test |
| **M5Stack ATOM Voice** (C008-C) | ESP32-PICO-D4, 4 MB flash, no PSRAM; NS4168 0.8 W I²S amplifier [S4 D] | single SPM1423 PDM microphone [S4 D] | NS4168, 0.8 W into the built-in speaker [S4 D] | on-board **or** HA-server wake word, selectable [S5 D] | ESPHome YAML in the official wake-word repo [S5 D] | `U` — no music path documented | ESP32 (Xtensa) [S4 D] | $13.50 USD, M5Stack shop [S4 D] | "10+ in stock" on 2026-11-15 [S4 D] | small, single-vendor; firmware examples are ESPHome's, not M5Stack's [S5 D] | music `U`; speaker "kind of quiet" [S4 R] |
| **M5Stack Atom VoiceS3R** (C126-ECHO) | ESP32-S3-PICO-1-N8R8, 8 MB flash, 8 MB octal PSRAM; ES8311 mono codec; NS4150B amplifier [S6 D] | **one** MEMS microphone, 65 dB SNR [S6 D] — "two mics" branding does not apply to this SKU | 8 Ω 1 W via NS4150B [S6 D] | "Okay Nabu" via ESPHome, ≥2026.1.0 [S7 D] | vendor-maintained HA/ESPHome application page [S7 D] | Sendspin **in the vendor ESPHome YAML**, not in its feature prose [S22 D]; not demonstrated here | ESP32-S3 [S6 D] | $14.50 USD M5Stack direct [S38 R]; $34.99 Amazon and £13 Pi Hut appear in R02 with no URL and are `U` | **out of stock** on re-check 2026-11-15 [S38 R] | vendor page only; no upstream project listed [S7 D] | stock `R` from one re-check; music is a config file, not a test |
| **ESP32-S3-BOX-3** | ES7210 ADC (dual mic) + ES8311 DAC, 48 kHz out [S3 D] | dual microphone via ES7210 [S3 D] | speaker enable GPIO, onboard speaker [S3 D] | ESPHome wake-word project [S2 D] | ESPHome project target [S2 D] | `U` | ESP32-S3 [S3 D] | sample price $49 USD reference [S9 D] | older BOX/-Lite listed "no longer for sale" [S9 D] | Espressif devkit, ESPHome support [S3 D] | silicon details come from a config file, not a datasheet, and no seller stock was checked |
| **ReSpeaker Lite, USB 2-Mic Array** (107990273) | XMOS XU316 DSP, **no application SoC, no Wi-Fi** `H` — report received without resolvable sources | 2 digital MEMS mics `H` | 5 W speaker output `H` | hosted (LVA/HA), none on board `H` | host-side only `H` | `U` | USB UAC2 device `H` | $24.90 USD Seeed `H` | `U` | `U` | **entire row is unreviewed**: the report's source keys were never defined, so it is being re-run |
| **ReSpeaker Lite Voice Kit** (XIAO ESP32S3, 110061601) | ESP32-S3 + XU316 `H` | as above `H` | as above `H` | microWakeWord on-device `H` | ESPHome + third-party firmware `H` | claimed yes with 48 kHz firmware `H` | ESP32-S3 | $29.90 USD Seeed `H` | `U` | `U` | **unreviewed**, same reason |
| **Raspberry Pi 5 + ReSpeaker 2-Mics Pi HAT v2.0** (Debra lab) | Pi 5 (BCM2712), aarch64; TLV320AIC3104 codec at I²C 0x18 [T] | stereo capture, two mics; **which mic feeds which channel `U`** [T] | speaker path through the codec's LINE output and amplifier; **headphone routing unverified**, and the speaker→air→mic path was measured [T] | none on the HAT; host-side LVA, tested [T] | **LVA `v1.1.18` installed and accepted by Home Assistant; wake word → STT → intent → TTS completed** [T] | **Sendspin `9.1.0` daemon; Music Assistant streamed FLAC to the HAT** [T] | aarch64 + I²S HAT [T] | HAT price `U`; Pi 5 price `U` | lab unit owned | stock kernel already ships the codec driver; overlay must be built and pinned [T] | one specimen, manually installed, not a Debra appliance: the power rail sagged under load with the old supply, and the original Zero W is untested — see the [lab result](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md) |
| **Satellite1.1 HAT Board** (FPH-SAT1.1-HAT) | XMOS XU316, 16-core 32-bit @800 MHz, 1024 KB SRAM, 8 MB flash; PCM5122 line out; TAS2780 25 W mono amp; FUSB302 USB-C PD; **no application SoC of its own** — 40-pin Pi header or the Core board [S10] | 4× PDM MEMS on the board; **the XMOS firmware drives 2 today**, 4 "coming" [S11] | TAS2780 25 W mono into 4 Ω, plus a 3.5 mm line out; 48 kHz streaming [S10][S11] | none on the HAT; host-side under LVA on a Pi, or on the ESP32 Core board [S8][S14] | LVA's README lists "Pi Zero 2 W + Satellite1 HAT" as a recommended pairing [S8]; ESPHome when paired with the Core board [S14] | **Sendspin**, documented: the speaker appears in Music Assistant with no provider setup, and supports stereo pairs and multi-room groups [S15] | armhf/aarch64 on a Pi; ESP32-S3 (Xtensa) on the Core board [S10][S14] | $54.99 USD direct, 31 g, 88 × 88 × 10 mm [S10] | listed available 2026-11-15 [S10 D] | XMOS firmware has had no stable release since v1.0.3 (2025-08-06) while ESPHome ships often [S18][S17] | 2 of 4 mics active; the assembly wants up to 30 W and the vendor asks for a 30 W PD supply [S10][S11] |
| **Satellite1.1 Dev Kit (DIY)** (FPH-SAT1-DK-US) | HAT above + Satellite1.1 Core Board: ESP32-S3 N16-R8, dual-core LX7 @240 MHz, 16 MB flash, 8 MB PSRAM [S12][S14] | as the HAT [S11] | as the HAT [S10] | microWakeWord on the ESP32-S3; "Okay Nabu" and "Hey Jarvis" [S16] | native ESPHome integration, Assist pipeline, OTA [S14] | Sendspin through Music Assistant, out of the box [S15] | ESP32-S3 (Xtensa) [S14] | $69.99 USD direct, 44 g [S12] | listed available 2026-11-15 [S12 D] | two firmwares to track (ESPHome, XMOS) [S17][S18] | the assembled stack height is not published; 10 mm is the HAT alone [S10][S12] |
| **Satellite1.1 Smart Speaker** (pre-assembled) | Dev Kit inside a printed PETG enclosure [S13][S19] | as the HAT [S11] | 3" woofer 15 W RMS / 20 W peak 4 Ω + 1.2" dome tweeter + passive 2-way crossover [S19] | microWakeWord on-device [S16] | ESPHome [S14] | Sendspin through Music Assistant [S15] | ESP32-S3 (Xtensa) [S14] | $132.99 USD (EU/UK SKUs), $134.99 US [S13] | listed available 2026-11-15 [S13 D] | vendor product; the enclosure is published as 3MF/STL/STEP for remixing [S19] | vendor's own caveat: at full volume the wake word may not be heard [S19]; drivers are not sold separately [S19] |

The **Satellite1.1 Core Board** ($24.99, 13 g) is not a device row because it is
not a voice device on its own: it is an ESP32-S3 board in the **Raspberry Pi Zero
form factor that accepts most Pi HATs** [S14]. That makes it a genuine third
architecture for the same HAT, and the reason the "Pi or ESP32?" question below
is not academic.

## Capability summary

The three columns people actually decide on. Everything here is a restatement of
the table above, not new evidence.

| Device | Voice assistant | Music player | Reuse of parts Debra already has |
| --- | --- | --- | --- |
| HA Voice PE | first-party firmware [S1 D] | external speaker required [S1 D]; Sendspin target [S2 D] | no |
| ATOM Voice (C008-C) | yes, cheap [S4 D][S5 D] | `U` | no |
| Atom VoiceS3R (C126-ECHO) | yes [S7 D] | Sendspin in vendor YAML, not its prose [S22 D] | no |
| ESP32-S3-BOX-3 | yes [S2 D] | `U` | no |
| ReSpeaker Lite (both) | `U` pending re-run | `U` pending re-run | no |
| Satellite1.1 HAT (on a Pi or the Core board) | yes, with LVA on a Pi or ESPHome on the Core board [S8][S14] | **yes, documented**: Sendspin, stereo pairs, multi-room [S15] | no: a second ecosystem to buy into [S10] |
| Satellite1.1 Dev Kit / Smart Speaker | yes, microWakeWord on-device [S16] | **yes, documented** [S15] | no [S12][S13] |
| Pi 5 + ReSpeaker 2-Mics v2 | **yes, lab-tested** [T] | **yes, lab-tested** [T] | **yes**: Pi 5 and HAT already in hand [T] |

## Open questions worth money

| Question | Why it blocks a decision | Where it will be answered |
| --- | --- | --- |
| Can a Pi + HAT do music playback as well as voice on the same device? | That is Debra's premise. The Satellite1 proves the *protocol* side works with Music Assistant [S15], but not on a Pi, and not with this HAT | LVA/Sendspin integration test on the lab Pi — partly done: the lab Pi 5 streams FLAC from the household MA to the HAT, see the [result record](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md) |
| Does the ReSpeaker Lite 48 kHz firmware really enable music, and on which variant? | Source pages conflict; row is unreviewed | `CMP02B` re-run with a resolvable source register |
| Would a Pi Zero 2 W + Satellite1 HAT beat the Pi 5 + 2-Mics HAT for a cheap appliance? | Satellite1 has a 25 W amp and four mics (two currently used), with a documented Sendspin path [S10 D][S11 D][S15 D]. The 2-Mics HAT has two mics and an on-board speaker amplifier; the lab's Sendspin receiver runs on the host [T] | Needs a build and a listen, not more research |
| Is any of these quiet enough to live in a bedroom? | No measured acoustic data exists for any row, and the vendor itself warns the wake word suffers at full volume [S19] | Needs measurement, not research |

## Not yet researched

Listed so nobody assumes they were rejected: AtomS3R with Atomic Voice Base or
Voice Pyramid, ESP32-S3-Korvo-2, ESP-VoCat. All are `U` until a sourced report
lands. The Satellite1 family left this list on 2026-11-15; the report behind
those rows is summarised above and its raw source register is [S10]–[S19].
