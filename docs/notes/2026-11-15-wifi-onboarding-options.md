---
title: Wi-Fi onboarding options and required failure handling
date: 2026-11-15
type: project-learning
status: unreviewed
task: N01
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - https://www.raspberrypi.com/documentation/computers/configuration.html
  - https://www.raspberrypi.com/documentation/computers/remote-access.html
  - https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/
  - https://www.raspberrypi.com/news/bookworm-the-new-version-of-raspberry-pi-os/
  - https://www.raspberrypi.com/news/usb-gadget-mode-in-raspberry-pi-os-ssh-over-usb
  - https://github.com/raspberrypi/rpi-imager/issues/1439
  - https://github.com/raspberrypi/rpi-imager/pull/1745
  - https://github.com/raspberrypi/rpi-imager/releases/tag/v2.0.7
  - https://github.com/raspberrypi/rpi-imager/releases/tag/v2.0.12
  - https://github.com/raspberrypi/rpi-usb-gadget
  - https://davesteele.github.io/comitup/
  - https://github.com/davesteele/comitup
  - https://raw.githubusercontent.com/davesteele/comitup/main/conf/comitup.conf
  - https://raw.githubusercontent.com/davesteele/comitup/debian/debian/changelog
  - https://github.com/balena-os/wifi-connect
  - https://github.com/balena-os/wifi-connect/releases/tag/v4.11.91
  - https://docs.raspap.com/
  - https://docs.raspap.com/features-experimental/ap-sta/
  - https://docs.raspap.com/features-core/ap-isolation/
  - https://docs.raspap.com/get-started/quick-installer/
  - https://networkmanager.dev/docs/api/latest/nm-settings-nmcli.html
  - https://www.rfc-editor.org/rfc/rfc6762.txt
  - https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/
  - docs/research/2026-11-15-rpi-preseed.md
  - docs/research/2026-11-14-preliminary-findings.md
  - docs/testing/results/2026-11-15-lab-pi5-silence-and-hang.md
  - docs/design/device-discovery.md
  - docs/design/web-control.md
supersedes: []
---

## Summary

**Recommendation for coordinator review, not a selection.** No Wi-Fi onboarding
approach meets Debra's requirement on its own, and one finding reorders the
whole flow: **on dual-band boards the Wi-Fi radio is disabled until a country is
set**, so a hotspot-first journey cannot be the first thing a beginner sees.

Recommended shape:

1. **Now / development:** a deterministic seed written by Debra's own image
   builder (`cloud-init` `network-config` with `regulatory-domain`, not Imager
   customisation), plus **USB gadget** (`rpi-usb-gadget`, in Trixie images by
   default) and Ethernet as the two non-Wi-Fi rescue paths. This is testable
   today and does not depend on the component that is currently unreliable.
2. **Product:** a small **Debra-owned first-boot service** that uses
   NetworkManager's own AP mode (`802-11-wireless.mode=ap`,
   `ipv4.method=shared`) and a Debra onboarding page — not a third-party router
   UI. Model the state machine on Comitup's (it is the closest match) and keep
   **Comitup as the named fallback candidate** if the portal overruns its budget.
3. **Do not** adopt RaspAP (router administration UI, root installer, PHP stack)
   or WiFi Connect (no ARMv6 binary, stale install docs) as the onboarding
   foundation.

The strongest single constraint is the single radio: AP and client cannot both be
up on one adapter unless the driver advertises it and both sit on one channel
(upstream calls this mode "completely unsupported"). Every flow below is built
around dropping the AP before associating and restoring it on failure.

Nothing here was tested on hardware. Every row is source evidence, not a Debra
result. See [Not verified](#not-verified--open-questions).

## Comparison

All source pages checked **2026-11-15**. "Maintenance" means releases or commits
observed on that date, not a quality judgement.

| Approach | What it is | License | Maintenance (checked 2026-11-15) | Headless on Pi OS Lite trixie | Root / container | What it does badly |
| --- | --- | --- | --- | --- | --- | --- |
| **Raspberry Pi Imager customisation** (`user-data` + `network-config`, legacy `firstrun.sh`) | Desktop app writes first-boot files onto the FAT boot partition; Pi OS Trixie consumes them with cloud-init | Apache-2.0 | Active: v2.0.12 published 2026-10-08 | Yes in principle, **but currently unreliable** — see traps | No root, no container (host-side flasher) | Silently applies part of the settings; no feedback to the person who flashed; builder-side only; cannot help the end user who just plugged the box in |
| **Debra-generated cloud-init seed** (same mechanism, Debra's author) | Debra's builder writes `user-data`/`network-config` itself | Debra's own | Depends on Debra | `regulatory-domain` and Wi-Fi are documented cloud-init keys | No root at build time | Still a one-shot, pre-flash step; wrong if the household network changes later |
| **Comitup** (NM AP + portal) | Python service: tries known networks, else raises `comitup-<nnn>` AP with a captive portal; mDNS `_comitup._tcp`; callback on state change | GPL-2.0 | Active: tag `v1.47.1` (2026-04-20), Debian `1.47.1-2` (2026-04-24), last push 2026-11-07 | **Unknown for trixie** — no Trixie statement found; Bookworm needs a newer `python3-networkmanager` from Comitup's repo | Root (system service, NM control) | **AP is open by default** unless `ap_password` is set; its portal is its own UI, not Debra's; "appliance/router mode" marked experimental; no Trixie confirmation |
| **WiFi Connect** | Rust binary: opens an AP with a captive portal, disables the AP to try the credentials, re-opens on failure | Apache-2.0 | Active: v4.11.91 (2026-10-22); 213 open issues | Probably, but README install path still describes Raspbian Stretch/dhcpcd | Needs NetworkManager + `NET_ADMIN` + host D-Bus (root or a privileged container) | **No armv6 asset** (armv7/aarch64/x86_64/i686 only) so original Zero W needs a source build; open AP unless `--portal-passphrase`; docs stale |
| **RaspAP** | Full router administration stack (hostapd, dnsmasq, lighttpd, PHP) with captive-portal plugin | GPL-3.0 | Active: 3.5.10 published 2026-11-11 | **Yes — officially listed**: Pi OS Lite trixie 32/64 | Root: `curl -sL https://install.raspap.com \| bash` rewrites host config | A router UI, not an onboarding wizard; large surface to leave exposed; AP-STA mode on one radio is "completely unsupported" |
| **Own NetworkManager AP + portal** (the "dispatcher-based" option) | Debra service: `mode=ap` profile with `ipv4.method=shared`, small HTTP form, state machine | Debra's own | N/A (Debra code) | Yes: NM is the Pi OS default controller | Root (NM + hostapd via NM) | Debra must write and maintain the state machine and the security of the portal — the part everyone else gets wrong |
| **systemd-networkd + wpa_supplicant** | Manual `.network`/`wpa_supplicant.conf`; no portal | LGPL/GPL components | Not a Pi OS default; maintained upstream only | Works, but only by deviating from the OS default | Root | Fights the OS: `raspi-config`, the desktop, and every tutorial assume NetworkManager; no user-facing path at all |
| **Pre-seeded file on the boot partition** (legacy `wpa_supplicant.conf`) | Copy a config onto the FAT partition before first boot | N/A | **Not documented in the current configuration guide** | Unverified — treat as unsupported, not as a method | No | Silent no-op if the OS no longer reads it; plaintext passphrase on a readable card |
| **Ethernet-first** | Plug in a cable; device appears on the LAN | N/A | N/A | Yes | No | Many homes have no cable run to where the device lives; not a beginner default |
| **USB gadget** (`rpi-usb-gadget`) | Pi presents a USB Ethernet adapter to a laptop; fixed fallback address `10.12.194.1` | Apache-2.0 | Included in Trixie images from 2025-10-20; repo quiet since v1.0.6 (2025-10-16) | Yes — documented for Trixie | Root to enable (`rpi-usb-gadget on`) | Uses the only USB-C/micro-USB port, so that port stops being a host port; Windows needs a driver installer; Imager toggle needs a custom manifest |
| **Serial console** | UART login shell | N/A | Part of Pi OS | Yes | Root to enable | On Pi 5 the primary UART is the **dedicated debug header**, not GPIO 14/15; needs a cable and a terminal program — developer-only |

### Evidence for the two constraints that shape the design

| Kind | Claim | Source / date / scope | Verification and limits |
| --- | --- | --- | --- |
| upstream-documented | On dual-band Pi models (3B+ onward, CM4 onward, keyboard computers) **networking is automatically disabled until a WLAN country is set** | [Pi configuration docs](https://www.raspberrypi.com/documentation/computers/configuration.html), checked 2026-11-15 | Direct quote; no Debra test. Means an AP-mode portal cannot start on a fresh dual-band board with no country |
| upstream-documented | Zero 2 W is **2.4 GHz only** | [Pi Zero 2 W product page](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/), checked 2026-11-15 | Suggests the country gate may not apply to Zero/Zero 2 W — **hypothesis**, needs a device test |
| upstream-documented | AP+STA on one radio needs `#{ AP } <= 1, #{ managed } <= 1, #channels <= 1`; RaspAP calls the mode "completely unsupported" and recommends a second adapter | [RaspAP AP-STA](https://docs.raspap.com/features-experimental/ap-sta/), checked 2026-11-15 | Vendor statement about its own feature; the `iw list` fragment is the real constraint |
| upstream-documented | NM `ipv4.method=shared` assigns `10.42.x.1/24`, **starts a DHCP server and DNS forwarder**, and configures NAT | [nm-settings-nmcli](https://networkmanager.dev/docs/api/latest/nm-settings-nmcli.html), checked 2026-11-15 | Primary NM reference. `802-11-wireless.mode` valid values include `ap` |
| upstream-documented | Trixie cloud-init reads `network-config` v2 with `renderer: NetworkManager`, `regulatory-domain: "GB"`, and `optional: true` | [cloud-init on Pi OS](https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/), checked 2026-11-15 | Vendor example; `optional: true` means boot does not wait for Wi-Fi — good for boot time, bad for diagnosis |
| upstream-documented | mDNS is link-local multicast: responses to `224.0.0.251`/`FF02::FB` are "necessarily deemed to have originated on the local link" | [RFC 6762](https://www.rfc-editor.org/rfc/rfc6762.txt), checked 2026-11-15 | Protocol design; it does not cross a router/VLAN without a reflector |
| upstream-documented | AP isolation (`hostapd ap_isolate`) blocks client-to-client frames at layer 2 | [RaspAP AP isolation](https://docs.raspap.com/features-core/ap-isolation/), checked 2026-11-15 | The mechanism household guest networks use; also blocks mDNS between phone and Pi |
| upstream-documented | Comitup's AP is **open unless `ap_password` (8–63 chars) is set**; it exposes `external_callback` for `HOTSPOT`/`CONNECTING`/`CONNECTED` | [comitup.conf](https://raw.githubusercontent.com/davesteele/comitup/main/conf/comitup.conf), checked 2026-11-15 | Default file, commented out; default behaviour is an open AP |
| reported | Debra's own provisioning failed on 2026-11-15 (Imager 2.0.12 Flatpak, Pi OS Lite 2026-10-06) and needed console access | [roadmap N06](../roadmap.md), [rpi-preseed note](../research/2026-11-15-rpi-preseed.md) | Operator report, cause not established |
| observed | mDNS still resolved while the lab Pi 5 was hung and sshd never sent a banner | [lab result](../testing/results/2026-11-15-lab-pi5-silence-and-hang.md) | `.local` resolution is not health evidence |
| observed | A Sendspin daemon that started before a route existed logged "Could not determine local IP address, mDNS may not work properly" | [lab result](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md) | Ordering matters: advertise only after the address exists |

Earlier coverage this note does **not** repeat: Imager/rpi-preseed mechanics are
in [the rpi-preseed evaluation](../research/2026-11-15-rpi-preseed.md); the
portal-vs-network-manager distinction and Comitup/WiFi Connect basics are in
[the preliminary findings](../research/2026-11-14-preliminary-findings.md);
device naming and mDNS discovery are in
[device discovery](../design/device-discovery.md); the browser surface is in
[web control](../design/web-control.md).

## Required behaviour

Concrete requirements for whichever implementation is chosen. Numbers are
proposals to review, not measured values.

### 1. AP-to-client transition, and proving success before the AP goes away

- **Keep the AP up while associating.** The portal must not tear down its own
  network until the uplink is proven; otherwise the user loses the page that
  would tell them what happened.
- Because of the single-radio limit, "keep the AP up" means the client attempt
  happens **after** the AP stops, so the order is: submit → stop AP → associate →
  verify → (on failure) restart AP with an explanation. If a second interface
  exists, the AP may stay up throughout.
- **Success requires all of:** the NM profile is activated; the interface holds a
  routable IPv4 address (never `169.254.x.x`); a default route exists; **and** one
  of DNS resolution or an HTTP probe succeeds. Association alone is not success —
  a wrong WPA3/enterprise choice can associate and then fail DHCP.
- **Tell the user before their phone drops.** The page must say, in advance, that
  the Debra network will disappear and that they should rejoin their home Wi-Fi.
- **Show the address while the page is still reachable**: hostname, IP, and the
  next URL, then a "Done" button plus a fixed grace period (proposal: 60 s)
  before the AP stops.
- **Never reboot to "apply" Wi-Fi.** A reboot hides failures and costs the user
  another two minutes of not knowing.
- If the uplink is later lost (router reboot, moved house), do not silently
  re-open an AP forever — see re-entry.

### 2. Bad credentials, and how the user is told

The portal must distinguish these and say something different for each:

| Condition | What the user sees | Next action offered |
| --- | --- | --- |
| Wrong passphrase | "The password for *Network* was not accepted." | Retry, password field focused, SSID kept |
| SSID not in range | "*Network* is not visible now. It may be out of range, or turned off." | Rescan |
| 5 GHz-only network on a 2.4 GHz-only board | "*Network* uses 5 GHz, which this model cannot see." | Show it greyed in the scan list rather than omitting it |
| WPA3-only / enterprise | "This network uses a security type Debra could not complete." | Name the type; do not claim the password is wrong |
| Associated but no address | "Connected to *Network*, but it did not give an address." | Retry; mention router DHCP |
| Address but no DNS/internet | "Joined *Network*, but names do not resolve." | Continue anyway (LAN-only is valid) or retry |
| Regulatory block | "This channel is not allowed in the selected country." | Offer country change, warn that it may disable channels |

- **Never show a bare "connection failed".** Every failure names a cause and one
  next action.
- **Retry policy:** proposal — 3 attempts per network with backoff, then return
  to the form with the SSID preserved and the password field cleared. Always
  leave a path back to the form.
- **Never log the passphrase.** `journalctl` and any exported diagnostic bundle
  must show the SSID and the failure class only.
- The scan list should show band and security for each entry; hiding a network
  the device cannot join is a support call waiting to happen.

### 3. Country / regulatory domain, and the single radio

- **Country is a precondition, not a setting inside the portal.** On a dual-band
  board with no country the radio is off, so the portal has nothing to run on.
  Debra must therefore ship a country chosen at image-build time (or have the
  builder set it), and let the user correct it later.
- The device must **detect "radio disabled because no country"** and say exactly
  that, rather than showing an empty network list.
- Changing country must warn that channels may disappear; it must not silently
  strand a working connection.
- **Do not design for simultaneous AP and client.** Treat one radio as
  "one or the other" and make the transition explicit to the user. Only use
  concurrent mode when `iw list` on that exact board advertises a combination
  that includes both `AP` and `managed`, and then pin both to one channel.
- The portal's own AP channel must be legal in the selected country; picking a
  fixed channel (e.g. 6, or 1) is safer than "auto" during onboarding.

### 4. Re-entry and reconfiguration after the device is on a network

Three independent entries, all required:

1. **Physical:** a button/GPIO hold (Comitup uses a 3 s short between pins 39 and
   40) re-arms the AP for a bounded window.
2. **Automatic:** N consecutive boots with no uplink (proposal: 3) re-arm the AP
   automatically, so a moved or re-flashed device recovers without a cable.
3. **Logical:** the normal browser UI at `debra-<id>.local` changes Wi-Fi using
   the same code path, with **the previous profile kept as a fallback** until the
   new one is proven (NM checkpoint or simply a higher `autoconnect-priority` on
   the old profile). A failed change must restore the old network, not leave the
   device unreachable.

The AP must **not** start when the device already has a working uplink.

### 5. Credential storage and account enrolment

- The Wi-Fi passphrase lives only in
  `/etc/NetworkManager/system-connections/*.nmconnection`, mode `0600`, root.
  Never in Git, never in a distributable image, never in a log, never echoed back
  by the portal.
- **The seed on the FAT partition is plaintext until consumed.** Debra must
  overwrite or delete it after a successful import, and say so in the guide. A
  card pulled out of a half-configured device currently exposes the household
  passphrase.
- **No universal image credential.** Each device generates its own AP passphrase
  and its own first admin credential at first boot, and the pairing material is
  printed on or attached to the device. No `debra/debra`, no shared key.
- **Account enrolment** happens on first visit to the device UI over the LAN (or
  the AP before it stops), not in the image. SSH key enrolment is a separate,
  explicit step for the developer path.
- Device identity (the `<id>`) is the subject of N02; do not derive it from
  `machine-id`, which changes on re-flash
  ([device discovery](../design/device-discovery.md)).

### 6. Finding the device after the AP disappears

Require **at least two independent** discovery routes, because mDNS is
link-local and is blocked or isolated on some networks:

1. **Shown before the AP stops** — hostname and IP on the final portal page.
2. **Written to the boot partition** — a small `debra-address.txt` (hostname, IP,
   timestamp, SSID name only) so a card reader always reveals the last known
   address.
3. **mDNS** — `debra-<id>.local` via the Avahi service that Pi OS already runs
   ([remote access docs](https://www.raspberrypi.com/documentation/computers/remote-access.html)).
4. **Router device list** — the device sends its hostname in the DHCP request, so
   the household router shows `debra-<id>` ([same docs](https://www.raspberrypi.com/documentation/computers/remote-access.html)).
5. **`avahi-browse -a`** from another Linux machine, as the official docs suggest.
6. **USB gadget** — the fixed `10.12.194.1` fallback when ICS is absent, which
   works with no network at all.

Rules: mDNS is never the only route; the printed instruction must name the
router-list and card-reader fallbacks in plain language; and a hostname collision
between two devices is currently **unknown** behaviour (Avahi may rename) and
must be tested before the ID scheme is frozen.

### 7. Never leaving an open, unattended administration portal

- **The AP is WPA2-protected** with a per-device passphrase. An open AP is the
  default in both Comitup and WiFi Connect; Debra must not inherit it.
- **The AP is time-boxed** (proposal: 15 minutes) and stops on success. It must
  not persist across a reboot into a working network.
- **The portal exposes only onboarding.** No shell, no file read, no device
  control, no component management. The full device UI must not be reachable
  from the AP network until the device is enrolled.
- One in-flight submission at a time; no CSRF-prone state changes; no credentials
  in the URL; no directory listing.
- If the AP is left running because the user walked away, it must still be
  encrypted and must expire.

### 8. What the user sees when it fails

Plain language, one cause, one action, no log lines, no Linux vocabulary:

> **Debra could not join "HomeWiFi".**
> The password was not accepted. Check it on your phone and try again.
> [ Try again ]  [ Choose a different network ]

> **Debra cannot see any Wi-Fi networks.**
> This model needs a country setting before its Wi-Fi can be used.
> [ Choose your country ]

> **Debra joined "HomeWiFi" but has no internet.**
> This is usually the router. Debra is at `http://debra-3c6b3f.local` and may
> still work for Home Assistant on your home network.

Diagnostics belong in the journal and in an explicit "copy diagnostic report"
action, never in the failure message itself.

## Traps

- **Imager customisation can apply only part of what was chosen.** Open upstream
  bug: hostname applied, user/locale/SSH not, across several reflashes
  ([issue 1439](https://github.com/raspberrypi/rpi-imager/issues/1439), opened
  2026-01-04, still open with 62 comments). Do not build Debra's story on it.
- **Non-ASCII SSIDs were written wrong.** `yamlEscapeSsidOctets()` emitted bytes
  where cloud-init expected code points, so an accented SSID silently failed;
  fixed 2026-09-24 and shipped in v2.0.12
  ([PR 1745](https://github.com/raspberrypi/rpi-imager/pull/1745)). A household
  with `Café` in its SSID needs 2.0.12 or later.
- **Stale Wi-Fi settings survived "Skip"** — fixed in v2.0.7
  ([release notes](https://github.com/raspberrypi/rpi-imager/releases/tag/v2.0.7)).
  A skipped Wi-Fi step could still write an old profile.
- **Old Imager + new OS is a known bad pairing**; Imager 2.0.7 added documentation
  about the interaction between old Imager versions and new Raspberry Pi OS
  releases ([same notes](https://github.com/raspberrypi/rpi-imager/releases/tag/v2.0.7)).
- **cloud-init runs once per instance-id.** Editing `user-data` on an
  already-booted card does nothing without a deliberate re-run; Imager 2.0.7 had
  to make the instance-id durable across reboots
  ([release notes](https://github.com/raspberrypi/rpi-imager/releases/tag/v2.0.7),
  [cloud-init instance data](https://cloudinit.readthedocs.io/en/latest/explanation/instancedata.html)).
- **`optional: true` hides failure.** The vendor's own example sets it so boot
  does not wait for Wi-Fi. Good for boot time; it also means a failed Wi-Fi join
  produces no error at boot. Debra needs its own state, not cloud-init's exit
  code.
- **Country unset = no radio** on dual-band boards. A "just works" hotspot image
  with no country is dead on arrival on a Pi 5.
- **Comitup's AP is open by default.** Set `ap_password` or you ship an open
  portal; `external_callback` is the hook for Debra's own state machine.
- **Comitup has no GitHub Release objects**, only tags (`v1.47.1`); "no releases"
  is not "unmaintained" — the Debian changelog is current to 2026-04-24.
- **WiFi Connect has no armv6 asset.** The original Pi Zero W cannot run the
  published binary; that is a build-from-source project, not a download.
- **RaspAP's own docs call single-radio AP-STA "completely unsupported"** and
  tell you to buy a second adapter. Do not plan around concurrency.
- **mDNS is link-local.** It does not cross a VLAN or a router, and AP isolation
  blocks it even on one subnet. Any plan that assumes `.local` works everywhere
  will fail in exactly the households that need help.
- **mDNS resolving proves nothing about health** — the lab device answered mDNS
  while sshd was wedged ([result](../testing/results/2026-11-15-lab-pi5-silence-and-hang.md)).
- **USB gadget takes the port.** Enabling it makes the USB-C/micro-USB port
  data-only, so a keyboard or stick cannot use it, and Windows needs a separate
  driver installer.
- **`rpi-usb-gadget` has a hardcoded `10.12.194.1/28`** for its shared mode, and
  NM `shared` uses `10.42.x.1/24` — two Debra devices onboarding at once can
  collide on the client side if both are attached to one laptop.
- **Serial console moved on Pi 5.** The primary UART is the dedicated debug
  header (`UART10`); the 40-pin header needs `enable_uart=1` before a console
  appears there ([configuration docs](https://www.raspberrypi.com/documentation/computers/configuration.html)).
- **Do not switch Pi OS to systemd-networkd** to get a "simpler" stack; it
  diverges from every Pi OS tool and from the desktop's own network UI.

## Verification

- Exact safe commands/procedure and working directory: none run. No card was
  flashed, no Pi contacted, no network changed, nothing installed.
- Observed results: **not-run** for every approach in the comparison table.
- What was actually done: read the primary sources listed in the frontmatter on
  2026-11-15, queried the GitHub API for release/tag/commit dates, and read the
  Debra notes cited above.
- Not tested, conflicting evidence, and remaining uncertainty: see below.
- Sanitized artifact references: none.

## Not verified / open questions

- **Does Comitup run on Pi OS Lite trixie?** No Trixie statement found on its
  site, wiki or changelog. Bookworm already needed a patched
  `python3-networkmanager`. Must be tried on a disposable card.
- **Does the country gate really skip Zero 2 W?** The documented list is "3B+
  onwards"; Zero 2 W is 2.4 GHz-only, so it probably does. Unverified.
- **Is `wpa_supplicant.conf` on the boot partition still read?** It is absent from
  the current configuration guide, which documents only Imager and `nmcli`. Absence
  is not proof it is ignored — do not claim either way without a mounted-card test.
- **Does Avahi rename on hostname collision, and to what?** Not established;
  matters if two boards derive the same ID.
- **Which WPA3/SAE and 802.1X cases actually work** on the Pi's firmware and
  `wpa_supplicant` in Trixie: unknown.
- **Power behaviour during AP mode.** The lab Pi 5's supply already sags under
  load; an AP plus portal adds radio time. Not measured.
- **How long association+DHCP actually takes** on each board, and therefore the
  right grace period before the AP stops: unknown.
- **Whether a captive-portal auto-popup works on current iOS/Android** with a
  WPA2-protected AP: unknown; the page must also be reachable by typing the
  address.
- **Whether `rpi-usb-gadget` still works with the Trixie images Debra will ship**
  — the package is in the image, but the repo has had no commit since 2025-10-15
  and there are 24 open issues.
- **Debra-specific:** no decision on whether Debra ships its own portal or adopts
  Comitup; that is a coordinator/F05 review, not this note.

## Handoff and correction links

- Current state: research complete for N01's comparison and failure matrix; no
  implementation selected.
- Concrete next action: N04 (blocked on N01/N03/B03) should test, on a leased
  board and a disposable SSID: wrong password, 5 GHz-only SSID, country unset,
  AP shutdown after success, re-entry by button, and mDNS-blocked discovery.
  N06 still owes the mounted-card inspection and a vendor-AppImage control flash.
- Authorization needed: none of the above is permission to flash, reconfigure the
  household router, or install packages.
- Earlier claim superseded: none. This note extends
  [preliminary findings](../research/2026-11-14-preliminary-findings.md) with
  dated sources and the country/single-radio constraints.
- Reviewed report/decision that later adopts this finding: none yet.
