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
| T | Debra device test — the lab Pi 5 specimen (two records: audio bring-up, then the voice/music stack) | [audio](../testing/results/2026-11-15-pi5-respeaker-v2-audio.md) and [LVA + Sendspin](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md) | 2026-11-15 | Card `seeed2micvoicec`, TLV320AIC3104 at I²C 0x18, measured capture/playback levels, mixer traps, overlay hashes, acoustic path confirmed by ear; then linux-voice-assistant `v1.1.18` and Sendspin `9.1.0` installed and observed working on the same specimen. One board, not a supported appliance |
| S10 | FutureProofHomes — Satellite1.1 HAT Board, product data (`.js` endpoint; the HTML page blocks plain fetch) | https://futureproofhomes.net/products/satellite1-1-hat-board | 2026-11-15 | $54.99 USD, SKU FPH-SAT1.1-HAT, 31 g, 88 × 88 × 10 mm, XU316 16-core @800 MHz with 1024 KB SRAM / 8 MB flash, 4× PDM MEMS, 24× WS2812, 4 buttons with one hardware mute, PCM5122 line out, TAS2780 25 W mono, FUSB302 USB-C PD up to 100 W, AHT20 + LTR-303ALS, LD2410/LD2450, 40-pin GPIO, "up to 30 W" assembly, 30 W 20 V supply recommended, listed available |
| S11 | FutureProofHomes docs — Satellite1 Dev Kit introduction | https://docs.futureproofhomes.net/satellite1-introduction/ | 2026-11-15 | spec comparison against Voice PE: four microphones but "XMOS firmware uses two microphones currently", 25 W amp with 48 kHz streaming and a 3.5 mm jack, 24 LEDs, temp/humidity/lux, USB-C PD, requires Home Assistant and 2.4 GHz Wi-Fi |
| S12 | FutureProofHomes — Satellite1.1 Dev Kit (DIY), product data | https://futureproofhomes.net/products/satellite1-pcb-dev-kit | 2026-11-15 | $69.99 USD, SKU FPH-SAT1-DK-US, 44 g, orders from 2026-02-17 ship the 1.1 design, listed available; the marketing description still says "Snapcast multi-room" although the current firmware streams with Sendspin [S15] |
| S13 | FutureProofHomes — Satellite1.1 Smart Speaker, product data | https://futureproofhomes.net/products/satellite1-smart-speaker | 2026-11-15 | $132.99 USD (EU/UK SKUs), $134.99 US, pre-assembled, "works with Home Assistant and Music Assistant", listed available |
| S14 | FutureProofHomes — Satellite1.1 Core Board, product data | https://futureproofhomes.net/products/satellite1-1-core-board | 2026-11-15 | $24.99 USD, SKU FPH-SAT1.1-CORE, 13 g, ESP32-S3 N16-R8 dual-core LX7 @240 MHz, 384 KB ROM / 512 KB SRAM / 16 MB flash / 8 MB PSRAM, Raspberry Pi Zero form factor that "supports most Raspberry Pi HATs", external antenna required, Wi-Fi 2.4 GHz + BLE 5 |
| S15 | FutureProofHomes docs — Streaming Music | https://docs.futureproofhomes.net/satellite1-streaming-music/ | 2026-11-15 | "The latest firmware uses Sendspin" and it "works out of the box with Music Assistant — no additional provider setup, port configuration, or server installation"; single speaker, stereo pair and multi-room groups; upgrade steps for v0.1.x Snapcast users; MA DSP/EQ guidance; vendor's own limits on voice control of music |
| S16 | Satellite1-ESPHome — `config/common/voice_assistant.yaml` (develop) | https://github.com/FutureProofHomes/Satellite1-ESPHome/blob/develop/config/common/voice_assistant.yaml | 2026-11-15 | `micro_wake_word` with `hey_jarvis.json`, `okay_nabu.json` and a `stop` model fetched from the vendor's asset bucket |
| S17 | Satellite1-ESPHome — releases | https://github.com/FutureProofHomes/Satellite1-ESPHome/releases | 2026-11-15 | latest v0.2.2-beta.0 (2026-11-13), last stable v0.2.1 (2026-09-17), before that v0.2.1-beta.0 (2026-08-05) |
| S18 | Satellite1-XMOS — releases | https://github.com/FutureProofHomes/Satellite1-XMOS/releases | 2026-11-15 | latest v1.1.0-beta.1 (2026-11-13), v1.1.0-beta.0 (2026-11-10); the report states no stable release since v1.0.3 on 2025-08-06 |
| S19 | FutureProofHomes docs — Smart Speaker and Enclosure Kit | https://docs.futureproofhomes.net/satellite1-smart-speaker/ | 2026-11-15 | kit parts: 3" woofer 15 W RMS / 20 W peak 4 Ω, 1.2" neodymium tweeter, passive 2-way crossover, JST-XH cable, M3×10 screws; printed PETG enclosure (0.4 mm nozzle, 3 walls, 30 %/15 % infill, no supports) published as 3MF/STL/STEP; 30 W USB-C supply; drivers not sold separately; "at full volume the wake word may not be heard perfectly" |
| S20 | home-assistant-voice-pe — release 25.12.0 | https://github.com/esphome/home-assistant-voice-pe/releases/tag/25.12.0 | 2026-11-15 | published 2025-12-17; the only line about audio transport is "Add support for Sendspin multi-room audio protocol (public preview, works with Music Assistant)"; re-read directly |
| S21 | ESPHome — `sendspin` component | https://esphome.io/components/sendspin/ | 2026-11-15 | the Sendspin media source and hub components, codecs, and that the component is new; used for "MA's Sendspin support is beta" |
| S22 | M5Stack esphome-yaml — VoiceS3R satellite base | https://raw.githubusercontent.com/m5stack/esphome-yaml/main/common/atom-voices3r-satellite-base.yaml | 2026-11-15 | contains a `sendspin` hub, a `sendspin` media source with `codecs: [FLAC, PCM]`, a `sendspin` group media player and a 48 kHz stereo `speaker_source`; re-read directly. The file names ESPHome 2026.10.0 while the vendor page [S7] says 2026.1.0 |
| S23 | wake-word-voice-assistants — ESP32-S3-BOX-3 configuration | https://github.com/esphome/wake-word-voice-assistants/blob/main/esp32-s3-box-3/esp32-s3-box-3.yaml | 2026-11-15 | stock upstream config is an announcement pipeline only: no Sendspin, no `speaker_source` media pipeline |
| S24 | Tater Home Assistant Satellites (third-party firmware) | https://github.com/TaterTotterson/Tater-Home-Assistant-Satellites | 2026-11-15 | claims a Sendspin player on BOX-class hardware; no upstream endorsement, no listening test found |
| S25 | Seeed wiki — ReSpeaker Lite with Home Assistant | https://wiki.seeedstudio.com/respeaker_lite_ha/ | 2026-11-15 | flash the 48 kHz XMOS I2S firmware, version ≥ 1.1.0, before any Sendspin use; points at the community ESPHome config [S26] |
| S26 | formatBCE — Respeaker-Lite-ESPHome-integration | https://github.com/formatBCE/Respeaker-Lite-ESPHome-integration | 2026-11-15 | community-maintained ESPHome config with Sendspin and a 48 kHz media pipeline; not vendor firmware |
| S27 | Seeed wiki — reSpeaker USB 4-Mic Array / USB sound card | https://wiki.seeedstudio.com/reSpeaker_usb_v3/ | 2026-11-15 | UAC2 plug-and-play card with speaker and 3.5 mm output; the published spec tops out at 16 kHz sample rate |
| S28 | Seeed wiki — ReSpeaker Lite on Raspberry Pi 5 | https://wiki.seeedstudio.com/respeaker_lite_pi5/ | 2026-11-15 | Pi 5 guide pins the card to a 16 kHz clock and uses `aplay`; no protocol on the device |
| S29 | Seeed wiki — ReSpeaker 2-Mics Pi HAT (Raspberry Pi v2) | https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/ | 2026-11-15 | ALSA card, 48 kHz maximum; music only through host software; the page names WM8960 while its own `aplay` output shows `tlv320aic3x` |
| S30 | Snapcast | https://github.com/badaix/snapcast | 2026-11-15 | synchronised multi-room client/server, the mature alternative to Sendspin |
| S31 | shairport-sync | https://github.com/mikebrady/shairport-sync | 2026-11-15 | AirPlay receiver for a Linux host |
| S32 | Music Assistant — Local Audio player | https://www.music-assistant.io/player-support/local-audio/ | 2026-11-15 | MA's own on-host player, successor to the retired "Local Audio Out", still experimental; the HA player provider defaults to MP3 and cannot synchronise with other players |
| S33 | Satellite1-ESPHome — release v0.2.0 | https://github.com/FutureProofHomes/Satellite1-ESPHome/releases/tag/v0.2.0 | 2026-11-15 | published 2026-05-28; Sendspin replaces Snapcast, and the upgrade note says old Snapcast players must be deleted rather than upgraded |
| S34 | Satellite1-ESPHome — issue 521 | https://github.com/FutureProofHomes/Satellite1-ESPHome/issues/521 | 2026-11-15 | announcements regressed after the Sendspin change; the vendor's own bug report |
| S35 | ameriDroid — Home Assistant Voice Preview Edition | https://ameridroid.com/products/home-assistant-voice-preview-edition/ | 2026-11-15 | $58.95 USD, pre-order with no restock date in R02 |
| S36 | CloudFree — Home Assistant Voice Preview Edition | https://cloudfree.shop/product/home-assistant-voice-preview-edition/ | 2026-11-15 | $58.95 USD, sold out in R02 |
| S37 | Seeed — Home Assistant Voice Preview Edition | https://www.seeedstudio.com/Home-Assistant-Voice-p-6998.html | 2026-11-15 | $59 USD, maximum two per account; stock not confirmed in R02 |
| S38 | M5Stack shop — Atom VoiceS3R | https://shop.m5stack.com/products/atom-echos3r-smart-speaker-dev-kit | 2026-11-15 | $14.50 USD; conflicting stock readings in R02 |
| S39 | PCMag — Amazon Echo Dot fifth-generation review | https://www.pcmag.com/reviews/amazon-echo-dot-5th-gen | 2026-11-15 | $79.99 USD list price reported in R02; review dated 2026-06-16 |
| S40 | Music Assistant — Alexa player support | https://www.music-assistant.io/player-support/alexa/ | 2026-11-15 | Experimental self-hosted Alexa skill route and prerequisites, as recorded in R02 |
| S41 | Home Assistant — Alexa Devices integration | https://www.home-assistant.io/integrations/alexa_devices/ | 2026-11-15 | Alexa integration limitations and cloud polling, as recorded in R02 |
| S42 | Orange Pi wiki — Zero 2W | http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_Zero_2W | 2026-11-15 | V1.1 header table: I2C on 3/5 and no listed I2S function, per R07 |
| S43 | Orange Pi wiki — Zero 3 | http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_Zero_3 | 2026-11-15 | 26-pin and 13-pin headers; no direct 40-pin HAT fit, per R07 |
| S44 | Orange Pi wiki — 3B | http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_3B | 2026-11-15 | 40-pin header; detailed pin table published as images and not evaluated in R07 |
| S45 | Radxa docs — ZERO 3W hardware interface | https://docs.radxa.com/en/zero/zero3/hardware-design/hardware-interface | 2026-11-15 | I2S pins, UART on 3/5 in pin table, I2C4 on 27/28; page has a pin-description conflict, per R07 |
| S46 | Radxa docs — ROCK 3C hardware interface | https://docs.radxa.com/en/rock3/rock3c/hardware-design/hardware-interface | 2026-11-15 | I2S and I2C header positions; matching positions do not establish HAT support, per R07 |
| S47 | Libre Computer forum — Le Potato overview and guides | https://hub.libre.computer/t/aml-s905x-cc-le-potato-overview-resources-and-guides/288 | 2026-11-15 | I2S header availability reports for original Le Potato, per R07 |
| S48 | Apple — HomePod mini | https://www.apple.com/shop/buy-homepod/homepod-mini | 2026-11-15 | HomePod mini 2 $149 USD price and setup requirements, as recorded in R02 |
| S49 | Music Assistant — AirPlay player support | https://www.music-assistant.io/player-support/airplay/ | 2026-11-15 | HomePod AirPlay player path, as recorded in R02 |
| S50 | Libre Computer — AML-S905X-CC V2 | https://libre.computer/products/aml-s905x-cc-v2/ | 2026-11-15 | Separate V2 I2S header, from a search-result extract; page body was JS-rendered in R07 |
| S51 | Nabu Casa — Voice Preview Edition getting started | https://support.nabucasa.com/hc/en-us/articles/25918770371229 | 2026-11-15 | USB-C power supply and cable not included, as recorded in R02 |
| S52 | Engadget — Google discontinues Nest Mini and Nest Audio | https://www.engadget.com/2197748/google-has-discontinued-the-nest-home-mini-and-nest-audio | 2026-11-15 | Google Home Speaker and Gemini-for-Home, reported in R02; article dated 2026-06-18 |

`T` is the only source in this register that is a Debra observation rather than a
third-party page. The others include vendor, upstream and attributed secondary
sources; none of their claims has been reproduced on Debra hardware here.

## What the register deliberately does not hold

- **Fetch failures.** Traps are recorded in the report that hit them, for example
  the 404s on `/en/core/ATOM%20Echo` and `/en/core/atom_echo`, or the Espressif
  BOX-3 user guide. A URL that did not resolve is not evidence and gets no key.
- **Prices without a date.** A price is a snapshot; the cell and the entry both
  carry the date read.
- **Unattributed secondary claims.** Secondary pages are labeled as reports;
  where a shop listing and a datasheet disagree, both are kept as separate keys
  rather than averaged.

## Adding a source

1. Add the row with the next key and the date the page was actually read.
2. Use that key in the cell it supports, with a label (`D`, `R`, `H`, `U`).
3. If the page later moves or changes, do not silently rewrite the claim: add a
   new key with the new date and note the change.
