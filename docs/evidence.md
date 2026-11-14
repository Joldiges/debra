# Evidence, comparisons, and source register

Established 2026-11-14. This file defines reporting conventions and research
starting points; it is not a hardware-validation report.

## Separate intent, evidence, and maturity

“Required” describes the product goal. “Supported” is a maintained,
version-scoped promise backed by tests. Neither follows merely from a source
mentioning a feature.

Use these evidence labels per claim, not once for an entire page:

| Label | Meaning |
| --- | --- |
| `tested` | A linked test record names exact hardware, versions, procedure, and observed result |
| `upstream-documented` | A linked primary source states this; Debra has not independently reproduced it |
| `reported` | A linked third-party report or attributed user observation; include context and limitations |
| `hypothesis` | An inference or experiment to try, not a capability/buying promise |
| `unknown` | Insufficient evidence; never turn an empty cell into “no” |
| `historical` | A dated claim or artifact retained for investigation, not current advice |

Record pass/fail/partial/not-run separately from evidence level. A failed test
on one version is not proof that every configuration is unsupported.

For each meaningful factual claim include:

- A direct source URL or repository file/commit reference, and date checked.
- Relevant product revision, OS/kernel, architecture, software version/commit,
  and configuration scope where applicable.
- A distinction between source statements, user reports, measurements, and
  inferences. Note conflicts and unresolved prerequisites.
- For mutable upstream docs, resolve a version/commit before relying on them
  for an installer pin or release.

## Comparison records

Prefer primary vendor/project docs for specifications and compatibility,
upstream code/releases/issues for implementation constraints, and tests for
actual behavior. Shopping listings support price/availability, not software
support or sound-quality claims.

Hardware rows should identify the exact revision/variant, inputs/outputs,
microphone topology, speaker/amplifier needs, power requirements, driver/kernel
constraints, optional peripherals, dimensions/enclosure implications,
measured versus advertised quality, and source/evidence links.

For alternative boards, assess mechanical/header fit, pin mapping and voltage/
power, I2S/I2C and other required interfaces, driver/device-tree support, and
the exact maintained OS/kernel separately. Do not infer HAT compatibility from
header pin count or CPU architecture. Record board-native audio expansions
and USB options too; distinguish documented compatibility from a Debra test.

Cost rows should record:

- Currency/market, date, seller/link, selected variant, and quantity.
- Item price, shipping/tax assumptions, and whether a bulk unit price requires
  buying more units than a typical user needs.
- Separate complete-purchase and reuse-existing-parts totals.
- Explicit power, storage, cable, speaker, and enclosure assumptions.
- Known availability/quality uncertainty; historical README prices are not
  current measurements.

Software rows should separate protocol, receiver implementation, server,
Home Assistant integration, and audio backend. Compare required servers,
supported architectures, pairing/discovery, synchronization and delay controls,
voice interruption behavior, recovery, maintenance, licensing, and evidence.
Do not compare a music server to a transport protocol as interchangeable peers.

## Test records

Future reports belong in `docs/testing/results/` with no raw secrets. Include:

```text
Task / date / author / exact model identifier when AI-authored:
Device alias / board and HAT revision / power and storage:
OS / kernel / CPU architecture / Python and component versions:
Server versions and relevant configuration:
Purpose / procedure / commands / expected result:
Actual observations / metrics / pass-fail-partial-not-run:
Sanitized artifact references:
Recovery point / restoration test, if relevant:
Limits / follow-up / reviewer:
```

Never place raw Wi-Fi profiles, private keys, pairing records, tokens, complete
serial/MAC inventories, or populated snapshots in a public report. Keep the
private mapping from aliases to operational access details in `.local/access/`,
raw logs in `.local/logs/`, and private recovery payloads in `.local/snapshots/`
inside the project, outside Git. Follow the
[development workspace guide](development.md) for permissions and backup
limitations. Redact before export, not after a credential-bearing bundle is
committed; publish sanitized reports in tracked paths.

For performance, publish the method and conditions as well as the number:
distance/noise/playback level for voice; CPU/RAM/temperature and duration for
resource tests; measurement method and uncertainty for multiroom skew.
Propose thresholds before declaring a device acceptable; do not invent
measurements or borrow upstream performance numbers as our own.

## Initial source register

Sources below were read on **2026-11-14**, except the explicitly blocked page.
Main-branch documentation is mutable. These are starting evidence, not pinned
dependencies or endorsements of every upstream installation command.

| Source | What was observed / how to use it |
| --- | --- |
| [Linux Voice Assistant](https://github.com/OHF-Voice/linux-voice-assistant) | Describes an ESPHome-protocol Home Assistant satellite; currently lists AMD64/AArch64, local wake detection, timers, announcements, and peripheral APIs. ARMv6 support remains an investigation, not a documented upstream baseline. |
| [LVA behavior guide](https://github.com/OHF-Voice/linux-voice-assistant/blob/main/docs/behavior.md) | Describes its own music/assistant players and their duck/pause/resume behavior. Does not establish behavior for an independent SendSpin/Snapcast process. Timers do not by themselves establish persistent alarm support. |
| [SendSpin Python CLI](https://github.com/Sendspin/sendspin-python-cli) | The old `Sendspin/sendspin-cli` URL redirected here. Current docs describe daemon/TUI modes, audio settings, discovery, pairing, persistent identities, and version-dependent server requirements. Recheck current implementation before designing the adapter. |
| [Snapcast](https://github.com/snapcast/snapcast) | Describes separate server/client roles, grouping, audio backends, delay/buffering, and distribution-specific packages. Old blanket “non-Debian unsupported” claims should not be reused. |
| [PiCompose](https://github.com/florian-asche/PiCompose) | Existing pi-gen-based prepared images for LVA/Snapcast and several audio boards. Research/reference candidate, **not a selected Debra foundation or dependency**. Assess information/partial reuse as well as adoption, architectures, licensing, resource cost, update policy, and onboarding gaps. Reference-only or another approach are valid outcomes. No Debra hardware test performed. |
| [pi-gen](https://github.com/RPi-Distro/pi-gen) | Image builder with separate 32-bit/64-bit branch guidance and build-host constraints. Upstream notes that Docker builds still access host kernel/device facilities; do not treat privileged builds as a harmless syntax check. |
| [NetworkManager](https://github.com/NetworkManager/NetworkManager) | Describes connection profiles and CLI/TUI clients. A network manager is not by itself a complete captive-portal onboarding solution; evaluate actual portal candidates and Pi Wi-Fi behavior. |
| [systemd hostname rules](https://www.freedesktop.org/software/systemd/man/latest/hostname.html) | Documents lowercase alphanumeric/hyphen hostnames. Supports the proposed `debra-<id>` spelling; do not assume every feature in the latest systemd manual exists on the selected Pi OS. |
| [Git submodules guide](https://git-scm.com/docs/gitsubmodules) and [command reference](https://git-scm.com/docs/git-submodule) | `upstream-documented`: a parent repository records a submodule commit separately from the fetch URL/path in `.gitmodules`; initialization is needed to populate sources, and `update --remote` selects a remote-tracking revision instead of the parent pin. Basis for the proposed dependency workflow in [development](development.md), not a claim that Debra already has or has tested submodules. |
| [GitHub repository visibility](https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories#about-repository-visibility) | Public repositories are accessible to everyone; private repositories restrict access. There is no unlisted-public setting. |
| [Raspberry Pi configuration docs](https://www.raspberrypi.com/documentation/computers/configuration.html) | Fetch returned HTTP 403 during this session. Not reviewed; obtain current official configuration/onboarding guidance before choosing a mechanism. |
| Local history at `bc81d9b` | See [legacy findings](legacy-findings.md). Code shows attempted workarounds, not successful test results. |

Add deeper primary sources as each research task proceeds. Especially missing:
current HAT revision/driver guides, complete hardware prices, factory/onboarding
tool comparisons, filesystem/recovery documentation, and exact ARMv6 dependency
requirements.
