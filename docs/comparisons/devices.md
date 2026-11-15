# Master device table

One row per exact variant. Cells carry `value [S# label]`; see
[README.md](README.md) for the tags and [sources.md](sources.md) for the
register. All sources checked 2026-11-15 unless the cell says otherwise.

## Complete devices and near-complete kits

| Device (exact variant) | SoC / audio silicon | Microphone topology | Speaker output | On-device wake word | Home Assistant path | Music playback | Architecture | Price, market, date | Availability | Maintenance burden | Weakest cell |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Home Assistant Voice PE** (official) | ESP32-S3, 16 MB flash, 8 MB octal PSRAM; XMOS XU316 for audio; AIC3204 DAC [S1 D] | dual microphones, 48 kHz [S1 D]; array geometry `U` | built-in speaker is **voice feedback only**; music needs a 3.5 mm external speaker [S1 D] | microWakeWord on-device; "Okay Nabu", "Hey Jarvis", "Hey Mycroft" [S1 D] | first-party: HA Voice Assistant, ESPHome firmware [S1 D] | listed as a Sendspin player target in ESPHome's ready-made projects [S2 D]; playback not demonstrated here `U` | ESP32-S3 (Xtensa) [S1 D] | $69 MSRP USD excl. tax; €59 [S1 D] | distributor list incl. EU/UK/US [S1 D]; no stock check | first-party hardware and firmware [S1 D] | music: project listing, not a test |
| **M5Stack ATOM Voice** (C008-C) | ESP32-PICO-D4, 4 MB flash, no PSRAM; NS4168 0.8 W I²S amplifier [S4 D] | single SPM1423 PDM microphone [S4 D] | NS4168, 0.8 W into the built-in speaker [S4 D] | on-board **or** HA-server wake word, selectable [S5 D] | ESPHome YAML in the official wake-word repo [S5 D] | `U` — no music path documented | ESP32 (Xtensa) [S4 D] | $13.50 USD, M5Stack shop [S4 D] | "10+ in stock" on 2026-11-15 [S4 D] | small, single-vendor; firmware examples are ESPHome's, not M5Stack's [S5 D] | music `U`; speaker "kind of quiet" [S4 R] |
| **M5Stack Atom VoiceS3R** (C126-ECHO) | ESP32-S3-PICO-1-N8R8, 8 MB flash, 8 MB octal PSRAM; ES8311 mono codec; NS4150B amplifier [S6 D] | **one** MEMS microphone, 65 dB SNR [S6 D] — "two mics" branding does not apply to this SKU | 8 Ω 1 W via NS4150B [S6 D] | "Okay Nabu" via ESPHome, ≥2026.1.0 [S7 D] | vendor-maintained HA/ESPHome application page [S7 D] | `U` — no music path shown [S7 D] | ESP32-S3 [S6 D] | `U` — price not captured | `U` | vendor page only; no upstream project listed [S7 D] | price and music both `U` |
| **ESP32-S3-BOX-3** | ES7210 ADC (dual mic) + ES8311 DAC, 48 kHz out [S3 D] | dual microphone via ES7210 [S3 D] | speaker enable GPIO, onboard speaker [S3 D] | ESPHome wake-word project [S2 D] | ESPHome project target [S2 D] | `U` | ESP32-S3 [S3 D] | sample price $49 USD reference [S9 D] | older BOX/-Lite listed "no longer for sale" [S9 D] | Espressif devkit, ESPHome support [S3 D] | silicon details come from a config file, not a datasheet, and no seller stock was checked |
| **ReSpeaker Lite, USB 2-Mic Array** (107990273) | XMOS XU316 DSP, **no application SoC, no Wi-Fi** `H` — report received without resolvable sources | 2 digital MEMS mics `H` | 5 W speaker output `H` | hosted (LVA/HA), none on board `H` | host-side only `H` | `U` | USB UAC2 device `H` | $24.90 USD Seeed `H` | `U` | `U` | **entire row is unreviewed**: the report's source keys were never defined, so it is being re-run |
| **ReSpeaker Lite Voice Kit** (XIAO ESP32S3, 110061601) | ESP32-S3 + XU316 `H` | as above `H` | as above `H` | microWakeWord on-device `H` | ESPHome + third-party firmware `H` | claimed yes with 48 kHz firmware `H` | ESP32-S3 | $29.90 USD Seeed `H` | `U` | `U` | **unreviewed**, same reason |
| **Raspberry Pi 5 + ReSpeaker 2-Mics Pi HAT v2.0** (Debra lab) | Pi 5 (BCM2712), aarch64; TLV320AIC3104 codec at I²C 0x18 [T] | stereo capture, two mics; **which mic feeds which channel `U`** [T] | headphone/JST output through the codec's HP amp; speaker→air→mic path measured [T] | none on the HAT; host-side (LVA/HA) `U` | no Debra stack installed yet `U` | `U` — nothing tested | aarch64 + I²S HAT [T] | HAT price `U`; Pi 5 price `U` | lab unit owned | stock kernel already ships the codec driver; overlay must be built and pinned [T] | music and HA integration untested; only the audio path is `T` |

## Capability summary

The three columns people actually decide on. Everything here is a restatement of
the table above, not new evidence.

| Device | Voice assistant | Music player | Reuse of parts Debra already has |
| --- | --- | --- | --- |
| HA Voice PE | first-party, best supported [S1 D] | external speaker required [S1 D]; Sendspin target [S2 D] | no |
| ATOM Voice (C008-C) | yes, cheap [S4 D][S5 D] | `U` | no |
| Atom VoiceS3R (C126-ECHO) | yes [S7 D] | `U` | no |
| ESP32-S3-BOX-3 | yes [S2 D] | `U` | no |
| ReSpeaker Lite (both) | `U` pending re-run | `U` pending re-run | no |
| Pi 5 + ReSpeaker 2-Mics v2 | `U` — not installed | `U` | **yes**: Pi 5 and HAT already in hand [T] |

## Open questions worth money

| Question | Why it blocks a decision | Where it will be answered |
| --- | --- | --- |
| Can a Pi + HAT do music playback as well as voice on the same device? | That is Debra's whole premise; no device here has a demonstrated local music path | LVA/Sendspin integration test on the lab Pi |
| Does the ReSpeaker Lite 48 kHz firmware really enable music, and on which variant? | Source pages conflict; row is unreviewed | `CMP02B` re-run with a resolvable source register |
| What does the Satellite1 HAT cost and support? | LVA's own documentation recommends it for Pi Zero 2 W and calls the 2-Mics Pi HAT a "much more basic codec" [S8 D] | `CMP03` task |
| Is any of these quiet enough to live in a bedroom? | No measured acoustic data exists for any row | Needs measurement, not research |

## Not yet researched

Listed so nobody assumes they were rejected: Satellite1 HAT and dev kit, AtomS3R
with Atomic Voice Base or Voice Pyramid, ESP32-S3-Korvo-2, ESP-VoCat. All are
`U` until a sourced report lands.
