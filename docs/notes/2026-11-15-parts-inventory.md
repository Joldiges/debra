---
title: Parts inventory and build cost
date: 2026-11-15
type: project-learning
status: unreviewed
task: R01
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - "[P1] https://www.adafruit.com/product/3400 — Raspberry Pi Zero W, $15.00, in stock, max 2 per customer (2026-11-15)"
  - "[P2] https://www.adafruit.com/product/3708 — Raspberry Pi Zero WH (pre-soldered header), $16.00, in stock, max 2 per customer (2026-11-15)"
  - "[P3] https://www.adafruit.com/product/5291 — Raspberry Pi Zero 2 W, $19.05, OUT OF STOCK (2026-11-15)"
  - "[P4] https://www.adafruit.com/product/6008 — Raspberry Pi Zero 2W with Header, $19.80, OUT OF STOCK (2026-11-15)"
  - "[P5] https://www.pishop.us/product/raspberry-pi-zero-2-w/ — Pi Zero 2 W SC1176, $17.25, 'Notify Me' (2026-11-15)"
  - "[P6] https://www.pishop.us/product/raspberry-pi-zero-2w-with-headers/ — Pi Zero 2 W with Header SC0721, $20.75, 'Notify Me'; duplicate listing at $21.75 (2026-11-15)"
  - "[P7] https://thepihut.com/products/raspberry-pi-zero-2-w — Zero 2 W £14.40, with header £17.30, in stock, GBP incl. VAT (2026-11-15)"
  - "[P8] https://thepihut.com/products/raspberry-pi-5 — Pi 5 1GB £43.20 / 2GB £74.40 / 4GB £105.60 / 8GB £168.00 / 16GB £369.60, in stock, GBP incl. VAT (2026-11-15)"
  - "[P9] https://www.pishop.us/product/raspberry-pi-5-4gb/ — Pi 5/4GB $110.00, availability 'OutOfStock' in the page's own product schema (2026-11-15)"
  - "[P10] https://www.seeedstudio.com/ReSpeaker-2-Mics-Pi-HAT.html — reSpeaker 2-Mics Pi HAT V2.0, SKU 107100001, USD$12.90 (2026-11-15)"
  - "[P11] https://www.waveshare.com/wm8960-audio-hat.htm — WM8960 Hi-Fi Sound Card HAT, SKU 15668, $18.99 (1), $17.99 (2), $17.49 (3), $17.29 (4+); package: HAT + 8Ω 5W speaker + screws (2026-11-15)"
  - "[P12] https://www.adafruit.com/product/1995 — 5V 2.5A switching PSU with 20AWG micro-USB cable, $8.25, in stock (2026-11-15)"
  - "[P13] https://www.pishop.us/product/raspberry-pi-12-5w-power-supply-us-white/ — official RPi 12.5W micro-USB PSU, US, $8.80, in stock; https://www.pishop.us/product/wall-adapter-power-supply-micro-usb-2-4a-5-25v/ 5.1V 2.5A UL $8.45, in stock (2026-11-15)"
  - "[P14] https://www.pishop.us/product/microsd-card-32-gb-class-10-blank/ — SanDisk Ultra 32GB Class 10 blank, $13.95, in stock; official RPi A2 32GB $19.95 'Notify Me'; SanDisk 32GB with Pi OS 64-bit $19.95 in stock (2026-11-15)"
  - "[P15] https://www.pishop.us/product/usb-c-pd-power-supply-for-raspberry-pi-5-27w-etl-listed/ — 27W USB-C PD PSU $11.95; https://thepihut.com/products/raspberry-pi-27w-usb-c-power-supply £11.50 (2026-11-15)"
  - "[P16] https://www.adafruit.com/product/2822 (price shown in the accessory list on [P1]) — 2x20 male header strip, $0.95; https://www.pishop.us/product/color-coded-header-for-raspberry-pi/ $1.95 (2026-11-15)"
  - "[P17] https://www.amazon.com/dp/B0B4D1BN4F, https://www.amazon.com/dp/B0B4D2Z35P, https://www.amazon.com/dp/B0BHST51PQ — all three returned HTTP 503 to this session; no 2026-11-15 price obtained (2026-11-15)"
  - "[P18] models/components/dweii-speakers/README.md — module identities, ASINs, electrical and mechanical claims, 4-pack product family for 701715519664 and 701715520462"
  - "[P19] docs/archive/readme-research-before-2026-11-15.md — historical README prices, undated, retained as a historical record only"
  - "[P20] https://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT/ (as cited in docs/notes/2026-11-15-alternative-board-screen.md [B14]) — HAT has its own micro-USB power input; vendor asks for it to be powered when using the speaker (2026-11-15)"
  - "[P21] https://www.pishop.us/search.php?search_query=zero+2+w — Pi Zero W $17.25 'Choose Options'; bought Zero cases: HiPi Zero Friction $7.45, Super Slim $4.95, Pibow Zero 2 W $8.95, UniPiCase Zero Tall $11.95 'Notify Me' (2026-11-15)"
  - "[P22] https://www.pishop.us/product/high-speed-hdmi-cable-for-pi-zero-gold-plated-connectors-3ft/ $4.95; https://thepihut.com/products/micro-hdmi-to-standard-hdmi-a-cable from £4.80 (2026-11-15)"
  - "[P23] docs/notes/2026-11-15-complete-alternatives-comparison.md — earlier record of Pi Hut £14.40 and Seeed $12.90 on 2026-11-15, reused here rather than re-derived"
  - docs/work/cards/R01.md, docs/roadmap.md, docs/project-brief.md, docs/evidence.md
supersedes: []
---

# Parts inventory and build cost

## Summary

**Two totals, both listed prices, neither a price paid.** All figures are what a
seller's page displayed on **2026-11-15**; no purchase was made, no cart was
checked out, no shipping or tax is included anywhere below.

| Total | What it buys | Amount |
| --- | --- | --- |
| **Complete build** (everything bought new, US sellers, voice + music) | Zero 2 W with header, ReSpeaker 2-Mics V2.0, one DWEII speaker, 32 GB microSD, one 5 V supply | **$59.90** listed |
| same, with a second supply for the HAT's own power input | as above plus a second 5 V supply | **$68.35** listed |
| **Reused-parts build** (Pi, power supply, microSD and printer already owned) | ReSpeaker 2-Mics V2.0 + one DWEII speaker | **$16.40** listed |
| same, if the Pi is a bare Zero with no header | + 2×20 header | **$17.35** listed |

**The ~$40 goal is reachable, but only in the reused-parts sense.** A new Pi
Zero W ($15, in stock) or Zero 2 W with header ($20.75) plus the HAT ($12.90) and
a speaker ($2.50–3.50) lands at **$31.35–$37.15** *if* the buyer already has a
5 V supply, a microSD card and printer access. A fully-inclusive retail kit does
**not** reach $40 and is not close: **$59.90–$68.35**.

**The single biggest caveat is stock, not price.** The Pi Zero 2 W — the board
this project actually wants — was **out of stock at both US sellers checked**
(Adafruit, PiShop) on the date of this note, and in stock only from a UK seller
in GBP. The one board that *is* in stock in the US is the original **Pi Zero W**,
whose ARMv6 support for this software stack is exactly what packet Z01 has not
established.

**Nothing here is tested.** This note prices parts; it does not prove that any
combination boots, records, plays, or fits in a case.

## How to read the prices

Per [evidence.md](../evidence.md):

- **Listed price**, not MSRP and not price paid. Only the Home Assistant Voice PE
  has a vendor-stated MSRP in this project ($69/€59) and it is not in this note.
  No cart was assembled, so shipping, tax and import duty are **excluded
  everywhere**. Two of the four sellers here (Seeed, Waveshare) ship from China
  and both advertise local-warehouse options that were not exercised.
- **Currencies are not converted.** USD and GBP figures appear side by side and
  are never added together. A GBP total is given only where every line in it is
  GBP, and there is no such total in this note — the HAT is only priced in USD,
  so a mixed-currency build cannot be totalled honestly.
- **Quantities matter.** Where a part is sold in a pack, the pack quantity is a
  column. The DWEII modules are sold as 4-packs in at least two cases
  [P18], which is why their per-module prices below are marked unreliable.
- **Stock is a snapshot.** Several of these rows changed within the same day in
  the earlier R02 session ([P23]); treat every stock cell as expired.
- `required` / `optional` / `dev-only` is a *build* judgement for this note, not
  a compatibility claim.

## 1. Boards

| Part (exact name / revision) | Seller, currency | Unit price | Pack qty | Stock, 2026-11-15 | Required? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Raspberry Pi Zero W (SC0020) | Adafruit, **USD** [P1] | **$15.00** | 1 | **In stock**, max 2 per customer | required (ARMv6 target) | No GPIO header fitted. Single-core ARMv6, 512 MB. ARMv6 support for LVA/Sendspin is unproven — see Z01 |
| Raspberry Pi Zero WH (Zero W with pre-soldered header) | Adafruit, **USD** [P2] | **$16.00** | 1 | **In stock**, max 2 per customer | required | The same board with the header already on; removes the soldering step |
| Raspberry Pi Zero W | PiShop, **USD** [P21] | **$17.25** | 1 | "Choose Options" — availability is per-variant, not stated in the list | alternative | Different seller, higher listed price than Adafruit |
| Raspberry Pi Zero 2 W (SC1176) | PiShop, **USD** [P5] | **$17.25** | 1 | **"Notify Me"** — out of stock | required (leading candidate) | No header. This is the board the project actually wants |
| Raspberry Pi Zero 2 W | Adafruit, **USD** [P3] | **$19.05** | 1 | **Out of stock** | required | Same board, higher listed price |
| Raspberry Pi Zero 2 W (SC1176) | The Pi Hut, **GBP** [P7] | **£14.40** incl. VAT | 1 | **In stock** | required | The only in-stock Zero 2 W found. GBP — not converted, not addable to the USD totals |
| Raspberry Pi Zero 2 W **with header** (SC0721) | PiShop, **USD** [P6] | **$20.75** | 1 | **"Notify Me"** — out of stock | required | A second PiShop listing for the same product shows $21.75 — see Traps |
| Raspberry Pi Zero 2 W **with header** | Adafruit, **USD** [P4] | **$19.80** | 1 | **Out of stock** | required | |
| Raspberry Pi Zero 2 W with header | The Pi Hut, **GBP** [P7] | **£17.30** incl. VAT | 1 | **In stock** | required | Avoids the header purchase and the soldering |
| Raspberry Pi 5, 1 GB | The Pi Hut, **GBP** [P8] | **£43.20** incl. VAT | 1 | In stock | dev-only | Cheapest Pi 5 observed; whether 1 GB runs LVA + Sendspin is `unknown` |
| Raspberry Pi 5, 2 GB | The Pi Hut, **GBP** [P8] | **£74.40** | 1 | In stock | dev-only | |
| Raspberry Pi 5, 4 GB | The Pi Hut, **GBP** [P8] | **£105.60** | 1 | In stock | dev-only (lab reference) | The lab unit's board class |
| Raspberry Pi 5/4GB | PiShop, **USD** [P9] | **$110.00** | 1 | **Out of stock** (page schema) | dev-only | |
| Raspberry Pi 5, 8 GB / 16 GB | The Pi Hut, **GBP** [P8] | £168.00 / £369.60 | 1 | In stock | not needed | Listed only to show the spread; nothing in Debra needs this |

**Pi 5 note.** Both sellers price the 4 GB board near **$110 / £105.60**. That is
well above the figure people usually associate with a Pi 5, and the 16 GB at
£369.60 confirms a very wide 2026 spread. **I did not investigate why** and I am
not asserting a cause. What it does mean practically: the Pi 5 is a poor value
*dev* board right now, and the lab already owns one.

## 2. Audio HATs

| Part (exact name / revision) | Seller, currency | Unit price | Pack qty | Stock, 2026-11-15 | Required? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| **reSpeaker 2-Mics Pi HAT V2.0**, SKU 107100001 | Seeed, **USD** [P10] | **$12.90** | 1 | Price and buy control shown; **no stock count displayed on the page fetched** | required (voice) | V2.0 = **TLV320AIC3104** codec (the V1 was WM8960). 2 analogue mics, 3 APA102 LEDs, 3.5 mm jack, user button, 65 × 30 × 15 mm. Seeed states V2.0 supports Pi 5 |
| **WM8960 Hi-Fi Sound Card HAT**, SKU 15668 / "WM8960 Audio HAT" | Waveshare, **USD** [P11] | **$18.99** (1), $17.99 (2), $17.49 (3), $17.29 (4+) | 1 HAT **+ 1 × 8 Ω 5 W speaker + 2 screws** | No stock indicator on the page fetched | required (alternative) | WM8960 codec, I²S + I²C, dual MEMS mics, 3.5 mm jack, **1 W per channel into 8 Ω BTL**, 98 dB DAC SNR |
| reSpeaker 2-Mics Pi HAT **V1** (WM8960-based) | no current primary listing found | **unknown** | — | — | optional | Only a historical $8 AliExpress figure exists [P19]. A V1 is a *different codec* needing a different overlay (`wm8960` at I²C `0x1a`) — see Traps |

**Which one.** The V2 HAT is the part the lab has actually run
([devices.md](../comparisons/devices.md) `[T]`, Pi 5 + 2-Mics v2). The WM8960
HAT is the better *value* line item because it ships with a speaker and has a
1 W/channel amplifier on board, so it needs no separate amp and no second power
supply — but it is **not** the combination Debra has tested, and its amplifier is
1 W, not 3–5 W.

**Bundle claim corrected.** The archived README said the Waveshare HAT "arrives
with Stereo version of the 701715520462" [P19]. The vendor's current package list
says **one 8 Ω 5 W speaker** [P11]. The archive is a historical record, not a
current specification; the current package list wins.

## 3. Speakers

| Part (exact name / ASIN) | Seller, currency | Unit price | Pack qty | Stock, 2026-11-15 | Required? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| DWEII **701715519671**, 8 Ω 3 W, JST-PH 2.0, 110 mm lead ([B0B4D1BN4F](https://www.amazon.com/dp/B0B4D1BN4F)) | Amazon, **USD** | **unknown** — page returned HTTP 503 [P17] | **unknown** (family sold as 4-packs) | **unknown** | required (one of three) | Historical figure **$2.50** [P19], undated. Smallest envelope, 44 × 28 × 15 mm per spec sheet [P18] |
| DWEII **701715519664**, 8 Ω 3 W, JST-PH 2.0, 480 mm lead ([B0B4D2Z35P](https://www.amazon.com/dp/B0B4D2Z35P)) | Amazon, **USD** | **unknown** [P17] | **4-pack** product family [P18] | **unknown** | required (one of three) | Historical **$2.50** [P19]. Same module as 671 with a longer lead; no individual module size is published |
| DWEII **701715520462**, 8 Ω **5 W** (5.5 W max), JST-PH 2.5 ([B0BHST51PQ](https://www.amazon.com/dp/B0BHST51PQ)) | Amazon, **USD** | **unknown** [P17] | **4-pack** [P18] | **unknown** | required (one of three) | Historical **$3.50** [P19]. 100 × 45 × 21 mm, best-sourced envelope. **Does not fit any case in this repository** — choosing it is a new case, not a pocket change |

**Honest position on speaker prices:** the three modules this project has
modelled could not be priced at all on 2026-11-15. Every total below that
includes a speaker is therefore **an arithmetic result using a historical
figure**, and the note says so at the point of use rather than burying it.
The $2.50–$3.50 band is plausible for a commodity module but is not evidence.

**A HAT with an amplifier does not need an amplifier; a HAT without one does.**
The ReSpeaker 2-Mics has no speaker amplifier — it drives the 3.5 mm jack and
line-level output. The DWEII modules are passive 8 Ω drivers. A build using the
2-Mics HAT and a bare DWEII module needs **an amplifier between them**, which is
not in any table here and was not priced. The WM8960 HAT does not have this
problem (1 W/ch BTL on board). This is the largest hidden cost in the cheap
route and it is `unknown`.

## 4. Storage

| Part (exact name) | Seller, currency | Unit price | Pack qty | Stock, 2026-11-15 | Required? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| SanDisk Ultra microSDHC 32 GB, Class 10 / UHS-I, blank | PiShop, **USD** [P14] | **$13.95** | 1 | **In stock** | required | The realistic cheap choice; 32 GB is ample for a satellite image |
| SanDisk microSD 32 GB with Raspberry Pi OS 64-bit pre-installed | PiShop, **USD** [P14] | **$19.95** | 1 | In stock | optional | Pre-imaged; irrelevant to Debra, which writes its own image |
| Official Raspberry Pi A2 V30 microSD 32 GB, blank (SC1628) | PiShop, **USD** [P14] | **$19.95** | 1 | **"Notify Me"** — out of stock | optional | |
| Official Raspberry Pi A2 microSD 64 GB, blank (SC1629) | PiShop, **USD** [P14] | **$30.95** | 1 | In stock | optional | |
| Official Raspberry Pi A2 microSD 64 GB, blank | Adafruit, **USD** [P14] | **$12.79** | 1 | **Out of stock** | optional | Cheaper listed than the 32 GB official card at PiShop, which is a reminder that capacity does not track price |
| SD/microSD 8 GB SDHC | Adafruit, **USD** [P14] | **$23.50** | 1 | **Out of stock** | not recommended | Priced for completeness; a bad deal and too small |
| microSD extension cable, 15 cm | PiShop, **USD** | $6.95 | 1 | In stock | optional | Only useful if the case blocks the slot |

## 5. Power

| Part (exact name) | Seller, currency | Unit price | Pack qty | Stock, 2026-11-15 | Required? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 5 V 2.5 A switching PSU with 20 AWG **micro-USB** cable (ID 1995) | Adafruit, **USD** [P12] | **$8.25** | 1 | **In stock** | required (Zero-class) | 5.25 V output to compensate cable drop; US 2-prong; cable included and captive |
| Official Raspberry Pi 12.5 W micro-USB PSU, US, white (SC0623) | PiShop, **USD** [P13] | **$8.80** | 1 | **In stock** | required (Zero-class) | The vendor's recommended supply for micro-USB Pis |
| Micro-USB PSU 5.1 V 2.5 A, UL listed | PiShop, **USD** [P13] | **$8.45** | 1 | In stock | alternative | |
| **Second** 5 V micro-USB supply for the HAT's own power input | either of the above | **$8.45–$8.80** | 1 | In stock | required **if** the HAT's power input is used | See the note under the totals: Seeed asks for the HAT to be powered separately when its speaker is used [P20] |
| Official Raspberry Pi 27 W USB-C PD PSU | PiShop **USD** $11.95 [P15]; The Pi Hut **GBP** £11.50 | — | 1 | In stock at both | required (Pi 5 only) | The Pi 5 will not take a micro-USB supply; the two supplies are not interchangeable |

**Power is not one part.** A Zero-class unit needs a micro-USB 5 V supply; a Pi 5
needs USB-C PD. Anyone reusing "a phone charger" is reusing an unknown-quality
supply, which is the failure mode the lab already hit — the lab Pi 5's rail
sagged under load with its old supply and reset the board
([lab result](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md)). Cheap
supplies are a false economy here, and this is not a price question.

## 6. Cables, headers and adapters

| Part | Seller, currency | Unit price | Pack qty | Stock, 2026-11-15 | Required? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Break-away 0.1″ 2×20-pin dual **male** header strip (ID 2822) | Adafruit, **USD** [P16] | **$0.95** | 1 strip | Not separately checked | required **only** for a bare Zero / Zero 2 W | Needs soldering to the board. Buying the "WH" / "with header" board avoids both |
| Colour-coded 2×20 header for Pi Zero | PiShop, **USD** [P16] | **$1.95** | 1 | In stock | alternative | Same function, colour-coded |
| Micro-USB cable with in-line on/off switch | The Pi Hut, **GBP** [P7 accessory list] | **£3.00** incl. VAT | 1 | Listed on the Zero 2 W page | optional | A power switch is genuinely useful; without it the only way to power-cycle is to unplug |
| Mini-HDMI → HDMI cable, 3 ft | PiShop, **USD** [P22] | **$4.95** | 1 | In stock | optional (setup only) | Only needed for a first-boot console on a Zero |
| Micro-HDMI → HDMI cable (Pi 5) | The Pi Hut, **GBP** [P22] | from **£4.80** | 1 | In stock | optional (setup only) | Pi 5 uses micro-HDMI; a Zero uses **mini**-HDMI. These are different cables |
| Micro-USB OTG adapter | The Pi Hut, **GBP** [P7 accessory list] | **£0.50** | 1 | In stock | optional | Only for USB-gadget setup |
| USB-C microSD card reader/writer | Adafruit, **USD** | $6.95 | 1 | **Out of stock** | optional | Only if the host has no card slot |

**What the HAT needs, exactly.** A ReSpeaker 2-Mics HAT is a 40-pin HAT: it needs
the Pi's 2×20 male header to be **present**, which is the whole reason the
header row above exists. The Pi Zero W and Zero 2 W ship with the header
footprint unpopulated; the "WH" / "with header" variants and the Pi 5 do not.
There is no other adapter in the path — no ribbon, no shim — for the 2-Mics HAT
on a Pi. Whether the Waveshare HAT includes a mating 2×20 socket in the box is
**not stated** on its package list [P11] and is `unknown`.

## 7. Enclosure

| Part | Seller, currency | Unit price | Pack qty | Stock, 2026-11-15 | Required? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| **Printed tray** from this repository (`models/`) | — | **unknown** (filament cost not priced; printer access assumed by the brief) | — | **Nothing has been printed** | required (intended) | The repository's tray is a design. It has not been sliced, printed or fit-tested, and there is no case or lid. Its own README says so |
| HiPi Zero Friction Case | PiShop, **USD** [P21] | **$7.45** | 1 | In stock | optional | **Bare Zero only** — no room for a HAT stack |
| Super Slim Raspberry Pi Zero Case | PiShop, **USD** [P21] | **$4.95** | 1 | In stock | optional | Same limitation |
| Pibow Zero 2 W | PiShop, **USD** [P21] | **$8.95** | 1 | In stock | optional | Layered; a HAT generally does not fit |
| UniPiCase Zero – Tall | PiShop, **USD** [P21] | **$11.95** | 1 | **"Notify Me"** — out of stock | optional | The only bought case here that might clear a HAT; not verified |

**No bought case in this list is documented as fitting a Pi Zero + audio HAT
stack.** They are all bare-board cases. The printed tray is the only design in
the project that accounts for the stack, and it does not exist as a printed
object yet.

## Totals, with the arithmetic shown

### A. Complete build — everything bought new (USD, listed, 2026-11-15)

| Line | Part | USD |
| --- | --- | --- |
| 1 | Pi Zero 2 W **with header** (PiShop $20.75 [P6]; Adafruit $19.80 [P4]) — **both out of stock** | 20.75 |
| 2 | reSpeaker 2-Mics Pi HAT V2.0 (Seeed [P10]) | 12.90 |
| 3 | DWEII 701715520462 5 W speaker — **historical figure, not a 2026-11-15 price** [P19] | 3.50 |
| 4 | SanDisk Ultra 32 GB microSD (PiShop [P14]) | 13.95 |
| 5 | Official 12.5 W micro-USB PSU (PiShop [P13]) | 8.80 |
| | **Subtotal, one power supply** | **59.90** |
| 6 | Second 5 V supply for the HAT's power input (if used) [P13] | 8.45 |
| | **Subtotal, two power supplies** | **68.35** |
| | Enclosure (printed) | unknown |
| | Speaker **amplifier** for a passive DWEII module on the 2-Mics HAT | unknown |
| | Shipping, tax, import duty | **excluded** |

### B. Reused-parts build — Pi, power supply, microSD and printer already owned

| Line | Part | USD |
| --- | --- | --- |
| 1 | reSpeaker 2-Mics Pi HAT V2.0 [P10] | 12.90 |
| 2 | DWEII speaker — historical figure [P19] | 3.50 |
| | **Total** | **16.40** |
| 3 | 2×20 header, if the owned Pi is a bare Zero / Zero 2 W [P16] | 0.95 |
| | **Total with header** | **17.35** |

This is the number the brief warns about: it is a **marginal** cost, not the
price of a unit. It is also the only one of the two that reaches the ~$40 goal
with room to spare — because most of the unit is already on the shelf.

### C. Reference totals that are *not* a Debra unit

| Build | Parts | USD |
| --- | --- | --- |
| Lab/dev board (Pi 5) | Pi 5/4GB $110.00 [P9] + 27 W USB-C PSU $11.95 [P15] + 32 GB microSD $13.95 [P14] | **135.90** |
| WM8960 route, complete | Zero 2 W with header $20.75 + WM8960 HAT $18.99 (speaker included) [P11] + microSD $13.95 + PSU $8.80 | **62.49** |
| WM8960 route, reused Pi/PSU/SD | WM8960 HAT $18.99 | **18.99** |

The WM8960 route is **$62.49** complete versus **$59.90** for the 2-Mics route —
within a few dollars, and it needs no separate amplifier and no second supply,
which the 2-Mics route does. It is *not* the tested combination, which is why it
is not the recommendation.

## Cheapest route

**Is $40 reachable? Yes — as a parts-only figure for someone who already owns a
Pi, a 5 V supply, a microSD card and printer access. No — as the price of a
complete unit.** The gap is not close: the complete build is $59.90 before
shipping, and $68.35 if the HAT is powered as Seeed asks.

Three concrete routes, cheapest first:

| Route | Parts | USD | Depends on |
| --- | --- | --- | --- |
| **1. New Zero W + HAT, reuse PSU/microSD/printer** | Zero W $15.00 [P1] + 2×20 header $0.95 [P16] + ReSpeaker V2 $12.90 [P10] + speaker (historical $2.50) | **$31.35** | **ARMv6 working at all.** Unproven (Z01). 512 MB, single core |
| **2. New Zero WH + HAT, reuse PSU/microSD/printer** | Zero WH $16.00 [P2] + ReSpeaker V2 $12.90 + speaker ($2.50) | **$31.40** | Same ARMv6 risk, but no soldering |
| **3. New Zero 2 W with header + HAT, reuse PSU/microSD/printer** | $20.75 [P6] + $12.90 + $3.50 | **$37.15** | Board **out of stock** in the US; in stock as £17.30 at The Pi Hut, which cannot be added to a USD total |

Route 3 is the only one that is both under $40 and on a board anyone expects to
work — and it is the one you cannot currently buy in the US at that price.

**What the $40 figure excludes, stated plainly:**

1. **The power supply** ($8.45–$8.80) and **the microSD card** ($13.95). Together
   that is $22.40 — more than half of the remaining budget.
2. **The enclosure.** Either printer access and filament (unpriced) or a bought
   case ($4.95–$11.95) that does not fit a HAT stack anyway.
3. **The speaker amplifier**, if a passive DWEII module is driven from the
   2-Mics HAT. Unpriced and easy to miss.
4. **A second power supply for the HAT's own input** ($8.45), which Seeed asks
   for when the speaker is used [P20].
5. **Shipping, tax and import duty.** The cheapest HAT ships from China; the
   cheapest board ships from the UK or a US seller with a 2-per-customer cap.
6. **Availability.** A $31.35 route that requires an out-of-stock board is not a
   route; it is a wish with arithmetic attached.
7. **Time and the probability of success.** Not priced here and not priced
   anywhere in the project yet.

**Honest recommendation for a first unit:** do not optimise to $40. Buy the
Zero 2 W **with header** (in stock as £17.30, GBP) plus the V2 HAT and a 32 GB
card, and accept ~$60–70 complete. The $40 figure buys a Zero W whose ARMv6
support is the project's biggest open engineering question, and a first unit that
does not work is more expensive than a first unit that costs $20 more.

## Traps

1. **The board you want is out of stock; the board in stock is the risky one.**
   Pi Zero 2 W was out of stock at Adafruit [P3][P4] and PiShop [P5][P6] on
   2026-11-15 and in stock only at The Pi Hut in GBP [P7]. The Pi Zero W is in
   stock at Adafruit [P1][P2] — with a 2-per-customer cap. A price table that
   ignores stock is fiction, and this one nearly was.
2. **Stock moved during the day.** Two sellers flipped stock within an hour in
   the R02 session [P23]; Waveshare and Seeed displayed **no stock indicator at
   all** on the pages fetched, so their rows are "orderable-looking", not
   "in stock". Re-check before buying.
3. **Revision drift on the HAT is the expensive trap.** "ReSpeaker 2-Mics" names
   **two different codecs**: V1 is WM8960, V2.0 is TLV320AIC3104 [P10]. They need
   different overlays, and only V2.0 is documented as Pi 5-capable. A cheap
   "ReSpeaker" at $8 [P19] is a V1 or a clone. The revision is printed on the
   board — read it, and see
   [Seeed's revision guide](https://wiki.seeedstudio.com/how-to-distinguish-respeaker_2-mics_pi_hat_hardware_revisions/).
4. **"ReSpeaker" is a family, not a product.** Seeed's own page cross-sells
   XVF3800, 4-mic and XIAO variants on the same listing [P10]. Buying the wrong
   one is one click away.
5. **Counterfeit and clone risk is real but unpriced.** The historical budget
   route leans on an AliExpress "Keyestudio ReSpeaker" at $8 [P19]. Nothing in
   this note verifies that any such board is a genuine Seeed design, and a clone
   codec may enumerate differently or not at all. No counterfeit was examined;
   this is a risk statement, not a finding.
6. **Pack quantities hide the real unit price.** Two of the three DWEII modules
   are sold as **4-packs** [P18]. A "$3.50" figure may be one module out of a
   four-pack or the whole pack — the listings could not be read [P17] and the
   historical figure does not say. Do not build a total on it without checking.
7. **The PiShop Zero 2 W listings disagree with each other.** The same
   "with header" product appears at **$20.75** and **$21.75** on two URLs [P6],
   and the Pi 5 page's own bullet list says "2GB LPDDR4X" while its
   specification says 4 GB [P9]. Seller copy is not a specification.
8. **The Pi 5 price is not what people remember.** $110 / £105.60 for 4 GB
   [P8][P9]. Whatever the cause, it means a Pi 5 is now a significant purchase
   and the lab's existing board is an asset, not a spare.
9. **Supplies are not interchangeable across the two boards.** Zero-class takes
   micro-USB 5 V; Pi 5 takes USB-C PD and will brown out on a lesser supply. The
   lab already reset a board on a sagging rail.
10. **Shipping is the invisible line item.** Seeed ships from China and
    advertises a local-warehouse option that was not exercised [P10]; Adafruit
    and PiShop ship from the US; The Pi Hut ships from the UK with VAT already
    in the price. A $12.90 HAT can arrive with a shipping charge comparable to
    the HAT. **No shipping figure is included in any total here.**
11. **The enclosure does not exist yet.** Every bought Zero case in this list is
    for a bare board [P21]; the repository's tray has never been printed. A
    complete build is not complete until someone prints and fits one.
12. **The 5 W DWEII module is a different case design, not an upgrade.** At
    100 × 45 × 21 mm it fits no case in this repository
    ([dweii README](../../models/components/dweii-speakers/README.md)). "Better
    speaker" and "same enclosure" are mutually exclusive here.

## Not verified / open questions

- **No part was bought, and no cart was assembled.** Every figure is a listed
  price. Shipping, tax, duty and any discount are unknown and excluded.
- **Speaker prices are `unknown`.** All three Amazon listings returned HTTP 503
  [P17]. The $2.50 / $3.50 figures used in the totals are **historical and
  undated** [P19] and are the weakest numbers in this note. If they are wrong by
  2×, the complete total moves by $3.50 — not enough to change the conclusion,
  but enough that the total should not be quoted as a price.
- **Pack quantity for the DWEII modules is `unknown`.** Two are documented as
  4-packs [P18]; the 671 is not.
- **Whether the ReSpeaker 2-Mics HAT needs its own 5 V input in Debra's
  configuration is `unknown`.** Seeed asks for it when the speaker is used
  [P20]; the lab Pi 5 ran music playback through the HAT, but this note does not
  establish whether that was with the HAT's power input connected. If it is not
  needed, the complete total drops from $68.35 to $59.90.
- **The amplifier question is unanswered.** The 2-Mics HAT has no speaker
  amplifier and the DWEII modules are passive. How the lab's audio actually
  reached a speaker is in the lab record, not here, and no amplifier was priced.
  Until this is resolved, the "cheap" route has an unpriced component.
- **No stock status for Seeed or Waveshare.** Neither page displayed one.
- **Pi 5 price cause not investigated.** $110 / £105.60 observed; no explanation
  asserted.
- **Filament cost not priced.** The printed case is `unknown`; printer access is
  assumed by the brief, not verified for any particular user.
- **No physical measurement of any part.** Dimensions in
  [dweii-speakers](../../models/components/dweii-speakers/README.md) are seller
  claims. Nothing was measured, fitted or printed.
- **The V1 HAT has no current listing.** Its $8 historical figure [P19] could
  not be confirmed and the board may not be sold new at all.
- **GBP and USD are not reconciled.** A UK-sourced build (Pi Hut board + PSU +
  card) could not be totalled because the HAT is only priced in USD. Anyone
  building in the UK should re-run these five lines in GBP.
- **No compatibility claim is made anywhere in this note.** A part being priced
  and in stock says nothing about whether it works, fits, or sounds acceptable.

## Handoff and correction links

- **Current state:** a dated price snapshot and a part list. Nothing purchased,
  nothing tested, no device touched, no CAD changed.
- **What this adds:** the cost arithmetic R01 asked for, two honest totals, and a
  documented failure to price the speakers. It does not supersede
  [devices.md](../comparisons/devices.md) (hardware) or
  [music-playback.md](../comparisons/music-playback.md) (transport).
- **Concrete next action, cheapest first:** read the three Amazon listings from a
  session that Amazon will serve, and record pack quantity, per-unit price and
  stock for the DWEII modules. That single gap is the difference between a
  sourced inventory and an estimate, and it is desk work with no purchase.
- **Then:** resolve the amplifier question from the lab record — what actually
  drove the speaker in the tested unit. If the answer is "an amplifier we already
  own", the cheap route is real; if it is "the HAT drove it directly", the
  electrical claim needs checking before anyone copies the build.
- **Authorization:** none of this is permission to buy, flash, print, or operate
  anything. Prices and stock move; re-check before acting.
- **For the coordinator:** R05 should not present these as a "kit price". The
  reused-parts total is a marginal cost, and the brief explicitly says never to
  present that as a fully inclusive retail price.
