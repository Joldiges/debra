---
title: Optional radio and room-presence research
date: 2026-11-15
type: project-learning
status: unreviewed
task: none
author: OpenCode research agent
author_model: openrouter/openai/gpt-6.1-terra
author_variant: unknown
sources:
  - External sources and access dates listed below
  - docs/testing/results/2026-11-15-lab-pi5-lva-sendspin.md
supersedes: []
---

| Option / proposed placement | Hardware and rough incremental cost | Power, CPU, voice/music and reboot implications | Evidence / disposition |
| --- | --- | --- | --- |
| Pi BLE proxy | [D] Existing Pi 5 or Zero 2 W has BLE; no additional radio purchase assumed [P5, PZ]. | [U] Incremental watts, CPU, RAM, Wi-Fi coexistence and audio effect on either Pi are unmeasured; a Pi reboot interrupts its proxy. | [H] Optional package to investigate, not a supported feature or default [GO, PY]. |
| Separate ESPHome BLE proxy | [D] Example: Adafruit ESP32 Feather V2 PCB antenna, $19.95, board only; cable and supply extra; sold out [ESP, SHOP]. | [U] Active-proxy watts/CPU and impact on shared Wi-Fi are unmeasured. [H] Separate power avoids Pi CPU use and a Pi reboot need not interrupt it; shared network still matters. | [D] ESPHome documents BLE advertisements and GATT on ESP32 [ESP]. [H] Prefer separate device for coverage today. |
| BLE room presence | [D] Bermuda uses supported scanners plus a trackable phone/beacon; ESPresense uses ESP32 nodes and MQTT [BER, PRES]. [H] Per-room ESP32 nodes start at $19.95 each with this board; tracked device, supplies and broker/host extra [SHOP]. | [U] Pi resource and radio impact, accuracy and privacy consequences under Debra workloads not measured. [H] Pi scanner reboot removes that observation, not necessarily all presence if other scanners remain. | [H] Optional HA integration/separate nodes; use for convenience, not sole safety or security evidence. |
| Zigbee coordinator | [D] ZBT-2 USB 802.15.4 adapter, $48.95 including antenna and cable; sold out [ZBT]; HA ZHA or Zigbee2MQTT stack needed [ZHA, Z2M]. | [U] Pi watts/CPU and RF impact unmeasured. [H] A coordinator hosted by Debra goes offline on Pi reboot; direct bound Zigbee actions can still work [ZHA]. | [H] Separate coordinator/host, no default image package; a Pi network gateway is possible but creates a dependency [Z2M]. |
| Z-Wave controller | [D] Zooz ZST39 USB stick, $29.95, sold out, host/software extra [ZWPRICE]; Z-Wave JS and a region-matched adapter are required [ZW]. | [U] Pi watts/CPU and audio effect unmeasured. [H] Pi-hosted adapter/server is unavailable on reboot; endpoints may have independent local behaviors. | [D] HA also documents an experimental ESPHome network-adapter path [ZW]. [H] Separate controller/host, not default. |
| Thread border router | [D] 802.15.4 radio such as ZBT-2, $48.95 including antenna/cable, plus an OpenThread border-router host; another existing border router may suffice [ZBT, THREAD]. | [U] Pi watts/CPU and RF/audio effect unmeasured. [H] Pi reboot removes that border-router path; another compatible border router may preserve connectivity. | [H] Prefer existing or separate border router, not default; select Zigbee or Thread for this radio rather than assume concurrent operation [ZBT]. |
| Matter bridge | [D] IP software such as Matterbridge with an HA plugin; existing host/network assumed, $0 incremental radio, no new hardware price implied [MAT, MB]. | [R] Upstream's dedicated Zero 2 W example reports ~250 MB RSS for Bun with ~75 MiB available, after trimming services including audio [MBZERO]. [U] Debra simultaneous load and watts unmeasured. [H] Reboot of its host interrupts exposed bridge entities. | [H] Separate HA-side/always-on host if wanted; no default Debra bridge. |
| 433 MHz receiver | [D] RTL-SDR Blog V4 USB-C dongle $39.95, dongle only, sold out; antenna/USB adapter, host and MQTT broker extra [SDRPRICE, RTL]. | [U] SDR decode CPU, watts, heat, enclosure fit and audio contention unmeasured; USB/OTG and adequate power matter, particularly on Zero 2 W [PZ]. [H] Pi reboot stops reception and events can be missed. | [D] rtl_433 decodes supported devices and can publish via MQTT; this path is receive-only, not a universal 433 MHz remote [RTL]. [H] Separate receiver or experimental optional package, not default. |

## Interpretation and shortlist

Labels: [D] upstream/vendor-documented, not Debra-tested; [R] attributed report, not a general result; [U] unknown/not measured; [H] hypothesis or proposed decision. Counts count every bracketed label occurrence, including repeats in a row, excluding this legend. All prices are USD, US seller, quantity one, checked 2026-11-15, excluding tax/shipping; they are examples, not complete purchase totals or compatibility guarantees. $0 incremental assumes an already powered and networked host; supplies, storage, cables, enclosures, audio and tracked devices are otherwise extra and unsourced.

1. **Separate ESPHome ESP32 BLE proxy:** established HA route; place near devices. [D] HA aggregates scanners and can choose a suitable proxy by signal/availability; proxying extends coverage by placement, not the intrinsic radio range [HA-BT, ESP].
2. **Optional Pi BLE proxy experiment:** reuse existing Pi radio, compare [GO] and [PY] before selecting any dependency; do not advertise support. [R] Go project reports Pi 3 arm64 operation, not Pi 5/Zero 2 W Debra; default three slots, optional encryption off by default [GO]. [D] Python fork documents three slots and plaintext-only API and warns it was largely LLM-assisted [PY]. [H] Require security review, authenticated/encrypted API, architecture and rollback checks before packaging.
3. **Bermuda room-presence evaluation:** builds on existing BLE scanners where suitable; [D] ESPresense is a distinct ESP32/MQTT alternative, suggesting one node per room for `mqtt_room` or 5–8+ nodes per floor for its coordinate approach [PRES]. [H] Need trackable identifiers, consent, retention limits and handling of random phone addresses before recommending either.
4. **Separate Zigbee/Thread/Z-Wave infrastructure:** reuse an existing HA-side controller or border router where possible; [H] independence from a frequently updated voice satellite is more valuable than bundling a coordinator. [D] Zigbee2MQTT documents remote Pi coordinator setups but does not support serial-over-Wi-Fi due to latency/packet loss [Z2M].

## BLE detail and reality checks

- [D] HA Bluetooth and ESPHome proxy are BLE, not Bluetooth Classic audio; advertisements are broadcast without a GATT slot, while some devices need a two-way connection for reads, writes or notifications [HA-BT, ESP].
- [D] ESPHome 2026.10.2 documents three ESP32 GATT slots by default, up to nine configurable, recommends at most five, and notes about 1 KB RAM per configured slot; these are not Pi limits [ESP]. [U] Reliable concurrent GATT count on either Pi, with Wi-Fi/voice/music, is unknown.
- [D] Active scanning requests extra scan responses; passive scanning listens, distinct from active GATT connections. ESPHome warns aggressive scanning can increase CPU/network use and cause Wi-Fi instability; Ethernet can reduce proxy radio contention [ESP].
- [R] In a 2023 forum discussion, one ESP32-WROOM user reported 5–10 m through plaster/double glazing; another reported very poor range near 2.5 m [RANGE]. [U] Neither establishes a universal distance, Pi range, or enclosure performance. Antenna, obstacles, orientation and interference matter [HA-BT].
- [R] Bermuda's FAQ describes possible sub-two-second reactions and signal noise; one tuned iPhone installation reported under ten seconds while a watch was less stable [BERFAQ, ROOM]. [U] Room accuracy, latency, identity stability and false transitions at James's home remain unmeasured.
- [D] Pi 5 has dual-band Wi-Fi and Bluetooth 5 BLE; Zero 2 W has 2.4 GHz Wi-Fi, Bluetooth 4.2 BLE, 512 MB RAM and one USB OTG data interface [P5, PZ]. [U] Neither spec establishes simultaneous BLE/Wi-Fi throughput or voice quality. Original Pi Zero W ARMv6 remains an engineering goal, not proved by either board.

## Do not ship by default, and why

- [H] No radio/presence service is ready for the base image: dependencies, security, workload, recovery and user value remain unvalidated. Even a running process is not proof of working proxy functionality.
- [D] Matter is an IPv6 application protocol; Thread is a mesh transport and a border router connects it to the LAN. HA's Matter integration is a controller, not a bridge exposing HA entities; HA's documented new-device commissioning uses the phone's BLE, not the server adapter [MAT, THREAD]. [H] A BLE proxy is not a Thread radio or a substitute Matter bridge.
- [H] Keep coordinator and border-router ownership outside the satellite by default: Pi upgrades/reboots could disrupt home automation. [D] ZHA notes direct bindings can bypass HA; HA documents Z-Wave adapter backups and security keys [ZHA, ZW]. [H] Never promise seamless failover or recovery without a tested backup and restore.
- [H] Do not include 433 MHz transmission or blanket sensor support based on rtl_433; protocol, regional frequency, antenna and device support require independent checks. [D] rtl_433 warns that radio input is untrusted [RTL].

## Open questions and verification

- [U] Which Pi OS/kernel/architecture and pinned proxy revision can coexist with the deployed LVA and SendSpin setup? Is BlueZ adapter sharing safe, and can encryption, permissions, identity and bonds survive updates and rollback? Pi Zero W ARMv6 is separately unverified.
- [U] What are baseline versus proxy-on idle/peak watts, CPU, RAM, temperatures, Wi-Fi loss, audio dropouts and wake/response success on Pi 5 and Zero 2 W? How many advertisements and GATT sessions succeed at defined distances, walls and enclosure orientations?
- [U] How do scanner loss/reboot, HA restarts, reconnect, phone privacy identifiers and beacon battery affect room-presence accuracy and delay? What happens with multiple scanners and crowded 2.4 GHz environments?
- [H] Future controlled tests need an explicitly authorized lab target, versions, known recovery point and predeclared thresholds; compare baseline against scanning and multiple GATT connections during voice and music, then verify rollback and reboot recovery. No device tests, installation, flashing or live-service changes were performed for this note.
- [H] If later implemented, WEB04 should separately show installed, enabled, configured, running, HA-connected and demonstrated-working states [WEB]; not a single misleading green status.
- [U] Prices and availability drift; complete kits, shipping, taxes, local alternatives and power-supply costs remain to be sourced. Official Raspberry Pi product/documentation pages returned HTTP 403; accessible retailer specifications were used instead.

## Sources

All links checked 2026-11-15; mutable documentation and repositories are not dependency pins. Vendor prices support cost only. No independent Debra validation is implied.

- [HA-BT] Home Assistant 2026.11.1, Bluetooth adapters, proxies, scan modes: https://www.home-assistant.io/connectivity/bluetooth/
- [ESP] ESPHome 2026.10.2, Bluetooth proxy and slot/scanning limits: https://esphome.io/components/bluetooth_proxy/
- [GO] yuzi-co/btproxy README, new Linux proxy, default and security caveats: https://github.com/yuzi-co/btproxy
- [PY] machineonamission/bt-proxy README, Pi-oriented Python fork: https://github.com/machineonamission/bt-proxy
- [P5] Adafruit Raspberry Pi 5 8 GB specifications: https://www.adafruit.com/product/5813
- [PZ] Adafruit Raspberry Pi Zero 2 W specifications: https://www.adafruit.com/product/5291
- [SHOP] Adafruit ESP32 Feather V2 PCB-antenna board, $19.95, sold out: https://www.adafruit.com/product/5400
- [BER] Bermuda project, Home Assistant room presence: https://github.com/agittins/bermuda
- [BERFAQ] Bermuda FAQ, response time and signal noise: https://github.com/agittins/bermuda/wiki/FAQ
- [PRES] ESPresense project, MQTT and node requirements: https://espresense.com/
- [ROOM] Derek Seaman, 2025 iPhone/watch room-presence account: https://derekseaman.com/2025/12/home-assistant-track-whos-in-each-room-with-esphome-bermuda-ble.html
- [RANGE] HA community, ESP32 range reports, January 2023: https://community.home-assistant.io/t/new-esp32-bluetooth-proxy-how-is-it-supposed-to-work/458377/75
- [ZHA] Home Assistant ZHA coordinator, direct binding, interference and backups: https://www.home-assistant.io/integrations/zha/
- [Z2M] Zigbee2MQTT remote-adapter instructions and Wi-Fi warning: https://www.zigbee2mqtt.io/advanced/remote-adapter/connect_to_a_remote_adapter.html
- [ZBT] Apollo Automation ZBT-2 listing, $48.95, sold out: https://apolloautomation.com/products/home-assistant-connect-zbt-2
- [ZW] Home Assistant Z-Wave JS, network adapter and backup guidance: https://www.home-assistant.io/integrations/zwave_js/
- [ZWPRICE] Home Automation Headquarters Zooz ZST39, $29.95, sold out: https://ha-hq.com/products/z-wave-800-series-long-range-usb-stick
- [THREAD] Home Assistant Thread and border routers: https://www.home-assistant.io/integrations/thread/
- [MAT] Home Assistant Matter integration, commissioning and bridging: https://www.home-assistant.io/integrations/matter/
- [MB] Matterbridge project, bridge and HA plugin: https://github.com/Luligu/matterbridge
- [MBZERO] Matterbridge author's Zero 2 W report, 2026-09-25 workload snapshot: https://github.com/Luligu/matterbridge/blob/main/Raspi-zero-2w-matterbridge.md
- [RTL] rtl_433 project, receivers, decoders and MQTT: https://github.com/merbanan/rtl_433
- [SDRPRICE] RTL-SDR Blog V4 USB-C dongle only, $39.95, out of stock: https://www.rtl-sdr.com/product/rtl-sdr-blog-v4-r828d-rtl2832u-1ppm-tcxo-sma-software-defined-radio-dongle-only-usb-c/
- [WEB] Project WEB04 state distinctions: [web control design](../design/web-control.md)
