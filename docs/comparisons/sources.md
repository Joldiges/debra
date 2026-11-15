# Source register

Numbered sources for [devices.md](devices.md). Every `[S#]` in a cell must have an
entry here, with its full URL and the date the page was read. A key with no entry
makes the cell unusable.

| Key | Source | URL | Read | Covers |
| --- | --- | --- | --- | --- |
| S1 | Home Assistant — Voice Preview Edition product and FAQ | https://www.home-assistant.io/voice-pe/ | 2026-11-15 | ESP32-S3 / XMOS XU316 / AIC3204, 48 kHz dual mic, speaker-is-feedback-only, microWakeWord model list, dimensions and weight, $69 / €59 MSRP, distributor list |
| S2 | ESPHome — ready-made projects, Voice Assistant | https://esphome.io/projects/?type=voice | 2026-11-15 | Which devices ESPHome offers a project for, including the Sendspin player target |
| S3 | ESPHome — ESP32-S3-BOX-3 device configuration | https://github.com/esphome/esphome/blob/dev/esphome/components/esp32_s3_box_3/esp32-s3-box-3.yaml | 2026-11-15 | ES7210 ADC, ES8311 DAC, 48 kHz, speaker-enable GPIO, 16 MB flash / octal PSRAM |
| S4 | M5Stack shop — ATOM Voice (C008-C), formerly "ATOM Echo" slug | https://shop.m5stack.com/products/atom-echo-smart-speaker-dev-kit | 2026-11-15 | ESP32-PICO-D4, 4 MB flash, no PSRAM, NS4168 0.8 W amp, SPM1423 PDM mic, SK6812 LED, 24×24×17 mm, $13.50 USD, "10+ in stock", "kind of quiet" review |
| S5 | ESPHome — `m5stack-atom-echo` wake-word configuration | https://github.com/esphome/wake-word-voice-assistants/blob/main/m5stack-atom-echo/m5stack-atom-echo.yaml | 2026-11-15 | Single PDM mic, 16 kHz, gain ×4, on-device versus HA wake word select |
| S6 | M5Stack documentation — Atom VoiceS3R (C126-ECHO) | https://docs.m5stack.com/en/core/Atom_VoiceS3R | 2026-11-15 | ESP32-S3-PICO-1-N8R8, 8 MB flash / 8 MB octal PSRAM, ES8311 mono codec, one MEMS mic at 65 dB SNR, NS4150B with 8 Ω 1 W, 24×24×16.8 mm, 9.3 g |
| S7 | M5Stack documentation — VoiceS3R Home Assistant application | https://docs.m5stack.com/en/homeassistant/applications/voice_assistant/atom_echos3r | 2026-11-15 | ESPHome ≥2026.1.0, "Okay Nabu", HA discovery; shows no music path |
| S8 | linux-voice-assistant (OHF-Voice) README | https://github.com/OHF-Voice/linux-voice-assistant | 2026-11-15 | linux/amd64 + linux/aarch64 only, 16 kHz mono mic, 1 GHz / 512 MB floor, on-device OWW/MWW, Pi Zero 2 W + Satellite1 HAT recommendation, ReSpeaker Lite "currently problematic" on Zero 2 W, 2-Mics Pi HAT described as a much more basic codec |
| S9 | Espressif — development kit product tables | https://www.espressif.com/en/products/devkits | 2026-11-15 | ESP32-S3-BOX-3 "sample price for reference" $49; older BOX and BOX-Lite marked no longer for sale |
| T | Debra device test — Pi 5 + ReSpeaker 2-Mics Pi HAT v2.0 audio | [../testing/results/2026-11-15-pi5-respeaker-v2-audio.md](../testing/results/2026-11-15-pi5-respeaker-v2-audio.md) | 2026-11-15 | Card `seeed2micvoicec`, TLV320AIC3104 at I²C 0x18, measured capture/playback levels, mixer traps, overlay hashes, acoustic path confirmed by ear |

`T` is the only source in this register that is a Debra observation rather than a
third-party page. Everything else is what a vendor or upstream project publishes;
none of it has been reproduced on Debra hardware.

## What the register deliberately does not hold

- **Fetch failures.** Traps are recorded in the report that hit them, for example
  the 404s on `/en/core/ATOM%20Echo` and `/en/core/atom_echo`, or the Espressif
  BOX-3 user guide. A URL that did not resolve is not evidence and gets no key.
- **Prices without a date.** A price is a snapshot; the cell and the entry both
  carry the date read.
- **Aggregated or secondary pages.** Where a shop listing and a datasheet
  disagree, both are kept as separate keys rather than averaged.

## Adding a source

1. Add the row with the next key and the date the page was actually read.
2. Use that key in the cell it supports, with a label (`D`, `R`, `H`, `U`).
3. If the page later moves or changes, do not silently rewrite the claim: add a
   new key with the new date and note the change.
