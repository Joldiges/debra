---
title: Optional network and household services a Debra device could run
date: 2026-11-15
type: project-learning
status: unreviewed
task: none (coordinator-assigned desk research)
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - Pi-hole documentation, "Prerequisites" — https://docs.pi-hole.net/main/prerequisites/ (checked 2026-11-15)
  - AdGuard Home README, master — https://github.com/AdguardTeam/AdGuardHome (checked 2026-11-15)
  - avahi-daemon.conf(5), Debian bookworm — https://manpages.debian.org/bookworm/avahi-daemon/avahi-daemon.conf.5.en.gz (checked 2026-11-15)
  - chrony 4.6, chrony.conf(5) — https://chrony-project.org/doc/4.6/chrony.conf.html (checked 2026-11-15)
  - Home Assistant apps repository, Mosquitto broker DOCS.md — https://github.com/home-assistant/apps/blob/master/mosquitto/DOCS.md (checked 2026-11-15)
  - Uptime Kuma README, master — https://github.com/louislam/uptime-kuma (checked 2026-11-15)
  - Homepage README, main — https://github.com/gethomepage/homepage (checked 2026-11-15)
  - Home Assistant Glances integration — https://www.home-assistant.io/integrations/glances/ (checked 2026-11-15)
  - Pi.Alert README (archived, renamed NetAlertX) — https://github.com/jokob-sk/Pi.Alert (checked 2026-11-15)
supersedes: []
---

## Summary

Desk study only: nothing here was installed, run or measured on Debra hardware, so
there are **no `tested` claims**. The decisive test applied to every candidate is
"what happens to the household when this device is off, updating or broken?".
On that test, most popular Pi services fail: a room voice satellite is a
replaceable peripheral, while DNS, DHCP and message brokering are house-wide
utilities whose failure is felt by every device at once. Recommended: keep the
image to NTP-client, mDNS-advertise and self-health-reporting; put Pi-hole,
brokers and dashboards on a separate always-on host if wanted at all.

Labels per [evidence](../evidence.md), applied per statement: `D`
upstream-documented, `R` third-party/vendor claim not independently checked,
`U` unknown/inferred. Existing mDNS facts are not repeated here; see
[device discovery](../design/device-discovery.md).

## Candidates

| Candidate | What it needs | Maintainer / activity | Memory, CPU, boot | Household when off / updating | Duplicates HA? | Verdict | Ev. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pi-hole | Static IP or DHCP reservation; exclusive UDP/TCP 53; 512 MB RAM and 2 GB free disk stated minimum; FTL ships prebuilt for armv6/armv7/aarch64 | Pi-hole project, active, Debian/RPi OS supported | Stated floor is 512 MB — the whole RAM of a Pi Zero W; boot/update cost on Debra unmeasured | If it is the DHCP-advertised resolver, every client loses name resolution until it returns or the client falls back to a second resolver; a failed update is house-wide | Partly: HA is unaffected (it resolves its own peers), but HA integrations that use hostnames on other clients do suffer | Nowhere | D,U |
| AdGuard Home | DNS 53 plus admin UI; single Go binary; GPL-3.0; builds for any Go OS/arch | AdGuard, active, very widely used | Go binary plus embedded web UI; available official armv6 asset unconfirmed | Same blast radius as Pi-hole | Same | Nowhere | D,U |
| DHCP server (Pi-hole / AdGuard / dnsmasq / NM `shared`) | Ports 67/547, authority over the subnet, correct lease/gateway/DNS options | Upstream projects offer it; the household router also does | Low, but the *role* is what matters | Losing the DHCP server is worse than losing DNS: renewals fail, new devices get nothing, and a wrong option taken at boot misconfigures clients silently (also a rogue-DHCP hazard) | Duplicates the router, which is the device that owns the link | Nowhere | D,U |
| chrony as **NTP server** | `allow <subnet>` (default denies all clients); `local` reference mode for isolated networks, default stratum 10 | chrony project, active, packaged everywhere | Negligible; small `clientloglimit` memory for per-client state | Losing a local time source is mild — clients keep their own clocks, drift slowly, and resync later; it is the one utility here whose failure is survivable | HA does not publish a local NTP service; no documented HA requirement for one was found | Separate device only, if ever | D,U |
| chrony (or systemd-timesyncd) as **NTP client** | Reachable upstream NTP at boot | Same packages Debra already has | Negligible | Nothing household-wide; only this device's own clock | No — this is baseline plumbing | Image | D |
| Avahi service advertisement | `avahi-daemon` already present; publishes `_debra._tcp` | Debian/freedesktop, packaged | Small, already counted in the discovery design | Only Debra peers stop seeing this device; nothing else notices | No — it is the mechanism `_debra._tcp` needs | Image (already) | D |
| Avahi mDNS **reflector** | `enable-reflector=yes` plus two or more interfaces *on the same host*; `reflect-filters` limits what crosses | In the packaged daemon; upstream warns against running more than one reflector between the same networks | Small, but only meaningful on a multi-interface box | Reflecting nothing is harmless; a misconfigured or doubled reflector causes packet ping-pong (documented upstream), i.e. a *new* fault rather than a fallback | No; it extends discovery. But it belongs on the gateway, which has the interfaces | Router, not Debra | D |
| Uptime Kuma | Node.js ≥ 20.4, or Docker, plus pm2; 20-second check intervals; SQLite-like local data | louislam, active, MIT, very large issue backlog | Node runtime on a Zero is disproportionate; boot cost unmeasured | Nothing breaks; monitoring simply stops — and *silently*, which is the classic monitoring-of-monitoring problem | Partly: HA already has per-entity availability, Ping and notification automations | Separate device | D,U |
| Homepage / Homer | Docker images built for AMD64 and ARM64 only; Next.js app; `docker.sock` for container widgets | gethomepage, active | No armv6/armv7 image stated; heavy runtime for a link page | Nothing breaks — it is a page of links | No, but it is a convenience, not infrastructure | Nowhere | D |
| Glances (HA integration) | `glances` in web server mode; HA Glances integration polls it | Nicolargo + HA core integration (one named owner) | Python agent, modest; per-host | Nothing breaks; you lose this host's metrics | Partly: HA's own system sensors cover the HA host, not Debra | Optional package (or fold into Debra's own health page) | D,U |
| Mosquitto MQTT broker | Broker on 1883/1884/8883; ACLs and per-client users | Eclipse Mosquitto, active; also shipped as the official HA app | Small in isolation, but adds a second broker with its own identity model | Losing a broker breaks every MQTT client at once: ESPHome-style devices drop, HA MQTT entities go unavailable | **Yes, outright**: HA's own Mosquitto app is the documented broker, tied to HA users | Nowhere | D |
| NetAlertX (formerly Pi.Alert) | Docker (hardware install marked experimental); `arp-scan` needs raw-socket privileges; optional UniFi / Pi-hole / DHCP-lease imports; GPL-3.0 | Renamed and moved by the author; the original repo is archived, a hardware-install fork exists | Container + scanner; scanning a subnet is bursty | Nothing breaks; the device map goes stale | Partly: HA's DHCP discovery and device registry already record joins | Separate device, if a map is really wanted | D,U |
| Debra health → HA (proposal, no new daemon) | Reuse the existing web/diagnostic data; publish as HA entities or MQTT | Debra itself | Nearly zero — it is data Debra already collects | Only this device's telemetry pauses | No; it feeds HA instead of competing with it | Image | U |

## Recommendations

1. **NTP client in the image; NTP server nowhere.** A Debra must know the time
   for TLS, logs and scheduling, and a Pi has no RTC, so it syncs at boot (`D`).
   Serving time is a different job: `allow` is off by default and `local`
   exists precisely for isolated networks (`D`). A per-room stratum-2-ish source
   adds accuracy nobody asked for while adding a new always-listening UDP port
   on every satellite (`U`). **Image / nowhere.**
2. **Keep mDNS as advertisement only; reflect on the router or not at all.** The
   reflector is a documented Avahi option but needs the multiple interfaces a
   gateway has, and upstream explicitly warns about doubled reflectors (`D`).
   Debra's `_debra._tcp` already works on a flat LAN and publishes nothing
   secret; a reflector does not fix a network that blocks multicast, it just
   moves the problem (`U`). **Image (publisher) / router (reflector).**
3. **Make each Debra report its own health, and let HA hold the dashboard.** The
   device already collects diagnostics for its own web page; surfacing them as
   HA entities is cheap, and HA already owns availability, notifications and
   history (`U` proposal, `D` for HA having those features). This answers most of
   what Uptime Kuma and Glances would be installed to answer, on the hardware
   that is already there, without a second database of truth (`U`).
   **Image.**
4. **If James wants ad-blocking, monitoring or a broker, give it its own
   always-on host** — the HA machine, a Pi 4/5, or a NAS — documented in Debra as
   an *optional household service* with its own recovery story (`U`). A device
   whose failure is felt only in one room should not host a service whose failure
   is felt in all of them (`U`). **Separate device.**

## Do not run here, and why

- **Pi-hole / AdGuard Home: no.** Both are excellent, and both are house-wide
  single points of failure (`U`). If one becomes the DHCP-advertised resolver,
  a reboot during an update, a full disk (Pi-hole states 2 GB minimum, 4 GB
  recommended, `D`) or a dead microSD takes name resolution away from every
  device in the house at once — including the phones needed to debug it (`U`).
  The Pi Zero W's total RAM equals Pi-hole's stated floor (`D`,`U`), so the
  satellite would be running a house-wide utility at its own memory limit. That
  is a bad tenant on a voice device: the failure mode is exactly reversed from
  what a satellite should have.
- **DHCP server: no, and more strongly than DNS.** DHCP is the bootstrap of the
  network. A wrong option or a stale lease misconfigures clients silently rather
  than failing visibly, and a rogue DHCP server is a known hazard (NetAlertX
  even ships a rogue-DHCP detector, `D`). The household router already owns the
  link, is the device that keeps working when Debra is unplugged, and is what the
  Raspberry Pi networking documentation recommends pairing with a reservation
  (`D`). A voice satellite must never be authoritative for address assignment.
- **MQTT broker: no.** HA's Mosquitto app is the documented broker, integrated
  with HA's user system and disallowing anonymous logins (`D`). A Debra-hosted
  broker duplicates it, splits the topic namespace, and makes one satellite the
  dependency of every MQTT client (`U`). A Debra may be an MQTT *client*; it must
  not be the broker.
- **Uptime Kuma / Homepage / Homer / NetAlertX: no.** All four are dashboards or
  scanners that answer questions HA or the router already answer (`U`), all are
  container-first with no armv6 story stated (`D`), and none of them being down
  breaks anything — which is precisely why they do not deserve an always-on slot
  on a $40 device. "Network map" is only a real need when you are hunting an
  unknown device; that is a task, not a permanent service (`U`).
- **Anything that owns a radio for the house** (Zigbee/Z-Wave coordinator stacks,
  BLE presence scanning) belongs on the HA host, next to the USB stick and the
  backup (`U`, `D` none — not researched here).

## Open questions

- What is the household network actually like: flat LAN or VLANs, is multicast
  passed, is there a second DNS resolver already? Unsurveyed (`U`, also open in
  the discovery design).
- What do Pi-hole, AdGuard Home, Uptime Kuma and Mosquitto actually cost in RAM
  and boot time on a Pi Zero W / Zero 2 W? Unmeasured — the 512 MB figure above
  is a project statement, not a Debra measurement (`U`).
- Does Home Assistant document any requirement for a local NTP server? None was
  found; treat "HA cares about time" as `U` until a primary source is read.
- Is a household-level service bundle a Debra deliverable at all, or a linked
  recommendation to the HA documentation? This note assumes the latter (`U`).
- Would a "hub" Debra role (a Pi 4/5 that may host optional services) be a
  product tier, or is that out of scope because HA already exists? (`U`)

Evidence tally for this note: 20 `D`, 0 `R`, 14 `U`; 0 `tested`. The AdGuard
feature-comparison table is vendor-authored and was deliberately not used.
