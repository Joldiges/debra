---
title: ReSpeaker 2-Mics Pi HAT v2 on Debian 13 trixie — codec support, vendor driver, and upgrade safety
date: 2026-11-15
type: project-learning
status: unreviewed
task: unattended research run, 2026-11-15 (no device access, no installs)
author: AI agent (DeepSeek V4.1 Flash 1017, unattended scheduled run)
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - Debian 13 trixie linux-config-6.12 6.12.117-1 kernel configs (arm64, armhf, armel), read 2026-11-15
  - Linux mainline source (v2.6.24, v2.6.25, v2.6.29, v2.6.30, v2.6.31, v6.12, v6.17–v6.18) via GitHub raw/API, read 2026-11-15
  - Raspberry Pi downstream kernel rpi-6.12.y device trees, defconfig and overlay list, read 2026-11-15
  - Seeed Studio wiki (ReSpeaker 2-Mics Pi HAT v1 and v2 pages) and github.com/Seeed-Studio/seeed-linux-dtoverlays, read 2026-11-15
  - github.com/respeaker/seeed-voicecard and github.com/HinTak/seeed-voicecard (source, README, issues), read 2026-11-15
  - PipeWire and ALSA documentation, read 2026-11-15
supersedes: []
---

# ReSpeaker 2-Mics Pi HAT v2 on Debian 13 trixie

**Research result from public sources only, 2026-11-15. The lab Pi 5 was not
contacted or inspected, nothing was installed, and no kernel was built.** Every
claim below carries one label and a source key from the register at the end of
this note.

Labels: **D** = documented upstream (stated by the cited primary source, not
reproduced here); **R** = reported (vendor statement, third-party report or
project record); **H** = hypothesis (my inference from the cited sources, not
stated by any of them); **U** = unknown; **T** = tested (Debra measurement,
cited).
Nothing here is `tested` on Debian 13 itself — see *Verification*.

---

## Summary

1. **Revision first.** The 2024 "v2" HAT does not contain a WM8960. Seeed's
   own v2 overlay and wiki put a **TLV320AIC3104 at I²C 0x18 with a 24.576 MHz
   MCLK**, and the codec is the I²S bit/frame master [S1][S2]. The
   `seeed-voicecard` DKMS package belongs to the **v1 (WM8960)** board [S3].
2. **Both codecs are in the mainline kernel**, and both are older than the
   boards: the TLV320AIC3x driver arrived in **Linux 2.6.25** (commit
   `44d0a879951a`) [S4], the WM8960 driver in **Linux 2.6.31** (commit
   `f2644a2c00a0`) [S5].
3. **Debian 13 trixie does not ship a usable in-tree driver for either board**
   in the combinations that matter: the TLV320AIC3x **I²C glue is explicitly
   disabled** on arm64, armhf and armel, and the WM8960 is enabled only on arm64
   [S6][S7][S8]. This is a Debian configuration choice, not a kernel limitation.
4. **On a Pi 5 the transport is missing too.** Mainline 6.12's BCM2712 device
   tree has no I²S node at all and mainline has no RP1 device trees before
   v6.17 [S9][S10]; Debian does not build the DesignWare I²S driver that the
   Pi 5's RP1 block uses [S6][S7][S8]. On a Pi Zero 2 W/Pi 4 the BCM283x I²S
   node and driver *are* present [S11].
5. **LEDs and the button never belonged to the kernel driver.** The button is
   on GPIO17 and the three LEDs are APA102 over SPI [S2][S12]; the v2 vendor
   path is a device-tree overlay plus, on Raspberry Pi OS, a hand-built copy of
   the in-tree TI codec driver [S2]. So "without the vendor driver" costs the
   codec binding and the shipped mixer state — not the button or LEDs.

---

## 1. Which board, which codec — get this right before comparing drivers

| Property | v1.0 (2017) | v2.0 (2024) |
| --- | --- | --- |
| Codec | WM8960 | TLV320AIC3104 |
| I²C address | 0x1a | 0x18 |
| MCLK | 12.288 MHz fixed clock, codec is clock slave (`slave_overlay`) | 24.576 MHz fixed clock; codec is `bitclock-master` and `frame-master` |
| Overlay | `seeed-2mic-voicecard.dtbo` (in the seeed-voicecard repo) | `respeaker-2mic-v2_0.dtbo` (seeed-linux-dtoverlays, MIT) |
| Card name in DT | `seeed-2mic-voicecard` | `seeed2micvoicec` |
| Vendor kernel module | yes — DKMS `seeed-voicecard`, name-clashes with in-tree `snd-soc-wm8960` | **none** — the overlay is the whole vendor artefact |
| Sources | [S3][S13] | [S1][S2][S14] |

`D` for every row above except the "vendor module" row for v2, which is `D`
in the negative sense: the v2 overlay repository contains no codec driver for
this board, and Seeed's v2 instructions build one from the Raspberry Pi kernel
tree rather than from Seeed code [S2][S1].

A second v1 overlay exists in the newer Seeed repository, and it disagrees with
the first about clocks: 24 MHz and `i2s_clk_consumer` instead of 12.288 MHz and
`slave_overlay` `D` [S26]. "The v1 overlay" is therefore ambiguous; take the one
from the repository whose instructions match the kernel you are running.

Seeed's v2 wiki opens by declaring the v1 installation method obsolete on
current Raspberry Pi OS and listing what breaks if you run it anyway: "The
desktop environment may be corrupted after installation. The ReSpeaker device
may not able to be detected by `aplay` / `arecord`." [S2] `D`.

---

## 2. In-tree kernel driver situation

### 2.1 When each driver entered the kernel

| Codec | Driver | First release | Evidence |
| --- | --- | --- | --- |
| TLV320AIC3104 (v2) | `sound/soc/codecs/tlv320aic3x.c` + `tlv320aic3x-i2c.c` | **Linux 2.6.25** | Commit `44d0a879951a` "[ALSA] ASoC TLV320AIC3X codec driver", 2007-11-14; file present at tag `v2.6.25`, absent at `v2.6.24` — `D` [S4] |
| WM8960 (v1) | `sound/soc/codecs/wm8960.c` | **Linux 2.6.31** | Commit `f2644a2c00a0` "ASoC: Add WM8960 CODEC driver", 2009-04-07; file absent at `v2.6.30`, present at `v2.6.31` — `D` [S5] |

The v2 codec is matched by the generic AIC3x driver: the I²C glue's OF table
contains `{ .compatible = "ti,tlv320aic3104" }`, and the codec file carries
AIC3104-specific register handling ("Not on tlv320aic3104",
"Left PGA Mixer for tlv320aic3104"). `D` [S15]. So no vendor codec source is
needed for the v2 board — only a kernel built with that driver and an overlay.

### 2.2 Is it enabled in Debian 13's kernel? (checked per architecture)

Read from the shipped build configs inside `linux-config-6.12_6.12.117-1` for
each architecture (the trixie kernel is 6.12.117-1; `D` [S6][S7][S8][S16]):

| Symbol | arm64 (Pi 3/4/5/Zero 2 W, 64-bit) | armhf (armmp) | armel (rpi flavour) |
| --- | --- | --- | --- |
| `CONFIG_SND_SOC_TLV320AIC3X` (v2 codec core) | hidden symbol; no `=m` line emitted | `=m` | absent |
| `CONFIG_SND_SOC_TLV320AIC3X_I2C` (**what actually binds an I²C codec**) | `# … is not set` | `# … is not set` | `# … is not set` |
| `CONFIG_SND_SOC_WM8960` (v1 codec) | `=m` | `# … is not set` | `# … is not set` |
| `CONFIG_SND_BCM2835_SOC_I2S` | `=m` | `=m` | `=m` |
| `CONFIG_SND_SIMPLE_CARD` / `_UTILS` | `=m` / `=m` | `=m` | `# … is not set` |
| `CONFIG_SND_DESIGNWARE_I2S` (Pi 5 RP1 I²S IP) | `# … is not set` | `# … is not set` | `# … is not set` |
| `CONFIG_SND_AUDIO_GRAPH_CARD` | `=m` | `=m` | (not checked) |

Consequences, each `D` from the config rows above:

- **v2 board on any Debian 13 architecture: no in-tree codec.** The core driver
  is behind a hidden symbol that the visible `…_I2C`/`…_SPI` options select
  (`D`, Kconfig [S15]); both glue options are disabled everywhere, so the codec
  cannot bind even though its source is in the tree. The `=m` on the parent in
  armhf does not change this: the I²C glue is a separate module.
- **v1 board on Debian 13 arm64: the codec module exists** (`CONFIG_SND_SOC_WM8960=m`).
- **v1 board on Debian 13 armhf/armel: no codec.** Note also that trixie's armhf
  package ships only `armmp`, `armmp-lpae` and `rt` configs, i.e. ARMv7+; the
  ARMv6 Pi Zero/Zero W is covered by the separate **armel `rpi`** flavour, whose
  config also lacks WM8960 `D` [S7][S8].

### 2.3 The transport half: Pi 5 versus Pi Zero 2 W/Pi 4

- Mainline 6.12's `arch/arm64/boot/dts/broadcom/bcm2712.dtsi` contains **no I²S
  node**, and mainline 6.12 has no `rp1.dtsi`; RP1 device trees first appear in
  mainline **v6.17** (`rp1.dtsi`, `rp1-common.dtsi`, `rp1.dtso`). `D` [S9][S10]
- The Raspberry Pi downstream tree models the Pi 5's I²S as DesignWare blocks
  inside RP1 — `rp1_i2s0`/`rp1_i2s1`, `compatible = "snps,designware-i2s"` —
  and aliases them as `i2s_clk_producer`/`i2s_clk_consumer`, with a `sound`
  node. `D` [S11]
- Mainline's BCM283x device tree does have an I²S controller
  (`i2s: i2s@7e203000`), i.e. the Pi Zero 2 W/3/4 path. `D` [S11]
- Debian builds `SND_BCM2835_SOC_I2S=m` on all three architectures and does
  **not** build `SND_DESIGNWARE_I2S`. `D` [S6][S7][S8]

**What this means.** On a **Pi 5 with Debian 13's mainline kernel**, the codec
question is moot: there is no in-tree I²S controller in the shipped Pi 5 device
tree and the RP1 I²S driver is not built, so a card cannot appear from in-tree
code alone. `D` from source; the *consequence* (that no card appears) is `U`
because it was not booted. On a **Pi Zero 2 W or Pi 4**, the transport exists in
mainline and Debian builds its driver, so a hand-written overlay plus an enabled
codec could produce a card. `U` — untested.

### 2.4 Overlay label dependency

Both Seeed overlays and the Raspberry Pi `wm8960-soundcard` overlay target
`&sound` (and `&i2s_clk_consumer`/`&i2s_clk_producer`) — labels that exist in
the **Raspberry Pi downstream** device trees. Mainline provides the `i2s` label
but neither `sound` nor `i2s_clk_*`. `D` [S1][S11]

The two vendor overlays for the *same* v1 board have drifted apart: the DKMS repo
uses a 12.288 MHz fixed clock with `slave_overlay`, the newer
`seeed-linux-dtoverlays` copy uses 24 MHz and `i2s_clk_consumer` `D` [S13][S26].
Which matches a given board revision is `U`; do not copy clocking numbers between
them.

So on a mainline-DT system (Debian 13) these overlays will not apply as shipped;
an overlay written for mainline must attach `simple-audio-card` (or
`audio-graph-card`) directly to the `i2s` node and declare the codec as master
if that is how the board clocks. `U` for whether such a rewrite works with this
HAT; it is a bounded experiment (see handoff).

---

## 3. The vendor path: `seeed-voicecard` and its DKMS package

This section applies to the **v1/WM8960** board. For the v2 board the vendor
path is a device-tree overlay only (§3.4).

### 3.1 What the package builds and what it patches

`D` from the repositories [S3][S13][S17]:

- **DKMS package** `seeed-voicecard` version `0.3`, `AUTOINSTALL="yes"`,
  building three modules:
  - `snd-soc-wm8960` — a **vendored copy of the in-tree codec driver**
    (`wm8960.c`, 1421 lines in the maintained fork), installed into
    `/kernel/sound/soc/codecs`;
  - `snd-soc-ac108` — the AC108/AC101 codecs for the 4-/6-mic arrays (not used
    by the 2-mic HAT);
  - `snd-soc-seeed-voicecard` — a fork of ASoC `simple-card` used as a machine
    driver.
- **The codec module reuses the in-tree module name.** The vendor module is
  installed as `snd-soc-wm8960.ko`, exactly the name the in-tree driver uses
  (`obj-$(CONFIG_SND_SOC_WM8960) += snd-soc-wm8960.o`) [S3][S18]. On a kernel
  that already ships the in-tree module, the DKMS build **replaces the distro's
  codec driver**.
- **It patches the boot configuration, not the kernel:** it copies three `.dtbo`
  files into `/boot/overlays` (or `/boot/firmware/overlays`), appends
  `dtoverlay=i2s-mmap` and `dtparam=i2s=on` to `config.txt`, adds the three
  modules to `/etc/modules`, installs `/etc/voicecard/*.conf` and `*.state`
  ALSA files, and enables a oneshot systemd unit that runs
  `/usr/bin/seeed-voicecard` at boot to re-apply `dtparam`/`dtoverlay` lines
  [S3][S17]. The install script also runs `apt-get install` for kernel headers
  and, if `git config --global user.email` is unset, **sets the operator's
  global git identity** to `respeaker@seeed.cc`/`respeaker` [S3].
- **Its ALSA config is userspace mixing:** `asound_2mic.conf` defines
  `pcm.dmixed` (`type dmix`) and `pcm.array` (`type dsnoop`) over
  `hw:seeed2micvoicec` with fixed `ipc_key`s [S17][S19].

### 3.2 Does it build on recent kernels?

| Observation | Label | Source |
| --- | --- | --- |
| Original repo last commit 2021-11-25; `dkms.conf` carries back-port patches matched only to kernels `4.19.*`, `5.4.*`, `5.8.*` | `D` | [S3] |
| Third-party fork `HinTak/seeed-voicecard` is current: HEAD 2026-10-19, with commits "v6.11: platform_driver::remove() return void" (2024-10), "v6.13: ASoC: rename rtd->num to rtd->id" (2025-02), and a July 2026 hardening series including a regression harness | `D` | [S20] |
| The fork's README advises `install.sh --compat-kernel` and warns the driver "may probably happen that … won't compile with the latest kernel when raspbian rolls out new patches" | `R` (vendor/fork statement) | [S20] |
| Reported build failure: "Bad return status for module build on kernel: 6.6.20+rpt-rpi-v8 (aarch64)" | `R` | [S21] |
| Reported installer failure on Raspberry Pi OS with kernel 6.12.47 (2025-10-16): wrong kernel version detected, offers to "revert the kernel", then refuses with "loaded kernel version is 6.12.47 / not matching 6.1.21" | `R` | [S22] |
| The vendor README's rationale — "upstream wm8960 has some bugs, we had fixed it" — and its support matrix limited to Raspberry Pi OS 32/64-bit on Pi 3/4/Zero(W) | `R` (vendor claim; the "not supported by current Pi kernel builds" half is contradicted by `CONFIG_SND_SOC_WM8960=m` in the rpi-6.12 defconfig [S11]) | [S3][S20] |
| Builds cleanly against Debian 13's `linux-headers-6.12.117-*` | `U` — not attempted, no report found | — |

### 3.3 What happens on a kernel upgrade

`D` for the mechanism (DKMS with `AUTOINSTALL="yes"` rebuilds per kernel when
matching headers are installed [S3][S23]); `U` for this specific package's
outcome, since it was not built here:

1. New kernel installed → DKMS postinst hook rebuilds `seeed-voicecard/0.3`
   against the new headers. If headers are missing or the build fails, there is
   **no module for the new kernel**.
2. The overlay is still applied (it is unconditional), so the device tree
   advertises a card whose codec driver is absent → the card does not appear.
   The user-visible result is "audio stopped after an update", with no
   obviously broken overlay.
3. Because the vendor module shares the in-tree module name, a *successful*
   build silently substitutes the vendor's modified codec for the maintained
   one; a *failed* build can leave the in-tree module in place on Debian arm64
   (where it is enabled) but nothing at all on armhf/armel.
4. The vendor boot service keeps rewriting `config.txt` and re-running
   `dtparam`, so stale or duplicated boot lines can survive across upgrades.

### 3.4 The v2 board's actual "vendor path"

`D` [S2]: Seeed's v2 instructions are (1) build an out-of-tree module **by hand**
from the Raspberry Pi kernel tree — copy `sound/soc/codecs/tlv320aic3x.c`,
`tlv320aic3x.h` and `tlv320aic3x-i2c.c` from `rpi-6.6.y`, write a two-line
Makefile, `make`, `sudo make install`, `modprobe snd-soc-tlv320aic3x-i2c`;
(2) build `respeaker-2mic-v2_0-overlay.dtbo`, copy it to
`/boot/firmware/overlays/`, add `dtoverlay=respeaker-2mic-v2_0` to
`config.txt`.

Why step 1 exists is visible in Raspberry Pi OS's own defconfig: it sets
`CONFIG_SND_SOC_WM8960=m`, `CONFIG_SND_SIMPLE_CARD=m` and
`CONFIG_SND_DESIGNWARE_I2S=m` but contains **no TLV320AIC3x symbol** `D` [S11].
So even on Raspberry Pi OS the v2 board needs a locally built module — and that
module is a plain `cp` into `/lib/modules/$(uname -r)`, not DKMS `D` [S2].
After a kernel upgrade it is in the previous kernel's directory and the card
disappears; the failure mode (silently missing card) is `U` in observation but
mechanically implied `H`.

---

## 4. What is actually lost without the vendor driver

Split by board, because "vendor driver" means different things.

| Capability | v2 board, no vendor artefacts | v1 board with in-tree WM8960 instead of the DKMS package |
| --- | --- | --- |
| **Capture channels** | Nothing. TLV320AIC3x advertises **exactly 2** playback and 2 capture channels (`channels_min = channels_max = 2`) `D` [S15]; the board has 2 analog mics `D` [S2]. | Nothing on the 2-mic HAT: WM8960 is 1–2 ch each way `D` [S18]. The vendor machine driver's channel-range override exists for AC108 TDM arrays, not this board `D` [S17]. |
| **LED access** | Nothing lost by omitting a driver: three APA102 RGB LEDs on **SPI**, driven from userspace; `dtparam=spi=on` is all the "driver" there is `D` [S2][S12]. No APA102/LED code exists in any vendor module `D` [S3][S20]. | Same. |
| **Button access** | Nothing; the button is **GPIO17** and read from userspace `D` [S12]. Seeed warns the `RPi.GPIO` demo does not work on Pi 5 and ships a `gpiozero` alternative `D` [S2]. | Same. |
| **Hardware mixing** | Does not exist on either board. ALSA exposes one substream per direction (`Subdevices: 1/1` in Seeed's own `aplay -l` output `D` [S20]); `dmix`/`dsnoop` are alsa-lib **userspace** plugins, and PipeWire mixes in userspace `D` [S19][S24]. | Same; the vendor's `asound_2mic.conf` adds `dmix`/`dsnoop` *configuration*, which is reproducible without the package `D` [S17]. |
| **TPA2005D1 amplifier path** | Not driver-gated. The amplifier sits downstream of the codec's line/headphone output and is enabled by codec routing/mixer state, which the overlay's `simple-audio-card,routing` and ALSA controls express `D` [S1]. | The vendor package contributes a saved mixer state (`wm8960_asound.state`) restored at boot `D` [S17]. Losing it costs the tuning, not the amplifier: you must reproduce the state with `alsactl`. `T` for "the amplifier is present and drives the JST speaker" on Debra's specimen (lab record); a public schematic statement naming the part was **not** found `U`. |
| **Vendor codec patches** (v1) | n/a | Lost, by definition. The vendor claims fixes to upstream WM8960 bugs `R` [S20]; whether they still matter on 6.12 is `U`. |
| **Board-specific boot edits** | Recoverable in a few lines: `dtparam=i2s=on`, the overlay line, and (on post-4.0 kernels, per Seeed) not `i2s-mmap` `D` [S2][S3]. | Same. |

**Net:** for either board, the vendor package is not what provides LEDs,
buttons, capture-channel count or amplification. What it provides is the codec
binding (v1), a tuned ALSA state, some boot lines, and — for v2 — nothing but an
overlay plus a from-source module build.

---

## 5. How the two paths present themselves to ALSA and PipeWire

| | v1 vendor path | v2 vendor path | In-tree generic path |
| --- | --- | --- | --- |
| ALSA card name | `seeed-2mic-voicecard` | `seeed2micvoicec` | whatever the overlay's `simple-audio-card,name` says (a mainline rewrite can keep either string) |
| ALSA handle | `hw:seeed-2mic-voicecard` (name-based) | `hw:seeed2micvoicec` | same shape |
| Streams | 1 substream each way, 2 ch | 1 substream each way, 2 ch (fixed) | same |
| PipeWire | ALSA card → one Device; each PCM stream → a node; without UCM/ACP profile the fallback is on/off or "Pro Audio" | identical | identical |
| Mixing | PipeWire (or ALSA `dmix` if something bypasses PipeWire) | PipeWire | PipeWire |

`D` for card names [S1][S3]; `D` for the PipeWire mapping — "ALSA cards are
represented as PipeWire devices … a node and an associated endpoint are created
for every available PCM stream", with on/off profiles in the ALSA fallback and
`api.alsa.path`/card properties for addressing [S24][S25]; `D` for
`dmix`/`dsnoop` being alsa-lib plugins [S19].

Two consequences worth designing around:

1. **PipeWire cannot tell the paths apart.** It sees an ALSA card with a name
   and two PCM streams. Whether a WM8960 or a TLV320AIC3104 produced it changes
   nothing above ALSA.
2. **Name is the stable handle; index is not.** The vendor's own ALSA config
   addresses the card by name (`hw:seeed2micvoicec`) rather than by `hw:0`/`hw:1`
   `D` [S17]. Probe order, and therefore card index, is not a stable
   configuration key; `R` (well-known ALSA behaviour, not measured here).

---

## 6. The safer default for an appliance that must survive an unattended kernel upgrade

Stated as a judgement (`H`/`U`, reasoned from the sources above, not measured):

1. **Best: in-tree codec + an overlay Debra owns, no out-of-tree module.** A
   kernel upgrade then only has to keep stable DT bindings and the same codec
   symbol; nothing is compiled at install time and nothing is copied into
   `/lib/modules/$(uname -r)`. Today this works for **v1 on arm64**
   (`CONFIG_SND_SOC_WM8960=m`) and does **not** work for v2 on any Debian 13
   architecture (I²C glue disabled) or for v1 on armhf/armel `D` [S6][S7][S8].
2. **Second: v2 with an overlay, provided the codec module is genuinely
   available** — i.e. from a distribution that enables `…_TLV320AIC3X_I2C`, or
   from a package Debra maintains itself with declared header dependencies and a
   post-boot audio check.
3. **Worst: any DKMS or hand-copied module** — the v1 package, or Seeed's v2
   "copy the .ko" recipe. Both fail silently on a kernel change, and the v1
   variant also replaces the maintained codec driver with a fork of it
   `D` [S3][S2].

Because Debian 13 as shipped has no codec enabled for the v2 board, "in-tree"
is not currently an available option for that board; the honest ranking is
therefore about **which module you accept rebuilding**, not about whether one
exists. A defensible appliance policy: pin the kernel; carry the overlay in
Debra's configuration; if a module is unavoidable, package it properly (DKMS or
a local package) with an explicit header dependency; and gate every kernel
upgrade on a post-boot audio check (card present, capture not silent, playback
device present) with rollback to the previous kernel. The policy is a proposal;
the check *contents* would need to be specified and tested.

---

## 7. Is the button wired to the codec or to a GPIO? What that means for mute

**GPIO17, not the codec.** `D` [S12]: "There is an on-board User Button, which
is connected to GPIO_17." No vendor kernel module or overlay declares a
gpio-keys node or a codec GPIO for it `D` [S3][S1]. Debra's own records describe
it as active-low (`R`, project record).

Consequences:

- **No ALSA control path from the button.** Nothing in `amixer`/`alsactl` will
  ever see it, on either revision, with or without the vendor driver.
- **A mute control must be userspace**: a daemon reading the GPIO (libgpiod, or
  `gpiozero` on Pi 5 — Seeed explicitly ships a `gpiozero` example because the
  old `RPi.GPIO` demo is incompatible with Pi 5 `D` [S2]) and acting on
  PipeWire or ALSA. That is `D` for the wiring and the Pi 5 GPIO caveat, `U`
  for the press-to-mute mapping (a product decision; debounce, long-press and
  visible feedback are unmeasured).
- **Codec mute ≠ application mute.** A codec-level mute (an ALSA switch on the
  codec) silences the DAC while the stream keeps running; a PipeWire-level mute
  is visible to Home Assistant and to other clients. Which one the appliance
  should use is `U`; they are not interchangeable for automation.
- **LEDs are in the same category**: SPI0/APA102, userspace, no codec or audio
  driver involvement `D` [S2][S12].

---

## Verification

- **Working directory:** `/tmp/opencode/respeaker-research` (scratch; nothing
  added to the repository except this note).
- **What was actually done (all read-only):**
  - downloaded `linux-config-6.12_6.12.117-1_{arm64,armhf,armel}.deb` from
    `deb.debian.org`, extracted with `ar x` and `tar -xf`, and read
    `usr/src/linux-config-6.12/config.*.xz` with `xz -dc` + `grep`;
  - fetched version-pinned kernel sources and directory listings from
    `raw.githubusercontent.com`/`api.github.com` at tags `v2.6.24`, `v2.6.25`,
    `v2.6.29`, `v2.6.30`, `v2.6.31`, `v6.12`, `v6.17`, `v6.18`;
  - `git clone --depth 1` of `respeaker/seeed-voicecard`,
    `HinTak/seeed-voicecard` and `Seeed-Studio/seeed-linux-dtoverlays`; read
    `dkms.conf`, `install.sh`, `Makefile`, overlays, `asound_2mic.conf`,
    `seeed-voicecard.service`, and grepped for GPIO/LED/button handling;
  - read the Raspberry Pi `rpi-6.12.y` device trees, `rp1.dtsi`, overlay
    Makefile and `bcm2711_defconfig`;
  - read Seeed's v1/v2 wiki pages, PipeWire documentation and alsa-lib plugin
    documentation.
- **Observed results:** every fetch and extraction succeeded; no page was
  blocked. One failed lookup is disclosed: the file list of Debian's
  `raspi-firmware` package could not be parsed, so **no claim is made** about
  which overlays that package ships.
- **Not tested, and it matters:**
  - Nothing ran on Debian 13, on a Pi 5, on a Pi Zero 2 W, or on the lab device.
    No module was built; no kernel was booted; no card was enumerated.
  - Whether Debian's 6.12 source backports RP1 device trees (which would change
    the Pi 5 transport conclusion) — `U`.
  - Whether `seeed-voicecard` (either repo) compiles against Debian's
    `linux-headers-6.12.117` — `U`.
  - Whether the in-tree TLV320AIC3x driver, once enabled, works with this
    board's 24.576 MHz MCLK and codec-master clocking — `U`.
  - Whether a mainline-style overlay (attached to `i2s`, not `&sound`) yields a
    working card on any Pi — `U`.
  - TPA2005D1 presence/behaviour is `T` only on Debra's specimen; no public
    schematic text naming it was found.

---

## Source register

All URLs checked 2026-11-15.

| Key | Source | What it supports |
| --- | --- | --- |
| S1 | https://github.com/Seeed-Studio/seeed-linux-dtoverlays/blob/master/overlays/rpi/respeaker-2mic-v2_0-overlay.dts | v2 board: `ti,tlv320aic3104` @0x18, 24.576 MHz fixed clock, `simple-audio-card` name `seeed2micvoicec`, `i2s_clk_consumer`, codec bit/frame master, routing to HPLOUT/HPROUT |
| S2 | https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/ | v2 codec/driver situation; v1 method deprecated; TLV320 build recipe; `dtoverlay=respeaker-2mic-v2_0`; button on GPIO_17; APA102 needs SPI; Pi 5 `RPi.GPIO` incompatibility and `gpiozero` alternative |
| S3 | https://github.com/respeaker/seeed-voicecard (`dkms.conf`, `install.sh`, `seeed-2mic-voicecard-overlay.dts`, `Makefile`, `seeed-voicecard.service`) | DKMS 0.3, three modules, in-tree-name collision, boot-file edits, `/etc/modules`, `/etc/voicecard` state, boot service, global-git-config side effect; last commit 2021-11-25 |
| S4 | https://github.com/torvalds/linux/commit/44d0a879951a | TLV320AIC3X codec driver added 2007-11-14 |
| S5 | https://github.com/torvalds/linux/commit/f2644a2c00a0 | WM8960 codec driver added 2009-04-07 |
| S6 | https://deb.debian.org/debian/pool/main/l/linux/linux-config-6.12_6.12.117-1_arm64.deb | arm64 config: `CONFIG_SND_SOC_WM8960=m`, `# CONFIG_SND_SOC_TLV320AIC3X_I2C is not set`, `CONFIG_SND_SIMPLE_CARD=m`, `CONFIG_SND_BCM2835_SOC_I2S=m`, `# CONFIG_SND_DESIGNWARE_I2S is not set` |
| S7 | https://deb.debian.org/debian/pool/main/l/linux/linux-config-6.12_6.12.117-1_armhf.deb | armhf config (armmp, armmp-lpae, rt): `CONFIG_SND_SOC_TLV320AIC3X=m` with `# …_I2C is not set`, `# CONFIG_SND_SOC_WM8960 is not set`, `CONFIG_SND_SIMPLE_CARD=m`, `CONFIG_SND_BCM2835_SOC_I2S=m`, `# CONFIG_SND_DESIGNWARE_I2S is not set` |
| S8 | https://deb.debian.org/debian/pool/main/l/linux/linux-config-6.12_6.12.117-1_armel.deb | armel `rpi` flavour (Pi Zero/1): `# CONFIG_SND_SOC_WM8960 is not set`, `# …_TLV320AIC3X_I2C is not set`, `# CONFIG_SND_SIMPLE_CARD is not set`, `CONFIG_SND_BCM2835_SOC_I2S=m` |
| S9 | https://raw.githubusercontent.com/torvalds/linux/v6.12/arch/arm64/boot/dts/broadcom/bcm2712.dtsi | mainline 6.12 Pi 5 SoC tree: no I²S node (grep for `i2s` returns nothing) |
| S10 | https://github.com/torvalds/linux/tree/v6.17/arch/arm64/boot/dts/broadcom | RP1 device trees (`rp1.dtsi`, `rp1-common.dtsi`, `rp1-nexus.dtsi`, `rp1.dtso`) present at v6.17; absent in the v6.13–v6.16 listings and in v6.12 |
| S11 | https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm64/boot/dts/broadcom/bcm2712-rpi.dtsi and https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm64/boot/dts/broadcom/rp1.dtsi and https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm64/configs/bcm2711_defconfig and https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm/boot/dts/overlays/Makefile | downstream `sound` node and `i2s_clk_producer/consumer` aliases; `rp1_i2s0/1` as `snps,designware-i2s`; defconfig has WM8960/SIMPLE_CARD/DESIGNWARE_I2S=m and no TLV320AIC3x; overlay list has `wm8960-soundcard.dtbo`, not `seeed-2mic-voicecard` |
| S12 | https://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT/ | v1 hardware overview: user button on GPIO17, 3 APA102 RGB LEDs on SPI, WM8960 codec, 3.5 mm and JST 2.0 speaker out |
| S13 | https://raw.githubusercontent.com/respeaker/seeed-voicecard/master/seeed-2mic-voicecard-overlay.dts | v1 overlay: `wlf,wm8960` @0x1a, 12.288 MHz fixed clock, `simple-audio-card` name `seeed-2mic-voicecard`, `slave_overlay` |
| S14 | https://raw.githubusercontent.com/torvalds/linux/v6.12/sound/soc/codecs/Kconfig | hidden `SND_SOC_TLV320AIC3X` selected by `…_I2C`/`…_SPI` glue |
| S15 | https://raw.githubusercontent.com/torvalds/linux/v6.12/sound/soc/codecs/tlv320aic3x.c and https://raw.githubusercontent.com/torvalds/linux/v6.12/sound/soc/codecs/tlv320aic3x-i2c.c | 2-in/2-out DAI; `ti,tlv320aic3104` in the OF table; AIC3104-specific register handling |
| S16 | https://packages.debian.org/trixie/linux-image-arm64 and https://packages.debian.org/trixie/linux-image-rpi | trixie kernel 6.12.117-1; `linux-image-rpi` is the armel Pi Zero/1 flavour |
| S17 | https://github.com/HinTak/seeed-voicecard (`asound_2mic.conf`, `seeed-voicecard`, `seeed-voicecard.service`, `wm8960.c`) | `dmix`/`dsnoop` over `hw:seeed2micvoicec`; boot service re-applying `dtparam`/`dtoverlay`; vendored codec source |
| S18 | https://raw.githubusercontent.com/torvalds/linux/v6.12/sound/soc/codecs/Makefile and https://raw.githubusercontent.com/torvalds/linux/v6.12/sound/soc/codecs/wm8960.c | in-tree module name `snd-soc-wm8960.o`; WM8960 DAI is 1–2 ch each way |
| S19 | https://www.alsa-project.org/alsa-doc/alsa-lib/pcm_plugins.html | `dmix`/`dsnoop`/`dshare` are alsa-lib plugins for userspace sharing and mixing |
| S20 | https://github.com/HinTak/seeed-voicecard and https://github.com/HinTak/seeed-voicecard/blob/master/README.md | HEAD 2026-10-19; commit titles "v6.11: platform_driver::remove() return void", "v6.13: ASoC: rename rtd->num to rtd->id", 2026-07 hardening; `--compat-kernel` guidance; vendor `aplay -l` output showing `card 1: seeed2micvoicec … Subdevices: 1/1`; vendor statement about upstream WM8960 bugs |
| S21 | https://github.com/HinTak/seeed-voicecard/issues/33 | reported module build failure on kernel 6.6.20+rpt-rpi-v8 (aarch64), 2024-04-07 |
| S22 | https://github.com/respeaker/seeed-voicecard/issues/351 | reported installer failure on kernel 6.12.47, kernel-version misdetection and reboot loop, 2025-10-16 |
| S23 | https://github.com/dkms-project/dkms | DKMS semantics: per-kernel rebuild; `AUTOINSTALL` drives rebuild on kernel install |
| S24 | https://docs.pipewire.org/page_objects_design.html | PipeWire object mapping: ALSA card → device, PCM stream → node (+endpoint); on/off fallback profiles |
| S25 | https://docs.pipewire.org/page_man_pipewire-props_7.html | `api.alsa.path`, `api.alsa.card.*`, ACP/UCM profile selection |
| S26 | https://github.com/Seeed-Studio/seeed-linux-dtoverlays/blob/master/overlays/rpi/respeaker-2mic-v1_0-overlay.dts | v1 overlay counterpart in the newer Seeed repo: `wlf,wm8960`, 24 MHz clock, `i2s_clk_consumer` |

---

## Handoff (≤900 words)

### Findings

| Claim | Label | Source URL | Limits |
| --- | --- | --- | --- |
| The v2 HAT's codec is a TLV320AIC3104 at I²C 0x18, 24.576 MHz MCLK, codec is I²S master — not a WM8960 | D | [S1](https://github.com/Seeed-Studio/seeed-linux-dtoverlays/blob/master/overlays/rpi/respeaker-2mic-v2_0-overlay.dts) | From Seeed's overlay; no unit inspected |
| `seeed-voicecard`/DKMS is the **v1 (WM8960)** path | D | [S3](https://github.com/respeaker/seeed-voicecard), [S13](https://raw.githubusercontent.com/respeaker/seeed-voicecard/master/seeed-2mic-voicecard-overlay.dts) | Same |
| TLV320AIC3x codec driver entered mainline in Linux 2.6.25 (`44d0a879951a`) | D | [S4](https://github.com/torvalds/linux/commit/44d0a879951a) | Tag-content check only |
| WM8960 codec driver entered mainline in Linux 2.6.31 (`f2644a2c00a0`) | D | [S5](https://github.com/torvalds/linux/commit/f2644a2c00a0) | Tag-content check only |
| Debian 13 is 6.12.117-1 and **disables** `SND_SOC_TLV320AIC3X_I2C` on arm64, armhf and armel, so the v2 codec cannot bind in-tree | D | [S6](https://deb.debian.org/debian/pool/main/l/linux/linux-config-6.12_6.12.117-1_arm64.deb), [S7](https://deb.debian.org/debian/pool/main/l/linux/linux-config-6.12_6.12.117-1_armhf.deb), [S8](https://deb.debian.org/debian/pool/main/l/linux/linux-config-6.12_6.12.117-1_armel.deb) | Configs only |
| Debian 13 enables `SND_SOC_WM8960=m` on **arm64 only** (not armhf, not armel) | D | [S6](https://deb.debian.org/debian/pool/main/l/linux/linux-config-6.12_6.12.117-1_arm64.deb), [S7](https://deb.debian.org/debian/pool/main/l/linux/linux-config-6.12_6.12.117-1_armhf.deb), [S8](https://deb.debian.org/debian/pool/main/l/linux/linux-config-6.12_6.12.117-1_armel.deb) | Configs only |
| Debian builds `SND_BCM2835_SOC_I2S=m` everywhere but **not** `SND_DESIGNWARE_I2S` | D | [S6](https://deb.debian.org/debian/pool/main/l/linux/linux-config-6.12_6.12.117-1_arm64.deb) | Configs only |
| Mainline 6.12's Pi 5 device tree has no I²S node; RP1 device trees first appear in mainline v6.17 | D | [S9](https://raw.githubusercontent.com/torvalds/linux/v6.12/arch/arm64/boot/dts/broadcom/bcm2712.dtsi), [S10](https://github.com/torvalds/linux/tree/v6.17/arch/arm64/boot/dts/broadcom) | Debian may backport RP1 trees: unverified |
| The Pi 5's I²S is an RP1 DesignWare block (`snps,designware-i2s`) exposed downstream as `i2s_clk_producer/consumer` | D | [S11](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm64/boot/dts/broadcom/rp1.dtsi) | Downstream tree, not mainline |
| Seeed/RPi overlays target downstream-only labels (`&sound`, `&i2s_clk_*`), so they do not apply to a mainline DT as shipped | D | [S1](https://github.com/Seeed-Studio/seeed-linux-dtoverlays/blob/master/overlays/rpi/respeaker-2mic-v2_0-overlay.dts), [S11](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm64/boot/dts/broadcom/bcm2712-rpi.dtsi) | Not applied on a running system |
| The vendor DKMS package installs its codec as `snd-soc-wm8960.ko`, replacing the in-tree module of the same name | D | [S3](https://github.com/respeaker/seeed-voicecard), [S18](https://raw.githubusercontent.com/torvalds/linux/v6.12/sound/soc/codecs/Makefile) | Name identity read from both Makefiles |
| The vendor stack is stale upstream (2021) with an active third-party fork (2026); build failures on 6.6.20, installer failures on 6.12.47 | D/R | [S20](https://github.com/HinTak/seeed-voicecard), [S21](https://github.com/HinTak/seeed-voicecard/issues/33), [S22](https://github.com/respeaker/seeed-voicecard/issues/351) | Two reports; other kernels may differ |
| The v2 vendor path is overlay-only, plus a hand-built copy of the in-tree TI codec driver that Raspberry Pi OS does not enable | D | [S2](https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/), [S11](https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/arch/arm64/configs/bcm2711_defconfig) | From Seeed instructions and defconfig |
| Capture channels lost nothing on either board: AIC3x is fixed 2-in/2-out, WM8960 1–2 ch | D | [S15](https://raw.githubusercontent.com/torvalds/linux/v6.12/sound/soc/codecs/tlv320aic3x.c), [S18](https://raw.githubusercontent.com/torvalds/linux/v6.12/sound/soc/codecs/wm8960.c) | Driver capability, not measured audio |
| LEDs (APA102/SPI) and the button (GPIO17) are userspace and were never in any kernel driver | D | [S12](https://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT/), [S2](https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/) | Vendor docs; not probed |
| Neither codec mixes streams; `dmix`/`dsnoop` are alsa-lib plugins and PipeWire mixes in userspace | D | [S19](https://www.alsa-project.org/alsa-doc/alsa-lib/pcm_plugins.html), [S24](https://docs.pipewire.org/page_objects_design.html) | No concurrent-stream measurement |
| PipeWire sees only an ALSA card with PCM streams; the paths are indistinguishable above ALSA | D | [S24](https://docs.pipewire.org/page_objects_design.html), [S25](https://docs.pipewire.org/page_man_pipewire-props_7.html) | No PipeWire run on the device |
| The onboard TPA2005D1 is downstream of the codec line output; losing vendor mixer state costs tuning, not the amplifier | T (presence, one specimen) / D (state file) | [S17](https://github.com/HinTak/seeed-voicecard), project lab record | No public statement names TPA2005D1 |
| In-tree codec + own overlay is most upgrade-safe; DKMS or copied modules fail silently on kernel change | H (reasoned) | [S2](https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/), [S3](https://github.com/respeaker/seeed-voicecard), [S23](https://github.com/dkms-project/dkms) | Not observed on hardware |

### Traps

1. **Wrong revision, wrong driver.** Running the v1 installer on a v2 board
   deploys a WM8960 overlay for a TLV320AIC3104 board; Seeed warns it corrupts
   current Raspberry Pi OS installs [S2].
2. **Module-name collision.** The vendor codec is `snd-soc-wm8960.ko`, the same
   name as the distro module [S3][S18] — a "successful" DKMS build silently
   replaces the maintained driver.
3. **Overlay unconditional, module conditional.** After a kernel upgrade the DT
   still advertises the card; if the module did not rebuild, the failure looks
   like "no sound card", not a broken overlay.
4. **armhf/armel are not smaller arm64.** WM8960 is off on both; trixie armhf is
   ARMv7-only, so the ARMv6 Pi Zero/Zero W needs the separate armel `rpi`
   flavour [S7][S8][S16].
5. **Pi 5 ≠ Pi 4 for audio.** No mainline RP1/I²S device tree in 6.12 and no
   DesignWare I²S driver built by Debian [S9][S10][S6].
6. **Legacy boot lines.** Seeed's v2 page says `dtoverlay=i2s-mmap` is
   unnecessary after 4.0 [S2]; the v1 script still writes it [S3].
7. **Installer side effects.** The v1 script runs `apt-get`, rewrites
   `config.txt`, and can set the operator's global git identity [S3].

### Unknowns / blocked

- Whether Debian's 6.12 source backports RP1 device trees, i.e. whether a
  Debian 13 Pi 5 can present any I²S card — `U`.
- Whether the in-tree TLV320AIC3x driver works with this board's 24.576 MHz
  MCLK and codec-master clocking — `U`.
- Whether either `seeed-voicecard` repo builds against Debian's
  `linux-headers-6.12.117` — `U`.
- Whether a mainline-style overlay on `i2s` produces a working card on
  Debian 13 — `U`.
- Which overlays Debian's `raspi-firmware` package ships — `U` (file list
  unparsable; no page was blocked otherwise).

### One next bounded check

On a **spare** Debian 13 arm64 install (not the lab device; no kernel change,
no installs): `modinfo snd-soc-wm8960` and
`modinfo snd-soc-tlv320aic3x-i2c`, then
`dtc -I dtb -O dts /usr/lib/linux-image-6.12.*/broadcom/bcm2712-rpi-5-b.dtb | grep -i i2s`.
That turns three `U` rows into facts — which codec the kernel can load and
whether the Pi 5 transport exists in Debian's shipped DT — with no appliance
contact and no build.
