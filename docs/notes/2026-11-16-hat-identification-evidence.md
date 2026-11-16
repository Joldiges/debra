---
title: What a Pi can actually learn about the audio HAT fitted to it
date: 2026-11-16
type: project-learning
status: unreviewed
task: unauthored — question from James in session
author: OpenCode session
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - "Pi 5 `debra-3c6b3f`, Pi Zero 2 W `debra-8518d6`, Pi Zero W `debra-f943dc`, read 2026-11-16"
  - "control/web/hats.py and control/web/server.py in this checkout"
  - "ReSpeaker 2-Mics Pi HAT v1 (WM8960) and v2 (TLV320AIC3104) as fitted to the lab boards"
---

# What a Pi can actually learn about the audio HAT fitted to it

## The question

James asked whether other HATs carry an EEPROM the Pi can read, whether there is
any way to probe what is fitted, and whether playing a tone and listening for it
would work as identification. The short answers: the mechanism exists in the
platform but **none of the three lab boards has it**; I²C probing identifies the
**codec family** and often settles v1 versus v2; and play-and-listen is a
verification step, not identification, for reasons given below.

## No EEPROM on any of the three boards

The Raspberry Pi HAT specification puts an ID EEPROM on the HAT, which the
firmware exposes as `/sys/firmware/devicetree/base/hat/`. That is the only
evidence `control/web` reads today (`detected_hat`). Read directly:

| Board | `/sys/firmware/devicetree/base/hat/` | ALSA card 0 | I²C device | Bound driver |
| --- | --- | --- | --- | --- |
| Pi 5 `debra-3c6b3f` | **absent** | `seeed2micvoicec` | `1-0018` | `tlv320aic3x` |
| Zero 2 W `debra-8518d6` | **absent** | `wm8960soundcard` | `1-001a` | `wm8960` |
| Zero W `debra-f943dc` | **absent** | `seeed2micvoicec` | `1-0018` | `tlv320aic3x` |

So the page's `detected_hat` is `null` on every board in the lab, including the
Pi 5 with the Seeed v2 HAT. That is not a bug in the reader; the node genuinely
does not exist. The earlier note in `hats.py` that "Seeed's EEPROM product string
for the 2-Mics HAT does not carry [a revision]" is consistent with this but
understates it: on these boards there is no product string at all.

## What probing does tell you

The codec is real hardware and answers on I²C, so it is evidence in a way an
absent EEPROM cannot be:

- **`1-0018` + `tlv320aic3x`** is a TLV320AIC310x codec at address `0x18`.
- **`1-001a` + `wm8960`** is a WM8960 at address `0x1a`.

That separates the two boards we own: the Pi 5 and the Zero W both show the
TLV320AIC310x path (ReSpeaker 2-Mics **v2**), and the Zero 2 W shows the WM8960
path (ReSpeaker 2-Mics **v1**). It cannot settle the WM8960 case alone, because
the Waveshare WM8960 Audio HAT is the same codec and also creates the
`wm8960soundcard` card; `hats.py` already says the driver "does not say which one
is fitted".

The ALSA card name is weaker than it looks: it is created by whichever overlay is
installed, so it reports our own configuration as much as the hardware. The I²C
answer is the part that comes from the board.

What this supports is a **fused verdict with a stated confidence**, not a single
magic read:

| Evidence | Honest conclusion |
| --- | --- |
| Device at `0x18` bound by `tlv320aic3x` | a TLV320AIC310x codec is fitted; consistent with ReSpeaker 2-Mics v2 |
| Device at `0x1a` bound by `wm8960` | a WM8960 codec is fitted; Seeed v1 **or** Waveshare WM8960, undecided |
| No codec on I²C, no audio card | no audio HAT driver is bound — possibly none fitted, possibly the overlay is missing |
| HAT EEPROM present | would name vendor/product if a spec-compliant HAT were fitted; none is |

## Why play-and-listen is not identification

The idea works mechanically — `tools/audio_selftest.py` already plays and records
on a device — but as an *identifier* it fails in four ways:

1. **It needs the answer to be right already.** Playing audio requires the
   correct overlay, driver and mixer state. On a board whose HAT is unknown,
   those are the things being determined.
2. **It is audible.** Automatic identification at boot or on page load would
   make a tone in the room, which is exactly the kind of write the web control
   README forbids as a deployment test.
3. **A tone proves less than it appears to.** Any working codec passes. It cannot
   separate Seeed v1 from Waveshare, and a broken speaker or a muted mixer
   produces a failure that looks identical to "wrong HAT".
4. **It cannot run at install time either**, because the install is what makes
   playback possible.

So the useful shape is: identify from I²C and device-tree evidence, then offer a
play/capture check as a **verification** the person asks for, with the result
reported as "audio path works" or "audio path not verified", never as "this is
board X".

## What this changes

- `control/web` reports `detected_hat` from the EEPROM only, so on the lab fleet
  it always reports `null`. That is a visible per-board gap for the "all the
  hats" goal, and WEB03 in the roadmap is the packet that owns it.
- The available improvement is a codec probe (`/sys/bus/i2c/devices/*`, the bound
  driver, `/proc/asound/cards`) presented as evidence with its ambiguity stated,
  not as a product name.
- Nothing here was measured beyond reading those files: no overlay change, no
  audio played, no capture, and no board was rebooted.
