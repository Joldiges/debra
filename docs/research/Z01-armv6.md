# Z01 — full original Pi Zero W support: dependency, instruction-set and ABI reconnaissance

**Status:** unreviewed evidence, 2026-11-15. This is the Z01 card's deliverable
([card](../work/cards/Z01.md)); it is not a decision and it authorizes nothing.
Author model: `openrouter/deepseek/deepseek-v4.1-flash-1017` (variant `high`),
assigned by the coordinator. Nothing was installed, downloaded as a wheel, built
or run, and no device was contacted: every runtime, performance and
combined-operation row is **`not-run`**.

**Scope.** Read the Z01 card, the [project brief](../project-brief.md) ARMv6
goal, [legacy findings](../legacy-findings.md) and the three existing notes
([ARMv6 wheels](2026-11-15-armv6-wheels.md), [LVA requirements](2026-11-15-lva-requirements.md),
[Pico and TTS](2026-11-15-pico-and-tts.md)), then inspected public upstream
sources: pinned LVA and SendSpin trees, PyPI and piwheels file listings, GitHub
release assets, Debian autobuilder status and Raspberry Pi documentation
sources. Access date for every URL is **2026-11-15** (some Debian autobuilder
pages render their footer in UTC 2026-11-16).

## 1. Dependency / instruction-set / ABI matrix

Route abbreviations: **wheel** = binary wheel install; **sdist** = source build
at install time; **apt** = distro package; **src** = git checkout. "armv6l"
means the platform tag `linux_armv6l`, which is an ABI label, not proof of ARMv6
code — see the traps in [the ARMv6 wheel note](2026-11-15-armv6-wheels.md).

| Component (version inspected) | Route | ARMv6 / armhf artifact | ARMv7 | AArch64 | ISA / ABI facts behind the answer |
| --- | --- | --- | --- | --- | --- |
| **Linux Voice Assistant v1.1.18** ([tag](https://github.com/OHF-Voice/linux-voice-assistant/tree/v1.1.18), [pyproject](https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/v1.1.18/pyproject.toml), [README](https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/v1.1.18/README.md)) | src (`script/setup` venv) or Docker | **No wheel, no container image.** Source only | source only | `linux/arm64` image; README states "linux/amd64 and linux/aarch64" | `upstream-documented`: pure-Python app; all native weight is in dependencies. The documented install route (Docker) has no armhf image, so only the bare-metal venv path exists. README requires CPU 1 GHz, RAM "min. 512MB", OS "linux/amd64 or linux/aarch64". |
| **pymicro-wakeword 2.5.0** (microWakeWord binding) ([PyPI](https://pypi.org/pypi/pymicro-wakeword/2.5.0/json)) | wheel (ctypes binding, no build step) | piwheels serves `pymicro_wakeword-2.5.0-py3-none-linux_armv6l.whl`, which **bundles an x86-64 `libtensorflowlite_c.so`** (prior note, `observed`) | `pymicro_wakeword-2.5.0-py3-none-manylinux_2_35_armv7l.whl` (ARMv7 / VFPv4 per prior note) | `…manylinux_2_35_aarch64.whl` | No ARMv6 wheel is published by PyPI at all; on a Zero W pip's compatible tags exclude `manylinux_2_35_armv7l`, so it falls to the sdist, which carries the same x86-64 `.so` (**`hypothesis`** on the exact resolver behaviour, from PEP 425/600 tag semantics). |
| **libtensorflowlite_c** (upstream prebuilt source: [tphakala/tflite_c v2.17.1](https://github.com/tphakala/tflite_c/releases/tag/v2.17.1)) | release tarball or self-build | **No armhf/armv6 asset.** Assets are `linux_amd64`, `linux_arm64`, `darwin_arm64`, `windows_amd64` | none | `linux_arm64` | This is the actual native inference runtime both engines dlopen. `upstream-documented` asset list; ARMv6 requires a self-built `libtensorflowlite_c.so` (Bazel or the TFLite C Makefile) — feasibility **`unknown`**. |
| **pymicro-features 2.0.2** (front-end) | wheel | `pymicro_features-2.0.2-cp39-abi3-linux_armv6l.whl`, ARMv6 / VFPv2 (prior note, `observed`) | yes | yes | abi3 C++ extension: one wheel per platform, so the `armv6l` tag is meaningful here. |
| **pyopen-wakeword 1.1.0** ([PyPI](https://pypi.org/pypi/pyopen-wakeword/1.1.0/json)) | wheel (ctypes, no build step) | none on PyPI; piwheels armv6l wheel bundles the same x86-64 `.so` | **none** | `…manylinux_2_35_aarch64.whl` | Same TFLite problem, worse: PyPI publishes no 32-bit ARM wheel for this package at all. |
| **sendspin 9.1.0** (CLI the lab runs) ([PyPI](https://pypi.org/pypi/sendspin/9.1.0/json), [tag](https://github.com/Sendspin/sendspin-python-cli/tree/9.1.0)) | sdist on 32-bit ARM; wheel elsewhere | **No armhf/armv7 wheel.** sdist builds `sendspin/_volume.c` as an **optional** extension with a numpy fallback | none | `…manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl` | `upstream-documented` in [`setup.py`](https://raw.githubusercontent.com/Sendspin/sendspin-python-cli/9.1.0/setup.py) (`OptionalBuildExt`) and [`.github/workflows/release.yml`](https://raw.githubusercontent.com/Sendspin/sendspin-python-cli/9.1.0/.github/workflows/release.yml) (cibuildwheel matrix = x86_64, aarch64 via QEMU, macOS, Windows; `SENDSPIN_REQUIRE_C_EXT=1` in CI). A source install *can* succeed without the extension; unproven. Requires Python ≥ 3.12. |
| **aiosendspin 10.2.2** | wheel | `py3-none-any` (prior note, `observed`) | same | same | Pure Python. |
| **av (PyAV) 16.1.0** | wheel | `av-16.1.0-…cp311-abi3-linux_armv6l` (prior note); **19.0.2 has no armv6l files**, and `av>=15.0.0` resolves to it | — | yes | Wheel links FFmpeg 7.1 sonames (`libavcodec.so.61` …), matching Debian trixie's `7:7.1.5`; unpinned resolution forces a Cython source build. |
| **numpy 2.2.1 / 2.5.4** | wheel | armv6l wheel exists, but 2.3.0+ contain `Tag_CPU_arch: v8` objects; **2.2.1 is the newest clean one** (prior note, `observed`) | yes | yes | Needed by LVA (`>=2,<3`) and by `aiosendspin[server]` (`>=2.1`). |
| **webrtc-noise-gain 1.3.0** | wheel | armv6l wheel present, but `Tag_FP_arch: VFPv3` on a v6 object (prior note, `observed`) | — | yes | VFPv3 instructions on ARM1176 (VFPv2) fault; whether gcc emits any is **`unknown`**. |
| **soundcard 0.4.6 → libpulse** | wheel + apt | pure Python; needs unversioned `libpulse.so` (i.e. `libpulse-dev`) | — | — | LVA's capture path is PulseAudio, not PortAudio (see the LVA note, §trap 1 — I agree). With PipeWire this means `pipewire-pulse` must provide the socket. |
| **sounddevice 0.5.6 → libportaudio2** | wheel + apt | pure Python + cffi; Debian trixie builds `libportaudio2` for armhf | — | — | SendSpin's output path. |
| **python-mpv 1.0.8 → libmpv2** | wheel + apt | pure ctypes; Debian trixie `mpv 0.40.0-3+deb13u1` is built for armhf ([buildd](https://buildd.debian.org/status/package.php?p=mpv&suite=trixie)) | — | — | LVA decodes TTS/announcement audio locally through mpv; nothing is offloaded here. |
| **PipeWire / WirePlumber** | apt | Debian trixie `pipewire 1.4.2-1` built for armhf ([buildd](https://buildd.debian.org/status/package.php?p=pipewire&suite=trixie)); the Pi OS armhf archive was not inspected | — | — | **ABI caveat:** Debian's `armhf` port "supports … 32-bit devices using **version 7** of the ARM architecture specification" ([debian.org/ports/arm](https://www.debian.org/ports/arm/)). Pi OS's own armhf build is the ARMv6 rebuild — an inference from Pi OS supporting the original Pi/Zero, not a package-level inspection. |
| **CPython 3.13.5** | apt | `python3.13 3.13.5-2+deb13u5`, armhf built ([buildd](https://buildd.debian.org/status/package.php?p=python3.13&suite=trixie)) | — | — | LVA ≥ 3.11, sendspin ≥ 3.12; both satisfied. |
| **OS / kernel** | image | `2026-10-06-raspios-trixie-armhf-lite.img.xz` ([downloads](https://downloads.raspberrypi.com/raspios_lite_armhf/images/raspios_lite_armhf-2026-10-06/)); kernel 6.18.60 at `stable_20261103` ([Makefile](https://raw.githubusercontent.com/raspberrypi/linux/stable_20261103/Makefile)) | — | separate arm64 image | `upstream-documented`: "The **32-bit** version is designed for older Raspberry Pi models that have 32-bit processors, like the original Raspberry Pi, Raspberry Pi 2, and Raspberry Pi Zero" ([rpi-os-introduction.adoc](https://raw.githubusercontent.com/raspberrypi/documentation/master/documentation/asciidoc/computers/os/rpi-os-introduction.adoc), mutable master). So the OS tier is documented, not merely assumed — but Debra has not verified image contents. |

**Agreement with the earlier notes.** The ARMv6 wheel note's core findings hold
(x86-64 TFLite inside `armv6l` wheels; numpy ARMv8 objects; `av`/`zeroconf`/`numpy`
pin ceilings), as does the LVA note's architecture and dependency analysis. Two
additions, not corrections: (a) `sendspin` itself — not just its dependencies —
publishes no 32-bit ARM wheel, which the earlier note did not cover because it
inspected `pyproject.toml` rather than the wheel set; (b) the note says
"`microwakeword.py` accepts `libtensorflowlite_c_path`", which is true of the
library, but LVA v1.1.18 never passes it — [`models.py`](https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/v1.1.18/linux_voice_assistant/models.py)
calls `MicroWakeWord.from_config(config_path=…)` and
`OpenWakeWord.from_model(model_path=…)`, so the default lookup picks the bundled
`.so` in the package. The repair is therefore a file replacement inside
site-packages or an LVA patch, not a configuration option.

## 2. Ranked blockers

**A. Artifact absent (blocks the feature outright)**

1. **No ARMv6 TensorFlow Lite C runtime for either wake engine.** Both libraries
   dlopen a bundled `libtensorflowlite_c.so`; every published artifact for 32-bit
   ARM is x86-64, and the only upstream prebuilt provider ships no 32-bit ARM at
   all. This removes LVA's core feature (local wake detection) on the target
   board. `not-run`; the failure mode (wrong ELF class at `ctypes.CDLL`) is
   **`hypothesis`**.
2. **No armhf LVA container image**, so upstream's recommended install route is
   unavailable and Debra must own a bare-metal venv path. A workaround exists; it
   is work, not a blocker of principle.
3. **No `sendspin` wheel for any 32-bit ARM.** sdist plus an optional C
   extension, so probably installable; unproven.
4. **No 32-bit ARM asset in `tphakala/tflite_c`**, so "just use the prebuilt
   library" is closed even for ARMv7.

**B. Artifact present but unproven on ARMv6**

5. `numpy` ≥ 2.3 ARMv8 objects; `webrtc-noise-gain` VFPv3 attribute (both
   `observed`, neither run).
6. **Debian-vs-Pi-OS package provenance**: Debian armhf is an ARMv7 baseline;
   whether every Pi OS armhf package the stack needs is rebuilt for ARMv6 was not
   inspected. This is the quietest risk in the matrix.
7. `av==16.1.0` wheel vs trixie FFmpeg sonames; `sendspin._volume`
   build-or-fallback; `zeroconf` cp313 wheel gap.
8. PipeWire vs PulseAudio on a 512 MB board, and whether `pipewire-pulse`'s
   `libpulse` compatibility satisfies `soundcard`'s `dlopen("libpulse.so")`.

**C. Works but too slow / RAM-tight** (all `not-run`; a Pi 5 proves none of this)

9. **Memory**: LVA's own floor is "min. 512MB" for the *application* — the Zero W
   has 512 MB total, shared with the GPU and the OS. Running LVA + SendSpin +
   PipeWire + mpv inside that is unmeasured.
10. **CPU**: single-core 1 GHz ARM1176 (no NEON) doing MFCC + wake inference +
    PulseAudio + mpv decode. Upstream's "1 Ghz" figure refers to amd64/aarch64
    hardware.
11. **Install-time compiles** on the board (`webrtc-noise-gain`, `av`, possibly
    `numpy`) — upstream already advises `-O1 -g0 -j1` for a Zero 2 W; a Zero W is
    far slower. Cross-build is likely mandatory, which is a build-system
    requirement, not a runtime verdict.
12. **Combined operation**: wake → STT → reply → TTS while music plays, with
    duck/pause, on one sound device. Untested by anyone here.

## 3. Offload options that keep the full-support goal

| Option | What moves off the Zero W | What it would prove | What it would not prove |
| --- | --- | --- | --- |
| **O1. Build offload** — cross/QEMU `arm1176` builder produces `libtensorflowlite_c.so` and the wheel set; runtime stays on the board | Build CPU time only | That ARMv6 artifacts can be produced reproducibly and that they load (via `qemu-arm -cpu arm1176`) | Performance, RAM, or audio behaviour. QEMU timing is not a measurement. |
| **O2. Wake detection hosted by Home Assistant**, LVA in output-only mode | The wake inference | Nothing yet — this needs an HA-side capability for a non-ESPHome satellite that does not exist in LVA v1.1.18. `ENABLE_OUTPUT_ONLY` is documented only as "output-only mode" ([install_application.md](https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/v1.1.18/docs/install_application.md)); what it stops doing is **`unknown`**. | Full support: an unverified mode is not a substitute. |
| **O3. Separate wake box** (Pi 3 / Zero 2 W / ESP32 running microWakeWord) triggering the Zero W | Wake inference, plus a new component and a new protocol hop | That a Zero W can be a voice *output* target | Full support — it redefines the architecture, so it must be labelled as such, not sold as Zero W support. |
| **O4. TTS offload** | *Nothing.* TTS synthesis already happens in Home Assistant; the device only fetches a URL and decodes it with mpv. | — | Useful negative result: "run TTS elsewhere" is not an available saving on this tier. |

"Zero W as music-only" is **not** proposed as a resolution. If O1 fails, the
honest statement is that full support on ARMv6 is blocked on an upstream-absent
artifact, and the board stays a research target rather than being silently
demoted.

## 4. Bounded experiments that would settle the open rows

None of these were run. Each is designed to be reversible and to avoid a live
household service.

- **E0 — image truth (cheapest; answers 6 and the `pip.conf` unknown).** Boot one
  freshly flashed `2026-10-06-raspios-trixie-armhf-lite` card, no network
  services, no HA pairing. Record `uname -r`, `dpkg -l | wc -l`,
  `dpkg -l pipewire wireplumber libmpv2 libportaudio2 libpulse-dev`,
  `cat /etc/pip.conf`, `python3 -VV`, `readelf -A /usr/bin/python3.13 | head`.
  Expected evidence: a dated transcript proving which archive built the userland
  and whether piwheels is preconfigured.
- **E1 — wheel/ELF audit, no ARM hardware.** `pip download --only-binary=:all:
  --platform linux_armv6l --python-version 3.13 --implementation cp --abi cp313
  --extra-index-url https://www.piwheels.org/simple <pkg>` into a scratch dir,
  then `unzip -l` and `readelf -A`/`-h` on every `.so`. Repeat with
  `--platform manylinux_2_35_armv7l`. Expected evidence: per-artifact
  `Tag_CPU_arch`/`Tag_FP_arch`, and which packages fall through to sdist.
- **E2 — resolver report, no install.** `pip install --dry-run --report
  /tmp/report.json --only-binary=:all: --platform linux_armv6l
  --python-version 3.13 -r requirements-pinned.txt`. Expected evidence: the JSON
  `download_info` list showing exactly where a source build would be required.
- **E3 — import probe under emulation.** Read-only chroot of the extracted image
  plus `qemu-arm-static`: `qemu-arm-static -cpu arm1176 -L /mnt/raspios
  /mnt/raspios/usr/bin/python3 -c "import numpy, webrtc_noise_gain;
  print(numpy.__version__)"`. Expected evidence: exit 0, or
  `SIGILL`/`Illegal instruction` naming the package. Caveat to record with the
  result: QEMU's CPU model is an approximation and says nothing about speed.
- **E4 — TFLite C build for ARMv6.** In a `linux/arm/v6` buildx container (or on a
  spare Zero with swap, offline): build `libtensorflowlite_c.so`, then
  `readelf -A` and a `ctypes.CDLL(...)` load under E3's emulator. Expected
  evidence: v6/VFPv2 attributes plus a successful `TfLiteModelCreateFromFile` on
  a bundled `.tflite`.
- **E5 — wake detection on real hardware.** On a Zero W, a fixed 10 s 16 kHz mono
  WAV: `time python -m pymicro_wakeword --model okay_nabu sample.wav`, with
  `/usr/bin/time -v` for peak RSS. Expected evidence: detection result,
  wall-clock, realtime factor, peak RSS. This is the first row that can become
  `tested`.
- **E6 — combined operation, last.** Only after E5: PipeWire + `sendspin daemon`
  + LVA on the same user, 30 minutes of music with three wake-word interruptions,
  logging RSS/CPU/underruns. Expected evidence: a pass/fail against thresholds
  agreed *before* the run.

## 5. What could not be established from public sources

- **`raspberrypi.com` documentation and `packages.debian.org` were blocked** in
  this session (HTTP 403 and an anti-bot interstitial respectively). The
  `raspberrypi/documentation` Git sources and Debian autobuilder status were used
  instead; per-package file lists (e.g. `libpulse0` vs `libpulse-dev`) come from
  the earlier note, not re-verified here.
- **Which archive built the Pi OS armhf packages**, and therefore whether every
  needed package is ARMv6-safe rather than ARMv7-baseline.
- **Whether the image preconfigures piwheels**, and what Python/`pip` defaults it
  ships.
- **What `--output-only` actually disables** in LVA — no documentation beyond the
  flag name.
- **Whether TFLite C (or TFLite Micro) can be built and run on ARM1176**, and
  whether microWakeWord's kernels are all portable there. TFLite Micro is not
  obviously a substitute: the bindings call the full `TfLiteModel*` /
  `TfLiteInterpreter*` C API, not TFLite Micro's API.
- **Any measured ARMv6 performance or memory figure** for LVA, SendSpin, mpv or
  PipeWire — none exists in the sources reached, and none was produced here.
- **`aiosendspin`/`sendspin` runtime use of newer `av`/`numpy` APIs** beyond
  declared constraints (carried over from the prior note; still `unknown`).
