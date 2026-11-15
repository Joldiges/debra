# What linux-voice-assistant actually requires

**Research result from a pinned source tree, not a device test, 2026-11-15.**
Commit `12e51272d37d786ed3168955b3fb6eda3c7159ce` (2026-11-14), the latest release
being `v1.1.18` — the version the lab Pi runs. Produced by the unattended runner
as task `VOICE01`.

Read this before planning an install: two of the assumptions an installer
naturally makes are wrong, and one of them is Debra's own.

## The requirements

| Requirement | Value | Status |
| --- | --- | --- |
| Python | ≥ 3.11; 3.11–3.13 declared, "tested with 3.11 and 3.13" | documented |
| Container base | `python:3.13-slim-trixie` | documented |
| Packaging | pip + venv only; **no uv, no poetry, no lockfile** | code |
| Audio capture | `soundcard`, which binds libpulse — **not PortAudio** | code |
| Audio playback | `libmpv` (`libmpv-dev` to build, `libmpv2` to run) | documented |
| Sound server | PulseAudio **or** PipeWire; linger required when headless | documented |
| Dependencies | 12, with only `aioesphomeapi==45.3.1` and `websockets==12` hard-pinned | documented |
| Wake words | microWakeWord (9 models + `stop`) and openWakeWord (5 models) bundled | documented |
| Service | Docker Compose (recommended) or systemd running `docker-entrypoint.sh` | documented |
| Home Assistant | ESPHome integration on port 6053, mDNS `_esphomelib._tcp`, API 1.10 | code |
| Zero 2 W | supported, and recommended with the Satellite1 HAT; needs `-O1 -g0` and `-j1` build flags | documented |

## The traps

1. **The PortAudio premise is wrong.** Nothing in the tree imports PortAudio or
   PyAudio. Installing `libportaudio2` buys nothing; `soundcard` goes through
   libpulse. Any setup guide that installs PortAudio for LVA is copying a
   different project.
2. **No lockfile.** `pymicro-wakeword>=2,<3`, `soundcard<1`, `zeroconf<1` and an
   unbounded `types-protobuf` mean a rebuild months later can differ from the
   image that was tested. Debra's pinned-component rule needs a hash-pinned
   requirements file generated from a resolved tree, not this.
3. **`network_mode: "host"` is mandatory** on the compose path: discovery and the
   ESPHome server both use the host interface, and `--mac-address` identity only
   works on one NIC.
4. **The audio socket, not the sound card, is the permission.** Container and
   PipeWire must run as the same UID, plus `group_add: [audio]` and
   `cap_add: [SYS_NICE]`. Headless, without linger, it dies silently after the
   SSH session ends.
5. **Bookworm is the floor.** The wake-word wheels are `manylinux_2_35`, so
   Bullseye's glibc 2.31 cannot use them.
6. **The Home Assistant side is not just "add the integration".** TTS is fetched
   from an HA URL and decoded by mpv, so the device needs HTTP reachability to HA
   and working FFmpeg codecs. This is the most likely silent failure.
7. **`script/setup` deletes `.venv` unconditionally.** Never point it at a venv
   worth keeping.
8. **No device is explicitly declared unsupported** at this commit. 32-bit/armhf
   is simply not built — amd64 and aarch64 only — which is a gap, not a refusal.
   The Zero 2 W is aarch64 and therefore fine; the original Zero W is not.
9. **The ESPHome API is unencrypted and unauthenticated** (empty
   `AuthenticationResponse`). That is upstream's design for the LAN, and worth
   knowing before anyone exposes port 6053.

## What it means for Debra

- **Pi Zero W (ARMv6, 32-bit) cannot run LVA as shipped**, not because of a
  documented limitation but because only amd64 and aarch64 wheels exist. That is
  a packaging problem to solve, and it lines up with the ARMv6 finding that the
  wake-word wheels carry x86-64 TensorFlow Lite binaries anyway — see
  [the ARMv6 note](2026-11-15-armv6-wheels.md). Pi Zero W support is a Debra
  requirement, so this is the real obstacle, not the CPU speed.
- The lab Pi 5 install matches upstream's supported path: systemd running
  `docker-entrypoint.sh`, PipeWire, `v1.1.18`.
- A reproducible Debra build needs a resolved, hash-pinned requirements file
  generated from this commit, plus the libmpv and codec packages named
  explicitly.

## Not established

- The minimum Home Assistant version. Nothing in the repository states it; the
  `minimum_esphome_version: 2024.7.0` in the manifests is about ESPHome
  firmware, not HA.
- Which codec HA actually serves for TTS.
- Whether every transitive dependency resolves to a wheel on aarch64 with no
  sdist fallback. **Next bounded check:** in a scratch venv, or with
  `pip download --platform manylinux_2_35_aarch64 --only-binary :all:
  --python-version 3.11`, resolve `pyproject.toml` at `12e5127` and confirm no
  source build is needed. That turns the largest remaining hypothesis into
  evidence and costs one command.
- The full source register (S1–S33) is in the runner's report under
  `.local/runner/runs/`; this note keeps the claims, not the quotations.
