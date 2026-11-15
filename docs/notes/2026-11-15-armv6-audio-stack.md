---
title: What is documented about the PipeWire audio stack on ARMv6 (Pi Zero W)
date: 2026-11-15
type: project-learning
status: unreviewed
task: none — unattended research run, 2026-11-15
author: OpenCode agent
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - Debian package pages, trixie and bookworm, armhf — https://packages.debian.org/trixie/pipewire , https://packages.debian.org/trixie/wireplumber , https://packages.debian.org/bookworm/pipewire , https://packages.debian.org/bookworm/wireplumber (checked 2026-11-15)
  - Debian wiki, ArmHardFloatPort — https://wiki.debian.org/ArmHardFloatPort (checked 2026-11-15)
  - Debian wiki, ArmEabiPort — https://wiki.debian.org/ArmEabiPort (checked 2026-11-15)
  - Raspbian armhf archive, trixie and bookworm package indexes and .debs — https://archive.raspbian.org/raspbian/dists/trixie/Release (checked 2026-11-15)
  - PipeWire and WirePlumber issue trackers — https://gitlab.freedesktop.org/pipewire/pipewire/-/issues/235 , https://gitlab.freedesktop.org/pipewire/wireplumber/-/issues/81 (checked 2026-11-15)
  - PipeWire 1.4.2 source, cpu-arm.c and fmt-ops.c — https://gitlab.freedesktop.org/pipewire/pipewire/-/blob/1.4.2/spa/plugins/support/cpu-arm.c (checked 2026-11-15)
  - WirePlumber 0.5.8 wireplumber.conf, main-embedded profile — https://gitlab.freedesktop.org/pipewire/wireplumber/-/blob/0.5.8/src/config/wireplumber.conf (checked 2026-11-15)
  - ALSA project, PCM plugins (dmix) — https://www.alsa-project.org/alsa-doc/alsa-lib/pcm_plugins.html (checked 2026-11-15)
  - BlueZ README and org.bluez.MediaEndpoint documentation — https://git.kernel.org/pub/scm/bluetooth/bluez.git/plain/README , https://raw.githubusercontent.com/bluez/bluez/master/doc/org.bluez.MediaEndpoint.rst (checked 2026-11-15)
  - Raspberry Pi trixie-feedback issue 24 (maintainer statements about 32-bit on Zero W) — https://github.com/raspberrypi/trixie-feedback/issues/24 (checked 2026-11-15)
  - Repository: docs/research/2026-11-15-armv6-wheels.md, docs/notes/2026-11-15-storage-durability.md, docs/notes/2026-11-15-music-transport-and-control-map.md (read 2026-11-15)
supersedes: []
---

# What is documented about the PipeWire audio stack on ARMv6

## Summary

The honest answer is a documentation gap, not a yes.

- **The Debian 13 and 12 armhf packages are not ARMv6 builds.** Debian's armhf port
  requires "at least an Armv7 CPU with Thumb-2 and VFP3D16", and the actual
  trixie/bookworm armhf libraries carry `Tag_CPU_arch: v7` (one carries NEON).
  A Pi Zero W is ARMv6/VFPv2, so the Debian packages are the wrong instruction set
  regardless of what version number they print.
- **Raspberry Pi OS 32-bit is a separate ARMv6 rebuild** from the Raspbian archive:
  *the same version strings* (PipeWire 1.4.2-1 / WirePlumber 0.5.8-2 in trixie,
  0.3.65 / 0.4.13 in bookworm) but libraries tagged `v6`/`VFPv2`. That is the only
  build that is instruction-compatible with the board, and it is the one the
  Pi Zero would actually run.
- **No upstream document says PipeWire supports ARMv6 or armhf.** The only
  armv6-specific upstream item found is a 2020 build failure when NEON was
  auto-enabled, and WirePlumber still has an open 32-bit ARM test-failure issue
  that names "armhf (armv6 with FPU)".
- **Nothing in the record measures the stack's memory on a 512 MB ARMv6 board.**
  Everything available is other-architecture data or a desktop session, so the
  answer to "what is left for a voice assistant" is currently `unknown` — and
  LVA's own documented floor is the whole 512 MB.
- **ALSA-only is viable for one sink and is already the Raspberry Pi OS Lite
  default**, but it removes the generic per-stream gain that a duck needs. Whether
  that matters depends entirely on whether the music receiver ducks itself.

No device was contacted, nothing was installed, and nothing below is a runtime
test. Where a fact could not be sourced it is marked `U`.

## 1. How to read this note

| Label | Meaning here |
| --- | --- |
| `D` documented | A linked primary source states it (upstream project, Debian, distro) |
| `O` observed | A published artifact was downloaded and inspected — package index, `.deb`, ELF attributes. Reproducible, but not executed |
| `R` reported | A named third party or individual states it; context and limits given |
| `T` tested | Would require the named hardware and procedure. **Not used in this note: no device was touched** |
| `H` hypothesis | Inference from code, packaging or arithmetic, not executed |
| `U` unknown | Not established; never read an empty cell as "no" |

Two things this note deliberately does not do: it does not treat "the package
exists for armhf" as "the code runs on ARMv6", and it does not treat a maintainer's
"it boots" as "the audio stack works".

## 2. Which versions ship, and what those builds actually contain

Package versions (checked 2026-11-15):

| Suite | PipeWire | WirePlumber | alsa-lib | BlueZ |
| --- | --- | --- | --- | --- |
| Debian 13 trixie armhf | 1.4.2-1 | 0.5.8-2 | 1.2.14-1+deb13u1 | 5.82-1.1 |
| Debian 12 bookworm armhf | 0.3.65-3+deb12u1 | 0.4.13-1 | 1.2.8-1 | 5.66-1+deb12u2 |
| Raspbian trixie armhf (Pi OS 32-bit) | 1.4.2-1 | 0.5.8-2 | 1.2.14-1+deb13u1 | 5.82-1.1 |
| Raspbian bookworm armhf | 0.3.65-3+deb12u1 | 0.4.13-1 | 1.2.8-1+b1 | 5.66-1+deb12u2 |

Sources: Debian package pages [1][2][3][4][6][7][8][9]; Raspbian `Release` and
`main/binary-armhf/Packages.xz` [11]. The Pi OS rebuild ships the *same version
strings* as Debian, which is the trap: a version string does not identify the
instruction set. The image's own `sources.list` was not read, so "the archive the
32-bit image installs from" is `R`/`U`; what is `O` is that this archive's armhf
index carries these exact versions.

Instruction-set evidence, from `readelf -A` on the shipped armhf objects:

| Build | `libpipewire` | `libwireplumber` | `spa-0.2/alsa` | `spa-0.2/audioconvert` |
| --- | --- | --- | --- | --- |
| Debian trixie armhf | v7, VFPv3-D16 | v7, VFPv3-D16 | v7, VFPv3-D16 | v7, VFPv3, **NEONv1** |
| Debian bookworm armhf | v7, VFPv3-D16 | — | — | — |
| Raspbian trixie armhf | v6, VFPv2 | v6, VFPv2 | v6, VFPv2 | v6, VFPv3, **NEONv1** |
| Raspbian bookworm armhf | v6, VFPv2 | v6, VFPv2 | — | — |

`O`. Objects inspected: `libpipewire-0.3-0t64 1.4.2-1_armhf` (deb
`e53b1c31…70`), `libspa-0.2-modules 1.4.2-1_armhf` (`27811b1d…c9`),
`libwireplumber-0.5-0 0.5.8-2_armhf` (`a3828090…2e`) from
`ftp.at.debian.org/debian/pool/main`, and the same three packages from
`archive.raspbian.org/raspbian/pool/main` (`9b7e2bce…dd`, `50021857…91`,
`aff21058…44`); plus `pipewire-bin` binaries and the Raspbian bookworm
`0.3.65`/`0.4.13` libraries.

What that means, carefully:

1. `Tag_CPU_arch: v7` on every object means the compiler was allowed to emit
   ARMv7 and VFPv3 instructions throughout. ARMv7 adds `movw`/`movt`, Thumb-2 and
   VFPv3 register forms that an ARM1176 (ARMv6, VFPv2) does not have. Executing
   one is a SIGILL. That the Debian binary **will** fault on a Zero is `H`, but it
   is the same inference that makes Debian's own baseline statement (`D`: "at
   least an Armv7 CPU with Thumb-2 and VFP3D16" [5]) meaningful.
2. `readelf -A` on a shared object reports the *union* of its input objects'
   attributes, so a NEON tag does not prove the default path executes NEON. In
   both builds the audioconvert plugin contains a NEON object while PipeWire
   selects implementations at runtime: `spa/plugins/support/cpu-arm.c` reads
   `/proc/cpuinfo`, sets `SPA_CPU_FLAG_NEON` only if the `Features:` line contains
   `neon`, and the format-conversion table gates each NEON entry on that flag
   (`MAKE(..., SPA_CPU_FLAG_NEON)`) [15][16] (`D`, code; `O`, the Raspbian `.so`
   contains `conv_s16_to_f32d_neon` symbols).
3. On a BCM2835 the `Features:` line does not advertise `neon`, so the NEON paths
   should not be chosen. Whether that holds for every plugin on ARMv6 is `U` —
   only the audioconvert/cpu path was read.

So the ARMv6 question resolves to: **Raspbian's armhf rebuild is the only build
that is instruction-compatible, and its compatibility rests on runtime dispatch
rather than on a documented ARMv6 baseline.** Debian's armhf port cannot be the
answer for a Zero at all (`D` [5]).

One adjacent Debian fact, for completeness: Debian's `armel` port explicitly
covers "ARM architecture versions 4T, 5T, and 6" with a 5T baseline [10], and
trixie publishes PipeWire 1.4.2-1 and WirePlumber 0.5.8-2 for armel [35]. It is a
soft-float ABI port, not interchangeable with armhf packages on a Pi OS image;
using it would mean an armel userland, which is `U` as a practical Debian base.

## 3. Documented armv6/armhf breakage, missing instructions and crashes

| Item | Status | Detail |
| --- | --- | --- |
| Debian armhf baseline excludes ARMv6 | `D` [5] | The port page states the ARMv7/VFPv3-D16 requirement. This is the root cause of everything else in this row group |
| PipeWire built with NEON broke the armv6l build | `D` [12] | Issue 235 (2020-05-01, closed): "pipewire-0.3.4 enabled compiling with NEON support on ARM, however … armv6l doesn't support NEON at all"; setting `have_neon = false` allowed the build. Fixed-state detail after closure: `U` |
| WirePlumber 32-bit ARM test failures, open | `D` [13] | Issue 81 (opened 2021-10-23, still open, last updated 2025-10-09): failures on `armv7` and on "`armhf` (`armv6` with FPU)" in `endpoint.c` and `si-standard-link.c` tests. Reported on Alpine/musl. **Runtime impact: `U`** — no evidence this reproduces on Raspberry Pi OS glibc |
| Float parsing tests fail on armv7/armhf | `D` [14] | Issue 4315 (2024-09-24, closed same day): `utils_strtof`/`utils_strtod`/`properties_parse_float` return 0.0 where 1.0 expected, on pmOS/Alpine (musl). Test-level; whether it touches audio properties at runtime is `U` |
| Debian bug reports naming armhf for pipewire/wireplumber in trixie | `U` | The trixie BTS pages [34] were fetched and contained no armhf/armv6 mention; absence of a bug report is not evidence of correctness |
| BlueZ on ARMv6 | `U` | No armv6/armhf-specific BlueZ issue was found. BlueZ is the same 5.82/5.66 source on both builds; its Bluetooth transports are not architecture-sensitive in any way this session could cite |
| Kernel/HAT side (I2S codec, UCM) | `U` | The ReSpeaker-style HAT path depends on the codec driver and ALSA UCM data, not on the audio server's architecture. Not investigated here; see the enclosure/audio corrections note for the HAT sides that are still unverified |

Two non-architecture traps that would look like "ARMv6 is broken" in the field:

- **Headless WirePlumber may wait for a seat/graphical session.** A 2026
  third-party guide for a headless Pi Zero Bluetooth receiver documents switching
  WirePlumber to the `main-embedded` profile to avoid this, and that profile is
  real: WirePlumber 0.5.8 ships `main-embedded = { inherits = [ main,
  mixin.systemwide-session, mixin.stateless ] }` described as "typical profile for
  embedded use cases, systemwide without maintaining state" (`D` [33], `R` [32]).
  A headless appliance should start from that, not the desktop default.
- **WirePlumber has a known BlueZ-path crash.** Issue 5470 (2026-07-14 →
  closed 2026-09-13): SIGSEGV in `g_variant_type_info_unref` when `bluetoothd` is
  killed, in the `libspa-bluez5` D-Bus call (`D` [17]). Not ARMv6-specific, but it
  is the bluez path an appliance would exercise.

Nothing found documents ARMv6 crashing *in the Raspbian build*. That is not the
same as "it works": see §7.

## 4. Runtime memory on a 512 MB board

Process model first, because "the session manager" is ambiguous: on this stack the
session manager **is** WirePlumber (`D`: Debian describes it as a "modular
session / policy manager for PipeWire" [2]). The processes are `pipewire`,
`wireplumber`, and — only if PulseAudio-API clients exist — `pipewire-pulse`
(`D` [1]). LVA's `soundcard` backend is PulseAudio-only and sendspin's volume path
uses `libpulse`, so the third process is effectively required for Debra's two
applications (`D`, this repository's ARMv6 note [25]).

| Data point | Value | Label | Transferable to a Zero W? |
| --- | --- | --- | --- |
| pipewire / wireplumber / pipewire-pulse RSS on the research host (Fedora 45, x86_64, PipeWire 1.6.11, WirePlumber 0.5.19, desktop session with many clients) | 19,116 kB / 31,408 kB / 16,992 kB | `O` | No. Different architecture, versions and client count |
| `systemctl --user status wireplumber` in a forum post, 0.4.11, x86_64 desktop | `Memory: 11.6M` | `R` [21] | Directionally; still not ARMv6 |
| PipeWire developer thread on per-client allocations: audioconvert load 3.7 MB, `reply_create_playback_stream` 4 MB, buffers 1 MB + 256K×2 + 128K; RSS retention after 100 clients attributed to the allocator, not a leak | ≈8–9 MB per playback client | `R` [20] | Per-client cost should scale similarly; unmeasured |
| Measured pipewire + wireplumber + pipewire-pulse on ARMv6 / Pi Zero W | — | `U` | Nothing published was found |

The budget question, then, is arithmetic on unknowns:

- Board: 512 MB total, single-core 1 GHz ARM11 (`R`: repository parts inventory
  [26]; raspberrypi.com returned HTTP 403 to this session — see §7).
- LVA upstream requirement: **"Memory: min. 512MB"**, CPU 1 GHz, and
  "OS: linux/amd64 or linux/aarch64" (`D` [18]). That floor is the entire board,
  and the listed OS targets exclude 32-bit ARM altogether.
- The Debian/Raspberry Pi OS base, Python, numpy, TFLite and the wake-word model
  are then all on the same 512 MB, before PipeWire's tens of megabytes.

So the defensible statement is: **the audio stack's share is plausibly a few tens
of MB (17–31 MB per process on a desktop-class system, so 35–70 MB for the three),
and on a 512 MB board that is not negligible — but no source measures it on ARMv6,
and LVA's own documented minimum already equals the whole board.** That range is
`H`, built from the `O`/`R` rows above. Whether it leaves enough for a voice
assistant is `U`, not "no".

CPU is the quieter constraint: PipeWire's graph defaults to 48 kHz with
`default.clock.quantum = 1024`, i.e. a 21.3 ms cycle (`D` [22]); a 44.1 kHz library
resampled to 48 kHz costs cycles on one 1 GHz core that is also running Python and
the wake-word model. `H`, unmeasured.

## 5. The ALSA-only alternative

What a single playback sink actually loses without PipeWire:

| Capability | With PipeWire (+WirePlumber) | ALSA directly |
| --- | --- | --- |
| Two clients at once (music + speech) | Native mixing in the graph | Requires the `dmix` plugin; ALSA hardware channels are otherwise exclusive (`D` [23]) |
| Per-stream gain (duck one, not the other) | Sink vs sink-input are distinct objects; per-stream gain is independent (`D` [24], already worked out in this repo) | No per-application object. Mixer elements belong to the card; lowering one lowers everything |
| Device policy / default device / hotplug | WirePlumber session policy (`D` [2][33]) | Application chooses `plughw:X,Y`; no policy layer |
| Bluetooth audio | `libspa-0.2-bluetooth` 1.4.2-1 connects BlueZ transports to the graph (`D` [1][11][31]) | Needs an endpoint provider: BlueALSA `bluez-alsa-utils 4.3.1-3` exists in trixie (`D` [27]); BlueZ itself only registers endpoints via a separate server process (`D` [28]) |
| Application compatibility | LVA's `soundcard` (PulseAudio-only) and sendspin's `pulsectl` volume path work via `pipewire-pulse` (`D` [25]) | Those code paths have nothing to talk to; volume/duck must be rebuilt |
| Echo cancellation / noise suppression / filter nodes | `module-echo-cancel`, filter-chain, loopback (`D` [24]) | Not available; per-application DSP only |

What is *not* lost: playing one stream to one ALSA device. Raspberry Pi OS Lite on
Bookworm ships **no sound server at all** — a Raspberry Pi maintainer states that
"neither pipewire nor pulseaudio need to be installed on the Lite image for audio
output", tested with `aplay` (`D` [29]); whether Trixie Lite is the same is `U`.
ALSA-only is therefore not exotic; it is the default shape of a headless Pi.

**Does the loss matter for a music receiver that must duck for speech?** It depends
on where the duck is implemented, and this is the one place a clear answer exists:

- If the duck is an **external controller lowering the music stream**, that control
  is `pactl set-sink-input-volume`-shaped and exists only because a sound server
  owns per-stream gain. ALSA-only converts it into a card-mixer change that
  attenuates the speech too — the feature is lost, not degraded.
- If the duck is **inside the music receiver**, it survives. Sendspin's volume
  modes include a software gain (TUI default) as well as ALSA mixer, PulseAudio
  sink and hook-script modes (`D`, already recorded in the music transport note
  [24]). A software gain multiplies that client's samples and is independent of
  whatever else is playing.

So: the loss matters, and it matters specifically as a **design constraint** — with
ALSA-only, ducking must be a property of the music player (or a per-PCM `softvol`
arrangement), not a property of the audio system. That is a real cost, but it is
not a blocker for a single-sink receiver; it is a constraint on which components
can be reused unchanged.

## 6. What existing notes already answer

Cited rather than repeated:

- **`docs/research/2026-11-15-armv6-wheels.md`** (the ARMv6 wheel note) already
  establishes the dependency facts this note relies on: `soundcard`'s Linux backend
  is PulseAudio-only and needs the unversioned `libpulse.so`; `pulsectl-asyncio`
  needs `libpulse0`; `linux_armv6l` is an ABI label rather than an instruction-set
  promise; and the two wake-word engines ship an x86-64 TFLite library. Do not
  re-derive those here. It does **not** cover PipeWire/WirePlumber versions,
  instruction-set tags of distro audio packages, or audio-stack memory.
- **`docs/notes/2026-11-15-storage-durability.md`** [30] answers the storage and power
  half of "will a 512 MB appliance survive": SD wear, write-abort behaviour, zram
  instead of SD swap, undervoltage as the documented corruption cause. It does not
  discuss audio memory; its zram section is the right place to look when the
  question becomes "what happens when PipeWire's buffers meet a full board".
- **`docs/notes/2026-11-15-music-transport-and-control-map.md`** already maps
  sink volume vs sink-input volume vs filter node, and why a device-side duck
  implemented as player volume rewrites MA's balance. §5 above builds on it; it
  does not contain the ALSA-only comparison.
- **`docs/notes/2026-11-15-audio-and-enclosure-corrections.md`** records that the
  announcement fan-out and the headphone tap are unverified; nothing in this note
  changes that.

## 7. Verification, unknowns and blocked

Verification performed (read-only, no installs, no device):

```
curl -sS https://packages.debian.org/trixie/pipewire ...            # versions, per-suite
curl -sS https://archive.raspbian.org/raspbian/dists/trixie/main/binary-armhf/Packages.xz
ar p <deb> data.tar.xz | tar -xJ -C .                               # extract without dpkg
readelf -A <lib>.so | grep -E 'Tag_CPU_arch:|Tag_FP_arch|SIMD'
strings <libspa-audioconvert.so> | grep neon
```

Artifacts lived in `/tmp/opencode/armv6audio/` and are not preserved (`/tmp` is not
storage). SHA-256 prefixes above are for re-fetch verification.

Unknowns / blocked:

- **`raspberrypi.com` returned HTTP 403** for both the OS-download and documentation
  pages in this session, the same block recorded in `docs/evidence.md`. The
  "32-bit image, all models" statement is therefore taken from a Raspberry Pi
  maintainer's comment in the official feedback repository [19], not from the
  product page.
- **No ARMv6 runtime of any kind**: no Pi Zero W was contacted, so no SIGILL, no
  startup time, no RSS, no underrun and no duck behaviour was observed on target.
- **Whether the Raspbian build disables NEON at compile time or relies purely on
  runtime dispatch** was not established; the `.so` contains NEON code either way,
  and `have_neon = false` was only ever a user workaround in issue 235.
- **Whether a Zero W sustains the graph at all** (one core, 48 kHz, 1024 quantum,
  wake-word model alongside) is unmeasured; boot time on Trixie Lite is separately
  reported as over two minutes before a later optimisation [19], which does not
  predict audio behaviour.
- **Trixie Lite's default sound-server presence** is `U`; Bookworm Lite's absence is
  documented [29].

## Handoff

### Findings

| Claim | Label | Source | Limits |
| --- | --- | --- | --- |
| Debian 13 ships PipeWire 1.4.2-1 / WirePlumber 0.5.8-2; Debian 12 ships 0.3.65-3+deb12u1 / 0.4.13-1 | D | https://packages.debian.org/trixie/pipewire ; https://packages.debian.org/bookworm/wireplumber | Versions only, no ARMv6 claim |
| Debian armhf requires ARMv7 + Thumb-2 + VFPv3-D16 | D | https://wiki.debian.org/ArmHardFloatPort | Port baseline |
| Debian armhf audio libraries are tagged v7/VFPv3-D16; audioconvert also NEON | O | debs under http://ftp.at.debian.org/debian/pool/main/p/pipewire/ , readelf -A | Artifact inspection, not execution |
| Pi OS 32-bit is a separate Raspbian ARMv6 rebuild: same versions, v6/VFPv2 libraries | O | https://archive.raspbian.org/raspbian/dists/trixie/Release | Only inspected packages |
| Upstream PipeWire states no supported architecture | D | https://gitlab.freedesktop.org/pipewire/pipewire/-/blob/1.4.2/README.md | Absence, not denial |
| NEON is selected at runtime from /proc/cpuinfo | D | https://gitlab.freedesktop.org/pipewire/pipewire/-/blob/1.4.2/spa/plugins/support/cpu-arm.c | Audioconvert/cpu path only |
| A 2020 NEON default broke the armv6l build | D | https://gitlab.freedesktop.org/pipewire/pipewire/-/issues/235 | Closed; post-fix state U |
| WirePlumber 32-bit ARM test failures open, incl. "armhf (armv6 with FPU)" | D | https://gitlab.freedesktop.org/pipewire/wireplumber/-/issues/81 | Alpine/musl; runtime impact U |
| BlueZ-path WirePlumber SIGSEGV existed in 2026 | D | https://gitlab.freedesktop.org/pipewire/pipewire/-/issues/5470 | Not ARM-specific, closed |
| Headless boxes should use WirePlumber `main-embedded` | D + R | https://gitlab.freedesktop.org/pipewire/wireplumber/-/blob/0.5.8/src/config/wireplumber.conf ; https://www.sefod.eu/posts/raspberry_bluetooth_audio_routing | Third-party guide plus upstream profile |
| ~17–31 MB per process on an x86_64 desktop; ~8–9 MB allocations per client | O + R | https://www.mail-archive.com/devel@lists.fedoraproject.org/msg174601.html | Not ARMv6, not 512 MB |
| LVA requires min 512 MB and lists only amd64/aarch64 | D | https://github.com/OHF-Voice/linux-voice-assistant | Upstream README |
| ALSA channels are exclusive without dmix; no per-application gain | D | https://www.alsa-project.org/alsa-doc/alsa-lib/pcm_plugins.html | Plugin model, not Debra behaviour |
| Bookworm Lite ships no sound server; BlueZ A2DP needs an endpoint provider | D | https://github.com/raspberrypi/bookworm-feedback/issues/134 ; https://raw.githubusercontent.com/bluez/bluez/master/doc/org.bluez.MediaEndpoint.rst | Trixie Lite U |

### Traps

1. Version string ≠ instruction set: both builds say 1.4.2-1, only Raspbian is `v6`.
2. Debian armhf is the wrong port for a Zero; the ARMv6 route is the Raspbian rebuild.
3. A NEON tag is not proof of a crash, nor is its absence proof of safety.
4. The "session manager" is WirePlumber; the footprint is `pipewire` +
   `wireplumber` + `pipewire-pulse`, not two processes.
5. A headless Pi can stall in WirePlumber's seat logic; `main-embedded` is the
   documented profile.
6. ALSA-only does not mean "no ducking": it means the duck must live in the player.

### Unknowns and blocked

- No runtime evidence of any kind: no SIGILL, RSS, startup time, underrun or duck
  result on ARMv6. `T` is empty in this note.
- `raspberrypi.com` returned HTTP 403; board facts came from repository notes and a
  maintainer comment.
- U: Trixie Lite sound-server presence; whether Raspbian disables NEON at build
  time; whether the open WirePlumber test failures touch runtime; whether `armel`
  is a practical base; whether the ReSpeaker/HAT ALSA path adds its own problems.

### One next bounded check

On the spare Pi Zero W with 32-bit Raspberry Pi OS Trixie Lite, no installs and no
audio output connected: `systemctl --user status pipewire wireplumber`,
`ps -o rss=,comm= -C pipewire,wireplumber,pipewire-pulse`, then
`timeout 20 pw-cli info 0`. Record exit codes, RSS in kB, and whether
`main-embedded` was needed. That converts the two largest unknowns (does it start,
what does it cost) into `T`/failed without playing a sound. Coordinator approval
and device ownership are prerequisites; nothing here authorizes touching the board.

## Source register

1. https://packages.debian.org/trixie/pipewire — `pipewire (1.4.2-1)`
2. https://packages.debian.org/trixie/wireplumber — `wireplumber (0.5.8-2)`, "modular session / policy manager for PipeWire"
3. https://packages.debian.org/bookworm/pipewire — `pipewire (0.3.65-3+deb12u1)`
4. https://packages.debian.org/bookworm/wireplumber — `wireplumber (0.4.13-1)`
5. https://wiki.debian.org/ArmHardFloatPort — "the Debian armhf port requires at least an Armv7 CPU with Thumb-2 and VFP3D16"
6. https://packages.debian.org/trixie/armhf/libasound2t64 — `libasound2t64 (1.2.14-1+deb13u1)`
7. https://packages.debian.org/bookworm/armhf/libasound2 — `libasound2 (1.2.8-1)`
8. https://packages.debian.org/trixie/armhf/bluez — `bluez (5.82-1.1)`
9. https://packages.debian.org/bookworm/armhf/bluez — `bluez (5.66-1+deb12u2)`
10. https://wiki.debian.org/ArmEabiPort — armel "default port in Debian for ARM architecture versions 4T, 5T, and 6", baseline updated to 5T
11. https://archive.raspbian.org/raspbian/dists/trixie/Release and https://archive.raspbian.org/raspbian/dists/trixie/main/binary-armhf/Packages.xz ; bookworm equivalents under `/dists/bookworm/`
12. https://gitlab.freedesktop.org/pipewire/pipewire/-/issues/235 — "pipewire-0.3.4 fails to build under armv6l/armv7l"
13. https://gitlab.freedesktop.org/pipewire/wireplumber/-/issues/81 — "32-bit ARM test failures", open
14. https://gitlab.freedesktop.org/pipewire/pipewire/-/issues/4315 — armv7/armhf float parsing test failures
15. https://gitlab.freedesktop.org/pipewire/pipewire/-/blob/1.4.2/spa/plugins/support/cpu-arm.c — `arm_init()` reads `/proc/cpuinfo`, sets `SPA_CPU_FLAG_NEON`
16. https://gitlab.freedesktop.org/pipewire/pipewire/-/blob/1.4.2/spa/plugins/audioconvert/fmt-ops.c — `MAKE(..., SPA_CPU_FLAG_NEON)`
17. https://gitlab.freedesktop.org/pipewire/pipewire/-/issues/5470 — wireplumber SIGSEGV in libspa-bluez5 D-Bus call
18. https://github.com/OHF-Voice/linux-voice-assistant — README "Requirements": 1 GHz, min. 512 MB, `linux/amd64` or `linux/aarch64`
19. https://github.com/raspberrypi/trixie-feedback/issues/24 — maintainer, 2026-03-12: 32-bit Raspberry Pi OS boots to desktop on a Pi Zero W; 2026-08-08 report of >2 min boot on Trixie Lite
20. https://www.mail-archive.com/devel@lists.fedoraproject.org/msg174601.html — per-client PipeWire allocations (2021-12-14)
21. https://bbs.archlinux.org/viewtopic.php?id=283410 — `systemctl --user status wireplumber` showing `Memory: 11.6M` (0.4.11)
22. https://docs.pipewire.org/page_man_pipewire_conf_5.html — `default.clock.rate = 48000`, `default.clock.quantum = 1024` (docs currently 1.6.11)
23. https://www.alsa-project.org/alsa-doc/alsa-lib/pcm_plugins.html — `dmix` "provides direct mixing of multiple streams"; hw channels exclusive otherwise
24. Repository: docs/notes/2026-11-15-music-transport-and-control-map.md — sink vs sink-input gain, filter/loopback nodes, sendspin volume modes
25. Repository: docs/research/2026-11-15-armv6-wheels.md — `soundcard` PulseAudio-only, `pulsectl`/`libpulse0`, `linux_armv6l` tag caveat
26. Repository: docs/notes/2026-11-15-parts-inventory.md — Zero W "Single-core ARMv6, 512 MB"
27. https://packages.debian.org/trixie/bluez-alsa-utils — `bluez-alsa-utils (4.3.1-3)`
28. https://raw.githubusercontent.com/bluez/bluez/master/doc/org.bluez.MediaEndpoint.rst — endpoint registered by a server on a unique D-Bus name; https://git.kernel.org/pub/scm/bluetooth/bluez.git/plain/README — `--disable-a2dp` "provided for distributions that do not have any audio capabilities"
29. https://github.com/raspberrypi/bookworm-feedback/issues/134 — maintainer: "neither pipewire nor pulseaudio need to be installed on the Lite image for audio output"
30. Repository: docs/notes/2026-11-15-storage-durability.md — SD wear, zram, undervoltage
31. https://packages.debian.org/trixie/armhf/libspa-0.2-bluetooth — `libspa-0.2-bluetooth (1.4.2-1)`, the BlueZ transport plugin
32. https://www.sefod.eu/posts/raspberry_bluetooth_audio_routing — headless Pi Zero Bluetooth receiver with PipeWire, `main-embedded` profile, 2026-04-10
33. https://gitlab.freedesktop.org/pipewire/wireplumber/-/blob/0.5.8/src/config/wireplumber.conf — `main-embedded = { inherits = [ main, mixin.systemwide-session, mixin.stateless ] }`, "typical profile for embedded use cases"
34. https://bugs.debian.org/cgi-bin/pkgreport.cgi?pkg=pipewire;dist=trixie and https://bugs.debian.org/cgi-bin/pkgreport.cgi?pkg=wireplumber;dist=trixie — fetched; no armhf/armv6 mention in either
35. https://packages.debian.org/trixie/armel/pipewire and https://packages.debian.org/trixie/armel/wireplumber — both `1.4.2-1` / `0.5.8-2`
