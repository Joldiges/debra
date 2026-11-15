---
title: Independent review of four Debra research notes
date: 2026-11-15
type: project-learning
status: unreviewed
task: review
author: OpenCode independent reviewer
author_model: openai/gpt-6.1-terra
author_variant: flex-high
sources:
  - docs/notes/2026-11-15-complete-alternatives-comparison.md (R02, reviewed 2026-11-15)
  - docs/notes/2026-11-15-alternative-board-screen.md (R07, reviewed 2026-11-15)
  - docs/notes/2026-11-15-upstream-reuse-audit.md (R04, reviewed 2026-11-15)
  - docs/notes/2026-11-15-wifi-onboarding-options.md (N01, reviewed 2026-11-15)
  - docs/evidence.md; docs/project-brief.md; docs/work/cards/R02.md; docs/work/cards/R04.md
  - docs/research/2026-11-15-armv6-wheels.md; docs/research/2026-11-15-rpi-preseed.md; docs/comparisons/sources.md
  - Public source URLs and revisions in the source-check ledger below, checked 2026-11-15
supersedes: []
---

## Summary and verdicts

Independent desk review, not a device test or an architecture decision. The four
original notes are preserved unchanged. Line numbers below refer to those notes
as read. Findings concern a specific claim, not the whole project or all versions.

| Note | Verdict | High | Medium | Low |
| --- | --- | ---: | ---: | ---: |
| [R02 complete alternatives](2026-11-15-complete-alternatives-comparison.md) | **Major revision before buying guidance.** Useful inventory and reports; complete-cost and exclusivity conclusions are not established. | 2 | 4 | 1 |
| [R07 alternative boards](2026-11-15-alternative-board-screen.md) | **Revise before screening or shortlisting decisions.** Useful pinout leads, but several exclusions and comparisons are stronger than the evidence. | 1 | 5 | 0 |
| [R04 upstream reuse](2026-11-15-upstream-reuse-audit.md) | **Major revision before choosing a builder or reuse plan.** Valuable pinned-source audit; boot, target feasibility and image reproducibility are not proved. | 3 | 4 | 0 |
| [N01 Wi-Fi onboarding](2026-11-15-wifi-onboarding-options.md) | **Major revision before implementation.** Its single-radio flow is internally impossible and its credential/re-entry guidance has security and recovery gaps. | 3 | 5 | 0 |
| **Total** | 28 distinct findings; cross-note references below are not additional findings. | **9** | **18** | **1** |

Severity: **High** can materially misdirect a product, security, recovery, buying,
or implementation decision; **Medium** needs correction or qualification before
relying on the affected claim; **Low** is a traceability/editorial defect. A
finding can group related occurrences of the same underlying problem. Verdicts
do not mean the unaffected claims have all been independently verified.

## R02 findings

| ID / severity | Location and evidence | Finding / recommended correction |
| --- | --- | --- |
| R02-1 **High** | Lines 144–168, 223–225, 291; [brief](../project-brief.md) cost scope; [evidence rules](../evidence.md) | The purported complete Debra list mixes GBP and USD, omits priced storage, cable, speaker/amplifier, enclosure, tax and shipping, and cannot prove that its parts are cheaper than every alternative or cost $30–50. A target near $40 **with some parts already owned** is not an all-in retail price. Provide dated, variant-specific US/import prices, comparable assumptions, and separate complete-purchase and reused-parts totals; do not invent an exchange rate. |
| R02-2 **High** | Lines 45–66, 199–225, 237–238, 299–302; [Satellite1 music](https://docs.futureproofhomes.net/satellite1-streaming-music/) and [M5Stack YAML](https://raw.githubusercontent.com/m5stack/esphome-yaml/main/common/atom-voices3r-satellite-base.yaml) | “Only” buyable voice/music box, “nobody” sells browser configuration, and the asserted only reasons to build exceed the checked market and conflict with the note's own VoiceS3R vendor YAML containing Sendspin. YAML presence does **not** prove an assembled out-of-box product; equally, one vendor's claim does not prove market exclusivity. Scope to the evaluated products and firmware; separate browser onboarding from full browser maintenance, and retain the brief's other goals. |
| R02-3 **Medium** | Lines 109–115, 176–180, 242–244; [latency report](https://community.home-assistant.io/t/ha-voice-preview-edition-slow-to-play-audio/819069) | A 20–50-second anecdote does not establish that latency is host-bound: the thread discusses fast processing and different behavior between devices. Nor do individual dropout reports prove Wi-Fi is the general cause or “solved” wake-word quality. Keep reports attributed, causal explanations as hypotheses, and quality unmeasured. Amplifier wattage alone also does not establish loudness. |
| R02-4 **Medium** | Lines 92–99, 153–154, 245–247; [project brief](../project-brief.md) | The claim that every listed device needs HA, or that cloud is **only** relevant when a host is too weak for Whisper, conflates the comparison's HA use case with independent vendor ecosystems and other supported cloud/local choices. State per-row prerequisites and optional services; do not turn one local model's host guidance into a universal requirement. |
| R02-5 **Medium** | Lines 92, 150, 195–197, 273–275; [ameriDroid](https://ameridroid.com/products/home-assistant-voice-preview-edition/) | The $180 for three is approximately the device-only subtotal, not three complete music setups; Seeed's two-per-account limit and unconfirmed stock make purchasing three from that seller unestablished. The note itself records preorder/sold-out sellers. Add three power supplies, speakers, tax and shipping, and check a feasible purchase route before promising an afternoon. |
| R02-6 **Medium** | Lines 94, 98, 231–236, 279–280; [VoiceS3R YAML](https://raw.githubusercontent.com/m5stack/esphome-yaml/main/common/atom-voices3r-satellite-base.yaml); [Sendspin page](https://www.music-assistant.io/player-support/sendspin/) | Vendor VoiceS3R prose names ESPHome 2026.1.0 while the checked mutable YAML names 2026.10.0; neither establishes all versions of a working build. The Google Cast row cites a Sendspin page even while its own limitation labels Cast behavior a hypothesis. Pin the exact config, verify dependencies, and cite the actual Cast provider or leave the row unknown. |
| R02-7 **Low** | Lines 45–46, 90–100, 319–324 | The comparison has **seven** named buyable products, plus Willow and the Debra baseline, not six. Numbered keys such as `[S4]`, `[S5]` and `[S22]` are not defined as Markdown references in this note; merely listing them in a separate register does not make those keys clickable. Link directly or define local references. |

## R07 findings

| ID / severity | Location and evidence | Finding / recommended correction |
| --- | --- | --- |
| R07-1 **High** | Lines 95, 100, 123–125, 225–227; [Libre forum JSON](https://hub.libre.computer/t/aml-s905x-cc-le-potato-overview-resources-and-guides/288.json) | Orange Pi Zero 2W's table not listing I2S is not proof the signal is absent; the note itself says the schematic and overlay were not checked. For original Le Potato, a **user**, not the vendor, asserts I2S is absent from the 40-pin header; the vendor reply suggests selecting I2S in `alsamixer` and does not establish a separate connector. Mark direct HAT use unverified/not demonstrated pending exact schematic, mux, voltage and driver evidence, rather than assert vendor-proved exclusion. Zero 3's 26-pin mechanical limitation remains a separately sourced observation. |
| R07-2 **Medium** | Lines 21, 106–108; [Armbian Zero 2W page](https://www.armbian.com/orange-pi-zero-2w/) | B11 is the **Zero 2W**, not the Orange Pi 3B board page. The 3B Armbian statement is therefore mis-cited; find the correct exact-board page and date/tier or mark it unknown. |
| R07-3 **Medium** | Lines 98, 109, 157–160; [Radxa ZERO 3W header](https://docs.radxa.com/en/zero/zero3/hardware-design/hardware-interface) | Pull-ups described on pins 3/5 do not by themselves prove that those pins are muxed to I2C, so “one of the two is wrong” is not established. The published table says UART on 3/5, I2C4 on 27/28, and **I2C5 SCL on 29 / SDA on 31**. Preserve the uncertainty and consult schematic and pinctrl before a wiring decision. |
| R07-4 **Medium** | Lines 106, 109–110, 203–207, 224–226; [Arace listing](https://arace.tech/products/radxa-zero-3w) | ZERO 3W is called “cheapest” when ROCK 3C and 3B prices are unknown and the $20 variant is reported sold out. The “3× spread” compares €53 in 2026 with a $15 2023 launch figure; currencies, dates, variant, stock, tax and shipping are not comparable. Treat both as dated leads, not a price ranking or multiple. |
| R07-5 **Medium** | Lines 58–62, 99, 120, 145–148, 185–202; [ROCK 3C pin table](https://docs.radxa.com/en/rock3/rock3c/hardware-design/hardware-interface) | “No overlay exists,” “every candidate needs a hand-written simple-audio-card overlay,” and “only” drop-in host go beyond a screen that did not read device trees or demonstrate boot/audio. Matching I2S and I2C positions is a promising lead, not enough to prove clocks, pinmux, power, SPI, GPIO, fit, or software support. Say no overlay was **identified or tested** and compare all necessary signals. |
| R07-6 **Medium** | Lines 39–42, 87–89, 208–213; [brief hardware scope](../project-brief.md) and [evidence rules](../evidence.md) | The note explicitly narrows the screen to one HAT, whereas the product research also asks for board-native expansions and USB audio. Those other paths are explicitly untested, not rejected. Do not turn the six-row HAT screen into a complete alternative-board recommendation; add separate sourced native/USB options and exact power/mechanical evidence. |

## R04 findings

| ID / severity | Location and evidence | Finding / recommended correction |
| --- | --- | --- |
| R04-1 **High** | Lines 164–167, 300–307; [ARMv6 artifact report](../research/2026-11-15-armv6-wheels.md) | “An armhf image boots on a Zero W” is presented as fact although neither this audit nor its cited dependency report booted or inspected that image. The inspected problematic piwheels artifacts are strong packaging evidence, not proof every installation route fails or a Zero W runtime works. Keep OS boot, each wheel's architecture, wake-engine repair and full voice/music performance as separate unverified questions. Do not silently downgrade full Zero W support. |
| R04-2 **High** | Lines 28–34, 174, 189–191, 204–211; [pinned rpi-image-gen guide](https://raw.githubusercontent.com/raspberrypi/rpi-image-gen/fb44a4cde4ac/getting_started.adoc) | “Cannot build/express a Zero W target” conflicts with the cited upstream guide saying the target can be any Pi, with some layers unavailable on older targets. An absent ready-made class/v6 layer is a real gap, but does not prove a custom layer cannot work. Rate the route **unproven and possibly requiring work**, not impossible; independently verify layers and a build before selecting or rejecting it. |
| R04-3 **High** | Lines 60, 110–113, 149, 297–299, 367–369; [pinned PiCompose workflow](https://raw.githubusercontent.com/florian-asche/PiCompose/1e5ff410163bcbb4704daea0c277fccc63a91214/.github/workflows/build-image-template.yml) | The workflow uses mutable `usimd/pi-gen-action@v1` and `pi-gen-version: arm64`. `c0d2c9f2cffc` is a branch head observed on the audit date, **not** proof of the pi-gen revision used for a particular earlier published image or a reproducible dependency pin. Recover actual build provenance or pin both inputs and rebuild under a separately authorized plan. |
| R04-4 **Medium** | Lines 112–114, 126–134, 311–312, 352–355; [workflow](https://raw.githubusercontent.com/florian-asche/PiCompose/1e5ff410163bcbb4704daea0c277fccc63a91214/.github/workflows/build-image-template.yml); [pi-gen first-user docs](https://raw.githubusercontent.com/RPi-Distro/pi-gen/6e3ff62bfd9c690a6a3d1d7de259d5e0af40cb78/README.md) | Build inputs specify `pi`/`raspberry` and SSH, but `disable-first-boot-user-rename: 0` plus the note's own limitation prevent asserting that these credentials necessarily survive first boot or Imager customization. Flag a serious default-credential risk, not an observed login; inspect resulting image and first-boot behavior before any adoption. |
| R04-5 **Medium** | Lines 54–60, 167, 275, 345–347 | Several relative links to `2026-11-15-lva-requirements.md` and `2026-11-15-armv6-wheels.md` resolve under `docs/notes/`, but the actual files are under `docs/research/`. Correct link targets in a later reviewed change; the present correction links directly to the research files. |
| R04-6 **Medium** | Lines 164–165, 171–174, 275; [pinned pi-gen README](https://raw.githubusercontent.com/RPi-Distro/pi-gen/6e3ff62bfd9c690a6a3d1d7de259d5e0af40cb78/README.md) | “No onboarding” needs a distinction: pi-gen documents `ENABLE_CLOUD_INIT=1` by default and supports bootfs first-boot provisioning. That is not a complete user-facing portal or recovery service, but it is meaningful provisioning. `STAGE_LIST` also does not guarantee one never needs a fork or a patch. |
| R04-7 **Medium** | Lines 73–77, 95, 233–247, 251–266, 313–316; [LVA release workflow](https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/12e51272d37d786ed3168955b3fb6eda3c7159ce/.github/workflows/docker-build-release.yml) | The example `ghcr.io/ohf-voice/linux-voice-assistant:v1.1.18@sha256:…` is not a usable pin: public registry manifest lookup returned **404 for `v1.1.18`**, while `1.1.18` returned 200 with index digest `sha256:089f321a4e7408c61fbcd1ec691eb073961be022d651139f32b0dbead9b2af58` and amd64/arm64 entries. The digest was not pulled or tested; revalidate before adoption. Also, “minimum privilege” is not demonstrated by a compose example, and an unresolved PiCompose license conflict is not cleared simply by attribution or rewriting; review provenance and obligations. |

## N01 findings

| ID / severity | Location and evidence | Finding / recommended correction |
| --- | --- | --- |
| N01-1 **High** | Lines 65–68, 121–138, 221–227 | A single-radio sequence cannot keep the AP reachable, stop it before association, verify the newly assigned address, and display that address on the still-reachable AP page before it stops. Define separate concurrent/two-radio and nonconcurrent state machines. For the latter, explain disconnection **before** attempting association, restore the AP with a saved result on failure, and provide independent post-join discovery; do not promise an IP before DHCP assigns it. |
| N01-2 **High** | Lines 187–197; [Comitup default config](https://raw.githubusercontent.com/davesteele/comitup/main/conf/comitup.conf) | The cited 3-second pins 39/40 action is optional `enable_nuke`, disabled by default, and **deletes all defined Wi-Fi connections** before restarting Comitup. It is not a benign re-entry example and contradicts preserving a previous fallback profile. Do not recommend activating it as ordinary recovery; design and test a non-destructive re-entry separately. |
| N01-3 **High** | Lines 201–210; [Pi cloud-init article](https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/) | The assertion that credentials live **only** in NetworkManager keyfiles is unproved: upstream says cloud-init stores `network-config` in `/etc/netplan/` without modification. Deleting the FAT seed alone does not prove all credential-bearing copies, caches or backups are removed. Map and protect the actual lifecycle for the selected version; inspect every copy and demonstrate cleanup without logging credentials. |
| N01-4 **Medium** | Lines 130–133, 150–158 | Requiring a default route and successful DNS or HTTP conflicts with the same note's “continue anyway” LAN-only case. Define association, local-address/HA reachability, DNS and internet as separate states; do not fail an otherwise usable local-only network solely for absent internet. Diagnose only causes supported by actual error codes, rather than promising an exact cause for every failure. |
| N01-5 **Medium** | Lines 150–152, 165–166 | A 2.4 GHz-only radio cannot itself scan a 5 GHz-only SSID and show it greyed out. A phone-assisted or manually entered SSID could supply independent information, but is a different, unverified workflow. Show only what the radio can observe and explain the limitation. |
| N01-6 **Medium** | Lines 44–55, 168–175, 265–267; [Pi configuration](https://www.raspberrypi.com/documentation/computers/configuration.html) | A country selection displayed only on the same Wi-Fi portal cannot help when the radio is disabled before the portal starts. A country preselected for an unspecified destination is not a safe universal factory default. Treat correctly scoped builder-provided country and a reachable non-Wi-Fi selection/rescue path as proposals requiring an end-to-end design and legal/regulatory verification. The article's board-specific gate is not proof of Zero 2 W behavior. |
| N01-7 **Medium** | Lines 89, 235–236, 317–319; [Pi USB gadget guide](https://www.raspberrypi.com/news/usb-gadget-mode-in-raspberry-pi-os-ssh-over-usb/) | “Only port” and “data-only” are inaccurate generalizations: the gadget port also supplies power; Zero boards have separate PWR IN and OTG ports; Pi 5 retains other USB host ports. Availability of a powered host, cable, driver and enabled gadget remains model-specific. It is a rescue candidate, not a demonstrated universal fallback. |
| N01-8 **Medium** | Lines 51–63, 82–89, 361–365; [Pi gadget article](https://www.raspberrypi.com/news/usb-gadget-mode-in-raspberry-pi-os-ssh-over-usb/), [gadget repository](https://github.com/raspberrypi/rpi-usb-gadget), [WiFi Connect release assets](https://github.com/balena-os/wifi-connect/releases/expanded_assets/v4.11.91) | The Pi article says gadget support is included in Trixie images dated 2025-10-20 onward; the repository README describes inclusion as future. Record this upstream conflict and inspect the exact image rather than asserting inclusion as tested. WiFi Connect's release has armv7/aarch64/x86_64/i686 assets, not an ARMv6 asset; this does not prove source build failure. A new Debra-owned portal, rejected alternatives and seed choice remain proposals for the open reuse/onboarding decision, not established requirements. |

## Cross-note contradictions and overlaps

| Topic | Comparison | Resolution / evidence level |
| --- | --- | --- |
| Pi Zero W | R02 64–66 and R04 345–347 call full support open; R04 164–167 and 300–303 state an armhf image boots; R04 204–209 rules out rpi-image-gen. | These are not equivalent. No boot or runtime was demonstrated by these notes; the image-builder feasibility is unresolved, and inspected wheel defects do not authorize dropping the full-support goal. See R04-1/2. |
| Price and availability | R02 lists Pi Zero 2 W at £14.40 incl. VAT and HAT at $12.90; R07's Zero 3W is $20 sold out, and Orange Pi Zero 2W is a separate €53 2026 or $15 2023 report. | Different boards, variants, sellers, currencies, times, taxes and accessories. No direct contradiction or common-currency cheapest result can be derived. Both notes acknowledge missing costs, despite stronger conclusions elsewhere; see R02-1 and R07-4. |
| Software and ARM versions | R07 cites current mutable LVA/Sendspin Python minimums; R04 evaluates LVA commit `12e5127` and its released container architecture. | Python version, CPU instruction set, wheel availability and image-builder architecture are different constraints. Python ≥3.12 does not prove ARMv6 wheels or performance; a 64-bit container does not prove source cannot be built. Compare exact pins and actual artifacts, not labels alone. |
| Builder provisioning / onboarding | R04 says pi-gen provides no onboarding; N01 documents cloud-init provisioning and recommends a builder seed; [pi-gen README](https://raw.githubusercontent.com/RPi-Distro/pi-gen/6e3ff62bfd9c690a6a3d1d7de259d5e0af40cb78/README.md) documents cloud-init. | Preseed is a provisioning mechanism, not an interactive portal. The two notes can agree once R04 qualifies “no onboarding”; neither proves the selected image has been validated or that N01's credential cleanup works. |
| Interface scope | R02 describes browser-first ordinary use; R07 175–180 uses older “SSH TUI” wording. | The current [brief](../project-brief.md) explicitly records browser-first normal operation and SSH/CLI/TUI as recovery/developer alternatives. Do not erase SSH as a recovery option or represent the older wording as the current everyday journey. |
| Sound/complete-device claims | R02 describes Voice PE as feedback-speaker plus external speaker and Satellite1 as assembled music/voice; R07 is a HAT/header screen, not a whole-device evaluation. | Neither a HAT pinout nor a vendor streaming claim proves comparable voice quality, acoustic performance, sync, or a full usable purchase. No cross-note hardware test was performed. |

## Arithmetic, conversions, dimensions, and counts

This pass recalculated the numerical comparisons and derived quantities in all
four notes; quoted product specifications, addresses, version numbers, clock
rates and proposed timeouts are identifiers or source values, not independently
measured dimensions or performance. No unprovided exchange rate was assumed.

| Note / calculation | Recalculation and limit |
| --- | --- |
| R02 Voice PE one-unit subtotal | $58.95 + $10 + $25 = **$93.95**; $59 + $20 + $60 = **$139.00**, before tax/shipping. “~$95–140” is reasonable approximate rounding, not a strict arithmetic error. The power/speaker ranges are estimates, not linked complete shopping carts. |
| R02 three units | 3 × $58.95 = **$176.85**; 3 × $59 = **$177.00**; ~$180 is a rounded **devices-only** estimate. With three of each estimated PSU and speaker, **$281.85–$417.00**, before taxes/shipping and subject to stock/quantity limits. |
| R02 other totals | Satellite1 is **$132.99–$134.99 plus an unpriced supply**, not a computed complete total. Echo Dot is **$79.99 plus any applicable subscription and unpriced setup**; $19.99/month × 12 = **$239.88/year** if paid all 12 months. The stated $6.50/month × 12 = **$78/year**, versus $65/year for the quoted optional annual plan: $13, or **16.67%**, less than 12 monthly payments, assuming equivalent coverage and no tax. No subscription need is inferred from this arithmetic. |
| R02 currencies and dimensions | £14.40 + £7.70 = **£22.10**, plus **$12.90** and unpriced items; no USD grand total is calculable without an exchange rate and comparable dated tax/shipping. $69 − $58.95 = **$10.05** (14.57% of $69); $69 − $59 = **$10** (14.49%). These are US dollar prices, not a conversion of €59. The **3.5 mm** figure is a nominal audio-jack size, not a computed speaker or case dimension. Seven buyable rows, one open-project row, one Debra baseline. |
| R07 prices, pin counts, dimensions | Nominal 53/15 = **3.53**, but €53/$15 is not a valid monetary ratio without an exchange rate, same market/date and variant. $20 is one out-of-stock listing, not a comparable purchase total. Six screened board rows; 40 versus 26 header positions is a count, not a measured mounting dimension. The 13-pin expansion is separate. 3.3 V/5 V and 2–3 A are cited specifications, not measured electrical compatibility or derived HAT power budgets. |
| R04 percentages and resources | The listed 80% PGA and 100% volume settings are configuration values, not measured loudness or a percent improvement; the 512 MB/~4 GB figures are upstream stated minimums, not measured Debra consumption. Dates and release identifiers are not arithmetic; asset/tag checks are in the ledger. |
| N01 timers, addresses, frequencies | 60 s = **1 minute**; 15 minutes = **900 s**; 3 s is the source's destructive optional GPIO hold, not a measured recovery time. `10.12.194.1/28` is in `10.12.194.0/28` (usable `.1`–`.14`, broadcast `.15`); `10.42.x.1/24` is a separately assigned shared-network example. Neither means two simultaneous devices were tested. 2.4/5 GHz are bands, not case dimensions or throughput measurements. No dimensional conversion is asserted in N01. |

## Source-check ledger

Checked 2026-11-15 using read-only public HTTP retrieval. These are bounded spot
checks, not independent acceptance of every claim on each page. Mutable pages can
change; pinned raw URLs are preferable for later implementation. Product prices
and stock are dated snapshots; a different later listing is not retroactive proof
of error. At least five distinct public URLs were checked for each note.

### R02 — six checks

| Public source | Check / outcome |
| --- | --- |
| [Voice PE product](https://www.home-assistant.io/voice-pe/) | Page retrieved; $69 and feedback-speaker wording appear. Does not establish a complete music-purchase price. |
| [ameriDroid Voice PE](https://ameridroid.com/products/home-assistant-voice-preview-edition/) | Page retrieved; $58.95 and preorder text occur. Stock must be rechecked at purchase, not inferred for other sellers. |
| [Satellite1 music docs](https://docs.futureproofhomes.net/satellite1-streaming-music/) | Vendor describes Sendspin and out-of-box Music Assistant path. It is vendor documentation, not a Debra test or proof of market exclusivity. |
| [M5Stack VoiceS3R YAML](https://raw.githubusercontent.com/m5stack/esphome-yaml/main/common/atom-voices3r-satellite-base.yaml) | Mutable source contains Sendspin and references ESPHome 2026.10; this is config evidence, not a preassembled-product test. |
| [VoiceS3R shop](https://shop.m5stack.com/products/atom-echos3r-smart-speaker-dev-kit) | Retrieved listing contains $14.50 and stock text; HTML can contain contradictory variant/stock strings. No purchase or availability promise. |
| [Voice PE delay discussion](https://community.home-assistant.io/t/ha-voice-preview-edition-slow-to-play-audio/819069.json) | Reported delays and device-dependent observations do not establish host-bound causation. |

### R07 — seven checks

| Public source | Check / outcome |
| --- | --- |
| [Radxa ZERO 3W header](https://docs.radxa.com/en/zero/zero3/hardware-design/hardware-interface) | Table documents UART3, I2S3 and I2C pin labels; pull-up wording alone does not resolve mux. |
| [Radxa ROCK 3C header](https://docs.radxa.com/en/rock3/rock3c/hardware-design/hardware-interface) | I2C3 and I2S3 pin labels retrieved; pin-position match is not a complete HAT test. |
| [Armbian Zero 2W](https://www.armbian.com/orange-pi-zero-2w/) | HTML title identifies Orange Pi Zero2W, not 3B. |
| [Libre forum JSON](https://hub.libre.computer/t/aml-s905x-cc-le-potato-overview-resources-and-guides/288.json) | User I2S assertion and vendor reply are distinguishable; no vendor-confirmed 40-pin absence established by the quoted reply. |
| [LVA pyproject](https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/main/pyproject.toml) | Mutable file contains Python ≥3.11 metadata; not an ARM runtime test. |
| [Sendspin CLI pyproject](https://raw.githubusercontent.com/Sendspin/sendspin-python-cli/main/pyproject.toml) | Mutable file contains Python ≥3.12 metadata; not proof wheels work on every board. |
| [Arace ZERO 3W listing](https://arace.tech/products/radxa-zero-3w) | HTML includes $20 and sold-out text; variant-specific availability and complete delivered cost require a fresh check. |

### R04 — seven checks

| Public source | Check / outcome |
| --- | --- |
| [PiCompose pinned workflow](https://raw.githubusercontent.com/florian-asche/PiCompose/1e5ff410163bcbb4704daea0c277fccc63a91214/.github/workflows/build-image-template.yml) | `arm64`, mutable action version, and user/SSH build inputs confirmed; actual built image not inspected. |
| [pi-gen pinned README](https://raw.githubusercontent.com/RPi-Distro/pi-gen/6e3ff62bfd9c690a6a3d1d7de259d5e0af40cb78/README.md) | 32/64 branch guidance, external `STAGE_LIST` and cloud-init input confirmed. |
| [rpi-image-gen pinned getting-started](https://raw.githubusercontent.com/raspberrypi/rpi-image-gen/fb44a4cde4ac/getting_started.adoc) | Says any Pi target but older-target layer limitations; no build performed. |
| [LVA pinned release workflow](https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/12e51272d37d786ed3168955b3fb6eda3c7159ce/.github/workflows/docker-build-release.yml) | Workflow declares amd64/aarch64 and semver-derived image tags; not evidence for unlisted source builds. |
| [LVA public OCI registry](https://ghcr.io/v2/ohf-voice/linux-voice-assistant/manifests/1.1.18) | Anonymous read-only manifest query: `1.1.18` 200 with amd64/arm64; `v1.1.18` 404. The registry requires an anonymous bearer token for this URL; no container was pulled. |
| [PiCompose v1.1.4 assets](https://github.com/florian-asche/PiCompose/releases/expanded_assets/v1.1.4) | Lists base, 2MicHat-v2, ReSpeaker Lite and Satellite1-v1.0 image variants with and without LVA, plus checksums. Asset names do not prove images boot. |
| [RAUC v1.15.2](https://github.com/rauc/rauc/releases/tag/v1.15.2) | Release tag resolves as cited; no recovery implementation was evaluated. |

### N01 — six checks

| Public source | Check / outcome |
| --- | --- |
| [Comitup config](https://raw.githubusercontent.com/davesteele/comitup/main/conf/comitup.conf) | `enable_nuke` documents destructive deletion of defined Wi-Fi connections; password option also appears. Mutable main is not a pinned implementation test. |
| [Pi cloud-init article](https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/) | Documents `/etc/netplan/` copy without modification, so seed-only cleanup is insufficient evidence. |
| [Pi USB gadget article](https://www.raspberrypi.com/news/usb-gadget-mode-in-raspberry-pi-os-ssh-over-usb/) | Identifies board-specific OTG ports and power/network use; compare the conflicting repository inclusion wording. |
| [Imager v2.0.12](https://github.com/raspberrypi/rpi-imager/releases/tag/v2.0.12) | Release page identifies PR 1745 and UTF-8 SSID fix; this does not prove every preseed issue is fixed. |
| [WiFi Connect v4.11.91 assets](https://github.com/balena-os/wifi-connect/releases/expanded_assets/v4.11.91) | Lists aarch64, armv7, i686, x86_64 and UI assets; no ARMv6 binary asset. Source-build outcome unknown. |
| [NetworkManager settings](https://networkmanager.dev/docs/api/latest/nm-settings-nmcli.html) | `shared` configuration and DHCP behavior documented; does not by itself implement the requested onboarding state machine. |

## Verification

- Procedure: read the four files, project brief, evidence rules, relevant cards,
  source register and related ARMv6/preseed research; search project memory;
  retrieve the public URLs above; recalculate the values shown. Public GitHub
  release expanded-assets pages were used because normal release pages defer
  rendering their asset lists. Registry lookup read metadata only.
- Result: **partial desk review**, 28 findings, source checks as recorded. No
  purchase, device contact, installation, flashing, build, image/container pull,
  or network/service configuration occurred. The sole intended output is this
  review note; no commit or push was made by this review.
- Pre-existing/concurrent working-tree changes are outside this review and were
  neither reverted nor attributed to it. The original notes remain unchanged.

## What I did not check

- I did not validate every cited URL, every product variant, all shopping carts,
  tax, shipping, or current stock, nor listen to devices or measure latency,
  synchronization, acoustic quality, pin voltages, dimensions or power.
- I did not inspect source trees exhaustively, reproduce the earlier ARM ELF
  inspection, boot Pi Zero W or alternative boards, build images, import wheels,
  test a portal, exercise rollback, verify credential erasure, or conduct legal
  review. The noted absence of a source or asset is not proof it cannot exist.
- Public pages and release assets can change; HTTP retrieval of a page or a
  manifest is not proof of functional behavior. Some original checks reported
  blocked/partial pages and JavaScript-only content. This review does not turn
  any proposal, note, or future experiment into authorization.

## Handoff and correction links

- Current state: the four research notes remain unreviewed research; this
  independent review is itself unreviewed, and no architecture or buying decision
  has been made. Source revisions and dates are in the ledger; local comparison
  files may contain concurrent changes.
- Next action: coordinator review of the high-severity findings, then correct
  curated guidance through a separately scoped change. Resolve the single-radio
  state machine, credential lifecycle and Zero W image/runtime evidence before
  implementing or purchasing on the disputed claims.
- Authorization needed: any purchase, board operation, network change, build,
  installation, publication, or edits outside this review require the applicable
  separate scope and recovery plan.
- Earlier claims corrected or qualified: the specific claims cited in the four
  tables above; `supersedes: []` because no entire note or standing decision is
  replaced. Reviewed report/decision adopting these findings: none known.
