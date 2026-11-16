---
title: ARMv6 dependency findings on a real Pi Zero W — the wheels work, the resolution does not
date: 2026-11-16
type: project-learning
status: unreviewed
task: unauthored — device bring-up directed by James in session
author: OpenCode session
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - Pi Zero W Rev 1.1, Raspbian 13 (trixie), kernel 6.18.50+rpt-rpi-v6, CPython 3.13.5, pip 25.1.1, observed 2026-11-16
  - docs/research/2026-11-15-armv6-wheels.md (the artifact inspection this tests)
  - docs/research/Z01-armv6.md (the ranked blockers this tests)
  - git history 90a4c19:legacy/raspi0/libtensorflowlite_c.so (the retained ARMv6 TFLite binary)
supersedes: []
---

# ARMv6 dependency findings on a real Pi Zero W

## Summary

The research said the wheels were the risk. On the board, **the wheels are fine
and the resolver is the risk.** Every artifact that was inspected as
"ARMv6-tagged but suspicious" installed and ran. What actually broke was pip
choosing a *newer* version that has no armv6l wheel at all, which silently turns
into a multi-hour source build on a 1 GHz single core.

The one genuine blocker — no ARMv6 TensorFlow Lite C runtime — is **solved by
the binary this repository already had in its history**, which loads and runs
wake-word inference faster than realtime.

## Claims and evidence

| Kind | Claim | Verification |
| --- | --- | --- |
| observed | `numpy` 2.5.4's `Tag_CPU_arch: v8` objects **do not fault** on ARM1176 | `import numpy` plus `dot` (BLAS), `fft`, `outer`, `matmul`, `linalg.norm`, `convolve` all correct on 2.5.4 **and** 2.2.1. The research's "3 of 19 objects declare v8" is real but does not translate into an illegal instruction on these paths |
| observed | `webrtc-noise-gain` 1.3.0's `Tag_FP_arch: VFPv3` object **does not fault** | `import webrtc_noise_gain` succeeds. This was the one wheel the research explicitly could not clear by inspection |
| observed | `av` 16.1.0 imports and links Trixie's FFmpeg | `import av` → 16.1.0 |
| observed | The first failures were **missing apt runtime libraries**, not ABI | `libopenblas.so.0` / `libblas.so.3` absent. After `libopenblas0-pthread liblapack3 libblas3 libgfortran5`, all three import. The research's apt-dependency column was correct and I had skipped it |
| observed | **numpy 2.5.5 has no armv6l wheel**, so an unpinned install builds it from source | pip resolved 2.5.5, fell back to the sdist, and started a meson/ninja build that was still running after 16 minutes. piwheels stops at 2.5.4 |
| observed | Pinning `numpy==2.5.4` makes the whole install wheel-only | numpy 2.5.4, pymicro-wakeword 2.5.0 and pymicro-features 2.0.2 all resolved as `linux_armv6l` wheels; install completed in minutes |
| observed | The retained historical ARMv6 TFLite binary **loads and runs** | `ctypes.CDLL` succeeds; 122 feature frames scored; `okay_nabu` detection at 0.86 probability; **2.2–2.8× realtime** for continuous scoring |
| observed | The binary is TensorFlow **2.14.0** | `strings` contains `2.14.0`, consistent with the historical `tfbuild.sh` target. Still not a build log, so provenance remains unproven |
| observed | The bundled wake-word wheels ship an **x86-64** library | `readelf -h` on `pymicro_wakeword/lib/libtensorflowlite_c.so` from the `linux_armv6l` wheel: `ELF64`, `x86-64`. Reproduces the research independently. Every piwheels ARM wheel 2.0.0–2.5.0 is the same; see [the upstream report](../upstream/2026-11-16-pymicro-wakeword-armv6-elf.md) |
| observed | The binding accepts an explicit library path | `MicroWakeWord.from_config(config_path, libtensorflowlite_c_path=...)` exists in 2.5.0, and the module's own `lib/` directory is searched first. So a drop-in `.so` replacement works without patching the caller |

## The correction that matters

The research framed the risk as "the `armv6l` tag is not a promise". That is
true and worth keeping. But the practical failure mode on this board was
different and more mundane: **an unpinned requirement resolves to a version
piwheels never built**, and pip then compiles it. On a Zero W that is not a
slow install, it is an hours-long one that looks like a hang.

So the rule for this platform is not "avoid ARMv6-tagged wheels". It is **pin
every native dependency to a version that has an armv6l wheel**, and treat a
source build as a signal that the pin is wrong.

## Verification

- Commands: `pip install --only-binary=:all:` per package in a clean venv;
  `python -c "import numpy; ..."`; `readelf -h` on bundled `.so` files;
  `~/ww/bin/python ww_test.py --lib <armv6 .so> --model okay_nabu --wav <wav>`.
- Observed: all of the above pass; the only failures were missing apt libraries
  and the unpinned numpy 2.5.5 source build.
- Not tested: whether every numpy code path is v8-safe (only the listed
  operations were exercised); long-running stability; whether the 2.14.0 TFLite
  library handles every operator in every bundled model (four models were
  loaded, two detected).
- Sanitized artifacts: none committed. The `.so` is in Git history at `90a4c19`.

## Handoff and correction links

- Next action: **resolved 2026-11-16.** A pinned 2.17.1 ARMv6 build now exists
  and is verified on the board; it replaces the historical 2.14.0 binary. The
  build needs `-marm`, `-march=armv6k` and a Raspbian bookworm armv6 sysroot;
  see [the upstream report](../upstream/2026-11-16-pymicro-wakeword-armv6-elf.md).
  The fork branch carries the library and the build scripts.
- Authorization: James directed this board's bring-up. Nothing here authorizes
  changing another device or publishing an image.
