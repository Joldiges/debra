# ARMv6 wheel availability for Debra's dependency set

**Research result, not a device test, 2026-11-15.** Nothing was installed and no
ARM device was contacted: every "observed" row is the inspection of a published
wheel or sdist, not a run. Produced by the unattended runner as task `Z02`, then
kept here because the raw working files were in a temporary directory.

This matters because **Pi Zero W support is a Debra requirement, not a
nice-to-have**, and the answer is not a clean yes:

| Question | Answer | Confidence |
| --- | --- | --- |
| Do the dependencies have 32-bit ARM wheels at all? | yes, 29 of 35 records install as-is from piwheels | observed |
| Is the `linux_armv6l` tag a promise that the code runs on ARMv6? | **no.** piwheels builds on Pi 3/4 hardware and renames; numpy's `armv6l` wheel contains ARMv8-tagged objects | observed |
| Can the two wake-word engines run on any ARM from piwheels? | **no.** Both bundle an x86-64 `libtensorflowlite_c.so` inside a wheel labelled `linux_armv6l` | observed |
| Does a Pi 5 (aarch64) lab device dodge this? | yes — the x86-64 wheel is only what piwheels serves for 32-bit ARM; PyPI publishes real aarch64 wheels, which is why LVA works on the lab Pi | hypothesis from the same metadata |

The wake-word finding is the one that changes plans: on ARMv6 the repair is a
self-built TensorFlow Lite C library (`microwakeword.py` accepts
`libtensorflowlite_c_path`), and whether that builds and runs is untested.

Read the labels as [evidence.md](../evidence.md) defines them: `observed` here
means an artifact was downloaded and its ELF headers read, which is stronger than
a vendor claim and weaker than a run.


Target: original **Raspberry Pi Zero W**, 32-bit Raspberry Pi OS **Trixie**, **CPython 3.13**.
Checked **2026-11-15** (UTC 07:2x–07:5x). Research only: nothing was installed, no device was contacted,
no build was executed on ARM.

Author model: `openrouter/deepseek/deepseek-v4.1-flash-1017#high` (host-reported identifier).

## Labels used

Debra's vocabulary (`docs/evidence.md`) plus one addition, declared here so it is not smuggled in:

| Label | Meaning in this report |
| --- | --- |
| `upstream-documented` | A linked primary source (project docs, FAQ, packaging metadata) states it |
| `observed` | **Reproducible inspection of a published artifact**: the named file was downloaded and its contents/ELF headers read. Not a device run, not a runtime test |
| `reported` | A third party's statement |
| `hypothesis` | Inference from code or packaging behaviour, not executed |
| `unknown` | Not established |

A wheel tag is not execution proof, and none of the `observed` rows claim the code runs.

## Upstream revisions inspected

| Project | Revision | How |
| --- | --- | --- |
| `linux-voice-assistant` | commit `12e51272d37d786ed3168955b3fb6eda3c7159ce`, main, 2026-11-14 | raw `pyproject.toml`, `README.md`, `docs/install.md`, `script/setup` |
| `sendspin` (`sendspin-python-cli`) | commit `e9a80e6afb6d4b00f8755b7bfd00bc4c20cbf503`, main, 2026-10-29 | raw `pyproject.toml`, `README.md`, `scripts/systemd/install-systemd.sh` |
| `aiosendspin` | commit `2174cdc4dd42145aa3b544d516a40a471f5b9781`, main, 2026-11-12 | raw `pyproject.toml` |
| `aiosendspin-mpris` | 2.1.1, homepage github.com/abmantis/aiosendspin-mpris | PyPI JSON `requires_dist` |

`LVA` main is mutable, so the commit above is the pin this table refers to. LVA itself pins
`websockets==12`, `netifaces2==0.0.22`, `aioesphomeapi==45.3.1` exactly and leaves the rest as ranges;
`sendspin` uses `~=` / `>=` only. "Resolved pin" below = the newest release on 2026-11-15 that satisfies the
constraint (i.e. what an unpinned `pip install` would choose), which is **not** the same as an ARMv6-safe pin.

## Exact index URLs checked

Per package (`<pkg>` = project name):

- `https://pypi.org/pypi/<pkg>/json` — release list, wheel filenames, `requires_python`, `requires_dist`
- `https://pypi.org/pypi/<pkg>/<version>/json` — the pinned version's own metadata and files
- `https://www.piwheels.org/project/<pkg>/json/` — piwheels releases, per-file `platform`, `file_abi_tag`,
  `requires_python`, `apt_dependencies`, `skip_reason`
- Wheel/sdist bytes: `https://www.piwheels.org/simple/<pkg>/<filename>` (some redirect to
  `https://archive1.piwheels.org/simple/<pkg>/<filename>`) and `https://files.pythonhosted.org/...` from the PyPI JSON

Index configuration a device would need (`upstream-documented`, piwheels FAQ):
`/etc/pip.conf` → `[global]` / `extra-index-url=https://www.piwheels.org/simple`; PyPI remains the default index.

## Assembled dependency set (direct deps of the inspected pyprojects)

LVA: `aioesphomeapi==45.3.1`, `netifaces2==0.0.22`, `soundcard<1`, `numpy>=2,<3`, `pymicro-wakeword>=2,<3`,
`pyopen-wakeword>=1,<2`, `python-mpv>=1,<2`, `zeroconf<1`, `getmac<1`, `types-protobuf`, `websockets==12`,
`webrtc-noise-gain>=1,<2`.
sendspin: `aiosendspin[server]~=10.2.2`, `aiosendspin-mpris~=2.1.1`, `av>=15.0.0`, `numpy>=1.26.0`,
`pillow>=10.0.0`, `pulsectl-asyncio>=1.2.2` (linux), `qrcode>=8.0`, `readchar>=4.0.0`, `rich>=13.0.0`,
`sounddevice>=0.4.6`, `textual-image>=0.13.0`.
aiosendspin: `aiohttp>=3.14.3`, `cpace>=0.1.0`, `cryptography>=44.0.1`, `mashumaro>=3.14`,
`noiseprotocol>=0.3.1`, `orjson>=3.11.6`, `zeroconf>=0.149.16`; `[server]` adds `av>=15`, `numpy>=2.1`,
`pillow>=12.3.0`.
aiosendspin-mpris: `aiosendspin>=2.0.0`, `mpris-api>=1.3.0` (linux).

## Findings table

`wheel ELF` = `readelf -A`/`-h` result for the objects inside the downloaded armv6l wheel.
`n/a` = no native object. `ARM v6 / VFPv2` = `Tag_CPU_arch: v6`, `Tag_FP_arch: VFPv2`, ARM EABI5 hard-float.

| project | package | upstream constraint | resolved pin | armv6l cp313 wheel on piwheels | wheel ELF | sdist toolchain | apt runtime libs | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LVA | `aioesphomeapi` | ==45.3.1 | 45.3.1 | yes - py2.py3-none-any (pure, no .so) | n/a (no native code in wheel) | Cython + gcc, but extensions optional -> pure-Python install works | none | PyPI itself ships only platform wheels for 45.3.1; the pure wheel comes from piwheels |
| LVA | `netifaces2` | ==0.0.22 | 0.0.22 | yes - netifaces2-0.0.22-cp37-abi3-linux_armv6l.whl | ARM v6 / VFPv2 | Rust + maturin (no Rust on Pi OS by default) | libc6, libgcc-s1 |  |
| LVA | `soundcard` | <1 | 0.4.6 | yes - py3-none-any (pure) | n/a | none | libpulse0 + libpulse-dev (dlopen needs unversioned libpulse.so) | cffi + numpy required; Linux backend is PulseAudio only (`soundcard/pulseaudio.py`) |
| LVA | `numpy` | >=2,<3 (aiosendspin server: >=2.1) | 2.5.4 resolved | yes - cp313 armv6l wheel exists | 3 of 19 objects declare Tag_CPU_arch v8 (incl. _multiarray_umath, _simd) | meson-python + C/C++/Fortran + BLAS | libopenblas0-pthread, libgfortran5, libstdc++6 | last fully v6 wheel: 2.2.1; 2.3.0+ carry v8 objects |
| LVA | `pymicro-wakeword` | >=2,<3 | 2.5.0 | wheel exists but is unusable: bundled libtensorflowlite_c.so is x86-64 | - | no compile step; sdist ships the same x86-64 .so | none | hard blocker on every ARM target, not only ARMv6 |
| LVA | `pymicro-features` | >=2 (transitive of pymicro-wakeword) | 2.0.2 | yes - pymicro_features-2.0.2-cp39-abi3-linux_armv6l.whl | ARM v6 / VFPv2 | C++ (pybind-style Extension) | none |  |
| LVA | `pyopen-wakeword` | >=1,<2 | 1.1.0 | wheel exists but is unusable: bundled libtensorflowlite_c.so is x86-64 | - | no compile step; sdist ships the same x86-64 .so | none | PyPI publishes aarch64/x86_64 only; no armv7l either |
| LVA | `python-mpv` | >=1,<2 | 1.0.8 | yes - py3-none-any (pure, ctypes) | n/a | none | libmpv2 (find_library('mpv') resolves libmpv.so.2) | LVA docs also list libmpv-dev |
| LVA | `zeroconf` | <1 | 0.154.0 | no cp313 armv6l wheel (cp311 only); last cp313 wheel is 0.151.5 | - | Cython optional, build failures suppressed -> pure-Python install | none | pin 0.151.5 for a wheel, or accept an sdist build |
| LVA | `getmac` | <1 | 0.9.6 | yes - py2.py3-none-any | n/a | none | none |  |
| LVA | `types-protobuf` | unpinned (typing stubs) | 7.35.1.20260906 | yes - py3-none-any | n/a | none | none | stubs only, no runtime code |
| LVA | `websockets` | ==12 | 12.0 | yes - websockets-12.0-cp313-cp313-linux_armv6l.whl | ARM v6 / VFPv2 | optional C speedups, pure-Python fallback | none |  |
| LVA | `webrtc-noise-gain` | >=1,<2 | 1.3.0 | yes - webrtc_noise_gain-1.3.0-cp39-abi3-linux_armv6l.whl | ARM v6, but Tag_FP_arch=VFPv3 | C++ (compile from ~660 sources) | libstdc++6 | VFPv3 attribute on VFPv2 hardware: runtime test needed |
| sendspin | `aiosendspin` | ~=10.2.2 | 10.2.2 | yes - py3-none-any | n/a | none | none |  |
| sendspin | `aiosendspin-mpris` | ~=2.1.1 | 2.1.1 | yes - py3-none-any | n/a | none | none | pulls mpris-api, whose dbus-next dep is not declared |
| sendspin | `av` | >=15.0.0 | 19.0.2 resolved | no wheel for 19.0.2 (piwheels release has zero files); 16.1.0 has cp311-abi3 armv6l | 16.1.0: all 49 objects ARM v6 / VFPv2 | Cython + pkg-config + FFmpeg -dev | libavcodec61, libavformat61, libavutil59, libswresample5, libswscale8, libavfilter10, libavdevice61 | pin av==16.1.0; wheel links dynamically to Trixie's FFmpeg 7.1 sonames |
| sendspin | `pillow` | >=10 (aiosendspin server: >=12.3.0) | 13.0.0 | yes - pillow-13.0.0-cp313-cp313-linux_armv6l.whl | ARM v6 / VFPv2 | C + many -dev libraries | libtiff6, libjpeg62-turbo, libopenjp2-7, libxcb1, zlib1g (wheel NEEDED) | piwheels apt list is larger; only these are runtime NEEDED |
| sendspin | `pulsectl-asyncio` | >=1.2.2 (linux) | 1.3.2 | yes - py3-none-any | n/a | none | libpulse0 (find_library('libpulse') -> libpulse.so.0) |  |
| sendspin | `qrcode` | >=8.0 | 8.2 | yes - py3-none-any | n/a | none | none |  |
| sendspin | `readchar` | >=4.0.0 | 4.2.2 | yes - py3-none-any | n/a | none | none |  |
| sendspin | `rich` | >=13.0.0 | 15.0.0 | yes - py3-none-any | n/a | none | none |  |
| sendspin | `sounddevice` | >=0.4.6 | 0.5.6 | yes - py3-none-any (+cffi) | n/a | none | libportaudio2 (find_library('portaudio')) | upstream systemd installer installs libportaudio2 |
| sendspin | `textual-image` | >=0.13.0 | 0.14.4 | yes - py3-none-any | n/a | none | none | needs pillow; textual only for the extra |
| aiosendspin | `aiohttp` | >=3.14.3 | 3.14.5 | yes - aiohttp-3.14.5-cp313-cp313-linux_armv6l.whl | ARM v6 / VFPv2 | C + Cython | libc6 |  |
| aiosendspin | `cpace` | >=0.1.0 | 0.1.0 | yes - py3-none-any | n/a | none | none | pure Python, needs cryptography>=42 |
| aiosendspin | `cryptography` | >=44.0.1 | 50.0.2 | yes - cryptography-50.0.2-cp313-abi3-linux_armv6l.whl | ARM v6 / VFPv2 | Rust + maturin | libssl3t64 (libssl.so.3), libcrypto.so.3 |  |
| aiosendspin | `mashumaro` | >=3.14 | 3.23 | yes - py3-none-any | n/a | none | none |  |
| aiosendspin | `noiseprotocol` | >=0.3.1 | 0.3.1 | yes - py3-none-any | n/a | none | none |  |
| aiosendspin | `orjson` | >=3.11.6 | 3.13.0 | yes - orjson-3.13.0-cp313-cp313-linux_armv6l.whl | ARM v6 / VFPv2 | Rust + maturin | libc6, libgcc-s1 |  |
| mpris | `mpris-api` | >=1.3.0 | 1.3.0 | no wheel (sdist only) | pure Python, no native code | none (setuptools) | none | imports dbus_next, not declared in its metadata |
| transitive | `cffi` | soundcard/sounddevice dep | 2.1.1 | yes - cffi-2.1.1-cp313-cp313-linux_armv6l.whl | ARM v6 / VFPv2 | C (libffi headers) | libffi8 |  |
| transitive | `protobuf` | aioesphomeapi: >=6,<8 | 7.36.2 | yes - protobuf-7.36.2-cp313-cp313-linux_armv6l.whl | ARM v6 / VFPv2 | C++ (upb) | libc6 |  |
| transitive | `ifaddr` | zeroconf dep | 0.2.0 | yes - py3-none-any | n/a | none | none |  |
| transitive | `pulsectl` | pulsectl-asyncio dep | 24.12.0 | yes - py2.py3-none-any | n/a | none | libpulse0 |  |
| transitive | `chacha20poly1305-reuseable` | aioesphomeapi dep | 0.13.2 | yes - py3-none-any | n/a | none | none |  |

Count: **35 records; 29 usable as-is; 3 need a ceiling/replacement pin (numpy, av, zeroconf);
1 needs a runtime check (webrtc-noise-gain); 2 are dead (both wake-word engines).**

## Traps

1. **`linux_armv6l` is an ABI label, not an instruction-set promise.** piwheels builds natively on Pi 3/4
   hardware (`upstream-documented`) and renames those wheels `armv6l`, with a handful of packages "built with
   optimisations available on Pi 3/4". `observed`: numpy 2.5.4's `armv6l` wheel contains `Tag_CPU_arch: v8`
   objects, including the core `_multiarray_umath` and `_simd`. Of the versions I inspected (1.26.2, 2.0.0,
   2.1.3, 2.2.0, 2.2.1, 2.3.0, 2.3.5, 2.4.0, 2.5.4), **2.2.1 is the newest wheel with no v8 object**.
2. **The two wake-word engines ship an x86-64 TensorFlow Lite.** `observed`: `pymicro_wakeword-2.5.0-py3-none-linux_armv6l.whl`
   (all 2.0.0–2.5.0) and `pyopen_wakeword-1.1.0-py3-none-linux_armv6l.whl` each contain
   `pymicro_wakeword/lib/libtensorflowlite_c.so` / `pyopen_wakeword/lib/libtensorflowlite_c.so` as
   `ELF 64-bit ... x86-64` (identical BuildID `8689b38195b83ac1`). Their `setup.py` has no build step — it
   repackages whatever is in the sdist, and the sdist contains the same x86-64 file. `hypothesis`: the
   `ctypes.CDLL(...)` in `wakeword.py` will raise "wrong ELF class". The PyPI `manylinux_2_35_armv7l` wheel
   does contain 32-bit ARM code, but `observed` `Tag_CPU_arch: v7`, `Tag_FP_arch: VFPv4` — still not ARMv6.
   What piwheels serves is therefore wrong for *every* ARM target; the PyPI `armv7l` wheel at least contains
   ARM code, so only ARMv6 is excluded there (`observed` v7 attribute, not run). Either way the ARMv6 repair is
   a self-built TFLite C library: `microwakeword.py` accepts `libtensorflowlite_c_path`.
3. **Unpinned resolution walks straight into the gaps.** `av` resolves to 19.0.2, which has no armv6l wheel,
   so pip builds PyAV from source (Cython + `pkg-config` + FFmpeg headers, hours on a Zero). `numpy` resolves
   to the v8-tainted 2.5.4. `zeroconf` resolves to a version piwheels never built for cp313.
4. **`aioesphomeapi==45.3.1` is only pure-Python because of piwheels.** PyPI publishes platform wheels only
   (cp311–cp314t, including `armv7l` — so upstream's own floor is ARMv7); the `py2.py3-none-any` wheel is
   piwheels' build with Cython extensions skipped (`observed`: no `.so` inside).
   Without the piwheels index the sdist is used, and its `OptionalBuildExt` tolerates a failed compile.
5. **`soundcard` needs the unversioned `libpulse.so`.** `observed` in its source: `dlopen('pulse')` then
   `dlopen('libpulse.so')`. Debian's `libpulse0` ships only `libpulse.so.0` / `libpulse-simple.so.0`;
   the unversioned symlink is in `libpulse-dev`. `hypothesis` on the exact failure, `upstream-documented` on
   the file lists — install `libpulse-dev` rather than gamble on `libpulse0` alone.
6. **`mpris-api` declares no dependencies.** `observed`: PyPI metadata `requires_dist: null`, sdist ships only
   a tarball, and its `requirements/release.txt` lists `dbus-next ~= 0.2`, `unidecode ~= 1.3`, `tunit ~= 1.7`.
   `aiosendspin-mpris` only requires `mpris-api`, so `dbus-next` can be missing at runtime. `hypothesis`:
   sendspin's MPRIS registration fails on a headless box without a session bus anyway — worth an explicit test.
7. **`av`'s wheel is not self-contained.** `observed` `NEEDED` entries: `libavcodec.so.61`,
   `libavformat.so.61`, `libavutil.so.59`, `libswresample.so.5`, `libswscale.so.8`, `libavfilter.so.10`,
   `libavdevice.so.61`. Trixie ships FFmpeg `7:7.1.5-0+deb13u1` with exactly those sonames
   (`upstream-documented`, Debian package pages), so 16.1.0 fits Trixie but would break on a distro with
   FFmpeg 6 or 8.
8. **`websockets==12` is old (12.0 released 2023-10-21) but healthy here**: cp313 armv6l wheels exist for 12.0 through 17.x, so
   this pin costs nothing. LVA's exact `==12` is a deliberate upstream choice, not a constraint we inherit
   from packaging.
9. **`webrtc-noise-gain` is the one wheel I cannot clear by inspection.** Its only object is
   `ARM v6 / VFPv3`. VFPv3 instructions on an ARM1176 (VFPv2) would fault; gcc may emit none. `unknown` until
   a device test.

## Unknowns and blocked

- **No runtime execution**: no wheel was installed or imported on ARMv6, so "wheel exists + ELF says v6" is
  the strongest claim here. The numpy v8 and webrtc VFPv3 findings need a `python -c "import ..."` on a Zero.
- **Pi Zero W / Raspberry Pi OS Trixie image contents not verified directly**: `raspberrypi.com` documentation
  returned **HTTP 403** in this session (same block recorded in `docs/evidence.md`). The ARMv6 hardware claim
  comes from the piwheels FAQ, and the CPython 3.13 claim from Debian trixie's `python3` package page plus the
  piwheels Debian→Python table. Whether the 32-bit Trixie image ships `/etc/pip.conf` with piwheels is
  `unknown` (the FAQ describes what the file *should* contain, not what the image contains).
- **aiosendspin/sendspin code-level use of newer `av`/`numpy` APIs** was not audited: `av==16.1.0` and
  `numpy<=2.2.1` satisfy declared constraints, but a runtime API call may still need newer versions. `unknown`.
- **`pymicro-wakeword` repair feasibility** (building `libtensorflowlite_c.so` for ARMv6 from the microWakeWord
  sources, and whether the TFLite Micro kernels it needs are all portable to ARMv6) is `unknown`.
- **`zeroconf` sdist build on cp313/armv6** is expected to succeed without a compiler because failures are
  suppressed, but that path was read, not run.
- Not investigated: whether Trixie's `libmpv` build carries the codecs LVA needs; performance
  (a Zero W running wake-word detection) — outside this packet.

## Next bounded check

One device, no service changes: on a spare Pi Zero W with 32-bit Trixie, create a venv,
`pip install --only-binary=:all: --extra-index-url https://www.piwheels.org/simple numpy==2.5.4`, then
`python -c "import numpy; print(numpy.__version__)"`; repeat for `numpy==2.2.1`, `av==16.1.0` and
`webrtc-noise-gain==1.3.0`, one clean venv each, recording exit codes and any `SIGILL`. That converts the three `observed`/`hypothesis` rows into
`tested`/failed and tells Z02 whether a source build of numpy is needed at all.

## Source register

1. https://github.com/OHF-Voice/linux-voice-assistant — repository root (main, commit `12e51272d37d786ed3168955b3fb6eda3c7159ce`)
2. https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/12e51272d37d786ed3168955b3fb6eda3c7159ce/pyproject.toml — dependency list
3. https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/12e51272d37d786ed3168955b3fb6eda3c7159ce/README.md — "linux/amd64 and linux/aarch64", prerequisites `libmpv-dev`, PulseAudio/PipeWire, `alsa-utils`
4. https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/12e51272d37d786ed3168955b3fb6eda3c7159ce/script/setup — venv install, `find_library("mpv")`/`("asound")` checks, `CXXFLAGS`/`MAKEFLAGS`
5. https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/12e51272d37d786ed3168955b3fb6eda3c7159ce/docs/install.md — PipeWire/PulseAudio install paths
6. https://github.com/Sendspin/sendspin-python-cli — repository root (main, commit `e9a80e6afb6d4b00f8755b7bfd00bc4c20cbf503`)
7. https://raw.githubusercontent.com/Sendspin/sendspin-python-cli/e9a80e6afb6d4b00f8755b7bfd00bc4c20cbf503/pyproject.toml — sendspin dependencies
8. https://raw.githubusercontent.com/Sendspin/sendspin-python-cli/e9a80e6afb6d4b00f8755b7bfd00bc4c20cbf503/scripts/systemd/install-systemd.sh — libportaudio2 check and install
9. https://raw.githubusercontent.com/Sendspin/aiosendspin/2174cdc4dd42145aa3b544d516a40a471f5b9781/pyproject.toml — aiosendspin dependencies and `[server]` extra
10. https://pypi.org/pypi/aiosendspin-mpris/json — `requires_dist`: `aiosendspin>=2.0.0`, `mpris-api>=1.3.0`
11. https://www.piwheels.org/faq.html — armv6l/armv7l tagging rationale, native builds on Pi 3/4, Debian→Python table (Trixie = 3.13), `/etc/pip.conf` `extra-index-url`
12. https://packages.debian.org/trixie/python3 — `python3 (3.13.5-1)`
13. https://packages.debian.org/trixie/ffmpeg — `7:7.1.5-0+deb13u1`; and the soname packages `libavutil59`, `libavcodec61`, `libavformat61`, `libavfilter10`, `libswresample5`, `libswscale8`, `libavdevice61`
14. https://packages.debian.org/trixie/armhf/libpulse0/filelist — `libpulse.so.0` only
15. https://packages.debian.org/trixie/armhf/libpulse-dev/filelist — unversioned `libpulse.so`
16. https://packages.debian.org/trixie/armhf/libmpv2/filelist — `libmpv.so.2`
17. https://packages.debian.org/trixie/armhf/libportaudio2/filelist — `libportaudio.so.2`
18. https://www.piwheels.org/project/pymicro-wakeword/json/ and https://www.piwheels.org/project/pyopen-wakeword/json/ — armv6l wheel listings used for the ELF inspection (files fetched from `https://archive1.piwheels.org/simple/...`)
19. https://pypi.org/pypi/mpris-api/1.3.0/json — sdist only, `requires_dist: null`
20. https://www.raspberrypi.com/documentation/computers/raspberry-pi.html — attempted, **HTTP 403**, not reviewed

## What Debra should do with this

1. **Pin, do not float.** An unpinned install on a Zero W walks into all three
   gaps at once: `av` 19.0.2 (no wheel, source build), numpy 2.5.4 (ARMv8
   objects), `zeroconf` 0.154.0 (no cp313 wheel). Pin `av==16.1.0`,
   `numpy<=2.2.1`, `zeroconf==0.151.5` for a 32-bit ARM target.
2. **Treat the wake-word engine as the open risk**, not as a solved dependency.
   Either build TFLite for ARMv6, or accept that a Zero W appliance needs the wake
   word hosted in Home Assistant, or choose a different board.
3. **Do not claim Pi Zero W support from a wheel tag.** The first honest evidence
   is `python -c "import numpy"` on the actual board, which is one clean venv and
   four installs — see the next bounded check above.
4. **Pi Zero 2 W is unaffected by the instruction-set findings** (ARMv8-A in
   32-bit mode, so the `v8` objects and VFPv3 are fine) but is affected by the
   x86-64 TFLite wheel, because piwheels serves the same broken artifact for both.

## Provenance

Raw artifacts from the run (PyPI and piwheels JSON, downloaded wheels, ELF dumps)
lived under `/tmp/opencode/z02/` and are not preserved: `/tmp` is not storage.
The claims are reproducible from the URLs in the register below with the method
described in the report.
