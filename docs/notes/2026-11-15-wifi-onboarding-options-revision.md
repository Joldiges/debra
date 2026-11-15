---
title: Wi-Fi onboarding options, revision 2
date: 2026-11-15
type: project-learning
status: unreviewed
task: N01
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - docs/notes/2026-11-15-wifi-onboarding-options.md (N01, the note this revises; read 2026-11-15)
  - docs/notes/2026-11-15-research-notes-review.md (findings N01-1 to N01-8; read 2026-11-15)
  - docs/project-brief.md; docs/evidence.md; docs/templates/learning-note.md (read 2026-11-15)
  - docs/research/2026-11-15-rpi-preseed.md; docs/research/2026-11-14-preliminary-findings.md; docs/design/device-discovery.md; docs/design/web-control.md; docs/testing/results/2026-11-15-lab-pi5-silence-and-hang.md (N01's own citations, not re-read in full here)
  - https://raw.githubusercontent.com/davesteele/comitup/main/conf/comitup.conf (2026-11-15: ap_name/ap_password 8-63 chars/web_service/enable_appliance_mode/external_callback/enable_nuke/ipv6_link_local; enable_nuke documented as deleting all defined Wi-Fi connections)
  - https://davesteele.github.io/comitup/ (2026-11-15: mDNS name advertising the IP on all interfaces, `_comitup._tcp`, captive portal, Locate function, Bookworm needs newer python3-networkmanager, default comitup/comitup image user)
  - https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/ (2026-11-15: network-config example with regulatory-domain and optional: true; "cloud-init stores your generated network configuration from network-config without modification" in /etc/netplan/; netplan clears /etc/netplan yaml; NM only manages netplan- prefixed profiles; runtime profiles in /run/NetworkManager/system-connections/)
  - https://raw.githubusercontent.com/raspberrypi/documentation/master/documentation/asciidoc/computers/configuration/configuring-networking.adoc (2026-11-15: country gate quote and affected models, regulatory-domain consequences, nmcli radio wifi, "Secrets were required, but not provided", DHCP reservation guidance, hostname character rules, /etc/NetworkManager/system-connections holds the password)
  - https://www.raspberrypi.com/documentation/computers/configuration.html (fetched 2026-11-15, HTTP 403; the asciidoc source above was used instead)
  - https://api.github.com/repos/raspberrypi/documentation/contents/documentation/asciidoc/computers/configuration (2026-11-15: file listing used to locate the source above)
  - https://networkmanager.dev/docs/api/latest/settings-ipv4.html (2026-11-15: shared method subnet 10.42.x.0/24, shared-dhcp-range, shared-dhcp-lease-time, forwarding always enabled for shared, dhcp-timeout default ~45 s, dhcp-send-hostname TRUE)
  - https://networkmanager.dev/docs/api/latest/settings-connection.html (2026-11-15: autoconnect, autoconnect-priority -999..999, autoconnect-retries default -1 = 4 and 1 = try once then block, connection.mdns requires systemd-resolved, stable-id)
  - https://networkmanager.dev/docs/api/latest/settings-802-11-wireless.html (2026-11-15: mode infrastructure|mesh|adhoc|ap, band a|bg|6GHz, channel requires band, ap-isolation NMTernary)
  - https://networkmanager.dev/docs/api/latest/settings-802-11-wireless-security.html (2026-11-15: key-mgmt values incl. sae/wpa-eap, psk, psk-flags secret flags)
  - https://networkmanager.dev/docs/api/latest/nmcli.html (2026-11-15: `nmcli device checkpoint [--timeout seconds] [ifname...] -- COMMAND`, prompts for confirmation, restores on timeout, default 15 s)
  - https://www.rfc-editor.org/rfc/rfc6762.txt (2026-11-15: section 3 .local is link-local; section 9 conflict resolution, loser must cease the name, append "2"/increment, persist the new name, tell the user)
  - https://manpages.debian.org/bookworm/avahi-daemon/avahi-daemon.conf.5.en.gz (2026-11-15: host-name/domain-name options; no statement about collision renaming)
  - https://cloudinit.readthedocs.io/en/latest/explanation/instancedata.html (2026-11-15: instance-data retains userdata; `cloud-init query userdata` returns decoded user-data to root; sensitive keys redacted for non-root)
  - https://github.com/balena-os/wifi-connect (2026-11-15: "disable the access point and try to connect... If the connection fails, it will enable the access point for another attempt"; unprotected by default; --portal-passphrase; saves on success; Raspbian Stretch install text)
  - https://www.raspberrypi.com/news/usb-gadget-mode-in-raspberry-pi-os-ssh-over-usb/ (2026-11-15: port table, "no longer operate as a regular USB host port", fallback 10.12.194.1, Windows driver installer, one Pi at a time, .local may not resolve on Windows)
  - https://docs.raspap.com/features-experimental/ap-sta/ (2026-11-15: "completely unsupported", buy a second adapter, iw list combination fragment)
supersedes:
  - docs/notes/2026-11-15-wifi-onboarding-options.md
---

## Summary

Revision 2 of the N01 Wi-Fi onboarding research, after the independent review's
eight findings. The original note is preserved unchanged. This note withdraws the
one flow that could not physically happen, states a flow that can, and restates
the credential, reset, re-entry, country and portal-security guidance.

**The decisive correction.** N01 proposed: submit → stop the hotspot → join the
home network → *verify the assigned address* → *show that address on the still-open
setup page* → then stop it. On one radio that page cannot exist at that moment: the
address does not exist until the client interface is up, the client interface
cannot be up while the access point is up, and the user's browser is only connected
while the access point is up. The page is gone before the address is known. The
same constraint applies to every single-radio tool evaluated here, including
WiFi Connect, whose own documentation describes the identical
access-point-down-then-try sequence.

**The corrected flow, in five lines.** Chosen shape: a single radio, an encrypted
short-lived hotspot, and *announce the name, never the address*.

1. Before anything changes, the setup page tells the user two things that are
   already true and cannot change: the device's name, `http://debra-<id>.local`,
   and that the setup network is about to disappear — so the address is never
   promised, because it is not yet knowable.
2. The user submits; the device stores the household credentials as a *trial*
   profile with autoconnect disabled, shows a "saving" page with the name and the
   instruction, and only then stops the hotspot. The phone's connection dies here,
   by design, and the page is not expected to come back.
3. The device joins, then verifies in layers — associated, routable address,
   default route, and separately DNS/internet — and writes the outcome (name, IP,
   state, timestamp) to a small file on the boot partition before announcing mDNS.
4. The user finds the device afterwards by *name* (mDNS), by the router's client
   list (the device sends its hostname in DHCP), by reading that boot-partition
   file on a computer, or from a second device that was on the home network all
   along. The address itself is learned after the fact, not promised in advance.
5. On failure the hotspot comes back up with the *same* SSID and passphrase for a
   bounded window, and the page shows one cause and one action; if the user walked
   away, a physical re-arm or N failed boots bring it back, and no saved bad
   profile is ever allowed to outrank the hotspot.

The one conditional variant is the concurrent case the review asked for: if the
driver advertises an AP-plus-managed combination *and* the hotspot is pinned to the
same channel as the household access point, the hotspot can stay up and the page
can show the live address. That is a real second state machine, not a fallback
story, and it is unverified on any Debra board.

**Tool position, unchanged in direction but re-argued.** A Debra-owned
NetworkManager access point plus a Debra-owned onboarding page remains the
recommendation, with Comitup as the named fallback candidate. The reason is no
longer "model the state machine on Comitup's"; it is that the corrected flow needs
a page Debra controls, a trial profile Debra can refuse to keep, and a
reconfiguration path with rollback — none of which the third-party portals expose.

Nothing here was tested on hardware. Every row is source evidence or a stated
inference. See [Verification](#verification) and [Still unknown](#still-unknown).

## How to read this

Evidence labels follow [the evidence rules](../evidence.md): `upstream-documented`,
`reported`, `hypothesis`, `unknown`, `proposed`. "Proposed" means a Debra design
choice for review, not an established requirement. Where a number is a proposal it
is marked as one; no timeout, window or retry count here is measured.

Two things this note deliberately does not do: it does not re-derive the
Imager/preseed mechanics (see
[the rpi-preseed evaluation](../research/2026-11-15-rpi-preseed.md)), and it does
not decide the identity scheme (N02). The device name is treated as an input that
already exists at first boot.

## The tool comparison, with corrected claims

All pages checked **2026-11-15**. "Maintenance" means releases or commits observed
on that date. The "Can it show the address on its own page?" column is the new
decisive column: it is the property N01 assumed and no single-radio tool has.

| Approach | What it is | License | Maintenance (2026-11-15) | Single-radio join sequence | Can it show the post-join address on its own setup page? | What it does badly |
| --- | --- | --- | --- | --- | --- | --- |
| **Raspberry Pi Imager / cloud-init seed** | Desktop app writes `user-data` + `network-config` onto the FAT boot partition | Apache-2.0 | Active (v2.0.12, 2026-10-08, per N01) | No hotspot at all | n/a — no page | One-shot and pre-flash only; cannot help the person who plugged the box in; the seed is plaintext on a readable card; N01 records it as currently unreliable |
| **Debra-owned NM AP + portal** (the "dispatcher" option) | Debra service: `mode=ap` profile with `ipv4.method=shared`, small HTTP form, explicit state machine | Debra's own | n/a | AP down → join → verify → AP back only on failure | **No, not on one radio** — but it can *announce the name* before the drop and *re-arm with the result* on failure | Debra writes and maintains the state machine, the portal and its security — the part everyone else gets wrong |
| **Comitup** | Python service: joins known networks, else raises `comitup-<nnn>` with a captive portal; mDNS name and `_comitup._tcp` | GPL-2.0 | Active (tag v1.47.1, 2026-04-20, per N01) | Same constraint; the AP must come down to try the uplink | No; it solves the *afterwards* problem instead, by advertising `comitup-<nnn>.local` and the device's IP on all interfaces | AP open unless `ap_password` (8–63 chars); `enable_nuke` is destructive (below); image ships `comitup`/`comitup` default credentials; Trixie support unknown; Bookworm needs a newer `python3-networkmanager` |
| **WiFi Connect** | Rust binary: opens an AP with a captive portal, then "disable the access point and try to connect… If the connection fails, it will enable the access point for another attempt" | Apache-2.0 | Active (v4.11.91, 2026-10-22, per N01) | Same constraint, documented by the project itself | No — the project's own flow confirms the page cannot survive the attempt | Unprotected by default (`--portal-passphrase` optional); no armv6 asset; README install path still describes Raspbian Stretch/dhcpcd |
| **RaspAP** | Router administration stack (hostapd, dnsmasq, lighttpd, PHP) with a captive-portal plugin | GPL-3.0 | Active (3.5.10, 2026-11-11, per N01) | Vendor: single-radio AP-STA is "completely unsupported… obtain a second Wi-Fi adapter" | Only in the unsupported concurrent mode | A router UI, not an onboarding wizard; root `curl \| bash` rewrites host networking; large surface to leave exposed |
| **systemd-networkd + wpa_supplicant** | Manual `.network`/`wpa_supplicant.conf` | LGPL/GPL components | Maintained upstream only | Manual | No | Fights the OS default; no user-facing path at all |
| **`wpa_supplicant.conf` on the boot partition** | Copy a config onto the FAT partition | n/a | Not in the current configuration guide | No hotspot | No | Silent no-op if unread; plaintext passphrase on a readable card |
| **Ethernet-first** | Plug in a cable | n/a | n/a | No hotspot | n/a | Many homes have no cable where the device lives |
| **USB gadget (`rpi-usb-gadget`)** | Pi presents a USB Ethernet adapter to a host | Apache-2.0 | In Trixie images from 2025-10-20 per the article; repository README describes inclusion as future (conflict recorded, see N01-8) | No hotspot; a wired USB network instead | No page, but the address is *fixed* (`10.12.194.1` when the host has no ICS) | Takes the chosen port out of host duty; Windows needs a driver installer; one Pi per host at a time; `.local` may not resolve on Windows without Bonjour |
| **Serial console** | UART login shell | n/a | Part of Pi OS | n/a | n/a | On Pi 5 the primary UART is the debug header, not GPIO 14/15; developer-only |

### Corrected claims in the rows above

- **"Comitup's 3-second pins 39/40 action is a re-entry example."** Withdrawn. That
  option is `enable_nuke`, it is off by default (`enable_nuke: 0`), and it
  **deletes all defined Wi-Fi connections** before restarting Comitup. It is a
  Wi-Fi factory reset, not a re-arm. See
  [Comitup's destructive reset](#comitups-destructive-reset-and-equivalents).
- **"WiFi Connect disables the AP, tries, and re-opens on failure"** is kept — it is
  the project's own wording — but it is now used as *evidence for the constraint*
  rather than as a feature summary. Every single-radio tool in this table has the
  same hole, so the hole is a design input, not a defect in one tool.
- **"Comitup's AP is open by default"** is kept, and its `ap_password` constraint
  (8–63 characters) is now the source for Debra's own minimum.
- **Comitup's `web_service` option** is added to the comparison: it disables a named
  systemd service while the hotspot is up and enables it when a normal connection
  exists. That is a documented mechanism for "the full device UI is not reachable
  from the hotspot network", which N01 asked for but did not source.
- **RaspAP's AP-STA quote** is kept as a *vendor statement about its own feature*.
  The real constraint is the driver's advertised interface combination
  (`iw list`), and RaspAP's own page shows an example where AP plus managed *is*
  advertised with `#channels <= 1`. So the accurate claim is: concurrency is
  chipset-dependent and, when available, forces one channel — not that concurrency
  is universally impossible.
- **USB gadget "only port / data-only"** is corrected. The article says the chosen
  port "will function exclusively as USB networking + power input; it will no
  longer operate as a regular USB host port". So the port still supplies power, the
  claim is port-specific, Zero boards have a separate `PWR IN` port, and a Pi 5
  keeps its other USB-A host ports. It is a rescue candidate, not a universal
  fallback.
- **"Two Debra devices onboarding at once can collide on `10.12.194.1`"** is
  downgraded to a caution, because the same article says to connect only one
  Raspberry Pi at a time in gadget mode. The address collision is real arithmetic;
  the multi-device scenario is explicitly discouraged upstream, not merely untested.

## The flow, and its states

### Why the original flow cannot work

Stated precisely, because "impossible" needs a scope:

1. An access point and a client association are two modes of the same radio.
   Without driver support they are mutually exclusive: bringing the client up takes
   the access point down.
2. The device's address on the household network is assigned by that network's DHCP
   server, so it does not exist until the client association succeeds.
3. The user's browser reaches the setup page only over the access point.
4. Therefore, at the moment the address first exists, there is no page and no
   client to display it to. The information the user needs is created at exactly
   the instant its delivery channel is destroyed.

Two honest qualifications, both of which the design must respect rather than
pretend away:

- **It is possible to show a *stale* address by re-raising the hotspot after the
  join.** AP up, client down, serve "I joined; last known address was
  `192.168.1.42`". That costs a second association, and the address may differ on
  re-association, so the page can be wrong. This is offered below as an optional,
  test-gated refinement — not as the primary mechanism.
- **It is possible to show a *live* address if the driver advertises AP plus
  managed and both are on one channel.** That is the concurrent machine below. It
  is conditional on hardware, on the driver, and on knowing the household access
  point's channel before the hotspot starts.

### Machine A — concurrent (conditional, not the chosen flow)

Preconditions, all of which must be checked at runtime and none of which is verified
on any Debra board:

- `iw list` on the exact board advertises a combination containing both `AP` and
  `managed`.
- The household access point's channel is known from the scan, and the Debra
  hotspot is pinned to that channel (`802-11-wireless.band` plus
  `802-11-wireless.channel`; `channel` requires `band`).

Flow: hotspot up on the household channel → user picks an SSID → the client profile
associates on a second interface while the hotspot stays up → the page polls and
shows the live address → the user is told they may close the page. No disconnection
step exists, so no "the hotspot is about to disappear" copy is needed. If the
household access point moves channel, the hotspot must follow or the pair breaks —
which is why this machine cannot be the default even where it works.

### Machine B — single radio, nonconcurrent (the chosen flow)

The user-visible contract, in order. The address is never promised; the name always
is.

| # | State | Device does | User sees |
| --- | --- | --- | --- |
| 1 | `BOOT` | Derives the device name from hardware (N02), sets the hostname | Nothing yet; power LED only |
| 2 | `RADIO_OFF` | Detects "no WLAN country, dual-band board", radio disabled | Not reachable over Wi-Fi at all; the builder's preselected country, or a non-Wi-Fi path, is the only way forward |
| 3 | `AP_UP` | Raises `Debra-<id>` (WPA2, per-device passphrase, pinned legal channel), serves the portal, starts a 15-minute idle timer | "Join **Debra-3c6b3f**. Password: (on the label)." Then a page: choose your home Wi-Fi, enter its password |
| 4 | `TRIAL_SAVED` | Writes the household credentials as a *trial* profile (`autoconnect=no`, `autoconnect-retries=1`), keeps the old profile untouched | "Saving. Debra will now try to join **HomeWiFi**. This setup network will disappear — that is expected. Debra will appear on your network as **debra-3c6b3f.local**. Write that down. [ Continue ]" |
| 5 | `AP_DOWN` | Stops the hotspot, starts the trial association | The page stops loading; the phone shows "connected, no internet" or drops to mobile data. This is the designed discontinuity |
| 6 | `VERIFYING` | Layers: associated → routable address (never `169.254.x.x`) → default route → DNS or HTTP probe | Nothing (no channel to the user) |
| 7 | `JOINED` | Writes `debra-address.txt` to the boot partition, announces mDNS, keeps the hotspot down, promotes the trial profile to `autoconnect=yes` | The phone rejoins the home Wi-Fi on its own if it is a saved network; the user opens `http://debra-3c6b3f.local` |
| 8 | `FAILED` | Records the cause class, removes the trial profile, re-raises the hotspot with the same SSID and passphrase for a bounded window | "Rejoin **Debra-3c6b3f** to try again." Then one cause and one action (below) |
| 9 | `REARM` | Physical button, or N boots without an uplink, raises the hotspot again without touching saved profiles | Same as state 3, with "Last time Debra could not join **HomeWiFi**" |
| 10 | `ONLINE` | Normal operation; the full device UI is served on the LAN only | `http://debra-3c6b3f.local` → Debra's own pages |

### State diagram in text

```text
                              power on
                                 |
                            [1] BOOT
                    country missing /    \ country set (builder, or later)
                    radio disabled /      \
                         [2] RADIO_OFF   uplink already up? --yes--> [10] ONLINE
                              |                | no
             non-Wi-Fi path:  |                v
             USB gadget,      |            [3] AP_UP  <---------------------+
             Ethernet,        |                |                           |
             serial,          |          user submits                     |
             card edit        |                v                           |
                              |        [4] TRIAL_SAVED  (name + warning)  |
                              |                |                           |
                              |          [5] AP_DOWN / ASSOCIATING        |
                              |          (phone disconnected here)        |
                              |                |                           |
                              |          [6] VERIFYING                    |
                              |          /            \                   |
                              |     success          failure              |
                              |        |                |                 |
                              |   [7] JOINED      [8] FAILED ------------+  (same SSID/PSK,
                              |        |           bounded window)           result page)
                              |        |                |
                              |        |          user walked away
                              |        |                |
                              |        |          [9] REARM (button, or 3 boots
                              |        |           with no uplink) --> [3]
                              |        v
                              +--> [10] ONLINE  (name announced; address recorded
                                                in debra-address.txt; full UI on LAN)
```

Failure inside states 4–6 always returns to 3 or 9, never to a state where nothing
is listening. That property — *every* failure path has a listening surface — is the
requirement; the specific windows are proposals.

### What happens when the hotspot disappears

This is the part beginners will not predict, so it is stated in the product copy and
again here:

- **The page dies.** Any half-filled form is lost. The form is therefore only
  submitted whole, and the credentials live in the trial profile from that moment —
  not in the browser.
- **The phone may look broken.** It either rejoins the home Wi-Fi automatically
  (if that network is saved) or stays on a network with no internet. The page's
  last instruction covers both: "If your phone seems stuck, turn Wi-Fi off and on."
- **The old setup address is dead.** `10.42.x.1` (NM's default shared subnet) now
  belongs to nothing, or to some other device. It is never printed as a permanent
  address and never bookmarked.
- **The setup network name is reusable.** On failure the hotspot returns with the
  same SSID and passphrase, so the phone already has it saved and reconnecting is
  one tap rather than a password. Changing the passphrase per attempt would be
  safer against guessing and much worse for the user; the retry rate limit is the
  compromise.
- **Silence is not failure.** If the join actually succeeded and the user walked
  away, the device is on the LAN and discoverable by name. Nothing needs to be
  undone.

## How the user finds the device afterwards

N01 listed six routes and called mDNS unreliable. The corrected rule is stronger:
**the name is promised before the drop; the address is never promised at all.**
Routes, in the order the product copy should present them:

| Route | How it works | Reliability | Evidence |
| --- | --- | --- | --- |
| **The name, announced in advance** | `http://debra-<id>.local` — printed on the last setup page, in the quick-start card, and on the label | Works on iOS, macOS and most Linux desktops; **may not resolve on Windows without Bonjour**; Android browsers vary | [Pi USB gadget article](https://www.raspberrypi.com/news/usb-gadget-mode-in-raspberry-pi-os-ssh-over-usb/) (Windows/mDNS note); RFC 6762 §3 |
| **The router's client list** | The device sends its hostname in DHCP (`ipv4.dhcp-send-hostname` defaults TRUE), so the household router lists `debra-<id>` | High — the router is the thing that assigned the address | [NM ipv4 settings](https://networkmanager.dev/docs/api/latest/settings-ipv4.html); [Pi networking docs](https://raw.githubusercontent.com/raspberrypi/documentation/master/documentation/asciidoc/computers/configuration/configuring-networking.adoc) |
| **The boot-partition record** | `debra-address.txt` on the FAT partition: hostname, IP, state, timestamp — **no SSID, no credentials** | High, needs a card reader and a power-off; FAT is not atomic, so keep the file tiny and rewrite rarely | proposal; FAT-on-boot-partition mechanics from [rpi-preseed](../research/2026-11-15-rpi-preseed.md) |
| **A second device on the home network** | A laptop that was never on the hotspot can resolve the name or read the router list *while* the phone still holds the portal — the only route that gives the address before the drop | High, but requires two devices | inference |
| **A DHCP reservation** | Router pins the address to the device's MAC | High, and it is what the Pi docs recommend over a static IP | [Pi networking docs](https://raw.githubusercontent.com/raspberrypi/documentation/master/documentation/asciidoc/computers/configuration/configuring-networking.adoc) |
| **USB gadget** | Fixed `10.12.194.1` when the host has no ICS | Works with no network at all, needs a host and a cable | [Pi USB gadget article](https://www.raspberrypi.com/news/usb-gadget-mode-in-raspberry-pi-os-ssh-over-usb/) |
| **A screen** | Show the address on a display | Not in the current bill of materials | n/a |

Two rules that follow:

- **The name may change, and the device must say so.** RFC 6762 §9 requires a host
  that loses a name conflict to stop using the name, and recommends appending "2"
  or incrementing a number, probing again, **recording the new name in persistent
  storage**, and **displaying a message to the user**. So a headless device cannot
  silently become `debra-3c6b3f-2.local`: the chosen name must be persisted, written
  to `debra-address.txt`, and shown on the next page load. Whether Avahi's exact
  rename format matches that recommendation is `unknown`.
- **Do not use `connection.mdns` to try to fix this.** NM's per-connection `mdns`
  property only works with the `systemd-resolved` DNS plugin, and Pi OS uses Avahi
  for `.local`. Advertising is Avahi's job.

## Bad credentials

N01 said "never show a bare connection failed" and gave a cause table. The review
found the table over-claimed exact causes. The corrected rule: **report the class the
device can actually observe, and never invent a cause.**

| Observable condition | What the device knows | What the user sees | Next action offered |
| --- | --- | --- | --- |
| The supplicant rejects the key ("Secrets were required, but not provided" is the documented `nmcli` outcome for a wrong password) | Wrong key, almost certainly | "The password for **HomeWiFi** was not accepted." | Retry, password field focused, SSID kept |
| The SSID is not in the scan | Out of range, or off, or hidden | "**HomeWiFi** is not visible now. It may be out of range or turned off." | Rescan; "enter the name manually" for a hidden network |
| Association succeeds, no address before the DHCP timeout (default is device-specific, usually 45 s) | Joined, no lease | "Debra connected to **HomeWiFi** but did not get an address." | Retry; mention the router |
| Address present, default route present, DNS/probe fails | Local network works, internet does not | "Debra joined **HomeWiFi**. The internet is not reachable from it." | **Continue** — a LAN-only network is valid for Home Assistant — or retry |
| The radio reports disabled, or the scan is empty and the country is unset | Country gate | "This model needs a country setting before its Wi-Fi can be used." | Country picker (non-Wi-Fi path) |
| Security type the device cannot complete (SAE-only, 802.1X) | Type mismatch | "**HomeWiFi** uses a security type Debra could not complete." | Name the type; do not claim the password is wrong |
| A channel the selected country forbids | Regulatory refusal | "**HomeWiFi** is on a channel that is not allowed in the selected country." | Offer a country change, with the warning |

Retry mechanics that keep the device reachable:

- The trial profile is created with `autoconnect=no` and `autoconnect-retries=1`.
  Documented meaning: the default is `-1` (4 tries), and `1` means "try activation
  only once before blocking autoconnect". A failing profile must never be allowed
  to compete with the hotspot for the radio on every boot.
- A failed trial is deleted (not merely disabled) once the cause is recorded, so it
  cannot be resurrected by a later priority change.
- The hotspot returns **before** the failure is reported, so the page that reports
  it exists. Reporting first and restoring the AP second is the N01-1 bug in a new
  costume.
- Proposed limits: 5 submissions per 10 minutes per hotspot session, then the form
  is rate-limited with a visible "wait N seconds" message. The point is to bound
  passphrase guessing and to stop a stuck loop, not to punish typing.
- The password field is always cleared after a failure; the SSID is kept. Nothing
  from the form is echoed back, ever.
- **Never log the passphrase.** The failure record contains: SSID, timestamp, cause
  class, and the NM device state — nothing else.

## Credential storage and cleanup

N01 claimed the PSK lives *only* in `/etc/NetworkManager/system-connections/*.nmconnection`.
That is not established, and the cloud-init path shows why: on Raspberry Pi OS,
cloud-init stores the generated `network-config` in `/etc/netplan/` **"without
modification"**, and Netplan then produces NetworkManager profiles that appear under
`/run/NetworkManager/system-connections/` with a `netplan-` prefix. Deleting the
seed on the FAT partition therefore proves nothing.

| Copy | Where | Contains the PSK? | Permissions / handling | Evidence |
| --- | --- | --- | --- | --- |
| Boot-partition seed | `network-config` on the FAT partition | Only if the builder wrote credentials there | World-readable on any computer. **Debra's design: no credentials in the seed at all** | [Pi cloud-init article](https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/) |
| Netplan copy | `/etc/netplan/*.yaml` | Yes, if the seed had them | Root-owned; verify mode on the real image | same |
| Netplan-generated NM profile | `/run/NetworkManager/system-connections/netplan-*.nmconnection` | Yes | Runtime only (tmpfs), gone on reboot | same |
| Debra's own profile | `/etc/NetworkManager/system-connections/*.nmconnection` | Yes — `psk=` in plaintext | Root-only; **verify `0600` on the image rather than assuming it** | [Pi networking docs](https://raw.githubusercontent.com/raspberrypi/documentation/master/documentation/asciidoc/computers/configuration/configuring-networking.adoc) (the password is editable there) |
| cloud-init instance data | under `/var/lib/cloud/` | Yes, if cloud-init consumed credentials | `cloud-init query userdata` returns the decoded user-data to root; non-root sees redaction | [cloud-init instance-data](https://cloudinit.readthedocs.io/en/latest/explanation/instancedata.html) |
| Journal / portal log | `/var/log/`, journald | Must never | Portal logs SSID and cause class only | proposal |
| Debra's own snapshots and backups | wherever the snapshot backend writes | **Yes, if taken after Wi-Fi setup** | The brief already says personal recovery points contain credentials and must never be distributed; this note makes that concrete for the PSK | [brief](../project-brief.md) |
| The user's phone | browser history/autofill | Possibly | Outside the device's control; disclosed in the guide | inference |

Design consequences, in order of importance:

1. **The image ships with no Wi-Fi credentials.** Then the only copies that ever
   exist are the ones the portal creates, and "cleanup" is a short, checkable list.
2. **The portal never writes the PSK to a temporary file.** It hands it to
   NetworkManager directly (D-Bus `AddAndActivateConnection`, or `nmcli --ask`
   reading stdin), so the first place it lands is NM's own keyfile. Anything Debra
   writes itself is a copy Debra then has to erase.
3. **After success, remove what is redundant, keep what is needed.** Removed: the
   trial profile's duplicate if one was made, the portal's in-memory copy, and any
   temp file (none, by rule 2). Kept: the NM keyfile (the device must reconnect
   after a reboot) and, if present, the cloud-init/Netplan copies — which are the
   ones that need an explicit decision rather than an accident.
4. **Cloud-init's retained copies need a deliberate step.** `cloud-init clean`
   removes the state under `/var/lib/cloud/`, with the caveat that it also makes
   cloud-init treat the next boot as a first boot. Whether that is acceptable on
   Debra's image is a question for the builder task, not something to do blind.
5. **A card pulled from a half-configured device must not leak the household
   passphrase.** With rule 1 that is automatic: the seed never held it.
6. **Never enable NetworkManager secret logging.** The keyfile is plaintext by
   design; the log is not.

Device-side secrets are separate and are *not* the household PSK: the hotspot
passphrase (WPA2, 8–63 characters, per device, printed on the label) and the first
admin credential. No `debra/debra`, no shared key — the Comitup image's documented
`comitup`/`comitup` default is exactly the pattern to avoid.

## Comitup's destructive reset, and equivalents

Stated plainly, because N01 recommended it as ordinary recovery:

> **`enable_nuke`** — "Comitup will monitor, on a Raspberry Pi, for a short between
> pins 39 and 40. If the short is maintained for 3 seconds, the device will delete
> all defined WiFi connections, flash the board LED 3 times, and restart Comitup."
> Default: `0` (off).
> — [comitup.conf](https://raw.githubusercontent.com/davesteele/comitup/main/conf/comitup.conf), checked 2026-11-15

So the pin short is a **Wi-Fi factory reset**: every saved network is gone,
including the household one that was working. It contradicts N01's own rule that the
previous profile is kept as a fallback, and it is the worst possible action on a
device whose owner has just moved it.

**How to avoid it:** do not enable `enable_nuke`; do not describe pins 39/40 as a
re-entry button in any Debra guide; and if Comitup is ever shipped, ship it with the
option explicitly `0` and a comment saying why. A pin short is also a poor input for
a beginner in general — it needs a jumper wire and a steady hand.

Equivalents in the alternatives, for completeness:

| Tool | Destructive action | Equivalent? |
| --- | --- | --- |
| Comitup | `enable_nuke` deletes all Wi-Fi connections | **Yes, explicit and optional** |
| WiFi Connect | None documented; it saves the configuration only after a successful connection and re-opens the AP on failure | **No** — its failure path is non-destructive |
| RaspAP | No reset button; but the installer rewrites host networking (`dhcpcd.conf`, `dnsmasq`, services) | **No**, though the install itself is a broad mutation |
| Debra's own portal | Must never have one | Design rule below |

Debra's rule: **no action anywhere deletes a working network profile.** "Forget this
network" is per-network, confirmed in the UI, and available only when another
working path exists. A factory reset, if it ever exists, is a physical action
documented in the recovery guide — not a side effect of a button hold.

## Re-entry and reconfiguration

N01's three entries were right in shape and wrong in detail. Corrected:

1. **Physical.** A deliberate input raises the hotspot for a bounded window
   (proposal: 10 minutes) and changes nothing else. It must be Debra's own input — a
   button on the HAT where one exists — and must not be pins 39/40 if Comitup is
   installed, because that pair is the nuke. The input must be debounced and must
   not fire from a single stray pulse.
2. **Automatic.** N consecutive boots with no uplink raise the hotspot (proposal:
   3). This needs persistent state (a small counter, root-owned, reset on success)
   and must not count boots where Ethernet already has a route. Without the counter
   the rule is unimplementable, which N01 did not say.
3. **Logical.** From the LAN web UI, changing Wi-Fi uses a checkpoint:
   `nmcli device checkpoint --timeout <seconds> -- connection up <new>` runs the
   command with a configuration checkpoint and restores it if confirmation is not
   given before the timeout (the CLI prompts; the default is 15 s). A headless
   service would use the equivalent D-Bus checkpoint calls and confirm them when
   the new uplink is proven, which is the same mechanism without a terminal
   prompt — *that D-Bus equivalence is not independently checked here*.
   In addition, the old profile stays enabled with a lower `autoconnect-priority`
   until the new one is proven, so a rollback has somewhere to land.

Two rules that N01 got right and this revision keeps: the hotspot must not start
when a working uplink exists (checked across all interfaces, not just `wlan0`), and
"never reboot to apply Wi-Fi".

## Country and band

The gate is real and is quoted verbatim from the current documentation:

> "On Raspberry Pi devices equipped with dual-band wireless, networking is
> automatically disabled as a safety measure until a Wireless LAN (WLAN) country is
> set. This applies from Raspberry Pi 3B+ onwards, Compute Module 4 onwards, and all
> keyboard computers (Raspberry Pi 400, 500, and 500+)."

Consequences, which the review's N01-6 correctly identified as unresolved:

- **A country picker inside the Wi-Fi portal cannot be the first step on a Pi 5 with
  no country**, because the portal has nothing to run on. The country must arrive
  from the builder (the documentation itself says it is "typically set when you
  install an OS onto your boot media using Imager", and cloud-init's
  `regulatory-domain` key is the scriptable form) or through a non-Wi-Fi path:
  USB gadget, Ethernet, serial, or editing the card.
- **A country chosen for an unspecified destination is not a safe factory default.**
  The documentation's warning is blunt: incorrect settings "can cause legal issues,
  increased interference, reduced capacity, and degraded connectivity". A device
  built for one country and shipped to another is a regulatory problem, not a
  support ticket.
- **The detection must be specific.** The documented check is `nmcli radio wifi`
  returning `enabled`/`disabled`. "Radio disabled because no country" must be
  distinguished from "no networks in range", because the fixes are different —
  and `nmcli radio wifi on` does not set a country.
- **A wrong country fails in two directions.** It restricts what the device may
  transmit on (so the hotspot may refuse to start on a chosen channel) and what it
  may receive or join (so a household network on a channel the configured domain
  forbids becomes invisible or unjoinable). Exact per-country channel tables are
  not asserted here; they are regulatory data, not something to infer from one
  source.
- **Changing country must not strand a working connection.** It is a
  reconfiguration, so it goes through the checkpoint path above, with a plain
  warning that channels may disappear.
- **The hotspot's channel must be legal in the selected country.** Pinning a fixed
  2.4 GHz channel is safer during onboarding than "auto", and it is mandatory in
  Machine A where the hotspot must match the household access point.
- **Zero 2 W is 2.4 GHz only, so the gate probably does not apply to it** — that
  remains a `hypothesis`. Do not design around it and do not claim it: the
  documented list is about dual-band boards, and no Debra test exists.

## Security of the open captive portal

N01 said "the AP is open by default in both Comitup and WiFi Connect; Debra must
not inherit it" and left the reasoning implicit. The reasoning is what makes it
non-negotiable:

**While an open hotspot is up, everything on it is readable by anyone in radio
range.** There is no encryption and no authentication, so:

- **The household passphrase crosses the air in cleartext.** The form is HTTP
  (there is no trusted certificate for `10.42.x.1`), so a passive listener nearby
  captures the exact credential the whole flow exists to protect. This alone rules
  out an open hotspot for a form that accepts a PSK.
- **Anyone can submit.** A neighbour can point the device at their own access point,
  or at a network that does not exist, and either way the owner's setup fails or the
  device ends up somewhere unexpected.
- **The SSID list leaks location.** The scan results shown on the page are a
  fingerprint of the neighbourhood.
- **An impostor hotspot harvests the user's password.** The instruction "join
  `Debra-3c6b3f` and type your Wi-Fi password" trains the user to do exactly the
  thing an evil-twin attacker wants. A per-device WPA2 passphrase printed on the
  label is the defence: the impostor does not know it, so the user's phone refuses
  to join the wrong network.
- **Whatever the device listens on is exposed on that interface.** The portal must
  bind to the hotspot interface only, and nothing else — no SSH, no device UI, no
  file endpoints — may answer there before enrolment.

Mitigations, all of them already in the flow above: WPA2 with a per-device
passphrase (8–63 characters, matching Comitup's documented constraint), the
passphrase printed on the device rather than derived from anything guessable, a
15-minute idle timeout, the hotspot stopping on success, the portal exposing
onboarding only, no credentials in URLs, one submission at a time, and a retry rate
limit. Comitup's `web_service` option is the documented pattern for gating the real
UI on "hotspot up" versus "normal connection" — Debra can implement the same rule
itself.

Honest limit: a WPA2 hotspot with a printed passphrase protects against the
neighbour and the evil twin, not against someone holding the device. Physical
possession ends the argument.

## Finding-by-finding changes

| Finding | What changed | Where in this note |
| --- | --- | --- |
| **N01-1** High — single-radio sequence cannot stop the AP, verify the new address, and display it on a still-reachable page | The impossible sequence is withdrawn and the reason is stated as a four-step argument. Two state machines are defined: **Machine A** (concurrent or two-radio, AP stays up, live address, conditional on `iw list` plus a shared channel) and **Machine B** (single radio: disconnect *before* the attempt, restore the AP *with the saved result* on failure, independent post-join discovery). The address is never promised; the name is announced before the drop | "Why the original flow cannot work", "Machine A", "Machine B", state diagram |
| **N01-2** High — the 3-second pins 39/40 action is `enable_nuke`, destructive, and contradicts keeping a fallback | Quoted verbatim with its default, reclassified as a Wi-Fi factory reset, excluded from Debra's guides, and replaced by a non-destructive physical re-arm on Debra's own input. Equivalents in WiFi Connect and RaspAP recorded as absent or different | "Comitup's destructive reset, and equivalents", "Re-entry and reconfiguration" |
| **N01-3** High — "credentials live only in NM keyfiles" is unproved; seed cleanup proves nothing | Replaced with a seven-row copy map (FAT seed, `/etc/netplan/`, `/run/NetworkManager/system-connections/netplan-*`, the NM keyfile, `/var/lib/cloud/`, logs, Debra's own snapshots, the user's phone), each with its evidence. The design now ships an image with **no** Wi-Fi credentials, passes the PSK straight to NetworkManager, and treats `cloud-init clean` as a deliberate decision with a stated caveat. Keyfile `0600` is marked "verify", not asserted | "Credential storage and cleanup" |
| **N01-4** Medium — requiring a route plus DNS conflicts with the LAN-only "continue anyway" case | Split into four independent layers (associated, routable address, default route, DNS/internet) with "continue anyway" as a first-class success for a LAN-only network. The cause table is rebuilt around what the device can observe, with "wrong password" tied to the documented `nmcli` outcome and other rows labelled as classes rather than invented diagnoses | "Bad credentials", "Machine B" state 6 |
| **N01-5** Medium — a 2.4 GHz-only radio cannot show a 5 GHz SSID greyed out | Withdrawn. The scan list shows only what the radio observes; a phone-assisted or manually typed SSID is named as a different, unverified workflow; the band limitation is explained in copy instead of faked in a list | "Bad credentials" (scan row and its note) |
| **N01-6** Medium — a country picker on the Wi-Fi portal cannot help when the radio is disabled, and an unspecified factory country is unsafe | Country is now a builder-supplied input or a non-Wi-Fi path, quoted from the documentation with the affected models; the "incorrect settings" warning is quoted; detection is tied to `nmcli radio wifi`; both failure directions (transmit and join) are stated; per-country channel tables are explicitly not asserted; Zero 2 W remains a hypothesis | "Country and band" |
| **N01-7** Medium — "only port" and "data-only" are inaccurate | Corrected: the port becomes USB networking **plus power input**, the claim is port-specific, Zero boards keep a separate `PWR IN`, Pi 5 keeps its other host ports. Recorded as a rescue candidate with a Windows driver requirement, one-Pi-per-host guidance and a `10.12.194.1` fallback | Comparison table, "Corrected claims in the rows above", "How the user finds the device afterwards" |
| **N01-8** Medium — gadget inclusion conflict; "no ARMv6 asset" does not prove a source build fails; proposals presented as requirements | The article-versus-repository conflict is recorded as unresolved instead of asserted; the WiFi Connect row keeps "no armv6 asset" and now says plainly that this does not prove a source build fails; the portal, the rejected alternatives and the seed choice are labelled as proposals for the open reuse/onboarding decision | Comparison table and its notes |

Additional corrections made while revising, not raised by the review:

- **AP isolation does not block the phone from reaching the Pi.** `ap-isolate`
  blocks station-to-station traffic on the same access point; the station can still
  reach the access point itself. What breaks `.local` in a real household is a guest
  network that puts the phone on a different subnet or VLAN, or blocks inter-client
  traffic. NM also exposes `802-11-wireless.ap-isolation` directly, so Debra's own
  hotspot can be explicit about it.
- **A "60-second grace period" before stopping the AP was pointless.** It was
  proposed so the user could read the address; there is no address to read. It is
  replaced by a "Continue" button (or a short idle timeout) whose only job is to let
  the user write down the *name*.
- **mDNS on Windows is not a given.** The Pi gadget article tells users to install
  Bonjour or fall back to an IP. That belongs in the quick-start card, not in a
  support call.
- **Comitup's image ships `comitup`/`comitup` default credentials** with SSH enabled.
  That is a second reason not to ship a Comitup image unmodified.

## Verification

- Exact safe commands/procedure and working directory: none run. No card was
  flashed, no Pi contacted, no hotspot raised, no network or router setting changed,
  nothing installed.
- Observed results: **not-run** for every row of the comparison and every state of
  both machines. No Debra hardware test exists for this note.
- What was actually done: read the original note, the review's N01 findings, the
  brief, the evidence rules and the learning-note template; retrieved the public
  pages listed in the frontmatter on 2026-11-15; read the Raspberry Pi
  configuration documentation from its asciidoc source because the rendered page
  returned HTTP 403; ran the offline documentation test suite (below).
- Not tested, conflicting evidence, and remaining uncertainty: see
  [Still unknown](#still-unknown).
- Sanitized artifact references: none.

## Still unknown

- **Does the Pi's Wi-Fi driver advertise AP plus managed on any board Debra cares
  about, and on which channels?** Machine A is unimplemented and unverified. The
  `iw list` check is the gate and has not been run on a Debra board.
- **Does Comitup run on Pi OS Lite trixie?** Still no Trixie statement; Bookworm
  already needed a newer `python3-networkmanager`.
- **Does the country gate really skip the Zero 2 W?** Unverified hypothesis; the
  documented list names dual-band boards only.
- **Where exactly does cloud-init retain `network-config`, and for how long?** The
  Pi article places a copy in `/etc/netplan/`; the cloud-init documentation
  establishes retained `user-data` under `/var/lib/cloud/` and root-readable
  `cloud-init query userdata`. Whether `network-config` is retained identically, and
  what `cloud-init clean` removes on the Pi build, needs a mounted-card inspection.
- **What mode are NM keyfiles actually on the Debra image?** `0600` root is the
  expectation, not a measurement.
- **Does Avahi rename on conflict, and to what?** RFC 6762 §9 recommends appending
  "2" and persisting the result; the Avahi manual page does not state the format.
  The device must report whatever it chose, which is a design requirement either
  way.
- **How long does association plus DHCP actually take on each board**, and therefore
  how long the failure-to-hotspot window should be? Unmeasured; the DHCP timeout
  default is device-specific and usually 45 s, which is a bound, not a measurement.
- **Will a phone rejoin the returning hotspot by itself** after a failed attempt, and
  will it stay on a hotspot with no internet long enough for a beginner to finish
  typing? Both vary by platform and are untested.
- **Does a captive-portal auto-popup still work on current iOS and Android with a
  WPA2-protected hotspot?** Unknown; the page must also be reachable by typing the
  address.
- **Is `wpa_supplicant.conf` on the boot partition still read?** Unchanged from N01:
  absent from the current guide, which is not proof either way.
- **Which WPA3/SAE and 802.1X cases work** on the Pi firmware and `wpa_supplicant` in
  Trixie: unknown.
- **Does `rpi-usb-gadget` work with the Trixie images Debra will ship?** The
  inclusion claim conflicts between the article and the repository.
- **Debra-specific:** whether Debra ships its own portal or adopts Comitup remains a
  coordinator decision, not this note's.

## Handoff and correction links

- Current state: N01's comparison and failure matrix are corrected; the flow is
  physically possible on one radio; no implementation selected; no hardware touched.
  Base revision `b23ed98`.
- Concrete next action: N04 should test, on a leased board and a disposable SSID, in
  this order: (1) the country gate with no country set on a dual-band board, (2) the
  `iw list` concurrency question for Machine A, (3) wrong password → hotspot returns
  → retry, (4) a LAN-only network reaching "continue anyway", (5) `debra-address.txt`
  written and readable after a successful join, (6) `.local` resolution from iOS,
  Android, Windows and Linux, (7) the non-destructive re-arm, and (8) a checkpointed
  reconfiguration that rolls back.
- Authorization needed: none of the above is permission to flash, reconfigure the
  household router, or install packages.
- Earlier claim superseded: the whole of
  [N01](2026-11-15-wifi-onboarding-options.md), specifically N01-1's flow,
  N01-2's re-entry example, N01-3's credential claim, N01-4's success criteria,
  N01-5's greyed 5 GHz entry, N01-6's portal-based country step, N01-7's USB port
  wording and N01-8's unqualified inclusion claim. The original note is preserved
  unchanged.
- Reviewed report/decision that later adopts this finding: none yet. This note is
  itself unreviewed.

## Sources cited in this note

Public pages, all checked 2026-11-15, all mutable except the RFC and the man page:

- [Comitup configuration file](https://raw.githubusercontent.com/davesteele/comitup/main/conf/comitup.conf)
- [Comitup project page](https://davesteele.github.io/comitup/)
- [Cloud-init on Raspberry Pi OS](https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/)
- [Raspberry Pi networking documentation (asciidoc source)](https://raw.githubusercontent.com/raspberrypi/documentation/master/documentation/asciidoc/computers/configuration/configuring-networking.adoc)
- [NetworkManager ipv4 settings](https://networkmanager.dev/docs/api/latest/settings-ipv4.html)
- [NetworkManager connection settings](https://networkmanager.dev/docs/api/latest/settings-connection.html)
- [NetworkManager 802-11-wireless settings](https://networkmanager.dev/docs/api/latest/settings-802-11-wireless.html)
- [NetworkManager 802-11-wireless-security settings](https://networkmanager.dev/docs/api/latest/settings-802-11-wireless-security.html)
- [nmcli reference](https://networkmanager.dev/docs/api/latest/nmcli.html)
- [RFC 6762, Multicast DNS](https://www.rfc-editor.org/rfc/rfc6762.txt)
- [avahi-daemon.conf(5)](https://manpages.debian.org/bookworm/avahi-daemon/avahi-daemon.conf.5.en.gz)
- [cloud-init instance-data](https://cloudinit.readthedocs.io/en/latest/explanation/instancedata.html)
- [WiFi Connect](https://github.com/balena-os/wifi-connect)
- [USB gadget mode in Raspberry Pi OS](https://www.raspberrypi.com/news/usb-gadget-mode-in-raspberry-pi-os-ssh-over-usb/)
- [RaspAP AP-STA mode](https://docs.raspap.com/features-experimental/ap-sta/)

Repository records this note relies on without re-deriving:
[project brief](../project-brief.md), [evidence rules](../evidence.md),
[N01](2026-11-15-wifi-onboarding-options.md),
[the independent review](2026-11-15-research-notes-review.md),
[device discovery](../design/device-discovery.md),
[web control](../design/web-control.md),
[rpi-preseed](../research/2026-11-15-rpi-preseed.md),
[preliminary findings](../research/2026-11-14-preliminary-findings.md),
[the lab Pi 5 hang record](../testing/results/2026-11-15-lab-pi5-silence-and-hang.md).
