---
title: Three microphone paths for a Pi Zero satellite — what 32-bit Raspberry Pi OS actually supports
date: 2026-11-15
type: project-learning
status: unreviewed
task: none — unattended research run, 2026-11-15 (no device access, no installs)
author: OpenCode agent
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - Raspberry Pi documentation, building the Linux kernel (32-bit defconfig map) — https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/linux_kernel/building.adoc
  - raspberrypi/linux rpi-6.12.y, arch/arm/configs/bcmrpi_defconfig and bcm2709_defconfig
  - raspberrypi/linux rpi-6.12.y, arch/arm/boot/dts/overlays/README and the overlay sources named below
  - raspberrypi/linux rpi-6.12.y, sound/soc/bcm and sound/soc/codecs sources named below
  - Linux kernel Documentation/sound/alsa-configuration.rst (snd-usb-audio)
  - PipeWire documentation, objects design and pipewire-props(7)
  - alsa-ucm-conf repository tree (ucm2/USB-Audio)
  - Seeed Studio wiki pages for ReSpeaker 2-Mics Pi HAT v1 and v2, and the v2.0 schematic PDF
  - Wolfson/Cirrus WM8960 datasheet; TI TLV320AIC3104 and TPA2005D1 datasheets; TDK INMP441 and ICS-43434 datasheets
  - Adafruit I2S MEMS microphone learn guide; Waveshare WM8960 Audio HAT README
  - respeaker/seeed-voicecard repository (dkms.conf, Makefile, v1 overlay)
  - Repository: docs/notes/2026-11-15-armv6-audio-stack.md and docs/notes/2026-11-15-respeaker-trixie-driver.md
supersedes: []
---

# Three microphone paths for a Pi Zero satellite

**Desk research from public sources only, 2026-11-15. No Pi Zero was contacted,
nothing was installed, no kernel was built, and no audio was recorded.** Every
claim carries one label and a key from the register at the end.

Labels: **D** upstream-documented (the cited primary source states it; for kernel
files, the source states it and the file was read at the stated revision);
**R** reported (vendor page, vendor README, third-party guide — attributed, not
verified here); **H** hypothesis (my inference from the cited sources, not stated
by any of them); **U** unknown. **T** (tested) is unused: this run touched no
hardware.

---

## Summary

The three paths differ far less at the ALSA/PipeWire layer than at the layer
below it. PipeWire sees an ALSA card with PCM streams in every case; what
changes is **which kernel symbol must exist**, **who supplies the device-tree
overlay**, and **whether an amplifier is on the board**.

- **A — I2S HAT with an onboard ADC.** A WM8960-based HAT is fully in-tree on
  32-bit Raspberry Pi OS: codec `=m` in both 32-bit kernel configs and an
  in-tree overlay that describes exactly that board. A TLV320AIC3104-based HAT
  (ReSpeaker 2-Mics **v2**) is not: the codec's I²C glue is absent from both
  32-bit configs, and Seeed's own instructions for a Pi Zero W build that module
  by hand.
- **B — USB microphone.** In-tree, no overlay, no vendor patch for a
  class-compliant device — but it consumes the Zero's only data port, and the
  board's USB current budget is not separately documented.
- **C — I2S microphone module wired to the board.** The codec driver is present,
  but no stock overlay binds a bare microphone; the one upstream example
  (`googlevoicehat-soundcard`) is fixed at 48 kHz, 2 channels, S32_LE.
- **Amplifier:** separate in B and C always, and in the v2 HAT; only the WM8960
  HAT integrates it (1 W/channel class-D).
- **Nothing below is a runtime result.** The gaps are listed in §7.

---

## 1. What "32-bit Raspberry Pi OS" means for this question

Raspberry Pi's own documentation maps the boards to two different 32-bit kernels
`D` [S1]:

| Board family | Kernel image | Config |
| --- | --- | --- |
| Pi 1, CM1, **Zero, Zero W** | `kernel.img` | `bcmrpi_defconfig` (ARMv6) |
| Pi 2, 3, 3+, CM3, **Zero 2 W** | `kernel7.img` | `bcm2709_defconfig` (ARMv7) |

I read both configs at `rpi-6.12.y` `D` [S2][S3]. The audio-relevant symbols are
identical in both:

| Symbol | `bcmrpi` (Zero W) | `bcm2709` (Zero 2 W, 32-bit) |
| --- | --- | --- |
| `CONFIG_SND_BCM2835_SOC_I2S` | `=m` | `=m` |
| `CONFIG_SND_SIMPLE_CARD` | `=m` | `=m` |
| `CONFIG_SND_USB_AUDIO` | `=m` | `=m` |
| `CONFIG_SND_SOC_WM8960` | `=m` | `=m` |
| `CONFIG_SND_SOC_ICS43432` | `=m` | `=m` |
| `CONFIG_SND_SOC_MAX98357A` | `=m` | `=m` |
| `CONFIG_SND_SOC_ADAU7002` | `=m` | `=m` |
| `CONFIG_SND_BCM2708_SOC_GOOGLEVOICEHAT_SOUNDCARD` | `=m` | `=m` |
| `CONFIG_SND_SOC_TLV320AIC3X` / `..._I2C` | **absent** | **absent** |
| `CONFIG_SND_SOC_DMIC` | **absent** | **absent** |

**Limit on that table:** a defconfig says what that kernel build enables. It does
not prove what a downloaded image contains; the image's module set was not
inspected (`U`).

Two supporting hardware facts, both `D` from the same tree: the BCM2835 I²S block
is declared with both TX and RX DMA [S11], and the Zero's device tree puts I²S on
GPIO 18–21, ALT0 [S13]. The overlays that matter target the downstream labels
`&sound`, `&i2s_clk_producer` and `&i2s_clk_consumer`, which the ARMv6 board tree
defines — and `i2s_clk_producer`/`i2s_clk_consumer` are two labels on the *same*
`i2s` node, not two controllers [S12].

---

## 2. Path A — I2S HAT with an onboard ADC

Two codecs are in scope because the project's HAT changed under the same name.
The v2.0 schematic revision history says the WM8960 became EOL and was replaced
by the TLV320AIC3104 `D` [S23].

### A1. WM8960 HAT (ReSpeaker 2-Mics v1; Waveshare WM8960 Audio HAT)

**Driver support.** `wm8960.c` has been in mainline since Linux 2.6.31
(`f2644a2c00a0`, 2009-04-07) `D` [S34]. `CONFIG_SND_SOC_WM8960=m` in both 32-bit
configs `D` [S2][S3].

**Overlay.** The Raspberry Pi kernel ships `wm8960-soundcard`, documented as
"Overlay for the Waveshare wm8960 soundcard" `D` [S4]. It puts a `wlf,wm8960` at
I²C 0x1a with a 12.288 MHz fixed MCLK, builds a `simple-audio-card` on
`&i2s_clk_producer` named `wm8960-soundcard`, routes LINPUT1/3 and RINPUT1/2 to
"Mic Jack", SPK_LP/SPK_LN to "Speaker", and exposes an `alsaname` parameter to
rename the card `D` [S5]. Because both the codec driver and the overlay are
in-tree, binding a WM8960 needs no vendor artefact; whether this overlay suits a
Seeed v1 board specifically is a separate question (§7).

**Are vendor kernel patches needed?** No `D` for the in-tree path. The vendor
alternative is a DKMS package: `seeed-voicecard` 0.3, `AUTOINSTALL="yes"`, which
builds `snd-soc-wm8960`, `snd-soc-ac108` and `snd-soc-seeed-voicecard`, with
back-port patches matched only to kernels 4.19, 5.4 and 5.8 `D` [S31]. Its codec
module uses the in-tree module name `snd-soc-wm8960.ko` (the kernel builds
`snd-soc-wm8960.o`), so a successful build replaces the maintained driver rather
than sitting beside it `D` [S31][S36].

Waveshare's README still states that "the upstream wm8960 codec is not currently
supported by current Pi kernel builds" and that its script must build the driver
manually `R` [S30]. That is contradicted by the `=m` symbol and by the in-tree
overlay above `D`; treat the README as stale rather than as evidence of a missing
driver.

**How it appears.** Card name `wm8960-soundcard` (or whatever `alsaname` says).
Waveshare's own `aplay -l` / `arecord -l` output shows one playback and one
capture PCM, `Subdevices: 1/1` `R` [S30]. PipeWire maps an ALSA card to a device
and each PCM stream to a node `D` [S18]; a filename search of `alsa-ucm-conf`
found no profile naming this card, so the session manager's ACP profiles are the
fallback `D` [S19][S20] — the consequence for the resulting profile list is `H`.

**Power.** From the WM8960 datasheet's typical-power tables `D` [S24]: record
mode, stereo input to ADC at 48 kHz, no signal, is 25.6 mW on 1.8/3.0/3.0/3.0 V
rails and 57.4 mW on 3.6/3.6/5.5/3.6 V; playback to 8 Ω speakers with no signal
is 27.5–69.5 mW on the same rail sets; a 1 kHz 0 dBFS signal into 8 Ω reaches
1.09 W with the speaker supply at 3.3 V and 2.87 W at 5.5 V, with power in the
load included. The HAT's total draw (codec plus regulators, LEDs, jack detect) is
not published in any source found — `U`.

**Amplifier separate?** **No.** The WM8960 integrates stereo class-D speaker
drivers, "1 W per channel into 8 Ω loads with a 5 V supply", and the datasheet
says "no separate microphone, speaker or headphone amplifiers are required"
`D` [S24]. Seeed's v1 wiki describes the board as WM8960-based with a 3.5 mm jack
and a JST 2.0 speaker out, max 48 kHz `R` [S21].

### A2. TLV320AIC3104 HAT (ReSpeaker 2-Mics v2, 2024)

**Driver support.** The codec driver is mainline since 2.6.25 (`44d0a879951a`,
2007-11-14) `D` [S34] — but neither 32-bit config enables
`SND_SOC_TLV320AIC3X_I2C`, the glue that actually binds an I²C codec `D`
[S2][S3]. So on stock 32-bit Raspberry Pi OS the card cannot appear from in-tree
code.

**Are vendor kernel patches needed?** Not patches — a locally built module.
Seeed's v2 page has a "Prepare for Raspberry Pi Zero W" section: install
`linux-headers-6.6.51+rpt-rpi-v6` (the ARMv6 header package), copy
`tlv320aic3x.c`, `tlv320aic3x.h` and `tlv320aic3x-i2c.c` out of a shallow clone
of `rpi-6.6.y`, build with a two-line Makefile, `make install` into
`/lib/modules/$(uname -r)`, `modprobe snd-soc-tlv320aic3x-i2c`; then build and
install `respeaker-2mic-v2_0.dtbo` and add `dtoverlay=respeaker-2mic-v2_0` `D`
(vendor instructions) [S22]. A module copied into a kernel-version directory
stops matching after a kernel upgrade; that failure mode is mechanically implied
`H` (the vendor page does not discuss upgrades).

The same page states that "if your kernel version is greater than 4.0, you don't
need to add `dtoverlay=i2s-mmap`" `R` [S22].

**How it appears.** Card `seeed2micvoicec`, one playback and one capture PCM,
`Subdevices: 1/1`, addressed by name because "this number may differ" between
systems `R` [S22]. Same PipeWire mapping as A1 `D` [S18]; no UCM profile for the
name `H`.

**Power.** The codec's own figure is 14 mW for stereo 48 kHz playback from a
3.3 V analogue supply `D` [S25]. The board adds a class-D amplifier (below). No
board-level total is published — `U`.

**Amplifier separate?** **Yes.** The v2.0 schematic carries a `TPA2005D1DGNR`
mono class-D amplifier with `AMP_CTL` and `SPK+`/`SPK−` `D` [S23]. The codec
itself has only headphone and line drivers; TI's device-comparison table says the
TLV320AIC3101 is "same as TLV320AIC3104, but with speaker and HP amplifier" and
the AIC3107 is the one with an "integrated mono class-D amplifier" `D` [S25].
The TPA2005D1 is 1.4 W into 8 Ω from 5 V, 2.8 mA quiescent, 0.5 µA shutdown `D`
[S26].

### A3. Multi-microphone HATs

Array HATs built on AC108/AC101 rely on the vendor package's `snd-soc-ac108`
module `D` [S31]; that driver is not in either 32-bit config `D` [S2][S3]. They
are out of scope for the three paths compared here, but they inherit the same
"module rebuilt per kernel" risk.

---

## 3. Path B — USB microphone

**Driver support.** `CONFIG_SND_USB_AUDIO=m` in both 32-bit configs `D`
[S2][S3]; the Kconfig entry is "USB Audio/MIDI driver" and produces
`snd-usb-audio` `D` [S17]. The kernel's ALSA configuration document lists its
module parameters, including `autoclock` ("auto-clock selection for UAC2
devices") and `quirk_flags` for device-specific workarounds `D` [S16].

**Are vendor kernel patches needed?** For a class-compliant device, no: the
generic driver binds it. For a particular product, whether it needs a quirk is
device-specific — `U` for any unnamed microphone, `H` for "most are fine".

**One ARM-specific trap, documented upstream.** The same kernel document warns
that for "architectures with non-coherent memory like ARM or MIPS, the mmap
access may give inconsistent results with vmalloc'ed buffers", and that
`use_vmalloc` can be turned off so DMA-coherent buffers are used `D` [S16]. A
Zero is such an architecture.

**How it appears.** As its own ALSA card, named from the USB device descriptor;
the card index depends on probe order, which the vendor pages themselves
acknowledge by telling users the number may differ `R` [S22]. PipeWire maps it to
a device with a capture node `D` [S18]. `alsa-ucm-conf` ships a per-device
USB-Audio profile tree under `ucm2/USB-Audio` (vendor directories such as RODE,
HyperX and Focusrite, plus a generic `USB-Audio.conf`) `D` [S20]; PipeWire uses
the UCM configuration "when one is available for a device" and otherwise falls
back to ACP profiles `D` [S19].
Whether a specific microphone has a profile is `U` until its USB ID is looked up.

**Power.** Bus-powered from the board's 5 V. Raspberry Pi's official table gives
the Zero W a 1.2 A recommended supply with 150 mA typical bare-board active
current, the Zero 2 W 2 A and 350 mA, and — unlike the Model B boards — states
that maximum total USB peripheral current is "limited by PSU, board, and
connector ratings only" `D` [S14]. There is therefore no documented per-port
number to budget against, and the microphone's own draw is device-specific — `U`.

**Ports.** The Zero W and Zero 2 W each have exactly two micro-USB ports: one for
input power and one OTG port "compatible with OTG adapters to connect keyboards,
mice, USB hubs, and other external devices" `D` [S15]. A USB microphone occupies
the only data port; anything else (including USB-gadget networking) then needs a
hub `H` (the port count is `D`; the hub consequence is arithmetic).

**Amplifier separate?** **Yes, always.** A USB microphone has no output stage; a
speaker needs its own amplifier and its own audio path.

---

## 4. Path C — I2S microphone module wired to the board

**Driver support.** `CONFIG_SND_SOC_ICS43432=m` in both 32-bit configs `D`
[S2][S3]. The driver describes itself as the "I2S MEMS microphone driver for
InvenSense ICS-43432 and similar MEMS-based microphones", non-configurable,
capture-only, 1–2 channels, `S24_LE`/`S32`, "64 BCLs per frame, 32 bits per
channel, 24 bit data", 7,190–52,800 Hz `D` [S10].

**Overlay.** There is no stock overlay for a bare microphone on a bare board.
The nearest upstream artefact is `googlevoicehat-soundcard`, documented as
"Configures the Google voiceHAT soundcard" `D` [S4]: it enables
`&i2s_clk_producer`, declares a `google,voicehat` codec node with an `sdmode`
GPIO, and binds a machine driver whose card name is
`snd_rpi_googlevoicehat_soundcard` `D` [S7][S8]. That machine driver is enabled
in both 32-bit configs `D` [S2][S3].

Adafruit's guide for its I2S MEMS microphone breakout tells users to add
`dtoverlay=googlevoicehat-soundcard` to `config.txt`, reboot, then record with
`arecord -D plughw:1 -c1 -r 48000 -f S32_LE -t wav -V mono -v file.wav` `R` [S29].
That is the only public, vendor-published recipe found for a bare I2S microphone
on Raspberry Pi OS, and it uses no out-of-tree code.

**The catch with that recipe.** The codec's DAI is fixed: 2 channels, 48 kHz
only, `S32_LE`, for both capture and playback `D` [S9]. A 16 kHz wake-word
pipeline therefore depends on resampling, which on one 1 GHz ARM11 core is a real
cost `H` (the repository's ARMv6 audio note already flags resampling cost as
unmeasured `R` [S33]).

**The alternative** is an overlay Debra writes itself: `simple-audio-card` plus
an `ics43432` codec node, in the shape of the in-tree `max98357a` overlay `D`
[S6]. That the pieces exist is `D`; that such an overlay produces a working
capture card on a Zero is `U` — nobody in the sources read has published it.

**Wiring.** I²S is on GPIO 18–21 in the Zero device tree `D` [S13]. The
microphone is a clock slave and needs 64 SCK per frame, which the codec driver
also states `D` [S10].

**Power.** INMP441: 1.4 mA at 1.8 V and 2.2 mA at 3.3 V, 24-bit I²S, 64 SCK per
WS frame, WS 7.8–50 kHz, package 4.72 × 3.76 × 1 mm; TDK now lists it as
obsolete/not recommended for new designs `D` [S27]. ICS-43434: 490 µA in
high-performance mode, 230 µA low-power, 12 µA sleep, 23–51.6 kHz in
high-performance mode; TDK lists it as EOL `D` [S28]. Either is a milliamp-class
load, two orders of magnitude below a speaker.

**Amplifier separate?** **Yes, always** — the microphone has no output. And on a
Zero there is no analogue audio jack to feed: the official port list for Zero W
and Zero 2 W contains two micro-USB ports, mini-HDMI, CSI, the GPIO header and
the microSD slot, and nothing else `D` [S15]. So the speaker needs a digital
input amplifier (the MAX98357A driver is `=m` and an in-tree overlay exists `D`
[S2][S4][S6]) or a codec HAT that already carries one.

---

## 5. Side-by-side

| | A1 WM8960 HAT | A2 AIC3104 HAT (v2) | B USB mic | C bare I2S mic |
| --- | --- | --- | --- | --- |
| Codec driver on 32-bit Pi OS | in-tree `=m` `D` | **not enabled**; built locally `D` | `snd-usb-audio=m` `D` | `ics43432=m` `D` |
| Vendor kernel patch needed | no `D` | no patch; out-of-tree module `D` | no `D` | no `D` |
| Overlay | in-tree `wm8960-soundcard` `D` | vendor `respeaker-2mic-v2_0` `D` | none `D` | `googlevoicehat-soundcard` or own `D`/`U` |
| ALSA card | `wm8960-soundcard` `D` | `seeed2micvoicec` `R` | device name, index varies `R` | `snd_rpi_googlevoicehat_soundcard` `D` |
| Capture format | 2 ch, codec rates `D` | 2 ch `R` | device-dependent `U` | fixed 2 ch/48 kHz/S32 `D` |
| PipeWire | device + source/sink `D` | same `D` | device + source `D` | device + source `D` |
| UCM profile | none → ACP `D`/`H` | none → ACP `H` | often present `D` | none → ACP `H` |
| Codec/board power | 25.6–57.4 mW record, 27.5–69.5 mW idle playback `D` | 14 mW playback `D` | device-specific `U` | 0.49–2.2 mA `D` |
| Amplifier | **integrated**, 1 W/ch `D` | **separate** TPA2005D1 `D` | separate | separate |

---

## 6. Traps

1. **"32-bit" is two kernels.** `kernel.img`/`bcmrpi` (ARMv6) and
   `kernel7.img`/`bcm2709` (ARMv7) are different builds `D` [S1]. Here they agree
   on every audio symbol, but a fix verified on one is not evidence for the other.
2. **Same product name, different codec.** ReSpeaker 2-Mics v1 is WM8960, v2 is
   TLV320AIC3104, and the v1 installer is explicitly deprecated by Seeed for
   current Raspberry Pi OS `D`/`R` [S22][S23]. Running the wrong one is not a
   tuning problem, it is the wrong driver for the chip on the board.
3. **Vendor READMEs outlive their truth.** Waveshare still says upstream WM8960 is
   unsupported `R` [S30] while the kernel ships both the codec and an overlay for
   its board `D` [S2][S5].
4. **Module-name shadowing.** The DKMS package installs `snd-soc-wm8960.ko`, the
   in-tree module's own name `D` [S31][S36]; a "successful" build silently swaps
   the maintained driver for a fork.
5. **The easy I2S-mic overlay is rigid.** 2 channels, 48 kHz, S32 only `D` [S9];
   a 16 kHz pipeline pays for resampling `H`.
6. **`i2s-mmap` is not in the kernel tree.** `arch/arm/boot/dts/overlays/i2s-mmap-overlay.dts`
   returns 404 at `rpi-5.10.y`, `rpi-6.6.y` and `rpi-6.12.y`; Seeed's v2 page says
   it is unnecessary after 4.0 `R` [S22]. Whether the firmware package still
   ships a copy was not checked `U`. The v1 install script still writes the line
   `D` [S31].
7. **Card index is not a configuration key.** Both vendor pages address cards by
   name and warn the number may differ `R` [S22][S30]; PipeWire exposes
   `api.alsa.path` for exactly this reason `D` [S19].
8. **A Zero has one data port.** A USB microphone and USB-gadget networking
   cannot both use it without a hub `D` [S15].
9. **ARM mmap caveat for USB audio.** Documented in the kernel's own ALSA
   configuration text `D` [S16].
10. **The v2 codec cannot lose channels.** TLV320AIC3x is fixed 2-in/2-out and
    the HAT has 2 microphones `D` [S23][S34], so "no vendor driver" costs the
    binding and mixer state, not channel count.

---

## 7. Unknowns and blocked

- **No runtime evidence of any kind.** No card was enumerated, no `arecord`, no
  PipeWire graph, no power measurement. `T` is empty.
- **Shipped-image module set** (`U`): the defconfigs were read, not an installed
  image's `/lib/modules`.
- **Whether the in-tree `wm8960-soundcard` overlay binds a Seeed v1 board.** It is
  written for the Waveshare board; the Seeed v1 overlay has the same codec, same
  I²C address, same 12.288 MHz clock and the same mic routing `D` [S5][S32], so
  it is plausible `H` — not tested.
- **HAT total current** (`U`): only codec figures are published.
- **Any named USB microphone's draw and UCM coverage** (`U`).
- **Whether a hand-written `simple-audio-card` + `ics43432` overlay works on a
  Zero** (`U`).
- **Whether the AIC3104 module built per Seeed's recipe loads on 6.12** — the
  vendor recipe names 6.6.51 headers `R`; 6.12 is untested `U`.
- **Whether PipeWire's 48 kHz→16 kHz resampling fits an ARMv6 budget** (`U`,
  consistent with the existing ARMv6 audio note).
- **raspberrypi.com product pages returned HTTP 403** to this session for both
  `/documentation/computers/raspberry-pi.html` and `/products/raspberry-pi-zero-w/`
  (`O`), so all Raspberry Pi facts above come from the `raspberrypi/documentation`
  and `raspberrypi/linux` repositories instead. No page content was guessed.

---

## 8. Verification performed

Working directory `/tmp/opencode/micpaths` (scratch; nothing preserved there).
All operations read-only over HTTPS:

```
curl -sS https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/configs/bcmrpi_defconfig
curl -sS .../bcm2709_defconfig
grep -nE "SND_USB_AUDIO|SND_BCM2835_SOC_I2S|SND_SIMPLE_CARD|SND_SOC_ICS43432|SND_SOC_DMIC|SND_SOC_WM8960|SND_SOC_TLV320|GOOGLEVOICEHAT" bcmrpi_defconfig bcm2709_defconfig
curl .../arch/arm/boot/dts/overlays/README ; curl .../overlays/{wm8960-soundcard,max98357a,googlevoicehat-soundcard}-overlay.dts
curl .../sound/soc/codecs/ics43432.c ; curl .../sound/soc/bcm/{bcm2835-i2s.c,rpi-simple-soundcard.c,googlevoicehat-codec.c}
curl .../arch/arm/boot/dts/broadcom/{bcm270x-rpi.dtsi,bcm2708-rpi-zero-w.dts}
curl .../Documentation/sound/alsa-configuration.rst ; curl .../sound/usb/Kconfig
curl https://docs.pipewire.org/page_objects_design.html ; .../page_man_pipewire-props_7.html
curl https://api.github.com/repos/alsa-project/alsa-ucm-conf/git/trees/master?recursive=1
curl -o *.pdf <datasheets> ; pdftotext -layout *.pdf ; grep ...
curl https://api.github.com/repos/torvalds/linux/commits/{f2644a2c00a0,44d0a879951a}
```

Observed: every fetch above returned 200 and the quoted strings appear in the
retrieved files. The only blocked hosts were `raspberrypi.com` (403) and
`statics.cirrus.com` (403 for the WM8960 PDF); the WM8960 datasheet was read
from a SparkFun-hosted copy of revision 4.2 `D` [S24]. Not run: any kernel build,
any module build, any device command.

---

## Handoff

### Findings

| Claim | Label | Source | Limits |
| --- | --- | --- | --- |
| Pi Zero/Zero W 32-bit kernel is `kernel.img` from `bcmrpi_defconfig`; Zero 2 W uses `kernel7.img` from `bcm2709_defconfig` | D | [S1](https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/linux_kernel/building.adoc) | Docs describe building, not the shipped image |
| Both 32-bit configs enable `SND_BCM2835_SOC_I2S`, `SND_SIMPLE_CARD`, `SND_USB_AUDIO`, `SND_SOC_WM8960`, `SND_SOC_ICS43432`, `SND_SOC_MAX98357A`, `SND_SOC_ADAU7002`, `SND_BCM2708_SOC_GOOGLEVOICEHAT_SOUNDCARD` | D | [S2](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/configs/bcmrpi_defconfig), [S3](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/configs/bcm2709_defconfig) | Config file only; installed image not inspected |
| Both 32-bit configs omit `SND_SOC_TLV320AIC3X(_I2C)` and `SND_SOC_DMIC` | D | [S2], [S3] | Same |
| The kernel ships an in-tree WM8960 overlay for the Waveshare HAT, named `wm8960-soundcard` | D | [S4](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/overlays/README), [S5](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/overlays/wm8960-soundcard-overlay.dts) | Written for Waveshare, not Seeed |
| WM8960 integrates 1 W/channel class-D; "no separate microphone, speaker or headphone amplifiers are required" | D | [S24](https://cdn.sparkfun.com/assets/a/3/a/7/4/WM8960_datasheet_v4.2.pdf) | Datasheet rev 4.2 mirror |
| WM8960 record at 48 kHz costs 25.6–57.4 mW; idle playback to 8 Ω 27.5–69.5 mW; 0 dBFS into 8 Ω up to 2.87 W | D | [S24] | Codec only, rails as tabulated |
| ReSpeaker v2 uses TLV320AIC3104 and a separate TPA2005D1 amp | D | [S23](https://files.seeedstudio.com/wiki/ReSpeaker_2_Mics_Pi_HAT/202004059_ReSpeaker-2-Mics-Pi-HAT-V2.0_SCH_PDF_241121.pdf) | Schematic, not a board |
| TLV320AIC3104 has HP/line drivers but no speaker amp; AIC3101 is the variant with one | D | [S25](https://www.ti.com/lit/ds/symlink/tlv320aic3104.pdf) | TI datasheet |
| TPA2005D1: 1.4 W into 8 Ω at 5 V, 2.8 mA quiescent, 0.5 µA shutdown | D | [S26](https://www.ti.com/lit/ds/symlink/tpa2005d1.pdf) | TI datasheet |
| Seeed tells Pi Zero W users to build `snd-soc-tlv320aic3x-i2c` against `linux-headers-6.6.51+rpt-rpi-v6` and add `dtoverlay=respeaker-2mic-v2_0` | D (vendor instructions) | [S22](https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/) | Vendor page; 6.12 not covered |
| v2 card appears as `seeed2micvoicec`, one substream each way | R | [S22] | Vendor console output |
| Vendor DKMS builds `snd-soc-wm8960` under the in-tree module name, patches only for ≤5.8 | D | [S31](https://raw.githubusercontent.com/respeaker/seeed-voicecard/master/dkms.conf) | Repo contents |
| Waveshare says upstream WM8960 is unsupported by current Pi kernels | R | [S30](https://raw.githubusercontent.com/waveshare/WM8960-Audio-HAT/master/README.md) | Contradicted by [S2][S5] |
| `snd-usb-audio` is built; UAC2 autoclock and quirk_flags documented; `use_vmalloc` mmap caveat on ARM | D | [S16](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/Documentation/sound/alsa-configuration.rst), [S17](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/usb/Kconfig) | Kernel docs |
| Zero W: 1.2 A supply, 150 mA typical, USB draw "limited by PSU, board and connector ratings only"; Zero 2 W: 2 A, 350 mA | D | [S14](https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/power-supplies.adoc) | No per-port figure |
| Zero W/Zero 2 W have two micro-USB ports (power + OTG) and no analogue audio jack | D | [S15](https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/zero/zero-models.adoc) | Port list |
| `ics43432` driver: capture-only, 1–2 ch, S24_LE/S32, 64 BCLK/frame, 7.19–52.8 kHz | D | [S10](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/soc/codecs/ics43432.c) | Driver source |
| `googlevoicehat` codec DAI is fixed 2 ch / 48 kHz / S32_LE; card `snd_rpi_googlevoicehat_soundcard` | D | [S9](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/soc/bcm/googlevoicehat-codec.c), [S8](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/soc/bcm/rpi-simple-soundcard.c) | Source |
| Adafruit's recipe for a bare I2S mic is `dtoverlay=googlevoicehat-soundcard` + `arecord -r 48000 -f S32_LE` | R | [S29](https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/raspberry-pi-wiring-test) | Vendor guide, model not specified |
| INMP441 1.4 mA @1.8 V / 2.2 mA @3.3 V, obsolete; ICS-43434 490 µA, EOL | D | [S27](https://product.tdk.com/system/files/dam/doc/product/sw_piezo/mic/mems-mic/data_sheet/inmp441.pdf), [S28](https://product.tdk.com/system/files/dam/doc/product/sw_piezo/mic/mems-mic/data_sheet/ds-000069-ics-43434-v1.2.pdf) | Datasheets; TDK status pages |
| PipeWire: ALSA card → device, PCM stream → node; UCM used when available, else ACP; `api.alsa.path` | D | [S18](https://docs.pipewire.org/page_objects_design.html), [S19](https://docs.pipewire.org/page_man_pipewire-props_7.html) | Docs |
| `alsa-ucm-conf` has a per-device USB-Audio tree and no entry for `wm8960-soundcard`, `seeed2micvoicec` or `voicehat` | D (tree) / H (consequence) | [S20](https://github.com/alsa-project/alsa-ucm-conf/tree/master/ucm2/USB-Audio) | Absence searched by name |
| `i2s-mmap` overlay absent from the kernel tree at 5.10/6.6/6.12 | D (404s) | [S35](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/overlays/i2s-mmap-overlay.dts) | Firmware package not checked |

### Traps

1. Two 32-bit kernels (ARMv6 `kernel.img`, ARMv7 `kernel7.img`) — same symbols
   here, different builds.
2. ReSpeaker v1 = WM8960, v2 = TLV320AIC3104; Seeed deprecates the v1 installer
   for current Raspberry Pi OS.
3. Vendor READMEs still claim upstream WM8960 is unsupported; the kernel ships
   the codec and an overlay for that board.
4. The DKMS package installs its codec under the in-tree module name, silently
   replacing it.
5. The stock bare-mic overlay is fixed at 48 kHz/2 ch/S32; 16 kHz costs
   resampling.
6. `dtoverlay=i2s-mmap` is not in current kernel trees, yet the v1 script writes
   it.
7. Card indices move; address cards by name or `api.alsa.path`.
8. A Zero has one data port; a USB mic excludes USB-gadget networking without a
   hub.
9. `use_vmalloc` + mmap is documented as unreliable on ARM.
10. No analogue jack on a Zero: a speaker needs a digital-input amp or a codec
    HAT.

### Unknowns / blocked

- No device evidence: no card enumerated, no recording, no power measurement.
- Installed image's module set not inspected (defconfig only).
- Whether the in-tree `wm8960-soundcard` overlay binds a Seeed v1 board.
- HAT total current; any named USB microphone's draw and UCM coverage.
- Whether a hand-written `simple-audio-card` + `ics43432` overlay works on a Zero.
- Whether Seeed's AIC3104 module recipe works on 6.12 (vendor names 6.6.51).
- Whether PipeWire's 48→16 kHz resampling fits an ARMv6 budget.
- `raspberrypi.com` returned 403; Raspberry Pi facts were taken from the
  documentation and kernel repositories instead.

### One next bounded check

On a **spare** Pi Zero W with stock 32-bit Raspberry Pi OS Lite, no installs and
no network changes: `arecord -l`, `modinfo snd-soc-ics43432 snd-soc-wm8960
snd-usb-audio`, `ls /boot/firmware/overlays | grep -E
'wm8960|googlevoicehat|max98357|i2s-mmap'`, and — only if a microphone is already
attached — `arecord -D plughw:<n> -f S16_LE -r 16000 -d 3 /dev/null`. That
converts four `U` rows (shipped modules, overlay availability, card names, one
real capture) into facts without building anything. Device ownership and
coordinator approval are prerequisites; nothing here authorizes touching a board.

---

## Source register

All URLs fetched 2026-11-15.

| Key | Source | What it supports |
| --- | --- | --- |
| S1 | https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/linux_kernel/building.adoc | 32-bit kernel/config map: Zero/Zero W → `kernel`/`bcmrpi_defconfig`; Zero 2 W → `kernel7`/`bcm2709_defconfig` |
| S2 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/configs/bcmrpi_defconfig | ARMv6 config: audio symbols present/absent |
| S3 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/configs/bcm2709_defconfig | ARMv7 config: same symbol set |
| S4 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/overlays/README | Overlay inventory and descriptions (`wm8960-soundcard`, `max98357a`, `googlevoicehat-soundcard`); no `i2s-mmap` entry |
| S5 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/overlays/wm8960-soundcard-overlay.dts | WM8960 @0x1a, 12.288 MHz, `simple-audio-card`, card name, routing, `alsaname` |
| S6 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/overlays/max98357a-overlay.dts | In-tree I2S amp overlay shape |
| S7 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/overlays/googlevoicehat-soundcard-overlay.dts | `google,voicehat` codec node, `sdmode` GPIO, machine-driver compatible |
| S8 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/soc/bcm/rpi-simple-soundcard.c | Card name `snd_rpi_googlevoicehat_soundcard`; DAI link to `voicehat-codec` |
| S9 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/soc/bcm/googlevoicehat-codec.c | Fixed 2 ch, 48 kHz, S32_LE capture and playback |
| S10 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/soc/codecs/ics43432.c | Bare-mic codec driver capabilities |
| S11 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/soc/bcm/bcm2835-i2s.c | I²S controller with capture stream and RX DMA |
| S12 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/broadcom/bcm270x-rpi.dtsi | `sound` node and `i2s_clk_producer`/`i2s_clk_consumer` labels on the ARMv6 tree |
| S13 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/broadcom/bcm2708-rpi-zero-w.dts | I²S on GPIO 18–21, ALT0 |
| S14 | https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/power-supplies.adoc | Recommended PSU, typical board current, USB current wording |
| S15 | https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/zero/zero-models.adoc | Zero W / Zero 2 W port list: two micro-USB (power + OTG), no analogue jack |
| S16 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/Documentation/sound/alsa-configuration.rst | `snd-usb-audio` parameters, UAC2 autoclock, ARM `use_vmalloc` mmap caveat |
| S17 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/usb/Kconfig | `SND_USB_AUDIO` = "USB Audio/MIDI driver" |
| S18 | https://docs.pipewire.org/page_objects_design.html | ALSA card → device, PCM stream → node, profile/verb mapping |
| S19 | https://docs.pipewire.org/page_man_pipewire-props_7.html | `api.alsa.path`, `api.alsa.use-ucm`, ACP fallback, Pro Audio clock semantics |
| S20 | https://github.com/alsa-project/alsa-ucm-conf/tree/master/ucm2/USB-Audio | Per-vendor USB audio UCM profiles; no entries for the I²S card names |
| S21 | https://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT/ | v1 board: WM8960, 3.5 mm jack, JST 2.0 speaker out, max 48 kHz |
| S22 | https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/ | v2 driver build for Pi Zero W (`rpt-rpi-v6` headers), overlay, card `seeed2micvoicec`, `i2s-mmap` note, v1 method deprecated |
| S23 | https://files.seeedstudio.com/wiki/ReSpeaker_2_Mics_Pi_HAT/202004059_ReSpeaker-2-Mics-Pi-HAT-V2.0_SCH_PDF_241121.pdf | TLV320AIC3104IRHBR, TPA2005D1DGNR with `AMP_CTL`/`SPK±`, revision history |
| S24 | https://cdn.sparkfun.com/assets/a/3/a/7/4/WM8960_datasheet_v4.2.pdf | WM8960 class-D 1 W/ch, "no separate … amplifiers", typical power tables |
| S25 | https://www.ti.com/lit/ds/symlink/tlv320aic3104.pdf | AIC3104 HP-only outputs, 14 mW playback, AIC3101/AIC3107 comparison |
| S26 | https://www.ti.com/lit/ds/symlink/tpa2005d1.pdf | TPA2005D1 1.4 W/8 Ω at 5 V, 2.8 mA quiescent, 0.5 µA shutdown |
| S27 | https://product.tdk.com/system/files/dam/doc/product/sw_piezo/mic/mems-mic/data_sheet/inmp441.pdf | INMP441 current, I²S format, rate range |
| S28 | https://product.tdk.com/system/files/dam/doc/product/sw_piezo/mic/mems-mic/data_sheet/ds-000069-ics-43434-v1.2.pdf | ICS-43434 current, modes, rates |
| S29 | https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/raspberry-pi-wiring-test | `dtoverlay=googlevoicehat-soundcard` and `arecord … S32_LE` recipe |
| S30 | https://raw.githubusercontent.com/waveshare/WM8960-Audio-HAT/master/README.md | Vendor install script, vendor claim about upstream WM8960, `aplay`/`arecord` output |
| S31 | https://raw.githubusercontent.com/respeaker/seeed-voicecard/master/dkms.conf | DKMS modules, in-tree module-name collision, patch matches ≤5.8 |
| S32 | https://raw.githubusercontent.com/respeaker/seeed-voicecard/master/seeed-2mic-voicecard-overlay.dts | v1 overlay: WM8960 @0x1a, 12.288 MHz, same routing as the in-tree overlay |
| S33 | Repository: docs/notes/2026-11-15-armv6-audio-stack.md | PipeWire/WirePlumber ARMv6 packaging, resampling-cost caveat, headless profile |
| S34 | https://github.com/torvalds/linux/commit/f2644a2c00a0 and https://github.com/torvalds/linux/commit/44d0a879951a | WM8960 driver (2009-04-07) and TLV320AIC3X driver (2007-11-14) entry dates |
| S35 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-5.10.y/arch/arm/boot/dts/overlays/i2s-mmap-overlay.dts , https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.6.y/arch/arm/boot/dts/overlays/i2s-mmap-overlay.dts , https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/overlays/i2s-mmap-overlay.dts | All three return HTTP 404, i.e. no `i2s-mmap` overlay in those kernel trees |
| S36 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/sound/soc/codecs/Makefile | `obj-$(CONFIG_SND_SOC_WM8960) += snd-soc-wm8960.o`; `snd-soc-ics43432.o` |
