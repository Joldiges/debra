---
title: Alternative board screen, revision 2
date: 2026-11-15
type: project-learning
status: unreviewed
task: R07
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - "docs/notes/2026-11-15-alternative-board-screen.md (R07, revision 1, superseded) — read 2026-11-15"
  - "docs/notes/2026-11-15-research-notes-review.md, section 'R07 findings' — read 2026-11-15"
  - "docs/evidence.md; docs/project-brief.md; docs/comparisons/README.md; docs/comparisons/devices.md — read 2026-11-15"
  - "[C1] https://docs.radxa.com/en/zero/zero3/hardware-design/hardware-interface — checked 2026-11-15"
  - "[C2] https://docs.radxa.com/en/rock3/rock3c/hardware-design/hardware-interface — checked 2026-11-15"
  - "[C3] https://radxa.com/products/rock3/3c/ — checked 2026-11-15"
  - "[C4] http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_Zero_2W — checked 2026-11-15"
  - "[C5] http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_Zero_3 — checked 2026-11-15"
  - "[C6] http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_3B — checked 2026-11-15"
  - "[C7] https://www.armbian.com/orange-pi-zero-2w/ (renders as /boards/orangepizero2w, title 'Orange Pi Zero2W') — checked 2026-11-15"
  - "[C8] https://www.armbian.com/orange-pi-3b/ (renders as /boards/orangepi3b, title 'Orange Pi 3B') — checked 2026-11-15"
  - "[C9] https://hub.libre.computer/t/aml-s905x-cc-le-potato-overview-resources-and-guides/288.json — checked 2026-11-15"
  - "[C10] https://arace.tech/products/radxa-zero-3w — checked 2026-11-15"
  - "[C11] https://botland.store/702-orange-pi — checked 2026-11-15"
  - "[C12] https://raspberry.tips/raspberrypi-infos/raspberry-pi-zero-2-w-alternative-ausverkauft (article dated 2026-11-08) — checked 2026-11-15"
  - "[C13] https://pinout.xyz/pinout/pin12_gpio18 (third-party Pi 40-pin reference) — checked 2026-11-15"
  - "[C14] https://www.raspberrypi.com/documentation/computers/raspberry-pi.html — HTTP 403, not readable, 2026-11-15"
supersedes:
  - docs/notes/2026-11-15-alternative-board-screen.md
---

## Summary

This note replaces the R07 screen after independent review. It corrects six
findings (one high, five medium) and does not add new boards. Two changes run
through all of them:

1. **An empty table cell is not an absent signal.** Everywhere revision 1 wrote
   "not present", this revision writes "not documented in the source checked"
   and names the drawing or file that would decide it.
2. **Prices from different years, currencies, variants and stock states are not
   comparable.** Every ranking and multiple is removed. What remains are dated,
   variant-specific seller figures, or `unknown`.

**Outcome of the screen, stated as evidence rather than verdict:** on the
published vendor tables, the **Radxa ROCK 3C** and **Radxa ZERO 3W** both document
I2S at the four positions a Pi HAT uses (12/35/38/40) plus an SoC MCLK at 13. The
ROCK 3C also documents I2C on pins 3/5; the ZERO 3W documents UART3 there and its
I2C buses at 27/28 and 29/31. **Neither board has a demonstrated HAT host**: no
overlay was identified or tested, no device tree was read, and no board was
powered. The **Orange Pi 3B** is undecided because its pin table is published only
as images. The **Orange Pi Zero 2W** documents no I2S function on its 40-pin
header and is not a HAT candidate on current evidence. The **Orange Pi Zero 3**
has no 40-pin header. The **Le Potato** is not demonstrated either way: the
"not in the 40-pin header" statement is a user report, and the vendor's reply
does not address header routing.

Nothing here is a compatibility claim, a shortlist for purchase, or a change to
[the master device table](../comparisons/devices.md). No board was bought,
imaged, powered or contacted. No device tree, schematic or overlay was opened.

## Evidence labels and method

`D` upstream-documented · `R` reported · `H` hypothesis · `U` unknown. An empty
cell is never "no". Same convention as [comparisons/README.md](../comparisons/README.md).

Every source marked `[C#]` was retrieved in this revision on **2026-11-15**.
Claims carried from R07 without re-reading are marked **carried** and keep R07's
`[B#]` keys so the provenance stays visible. The `[B#]` keys are R07's own
register and are not re-listed here; for convenience they map to:

| Key | R07 source (not re-read in this revision unless also given a `[C#]`) |
| --- | --- |
| `[B7]` `[B8]` | Radxa ZERO 3W and ROCK 3C download pages — kernel/distro claims |
| `[B10]` | libre.computer AML-S905X-CC-V2 product page (JS-rendered in R07) |
| `[B13]` | Arace Tech ZERO 3W listing (re-checked this revision as `[C10]`) |
| `[B14]` `[B15]` | Seeed ReSpeaker 2-Mics Pi HAT wiki and v2 install page |
| `[B16]` | `seeed-2mic-voicecard` v1 overlay DTS |
| `[B17]` `[B18]` | LVA and Sendspin CLI `pyproject.toml` Python floors |
| `[B19]` | LVA discussion 99 (community opinions) |
| `[B22]` | Debra's own Pi 5 + 2-Mics test record in `devices.md` |

The Raspberry Pi documentation site
returned **HTTP 403** again [C14], so Pi-side pin positions are cited from a
third-party pinout [C13] labelled `R`.

Two scope notes from the review are accepted as written:

- This is a screen of one specific HAT against six boards. It is not a complete
  alternative-board recommendation, and it does not evaluate board-native audio
  or USB audio as replacement paths (see "Still unknown").
- The Orange Pi Zero 3 header-count observation is kept because its source
  supports it, but it settles mechanics only (see below).

## The corrected per-board screen

### Table 1 — signals a Pi HAT needs, at the positions a Pi uses

Pi-side positions for reference [C13 R]: 3/5 = I2C1 SDA/SCL · 11 = GPIO17 ·
12/35/38/40 = PCM CLK/FS/DIN/DOUT · 13 = GPIO27 (no clock) · 19/21/23/24 = SPI0
MOSI/MISO/SCLK/CE0 · 27/28 = the dedicated HAT ID EEPROM bus.

| Board (exact revision) | 40-pin header | I2S at 12/35/38/40 | Clock at 13 | I2C for a codec at 3/5 | SPI at 19/21/23/24 | GPIO at 11 | Board-native audio | HAT status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Orange Pi Zero 2W V1.1** (H618) | Yes, 40 positions, 28 GPIO, 3.3 V; **pins not soldered by default** [C4 D] | **Not documented in the vendor's 40-pin table.** Pins 12, 18, 29, 31, 35, 36, 37, 38, 40 each list only a GPIO name and no alternate function [C4 D]. Vendor summary of the header: "GPIO, UART, I2C, SPI, PWM" [C4 D] | Not documented; pin 13 is `PH3 UART5_RX` [C4 D] | **Documented:** pin 3 `PI8 TWI1-SDA`, pin 5 `PI7 TWI1-SCL` [C4 D]. Also TWI0 at 15/22, TWI2 at 27/28 | Documented: `SPI1_MOSI/MISO/CLK/CS0` at 19/21/23/24, `SPI1_CS1` at 26 [C4 D] | Pin 11 is `PH2 UART5_TX` [C4 D] — a UART function is what the table documents there, not a plain GPIO | Mini-HDMI audio; an onboard codec exists (the vendor's `aplay -l` shows `card 0: audiocodec … CDC PCM Codec-0`) [C4 D]; analog out and mic are on the 24-pin expansion board [C4 D] | **Not a HAT candidate on current evidence.** The codec bus is where a HAT expects it; the data path is not documented anywhere in the vendor table. `U` whether H618 I2S nets reach any header pad |
| **Orange Pi Zero 3** (H618) | **No.** Vendor lists a 26-pin connector ("I2Cx1, SPIx1, UARTx1 and multiple GPIO ports") and a 13-pin connector [C5 D] | No 40-pin positions exist. The 26-pin table lists no I2S function either [C5 D] | n/a | 26-pin pin 3 `PH5 TWI3-SDA`, pin 5 `PH4 TWI3-SCK` (as printed) [C5 D] | 26-pin 19/21/23/24 = `SPI1_MOSI/MISO/CLK/CS` [C5 D] | 26-pin pin 11 is `PC6` [C5 D] | 3.5 mm + AV **via the 13-pin expansion board**, and the analog AV entry says "(Android system only)" [C5 D]; the 13-pin board's **mic is explicitly unsupported** on this board ("No support, no support, no support!!!") [C5 D] | **No direct fit** — 26 positions, not 40. See the mechanical note below for exactly what that does and does not settle |
| **Orange Pi 3B** (RK3566) | Yes, 40 positions, 28 GPIO, 3.3 V [C6 D] | **`U` — not documented in text.** The full pin table, and its left/right halves, are published **only as three PNG images** [C6]; the vendor summary is "GPIO, UART, I2C, SPI, PWM" [C6 D] | `U` — image-only table | `U` — image-only table | `U` — image-only table | `U` — image-only table | 3.5 mm headphone jack with **input and output** [C6 D] | **Undecided, not "probably fine" and not excluded.** The decisive pin data exists; it is a picture and was not read |
| **Radxa ZERO 3W** (V1.11 production / V1.12 AIC8800 variant) | Yes, 40-pin; sold with or without a soldered header [C10 R] | **Documented:** 12 `I2S3_SCLK_M0`, 35 `I2S3_LRCK_M0`, 38 `I2S3_SDI_M0`, 40 `I2S3_SDO_M0` [C1 D] | **Documented:** 13 `I2S3_MCLK_M0` [C1 D] | **Not documented at 3/5.** The table assigns 3 `UART3_RX_M0`/`GPIO1_A0` and 5 `UART3_TX_M0`/`GPIO1_A1`; I2C4 is at 27/28 and I2C5 at 29/31 [C1 D]. See the pull-up note below | `SPI3_*_M1` at 19/21/23/24 [C1 D] | 11 = `GPIO3_A1` [C1 D] | None documented (micro-HDMI only) [C1 D] | **Four of five signal positions match; the codec bus does not.** A HAT's codec would need its two I2C wires moved to 27/28, or a mux decision this screen cannot make |
| **Radxa ROCK 3C** (V1.3 / V1.4) | Yes, 40-pin [C2 D] | **Documented:** 12 `I2S3_SCLK_M0`, 35 `I2S3_LRCK_M0`, 38 `I2S3_SDI_M0`, 40 `I2S3_SDO_M0` [C2 D] | **Documented:** 13 `I2S3_MCLK_M0` [C2 D] | **Documented:** 3 `I2C3_SDA_M0`, 5 `I2C3_SCL_M0` (UART3_RX/TX_M0 are listed as alternates on the same pins) [C2 D] | `SPI3_*_M1` at 19/21/23/24, `SPI3_CS1_M1` at 26 [C2 D] | 11 = `GPIO3_A1` [C2 D] | None documented [C2 D] | **All four Pi audio/control positions have a documented match** — the strongest documented starting point in this screen, and still only a starting point: clocking, pinmux selection, power, overlay and audio are all unproven |
| **Libre Computer Le Potato AML-S905X-CC** (S905X) | 40-pin header — **carried** from R07 [B10 R], not re-read this revision; the vendor index links a "GPIO Pinout Header Maps and Wiring Tool" topic [C9 D] | **Not documented as available.** The vendor's own pinned index lists "I2S - please request if needed" and "PCM - please request if needed" [C9 D]. A **user** reports "the signals are not in the 40-pin header" and `ldto` showing no i2s [C9 R] | `U` | `U` — no pin-level table was read | `U` | `U` | 3.5 mm jack (with its own "no analog audio issue" thread) and a separate SPDIF how-to [C9 D/R] | **Not demonstrated either way.** The vendor documents no I2S function and offers no overlay; one user says it is absent from the header; the vendor's reply does not address that |

### The Orange Pi Zero 3 26-pin observation, and what it implies

Kept, because the vendor states the connector counts directly [C5 D]. What it
implies: a 2×20 HAT cannot be fully seated. At most the first 13 rows (pins
1–26) would line up with the 26-pin header; pins 27–40 would have nothing under
them, so the HAT would be mechanically unsupported and electrically incomplete.

What it does **not** imply: nothing about whether the H618 I2S controller
exists, is routed to those 26 pads, or could be reached with jumpers. The 26-pin
header does carry `TWI3` at 3/5 and `SPI1` at 19/21/23/24 [C5 D], so a jumper
harness is a plausible but separate engineering task with its own decisive
document (the Zero 3 schematic). "No direct fit" is the whole of the claim.

### The ZERO 3W pull-up sentence, quoted rather than interpreted

Revision 1 treated the pull-up wording as contradicting the pin table. It does
not, and the two boards show why. Quoting both pages exactly [C1 D][C2 D]:

- ZERO 3W: *"Pin 3, Pin 5, Pin 27, and Pin 28 add extra pull-up resistors for
  I2C device power supply, so they work abnormally when used as GPIOs."*
- ROCK 3C: *"Pin 3 and Pin 5 have additional pull-up to power downstream I2C
  devices, as such when used as GPIO they may not work correctly."*

The same-shaped caution appears on a board whose table assigns `I2C3` to 3/5
(ROCK 3C) and on one whose table assigns `UART3` to 3/5 (ZERO 3W). The sentence
therefore carries no information about which function is muxed onto a pin; it
warns that a pin may already be pulled up for someone else's I2C device. What
the ZERO 3W table actually says is: UART3 on 3/5, I2C4 on 27/28, I2C5 SCL on 29
and SDA on 31 [C1 D]. Whether 3/5 can be muxed to I2C in software is `U`, and
the deciding documents are the ZERO 3W schematic and the RK3566 pinctrl in the
vendor kernel — not this page.

Documentation quality, also from [C2]: pin 31 is printed `I2C5_SCD_M0` on the
ROCK 3C page where the ZERO 3W page prints `I2C5_SDA_M0`. Vendor tables contain
typos; that is one more reason to treat them as leads and not as design inputs.

### Table 2 — dated, variant-specific prices

No ranking, no ratio, no "cheapest". A EUR marketplace price for a 1 GB board and
a USD single-listing page price are different markets, sellers, dates, variants
and stock states, and no exchange rate is assumed
([evidence.md](../evidence.md)).

| Board | Price | Variant | Seller / market | Date of the figure | Stock state then | Label |
| --- | --- | --- | --- | --- | --- | --- |
| Orange Pi Zero 2W | **53,00 € incl. VAT** | 1 GB | Amazon.de marketplace listing, via a German price article's live price widget | widget stamped 2026-11-11 19:50; article dated 2026-11-08 | "Nur noch wenige verfügbar" (few left) | [C12 R] |
| Orange Pi Zero 2W | "ab rund 86 €" | higher-RAM variants | same source, same market | 2026-11-08 (article text) | not stated | [C12 R] |
| Orange Pi Zero 2W | "rund 13 Dollar" | 1 GB | launch price, as recollected by the same article | historical, undated | n/a | [C12 R] — a historical lead, not a current price |
| Orange Pi Zero 3 | `U` | — | — | — | — | no seller page read |
| Orange Pi 3B | `U` | — | — | — | — | no seller page read |
| Radxa ZERO 3W | **$20.00** page regular price | which variant the $20 applies to was **not rendered**; 12 RAM/eMMC/header combinations are listed | Arace Tech (HK), USD | 2026-11-15 | **Out of stock**; all 12 combinations marked "Sold Out" | [C10 R] |
| Radxa ROCK 3C | `U` — no price published | — | Radxa states the product is "exclusively available through our network of Approved Partners" | 2026-11-15 | n/a | [C3 D] |
| Le Potato | `U` | — | — | — | — | no seller page read |

Correction to revision 1's price text: it compared "€53 for 1 GB" with a
"$15 2023 launch figure". The article's launch recollection is **"rund 13
Dollar"** for the 1 GB Zero 2W; the **$15** in the same article is the Raspberry
Pi Zero 2 W list price [C12]. The two figures were also never comparable as a
multiple, and the multiple is now removed.

## Finding-by-finding changes

| ID | Severity | What revision 1 claimed | What changed | Where in this note |
| --- | --- | --- | --- | --- |
| **R07-1** | High | Zero 2W "has no I2S" and its row was "not usable"; Le Potato "not usable as a HAT **on the vendor's own statements**", with the absence of I2S attributed to the vendor | Both re-stated as "not documented in the source checked". Zero 2W: the vendor's 40-pin table lists no I2S/PCM function on any pin — that is a statement about the table, and the deciding documents are the **Zero 2W schematic** (vendor download page, "user manual and schematic diagram") plus the **H618 datasheet pinmux** and the vendor kernel DTS. Le Potato: the "signals are not in the 40-pin header" sentence is a **user's** post, the vendor's pinned index only says "please request if needed", and the vendor reply ("select I2S or PCM in alsamixer") says nothing about header routing — so the vendor has **not** proved absence. The deciding documents are the **AML-S905X-CC schematic**, the **S905X pinmux**, and the `ldto` overlay list on a Libre image. Zero 3's 26-pin limitation is kept, separately sourced, and bounded | Table 1 rows 1, 6; "26-pin observation"; Table 3 |
| **R07-2** | Medium | The Orange Pi 3B's Armbian status was cited to `armbian.com/orange-pi-zero-2w/` | **Mis-citation confirmed and fixed.** That URL renders the page titled **"Orange Pi Zero2W"** (Community, 3 images, `current 6.18.63`, build date 2026-11-13) [C7]. Armbian has a **separate** 3B page, checked this revision: **"Orange Pi 3B"**, Community, 8 images, `current 6.18.63` and `vendor 6.1.172`, build date 2026-11-13 [C8]. The 3B's Armbian statement is now cited to [C8] and no longer borrows the Zero 2W's evidence. The Python-floor inference is demoted to `H` and no longer presented as a documented property of these images | Table 1; "Software, carried and not re-checked" |
| **R07-3** | Medium | "The Radxa ZERO 3W page contradicts itself … one of the two is wrong" | **Claim withdrawn.** The pull-up sentence does not establish a mux, and the same sentence shape appears on a board whose table *does* list I2C on 3/5. Both pages are now quoted verbatim and the uncertainty is preserved instead of being resolved by inference. The ROCK 3C's `I2C5_SCD_M0` typo is recorded as a documentation-quality caution | "The ZERO 3W pull-up sentence" |
| **R07-4** | Medium | "ZERO 3W … cheapest", a "3× spread", and a €53-vs-$15 comparison | **All removed.** No ranking, no multiple, no cross-currency or cross-date arithmetic. What remains: one dated EUR marketplace price for a named variant and stock state, one USD page price with the variant unresolved and the product sold out, and `U` for the rest. The "$15 launch" figure is corrected to the source's "rund 13 Dollar" | Table 2 |
| **R07-5** | Medium | "No overlay exists", "every candidate needs a hand-written overlay", ROCK 3C is the "only drop-in HAT host" | **Softened to what a desk screen can support:** no overlay was **identified or tested**, no device tree was read, and matching four pin positions is a lead, not a demonstration of clocks, pinmux, power, SPI, GPIO, fit or software. The screen now compares **all** the signals a HAT needs — I2S, MCLK, I2C, SPI, a GPIO at 11, and power — instead of only I2S and I2C | Table 1 (columns for MCLK, SPI, GPIO); "Still unknown" |
| **R07-6** | Medium | The six-row HAT screen read as an alternative-board recommendation | **Scope stated explicitly.** This note screens one HAT and says so. Board-native and USB audio are named as **untested, not rejected**, with the documented native paths recorded and the ReSpeaker Lite rows still `unreviewed` in [devices.md](../comparisons/devices.md) | Summary; "Native and USB audio" in Still unknown |

### Other corrections made while checking

- **Botland (trap 10).** Kept, and upgraded from inference to a seller
  statement: the page sits in Botland's "Withdrawn products" tree and says
  *"Tiny computers Orange Pi were withdrawn due to the lack of delivery from
  manufacturer's appropriate certification."* [C11 R]. This is one distributor's
  stated reason, not a certification finding.
- **Arace sold-out state (trap 10).** Kept with the detail revision 1 omitted:
  all twelve listed RAM/eMMC/header combinations were "Sold Out" [C10 R].
- **Libre kernel 6.18.68 (Table 2 of revision 1).** The forum topic discussing
  it is about **Alta and Solitude** boards, not Le Potato [C9]. It does not
  establish a Le Potato image.
- **"Documentation absence is a finding" (trap 9).** Kept as a documentation
  observation, but it no longer carries a verdict: a board whose pinout cannot
  be read is `U`, which is exactly what the 3B row now says.
- **Python floor (trap 8).** LVA ≥3.11 and Sendspin ≥3.12 were cited from
  mutable `pyproject.toml` files that this revision did not re-read. The claim is
  now marked carried and the distro-Python step is `H`.

## Decisive unknown per board

One check each. Filling these is the whole of R07's remaining desk work; none is
a purchase and none needs a device.

| Board | Decisive unknown (one check) | Exact document or artefact that decides it | Why it settles the row |
| --- | --- | --- | --- |
| **Radxa ROCK 3C** | Does an overlay that binds `i2s3_8ch` to a TLV320AIC3104 at `0x18` on `i2c3` (M0 pinctrl) boot and play/capture on a V1.4 board with the HAT fitted? | **ROCK 3C V1.4 schematic** + **RK3566 TRM pinmux** + the vendor kernel DTS for `i2s3_8ch`/`i2s3m0` + a written `simple-audio-card` overlay | All four Pi audio/control positions already have a documented match; this is the only board where the remaining question is "does the obvious overlay work" rather than "is the wire even there" |
| **Radxa ZERO 3W** | Can the HAT's codec be reached with its I2C moved to **I2C4 on 27/28** — i.e. a working overlay plus a documented two-wire re-pin? | **ZERO 3W schematic** (which is also the only thing that settles the 3/5 pull-up/mux question) + RK3566 pinctrl + a tested overlay | I2S is on the right pins; only the control bus is wrong. Two wires is a small change or a hard no, and only the schematic and a boot decide which |
| **Orange Pi 3B** | Which functions does the vendor's 40-pin table assign to 12/35/38/40 and 3/5? | The three PNG tables [C6], or better the **3B schematic PDF** from the vendor's "user manual and schematic diagram" download, or the vendor kernel DTS for the 3B | The data exists but is not machine-readable text here. Until it is read the board is `U`, not "probably compatible" |
| **Orange Pi Zero 2W** | Are H618 I2S nets routed to **any** 40-pin pad, and does the vendor kernel expose them? | **Zero 2W schematic** + **H618 datasheet pinmux** + the vendor kernel DTS for `i2s`/`pcm` | The vendor table lists no I2S function and the SoC clearly has an audio codec; only the schematic shows whether the data path reaches a pad at all |
| **Orange Pi Zero 3** | None for direct HAT fit — the vendor documents 26-pin and 13-pin connectors and no 40-pin header [C5 D]. If a jumper harness were ever considered, its decisive document is the Zero 3 schematic | Zero 3 schematic (jumper case only) | No drawing can make a 2×20 HAT seat on a 2×13 header; a harness is a different task |
| **Le Potato** | Do I2S/PCM signals reach the 40-pin header, and is there a maintained overlay for a WM8960/TLV320 codec? | **AML-S905X-CC schematic** + **S905X pinmux** + the `ldto` overlay list on a Libre image (the vendor's own wiring tool) | The vendor says "please request if needed" and offers no overlay; one user says the signals are absent; the vendor reply does not address it. The schematic is the only neutral arbiter |

## Still unknown

- **Nothing was tested.** No board was bought, powered, imaged, measured or
  contacted. Every row is documentation or a third-party report.
- **No device tree, schematic or overlay was opened for any board.** "Driver
  support" is therefore `U` everywhere. Matching pin labels on a marketing table
  is not evidence that a pinctrl group, a controller node or a codec binding
  exists in the kernel those images ship.
- **The HAT's own requirements are carried from R07, not re-read here:** I2S on
  the Pi's PCM pins, a TLV320AIC3104 at `0x18` on I2C-1, three APA102 LEDs on
  SPI, a button on GPIO17, and an install procedure that writes `dtoverlay=` into
  `/boot/firmware/config.txt` [B14][B15][B16][B22]. None of these boards has
  `config.txt` or the Pi firmware overlay loader, so any candidate needs a
  hand-written overlay — a Debra engineering task, and one that has **not been
  identified or attempted**, not a thing that "does not exist".
- **MCLK.** The v1 overlay models MCLK as a fixed 12.288 MHz clock rather than a
  SoC clock [B16, carried]. The Radxa boards expose an SoC MCLK at pin 13, which
  a Pi does not [C1 D][C2 D][C13 R]. Whether the HAT's codec needs an SoC MCLK,
  and whether that clock's parent can be set correctly, is `U` and could sink the
  ROCK 3C row.
- **HAT ID EEPROM.** No board in this screen has a Pi ID bus: 27/28 are `TWI2`
  on the Zero 2W [C4 D] and `I2C4` on both Radxa boards [C1 D][C2 D]. HAT
  auto-detection is absent; the EEPROM would sit unaddressed on an unrelated
  bus. This is a real design consequence, not a measurement.
- **Software (carried from R07, not re-checked).** LVA needs Python ≥3.11 and
  Sendspin ≥3.12 per their `pyproject.toml` files [B17][B18, carried]. Radxa's
  own images are Debian 12 bookworm and 5.10/6.1 kernels [B7][B8, carried]. The
  claim that a given Armbian image clears both floors is a **hypothesis**: the
  Armbian pages state distributions and kernel versions, not Python versions
  [C7 D][C8 D].
- **Native and USB audio — untested, not rejected.** The brief asks for
  board-native expansions and USB audio as well as HAT compatibility
  ([brief](../project-brief.md)). Documented native paths exist and were not
  evaluated: Zero 2W mini-HDMI plus 24-pin expansion audio out [C4 D]; Zero 3
  3.5 mm/AV via the 13-pin board, analog AV labelled Android-only, and the
  expansion mic explicitly unsupported [C5 D]; 3B 3.5 mm jack with input and
  output [C6 D]; Le Potato 3.5 mm jack and a separate SPDIF path [C9]. USB audio
  is a generic Linux path that no board in this screen was tested with, and the
  repo's ReSpeaker Lite rows are still `unreviewed` in
  [devices.md](../comparisons/devices.md). None of these is a substitute
  conclusion for the HAT question, and none has been screened.
- **Prices and availability are snapshots.** Only two figures survived checking:
  one EUR marketplace price for a named variant with "few left", and one USD
  page price with the variant unresolved and everything sold out. No complete
  purchase total exists for any board, and none can be derived without tax,
  shipping, a power supply, storage, a soldered header where applicable, and a
  comparable date.
- **Not screened at all** (named so nobody assumes rejection): Banana Pi
  M2/M4 Zero, MangoPi, Geniatech XPI-3566-ZERO, Radxa ZERO and ZERO 2 (a
  community report calls the latter poorly supported [B19 R]), Orange Pi 5
  family, BeagleBone, and every USB-audio path.
- **A community opinion, not evidence.** An LVA discussion participant calls the
  RK35xx boards "by some way the best non raspberry alternative" and suggests
  jumper wires for I2S/I2C [B19 R]. One person's report, no test record.

## Verification

- Procedure: read R07, the review's R07 findings, the brief and evidence rules;
  re-retrieved every board, pinout, price and seller page listed in `sources`;
  re-read each disputed sentence on the vendor page rather than relying on
  revision 1's paraphrase; removed every cross-currency, cross-date and
  cross-variant comparison. Public HTTP retrieval only; no login, no purchase.
- Observed results: **partial** — the six findings are corrected, and the
  underlying pin tables for five of six boards were read as text. The 3B table
  remains image-only and was not read. `python3 -B -m unittest tests.test_docs -v`
  is reported in the handoff below.
- Not tested: any board, HAT, overlay, image, kernel or device tree. No
  schematic PDF was opened. Raspberry Pi's own documentation returned 403 [C14].
- Authorization: none needed and none used. No commit, push, device contact or
  purchase was made by this revision.

## Handoff and correction links

- **Current state:** revision 2 of the R07 screen; `unreviewed`. It supersedes
  [revision 1](2026-11-15-alternative-board-screen.md) for the six reviewed
  findings only. Revision 1 is preserved unchanged, and the review note is
  untouched.
- **What survives as a candidate:** Radxa ROCK 3C (all four Pi signal positions
  documented) and Radxa ZERO 3W (I2S documented, control bus elsewhere), both
  **unproven**. Orange Pi 3B is undecided pending a readable pin table.
- **What was demoted, and why:** Orange Pi Zero 2W — from "not usable" to "not a
  HAT candidate **on current evidence**", because the vendor table documents no
  I2S function but no schematic was read. Le Potato — from "not usable on the
  vendor's own statements" to "not demonstrated either way", because the absence
  claim is a user's, not the vendor's. Orange Pi Zero 3 — unchanged in outcome
  but narrowed to a mechanical statement. ROCK 3C — from "closest on paper /
  only drop-in host" to "best documented starting point, unproven".
- **Next concrete action:** obtain and read the ROCK 3C V1.4 schematic and the
  RK3566 vendor kernel device tree for `i2s3_8ch` / `i2s3m0` pinctrl and a codec
  node. Desk work, no purchase, no device contact. The ZERO 3W schematic answers
  the 3/5 mux question at the same time.
- **Authorization needed:** buying, imaging, or connecting any board to the
  household Home Assistant / Music Assistant is out of scope for R07 and needs a
  separate named decision with recovery.
- **Earlier claim superseded:** the six findings above, plus the price
  comparison, the $15 launch figure, the "page contradicts itself" claim and the
  Le Potato vendor-attribution. All are corrected here, not edited in place.
- **Reviewed report/decision adopting this revision:** none known. A coordinator
  review is still required before any of this informs a shortlist or a purchase.
