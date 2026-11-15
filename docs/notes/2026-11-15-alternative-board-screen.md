---
title: Non-Raspberry-Pi board screen for a Debra host
date: 2026-11-15
type: project-learning
status: unreviewed
task: R07
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - "[B1] https://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/details/Orange-Pi-Zero-2W.html — checked 2026-11-15"
  - "[B2] http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_Zero_2W — checked 2026-11-15"
  - "[B3] http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_Zero_3 — checked 2026-11-15"
  - "[B4] http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_3B — checked 2026-11-15"
  - "[B5] https://docs.radxa.com/en/zero/zero3/hardware-design/hardware-interface — checked 2026-11-15"
  - "[B6] https://docs.radxa.com/en/rock3/rock3c/hardware-design/hardware-interface — checked 2026-11-15"
  - "[B7] https://docs.radxa.com/en/zero/zero3/download — checked 2026-11-15"
  - "[B8] https://docs.radxa.com/en/rock3/rock3c/download — checked 2026-11-15"
  - "[B9] https://hub.libre.computer/t/aml-s905x-cc-le-potato-overview-resources-and-guides/288 (JSON: .../288.json) — checked 2026-11-15"
  - "[B10] https://libre.computer/products/aml-s905x-cc-v2/ (search-result extract; page body is JS-rendered) — checked 2026-11-15"
  - "[B11] https://www.armbian.com/orange-pi-zero-2w/ — checked 2026-11-15"
  - "[B12] https://www.armbian.com/orange-pi-zero3/ — checked 2026-11-15"
  - "[B13] https://arace.tech/products/radxa-zero-3w — checked 2026-11-15"
  - "[B14] https://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT/ — checked 2026-11-15"
  - "[B15] https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/ — checked 2026-11-15"
  - "[B16] https://raw.githubusercontent.com/respeaker/seeed-voicecard/master/seeed-2mic-voicecard-overlay.dts — checked 2026-11-15"
  - "[B17] https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/main/pyproject.toml — checked 2026-11-15"
  - "[B18] https://raw.githubusercontent.com/Sendspin/sendspin-python-cli/main/pyproject.toml — checked 2026-11-15"
  - "[B19] https://github.com/OHF-Voice/linux-voice-assistant/discussions/99 — checked 2026-11-15"
  - "[B20] https://raspberry.tips/raspberrypi-infos/raspberry-pi-zero-2-w-alternative-ausverkauft (prices dated 2026-11-08 in page table) — checked 2026-11-15"
  - "[B21] https://botland.store/702-orange-pi — checked 2026-11-15"
  - "[B22] docs/comparisons/devices.md (Debra internal; Pi 5 + ReSpeaker 2-Mics v2 row, `[T]`) — checked 2026-11-15"
  - "[B23] https://radxa.com/products/rock3/3c/ — checked 2026-11-15"
supersedes: []
---

## Summary

Six exact board revisions were screened against the one question that decides
whether a ReSpeaker 2-Mics Pi HAT can work at all: **is I2S brought out on the
40-pin header, and is an I2C bus on pins 3/5?** Nothing here is a compatibility
claim; no board was bought, powered, or tested, and no device tree was read.

Three results matter:

1. **Orange Pi Zero 3 has no 40-pin header at all** — it has 26-pin + 13-pin
   headers [B3 D]. A HAT cannot be physically fitted. Excluded, not "unevaluated".
2. **I2S position is not portable.** The Radxa ZERO 3W and ROCK 3C put
   `I2S3_SCLK/LRCK/SDI/SDO` on header pins 12/35/38/40 — the same positions a Pi
   uses for `PCM_CLK/FS/DIN/DOUT` [B5 D][B6 D]. Orange Pi's H618 boards do not:
   the Zero 2W's 40-pin table lists no PCM/I2S function on any pin [B2 D], and
   the vendor's own summary of that header is "GPIO、UART、I2C、SPI、PWM" [B1 D].
3. **Two boards with the same RK3566 differ at pins 3/5.** On the ROCK 3C they
   are `I2C3_SDA/SCL` [B6 D]; on the ZERO 3W they are `UART3_RX/TX` and the I2C
   buses are elsewhere [B5 D]. That single difference decides whether a HAT's
   codec is addressable without rewiring.

The strongest candidate on paper is the **Radxa ROCK 3C**, because it is the only
board in this screen that has I2S *and* I2C where a Pi HAT expects them. It is
still **not evaluated**: nobody has written or tested an overlay for it, and the
HAT's own supported install path is a Raspberry Pi firmware `dtoverlay=` line
[B15 D] that does not exist on any of these boards.

Nothing in this note changes [the master device table](../comparisons/devices.md);
that table's only `[T]` row remains the lab Pi 5 + 2-Mics HAT [B22 T].

## Evidence labels

`D` upstream-documented · `R` reported · `H` hypothesis · `U` unknown (an empty
cell is never "no"). Same convention as
[comparisons/README.md](../comparisons/README.md). All sources checked
**2026-11-15** unless the cell says otherwise.

## What the HAT actually needs

Before the boards, the requirement — otherwise "40 pins" looks sufficient.

| Requirement | Detail | Label |
| --- | --- | --- |
| I2S data path | v2.0 driver is `respeaker-2mic-v2_0-overlay.dtbo` from Seeed's dtoverlays repo; the resulting card is `tlv320aic3x-hifi` on `1f000a4000.i2s` — i.e. it binds the SoC's I2S controller, not a USB or on-board codec | [B15 D] |
| I2C codec control | v1 driver overlay enables `&i2c1` with `wm8960` at `0x1a` [B16 D]; Debra's own v2.0 unit is a TLV320AIC3104 at `0x18` on I2C-1 [B22 T] | D/T |
| SPI | three APA102 LEDs on the SPI interface [B14 D] | D |
| GPIO17 | user button [B14 D] | D |
| Extra 5 V | the HAT has its own micro-USB power input, "please power the board for providing enough current when using the speaker" [B14 D] | D |
| Install mechanism | vendor procedure writes `dtoverlay=respeaker-2mic-v2_0` into `/boot/firmware/config.txt` [B15 D] | D |

Consequence: a board needs **I2S + an I2C bus** on the HAT's pin positions. A
board that has neither, or has one of them, is not a candidate — it is a
different product with a jumper harness, which is a different engineering task.

## Table 1 — header and audio path

| Board (exact revision) | SoC / RAM | 40-pin header | I2S on header | I2C on pins 3/5 | Other audio on board | HAT verdict |
| --- | --- | --- | --- | --- | --- | --- |
| **Orange Pi Zero 2W V1.1** | Allwinner H618, 4×A53 1.5 GHz; 1/1.5/2/4 GB LPDDR4 [B1 D][B2 D] | **Yes**, 28 GPIO, 3.3 V; **header pins not soldered by default** [B2 D] | **None documented.** Full 40-pin table lists TWI1/TWI2/TWI0, SPI1, UART0/2/4/5, PWM1-4; pins 12, 18, 29, 31, 35, 36, 37, 38, 40 have no alternate function listed [B2 D]. Vendor summary: "GPIO、UART、I2C、SPI、PWM" [B1 D] | **Yes**, `TWI1-SDA`/`TWI1-SCL` (PI8/PI7) [B2 D] | mini-HDMI audio only; analog out and mic via the 24-pin expansion board [B1 D] | **Not usable as a HAT.** Codec is addressable, audio data path is absent. `U` whether H618 I2S exists on any header pin under an overlay — no schematic was read |
| **Orange Pi Zero 3** | H618, 1/1.5/2/4 GB [B3 D] | **No.** 26-pin (17 GPIO) + 13-pin headers [B3 D] | n/a — no 40-pin header | n/a (26-pin pin 3 is `TWI3-SDA`) [B3 D] | 3.5 mm + AV via 13-pin board; the 13-pin board's **mic is explicitly unsupported** on this board [B3 D] | **Excluded — mechanical.** A 40-pin HAT cannot be fitted |
| **Orange Pi 3B** | Rockchip RK3566, 4×A55 1.8 GHz; 2/4/8 GB [B4 D] | **Yes**, 28 GPIO, 3.3 V [B4 D] | **`U` — not documented.** Vendor lists the header as "GPIO, UART, I2C, SPI, PWM" [B4 D]; the full pin table is published **only as PNG images**, so it could not be read as text [B4] | `U` — table is image-only [B4] | 3.5 mm jack with audio **input and output** [B4 D] | **Not evaluated.** The one Orange Pi with a 40-pin header worth pursuing, but the decisive pin data is a picture |
| **Radxa ZERO 3W** (V1.11 production; V1.12 = AIC8800 Wi-Fi variant) | RK3566; 1/2/4/8 GB LPDDR4; Wi-Fi5 or Wi-Fi6 SKUs [B7 D] | **Yes**, 40-pin; sold as *without* header or *soldered header* SKU [B13 R] | **Yes** — pin 12 `I2S3_SCLK_M0`, 35 `I2S3_LRCK_M0`, 38 `I2S3_SDI_M0`, 40 `I2S3_SDO_M0`; pin 13 `I2S3_MCLK_M0` [B5 D] | **No.** Pins 3/5 are `UART3_RX_M0`/`UART3_TX_M0` (GPIO1_A0/A1); I2C4 is on 27/28, I2C5 on 29/31 [B5 D] | none documented (HDMI only) | **Not usable as a HAT.** I2S present, codec bus absent — a HAT would need its I2C rewired to 27/28 |
| **Radxa ROCK 3C** (V1.3 / V1.4) | RK3566, 1/2/4 GB [B23 D] | **Yes**, 40-pin [B6 D] | **Yes** — 12 `I2S3_SCLK_M0`, 35 `I2S3_LRCK_M0`, 38 `I2S3_SDI_M0`, 40 `I2S3_SDO_M0`; 13 `I2S3_MCLK_M0` [B6 D] | **Yes** — `I2C3_SDA_M0` / `I2C3_SCL_M0` (GPIO1_A0/A1) [B6 D] | none documented | **Closest on paper; not evaluated.** I2S and I2C both land where the HAT expects them, but no overlay exists and none was tested |
| **Libre Computer Le Potato AML-S905X-CC** (S905X) | Amlogic S905X; RAM `U` (not read) | **Yes**, vendor calls it "40-pin Pi-compatible" [B10 R] | **No.** Vendor index lists "I2S — please request if needed"; a user confirms "I need I2S working though the signals are not in the 40-pin header"; vendor's reply is to select I2S in `alsamixer`, i.e. a different connector [B9 R] | `U` (Pi-compatible header claimed, not verified pin by pin) | 3.5 mm jack, HDMI, SPDIF on a separate header [B9 R][B10 R] | **Not usable as a HAT** on the vendor's own statements. The V2 "Sweet Potato" adds a dedicated **8-pin SARADC/I2S header** [B10 R] — a different wiring job |

## Table 2 — software, power, price, maintenance

| Board | Maintained OS images / kernel | Python floor for LVA ≥3.11 [B17 D] and Sendspin ≥3.12 [B18 D] | Power input | Price, market, date | Maintenance evidence |
| --- | --- | --- | --- | --- | --- |
| Orange Pi Zero 2W | Vendor Debian 11/12, Ubuntu 20.04/22.04, Orange Pi OS (Arch); example image `…linux6.1.31` [B2 D]. **Armbian: "Community" tier, kernel `current 6.18.63`, build date 2026-11-13** [B11 D] | Armbian trixie/resolute images clear both floors [B11 D]; the vendor's Ubuntu 20.04/22.04 images ship Python older than 3.12 `H` | USB-C 5 V/2 A or 5 V/3 A; either of the two Type-C ports can power it [B1 D][B2 D]. Vendor: most "unstable" start-up behaviour is a power-supply problem [B2 D]. Header 5 V current budget `U`; undervoltage telemetry `U` | `U` — vendor page lists purchase links, no price [B1]. Third-party comparison quotes **from €53 for 1 GB** (Amazon.de, table dated 2026-11-08) [B20 R]; launch coverage in 2023 quoted $15 [B20 R] — treat both as market snapshots, not measurements | Armbian CSC maintained by one community member (`chraac`) [B11 D]; vendor wiki actively maintained; vendor forum/Telegram/Discord [B1 D]. **EU distributor Botland has withdrawn Orange Pi entirely, citing the manufacturer's certification** [B21 R] |
| Orange Pi Zero 3 | Vendor images as above, `linux6.1.31` [B3 D]; Armbian "Community", 6.18.63, 2026-11-13 [B12 D] | as above | USB-C 5 V/2 A–3 A; "do not exceed 5 V" [B3 D] | `U` | as above; same Botland withdrawal [B21 R] |
| Orange Pi 3B | Vendor Ubuntu 20.04/22.04, Debian 11/12; example image `Linux5.10.160` [B4 D]. Armbian lists a board page [B11] — tier not read `U` | vendor images older than 3.12 `H` | USB-C 5 V/3 A [B4 D] | `U` | vendor wiki; Botland withdrawal [B21 R] |
| Radxa ZERO 3W | Official Radxa OS: **6.1 kernel (bookworm KDE)** and **5.10 kernel (bullseye XFCE)** [B7 D]; third-party Armbian and DietPi linked from Radxa's own page [B7 D] | Debian 12 bookworm ships Python 3.11, which satisfies LVA but **not Sendspin's ≥3.12** `H` — needs a newer distro or a hand-built Python | USB-C 1, **5 V only**, 5 V/2 A+ recommended [B5 D] | **$20.00 USD**, Arace Tech (HK), **all variants sold out** on 2026-11-15 [B13 R] | Radxa docs current; **vendor's own page contradicts itself** on pins 3/5 (see Traps) [B5 D]; community reports heat without a fan [B13 R] |
| Radxa ROCK 3C | Official Radxa OS: **6.1 (bookworm)** and **5.10 (bullseye)** [B8 D]; OpenWrt third-party [B8 D] | same Debian 12 vs Sendspin ≥3.12 gap `H` | `U` — power page not read | `U` — Radxa sells through "Approved Partners" and publishes no price [B23 D] | Radxa docs, forum, GitHub org [B23 D]; V1.4 current revision with published schematic [B6 D] |
| Le Potato AML-S905X-CC | Libre Computer's own images; a Libre repo **kernel 6.18.68** is discussed in their forum (topic created 2026-02-08) [B9 R] | `U` — distro Python not checked | `U` — vendor asks for >5.0 V and <5.5 V supply [B9 R] | `U` — product pages are JS-rendered and no seller page was readable this session [B10] | Active vendor-run forum with staff replies [B9 R]; overlay tooling (`ldto`) is tied to Libre's own image — a user reports it does not work on a third-party distro [B9 R] |

## Decisive unknown per board

One piece of missing evidence each. Filling these is the whole of R07's remaining
research; none of them is a purchasing decision.

| Board | The single missing piece | Why it decides the row |
| --- | --- | --- |
| **Radxa ROCK 3C** | A device-tree overlay (or a vendor statement) showing `i2s3_8ch` + a codec on I2C3 working **simultaneously** on the 40-pin, with the HAT's MCLK arrangement | I2S and I2C positions already match. If the mux/clocking works, this is the only board here that is a drop-in HAT host; if `I2S3_MCLK_M0` on pin 13 collides with something, the HAT still needs wiring changes |
| **Radxa ZERO 3W** | Whether the HAT's codec can be reached when its I2C is moved to pins 27/28 (`I2C4`) — i.e. a working overlay plus a documented re-pin | I2S is on the right pins; only the control bus is wrong. That is a two-wire re-pin, or a hard no, depending on whether anyone has done it |
| **Orange Pi 3B** | The 40-pin pin table as text, or the schematic, showing whether `I2S3`/`PCM` reaches pins 12/35/38/40 | The vendor publishes this only as PNGs [B4]. Without it the board is `U`, not "probably fine" |
| Orange Pi Zero 2W | The Zero 2W schematic: are H618 I2S nets routed to any header pin, and does the vendor kernel expose them? | The vendor table lists no PCM function anywhere [B2 D]; a schematic either confirms that or shows a hidden capability |
| Orange Pi Zero 3 | none — excluded on documented header count (26-pin, not 40) [B3 D] | No research can make a 26-pin header accept a 40-pin HAT |
| Le Potato | Whether the V2's 8-pin I2S header has a maintained overlay for a WM8960/TLV320 codec, and whether the HAT can be jumpered to it | The vendor already says I2S is not in the 40-pin [B9 R]; the question is whether the separate header is a supported audio path or an unexercised pinmux |

## Traps

1. **A brand is not a platform, and an SoC is not a board.** Orange Pi Zero 2W
   and Zero 3 share the H618 and are mechanically incompatible (40-pin vs
   26-pin) [B2 D][B3 D]. Radxa ZERO 3W and ROCK 3C share the RK3566 and differ at
   pins 3/5 — I2C on one, UART on the other [B5 D][B6 D]. Any table that lists
   "RK3566 board" or "Orange Pi" as a row is wrong by construction.
2. **Same pin position, different signal.** Pins 12/35/38/40 carry
   `PCM_CLK/FS/DIN/DOUT` on a Pi and `I2S3_SCLK/LRCK/SDI/SDO` on RK3566
   [B5 D][B6 D]. Positional agreement does not imply the same controller,
   master/slave default, or clock parent. It is a hypothesis until an overlay
   plays audio.
3. **No Pi ID EEPROM bus anywhere in this screen.** A Pi HAT's ID EEPROM sits on
   the Pi's dedicated ID bus (header pins 27/28). On the Zero 2W those pins are
   `TWI2` [B2 D]; on both Radxa boards they are `I2C4` [B5 D][B6 D]. The EEPROM
   will not be probed and becomes an extra unaddressed device on an unrelated
   bus. HAT auto-detection is simply absent.
4. **The HAT's supported install path is Raspberry Pi firmware.** Seeed's
   procedure writes `dtoverlay=` into `/boot/firmware/config.txt` [B15 D]. None
   of these boards has `config.txt`, `raspi-config`, or the Pi firmware overlay
   loader. Every candidate needs a hand-written `simple-audio-card` overlay — a
   Debra engineering task, not a configuration step.
5. **"40-pin header" hides a soldering decision.** Zero 2W header pins are
   unsoldered by default [B2 D]; the ZERO 3W is sold at extra cost with or
   without a soldered header [B13 R]. A price comparison that ignores this is
   comparing different products.
6. **Vendor "compatible" wording is not a pinout guarantee.** Radxa: "compatible
   with most SBC accessories … actual compatibility is subject to usage"
   [B5 D][B6 D]. Libre Computer calls its header "40-pin Pi-compatible" while
   its own forum says I2S is not in that header [B10 R][B9 R].
7. **The Radxa ZERO 3W page contradicts itself.** The text says pins 3, 5, 27,
   28 "add extra pull-up resistors for I2C device power supply", while the pin
   table assigns pins 3/5 to `UART3` [B5 D]. One of the two is wrong; do not
   design against either without a schematic.
8. **The Python floor, not the SoC, blocks the software.** LVA needs ≥3.11
   [B17 D]; Sendspin needs **≥3.12** [B18 D]. Both Radxa official images are
   Debian 12 bookworm (Python 3.11) [B7 D][B8 D]. So the vendor's *best*
   supported image still cannot `pip install` Sendspin unmodified. Armbian's
   trixie/resolute images clear both [B11 D].
9. **Documentation absence is a finding.** Orange Pi publishes the 3B's pin
   table only as images [B4]; Libre Computer's product pages render only with
   JavaScript, and their forum is the machine-readable copy [B9][B10]. A board
   whose pinout cannot be read cannot be assessed — it does not become
   "probably compatible".
10. **Availability and certification are part of the screen.** Botland, an EU
    distributor, has withdrawn Orange Pi boards citing the manufacturer's
    certification [B21 R]; the only priced Radxa board in this screen was sold
    out in every variant on the date checked [B13 R].
11. **Onboarding, identity and recovery fragment.** Each vendor brings its own
    update and overlay mechanism — `rsetup` on Radxa [B7], `orangepi-build` on
    Orange Pi [B2], `ldto` on Libre's images only [B9 R]. Debra's "assembled,
    prepared board + SSH TUI" premise currently leans on Pi conventions
    (`/boot/firmware`, `config.txt`, first-boot Wi-Fi). Any non-Pi port re-opens
    that design, which is a product decision, not a research gap.

## Not verified / open questions

- **Nothing was tested.** No board was purchased, powered, imaged or measured.
  Every row is documentation.
- **No device tree was read for any board.** "Driver support" is therefore `U`
  everywhere: I have kernel *versions* [B7 D][B8 D][B11 D], not evidence that
  `i2s3_8ch`, the pinctrl groups, or a TLV320AIC3x/WM8960 codec node exist in
  those kernels for these boards.
- **LVA dependency wheels on aarch64 are unchecked.** LVA pins `pymicro-wakeword`,
  `pyopen-wakeword`, `webrtc-noise-gain`, `soundcard` and `python-mpv` [B17 D].
  Whether each publishes an aarch64 wheel (or needs a compiler plus `libmpv`) is
  the practical LVA blocker on *any* non-Pi board, and it is independent of I2S.
  This should be checked before any board is bought.
- **PipeWire + a codec HAT on RK3566 is unwritten.** A `simple-audio-card`
  overlay binding `i2s3_8ch` to the HAT codec, with the right bit/frame clock
  master, has not been authored or tested. Debra's lab Pi used an overlay it had
  to build and pin [B22 T]; the same work is larger here.
- **The HAT's MCLK arrangement is unclear.** The v1 overlay models MCLK as a
  fixed 12.288 MHz clock rather than a SoC-provided clock [B16 D]; how that maps
  onto `I2S3_MCLK_M0` on pin 13 of the Radxa boards is unknown and could sink
  the ROCK 3C row.
- **Prices are the weakest column.** Only one figure came from a seller page that
  could be read (Arace Tech, $20, sold out) [B13 R]; the Orange Pi figures are
  third-party snapshots with a 3× spread [B20 R]. Currency, tax, shipping and
  the soldered-header option are not reconciled, so no complete-purchase total
  exists — see the cost rules in [evidence.md](../evidence.md).
- **Not screened at all** (named so nobody assumes rejection): Banana Pi
  M2/M4 Zero, MangoPi, Geniatech XPI-3566-ZERO, Radxa ZERO/Zero 2 (which a
  community report calls poorly supported [B19 R]), Orange Pi 5 family,
  BeagleBone. Also unscreened: whether the **USB** ReSpeaker Lite sidesteps the
  whole header problem — attractive, but the repo's own ReSpeaker Lite rows are
  still `unreviewed` in [devices.md](../comparisons/devices.md).
- **A community opinion, not evidence:** an LVA discussion participant argues
  the RK35xx boards are "by some way the best non raspberry alternative" for
  support, compute and cost, and that Orange Pi's H616 boards have "almost as
  good mainline support" [B19 R]. Same thread: "you can use jumper wires …
  as I2s and i2c is not that many jumpers to correct the header layout of the
  RK35xx" [B19 R] — consistent with Table 1, but it is one person's report, not
  a test record.

## Handoff and correction links

- **Shortlist for a future build decision:** Radxa ROCK 3C (electrically
  closest), Radxa ZERO 3W (cheapest, I2S present, control bus mismatched),
  Orange Pi 3B (unresolved pinout). Zero 3 is excluded mechanically; Zero 2W and
  Le Potato cannot carry this HAT as a HAT.
- **Next concrete action:** read the ROCK 3C v1.4 schematic and the RK3566
  vendor kernel device tree for `i2s3_8ch` / `i2s3m0` pinctrl and codec nodes.
  That is desk work with no purchase and no device contact.
- **Authorization needed:** buying any board, imaging it, or connecting it to the
  household Home Assistant / Music Assistant is out of scope for R07 and needs a
  separate named decision with recovery. Physical validation and a maintained
  Debra port are separate selections.
- **Earlier claim superseded:** none. This note adds rows; it does not correct
  [devices.md](../comparisons/devices.md), which should only be updated from a
  reviewed finding, per that page's own instructions.
