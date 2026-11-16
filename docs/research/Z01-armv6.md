# Z01 — full original Pi Zero W support: dependency, instruction-set and ABI reconnaissance

**Status:** unreviewed evidence, 2026-11-15. This is the Z01 card's deliverable
([card](../work/cards/Z01.md)); it is not a decision and it authorizes nothing.
Author model: `openrouter/deepseek/deepseek-v4.1-flash-1017` (variant `high`),
assigned by the coordinator. Nothing was installed, downloaded as a wheel, built
or run, and no device was contacted: every runtime, performance and
combined-operation row is **`not-run`**.

Reviewed four times by `openrouter/openai/gpt-6.1-sol#flex-high`, 2026-11-15:
**changes required** each time. docs-r1 raised seven findings against this
document: the leading blocker generalized a broken piwheels artifact to all
32-bit ARM, the experiments could not produce their promised evidence, and the
historical build leads had no disposition. The repairs below **address** those
seven findings and are pending re-review. docs-r2, which re-read them, closed the
High finding and three others (the quick-rollback finding was the acceptance
document's), and rejected the repairs to E1, E3 and E0 plus the wording of the
historical section. docs-r3 closed the E0 repair, the failed-performance-run wording
and the browser recovery/report additions, and rejected E1 and E3 again, the
binary's provenance claim, and two narrower source descriptions; it left the
browser contrast criterion open, which the acceptance document's own record
settles. docs-r4 closed five of its eight findings and rejected the repaired E3
command, E1's notion of a target environment, and this header's claim that r3 had
closed the browser work. This revision addresses those three. Review records:
`.local/reviews/docs-r1-20261115/verdict.md`, `docs-r2-20261115/verdict.md`,
`docs-r3-20261115/verdict.md` and `docs-r4-20261115/verdict.md` (not in Git). The
repairs are the coordinator's, so nothing here is reviewed evidence yet.

The reader should also know that the repair round added one piece of first-hand
evidence: an ARMv6 TensorFlow Lite binary retained in this repository's Git
history was extracted and inspected with `readelf` (section 3). This inspection
did not execute it; whether it was ever run before is not recorded, and no device
was contacted.

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
| **pymicro-wakeword 2.5.0** (microWakeWord binding) ([PyPI](https://pypi.org/pypi/pymicro-wakeword/2.5.0/json)) | wheel (ctypes binding, no build step) | piwheels serves `pymicro_wakeword-2.5.0-py3-none-linux_armv6l.whl`, which **bundles an x86-64 `libtensorflowlite_c.so`** (prior note, `observed`) | `…manylinux_2_35_armv7l.whl`, which packages the project's **own** TensorFlow Lite C v2.17.1 built for ARMv7-A + NEON/VFPv4 ([`lib/linux_armv7l/SOURCE`](https://raw.githubusercontent.com/OHF-Voice/pymicro-wakeword/v2.5.0/lib/linux_armv7l/SOURCE), [publish workflow](https://raw.githubusercontent.com/OHF-Voice/pymicro-wakeword/v2.5.0/.github/workflows/publish.yml)) — an ARMv7 artifact, unusable on ARM1176 | `…manylinux_2_35_aarch64.whl` | No ARMv6 wheel is published by PyPI at all; on a Zero W pip's compatible tags exclude `manylinux_2_35_armv7l`, so it falls to the sdist, which carries the same x86-64 `.so` (**`hypothesis`** on the exact resolver behaviour, from PEP 425/600 tag semantics). The ARMv7 build shows the project can supply its own TFLite library; it says nothing about ARMv6. |
| **libtensorflowlite_c** (upstream prebuilt source: [tphakala/tflite_c v2.17.1](https://github.com/tphakala/tflite_c/releases/tag/v2.17.1)) | release tarball or self-build | **No armhf/armv6 asset.** Assets are `linux_amd64`, `linux_arm64`, `darwin_arm64`, `windows_amd64` | none | `linux_arm64` | This is the actual native inference runtime both engines dlopen. `upstream-documented` asset list; ARMv6 requires a self-built `libtensorflowlite_c.so` (Bazel or the TFLite C Makefile) — feasibility **`unknown`**. |
| **pymicro-features 2.0.2** (front-end) | wheel | `pymicro_features-2.0.2-cp39-abi3-linux_armv6l.whl`, ARMv6 / VFPv2 (prior note, `observed`) | yes | yes | abi3 C++ extension: one wheel per platform, so the `armv6l` tag is meaningful here. |
| **pyopen-wakeword 1.1.0** ([PyPI](https://pypi.org/pypi/pyopen-wakeword/1.1.0/json)) | wheel (ctypes, no build step) | none on PyPI; piwheels armv6l wheel bundles the same x86-64 `.so` | **none** | `…manylinux_2_35_aarch64.whl` | Same TFLite problem, worse: PyPI publishes no 32-bit ARM wheel for this package at all. |
| **sendspin 9.1.0** (CLI the lab runs) ([PyPI](https://pypi.org/pypi/sendspin/9.1.0/json), [tag](https://github.com/Sendspin/sendspin-python-cli/tree/9.1.0)) | sdist on 32-bit ARM; wheel elsewhere | **No armhf/armv7 wheel.** sdist builds `sendspin/_volume.c` as an **optional** extension with a numpy fallback | none | `…manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl` | `upstream-documented` in [`setup.py`](https://raw.githubusercontent.com/Sendspin/sendspin-python-cli/9.1.0/setup.py) (`OptionalBuildExt`) and [`.github/workflows/release.yml`](https://raw.githubusercontent.com/Sendspin/sendspin-python-cli/9.1.0/.github/workflows/release.yml) (cibuildwheel matrix = x86_64, aarch64 via QEMU, macOS, Windows; `SENDSPIN_REQUIRE_C_EXT=1` in CI). A source install *can* succeed without the extension; unproven. Requires Python ≥ 3.12. |
| **aiosendspin 10.2.2** | wheel | `py3-none-any` (prior note, `observed`) | same | same | Pure Python. |
| **av (PyAV) 16.1.0** | wheel | `av-16.1.0-…cp311-abi3-linux_armv6l` (prior note); **19.0.2 has no armv6l files**, and `av>=15.0.0` resolves to it | — | yes | Wheel links FFmpeg 7.1 sonames (`libavcodec.so.61` …), matching Debian trixie's `7:7.1.5`; unpinned resolution forces a Cython source build. |
| **numpy 2.2.1 / 2.5.4** | wheel | armv6l wheel exists, but 2.3.0+ contain `Tag_CPU_arch: v8` objects; **2.2.1 is the newest of the versions the earlier note inspected with no v8 object** (prior note, `observed`; it lists the nine versions it checked) | yes | yes | Needed by LVA (`>=2,<3`) and by `aiosendspin[server]` (`>=2.1`). The inspected set is a sample, not a proof that no newer clean wheel exists. |
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
   dlopen a bundled `libtensorflowlite_c.so`. Three facts have to be kept apart,
   because an earlier draft of this report ran them together and overstated the
   blocker:

   - the **piwheels `armv6l` wheels and the sdist** of both engines carry an
     x86-64 `libtensorflowlite_c.so` (prior note, `observed`), so the `armv6l`
     tag there is a label on the wrapper, not on the library;
   - a **32-bit ARM build does exist, but for ARMv7**: pymicro-wakeword's
     `manylinux_2_35_armv7l` wheel packages its own TensorFlow Lite C v2.17.1
     built for ARMv7-A with NEON/VFPv4. ARM1176 has neither NEON nor VFPv4, so
     this artifact does not run on the target board;
   - **no ARMv6 build is published by anyone inspected**, and the only prebuilt
     provider reached (`tphakala/tflite_c`) ships no 32-bit ARM at all;
   - the **one ARMv6 binary this project has** is a separately retained artifact
     in its own Git history (`90a4c19:legacy/raspi0/libtensorflowlite_c.so`).
     Its own header and attributes were verified — `Tag_CPU_arch: v6`,
     `Tag_FP_arch: VFPv2` — and it exports the 16 symbols the bindings bind
     (section 3). **Its relationship to the historical build script, and
     therefore to TensorFlow 2.14.0, is unverified**: no build log, hash or
     manifest connects them. It has no recorded provenance, and this inspection
     did not execute it.

   So the blocker is the absence of a **supported, provenance-pinned ARMv6
   artifact**, not of every 32-bit ARM artifact and not of any ARMv6 library ever
   built here. On the target board, an ordinary install removes LVA's core
   feature (local wake detection). Three things are easy to run together and
   must be kept apart, because each fails differently:

   - *package selection:* pip's compatible tags decide which wheel is installed.
     The matrix above says a Zero W excludes `manylinux_2_35_armv7l`, so the
     ARMv7 wheel is **not** what pip installs there; the piwheels `armv6l` wheel
     or the sdist is;
   - *which library is loaded from an installed wheel:* the binding looks in the
     installed module's own `lib` directory **first** (`microwakeword.py`,
     read 2026-11-15), before any platform mapping. The piwheels `armv6l` wheel's
     library is reported as x86-64 by the earlier note, so the predicted failure
     on that route is a wrong-ELF-class error at `ctypes.CDLL` — **`hypothesis`**
     in that note and not a run here;
   - *which library a source checkout loads:* only when the module directory has
     no library does the code fall back to a repository `lib/<platform>` path,
     and `get_platform()` maps **every** 32-bit ARM, `armv6l` included, to
     `linux_armv7l`. A source checkout on a Zero W would therefore pick the
     ARMv7-A + NEON/VFPv4 library. ARM1176 has neither NEON nor VFPv4, so the
     predicted result is a load failure or `SIGILL` — again **`hypothesis`**,
     now about a specific line of code rather than a tag.

   The failure of an ordinary install is what makes the missing artifact a
   blocker; the existence of the historical binary is what makes it an
   engineering gap rather than a dead end.
2. **No armhf LVA container image**, so upstream's recommended install route is
   unavailable and Debra must own a bare-metal venv path. A workaround exists; it
   is work, not a blocker of principle.
3. **No `sendspin` wheel for any 32-bit ARM.** sdist plus an optional C
   extension, so probably installable; unproven.
4. **No 32-bit ARM asset in `tphakala/tflite_c`**, so "just use the prebuilt
   library" is closed for ARMv7 as well — which is why pymicro-wakeword builds and
   ships its own ARMv7 library instead.

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

**C. Unmeasured CPU and RAM risk** (all `not-run`; a Pi 5 proves none of this)

9. **Memory**: LVA's README states a general system requirement of "min. 512MB";
   it does not say that figure is an application-only budget. The Zero W has
   512 MB in total, shared with the GPU and the OS, so running LVA + SendSpin +
   PipeWire + mpv inside it is unmeasured.
10. **CPU**: single-core 1 GHz ARM1176 (no NEON) doing MFCC + wake inference +
    PulseAudio + mpv decode. Upstream's "1 Ghz" figure refers to amd64/aarch64
    hardware.
11. **Install-time compiles** on the board (`webrtc-noise-gain`, `av`, possibly
    `numpy`) — upstream already advises `-O1 -g0 -j1` for a Zero 2 W; a Zero W is
    far slower. Cross-build is likely mandatory, which is a build-system
    requirement, not a runtime verdict.
12. **Combined operation**: wake → STT → reply → TTS while music plays, with
    duck/pause, on one sound device. Untested by anyone here.

## 3. Historical build leads, and what they do not establish

The card asks for the named historical leads to be inspected, not just listed.
Both are recorded in [legacy findings](../legacy-findings.md) and neither is a
verified build.

- **`legacy/tflitebuilder/tfbuild.sh`** (read in history at
  `90a4c19:legacy/tflitebuilder/tfbuild.sh`; the file is not in the working tree)
  tries TensorFlow Lite C **v2.14.0** with ARMv6/VFP hard-float flags and XNNPACK
  disabled, and prints a suggested installation destination inside a Python-3.13
  site-packages directory (it does not install there itself).
  What it actually does, verified from the script: it installs current
  distribution `cmake`/`build-essential` with no version pins, shallow-clones the
  **branch/tag name** `v2.14.0` (not a commit hash), configures
  `../tensorflow/lite/c` with CMake using `-march=armv6 -mfpu=vfp
  -mfloat-abi=hard` and `-DTFLITE_ENABLE_XNNPACK=OFF`, builds with `make`, copies
  the first `libtensorflowlite_c.so` that `find` returns and strips it. Reusable
  information: the CMake + `make` route, the exact ARMv6 flags, and XNNPACK as
  the part that was switched off. Not reusable as a reproducible build: a tag is
  not a hash, the toolchain is whatever the distribution had that day, and
  "first match from `find`" is not a verified output. The historical concern
  about an older library against the currently bundled 2.17.1 is narrower than it
  looked; see the binary check below.
- **`legacy/wheelbuilder/Dockerfile`** bootstraps a Raspbian trixie armhf rootfs
  under QEMU `arm1176` and carries native/Rust build tools. Reusable information:
  an emulated armhf rootfs is a plausible build environment for ARMv6 wheels.
  Must not be inherited: the foreign bootstrap runs with `--no-check-gpg`.
  Package-signature verification has to be restored before any artifact from this
  route is trusted, and the rootfs has to be pinned by digest rather than by
  distribution name.

### A separately retained historical binary, inspected

This repository also contains an ARMv6 TensorFlow Lite binary, in history at
`90a4c19:legacy/raspi0/libtensorflowlite_c.so` (3,029,304 bytes as `ls -l`
reported it, stripped, BuildID `552c58ae…`). I extracted it to a scratch
directory and read it with `readelf` on 2026-11-15. I did not execute it, and I
found no build log, hash or manifest that ties it to the script above or to any
TensorFlow release: **its build lineage and version are unverified**, and whether
it was ever loaded or run before this inspection is not known.

| Check | Result | What it establishes |
| --- | --- | --- |
| `readelf -h` | `ELF32`, `Machine: ARM`, `EABI5`, `DYN` | a 32-bit ARM shared object, not x86-64 |
| `readelf -A` | `Tag_CPU_arch: v6`, `Tag_FP_arch: VFPv2`, `Tag_CPU_unaligned_access: v6` | declared ARMv6 / VFPv2 attributes, i.e. the profile ARM1176 needs |
| `readelf --dyn-syms` | all **16** symbols the pinned bindings bind in `wakeword.py` are exported (versioned `@@VERS_1.0`), including `TfLiteModelCreateFromFile`, `TfLiteInterpreterCreate`, `TfLiteInterpreterInvoke`, `TfLiteTensorCopyFromBuffer` and the tensor-introspection calls `TfLiteTensorByteSize`/`TfLiteTensorQuantizationParams` | the C API surface the bindings call is **present** in this binary |
| `readelf -d` | needs `libstdc++.so.6`, `libm.so.6`, `libgcc_s.so.1`, `libc.so.6`, `ld-linux-armhf.so.3` | it is hard-float (`armhf`); it cannot load in an ARMv6 `armel` userspace |

So the question "is there an ARMv6 binary whose symbol set satisfies the
bindings" has a concrete answer: at the symbol level, yes. That is not the same
as "it works", and it says nothing about which TensorFlow version produced it. A
stripped binary with no recorded provenance can be present and still be the wrong
thing to ship: a symbol can resolve while behaviour, tensor layout or operator
support differ between releases. What the check removes is the assumption that an
ARMv6 build is impossible here; what it cannot remove is the need to build one
with provenance and test it.

None of this is evidence that ARMv6 voice works. E4 below is the experiment that
would build a provenance-pinned library and load it, and it no longer has to
guess whether the API surface exists at all.

## 4. Offload options that keep the full-support goal

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

## 5. Bounded experiments that would settle the open rows

None of these were run. Each is designed to be reversible and to avoid a live
household service.

- **E0 — initial image inventory.** Boot one freshly flashed
  `2026-10-06-raspios-trixie-armhf-lite` card, no network services, no HA
  pairing. Record `uname -r`, `dpkg -l | wc -l`,
  `dpkg -l pipewire wireplumber libmpv2 libportaudio2 libpulse-dev`,
  `cat /etc/pip.conf`, `python3 -VV`, `readelf -A /usr/bin/python3.13 | head`.
  Expected evidence: a dated transcript of what the image ships and whether
  piwheels is preconfigured. **This does not establish which archive built the
  packages, and it cannot**: an installed version string does not carry a build
  origin, an instruction-set guarantee, or working audio. Three questions stay
  separate and stay `unknown` until each has its own evidence:

  - *archive provenance* (blocker 6): the image's archive configuration and
    package metadata, tied to the image hash;
  - *declared instruction-set and ABI attributes* (blocker 5 and the `readelf`
    question): the exact binaries read with `readelf` on the card. This shows what
    the binaries declare, not that every instruction path is safe or that they
    run;
  - *functional audio* (blocker 8): PipeWire's Pulse compatibility, the socket,
    and whether `soundcard` can play and record — a load-and-play test, not an
    attribute.

  `readelf` speaks to the second and nothing else — declared attributes, not
  execution. Write down which of the three the run touched; do not report the
  inventory as provenance.
- **E1 — artifact audit, no ARM hardware.** Two separate checks, because one
  command cannot answer both questions:
  1. *What is published.* `pip download --only-binary=:all: --platform
     linux_armv6l --python-version 3.13 --implementation cp --abi cp313
     --extra-index-url https://www.piwheels.org/simple <pkg>` into a scratch
     directory, then `unzip -l` and `readelf -A`/`-h` on every `.so`. Repeat with
     `--platform manylinux_2_35_armv7l` and `manylinux_2_35_aarch64`. Expected
     evidence: per-artifact `Tag_CPU_arch`/`Tag_FP_arch`, and — for a package
     that fails — the pip error, which is itself the result: `--only-binary=:all:`
     makes a package with no matching wheel fail rather than fall back, so a
     failure means "no binary for this platform", not "a source build was
     chosen". Record the pip version, the indexes and the requirement strings
     with their pins.
  2. *What a source build would involve, package by package.* This cannot be a
     second cross-target `pip download`: `--platform`, `--python-version`,
     `--implementation` and `--abi` are only valid together with
     `--only-binary=:all:` **or** `--no-deps`, so "the same audit without
     `--only-binary`" is not a runnable command. The valid shapes are:
     - a per-package sdist inspection —
       `pip download --no-deps --no-binary=:all: <pkg>==<pinned version>` — then
       read `pyproject.toml`/`setup.py`, the declared build backend and its
       requirements. This says what a build would need; it does not say what a
       complete install on the target would choose;
     - a source-aware target resolution, which needs an environment that
       **matches the target**, not merely any armhf one: Raspberry Pi OS trixie
       armhf on ARMv6 (a disposable card on a Zero/Zero W, or an emulated
       `linux/arm/v6` environment built the same way), because the compatible
       platform tags are what pip chooses by, and a Debian ARMv7 armhf container
       is a different tag set — Debian's armhf baseline is ARMv7 even when the
       wheel is nominally 32-bit. Record `sysconfig.get_platform()`,
       `python3 -m pip debug --verbose`'s compatible-tag list, the pip version and
       the index configuration with the result; without them the run is not
       reproducible and "armhf" on its own proves nothing. It is not E2: E2 is a
       cross-target, binary-only report and cannot show what a normal install
       would choose. The same backend-isolation caution applies, because
       resolving a source candidate prepares its metadata.
     Two cautions to record with the result: preparing sdist metadata can execute
     build-backend code, so it belongs in a disposable, network-restricted
     environment rather than a scratch directory; and an arbitrary pip failure
     does not by itself mean "no binary exists" — an unreachable index and a
     dependency conflict look the same in a one-line error, so keep the full
     diagnostic.
- **E2 — resolver report, no install.** After a pinned requirement set exists —
  there is no `requirements-pinned.txt` in the repository yet, so creating one
  from the resolved versions is a prerequisite, not a step — run `pip install
  --dry-run --ignore-installed --report /tmp/report.json --platform linux_armv6l
  --python-version 3.13 --only-binary=:all: -r requirements-pinned.txt` from a
  clean virtual environment, with the index URLs named explicitly. Expected
  evidence: the JSON `download_info` list — the exact artifacts pip would take —
  and, for anything it cannot resolve, the failure. Because unpinned ranges can
  also make pip select an *older* wheel-bearing version rather than fail, a pass
  here is not proof that the newest declared version is installable. Report it as
  an artifact list, never as a source-build inventory.
- **E3 — import probe under emulation.** One execution context, named before the
  run, with paths that make sense inside it. The proposed mechanism is a
  **bubblewrap mount namespace** (`bwrap`) whose root is the extracted image,
  bound read-only, with the host's `qemu-arm-static` bound in **read-only** at a
  destination whose parent is writable when `bwrap` creates the mountpoint —
  not a path that must already exist in the image:

  ```sh
  bwrap --ro-bind /mnt/raspios / \
        --tmpfs /run \
        --ro-bind /usr/bin/qemu-arm-static /run/qemu-arm-static \
        --dev /dev --proc /proc --tmpfs /tmp --unshare-all \
        /run/qemu-arm-static -cpu arm1176 /usr/bin/python3 -c "import numpy; print(numpy.__file__)"
  ```

  The ordering and the mountpoint are the point, not decoration. `bwrap` creates
  a missing destination while setting up mounts, which needs a **writable parent
  at that moment**; after `--ro-bind /mnt/raspios /` the image tree is read-only,
  so binding the emulator to `/usr/bin/qemu-arm-static` would fail unless that
  file already existed in the image, and creates a second failure mode the
  document cannot assume away. `/run` is therefore a fresh `tmpfs` — writable, so
  the mountpoint can be created — and the emulator sits on it **read-only**
  (`--ro-bind`, not `--bind`), so nothing about the probe depends on the host
  binary being writable. If a different destination is used, it must be a
  prepared writable location, not a path that may not exist.

  Inside that namespace every path is a path in the image: the interpreter is
  `/usr/bin/python3`, the imported module reports a path under `/usr/lib/...`,
  and no `-L` prefix is needed because the dynamic loader is the image's own.
  Prerequisites, each verified rather than assumed: (a) **the image tree is
  read-only** — a write attempt under `/usr` is observed to be refused, and the
  claim is about the image bind, not about every mount in the namespace: `/run`,
  `/tmp`, `/dev` and `/proc` are deliberately writable exceptions, and the
  emulator bind is read-only. (b) **the confinement itself** — a mount namespace
  (bwrap or `unshare --mount`). A **chroot alone is refused** as insufficient:
  `chroot(2)` changes pathname resolution and nothing else, so it is neither
  read-only storage nor a security boundary. QEMU's `-L` is an ELF-interpreter
  prefix and confines nothing either, so a bare `qemu-arm-static -L /mnt/raspios`
  invocation is not this experiment. (c) the interpreter and search paths are
  recorded with the result, taken from the probe's own output rather than
  assumed. (d) the host permits the namespaces `--unshare-all` asks for; that is
  an environment check, not something the command can assume.

  Probe each package in its own process — the command above, then the same for
  `webrtc_noise_gain`, then the TFLite load — because a combined import cannot
  tell you which package raised `SIGILL`. Expected evidence: exit status per
  package, the imported file path, the signal or error text, the refusal of the
  write attempt, and an explicit statement of the namespace and bind mounts used.
  Caveat to record with the result: QEMU's CPU model is an approximation and says
  nothing about speed.
- **E4 — TFLite C build for ARMv6.** In a `linux/arm/v6` buildx container (or on a
  spare Zero with swap, offline): build `libtensorflowlite_c.so` from a commit
  hash — not a tag — with a pinned toolchain, at the version the pinned wheels
  currently bundle (**2.17.1**), chosen as the first target because it matches
  what the bindings ship beside. Whether the bindings work with an older library
  is a separate, open question; section 3 shows that a retained ARMv6 binary
  exports every symbol they bind, which is encouragement, not proof, and says
  nothing about the version that produced it. Then `readelf -A`, a
  `ctypes.CDLL(...)` load under E3's emulator, and a check that those same
  symbols resolve. Expected evidence: v6/VFPv2 attributes, a successful load, the
  symbol check, and `TfLiteModelCreateFromFile` on a bundled `.tflite`.
- **E5 — wake detection on real hardware.** On a Zero W, a fixed 10 s 16 kHz mono
  WAV: `time python -m pymicro_wakeword --model okay_nabu sample.wav`, with
  `/usr/bin/time -v` for peak RSS. Expected evidence: detection result,
  wall-clock, realtime factor, peak RSS. Note for the analysis: the CLI stops its
  WAV loop at the first detection, so a realtime factor has to divide by the
  audio actually processed, not by the full clip length. This is the first row
  that can become `tested`.
- **E6 — combined operation, last.** Only after E5: PipeWire + `sendspin daemon`
  + LVA on the same user, 30 minutes of music with three wake-word interruptions,
  logging RSS/CPU/underruns. Expected evidence: a pass/fail against thresholds
  agreed *before* the run.

## 6. What could not be established from public sources

- **`raspberrypi.com` documentation and `packages.debian.org` were blocked** in
  this session (HTTP 403 and an anti-bot interstitial respectively). The
  `raspberrypi/documentation` Git sources and Debian autobuilder status were used
  instead; per-package file lists (e.g. `libpulse0` vs `libpulse-dev`) come from
  the earlier note, not re-verified here.
- **Which archive built the Pi OS armhf packages**, and therefore whether every
  needed package is ARMv6-safe rather than ARMv7-baseline.
- **Whether the image preconfigures piwheels**, and what Python/`pip` defaults it
  ships.
- **What `--output-only` actually disables** in LVA. There is no documentation
  beyond the flag name, and the pinned `__main__.py`/`satellite.py` show it
  changing advertised capabilities while startup still loads the wake and stop
  models and starts audio processing. It is therefore not evidence that local
  inference cost disappears, and O2 is not a saving until it is measured.
- **Whether TFLite C (or TFLite Micro) can be built and run on ARM1176**, and
  whether microWakeWord's kernels are all portable there. TFLite Micro is not
  obviously a substitute: the bindings call the full `TfLiteModel*` /
  `TfLiteInterpreter*` C API, not TFLite Micro's API.
- **Any measured ARMv6 performance or memory figure** for LVA, SendSpin, mpv or
  PipeWire — none exists in the sources reached, and none was produced here.
- **`aiosendspin`/`sendspin` runtime use of newer `av`/`numpy` APIs** beyond
  declared constraints (carried over from the prior note; still `unknown`).
