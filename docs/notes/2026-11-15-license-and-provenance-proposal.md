---
title: License and provenance proposal for Debra
date: 2026-11-15
type: project-learning
status: unreviewed
task: F04
author: OpenCode subagent
author_model: openai/gpt-6.1-terra
author_variant: flex-high
sources:
  - "docs/roadmap.md F04, docs/project-brief.md, docs/development.md and docs/evidence.md at efcad08f5af4cd9af73b919933ef85bb043068b6"
  - "https://opensource.org/license/mit and https://www.apache.org/licenses/LICENSE-2.0, checked 2026-11-15"
  - "https://github.com/OHF-Voice/linux-voice-assistant/tree/12e51272d37d786ed3168955b3fb6eda3c7159ce, checked 2026-11-15"
  - "https://github.com/esphome/micro-wake-word-models/tree/40ff33f57f8fc6ad71a75ef085abbf742495b225, checked 2026-11-15"
  - "https://www.debian.org/doc/debian-policy/ch-docs.html#copyright-information, checked 2026-11-15"
supersedes: []
---

## Summary

**Proposal, not a decision or legal advice:** use **MIT for Debra-authored code
and documentation** when the relevant rights holders approve. It is short and
permissive; Apache-2.0 is a credible alternative with an explicit, limited
contributor patent grant and patent-litigation termination, but more detailed
notice/change requirements. Neither option licenses someone else's files or
settles physical-design, model, firmware, image, trademark, or patent rights.

Treat the CAD license separately; CERN-OHL-P-2.0 is a candidate, not a selected
license. Keep third-party materials under their own terms and **block release of
an affected artifact** if its model, firmware, source access, or other necessary
redistribution rights cannot be established. There is no complete Debra image
or completed image license audit here; James and the coordinator must review.

All external links in the six tables were checked **2026-11-15**. Labels apply
to the stated evidence, not to legal clearance: `upstream-documented` is a
source statement; `reported` is an attributed report; `hypothesis` is a
proposed interpretation or procedure; `unknown` is not established. Upstream
revision names below are evidence snapshots, **not Debra dependency selections**.
Scope is the requested Debra base `efcad08`; current HEAD advanced to `4b5085d`
only in an activity update/tool/test, not the F04 inputs.

## 1. Debra-authored code and documentation

| Material / evidence | License and distribution consequence | Source and checked scope |
| --- | --- | --- |
| `hypothesis` — Original Debra code, scripts and documentation | Recommend MIT for material the relevant holders can license: redistribution retains the copyright and permission notices. No separate patent grant appears in its short text; do not infer that it expressly grants one. Applicable third-party inclusions remain excepted. | [OSI MIT text](https://opensource.org/license/mit); [F04](../roadmap.md) and [brief](../project-brief.md), base `efcad08`; checked 2026-11-15. |
| `upstream-documented` — Apache-2.0 alternative | Sections 2–4 contain copyright and limited contributor patent grants, a patent-litigation termination provision, license-copy and changed-file notices, source-form notice retention, and applicable `NOTICE` attribution for distributed derivatives. It does not generally require publication of modifications. | [Apache-2.0 §§2–4](https://www.apache.org/licenses/LICENSE-2.0), checked 2026-11-15. |
| `unknown` — Existing Debra and AI-assisted contributions | Neither a named copyright holder nor authority to license every existing contribution is established by the model name, Git history, or this proposal. Review human contributions, generated content, copied text/images, and applicable provider terms before assigning copyright or applying a blanket notice. | [F04](../roadmap.md), [development guidance](../development.md), base `efcad08`; [MIT form](https://opensource.org/license/mit), checked 2026-11-15. |
| `hypothesis` — Contribution policy | After approval, define contributor assurance of permission, contribution terms, preservation of third-party notices and upstream attribution, plus a clear review for copied material; decide DCO, CLA or neither rather than silently imposing one. A contribution to an upstream follows its own terms, not automatically Debra's proposed MIT. | [Apache-2.0 §5](https://www.apache.org/licenses/LICENSE-2.0); [Debra contribution boundary](../development.md), checked 2026-11-15. |

## 2. Upstream code, wheels, and scoped patches

The obligations are conditional on what is actually copied, modified, linked,
or distributed. Independent programs placed on one image are not automatically
one derivative; a combined program, copied source, or linked library needs its
own compatibility review. Use the exact license text and packaging facts, not
the project-name shorthand.

| Material / evidence | License and distribution consequence | Source and checked scope |
| --- | --- | --- |
| `upstream-documented` — LVA and Sendspin CLI code | Apache-2.0; include license, applicable attribution/`NOTICE`, and prominent changed-file notices for distributed changes. The LVA code license does not by itself clear all its models, sounds or dependencies. | [LVA LICENSE](https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/12e51272d37d786ed3168955b3fb6eda3c7159ce/LICENSE.md); [Sendspin CLI LICENSE](https://raw.githubusercontent.com/Sendspin/sendspin-python-cli/e9a80e6afb6d4b00f8755b7bfd00bc4c20cbf503/LICENSE); [Apache §4](https://www.apache.org/licenses/LICENSE-2.0); checked 2026-11-15. |
| `upstream-documented` — Snapcast `v0.31.0` | Its Debian copyright file specifies GPL-3-or-later for `*`, with LGPL-2.1-or-later, zlib and MIT/Expat exceptions for named files. Conveying unmodified binaries still requires the applicable notices and a compliant corresponding-source route; patching additionally requires preserving notices and marking changes. | [Snapcast copyright](https://raw.githubusercontent.com/badaix/snapcast/v0.31.0/extras/package/debian/copyright); [GPL-3 §§4–6](https://www.gnu.org/licenses/gpl-3.0.html); checked 2026-11-15. |
| `upstream-documented` — Comitup `v1.47.1` | Its main Python file is SPDX `GPL-2.0-or-later`; audit the actual selected files and dependencies. Both unmodified and modified distributed copies have GPL obligations; a separate onboarding program is not automatically relicensed merely by co-installation. | [comitup.py header](https://raw.githubusercontent.com/davesteele/comitup/v1.47.1/comitup/comitup.py); [GPL-2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html); checked 2026-11-15. |
| `upstream-documented` — RAUC `v1.15.2`; NetworkManager `1.54.2`; PipeWire `1.4.9` | RAUC says LGPL-2.1-or-later. NetworkManager states GPL-2.0-or-later and LGPL-2.1-or-later; determine which files/packages apply. PipeWire says MIT except its ALSA plugin LGPL and JACK server GPL2; exact exception versions and shipped package contents require checking. LGPL distribution can require source, notices and a way for users to replace/relink a modified library, depending on how combined. | [RAUC license section](https://raw.githubusercontent.com/rauc/rauc/v1.15.2/README.rst); [NetworkManager](https://raw.githubusercontent.com/NetworkManager/NetworkManager/1.54.2/README.md); [PipeWire LICENSE](https://raw.githubusercontent.com/PipeWire/pipewire/1.4.9/LICENSE); [LGPL-2.1](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html); checked 2026-11-15. |
| `upstream-documented` — pi-gen and rpi-image-gen | The checked top-level licenses are BSD-3-Clause: retain specified notices/disclaimer in source and binary distributions and observe the non-endorsement clause. These are builder terms, not a license for all packages in their output. | [pi-gen LICENSE](https://raw.githubusercontent.com/RPi-Distro/pi-gen/6e3ff62bfd9c690a6a3d1d7de259d5e0af40cb78/LICENSE); [rpi-image-gen LICENSE](https://raw.githubusercontent.com/raspberrypi/rpi-image-gen/fb44a4cde4ac/LICENSE); checked 2026-11-15. |
| `upstream-documented` — Other candidates | WiFi Connect `v4.11.91`, pi-gen-micro `v0.4.1` and rpi-sb-provisioner `v2.3.5` have Apache-2.0 license files; Wyoming Satellite `v1.4.1` has MIT. rpi-preseed's mutable `main` copyright file states Apache-2.0 and its changelog says 0.2.1; no `v0.2.1` tag was found, so confirm a commit and distributed files before reuse. | [WiFi Connect](https://raw.githubusercontent.com/balena-os/wifi-connect/v4.11.91/LICENSE); [pi-gen-micro](https://raw.githubusercontent.com/raspberrypi/pi-gen-micro/v0.4.1/LICENSE); [provisioner](https://raw.githubusercontent.com/raspberrypi/rpi-sb-provisioner/v2.3.5/LICENSE); [Wyoming](https://raw.githubusercontent.com/rhasspy/wyoming-satellite/v1.4.1/LICENSE.md); [preseed copyright](https://raw.githubusercontent.com/raspberrypi/rpi-preseed/main/debian/copyright), [changelog](https://raw.githubusercontent.com/raspberrypi/rpi-preseed/main/debian/changelog); checked 2026-11-15. |
| `upstream-documented` — Shairport Sync | Its main Shairport Sync license is MIT, but `LICENSES` also identifies separately licensed included code; review actual build options and dependencies. | [LICENSES at 7ce90d8](https://raw.githubusercontent.com/mikebrady/shairport-sync/7ce90d89529dd760488f20592a7cbff626672f6c/LICENSES), checked 2026-11-15. |
| `unknown` — PiCompose | At `1e5ff41`, `LICENSE` contains MIT but README says BSD-3-Clause and links to that same file. **Do not choose either interpretation or copy/adapt its protected files on this basis**; seek maintainer clarification or separate permission. Its vendored `seeed-voicecard-v2` tree also needs its own file-level audit. | [LICENSE](https://raw.githubusercontent.com/florian-asche/PiCompose/1e5ff410163bcbb4704daea0c277fccc63a91214/LICENSE); [README](https://raw.githubusercontent.com/florian-asche/PiCompose/1e5ff410163bcbb4704daea0c277fccc63a91214/README.md); [reuse audit](2026-11-15-upstream-reuse-audit.md); checked 2026-11-15. |
| `unknown` — Transitive Python wheels, native libraries and containers | A package's own license does not clear its embedded `.so` files, models, vendored components or build dependencies. Enumerate wheel hashes, platform, metadata, bundled files and source/notice obligations for each exact release artifact; no complete inventory was audited. | [LVA dependency inventory](../research/2026-11-15-armv6-wheels.md); [LVA Dockerfile](https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/12e51272d37d786ed3168955b3fb6eda3c7159ce/Dockerfile), checked 2026-11-15. |

For any eventual fork or patch, record upstream URL, base commit, license,
copyright, patch authorship, modification dates, patch hashes, tests, release
source location and maintenance owner. Keep upstream changes distinct from
Debra integration, keep originals and notices, and follow upstream contribution
rules. A submodule or separate Git history helps trace provenance; it is not a
license exemption or a guarantee that archives contain the source.

## 3. Wake-word weights, other models, and sound assets

| Material / evidence | License and distribution consequence | Source and checked scope |
| --- | --- | --- |
| `upstream-documented` — ESPHome micro-wake-word collection | At `40ff33f`, the collection explicitly says its `.tflite` weights and `.json` manifests are Apache-2.0, with Open Home Foundation attribution in `NOTICE`. Include the license and applicable notices; names may also involve trademarks. | [README](https://raw.githubusercontent.com/esphome/micro-wake-word-models/40ff33f57f8fc6ad71a75ef085abbf742495b225/README.md); [NOTICE](https://raw.githubusercontent.com/esphome/micro-wake-word-models/40ff33f57f8fc6ad71a75ef085abbf742495b225/NOTICE); checked 2026-11-15. |
| `hypothesis` — Six LVA model pairs match the collection | Git tree blob IDs match for both JSON and TFLite of `alexa`, `choo_choo_homie`, `hey_home_assistant`, `hey_jarvis`, `hey_mycroft` and `okay_computer`; `choo_choo_homie`, `hey_home_assistant` and `okay_computer` are under `models/v2/experiments` in the collection. This supports applying the collection's stated terms to **those identical bytes**, subject to rights/provenance review, not to other LVA files. Example: `hey_jarvis.tflite` blob `0075302434cc72a460ced0b8f6c09c69214e5cf0` in both trees. | [LVA recursive tree](https://api.github.com/repos/OHF-Voice/linux-voice-assistant/git/trees/12e51272d37d786ed3168955b3fb6eda3c7159ce?recursive=1); [ESPHome recursive tree](https://api.github.com/repos/esphome/micro-wake-word-models/git/trees/40ff33f57f8fc6ad71a75ef085abbf742495b225?recursive=1); [collection terms](https://raw.githubusercontent.com/esphome/micro-wake-word-models/40ff33f57f8fc6ad71a75ef085abbf742495b225/NOTICE); checked 2026-11-15. |
| `unknown` — Remaining LVA micro-wake-word files | `hey_luna`, `hey_morgan`, `okay_nabu`, and `stop` JSON and TFLite files have **no identical blob** in the checked ESPHome tree; in particular LVA's `okay_nabu.tflite` is not the checked ESPHome v2 binary. Non-match does not prove they are unlicensed; trace each origin, version, hash and permission or exclude the affected bytes. | [LVA tree](https://api.github.com/repos/OHF-Voice/linux-voice-assistant/git/trees/12e51272d37d786ed3168955b3fb6eda3c7159ce?recursive=1); [ESPHome tree](https://api.github.com/repos/esphome/micro-wake-word-models/git/trees/40ff33f57f8fc6ad71a75ef085abbf742495b225?recursive=1); checked 2026-11-15. |
| `upstream-documented` / `unknown` — openWakeWord | `v0.6.0` says its **code** is Apache-2.0 but included pretrained models are CC-BY-NC-SA-4.0. The noncommercial and share-alike terms are incompatible with an unrestricted commercial-use promise for those covered models. The exact origin/license of LVA's `wakewords/openWakeWord/` files has not been matched to those artifacts: don't assume either Apache or CC terms merely from the folder name. | [openWakeWord license section](https://raw.githubusercontent.com/dscripka/openWakeWord/v0.6.0/README.md); [CC-BY-NC-SA-4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/); [LVA tree](https://api.github.com/repos/OHF-Voice/linux-voice-assistant/git/trees/12e51272d37d786ed3168955b3fb6eda3c7159ce?recursive=1); checked 2026-11-15. |
| `upstream-documented` — LVA sounds | Separate attribution states CC-BY-4.0 for Home Assistant Voice Preview Edition sounds by Clayton Charles Tapp. If distributed, preserve attribution, license link and indication of changes as applicable; check the exact asset mapping and other assets individually. | [LVA sounds notice](https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/12e51272d37d786ed3168955b3fb6eda3c7159ce/sounds/LICENSE.md); [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/); checked 2026-11-15. |

The pinned [LVA Dockerfile](https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/12e51272d37d786ed3168955b3fb6eda3c7159ce/Dockerfile)
copies the entire `wakewords/` and `sounds/` trees and removes `/usr/share/doc`.
An upstream container label saying Apache-2.0 therefore is not a complete
contents or notice audit. This is a source reading, not an inspection of an
actual pulled image. Checked 2026-11-15.

## 4. CAD, renders, printable exports, and physical parts

| Material / evidence | License and distribution consequence | Source and checked scope |
| --- | --- | --- |
| `hypothesis` — Original Debra editable CAD and printable designs | Consider CERN-OHL-P-2.0 instead of assuming a software license resolves physical-design questions: it expressly covers design source, making/conveying products, applicable notices and a limited patent grant. Modified source needs dated modification notices; product recipients need access to applicable notices. It does not guarantee freedom from third-party rights. | [CERN-OHL-P-2.0 text](https://raw.githubusercontent.com/spdx/license-list-data/main/text/CERN-OHL-P-2.0.txt), checked 2026-11-15; [model inventory](../../models/README.md), base `efcad08`. |
| `upstream-documented` — Alternative physical-design terms | Solderpad 2.1 wraps Apache-2.0, explicitly includes design rights and physical objects, and allows the recipient to elect Apache-2.0 instead. CERN-OHL-W and CERN-OHL-S are reciprocal rather than the proposed permissive P variant. Selection and applicability to renders, STL exports and manufactured parts need review. | [Solderpad 2.1](https://solderpad.org/licenses/SHL-2.1/); [CERN-OHL-P preamble](https://raw.githubusercontent.com/spdx/license-list-data/main/text/CERN-OHL-P-2.0.txt); checked 2026-11-15. |
| `unknown` — Third-party CAD, vendor illustrations, photographs and James's source design | Check owner and terms for each exact imported file, image, drawing and adapted design; keep component, original URL/version, author, date and rights together. An independently drawn envelope using dimensions is not proof that copied artwork or CAD may be redistributed, nor that patents/design rights are cleared. Existing models are not printed or fit-tested. | [models inventory](../../models/README.md); [enclosure brief](../design/enclosures.md); [development guidance](../development.md), base `efcad08`; [CERN-OHL-P disclaimer §5](https://raw.githubusercontent.com/spdx/license-list-data/main/text/CERN-OHL-P-2.0.txt), checked 2026-11-15. |

## 5. Firmware, kernel, and device-tree materials

| Material / evidence | License and distribution consequence | Source and checked scope |
| --- | --- | --- |
| `upstream-documented` — Raspberry Pi boot firmware at `896fc67` | Upstream identifies `start*.elf`, `fixup*.dat`, and `bootcode.bin` under `boot/LICENCE.broadcom`. It allows **unmodified binary** redistribution/use for specified Raspberry Pi or authorized derivative purposes, with copyright/disclaimer and non-endorsement conditions. This is not a general permission for every Pi, Wi-Fi, HAT or other vendor blob. | [firmware README](https://raw.githubusercontent.com/raspberrypi/firmware/896fc67d292bfde6d9889d4c585bb685758dc1ad/README.md); [LICENCE.broadcom](https://raw.githubusercontent.com/raspberrypi/firmware/896fc67d292bfde6d9889d4c585bb685758dc1ad/boot/LICENCE.broadcom); checked 2026-11-15. |
| `upstream-documented` — Raspberry Pi kernel/modules and kernel-built overlays | The same firmware repository describes kernel images, modules and kernel-sourced DTBs/overlays as GPL; its directory-specific terms and the exact selected source/header determine the version and exceptions. Preserve corresponding source and build/configuration material required for each distributed kernel artifact. | [firmware README](https://raw.githubusercontent.com/raspberrypi/firmware/896fc67d292bfde6d9889d4c585bb685758dc1ad/README.md); [Linux COPYING](https://raw.githubusercontent.com/raspberrypi/firmware/896fc67d292bfde6d9889d4c585bb685758dc1ad/boot/COPYING.linux); checked 2026-11-15. |
| `upstream-documented` — Seeed ReSpeaker 2-Mics v2 overlay | This specific `respeaker-2mic-v2_0-overlay.dts` header says MIT. The bytes fetched from Seeed commit `1d53c3c` have SHA-256 `32fad2570bc9e864d19365137a64c28614a1b7be9d816d78bf40043d73d0782c`, matching the lab record; preserve its copyright and MIT notice when redistributed. Do not generalize this to the entire repository or the v1 driver. | [overlay](https://raw.githubusercontent.com/Seeed-Studio/seeed-linux-dtoverlays/1d53c3cf2c96bd5ca2b2b7b9cbb198d398e4031c/overlays/rpi/respeaker-2mic-v2_0-overlay.dts); [lab result](../testing/results/2026-11-15-pi5-respeaker-v2-audio.md); [MIT](https://opensource.org/license/mit); checked 2026-11-15. |
| `unknown` — Other device firmware and PiCompose's vendored v1 voicecard driver | Exact blobs, hashes, versions, per-file license and permission to redistribute in each prospective image have not been inventoried. Treat unverified redistribution as a blocker for those files; installing locally or a vendor download being public does not itself establish a license. | [reuse audit](2026-11-15-upstream-reuse-audit.md); [PiCompose source](https://github.com/florian-asche/PiCompose/tree/1e5ff410163bcbb4704daea0c277fccc63a91214); checked 2026-11-15. |

## 6. Debian/Raspberry Pi OS and image or container distribution

| Material / evidence | License and distribution consequence | Source and checked scope |
| --- | --- | --- |
| `upstream-documented` — Debian package metadata | Debian policy requires package copyright/license information in `/usr/share/doc/PACKAGE/copyright`, with some standard license texts referred to in `/usr/share/common-licenses`. Raspberry Pi OS package details and any locally built components must still be checked individually; a Debian policy citation alone does not establish a particular image's contents. | [Debian policy §12.5](https://www.debian.org/doc/debian-policy/ch-docs.html#copyright-information), checked 2026-11-15. |
| `hypothesis` — A downloadable prepared image or distributed container | Create a machine-readable inventory per actual artifact: package and source name, exact version/architecture, hashes, origin, license expression or `unknown`, copyright, notice location, modifications, source route and firmware/model file hashes. Include package notices and their referenced license texts in the image or accompanying materials as required. Do not distribute an unreviewed artifact whose included material cannot be cleared. | [Debian copyright format](https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/); [LVA Dockerfile](https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/12e51272d37d786ed3168955b3fb6eda3c7159ce/Dockerfile); checked 2026-11-15. |
| `upstream-documented` — GPL source distribution | For each covered binary, including an unmodified one, provide the exact corresponding source, changes and applicable scripts through a method permitted by its version: e.g. for GPL-3 network downloads, equivalent access and clear directions alongside the binary; GPL-2 and physical distribution have their own allowed options and written-offer conditions. A generic upstream homepage or a list of package names is not proof that exact source remains available. Retain notices and license texts as well. | [GPL-3 §§1, 4–6](https://www.gnu.org/licenses/gpl-3.0.html); [GPL-2 §3](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html); checked 2026-11-15. |
| `upstream-documented` — Modified software on a physical consumer device | GPL-3 §6 may additionally require installation information when object code is conveyed with/for a User Product in a qualifying transfer, subject to its stated exceptions. Plan for recipients to install modified covered software where the clause applies; this is not a blanket instruction to publish private keys. | [GPL-3 §6](https://www.gnu.org/licenses/gpl-3.0.html), checked 2026-11-15. |
| `unknown` — Actual image compliance | Base image, package versions, source mirror/offer, wheel and container digests, firmware, weights, notice preservation and release channel are not finalized or audited. No distributed image, source bundle, or physical-device compliance is verified by this note. | [F04/I02/I04](../roadmap.md); [lab build](../../tools/device/lab-pi5/README.md); [Debian policy](https://www.debian.org/doc/debian-policy/ch-docs.html#copyright-information); checked 2026-11-15. |

### Proposed release gate, not an implemented workflow

1. Freeze the precise image/container and build inputs; enumerate installed
   Debian/Raspberry Pi OS packages, wheels and their native contents, copied
   files, models, firmware, artwork and licenses. Keep the source revision,
   package version, architecture, digest, and license evidence beside each.
2. Resolve unknown/conflicting rights or omit the affected bytes. Retain
   license texts, required attribution and changes; check notices inside the
   actual artifact, not just the source tree or an OCI label.
3. For each copyleft artifact, assemble exact corresponding source and build
   scripts and choose a distribution channel permitted by its license and
   physical/network delivery method. Preserve availability for the required
   period; verify a recipient can retrieve it. Check LGPL replacement/relinking
   and GPL-3 installation-information requirements where applicable.
4. Review source availability, notice bundle, firmware conditions, trademarks
   and any commercial-use restrictions for the actual release. Re-audit after
   component changes. Have a knowledgeable reviewer or lawyer assess uncertain
   combinations; this note is not legal advice or permission to publish.

## Decisions James must make

1. Approve MIT for Debra-authored code and docs, choose Apache-2.0 instead, or
   defer; decide the holder name only after establishing actual rights.
2. Choose separate terms for original CAD/printed parts, including whether the
   permissive CERN-OHL-P-2.0 candidate or Solderpad fits the intended physical
   and commercial reuse. Decide scope for renders, documentation and exports.
3. Decide contribution policy (DCO, CLA or neither), attribution and handling
   of human/AI-assisted or externally derived content.
4. Decide whether commercial redistribution is an explicit goal and whether
   noncommercial model weights should be excluded, separately offered where
   allowed, or replaced. A commercial-use goal does not itself grant rights.
5. Decide who owns release compliance, source hosting/retention and the
   process for maintainer clarifications and legal review. Any image release,
   public contribution or new remote remains separately authorized.

## Traps

- MIT on Debra's repository does not relicense copyleft programs, model
  weights, vendor blobs, photos or CAD, and is not an image-wide license.
- Even a perfectly unmodified GPL binary has distribution obligations. An
  independent program in an aggregate is not automatically GPL merely because
  it shares an image; linking, modification and other combinations need review.
- An Apache code license does not establish the terms of its pretrained weights;
  matching names are weaker than matching exact bytes and source provenance.
- PiCompose's contradictory statements cannot be resolved by picking the more
  convenient one. Its vendor copies need separate treatment too.
- `/usr/share/doc` deletion can remove useful license evidence. Retaining notices
  elsewhere may help, but a notice list is not corresponding source or proof of
  compliance, and a manifest does not confer redistribution permission.
- Git submodule pointers, package metadata, web links, a successful build or a
  local lab install do not prove that source, license notices and rights travel
  with a released image. Model names and logos may involve trademark rights.

## Not verified / open questions

- PiCompose's intended license and its vendored `seeed-voicecard-v2` file-level
  licenses remain unresolved. The Seeed v2 overlay above is a different file
  and its MIT header does not resolve the v1 tree or whole Seeed project.
- LVA's `hey_luna`, `hey_morgan`, `okay_nabu`, `stop` and five
  `openWakeWord/` model pairs lack matched provenance/terms here; also check
  feature-extraction/backbone models and all transitive wheel assets. The six
  matching ESPHome pairs are a scoped comparison, not an actual image audit.
- Firmware other than the named Broadcom files, any selected OS package and
  any selected Python wheel not audited above remain unknown. rpi-preseed's
  `main` is mutable and its exact 0.2.1 release revision is not pinned here.
- Debra's rights holders, prior copied material, James's source CAD permissions,
  model training data rights, commercial-use policy, license selection and
  contribution terms need review; do not invent holders or blanket clearance.
- Exact source archives, reproducible build scripts, source access duration,
  license/notice location, applicable GPL version, LGPL relinkability, and
  GPL-3 installation information depend on a real selected and built artifact.
  Neither a Raspberry Pi OS image nor an LVA container was inspected.

## Verification

- Read the F04 brief, evidence rules, development guidance, template, upstream
  reuse audit, model inventory and lab material at the requested base. Public
  HTTPS fetches of pinned upstream texts, GitHub tree metadata and license
  documents were performed on 2026-11-15; mutable sources are identified.
- Compared Git tree blob IDs for LVA root wake-word JSON/TFLite files against
  the ESPHome collection tree; six pairs match and four do not. Re-fetched the
  Seeed overlay and computed SHA-256 in memory: it matches the lab record.
- Partial: GitHub API eventually returned a rate-limit 403, and no rpi-preseed
  `v0.2.1` tag was found; mutable `main` was read instead. A guessed Seeed
  repository `LICENSE` and some guessed source paths returned 404, which does
  **not** establish that a repository has no license.
- A local read-only Python structure check passed for six material sections,
  required frontmatter/headings, 30 labeled and dated source-linked rows, local
  Markdown link targets and trailing whitespace. An initial check found one
  row without a web URL; its reference was added before the passing check.
- Not run: image/container pull, package installation or build, device or
  private network-service contact, legal review, release, commit or push.

## Handoff and correction links

- Requested evidence base: `efcad08f5af4cd9af73b919933ef85bb043068b6`;
  checkout HEAD was `4b5085d4274398db23fa7c1872417de041972f55` at writing.
  Unrelated comparison-file edits were already present; additional unrelated
  edits appeared during the work. None were touched by this task.
- Reviewer: resolve James's choices and remaining per-artifact rights, then
  promote only reviewed conclusions through the coordinator. Recheck revisions
  and actual build contents before any release.
- This note narrows the earlier [reuse audit](2026-11-15-upstream-reuse-audit.md)
  model-licensing unknown for six exact matched pairs; it does not supersede or
  edit that record. Its suggestion to choose MIT attribution or rewrite around
  the PiCompose conflict is **not** a license clearance; obtain clarification
  before copying or adapting protected material.
- No reviewed decision, license file, source bundle or release has been made.
