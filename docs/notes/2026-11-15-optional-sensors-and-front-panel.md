---
title: Optional sensors and front-panel options
date: 2026-11-15
type: project-learning
status: unreviewed
task: Optional sensors and front-panel research
author: OpenCode
author_model: openrouter/openai/gpt-6.1-terra
author_variant: unknown
sources:
  - docs/notes/2026-11-15-rpispeaker-v17-bay-inventory.md
  - models/components/respeaker-2mic-hat/README.md
  - Vendor and project URLs in the table, accessed 2026-11-15
supersedes: []
---

# Optional sensors and front panel

`D` = upstream-documented, `R` = attributed report, `U` = unknown/unverified; hypotheses are explicitly named. These map to [evidence rules](../evidence.md), not to Debra test passes. All external URLs below were fetched **2026-11-15**; mutable docs and listings are not pinned. Prices are **Adafruit US, one item, USD, 2026-11-15**, linked in each row, excluding shipping, tax, cables, mount, controller and power; incremental parts prices are not a complete purchase cost. $0 means reuse of an assumed existing part, not a free complete device.

`U`: No option below is established as a working Debra integration or physical fit. Home Assistant (HA) has [MQTT sensors](https://www.home-assistant.io/integrations/sensor.mqtt/) and [MQTT lights](https://www.home-assistant.io/integrations/light.mqtt/) (`D`), but a device-side driver, state/command adapter, availability handling and an MQTT broker are needed for that route; another integration could be chosen instead. Do not infer any of this from the existing voice connection.

| Option and example cost | Exposure, software, power/interference and placement |
| --- | --- |
| **Existing HAT button + three LEDs**, reuse $0 | `D` [Seeed ReSpeaker 2-Mics v2](https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/) documents GPIO17 button and SPI LEDs; [local LED spec](../design/led-profiles.md) proposes states, not implemented/approved. `U` An adapter could expose button events and mute/status in HA; avoid competing LED writers. Visible/button-accessible surface needed; light pipes, obstruction by speaker, low-brightness visibility and power are untested. Button controls software, **not a hardware mic disconnect**. |
| **SHT40 temperature/RH**, [$5.95](https://www.adafruit.com/product/4885) | `D` I²C, vendor Python library, typical ±0.2 °C / ±1.8% RH in stated ranges; bare chip averages 0.4 µA at 1 Hz, not the breakout total. `U` HA temperature and humidity via adapter; breakout/connection and heat need evaluation. Hypothesis: exposed, ventilated and thermally separated from Pi, amplifier and exhaust is preferable to inside the hot case. |
| **BME280 temperature/RH/pressure**, [$14.95](https://www.adafruit.com/product/2652) | `D` I²C or SPI, Python library; adds pressure, with vendor ±1 °C and ±3% RH specifications. `U` HA sensor entities need adapter; current and assembled placement not measured. Same heat isolation as SHT40. `R` [Bouvy 2020 Pi Zero comparison](https://michael.bouvy.net/post/temperature-humidity-sensors-benchmark-for-raspberry-pi-and-arduino) found BME280 ~1 °C above the average of other sensors overnight; heat was the author's inference, not a measured cause or transferable correction. |
| **SCD-41 CO₂ + temperature/RH**, [$49.95](https://www.adafruit.com/product/5190) | `D` Photoacoustic actual CO₂ in ppm, I²C, vendor Python; specified sensor current 17 mA at 5-second or 0.5 mA at 5-minute interval, not necessarily whole-breakout consumption. `U` Publish HA CO₂/temp/RH via adapter; calibration, supply noise and Pi compatibility need checking. Hypothesis: separate ventilated position away from breath and board heat is more representative; do not present as a CO or fire alarm. |
| **SGP40 VOC index**, [$14.95](https://www.adafruit.com/product/4829) | `D` I²C MOX gas sensor has heater and vendor Python plus VOC-index algorithm; requires external humidity for humidity compensation. Reports an index, **not measured CO₂ or a specific gas concentration**. `U` HA numeric sensor needs adapter, conditioning and power/heat assessment; sample room air away from contamination/heat, with suitability unproven. |
| **PMSA003I particulate matter**, [$39.95 bare module](https://www.adafruit.com/product/4505) | `D` PM1/2.5/10, I²C, 5 V supply and 3.3 V logic, ≤100 mA active, 38 × 35 × 12 mm; vendor Python. `U` HA particle entities need adapter and appropriate connector; airflow and acoustic interference require testing. Keep its air path clear and treat fan noise near mics as a hypothesis, not a measured result. |
| **Existing microphones / relative sound level**, reuse $0 | `D` [ESPHome sound-level sensor](https://esphome.io/components/sensor/sound_level/) describes relative level, not this Linux Voice Assistant (LVA) implementation. `U` A shared capture tap plus local RMS/peak computation and HA sensor publisher could yield relative dBFS trends; gain/AGC, clipping, filtering, voice/audio sharing, fan and speaker playback confound it. Position is fixed by HAT; no calibrated dBA, SPL or safe-exposure claim; privacy and capture-mute behavior need explicit design. CPU/power impact unknown. |
| **VEML7700 right-angle lux**, [$4.95](https://www.adafruit.com/product/5378) | `D` I²C, vendor Python; detects light parallel to PCB. `U` Adapter could publish HA illuminance or drive dimming; needs a view of room light, shielded from its own LEDs to avoid feedback, with power/placement unmeasured. Scheduling or manual dimming is a simpler alternative. |
| **12-RGB NeoPixel ring**, [$8.95](https://www.adafruit.com/product/1643) | `D` Ø36.8 mm, 5 V, timing-sensitive; seller warns against ordinary Linux driving. `D` [Adafruit power guide](https://learn.adafruit.com/adafruit-neopixel-uberguide/powering-neopixels): worst-case estimate 60 mA/pixel: 12 × 60 mA = 0.72 A, ~3.6 W at 5 V, before supply losses. `U` Dedicated controller/driver, logic-level and power design, HA light adapter and visible external placement all need validation; status must take priority over decorative commands. |
| **0.91-inch 128×32 OLED**, [$12.50](https://www.adafruit.com/product/4440) | `D` I²C, vendor Python; PCB listed 35 × 20 mm, display consumption varies (~15–20 mA vendor examples), continuous pixels age. Listing also gives a conflicting 46.3 mm module size: total envelope `U`. `U` A display renderer could show HA/device information but is not an HA entity by itself; readable view and light leakage near lux sensor need assessment. |
| **I²C rotary encoder with push switch**, [$7.95](https://www.adafruit.com/product/5880), optional knob $0.75 at same listing | `D` Seesaw controller tracks turns and push over I²C, with Python library and onboard light; PCB nominally 1 inch square. `U` Device-side input mapping and HA event/state adapter needed; mounting/shaft reach, power, electrical and acoustic effects untested. Can provide tactile volume control without assuming direct control of the music receiver. |
| **Capacitive touch**, [$5.95](https://www.adafruit.com/product/1374) | `D` AT42QT1010 digital output, ~0.5 mA fast mode, PCB 20 × 28 mm. `U` GPIO availability/voltage, input adapter and HA event mapping require verification. Surface, case material, accidental touches, LED feedback, noise and grounding sensitivity are untested; not a hardware microphone disconnect. |
| **Board and bus constraints** | `D` HAT uses SPI LEDs and GPIO17 button; [component inventory](../../models/components/respeaker-2mic-hat/README.md) shows I²C/GP12 Grove connectors based on V1 layout as a V2 proxy, not a measured V2 connector guarantee. `U` Grove voltage/pinout, accessible pins with the HAT installed, I²C address/pull-up conflicts, cable limits and the complete pin map must be checked for each board and OS. `D` Seeed specifically flags its old button demo as incompatible with Pi 5; do not assume Pi 5 and Zero 2 W GPIO software are interchangeable. `U` Pi 5 and Zero 2 W thermal bias, headroom and coexistence with voice/music are unmeasured. `R` [Pi 5 lab record](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md) notes earlier undervoltage and James's report of improvement after a supply replacement; the improvement is unmeasured. Original Zero W/ARMv6 compatibility is a separate unproven goal. |
| **V17 nominal arithmetic, not fit** | `R` [corrected STEP inventory](2026-11-15-rpispeaker-v17-bay-inventory.md) reports a lower comparison box **31.10 × 28.125 × 13.00 mm**; not a fully walled pocket or free space after a speaker. Using the vendor dimensions linked above (`D`), BME280 **25.2 × 18.0 × 4.6** leaves nominal axis differences **5.90 × 10.125 × 8.40 mm**; SCD-41 **25.5 × 22.8 × 7.7** leaves **5.60 × 5.325 × 5.30 mm**. Ring Ø36.8 exceeds the two plan spans by **5.70 / 8.675 mm**; OLED PCB 35 mm exceeds 31.10 by **3.90 mm** in that orientation. PMSA003I 38 × 35 exceeds both spans by **6.90 / 6.875 mm**. `U` These comparisons omit speaker, connectors, mounts, orientation and tolerances; overhang/external mounting is not ruled out. `R` That inventory reports no four-screw square mount in the STEP; its two through holes are 36.5 mm apart. |

## Recommendations

1. **Base device — Pi 5 + ReSpeaker 2-Mics v2:** reuse its button and three LEDs for assistant status, subject to software/visibility review. Do not call the button a hardware mute. Pi Zero 2 W + the same HAT is a candidate, not an established equivalent.
2. **Add-on — Pi 5 or Pi Zero 2 W + HAT:** evaluate SHT40 for room temperature/RH; use BME280 only if pressure is wanted. Favor a thermally isolated, air-exposed location; validation against a reference across idle, voice and music is a prerequisite.
3. **Add-on — Pi 5 or Pi Zero 2 W + HAT:** consider VEML7700 only if automatic brightness or HA lux is useful; manual/scheduled dimming needs no extra sensor. Placement and bus compatibility remain `U`.
4. **Separate — independent HA-compatible CO₂ sensor, or later Pi 5/Zero 2 W add-on:** investigate actual CO₂ such as SCD-41 if ventilation information is wanted; separate placement may avoid device heat and permits independent room placement. Its complete independent device, integration and cost are `U`.

## Do not add, and why

- No internal temperature/RH sensor marketed as room-accurate without comparison to a reference under changing load; no blanket software offset from the Bouvy report.
- No VOC index sold as CO₂, pollutant concentration or a safety alarm; no CO₂ sensor substituted for a certified CO/smoke alarm.
- No calibrated sound-level or dBA claim from the voice microphones; relative sound sensing is an optional experiment only, with privacy and audio-sharing design first.
- No default ring, OLED, rotary or touch module yet: extra cost, integration, placement and interference are unverified. A ring's power and LED-priority requirements are especially significant; an OLED's total envelope is inconsistent in the listing. No assumption that the speaker bay is empty.

## Open questions and handoff

- Which room measurements and front-panel actions does James actually want, and is a separate sensor more useful than mounting one on the voice device?
- What are the actual V2 Grove electrical details, available pins, bus addresses and voltage/pull-up interactions on each exact Pi/OS/HAT combination?
- What thermal/RH bias occurs against a trusted reference at idle, during sustained music and voice, and after warm-up on each board? How does speaker placement affect the remaining space and airflow?
- Which HA transport and audio-sharing design can handle stale values, privacy, mute and restart without disrupting LVA or SendSpin? Can existing LEDs remain legible and truthful at night?
- Verification: source pages fetched and repository records read 2026-11-15; arithmetic is comparison only. No hardware, software integration, assembly, print or fit testing was performed. Next: review this note and obtain explicit authorization before any device test or purchase; this note grants none.
