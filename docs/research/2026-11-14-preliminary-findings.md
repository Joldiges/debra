# Preliminary research: corrected findings and remaining gaps

**2026-11-14 — source research, not completed roadmap packets.** Six read-only
submissions were triaged separately: Pi/HAT, ARMv6, onboarding and recovery
needed material corrections; speaker and reuse research were usable with
qualifications. This short synthesis keeps the useful evidence, not the drafts'
unsupported conclusions. R01/R04/N01/B01/Z01/D01 remain incomplete; no dependency,
backend, supported combination or enclosure matrix is selected here.

Author: OpenCode coordinator, `openrouter/openai/gpt-6.1-sol`, host-selected
`flex-xhigh`. Researchers: the same model via OpenAI `xhigh` for speaker/reuse;
`openrouter/deepseek/deepseek-v4.1-flash-1017#high` for the other four. Triage:
separate OpenRouter Sol `flex-xhigh` context, not cross-model independence for
Sol-authored material. All source checks below are dated **2026-11-14**.

## Mechanical inputs for SolidCraft

These are **upstream-documented**, not measurements of James's specimens.
The coordinator visually inspected the Pi PDF and Waveshare dimension image;
James also supplied their rendered content in the conversation.

| Part/source | Usable input | Still unknown; do not infer |
| --- | --- | --- |
| [Pi Zero 2 W product brief](https://datasheets.raspberrypi.com/rpizero2/raspberry-pi-zero-2-w-product-brief.pdf), published April 2024, pp. 3–4 | 65 × 30 mm outline; mounting centres 3.5 mm from the corresponding edges, 23 mm between rows. With origin at the drawing's lower-left board corner, derived centres are (3.5, 3.5), (61.5, 3.5), (3.5, 26.5), (61.5, 26.5) mm: 58 × 23 mm pitch. Drawing labels connector x datums 12.4, 41.4 and 54 mm. | Hole diameter, board thickness, full connector envelopes, component heights, microSD service travel and assembled HAT clearances are not established by this drawing. The 3.5 mm labels are offsets, not hole diameters. |
| [Waveshare SKU 14595 illustration](https://www.waveshare.com/img/devkit/accessories/8ohm-5w-speaker/8ohm-5w-speaker-size.jpg) and [product page](https://www.waveshare.com/8ohm-5w-speaker.htm) | Illustration annotates one module as 92 × 36 mm. The research draft separately recorded the page's 100 × 45 × 21 mm claim; these are conflicting/ambiguous inputs, not interchangeable geometry. | Height, mounting pattern, rear envelope, acoustic openings, connector/polarity and equivalence to the pair actually supplied with a HAT. Do not silently combine the image's footprint with the page's 21 mm figure. |
| [Waveshare WM8960 wiki](https://www.waveshare.com/w/index.php?title=WM8960_Audio_HAT&oldid=105389) | Dual MEMS microphones, 3.5 mm output, LP/LN/RP/RN speaker connections and GPIO17 button. Wiki separately states 8 Ω/5 W supplied speakers and 1 W/channel HAT output into 8 Ω BTL. | Connector construction, LED absence, extra-HAT stacking safety and microphone-port coordinates. The draft's purported 8 mm/male-header FAQ is absent; the actual FAQ discusses **kernel** headers. |

Keep the four historical loose-speaker listing identities separate:
[`B0B4D1BN4F`](https://www.amazon.com/dp/B0B4D1BN4F),
[`B0B4D2Z35P`](https://www.amazon.com/dp/B0B4D2Z35P),
[`B0BHST51PQ`](https://www.amazon.com/dp/B0BHST51PQ) and
[`B0BTP67F81`](https://www.amazon.com/dp/B0BTP67F81).
Direct listing retrieval failed in the speaker pass; indexed seller descriptions
and historical identifier mappings remain **reported**, not verified specimen
identities. In particular, the first listing's 31 × 28 × 15 versus 44 × 28 × 15 mm
conflict is not fit-ready geometry. Connector pitch text does not prove polarity
or mating compatibility.

**Next bounded result:** an exact-revision dimension/provenance table for one
Pi/HAT plus one identified speaker, then a reviewed first assembly. Apply the
[enclosure requirements](../design/enclosures.md): reusable trays/carriers,
removable lids/grilles/cloth frame, plug/wiring and card-removal space. Community
features are design ideas, not proven fits. HAT revision equivalence, stack
heights, microphone openings and vendor CAD redistribution permissions remain
unknown. No Debra CAD file, print, fit, thermal or acoustic test exists from this
research; the unrelated open SolidCraft design was left untouched.

## ARMv6: preserve the target, narrow the blockers

- **Upstream-documented:** the official [OS downloads page](https://www.raspberrypi.com/software/operating-systems/)
  lists current 32-bit Trixie as compatible with **all Raspberry Pi models**.
  Zero W appearing under Legacy does not exclude it from current 32-bit OS.
  The draft's Legacy-only/platform-wide Python blocker is withdrawn. Selected
  image/Python/dependency combinations still need exact-version verification.
- **Upstream-documented:** [LVA at `12e5127`](https://github.com/OHF-Voice/linux-voice-assistant/blob/12e51272d37d786ed3168955b3fb6eda3c7159ce/README.md)
  documents AMD64/AArch64, not an ARMv6 support promise. Research identified native
  wake dependencies as build/artifact risks; no suitable-build impossibility was
  established. The inspected [pymicro-features](https://pypi.org/pypi/pymicro-features/2.0.2/json)
  and [pyopen-wakeword](https://pypi.org/pypi/pyopen-wakeword/1.1.0/json)
  PyPI releases lacked 32-bit ARM wheels in that pass. This does not inventory all
  other distribution channels or establish that a source build fails.
- The [Sendspin CLI](https://github.com/Sendspin/sendspin-python-cli) is a playback
  receiver; do not transfer LVA's microphone-capture requirement to it. Exact
  released client/server pairing, Python and native audio dependencies remain
  open. Mutable branch requirements are not installer pins.
- **Unknown:** full-stack performance, wake accuracy/latency, audio underruns,
  memory and thermal behavior on original Zero W. Identical NumPy wheel hashes
  under two architecture tags are not themselves a defect or instruction-set
  blocker. Exact artifacts still need execution on ARMv6. Moving wake inference
  off-device removes that inference work but may add streaming work; net CPU
  effect and LVA remote-wake integration are unmeasured/unknown.

Next: finish a pinned OS/Python/native-artifact matrix before choosing the
smallest missing-artifact build experiment. No Pi 5/Zero 2 W result substitutes
for original Zero W execution, and no music-only downgrade is proposed.

## Onboarding: compare real portals without assuming safety

**Upstream-documented:** [Comitup](https://github.com/davesteele/comitup) uses
NetworkManager/systemd, creates a fallback hotspot and portal, remembers networks,
and describes a two-interface persistent-hotspot mode.
[WiFi Connect](https://github.com/balena-os/wifi-connect) documents disabling its
AP for a connection attempt and re-enabling it on failure. Its README's
Stretch/dhcpcd installation path is not a verified modern Pi OS procedure.
These are reuse candidates, not maintenance rankings or package selections.

Corrections retained from triage:

- No GitHub Release object does not prevent commit pinning or establish missing
  tags. Exact source/package pins and ARMv6 packaging remain unresolved.
- Single-radio AP/STA concurrency is hardware/driver/firmware dependent, not
  universally impossible. Reliable Zero-family behavior needs device tests.
- Comitup's documented `10.41.0.1` is a private AP-subnet address, not IPv4
  link-local ([RFC1918](https://www.rfc-editor.org/rfc/rfc1918.html),
  [RFC3927](https://www.rfc-editor.org/rfc/rfc3927.html)).
- [NetworkManager checkpoints](https://networkmanager.dev/docs/api/latest/nmcli.html)
  offer timeout-based restoration of checkpointed configuration, not guaranteed
  SSH availability or recovery from every reboot/failure.
- James's earlier Imager failures are **reported**; cause remains **unknown**.
  Country settings, credentials and band restrictions are test cases, not a
  diagnosis. Issue counts, language choice and CI badges do not prove maintenance
  quality or a smaller security risk.

Next: resolve pins and credential/account flow, then propose exact-board tests
for bad credentials, interrupted setup, portal shutdown/re-entry and hostname/IP
discovery. Use separately authorized disposable media/test networking; never
reconfigure the household router as a test.

## Recovery: partition coverage is not coherent capture

**Upstream-documented:** [rpi-clone's initialization](https://github.com/billw2/rpi-clone#clone-by-initialization)
copies partitioning information, makes filesystems and syncs files; it is not
synonymous with a sector-for-sector whole-device image. Its sequential boot/root
sync does not prove temporal consistency across kernel/modules/overlays and
application state. Rewriting PARTUUID references does not solve that problem.

The official [boot documentation](https://raw.githubusercontent.com/raspberrypi/documentation/master/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc)
states **all Pi models support `tryboot`**. The draft's Zero/Zero 2 exclusion is
withdrawn. That statement alone does not implement Debra A/B slots, application
health acceptance or demonstrate installed-firmware recovery behavior.

Keep [Btrfs snapshots](https://btrfs.readthedocs.io/en/latest/btrfs-subvolume.html),
incremental file-copy tools and [RAUC A/B](https://rauc.readthedocs.io/en/latest/scenarios.html)
as comparison candidates. No first backend is selected: coherent capture,
boot/root restoration, storage cost, unbootable rescue and timings remain
unproven. No restore-speed claim is justified by the word "incremental."
Never prune or overwrite recovery points; an upstream recycle option is not
permission to use it. Same-card rollback is not independent backup.

Next: complete the consistency/restore comparison and propose **directory-only**
fixtures without host `/`, devices or mounts. Loop-mount tests are a separate
privilege/authorization class, not inherently unprivileged. No capture, restore,
mount or historical backup script was run.

## Upstream reuse and licensing follow-up

The reuse researcher inspected LVA `12e51272d37d786ed3168955b3fb6eda3c7159ce`,
PiCompose `1e5ff410163bcbb4704daea0c277fccc63a91214` and pi-gen `master`
`6e3ff62bfd9c690a6a3d1d7de259d5e0af40cb78`; these are **research revisions, not
selected dependencies**. The pi-gen `arm64` pin remains unresolved.

PiCompose's pinned [LICENSE](https://github.com/florian-asche/PiCompose/blob/1e5ff410163bcbb4704daea0c277fccc63a91214/LICENSE)
says MIT while its [README](https://github.com/florian-asche/PiCompose/blob/1e5ff410163bcbb4704daea0c277fccc63a91214/README.md#license)
says BSD-3-Clause. Preserve both declarations and unresolved file/provenance
scope, rather than declaring blanket clearance. Partial stage/configuration
reuse, reference-only and another approach all remain valid. Pinning a parent
project does not pin mutable builder actions or transitive/runtime dependencies.

A separate F04 research draft suggested MIT for Debra-authored work and a
component/CAD provenance checklist. It is **not adopted**: a submodule or shared
image does not, by itself, settle whether works form an aggregate or a combined
work, and share-alike CAD is not categorically banned. Record the actual work,
license/version, modifications, notices, distribution form and uncertainty for
review ([GPLv3 §5](https://www.gnu.org/licenses/gpl-3.0.html#section5),
[CC license overview](https://creativecommons.org/share-your-work/cclicenses/)).
No copyright holder, contribution terms, CAD license or root LICENSE was applied.
Vendor-download availability does not establish redistribution permission.

## Verification, provenance and handoff

Research was limited to named repository reads and public-source retrieval.
The coordinator rechecked the principal OS, tryboot, Waveshare, portal,
rpi-clone and PiCompose conflicts; other detailed draft claims were deliberately
not promoted. No builds, dependency installs, devices, network changes, CAD
mutations or physical measurements occurred. Mutable sources need revision pins
before implementation. This is not a complete R01 cost inventory or any packet's
full acceptance evidence.

Private, ignored records: `.local/delegation/20261114-parallel-research/`
contains submitted reports, task scopes, triage and host model/cost metadata;
`.local/artifacts/enclosure-sources-20261114/` contains local-only source captures
and hashes. No vendor binary is redistributed here. A later corrected packet
should cite the applicable section rather than treating this synthesis as a
support claim. Production editing remains subject to [F05](../testing/results/2026-11-14-ai-readiness.md).
