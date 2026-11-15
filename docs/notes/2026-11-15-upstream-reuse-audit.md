---
title: Upstream reuse audit for the Debra appliance
date: 2026-11-15
type: project-learning
status: unreviewed
task: R04
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - "https://github.com/OHF-Voice/linux-voice-assistant — main @ 12e51272d37d786ed3168955b3fb6eda3c7159ce (2026-11-14), release v1.1.18 (2026-10-29), checked 2026-11-15"
  - "https://github.com/florian-asche/PiCompose — main @ 1e5ff410163bcbb4704daea0c277fccc63a91214 (2026-10-26), tag v1.1.4 (2026-07-26), checked 2026-11-15"
  - "https://github.com/RPi-Distro/pi-gen — master @ 6e3ff62bfd9c690a6a3d1d7de259d5e0af40cb78 and arm64 @ c0d2c9f2cffc (both 2026-11-06), checked 2026-11-15"
  - "https://github.com/raspberrypi/rpi-image-gen — master @ fb44a4cde4ac (2026-11-05), release v2.9.0 (2026-10-23), checked 2026-11-15"
  - "https://github.com/davesteele/comitup — tag v1.47.1 (2026-04-20), head 2026-11-07, checked 2026-11-15"
  - "https://github.com/balena-os/wifi-connect — v4.11.91 (2026-10-22), checked 2026-11-15"
  - "https://github.com/rauc/rauc — v1.15.2 (2026-03-27), head 2026-11-13, checked 2026-11-15"
  - "docs/research/2026-11-15-lva-requirements.md (task VOICE01) — LVA dependency, audio and container requirements at the same commit"
  - "docs/research/2026-11-15-armv6-wheels.md (task Z02) — ARMv6 wheel/ELF findings for the LVA and Sendspin dependency sets"
  - "docs/research/2026-11-14-preliminary-findings.md — 'Upstream reuse and licensing follow-up' section, 2026-11-14"
  - ".local/delegation/20261114-parallel-research/REUSE-PREP-submitted.md — private, untracked prior reuse pass, 2026-11-14 (cited, not duplicated)"
  - "docs/evidence.md and docs/work/cards/R04.md — reporting rules and packet scope"
supersedes: []
---

## Summary

The evidence supports **reuse of three upstreams, none of them as "the Debra
appliance"**: linux-voice-assistant (LVA) as the voice component, pi-gen as the
image builder, and PiCompose as **reference material with two narrow
file-level reuse candidates**. A fourth candidate found during this audit,
Raspberry Pi's own **rpi-image-gen**, is the better long-term builder for
64-bit targets but cannot build for a Pi Zero W today, so it is reference-only
for now — specifically for its A/B slot and SBOM layers.

PiCompose remains *not* preselected, and this audit strengthens that: its images
are built from pi-gen's `arm64` branch (64-bit only, so no Pi Zero W at all),
they ship `pi`/`raspberry` with SSH enabled, they carry Snapcast rather than
Sendspin, and they have no rollback story. Its real value is a handful of
hard-won PipeWire/ALSA files and a stage layout worth imitating.

Nothing here was built, installed or run on hardware. Every claim is a reading
of a pinned public source on 2026-11-15, or a citation of an earlier Debra note.

### Labels and what "checked" means here

Per [evidence.md](../evidence.md): `upstream-documented` means a linked primary
source states it (a file read at a named commit counts); `reported` is a
third-party statement; `hypothesis` is inference from code; `unknown` is
unestablished. No `tested` row exists in this note — Debra ran nothing.
Version claims are pinned to the SHAs in the frontmatter; upstream `main`
branches are mutable and will drift from them.

### Already covered elsewhere — do not re-derive

| Topic | Canonical note | This note adds |
| --- | --- | --- |
| LVA dependencies, audio stack, container traps, ARMv6 packaging gaps | [lva-requirements](../research/2026-11-15-lva-requirements.md) (VOICE01) | Maintenance/activity data, the release-workflow platform matrix, the onboarding/update/recovery gap analysis, and the adoption verdict |
| ARMv6 wheel/ELF viability for LVA + Sendspin | [armv6-wheels](../research/2026-11-15-armv6-wheels.md) (Z02) | Nothing; ARMv6 conclusions are cited, not repeated |
| PiCompose licence conflict, pi-gen arm64 pin unresolved, first-pass reuse table | [preliminary-findings](../research/2026-11-14-preliminary-findings.md) and private `REUSE-PREP` | The **arm64 pin is now resolved** (`c0d2c9f2cffc`, 2026-11-06), plus rpi-image-gen, plus per-option verdicts |
| Commercial/whole-product alternatives (Voice PE, ESPHome voice kits, commercial speakers) | [complete-alternatives-comparison](2026-11-15-complete-alternatives-comparison.md) (R02) | Nothing — that packet is about buying or copying a finished product; this one is about upstream *code* to reuse |

## Candidate 1 — linux-voice-assistant (OHF-Voice)

What it is: an *experimental* Python voice satellite that speaks the ESPHome
protocol to Home Assistant, running local wake-word detection and playback
through `libmpv` on top of PulseAudio/PipeWire. `upstream-documented` — the
README's own first sentence calls it experimental
([README](https://github.com/OHF-Voice/linux-voice-assistant/blob/12e51272d37d786ed3168955b3fb6eda3c7159ce/README.md)).

| Property | Value | Label |
| --- | --- | --- |
| Licence | Apache-2.0 (`LICENSE.md`; GitHub API `license.spdx_id`) | upstream-documented |
| Latest release | `v1.1.18`, 2026-10-29 (the version the lab Pi 5 runs) | upstream-documented |
| Last commit on `main` | `12e5127` 2026-11-14; 51 commits in the 30 days to 2026-11-15 | upstream-documented (API) |
| Maintained? | Yes, actively — releases in Jul/Aug/Oct 2026, daily-scale commits | upstream-documented |
| Published container platforms | `linux/amd64,linux/aarch64` only | upstream-documented ([workflow L71](https://github.com/OHF-Voice/linux-voice-assistant/blob/12e51272d37d786ed3168955b3fb6eda3c7159ce/.github/workflows/docker-build-release.yml#L71)) |
| Stated minimums | 1 GHz CPU, 512 MB RAM, ~4 GB OS+software, 16 kHz mono mic | upstream-documented (README "Requirements") |
| Open issues | 79 | upstream-documented (API) |

**What Debra would inherit if adopted whole:** the runtime application, its
`preferences.json`/env configuration surface, the ESPHome discovery and identity
behaviour (mDNS `_esphomelib._tcp`, port 6053), wake-word model handling,
timer/announcement/media-player entities, and a Docker or bare-metal install
recipe. Details are in [lva-requirements](../research/2026-11-15-lva-requirements.md) and are
not repeated here.

**What it does not give us:** no onboarding, no Wi-Fi provisioning, no
hostname/identity scheme of Debra's kind, no update mechanism, no rollback, no
TUI, no Sendspin integration, no browser control, no ARMv6/armhf artifact.

| Option | What it would mean | Evidence | Verdict |
| --- | --- | --- | --- |
| a) Whole adoption as the foundation | Debra ships LVA's compose stack as the appliance | No onboarding, update, recovery or identity layer exists upstream; README says experimental; container is amd64/aarch64 only | **Rejected** |
| b) Partial reuse | Adopt the LVA *application* unmodified as the voice component, pinned by digest; copy its env/preferences schema shape and its systemd/compose unit patterns; write Debra's own onboarding, identity, update and rollback around it | Apache-2.0 permits it; the app is the part that is genuinely hard to replace; Debra already has it working on the lab Pi 5 | **Supported** — this is the recommendation |
| c) Reference only | Reimplement a satellite | Discards a working, actively maintained implementation; contradicts the reuse-first mandate | Rejected |
| d) Different approach | Use a different satellite (e.g. the archived `rhasspy/wyoming-satellite`) | `rhasspy/wyoming-satellite` is archived (last commit 2026-01-24), MIT, 212 open issues | Rejected on maintenance grounds |

## Candidate 2 — PiCompose (florian-asche)

What it is: prebuilt Raspberry Pi OS images (built with pi-gen) that boot a
Docker host, install a specific audio HAT's driver, start PipeWire, and
auto-deploy every compose project found in `/compose`. `upstream-documented`
(README overview). 44 stars.

| Property | Value | Label |
| --- | --- | --- |
| Licence | **Conflicting**: `LICENSE` is MIT ("Copyright (c) 2025 Florian Asche"); README §License says BSD-3-Clause | upstream-documented (both files read) |
| Latest semver tag | `v1.1.4`, 2026-07-26 (assets: base, 2MicHat-v2, ReSpeaker Lite, Satellite1 ± LVA) | upstream-documented (API) |
| Latest published image | 2026-10-26 branch prereleases; `main` head `1e5ff41`, 2026-10-26 | upstream-documented (API) |
| Activity | 5 commits in the 30 days to 2026-11-15; no semver release since July | upstream-documented |
| Build base | pi-gen **`arm64` branch**, `release: trixie`, `usimd/pi-gen-action@v1`, `runs-on: ubuntu-24.04-arm` | upstream-documented ([template](https://github.com/florian-asche/PiCompose/blob/1e5ff410163bcbb4704daea0c277fccc63a91214/.github/workflows/build-image-template.yml)) |
| Default account | `username: pi`, `password: raspberry`, `enable-ssh: 1`, `pubkey-only-ssh: 0` | upstream-documented (same file) |
| First-run experience | image auto-reboots to install drivers, then "you need to manually reboot one more time"; LVA's own docs say "you may need to reboot the board like 3 times" | upstream-documented ([README](https://github.com/florian-asche/PiCompose/blob/1e5ff410163bcbb4704daea0c277fccc63a91214/README.md), [LVA install.md](https://github.com/OHF-Voice/linux-voice-assistant/blob/12e51272d37d786ed3168955b3fb6eda3c7159ce/docs/install.md)) |

**What Debra would inherit:** a pi-gen stage library (base, four audio-driver
stages, LVA, Snapcast, finish), a compose-manager systemd unit and `picompose.conf`
schema, WirePlumber drop-ins, per-boot mixer tuning services, hostname-from-MAC,
and an Imager JSON feed.

**What it costs:** a Docker daemon and container runtime on every device
(`docker-ce`, `containerd.io`, buildx, compose plugin —
`01-stage-picompose/01-packages/02-packages`), the 64-bit-only pi-gen branch,
root-owned oneshot units, a mutable build chain, and an unresolved licence.

**What it does not give us:** no armhf/ARMv6 image (so no Pi Zero W), no
Sendspin (the tree contains `03-stage-linux-voice-assistant/02-snapcast`, nothing
Sendspin-related), no snapshot/rollback tooling, no captive portal, no pinned
runtime versions (`LVA_IMAGE_TAG` defaults to `latest`), no TUI, no browser
control, and an insecure default account.

| Option | What it would mean | Evidence | Verdict |
| --- | --- | --- | --- |
| a) Whole adoption as the foundation | Ship PiCompose images as Debra | arm64-only build → cannot serve the Pi Zero W requirement; `pi`/`raspberry` + SSH on; no rollback; licence conflict; a 44-star hobby project becomes Debra's release engineering | **Rejected** |
| b) Partial reuse | Take specific files/stages: the TLV320AIC3104 per-boot mixer service, the WirePlumber volume/no-suspend drop-in, the stage-directory layout, the Imager-JSON idea | These encode real hardware findings Debra would otherwise rediscover (see Reuse targets) | **Supported for two files after review**, not for stages as a dependency |
| c) Information/reference reuse | Learn from the stage layout, the `picompose.conf` option set, and the driver-selection-per-HAT pattern; write Debra's own equivalents | Same evidence, without inheriting the licence ambiguity, the arm64 pin or the Docker requirement | **Supported** — this is the primary recommendation |
| d) Different approach | No PiCompose involvement | Loses a genuinely useful audio-configuration reference | Allowed but wasteful |

## Candidate 3 — pi-gen (RPi-Distro)

What it is: the tool Raspberry Pi uses to build Raspberry Pi OS itself, and the
supported way to build custom images derived from it. `upstream-documented`
(README opening line).

| Property | Value | Label |
| --- | --- | --- |
| Licence | BSD-3-Clause (GitHub API) | upstream-documented |
| Releases | **None** (GitHub Releases API returns 404). Progress is tracked by per-image tags, newest `2026-10-06-raspios-trixie-armhf` / `-trixie-arm64` | upstream-documented |
| Last commit | `master` `6e3ff62` 2026-11-06; `arm64` `c0d2c9f2cffc` 2026-11-06 (**the previously unresolved arm64 pin**) | upstream-documented |
| Activity | 3 commits in 30 days — maintained, but as a maintenance track, not a feature track | upstream-documented |
| Branch model | "32 bit images should be built from the `master` branch. 64 bit images should be built from the `arm64` branch." | upstream-documented (README) |
| Build host | Debian-based, released after 2017; `sudo ./build.sh`; Docker path "partially isolates" and needs `--privileged` and loop devices | upstream-documented (README "Docker Build") |
| External stages | `STAGE_LIST` accepts arbitrary stage directories outside the tree | upstream-documented (README "Config") |

**What Debra would inherit:** a complete, reproducible-ish image pipeline, a
stage/hook model, export metadata (`os.json` now carries kernel and Debian
versions — commit `6e3ff62`), and the ability to add Debra stages without
forking.

**What it costs:** root or a privileged container on a Debian host; tens of GB of
workspace; two branch pins if Debra ships both 32- and 64-bit images; bash, not
a declarative config.

**What it does not give us:** nothing at runtime — no audio, no voice, no
onboarding, no update or rollback. It also does not make the ARMv6 problem go
away: an armhf image boots on a Zero W, but the LVA wake-word wheels are still
x86-64 inside an armv6l label (see [armv6-wheels](../research/2026-11-15-armv6-wheels.md)).

| Option | What it would mean | Evidence | Verdict |
| --- | --- | --- | --- |
| a) Whole adoption as the image-build foundation | Debra pins pi-gen and adds its own stages via `STAGE_LIST` | It is the only one of the four candidates that produces a 32-bit Trixie image today (`2026-10-06-raspios-trixie-armhf` tag; README's master=32-bit rule), which Debra needs for the Pi Zero W | **Supported** — recommended as the builder |
| b) Partial reuse | Copy individual stages (e.g. stage2's package set) into a different builder | No benefit over `STAGE_LIST` external stages; loses upstream updates | Rejected as primary, allowed for specific files |
| c) Reference only | Write a Debra builder from scratch | Months of work to reach parity on partitioning, firmware, first-boot | Rejected |
| d) Different approach | Use rpi-image-gen or CustomPiOS instead | rpi-image-gen: no Pi Zero W device class, arm64-only Debian bases (see candidate 4). CustomPiOS: GPL-3.0, `devel` branch, 613 stars, v2.0.0 2026-07-14 | Rejected for now; revisit if ARMv6 is dropped |

## Candidate 4 — rpi-image-gen (raspberrypi) — new, not in the source register

What it is: Raspberry Pi's newer declarative image generator (layers + hooks +
YAML), positioned *alongside* pi-gen: "For the tool used to create the Raspberry
Pi OS distribution, please go to pi-gen". `upstream-documented`
([README.adoc](https://github.com/raspberrypi/rpi-image-gen/blob/fb44a4cde4ac/README.adoc)).

| Property | Value | Label |
| --- | --- | --- |
| Licence | BSD-3-Clause | upstream-documented (API) |
| Latest release | `v2.9.0`, 2026-10-23; head `fb44a4c` 2026-11-05; 961 stars | upstream-documented (API) |
| Privilege | "The tool runs as a regular user and does not require root privileges", but the build needs `CAP_SYS_ADMIN` (mount namespace) — so `--privileged`/`unconfined` in a container | upstream-documented (README "Important") |
| Supported host | "developed on Raspberry Pi OS, with Debian Bookworm and Trixie arm64 as the supported native hosts"; amd64 via QEMU "not formally supported" | upstream-documented |
| Device classes | `zero2w,pi3,pi4,cm4,pi5,cm5` — **no Pi Zero / Zero W class** | upstream-documented ([`layer/rpi/device/family-base.yaml`](https://github.com/raspberrypi/rpi-image-gen/blob/fb44a4cde4ac/layer/rpi/device/family-base.yaml)) |
| Feature ceiling by target | "The build target can be any Raspberry Pi, but all features are available only on RPi4 or later" | upstream-documented ([getting_started.adoc](https://github.com/raspberrypi/rpi-image-gen/blob/fb44a4cde4ac/getting_started.adoc)) |
| 32-bit support | Raspbian armhf base layers exist, and armhf kernels `linux-image-v7`/`v7l` — but **no v6 (ARM1176) kernel layer** and no armhf Debian base | upstream-documented (tree at `fb44a4c`) |
| Provenance | Reproducible builds (`SOURCE_DATE_EPOCH`), SBOM/CVE via `deploy99-manifest`, signed boot, IDP provisioning | upstream-documented (v2.9.0 notes; `builtin/hooks/deploy99-manifest`) |

**What Debra would inherit:** the A/B slot layer (`layer/rpi/device/ab-slots.yaml`
+ `slot-mapper` with `rpi-slot-tryboot`, exposing `/dev/disk/by-slot/{active,other}/{boot,system}`),
an SBOM/manifest hook, declarative layer composition with validation, and an
optional secure-boot/provisioning path via `rpi-sb-provisioner`.

**What it costs:** a native arm64 Debian host for the supported path, a
`CAP_SYS_ADMIN` build, and a tool still self-described as "under active
development" whose v2.9.0 release notes warn "Custom layers will probably need
updating" — an API-churn cost for anything Debra builds on it.

**What it does not give us:** a Pi Zero W target, ARMv6, any runtime component,
any onboarding UI.

| Option | What it would mean | Evidence | Verdict |
| --- | --- | --- | --- |
| a) Whole adoption as the foundation | Build all Debra images with it | Cannot express the Pi Zero W target (no class, no v6 kernel, "features only on RPi4 or later") | **Rejected for now** |
| b) Partial reuse | Import its `ab-slots`/`slot-mapper` design or the manifest hook into a Debra pi-gen stage | The code is BSD-3-Clause and self-contained, but it assumes systemd + GPT labels + `tryboot`; how much works on ARMv6 is unproven | **Possible later**; today (c) |
| c) Reference only | Adopt its A/B slot semantics, `by-slot` symlink contract and SBOM manifest idea as the *design* for Debra's recovery story, implemented in our own stages | Debra's recovery comparison is still open (see preliminary findings); this is the most complete public worked example of the pattern | **Supported** — recommended now |
| d) Different approach | RAUC / systemd-sysupdate / btrfs | RAUC is LGPL-2.1, v1.15.2 2026-03-27, active; still an open comparison in the recovery packet | Not decided here |

## Secondary candidates (maintenance facts only)

These were already named in the preliminary findings; only current status is
added, no new recommendation.

| Project | Licence | Last release | Last commit | Note | Label |
| --- | --- | --- | --- | --- | --- |
| [comitup](https://github.com/davesteele/comitup) | GPL-2.0 | `v1.47.1`, 2026-04-20 | 2026-11-07 | NetworkManager-based fallback hotspot + portal; copyleft — bundling unmodified is one thing, patching it another | upstream-documented |
| [wifi-connect](https://github.com/balena-os/wifi-connect) | Apache-2.0 | `v4.11.91`, 2026-10-22 | 2026-10-22 | Requires NetworkManager; README documents a list of dongles known *not* to work in AP mode; install script targets Raspbian Stretch | upstream-documented |
| [RAUC](https://github.com/rauc/rauc) | LGPL-2.1 | `v1.15.2`, 2026-03-27 | 2026-11-13 | A/B update framework, still a comparison candidate | upstream-documented |
| [pi-gen-micro](https://github.com/raspberrypi/pi-gen-micro) | Apache-2.0 | `v0.4.1` | last push 2026-10-27 | Minimal images "which do not contain apt or dpkg" — interesting for boot time, hostile to field updates | upstream-documented |
| [rpi-sb-provisioner](https://github.com/raspberrypi/rpi-sb-provisioner) | Apache-2.0 | `v2.3.5` | 2026-11-12 | Factory provisioning/signed boot; out of scope until identity design exists | upstream-documented |
| [rhasspy/wyoming-satellite](https://github.com/rhasspy/wyoming-satellite) | MIT | `v1.4.1`, 2025-02-10 | 2026-01-24 | **Archived**; 212 open issues. Not a live alternative to LVA | upstream-documented |

## Reuse targets

Concrete, with the revision they were read at. Nothing here is approved for
copying — each needs licence review and a named owner (see Traps).

**From LVA (Apache-2.0) — adopt as a component, not as files to copy:**

1. The released container, pinned by digest, not tag:
   `ghcr.io/ohf-voice/linux-voice-assistant:v1.1.18@sha256:…` — the upstream
   compose defaults to `:latest`
   ([docker-compose.yml](https://github.com/OHF-Voice/linux-voice-assistant/blob/12e51272d37d786ed3168955b3fb6eda3c7159ce/docker-compose.yml)),
   which is exactly what Debra's pinned-component rule forbids.
2. `docs/install_application.md` environment-variable table as the *shape* of
   Debra's device-side option set — `AUDIO_INPUT_DEVICE`, `AUDIO_OUTPUT_DEVICE`,
   `MIC_VOLUME`, `MIC_AUTO_GAIN`, `MIC_NOISE_SUPPRESSION`, `WAKE_MODEL`,
   `ENABLE_OUTPUT_ONLY`, `PREFERENCES_FILE`. PiCompose's filled-in `.env`
   (`03-stage-linux-voice-assistant/.../files/lva/.env`) is a readable example.
3. `docker-entrypoint.sh` + `network_mode: host` + `group_add: [audio]` +
   `cap_add: [SYS_NICE]` as the minimum privilege set — the permission model is
   the audio socket, not the sound card.
4. `docs/behavior.md` for the duck/pause/resume semantics Debra must *not*
   assume for an independent Sendspin receiver.

**From PiCompose (licence unresolved — read, then rewrite or attribute):**

5. `02-stage-audiodriver-2michat-v2/02-set-audio-volume/files/configure_audio.sh`
   — the TLV320AIC3104 recipe Debra independently hit on the lab Pi 5:
   `HP DAC 100%`, `Line DAC 100%`, `HP`/`Line` unmute, `PGA 80% cap`, then
   `wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0`, then `alsactl store`. Its comment
   records that the card alias is still `seeed2micvoicec` for both HAT revisions
   and that the `PCM` control distinguishes v2's tlv320aic3x from v1's wm8960.
6. The same stage's `configure_audio.service` pattern: oneshot, re-run **every
   boot** (not first-boot-only), because WirePlumber resets ALSA state per
   session. Debra's own test record shows the same class of trap.
7. `01-stage-picompose/03-install-pipewire-audio/files/50-alsa-output.conf` —
   `audio.volume = 1.0`, `session.suspend-timeout-seconds = 0`,
   `node.pause-on-idle = false` for `node.name = "~alsa_output.*"`. Review before
   use: a blanket 100 % volume on every ALSA output is a hearing/speaker-safety
   default, and the match is broad.
8. `01-stage-picompose/04-set-hostname/files/configure_hostname.sh` — the
   MAC-derived identity idea (`picompose-<mac>`), which Debra would respell as
   `debra-<id>`; note it only fires when the hostname is still `picompose`.
9. The stage-directory layout itself (`NN-stage-name/NN-substep/NN-run.sh` +
   `prerun.sh`) as the organising convention for Debra's own pi-gen stages.

**From pi-gen (BSD-3-Clause) — adopt as the builder:**

10. `STAGE_LIST` external stages so Debra never forks pi-gen
    ([README "Config"](https://github.com/RPi-Distro/pi-gen/blob/6e3ff62bfd9c690a6a3d1d7de259d5e0af40cb78/README.md)).
11. `export-image` metadata (`os.json` kernel/Debian fields, commit `6e3ff62`)
    as the provenance record attached to each factory image.
12. Pin `master` for armhf and `arm64` at `c0d2c9f2cffc` for aarch64; both
    currently resolve to the same date, which will not stay true.

**From rpi-image-gen (BSD-3-Clause) — design reference:**

13. `layer/rpi/device/ab-slots.adoc` — the `/dev/disk/by-slot/{active,other}/{boot,system}`
    contract, GPT-label-first with a static fallback, explicitly agnostic about
    filesystem, encryption and update mechanism.
14. `layer/rpi/device/slot-mapper/` — `rpi-slot-tryboot` and the
    initramfs/udev helpers that make slot selection survive a failed boot.
15. `builtin/hooks/deploy99-manifest` and the v2.9.0 reproducible-build notes
    (`SOURCE_DATE_EPOCH`, `BUILD_ID`) as the shape of Debra's image manifest.
16. `getting_started.adoc`'s worked example of provisioning Wi-Fi into
    NetworkManager offline inside a hook (`nmcli --offline connection add …`) —
    a pattern Debra's identity/network stage can borrow without adopting the tool.

## Traps

1. **A branch name is not a pin.** PiCompose's build calls
   `usimd/pi-gen-action@v1` with `pi-gen-version: arm64`; both are mutable. Pinning
   PiCompose's commit does not pin the image it produces. `upstream-documented`.
2. **`linux/armv6l` and `armhf` are not ARMv6 promises.** Already established in
   [armv6-wheels](../research/2026-11-15-armv6-wheels.md); the same caution applies to any
   "32-bit supported" reading of pi-gen or rpi-image-gen. An armhf image boots;
   it does not make the wake-word wheels run.
3. **LVA's container has no 32-bit variant at all** — `platforms: linux/amd64,linux/aarch64`
   in the release workflow. On a Pi Zero W there is nothing to pull, so a Debra
   Zero W image must run LVA from source with a self-built TFLite, or move wake
   detection to Home Assistant. `upstream-documented`.
4. **`:latest` is the default in both upstream compose files.** Adopting either
   compose file unchanged violates Debra's pinned-component rule on day one.
5. **PiCompose's defaults are the opposite of Debra's security posture**:
   `pi`/`raspberry`, SSH enabled, `pubkey-only-ssh: 0`, and a README instruction
   to "change the password if you didn't change it before". `upstream-documented`.
6. **PiCompose's licence is internally contradictory** (MIT file, BSD-3-Clause
   README). Treat file-level reuse as requiring either attribution to the MIT
   text or a rewrite; do not declare blanket clearance. This was already flagged
   in the preliminary findings and is unchanged at `1e5ff41`.
7. **UID 1000 is hardcoded** in PiCompose's audio units
   (`Environment=XDG_RUNTIME_DIR=/run/user/1000`) and in LVA's compose defaults.
   Any Debra user model that is not "first user is 1000" silently breaks audio.
8. **`script/setup` in LVA deletes `.venv` unconditionally** — already recorded
   in [lva-requirements](../research/2026-11-15-lva-requirements.md); repeated here because it
   is the kind of thing a "just reuse the installer" plan walks into.
9. **rpi-image-gen is not a drop-in pi-gen replacement for 32-bit work**: no
   `zero`/`zerow` device class, arm64-only Debian base layers, and "all features
   are available only on RPi4 or later". `upstream-documented`.
10. **rpi-image-gen's own API is moving**: v2.9.0 notes say "Custom layers will
    probably need updating" and the README says it is "under active development".
    Anything Debra builds on its layer format inherits that churn.
11. **Comitup is GPL-2.0.** Shipping the unmodified program is ordinary
    distribution; patching or linking it changes the obligation. Legal review
    before it becomes a Debra dependency.
12. **`wifi-connect`'s documented install path is Raspbian Stretch-era** and its
    README lists dongles that do not work in AP mode. It also needs
    NetworkManager to be the active manager, which is a host-level decision, not
    an app-level one.

## Not verified / open questions

- **Nothing was built, flashed, installed or run.** No pi-gen or rpi-image-gen
  build; no image inspected; no Docker pull. Every "would inherit" statement is
  a reading of source, not a demonstration.
- **LVA wake-word model licences** (microWakeWord/openWakeWord model files
  bundled in the container) are `unknown`. Apache-2.0 covers the code; it may not
  cover every bundled model. Needed before Debra redistributes an image.
- **Whether a Debra-owned pi-gen stage can produce a working ARMv6 voice stack**
  is `unknown` and depends on the TFLite build question in
  [armv6-wheels](../research/2026-11-15-armv6-wheels.md), not on the builder.
- **Whether rpi-image-gen's `ab-slots`/`tryboot` mechanism works on a Pi Zero W**
  is `unknown`. The boot documentation cited in the preliminary findings says all
  models support `tryboot`; slot *management* on a single-card ARMv6 device is
  untested.
- **PiCompose's first-boot account behaviour** (does `pi`/`raspberry` survive an
  Imager-customised flash? does the documented extra reboot always happen?) is
  `unknown`; the README describes an intent, and `disable-first-boot-user-rename: 0`
  is a build input, not a result.
- **Comitup's presence in current Raspberry Pi OS repositories** was not checked;
  package availability and version are `unknown`.
- **PiCompose's driver provenance**: the v1 stage vendors a `seeed-voicecard-v2`
  tree and v2 relies on Seeed's `seeed-linux-dtoverlays`; the licences and
  versions of those vendored files were not audited.
- **pi-gen's future**: whether Raspberry Pi intends pi-gen to remain the
  recommended path for 32-bit custom images, or to steer custom builds to
  rpi-image-gen, is `unknown`. The READMEs describe a division of labour, not a
  deprecation.
- **LVA's minimum Home Assistant version** remains `unknown` (unchanged from
  VOICE01).
- Prior pass' open item, now partly closed: the pi-gen `arm64` pin is resolved to
  `c0d2c9f2cffc` (2026-11-06). It is a branch head, not a release, and must be
  re-pinned deliberately rather than tracked.

## Verification

- Exact procedure: read-only retrieval of public sources on 2026-11-15 —
  `gh api` for repository metadata, releases, tags, branches, commits and trees;
  `curl` of `raw.githubusercontent.com` files at the SHAs named above. Working
  directory `/tmp/opencode/r04` (scratch, not preserved).
- Observed: all repositories, releases, tags and commits above resolved as
  stated; `pi-gen` GitHub Releases API returned 404 (no release objects); two
  404s for stale paths (`rpi-image-gen/README.md`, `pi-gen/docs/README.md`).
- Not run: no build, no container pull, no image inspection, no device contact,
  no dependency install, no submodule or pin change, no commit.
- Sanitized artifacts: none. The only file written is this note.

## Handoff and correction links

- Current state: research only, on base `ac2298c308d374d06bdc1ebef9340dc134b3ad1a`
  with other sessions' uncommitted edits present in the tree.
- Concrete next action: a reviewer decides whether LVA-as-component, pi-gen-as-builder
  and the two PiCompose file candidates become F03's dependency mechanism; the
  rpi-image-gen A/B material feeds the open recovery comparison rather than F03.
- Authorization needed: none of this is permission to clone, pin, submodule,
  build, flash or publish. A fork, remote push or image release needs separate
  approval. `docs/work/cards/R04.md` acceptance is not satisfied by this note
  alone — it asks for pinned patch/test/maintenance plans per selected reuse,
  which belongs in the reviewed R04 output.
- Earlier claims this note updates: the preliminary findings' "pi-gen `arm64`
  pin remains unresolved" is now resolved; its PiCompose licence conflict and
  reference-only framing are confirmed at a later commit.
- Reviewed report/decision that adopts this: none yet.
