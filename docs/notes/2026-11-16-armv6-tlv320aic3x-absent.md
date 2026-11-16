---
title: The armv6 kernel has no ReSpeaker v2 codec driver, and the v1 overlay is the one that ships
date: 2026-11-16
type: project-learning
status: unreviewed
task: unauthored — device bring-up directed by James in session
author: OpenCode session
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - Pi Zero W Rev 1.1 at 192.168.0.70, Raspbian 13 (trixie), kernel 6.18.50+rpt-rpi-v6, observed 2026-11-16
  - /boot/config-6.18.50+rpt-rpi-v6 on the device, read 2026-11-16
  - /lib/modules/6.18.50+rpt-rpi-v6 on the device, read 2026-11-16
  - docs/testing/results/2026-11-15-pi5-respeaker-v2-audio.md (arm64 comparison, 2026-11-15)
  - docs/notes/2026-11-15-respeaker-trixie-driver.md (codec-per-revision research, 2026-11-15)
  - Seeed-Studio/seeed-linux-dtoverlays, overlays/rpi/respeaker-2mic-v2_0-overlay.dts, fetched 2026-11-16
supersedes: []
---

# The armv6 kernel has no ReSpeaker v2 codec driver

## Summary

On the original Pi Zero W, the ReSpeaker 2-Mics Pi HAT **v2.0** works, but only
after two out-of-tree artefacts are supplied by hand: the TLV320AIC3104 codec
driver and Seeed's device-tree overlay. Neither is in the image, and the overlay
that *is* in the image belongs to the **v1** board.

The arm64 Pi 5 kernel ships the driver (`=m`). The armv6 kernel does not:
`CONFIG_SND_SOC_TLV320AIC3X_I2C is not set`. This is a per-architecture config
difference inside the same Raspberry Pi kernel package line, so a Pi 5 result
does not transfer to a Zero W for this HAT — which is the general shape of the
ARMv6 risk the project already tracks.

## Claims and evidence

| Kind | Claim | Source / scope | Verification and limits |
| --- | --- | --- | --- |
| observed | The attached HAT is the **v2.0** board (TLV320AIC3104), not v1 (WM8960) | Pi Zero W, 2026-11-16 | `i2cdetect -y 1` answers at **0x18** and nothing answers at 0x1a. Decisive between the two revisions, and it matches the address in the [driver note](2026-11-15-respeaker-trixie-driver.md) |
| observed | The armv6 kernel does not build the codec's I²C glue | `/boot/config-6.18.50+rpt-rpi-v6` | `CONFIG_SND_SOC_TLV320AIC3X_I2C is not set`; `find /lib/modules/... -name '*aic3x*'` returns nothing. By contrast the Pi 5's `rpt-rpi-2712` config has `=m` |
| observed | The image's only matching overlay is the **v1** one | `/boot/firmware/overlays/` | `wm8960-soundcard.dtbo` present; no ReSpeaker overlay of any revision |
| observed | A two-module out-of-tree build fixes the driver gap | Pi Zero W, 2026-11-16 | Built `snd-soc-tlv320aic3x.ko` + `snd-soc-tlv320aic3x-i2c.ko` against the installed `linux-headers-6.18.50+rpt-rpi-v6` in **75 s natively on the board**. Codec then probes at `1-0018` |
| observed | Seeed's DT-only overlay applies unmodified on bcm2835 | Pi Zero W, 2026-11-16 | Compiled `respeaker-2mic-v2_0-overlay.dts` with `dtc -@`; resulting SHA-256 `ff25ac56…` is **identical** to the Pi 5 build recorded on 2026-11-15, so the overlay is bit-reproducible across architectures |
| observed | The card enumerates and captures and plays | Pi Zero W, 2026-11-16 | `seeed2micvoicec` at ALSA card 0; see the [bring-up result](../testing/results/2026-11-16-zero-w-bringup.md) for the measured tone response |
| hypothesis | The regulator warnings are benign on this board too | Inferred from the Pi 5 run | `supply IOVDD/DVDD/AVDD/DRVDD not found, using dummy regulator` appears identically; the Pi 5 precedent says it is not a fault, and audio works here |

## Detail: why the build is small

The driver is ordinary mainline code; only the kernel's *config* omits it. So
`make -C /lib/modules/$(uname -r)/build M=$PWD modules` against the distro
headers is enough — no kernel rebuild, no DKMS, no vendor package. The three
files needed are `tlv320aic3x.c`, `tlv320aic3x-i2c.c` and `tlv320aic3x.h` from
`raspberrypi/linux` at the matching series, plus a three-line `Makefile`.

The modules are therefore **out-of-tree and unsigned**, and the kernel records
`taints kernel` on load. Any future Debra image should decide deliberately
between carrying these modules and building a kernel with the config enabled;
a DKMS package would at least rebuild them on kernel upgrade, which a copied
`.ko` in `/lib/modules` will not.

## Verification

- Safe commands, run on the board: `i2cdetect -y 1`; `grep TLV320AIC3X
  /boot/config-$(uname -r)`; `make -C /lib/modules/$(uname -r)/build M=$PWD
  modules`; `dtc -@ -I dts -O dtb -o respeaker-2mic-v2_0.dtbo <overlay>.dts`.
- Observed results: driver built and loads, overlay applies at boot, card
  present at card 0, capture and playback measured.
- Not tested: a kernel upgrade (the modules would need rebuilding and the
  overlay re-checking); the LED and button paths; whether a Debian-packaged
  kernel (rather than Pi OS's) has the same config.
- Sanitized artifacts: none committed; the built `.ko` files and `.dtbo` are on
  the device under `~/tlv320-build/` and `/boot/firmware/overlays/`.

## Handoff and correction links

- Base: `51465fa` plus the in-flight `control/*` changes owned by another
  session, which this work did not touch.
- Next action: decide the durable home for the two modules (DKMS package vs
  patched kernel config) before this is turned into an image step. That is a
  roadmap/packet decision, not something this note authorizes.
- Authorization: James directed the bring-up of this specific board. Nothing
  here authorizes flashing, repartitioning, or changing another device.
