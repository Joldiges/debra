---
title: Captive-portal DNS in NetworkManager shared mode
date: 2026-11-15
type: project-learning
status: unreviewed
task: N02
author: OpenCode research subagent (debra-research)
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - "https://raw.githubusercontent.com/NetworkManager/NetworkManager/1.52.0/src/core/dnsmasq/nm-dnsmasq-manager.c (checked 2026-11-15: shared-mode dnsmasq argv, --conf-file=/dev/null, no --no-resolv, CONFDIR dnsmasq-shared.d, --conf-dir only when the directory exists)"
  - "https://raw.githubusercontent.com/NetworkManager/NetworkManager/main/src/core/dnsmasq/nm-dnsmasq-manager.c (checked 2026-11-15: same structure on main)"
  - "https://thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html (man updated 2025-02-05: -r/-R resolv behaviour, -A/address= semantics, wildcard address=/#/x for queries not otherwise answered)"
  - "https://networkmanager.dev/docs/api/latest/NetworkManager.conf.html (checked 2026-11-15: documents dnsmasq.d, not dnsmasq-shared.d)"
  - "https://manpages.debian.org/bookworm/network-manager/NetworkManager.conf.5.en.html (1.42.4; same absence)"
  - "https://unix.stackexchange.com/questions/575226/create-a-captive-portal-with-network-manager-nmcli (2021)"
  - "https://alaneuler.me/blog/nmcli_gateway and https://op-co.de/blog/posts/samsung_nx_mastodon/ (2024-07-05; wildcard-to-AP in practice)"
  - "https://learn.microsoft.com/en-us/windows-server/networking/ncsi/ncsi-overview (2025-02-25: Windows probe and payload)"
  - "https://developer.apple.com/news/?id=q78sq5rv (2020-06-22: Apple automatic probe; option 114 / RA 37 alternative needs TLS)"
  - "https://isc.sans.edu/diary/33172 (2026-07-21: four-OS probe list, and that lists change)"
  - "https://github.com/openNDS/openNDS/issues/170 (2021: clients reported rejecting a private address in the probe answer)"
supersedes: []
---

## Summary

The queued concern is real: NetworkManager's shared mode starts dnsmasq with
`--conf-file=/dev/null` and **without** `--no-resolv`, so its upstreams come
from `/etc/resolv.conf`. With no uplink there is nothing to forward to, so the
operating system's probe hostname does not resolve to the portal and the
sign-in sheet never opens. NM does pass
`--conf-dir=/etc/NetworkManager/dnsmasq-shared.d` to that instance **when the
directory exists**, which gives Debra a one-file fix with no new package and no
new service:

```
/etc/NetworkManager/dnsmasq-shared.d/50-debra-captive.conf
address=/#/10.42.0.1
```

The main limits: `dnsmasq` must actually be installed and NM must pass that
`--conf-dir` on the image's NM version (read in 1.52.0 and main only), the
wildcard must name the address the AP really has, and whether a phone shows the
sheet for a private-address answer plus a `302` is contested in reports. None of
that is settled by this note; it needs one device run.

## Claims and evidence

| Kind | Claim | Source / scope | Verification and limits |
| --- | --- | --- | --- |
| upstream-documented | Shared mode runs dnsmasq per interface with `--conf-file=/dev/null --no-hosts --keep-in-foreground --bind-interfaces --except-interface=lo --clear-on-reload --strict-order --listen-address=<gw> --dhcp-range=... --dhcp-leasefile=... --pid-file=...` | NM `nm-dnsmasq-manager.c`, 1.52.0 and main, checked 2026-11-15 | Read from source; not executed here |
| upstream-documented | `CONFDIR` is `NMCONFDIR "/dnsmasq-shared.d"`, and `--conf-dir=` is added only if that directory exists (dnsmasq exits if a named conf dir is absent) | same file | Explains why the directory must be created before the AP is raised |
| upstream-documented + hypothesis | No `--no-resolv` and no `address=`/`server=` redirect is generated, so upstreams are read from `/etc/resolv.conf`; with no uplink the probe names do not resolve to the portal | same file (absence) + dnsmasq(8) | The absence is documented; the no-uplink failure mode is inference and needs a device probe |
| upstream-documented | DHCP option 6 is emitted only when the shared profile's L3 config has nameservers | same file | What the phone actually receives in the lease is unknown |
| upstream-documented | `address=/#/1.2.3.4` answers every query not answered from hosts/DHCP or a more specific server; since dnsmasq 2.86 non-A/AAAA types go upstream | dnsmasq(8) | Syntax and semantics documented |
| upstream-documented (absence) | `dnsmasq-shared.d` is not documented in `NetworkManager.conf(5)`; the documented per-instance dir is `dnsmasq.d` | NM.conf 1.52 and Debian 1.42.4 man pages | Treat as version-scoped until the image's NM is checked |
| reported | Operators use `dnsmasq-shared.d` with a wildcard to the AP address for a captive portal | StackExchange 2021, alaneuler 2024, op-co.de 2024 | Unverified on this project's image |
| upstream-documented | Windows probes `www.msftconnecttest.com/connecttest.txt`; Apple devices probe automatically on first join; the standard modern alternative is DHCP/RA option 114 with TLS | Microsoft NCSI, Apple developer news 2020 | Probe sets change over time, so per-host lists rot |
| reported, unresolved | Some operators report clients reject a private address in the probe answer as interception; others report wildcard-to-AP works | openNDS #170 (2021) vs the 2024 reports above | Conflicting; only a phone run settles it |

## Recommended configuration (proposed, not implemented)

1. Create `/etc/NetworkManager/dnsmasq-shared.d` (mode `0755`) before the AP is
   raised.
2. Write `/etc/NetworkManager/dnsmasq-shared.d/50-debra-captive.conf` (mode
   `0644`) containing `address=/#/<AP address>`. Prefer making the AP address
   deterministic (`ipv4.method shared` with `ipv4.addresses 10.42.0.1/24`)
   instead of assuming the `nmcli device wifi hotspot` default: a wildcard that
   names an address the AP does not have is worse than no wildcard.
3. Do not expect `connection.ipv4.dns` to redirect dnsmasq's answers; it is not
   the same setting. If the lease turns out to carry no DNS server, set
   `ipv4.dns=10.42.0.1` on the profile rather than adding a second DHCP option.
4. Reject alternatives: Debra's own resolver (new dependency and port-53
   conflict with NM's dnsmasq), option 114/RA 37 (Apple requires TLS with a
   valid certificate; the portal is plain HTTP), and doing nothing (leaves the
   card-note address as the only route).

## Verification

- Exact safe commands/procedure and working directory: not run. A host-side
  check could start dnsmasq with the copied argv and a copied fragment and
  answer `dig`/`curl`; that proves syntax and the redirect only.
- Observed results: not-run.
- Device checks that would settle it: `command -v dnsmasq`; with the AP up,
  `sudo tr '\0' '\n' </proc/$(pgrep -x dnsmasq)/cmdline | grep -E 'conf-dir|resolv|listen-address'`;
  from a laptop on the AP, `dig @10.42.0.1 connectivitycheck.gstatic.com +short`
  and `curl -sI http://connectivitycheck.gstatic.com/generate_204`; from a phone,
  the lease's DNS server, then forget/rejoin the SSID and watch for the sheet.
- Not tested, conflicting evidence, and remaining uncertainty: dnsmasq presence
  on the target image; whether the image's NM passes `--conf-dir`; the lease's
  DNS server; phone behaviour for a private-address answer; AAAA-only clients;
  probe timing against portal readiness.
- Sanitized artifact references, if any: none.

## Handoff and correction links

- Current state and relevant base/candidate revision: research only, no files
  changed; the setup subsystem is under review at `f9c5e7b` and must not be
  edited until that review is resolved.
- Concrete next action and prerequisites: after the review, add the directory
  and fragment to the setup service's AP path (or the image build), make the AP
  address explicit, and run the device checks above on a named Pi and card.
- Authorization needed; do not treat this suggestion as permission: this note
  does not authorize a radio, a phone, or a network change. A device run needs
  James's named target and recovery path, as in
  [`docs/testing/first-boot-trial-plan.md`](../testing/first-boot-trial-plan.md).
- Earlier claim superseded, if this is a correction: none.
- Reviewed report/decision that later adopts this finding, if known: none.
