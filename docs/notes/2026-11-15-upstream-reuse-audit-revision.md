---
title: Upstream reuse audit, revision 2
date: 2026-11-15
type: project-learning
status: unreviewed
task: R04
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - "docs/notes/2026-11-15-upstream-reuse-audit.md — original R04 note under correction, read 2026-11-15"
  - "docs/notes/2026-11-15-research-notes-review.md — 'R04 findings' R04-1..R04-7, read 2026-11-15"
  - "docs/notes/2026-11-15-license-and-provenance-proposal.md (F04) — licence conclusions already checked, read 2026-11-15"
  - "docs/evidence.md, docs/development.md, docs/work/cards/R04.md — reporting rules, reuse mechanism, packet scope, read 2026-11-15"
  - "docs/research/2026-11-15-armv6-wheels.md (Z02) — ARMv6 wheel/ELF findings, read 2026-11-15"
  - "docs/research/2026-11-14-preliminary-findings.md — reuse/licensing and tryboot sections, read 2026-11-15"
  - "https://raw.githubusercontent.com/raspberrypi/rpi-image-gen/fb44a4cde4ac/getting_started.adoc — checked 2026-11-15"
  - "https://raw.githubusercontent.com/raspberrypi/rpi-image-gen/fb44a4cde4ac/layer/rpi/device/family-base.yaml — checked 2026-11-15"
  - "https://raw.githubusercontent.com/raspberrypi/rpi-image-gen/fb44a4cde4ac/layer/rpi/device/ab-slots.adoc — checked 2026-11-15"
  - "https://raw.githubusercontent.com/raspberrypi/rpi-image-gen/fb44a4cde4ac/layer/raspbian/trixie/base-apt.yaml — checked 2026-11-15"
  - "https://api.github.com/repos/raspberrypi/rpi-image-gen/git/trees/fb44a4cde4ac?recursive=1 — tree read, checked 2026-11-15"
  - "https://raw.githubusercontent.com/florian-asche/PiCompose/1e5ff410163bcbb4704daea0c277fccc63a91214/.github/workflows/build-image-template.yml — checked 2026-11-15"
  - "https://raw.githubusercontent.com/florian-asche/PiCompose/1e5ff410163bcbb4704daea0c277fccc63a91214/README.md — checked 2026-11-15"
  - "https://raw.githubusercontent.com/florian-asche/PiCompose/1e5ff410163bcbb4704daea0c277fccc63a91214/LICENSE — checked 2026-11-15"
  - "https://raw.githubusercontent.com/florian-asche/PiCompose/1e5ff410163bcbb4704daea0c277fccc63a91214/02-stage-audiodriver-2michat-v2/02-set-audio-volume/files/configure_audio.sh — checked 2026-11-15"
  - "https://raw.githubusercontent.com/florian-asche/PiCompose/1e5ff410163bcbb4704daea0c277fccc63a91214/02-stage-audiodriver-2michat-v1/01-driver/03-run-chroot.sh and .../2michat-v2/01-driver/03-run-chroot.sh — checked 2026-11-15"
  - "https://api.github.com/repos/florian-asche/PiCompose/git/trees/1e5ff410163bcbb4704daea0c277fccc63a91214?recursive=1 — tree read, checked 2026-11-15"
  - "https://raw.githubusercontent.com/RPi-Distro/pi-gen/6e3ff62bfd9c690a6a3d1d7de259d5e0af40cb78/README.md — checked 2026-11-15"
  - "https://api.github.com/repos/RPi-Distro/pi-gen/tags and /branches — checked 2026-11-15"
  - "https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/12e51272d37d786ed3168955b3fb6eda3c7159ce/.github/workflows/docker-build-release.yml — checked 2026-11-15"
  - "https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/12e51272d37d786ed3168955b3fb6eda3c7159ce/docker-compose.yml, README.md, docs/install_application.md — checked 2026-11-15"
  - "https://ghcr.io/v2/ohf-voice/linux-voice-assistant/manifests/{v1.1.18,1.1.18} — anonymous token, metadata only, checked 2026-11-15"
  - "https://raw.githubusercontent.com/raspberrypi/documentation/master/documentation/asciidoc/computers/raspberry-pi/bootflow-eeprom.adoc and .../computers/config_txt/autoboot.adoc — mutable main, checked 2026-11-15"
supersedes:
  - "docs/notes/2026-11-15-upstream-reuse-audit.md — its conclusions and verdicts only; the original file, its observations and its source register are preserved unchanged"
---

# Revise the audit to the strength of its sources

## Summary

The review's theme is right: the original note repeatedly converts *"the source
says X is intended"* into *"X happens"*. This revision keeps the audit's
pinned-source work and rewrites the conclusions at the strength the retrieved
text supports. **Nothing was built, flashed, pulled, installed or booted for this
revision either** — the difference is that the note now says so per claim instead
of once in a disclaimer.

Revised recommendation per candidate:

| Candidate | Original verdict | Revised verdict | What moved |
| --- | --- | --- | --- |
| **LVA** | Partial reuse — adopt as the voice component | **Partial reuse — adopt as a pinned component** (unchanged in kind) | Pin corrected to the tag/digest that actually exists; "minimum privilege" demoted to "the privilege set upstream declares"; the Zero W source-build route demoted to a hypothesis with a test |
| **PiCompose** | Partial reuse of two files, plus reference reuse | **Reference only — read, then re-derive.** File-level copy is **blocked**, not merely "review-gated" | F04's licence position governs: the conflict is unresolved, so no copying or adapting of its protected files. The two audio files stay as *named references to verify on our own hardware* |
| **pi-gen** | Adopt as the image-build foundation | **Adopt as the builder** — the best-evidenced route to a 32-bit Raspberry Pi OS derivative, with no reproducibility claim attached | "Reproducible-ish" removed; `STAGE_LIST` demoted from "never fork" to "add stages without forking"; "no onboarding" qualified with the documented cloud-init preseed |
| **rpi-image-gen** | "Cannot build for a Pi Zero W", reference-only | **Unknown / unproven — a candidate with a named deciding test** (reference-only for its A/B *design*) | The upstream guide says the target can be any Pi; the real gap is the missing Zero W device class and ARMv6 kernel layer, which is a work item, not a proof of impossibility |
| **Pi Zero W full support** | Treated as achievable but blocked by wheels | **Requirement retained; four separate unverified questions**, none of them decided by this audit | OS boot was asserted as fact and is now separated from wheel import, wake-engine repair and performance |
| **rpi-image-gen A/B + SBOM design** | Reference only | **Reference only** (unchanged) | Kept, but `tryboot`'s "all models" support is separated from whether slot *management* works on a Zero W |

## Labels used here

Per [evidence.md](../evidence.md), plus one declared local label so that a fetch
is not mistaken for a test:

| Label | Meaning in this note |
| --- | --- |
| `upstream-documented` | A linked primary source states it; Debra has not reproduced it |
| `retrieved` | A named public URL or registry endpoint answered on 2026-11-15 and returned the quoted text, status or digest. **Not a run, not a pull, not a build** |
| `reported` | A third party's statement, including an upstream README's claim about its own product's behaviour |
| `hypothesis` | Inference from source, packaging or configuration, not executed |
| `unknown` | Not established. An absent file is not proof that a capability is absent |
| `not-run` | Explicitly attempted nothing |

## Corrected audit

### Candidate 1 — linux-voice-assistant

| Property | Corrected value | Label |
| --- | --- | --- |
| Licence | Apache-2.0 for the code; bundled models and sounds are separate questions (F04 §3) | upstream-documented |
| Published container platforms | `platforms: linux/amd64,linux/aarch64` in the release workflow | upstream-documented |
| Container tags produced | semver tags `1.1.18`, `1.1`, `1`, `latest` from a `v1.1.18` Git tag — **no `v`-prefixed image tag** | upstream-documented (workflow `docker/metadata-action` `type=semver`) + retrieved |
| `v1.1.18` image tag | **HTTP 404** at the public registry | retrieved |
| `1.1.18` image tag | HTTP 200, OCI index digest `sha256:089f321a4e7408c61fbcd1ec691eb073961be022d651139f32b0dbead9b2af58`, entries for `amd64`, `arm64` and two attestation manifests | retrieved — metadata only; nothing pulled or run |
| Stated minimums | 1 GHz CPU, 512 MB RAM, ~4 GB OS+software, 16 kHz mono mic, **OS `linux/amd64` or `linux/aarch64`** | upstream-documented (README "Requirements") |
| Compose defaults | `LVA_IMAGE_TAG:-latest`, `LVA_USER_ID:-1000`, `network_mode: host`, `group_add: [audio]`, `cap_add: [SYS_NICE]` | upstream-documented |
| Actions pinned by commit | Yes — e.g. `docker/login-action@8aa5831…# v4.8.0` | upstream-documented |

The original's verdicts survive, with two corrections:

- **The pin form was wrong.** `ghcr.io/ohf-voice/linux-voice-assistant:v1.1.18@sha256:…`
  names a tag that does not exist, so the line could not be used as written. The
  usable forms are `ghcr.io/ohf-voice/linux-voice-assistant@sha256:089f321a…`
  (digest only) or `:1.1.18@sha256:089f321a…`. The digest pins the multi-arch
  index; a per-architecture pin would need the child manifest digest for the
  target platform. **Neither was pulled, so neither is a tested artifact.**
- **"Minimum privilege" was an assertion about a compose file.** The upstream
  compose *declares* host networking, the `audio` group and `SYS_NICE`. That is
  an example of a working configuration on the lab Pi 5, not a demonstration
  that nothing less suffices. Treat it as a starting point for a reduction test,
  not a minimum.

Unchanged and still supported: partial reuse (option b) is the recommendation;
whole adoption (a) and reimplementation (c) remain rejected; `wyoming-satellite`
remains rejected on maintenance grounds. The Zero W route is *not* settled — see
the corrected traps.

### Candidate 2 — PiCompose

| Property | Corrected value | Label |
| --- | --- | --- |
| Licence | `LICENSE` is MIT ("Copyright (c) 2025 Florian Asche"); README §License says "released under the BSD-3-Clause License" and links to that same file | upstream-documented (both files re-read) |
| Build inputs | `username: pi`, `password: raspberry`, `enable-ssh: 1`, `pubkey-only-ssh: 0`, `disable-first-boot-user-rename: 0`, `pi-gen-version: arm64`, `usimd/pi-gen-action@v1`, `runs-on: ubuntu-24.04-arm`, `release: trixie` | upstream-documented |
| What those inputs produce at first boot | **Contested between two upstream documents.** pi-gen: unless the rename is disabled, the first user "will be renamed on the first boot with a name chosen by the final user", described as a security feature against shipping a default username. PiCompose's README tells the user to "login with the user `pi`" after the automatic driver reboot and to change the password "if you didnt change it before with the imager tool" | `reported` (both are documentation; neither is an observation) |
| Driver provenance | The v1 stage **downloads at build time** from `github.com/HinTak/seeed-voicecard` branch `v$kernel_version` (a third-party fork) and the v2 stage `git clone --depth 1` of `Seeed-Studio/seeed-linux-dtoverlays`. There is no vendored driver tree at this commit; `files/seeed-voicecard-v2` is a single 4.4 KB install script carrying an MIT header | upstream-documented (tree + scripts) |
| Sendspin | Absent; the tree contains `03-stage-linux-voice-assistant/02-snapcast`, and the README says Snapcast is disabled by default | upstream-documented |

Corrected verdicts:

- **Option b (copy two files) is withdrawn as "supported".** It was already
  conditional on licence review; F04 has since concluded that the conflict
  "cannot be resolved by picking the more convenient one" and that its protected
  files should not be copied or adapted without maintainer clarification or
  separate permission. A recommendation cannot sit in front of an unresolved
  blocker. What remains is option c.
- **Option c (reference reuse) is the recommendation, restated precisely:** the
  TLV320AIC3104 mixer recipe and the per-boot oneshot pattern are *read as
  evidence about the hardware*. The settings themselves (control names, values,
  "WirePlumber resets ALSA state per session") are hardware facts Debra can
  re-derive and verify on its own ReSpeaker; a copied script is not needed to
  benefit from them and is not licensed to be copied today.
- **Option a stays rejected**, and the driver finding strengthens it: the build
  fetches unpinned third-party source at build time, so even a pinned PiCompose
  commit does not describe the image it produces.

### Candidate 3 — pi-gen

| Property | Corrected value | Label |
| --- | --- | --- |
| Branch model | 32-bit from `master`, 64-bit from `arm64` | upstream-documented |
| Branch heads on 2026-11-15 | `master` `6e3ff62bfd9c`, `arm64` `c0d2c9f2cffc` | retrieved (branches API) |
| Published image tags | e.g. `2026-10-06-raspios-trixie-armhf`, `-trixie-arm64`, `-bookworm-armhf` | retrieved (tags API) |
| Releases | **Not rechecked** — the GitHub API hit its anonymous rate limit during this revision | unknown |
| Onboarding | `ENABLE_CLOUD_INIT` defaults to `1`: cloud-init and netplan installed and configured, reading config from bootfs or `stage2/04-cloud-init/files` on first boot. Not an interactive portal and not a recovery service | upstream-documented |
| External stages | `STAGE_LIST` accepts absolute or relative paths outside the tree; `EXPORT_CONFIG_DIR` likewise. The README states no stability promise for `build.sh` or for the base stages | upstream-documented |
| First user | `FIRST_USER_NAME` default `pi`; renamed at first boot unless `DISABLE_FIRST_BOOT_USER_RENAME=1`; if the name is `pi` and no `FIRST_USER_PASS` is set, a setup wizard runs on first boot | upstream-documented |
| Docker build | "partially isolates" the build; needs privileged access for loop devices and binfmt | upstream-documented |

Corrected verdicts:

- **Option a remains the recommendation, with the claim reduced.** pi-gen is the
  tool Raspberry Pi uses to build Raspberry Pi OS, it publishes armhf Trixie
  image tags, and it documents external stages. That is a well-evidenced route
  to a 32-bit Raspberry Pi OS derivative. It is **not** shown to be reproducible,
  and it is no longer described as the *only* candidate that can produce 32-bit
  Trixie — see rpi-image-gen below.
- **"No onboarding" is qualified** (finding R04-6): there is no interactive
  portal, but pi-gen documents bootfs cloud-init provisioning and enables it by
  default. Debra's Wi-Fi/identity flow still has to be designed; the existence of
  a preseed mechanism is not that design, and N01's credential-lifecycle
  questions apply to it.
- **`STAGE_LIST` no longer promises "never forks".** It lets Debra add stages
  without forking, which is real and useful. A change needed *inside* a base
  stage or `build.sh` would still be a patch or a copy; nothing in the README
  says otherwise.

### Candidate 4 — rpi-image-gen

| Property | Corrected value | Label |
| --- | --- | --- |
| Target support | "The build target can be any Raspberry Pi, but all features are available only on RPi4 or later … When building for older targets, some layers will not work" | upstream-documented (getting_started.adoc) |
| Ready-made device classes | `X-Env-Var-class-Valid: zero2w,pi3,pi4,cm4,pi5,cm5`; `config/device/` has no `zero`/`zerow` | upstream-documented |
| ARMv6 kernel layer | None. `layer/rpi/device/armhf/` contains `linux-image-v7` and `linux-image-v7l` only | upstream-documented (tree) |
| 32-bit distribution layer | **Exists**: `layer/raspbian/trixie/base-apt.yaml` declares `X-Env-Layer-Name: raspbian-trixie-armhf`, `architectures: [armhf]`, `suite: trixie` | upstream-documented |
| A/B slot layer | `layer/rpi/device/ab-slots.adoc` + `slot-mapper/` (`rpi-slot-tryboot`, `rpi-slot-label`, `rpi-slot-static`, udev rule, initramfs hooks). "Devices booting from SD, eMMC and NVMe are supported"; the doc says nothing about ARMv6 or model classes | upstream-documented |
| `tryboot` itself | "All Raspberry Pi models support `tryboot`" (mutable `main` of the Pi documentation) | upstream-documented |
| Reproducibility | Reproducible-build and SBOM hooks are *documented by the project*; no build was inspected or reproduced | upstream-documented / not-run |

Corrected verdicts:

- **"Cannot build/express a Zero W target" is withdrawn.** What the sources
  support: at `fb44a4c` there is no Zero W device class and no ARMv6 kernel
  layer, and the Raspbian armhf Trixie base is available. Building an ARMv6 image
  would therefore require a custom device layer and a v6 kernel layer — **work,
  not impossibility**. Upstream explicitly contemplates older targets with some
  layers unavailable.
- **Option a moves from "rejected for now" to "not selected now; unproven".** The
  deciding evidence is a build attempt (T2 below), not a document.
- **Option c (A/B and manifest as design reference) stands**, and the
  reproducibility/SBOM claims stay labelled as upstream statements about the
  tool, not as properties Debra has obtained.
- **"The better long-term builder for 64-bit targets"** is reduced to "a credible
  candidate for 64-bit targets, unbuilt here".

### Corrected traps

1. **A branch name is not a pin** — unchanged and now stronger: PiCompose's build
   resolves `pi-gen-version: arm64` through `usimd/pi-gen-action@v1` *and* fetches
   `HinTak/seeed-voicecard` branch tarballs and `Seeed-Studio/seeed-linux-dtoverlays`
   HEAD at build time. Three mutable inputs, none recorded in the output.
2. **`linux/armv6l` and `armhf` are not ARMv6 promises** — unchanged (Z02).
3. **LVA has no 32-bit container artifact** (`platforms: linux/amd64,linux/aarch64`).
   *Corrected consequence:* running LVA on a Zero W would require a source
   install, and the wake engines need a self-built TFLite library. That is a
   `hypothesis` chain with three unproven links, not a plan. It does not
   establish that a Zero W appliance is impossible, and it does not license
   dropping the requirement.
4. **`:latest` is the default in LVA's compose** (`LVA_IMAGE_TAG:-latest`) —
   unchanged. Adopting either compose file unchanged violates the pinned-component
   rule on day one.
5. **PiCompose's default-credential posture** — corrected. The build inputs are
   as stated, but *whether the `pi`/`raspberry` account survives first boot is
   contested between two upstream documents* and unobserved. PiCompose's own
   README tells users to log in as `pi` with password `raspberry`, which is
   itself a security statement about the shipped image: Debra must assume the
   credential is live and reachable over SSH rather than assume pi-gen's rename
   protects it. Renaming the user is not documented as changing the password, so
   password survival is `unknown` in both readings. The correct action is an
   image inspection (T4), not a conclusion.
6. **PiCompose's licence is internally contradictory** (MIT file, BSD-3-Clause
   README). Unchanged, and now a **blocker** for file-level reuse rather than a
   "attribute or rewrite" choice — F04's position governs.
7. **UID 1000 is hardcoded** in LVA's compose defaults (`LVA_USER_ID:-1000`,
   `XDG_RUNTIME_DIR=/run/user/1000`) — unchanged, still a real coupling for a
   non-1000 user model.
8. **rpi-image-gen is not a drop-in pi-gen replacement for 32-bit work today** —
   restated as: no Zero W class, no ARMv6 kernel layer, features documented as
   RPi4+ only. Not "cannot".
9. **rpi-image-gen's layer API is moving** — unchanged (README "under active
   development"; release notes about custom layers needing updates).
10. **`tryboot` is documented for all models, but slot *management* is not.**
    `ab-slots.adoc` supports SD/eMMC/NVMe boot devices and is silent on ARMv6;
    the `autoboot.txt` partition-switch flow documented upstream reads
    `/proc/device-tree/chosen/bootloader/*`, a node whose population on a
    firmware-booted Zero W is unverified here. Two questions, one of them still
    open.
11. **Comitup is GPL-2.0-or-later** (F04 §2). Unchanged.
12. **`wifi-connect`'s install path is Stretch-era** and it needs NetworkManager
    to be the active manager. Unchanged.

## Finding-by-finding changes

| Finding | Severity | What changed | Where |
| --- | --- | --- | --- |
| **R04-1** "an armhf image boots on a Zero W" | High | Withdrawn as fact. Nothing was built, flashed or booted. What is `retrieved` is that pi-gen publishes `2026-10-06-raspios-trixie-armhf`; what is `unknown` is whether that image boots on an original Zero W (raspberrypi.com returned 403 in both Z02 and this session). Four questions are now separate: OS boot, per-wheel architecture/import, wake-engine repair, full voice+music performance. Full Zero W support is retained as a requirement, not downgraded. | Summary; Candidate 3 table; Trap 3; "What would settle" T1 |
| **R04-2** "cannot build/express a Zero W target" | High | Withdrawn. Upstream says the target can be any Pi with some layers unavailable on older targets. The evidenced gap is narrower: no `zero`/`zerow` device class (`class-Valid: zero2w,pi3,pi4,cm4,pi5,cm5`) and no ARMv6 kernel layer (`linux-image-v7`/`-v7l` only). A custom layer route is **unproven and probably requires work**, not impossible. Added: an armhf Trixie distribution layer exists (`raspbian-trixie-armhf`), so "pi-gen is the only 32-bit Trixie builder" is also too strong. Verdict changed to "not selected now; unproven". | Candidate 4 table and verdicts; Trap 8; T2 |
| **R04-3** `c0d2c9f2cffc` as "the resolved arm64 pin" | High | Demoted to a **dated observation of a branch head** (re-read 2026-11-15: `arm64` → `c0d2c9f2cffc`, `master` → `6e3ff62bfd9c`). It is not the pi-gen revision used by any published PiCompose image; that cannot be recovered from the workflow, because `usimd/pi-gen-action@v1` + `pi-gen-version: arm64` resolve at build time. Reuse target 12 rewritten: pin deliberately after a build test, do not treat today's head as a selection. Provenance is now a named recovery task, not a "resolved" line. | Candidate 2 (driver provenance), Candidate 3 table, Trap 1, T3 |
| **R04-4** "insecure default account" asserted as shipped state | Medium | Split into three claims. Build inputs: `upstream-documented`. Survival of `pi`/`raspberry` at first boot: **contested** — pi-gen documents a rename at first boot, PiCompose's README documents logging in as `pi`. Observed login: **not-run**. The risk is now stated as a risk Debra must assume is live (SSH with password auth is enabled at build time) rather than as an observed state, and password replacement after a rename is `unknown`. | Candidate 2 table, Trap 5, T4 |
| **R04-5** broken relative links to the two research notes | Medium | Corrected here: links point to `../research/2026-11-15-lva-requirements.md` and `../research/2026-11-15-armv6-wheels.md`. The original note is unchanged, so its links remain broken; this note is the corrected target. A link check for `docs/notes/` is proposed, not implemented. | This note's links; T5 |
| **R04-6** "pi-gen gives no onboarding"; `STAGE_LIST` means never fork | Medium | Qualified. pi-gen documents `ENABLE_CLOUD_INIT=1` by default with bootfs/stage2 cloud-init config read on first boot — provisioning, not a portal or a recovery service, and not Debra's Wi-Fi/identity design. `STAGE_LIST`/`EXPORT_CONFIG_DIR` externalise stages and export scripts; nothing promises stability for `build.sh` or the base stages, so a patch may still be needed. Reuse target 10 reworded. | Candidate 3 table and verdicts |
| **R04-7** unusable `v1.1.18` pin; "minimum privilege"; licence "attribution or rewrite" | Medium | Pin corrected: `v1.1.18` returned **404**; `1.1.18` returned 200 with index digest `sha256:089f321a…` and `amd64`/`arm64` entries (metadata only, not pulled). The workflow's semver tags explain the missing `v`. "Minimum privilege" demoted to "the privilege set upstream declares", with a reduction test named. Licence route corrected per F04: no copying or adapting PiCompose's protected files on the current evidence; attribution or rewriting is not a clearance. | Summary; Candidate 1 table; Candidate 2 verdicts; Trap 6; T7 |

Two corrections this revision adds beyond the seven findings, both from re-reading
the pinned trees:

- **PiCompose does not vendor a driver tree.** The v1 stage downloads
  `HinTak/seeed-voicecard` branch tarballs and the v2 stage clones
  `Seeed-Studio/seeed-linux-dtoverlays` at HEAD during the build. The original's
  open question and F04's wording ("vendored `seeed-voicecard-v2` tree") describe
  a single 4.4 KB MIT-headed install script. The licence caution stands; the
  description does not. F04 is not edited.
- **"Only 32-bit Trixie builder" was too strong.** `layer/raspbian/trixie/base-apt.yaml`
  in rpi-image-gen declares an armhf Trixie base. An end-to-end armhf build there
  remains unproven for the reasons in R04-2, but it is not excluded.

## What would settle each open question

Each test is bounded, names its decision rule, and needs its own authorization.
None is granted by this note.

| ID | Question | Test | Decision rule |
| --- | --- | --- | --- |
| **T1** | Does a 32-bit Trixie Raspberry Pi OS image boot on an original Zero W? | Spare Zero W + spare card; flash the official 32-bit Trixie image (or a pi-gen armhf build); record boot to console, `uname -m`, `dpkg --print-architecture`, then run Z02's four clean-venv imports (`numpy==2.5.4`, `numpy==2.2.1`, `av==16.1.0`, `webrtc-noise-gain==1.3.0`) | Boot plus successful imports makes the OS/packaging half `tested`; a `SIGILL` or wrong-ELF failure closes the affected wheel route and nothing else |
| **T2** | Can rpi-image-gen produce an ARMv6 Trixie image at all? | On an arm64 host: add a device layer with an ARMv6 class and a v6 kernel layer, use the `raspbian-trixie-armhf` base, build, inspect the image, then boot it on T1's card | A bootable armhf image makes rpi-image-gen a live candidate and weakens pi-gen's position; a kernel/layer failure keeps pi-gen as the only evidenced route |
| **T3** | Which pi-gen revision produced a given PiCompose image? | Read the GitHub Actions run log for the run that published a named asset; or rebuild with both inputs pinned and compare the recorded SHA-256 in the release | Provenance recovered only if the log names a commit, or two rebuilds from the same two pins match |
| **T4** | Does the `pi`/`raspberry` account exist and answer SSH after first boot? | Flash a PiCompose image, boot headless with no Imager customisation, then with customisation; record whether the rename wizard appears and whether `ssh pi@…` succeeds before setup completes | A successful password login before setup completes = credential survives; the wizard appearing and completing = it does not. Either result must be recorded per flash method |
| **T5** | Are `docs/notes/` links and citations checked? | Extend the offline `tests/test_docs.py` relative-link check to `docs/notes/` (a repository change, separately scoped) | The check fails on the original note's two links and passes on this one |
| **T6** | Does cloud-init bootfs provisioning actually join Wi-Fi on a Debra image? | Belongs to N01: a disposable image, a saved non-household SSID, and a recorded state machine | Out of scope here; the point is only that pi-gen's mechanism is not Debra's design |
| **T7** | What privilege does LVA actually need? | Pull the pinned digest, inspect labels and contents, then run the compose as declared and again with `SYS_NICE` removed and with host networking replaced by explicit socket mounts | Whatever still works is the candidate minimum; anything that breaks identifies a real requirement |
| **T8** | Does rpi-image-gen's `ab-slots`/`tryboot` slot management work on a Zero W? | Build a two-slot armhf image with the `ab-slots` layer, boot it, check `/dev/disk/by-slot/{active,other}/{boot,system}`, run `reboot '0 tryboot'`, then read `/proc/device-tree/chosen/bootloader/tryboot` | Slots present plus a successful tryboot round trip = usable; a missing device-tree node or a firmware that ignores `autoboot.txt` = the design needs a different mechanism on this target |

## Still unknown

- **Nothing was built, flashed, pulled, installed or booted** in this revision,
  and nothing was in the original. Every "would inherit" statement remains a
  reading of source.
- **Whether an armhf image boots on a Zero W** (T1). The general claim is
  plausible and widely repeated; no primary source could be fetched on
  2026-11-15 (`raspberrypi.com` returned 403, the same block recorded in
  `docs/evidence.md`).
- **Whether a custom rpi-image-gen ARMv6 layer can build and boot** (T2).
- **Whether `ab-slots`/`tryboot` slot management works on a Zero W** (T8).
  `tryboot` itself is documented for all models; the partition-switch flow and
  its device-tree signals on a firmware-booted Zero W are not.
- **PiCompose build provenance** for any published image (T3), and **first-boot
  account behaviour** (T4). The two upstream documents disagree; neither is an
  observation.
- **LVA's actual minimum privilege set** (T7) and **whether the `1.1.18` digest
  pulls and runs on aarch64** — the manifest was read, not fetched.
- **LVA wake-word model licences**: F04 closed six exact matched pairs against
  the ESPHome collection and left `hey_luna`, `hey_morgan`, `okay_nabu`, `stop`
  and five `openWakeWord/` pairs unmatched. Not resolved here.
- **Whether a self-built TFLite C library for ARMv6 builds and runs** — the Z02
  unknown, unchanged, and it is the hinge on which the Zero W voice path turns.
- **PiCompose's vendored-file licences**: the `seeed-voicecard-v2` install script
  carries an MIT header; the driver source it downloads at build time carries
  whatever licence the branch head had on that day. Unaudited.
- **Whether Raspberry Pi intends pi-gen to remain the 32-bit custom-image path.**
  The READMEs describe a division of labour, not a deprecation.
- **pi-gen's release objects** were not rechecked this session (GitHub API rate
  limit reached), so the original's "no GitHub Releases" line is neither
  confirmed nor refuted here.
- **LVA's minimum Home Assistant version** remains unknown (VOICE01).

## Verification

- Procedure: read the two notes under correction, the review's R04 section, the
  F04 licence note, `docs/evidence.md`, `docs/development.md`, the R04 card, Z02
  and the preliminary findings; then re-fetched every pinned source cited by a
  corrected finding and re-read the PiCompose and rpi-image-gen trees at their
  pinned commits. Read-only retrieval only; working directory `/tmp/opencode`.
- `retrieved`: pi-gen `master`/`arm64` branch heads and published tags;
  PiCompose workflow inputs and stage tree; `HinTak/seeed-voicecard` and
  `seeed-linux-dtoverlays` as the actual driver sources; rpi-image-gen
  `getting_started.adoc`, `family-base.yaml`, `ab-slots.adoc`,
  `raspbian/trixie/base-apt.yaml` and the armhf kernel-layer listing; LVA
  workflow platforms, compose defaults, README requirements and
  `docs/install_application.md` env table; anonymous registry metadata for
  `1.1.18` (200, digest `sha256:089f321a…`) and `v1.1.18` (404).
- **Not run:** no build, no image or container pull, no device contact, no
  installation, no clone, no fork, no commit or push. `raspberrypi.com`
  returned 403; the GitHub REST API hit its anonymous rate limit partway
  through, which is why the pi-gen release question is marked unknown.
- Documentation check: `python3 -B -m unittest tests.test_docs -v` — see the
  handoff below for the exact result; that suite covers `docs/comparisons`,
  `models/` and the front-door guides, **not** `docs/notes/`, so it does not
  validate this note's own links (T5).

## Handoff and correction links

- Current state: research revision, branch `main` at `b23ed98`, with an
  unrelated untracked `models/parts/rpispeaker-v17-lid/` present in the tree and
  left untouched. This note is unreviewed and is the only file created.
- What this note supersedes: the **conclusions and verdicts** of
  [the original audit](2026-11-15-upstream-reuse-audit.md). The original file,
  its observations, its source register and its broken links are preserved
  unchanged; read this note alongside it, not instead of it.
- Concrete next action: a reviewer accepts or rejects the four revised verdicts,
  then decides which of T1–T8 are worth authorizing. T1 and T2 are the pair that
  decides whether the Zero W requirement has an evidenced builder at all; T3 and
  T4 are the pair that decides whether PiCompose can be cited as anything but
  reference material.
- Authorization needed: none of this is permission to clone, pin, submodule,
  build, flash, pull a container, or publish. A fork, remote push, image release
  or maintainer approach for PiCompose's licence needs separate approval. R04's
  acceptance still asks for pinned patch/test/maintenance plans per selected
  reuse; that belongs in the reviewed output, not here.
- Earlier claims this revision corrects: R04-1..R04-7 as tabulated above, plus
  the vendored-driver description shared with F04 and the "only 32-bit Trixie
  builder" line. F04's licence conclusion is adopted here, not revised.
- Reviewed report or decision adopting this: none yet.
