---
title: Wheels built from the sdist carry an x86-64 libtensorflowlite_c.so, so every piwheels ARM wheel is unusable
date: 2026-11-16
type: upstream-report
state: evidenced
project: OHF-Voice/pymicro-wakeword
component: sdist contents, script/copy_lib, setup.py, pymicro_wakeword/lib/libtensorflowlite_c.so
affected_versions: 2.0.0–2.5.0 (piwheels armv6l/armv7l wheels); 1.1.0 (pyopen-wakeword, same file)
fixed_in: unknown
environment: Raspbian 13 (trixie) armhf, kernel 6.18.50+rpt-rpi-v6, ARM1176 (ARMv6), CPython 3.13.5, pip 25.1.1
author: OpenCode session
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - https://www.piwheels.org/simple/pymicro-wakeword/ (all armv6l/armv7l wheels, 2.0.0–2.5.0)
  - https://pypi.org/pypi/pymicro-wakeword/2.5.0/json (sdist pymicro_wakeword-2.5.0.tar.gz)
  - https://www.piwheels.org/simple/pyopen-wakeword/pyopen_wakeword-1.1.0-py3-none-linux_armv6l.whl
  - docs/research/2026-11-15-armv6-wheels.md (prior artifact inspection)
  - docs/testing/results/2026-11-16-zero-w-bringup.md (device run)
links:
  issue: https://github.com/OHF-Voice/pymicro-wakeword/issues/13
  pull_request: https://github.com/OHF-Voice/pymicro-wakeword/pull/18
  related:
    - https://github.com/OHF-Voice/pymicro-wakeword/issues/2
    - https://github.com/OHF-Voice/pymicro-wakeword/pull/19
    - https://github.com/OHF-Voice/linux-voice-assistant/issues/158
    - https://github.com/OHF-Voice/linux-voice-assistant/tree/arm32
    - https://github.com/Joldiges/pymicro-wakeword/tree/fix/sdist-platform-library
---

## Summary

`pymicro-wakeword`'s sdist contains exactly one prebuilt
`pymicro_wakeword/lib/libtensorflowlite_c.so`, and that file is **x86-64**. The
per-architecture libraries live in `lib/linux_armv7l/`, `lib/linux_arm64/` and
so on, and are copied into place by `script/copy_lib` — a script that is **not
in the sdist** and only runs in the project's own release workflow.

Any wheel built from the sdist therefore ships the x86-64 library, whatever
platform it was built on. piwheels builds from the sdist, so **every piwheels
`linux_armv6l` and `linux_armv7l` wheel from 2.0.0 to 2.5.0 contains an x86-64
`.so`** and fails at `ctypes.CDLL` with a wrong-ELF-class error.
`pyopen-wakeword` 1.1.0 ships the byte-identical file.

This is a narrower and more actionable claim than "ARM is broken": the
project's own PyPI wheels are correct. The defect is that the sdist is not
buildable into a correct wheel on any non-x86-64 machine.

## Impact

**Anyone who installs from piwheels gets a package that cannot load.** That is
not an edge case: Raspberry Pi OS preconfigures `/etc/pip.conf` with
`extra-index-url=https://www.piwheels.org/simple`, so a stock Pi install selects
the piwheels wheel by default.

Two distinct populations are affected, and they need different answers:

| Target | What pip gets | Result |
| --- | --- | --- |
| ARMv7 (Pi 2/3 32-bit, Orange Pi) | PyPI `manylinux_2_35_armv7l` wheel, or the piwheels `armv7l` wheel | PyPI wheel works; piwheels wheel is x86-64 and fails |
| ARMv6 (Pi Zero W, Pi 1) | piwheels `armv6l` wheel only — PyPI publishes no armv6l wheel | Always fails |

For ARMv6 there is a second, independent blocker even if the packaging were
fixed: the project's ARMv7 library is built for **ARMv7-A + NEON + VFPv4**
(`Tag_CPU_arch: v7`, `Tag_Advanced_SIMD_arch: NEONv1 with Fused-MAC`,
`Tag_FP_arch: VFPv4`). ARM1176 has none of those, so a correctly packaged
armv7l library would raise `SIGILL` on a Pi Zero W rather than load.

Workarounds exist and are not discoverable from the error:

- pass `libtensorflowlite_c_path=` to `MicroWakeWord.from_config()` (the
  parameter exists, but the caller must know to use it and must supply a
  correctly built library);
- replace the `.so` inside `site-packages` after install.

## Minimal reproduction

No ARM hardware is needed to see the defect; only to see the failure.

```sh
# 1. The piwheels armv6l wheel is x86-64, whatever the tag says
curl -sfLO https://archive1.piwheels.org/simple/pymicro-wakeword/\
pymicro_wakeword-2.5.0-py3-none-linux_armv6l.whl
unzip -o pymicro_wakeword-2.5.0-py3-none-linux_armv6l.whl -d x
readelf -h x/pymicro_wakeword/lib/libtensorflowlite_c.so | grep -E 'Class|Machine'
```

Expected: `ELF32`, `ARM`. Actual:

```
  Class:   ELF64
  Machine: Advanced Micro Devices X86-64
```

```sh
# 2. The sdist carries the same file and has no per-platform libs at all
pip download --no-deps --no-binary=:all: pymicro-wakeword==2.5.0 -d sdist
tar tzf sdist/pymicro_wakeword-2.5.0.tar.gz | grep -E 'lib/|copy_lib'
```

Actual: one `pymicro_wakeword/lib/libtensorflowlite_c.so`, no `lib/linux_*`
directories, no `script/copy_lib`. Its SHA-256 is
`25465edb5cd7aadd00249d4d28f1d922ce5cc90195ad4403458111dd63493bae`, identical
to the wheel's copy.

On the target board, `ctypes.CDLL(<that file>)` raises
`OSError: ... wrong ELF class: ELFCLASS64`.

## Evidence

| Kind | Claim | Scope | Verification |
| --- | --- | --- | --- |
| observed | Every piwheels ARM wheel is x86-64 | 2.0.0, 2.1.0, 2.2.0, 2.2.1, 2.3.0, 2.4.0, 2.4.1, 2.5.0 — both `armv6l` and `armv7l` tags | `readelf -h` on each downloaded wheel: `ELF64`, `x86-64` in all cases |
| observed | The sdist contains one x86-64 library and no per-platform directories | 2.5.0 | `tar tzf` file list; `sha256sum` matches the wheel's copy |
| observed | `pyopen-wakeword` 1.1.0 ships the identical file | 1.1.0, piwheels | same SHA-256 |
| observed | The project's own ARMv7 wheel is real ARMv7 code | PyPI `manylinux_2_35_armv7l` 2.5.0 | `ELF32`/`ARM`; `Tag_CPU_arch: v7`, `NEONv1 with Fused-MAC`, `VFPv4` |
| observed | That ARMv7 library cannot run on ARMv6 | ARM1176 has no NEON and no VFPv4 | Attribute comparison; not executed on the board (the x86-64 file fails first) |
| observed | `setup.py` declares a platform wheel but builds nothing | 2.5.0 sdist | `has_ext_modules()` returns `True`; `bdist_wheel.get_tag()` forces `py3-none-<plat>`; no `ext_modules`, no build step |
| observed | A correctly built ARMv6 library makes the package work | Pi Zero W, 2026-11-16 | Substituting an ARMv6 `libtensorflowlite_c.so` gave working inference at 2.2–2.8× realtime; see the [bring-up result](../testing/results/2026-11-16-zero-w-bringup.md) |
| upstream-documented | The aarch64 symptom was reported and closed unplanned | issue #13, 2026-03-25 → 2026-09-17 | Reporter's traceback is the same `CDLL` failure; maintainer asked for `sys.platform`/`platform.machine()`; closed `not_planned` |
| upstream-documented | 32-bit ARM support was declined, then partially added | issue #2, PRs #18/#19 | Maintainer, 2025-10-09: "I don't have any plans for 32-bit ARM support." PR #18 (merged 2026-06-22) added `armv7l`; PR #19 fixed its wheel build |
| observed | PR #18 does not fix the piwheels path | 2.4.1 and 2.5.0, both released after the merge | Both piwheels `armv6l` wheels are still x86-64; `from_config()` prefers `pymicro_wakeword/lib/`, so `get_platform()` is never reached in an installed wheel |
| upstream-documented | LVA's own 32-bit request is closed, with an experimental branch | LVA issue #158, closed 2026-11-16 | Closed `completed`; `arm32` branch exists, microWakeWord only, openWakeWord unsupported |

## Root cause

The sdist vendors a prebuilt `libtensorflowlite_c.so` and `setup.py` repackages
it without building. `has_ext_modules()` is set to `True` so the wheel is tagged
platform-specific, but the tag is then forced to `py3-none-<plat>` where
`<plat>` is whatever machine ran the build.

The project's own release workflow avoids the trap by running
`script/copy_lib`, which selects `lib/linux_<arch>/` for the target and copies
it over the default. That script is not shipped in the sdist, so a third-party
builder — piwheels is the important one — has no way to make the same choice and
silently produces a wheel whose tag describes the *builder* while its payload is
the x86-64 default.

### Why PR #18 does not fix this

PR #18 (merged 2026-06-22) is the obvious "already fixed" objection, and it is
worth answering precisely, because it fixed two other paths and left this one
untouched.

What #18 changed:

- `script/copy_lib` and `script/package` now map `armv6l`/`armv7l`/`armv8l`/
  `armhf` to `linux_armv7l` instead of `linux_arm64`, and `publish.yml` builds
  an `armv7l` wheel. This is why PyPI has a correct
  `manylinux_2_35_armv7l` wheel from 2.4.1 onward.
- `get_platform()` in `wakeword.py` now returns `linux_armv7l` on 32-bit ARM,
  so running from a git checkout finds `lib/linux_armv7l/`.

What it did not change is the order of resolution in
`MicroWakeWord.from_config()`:

```python
if libtensorflowlite_c_path is None:
    # Try module lib dir first (inside wheel)
    libtensorflowlite_c_path = next(
        iter(_MODULE_LIB_DIR.glob("*tensorflowlite_c.*")), None
    )
    if not libtensorflowlite_c_path:
        # Try repo dir
        platform = get_platform()
        ...
```

`get_platform()` is a **fallback**, and the sdist always populates the
directory that is checked first. On the board:

```
get_platform()      : linux_armv7l          <- correct, and never consulted
_MODULE_LIB_DIR     : .../pymicro_wakeword/lib
  glob hits         : ['libtensorflowlite_c.so']   <- x86-64, taken immediately
_REPO_LIB_DIR       : .../site-packages/lib
  exists            : False                  <- fallback target absent
```

The fallback target cannot exist either: `MANIFEST.in` ships only
`recursive-include pymicro_wakeword/lib *`, so the top-level `lib/linux_*`
directories are not in the sdist at all (verified: zero `lib/linux` entries in
the 2.5.0 tarball).

The decisive check is the artifacts released *after* the merge:

| Version | Released | piwheels `armv6l` wheel |
| --- | --- | --- |
| 2.4.0 | 2026-06-22 16:16 | x86-64 |
| 2.4.1 | 2026-06-22 19:45 | x86-64 |
| 2.5.0 | 2026-09-17 21:26 | x86-64 |

#18 merged at 2026-06-22 16:09. Two releases later the piwheels artifact is
still x86-64, so the merge did not reach it.

## Proposed direction

Suggestions, in order of how much they help:

1. **Make the sdist self-correcting.** Ship all `lib/linux_*` directories in the
   sdist and have `setup.py` (or a `build_py` hook) select by
   `platform.machine()`, so any builder produces a correct wheel. This is the
   only option that fixes piwheels without piwheels changing anything.
2. **Fail loudly.** If the selected library's ELF class does not match the
   target, raise at build or import time with a message naming
   `libtensorflowlite_c_path`, instead of a bare `wrong ELF class`.
3. **Stop publishing ARM wheels that cannot work.** If ARMv6 is out of scope —
   which the maintainer has said — do not let piwheels publish an `armv6l` tag
   for it, so the failure is "no distribution" rather than a broken binary.

A README note that `libtensorflowlite_c_path` must be supplied on platforms
without a bundled library would help users of option 3.

## Building an armv6 library

The packaging fix alone leaves armv6 with no library. A working one can be
built, and the build is more delicate than the armv7l one because Debian's
armhf toolchain targets armv7-a.

Three things are required, and each was found by a separate failure:

| Flag | Failure without it |
| --- | --- |
| `-marm` | `sorry, unimplemented: Thumb-1 'hard-float' VFP ABI` — ARMv6 Thumb is Thumb-1 and cannot use the hard-float ABI |
| `--sysroot` to a Raspbian armv6 sysroot | `SIGILL` at `dlopen`: `crtbeginS.o` contains Thumb-2 (`add.w`) in `register_tm_clones`, and libgcc's `__sync_*` helpers contain `movw`/`movt` |
| `-march=armv6k` | links, then fails to load: `undefined symbol: __sync_val_compare_and_swap_1`, `__atomic_load_8`, … |

The second is the subtle one. Every object compiled from TensorFlow source is
`Tag_CPU_arch: v6`, so the library *looks* correct, but the linked result is
`v7` because Debian's crt objects and libgcc are armv7-a. gdb on the board
showed the fault at `register_tm_clones+16`, executing `add.w` — a Thumb-2
instruction ARM1176 cannot decode.

The third is because ARM1176 is ARMv6**K**: it has `ldrexb`/`strexb`/
`ldrexd`/`strexd`, but `-march=armv6` does not enable them, so GCC emits
libcalls that Raspbian's armv6 libgcc does not ship.

The sysroot also sets the glibc floor. Building against trixie gives
`GLIBC_2.38` / `GLIBCXX_3.4.32`, which excludes Raspbian bookworm (glibc 2.36,
GCC 12). A bookworm sysroot gives `GLIBC_2.36` / `GLIBCXX_3.4.30`, so the
library runs on bookworm and newer — the same intent as `linux_armv7l`, which
targets `GLIBC_2.34`.

## Local implementation (not filed)

A fork branch implements options 1 and 2, plus the README note from option 3,
and adds a `linux_armv6l` library:
[`Joldiges/pymicro-wakeword` `fix/sdist-platform-library`](https://github.com/Joldiges/pymicro-wakeword/tree/fix/sdist-platform-library).
**No pull request was opened** — James asked for the branch only.

What it changes:

| File | Change |
| --- | --- |
| `MANIFEST.in` | Ships every `lib/<platform>/`; `prune pymicro_wakeword/lib` removes the stale default |
| `setup.py` | `target_platform()` and `select_library()`; a `build_py` subclass copies the right library before package data is collected; `armv6l` maps to `linux_armv6l` |
| `pymicro_wakeword/wakeword.py` | `get_platform()` maps `armv6l` to `linux_armv6l` instead of the armv7l library; `CDLL` failures name the path and architecture |
| `script/copy_lib`, `script/package` | Same `armv6l` mapping, so the release scripts cannot disagree |
| `lib/linux_armv6l/` | TFLite C v2.17.1 for ARM1176JZF-S, plus a `SOURCE` file |
| `script/build-tflite-armv6.sh`, `script/make-armv6-sysroot.sh` | The reproducible cross-build |
| `tests/test_platform.py` | The mapping, the copy, the stale-default replacement, and both failure paths |
| `README.md`, `CHANGELOG.md` | Supported platforms, the `libtensorflowlite_c_path` escape hatch, an `Unreleased` entry |

Verified by building from the sdist three ways: natively on x86-64 (x86-64
library), with `platform.machine()` faked to `armv7l` (ARMv7 library), and to
`armv6l` (ARMv6 library). The armv6 library was then loaded on a Pi Zero W Rev
1.1: `TfLiteVersion()` reports 2.17.1, and it scores the bundled models
identically to the 2.14.0 build it replaces.

The sdist grows from 2.1 MB to 8.5 MB because it now carries all five
libraries. That is the cost of a self-correcting sdist; the alternative is a
build-time download, which needs network access a builder may not have.

## What is still missing before filing

- Decide the framing. The packaging defect (option 1) is a real bug that also
  affects ARMv7 and is worth an issue. ARMv6 *support* is a policy question the
  maintainer has already answered twice, so it should not be the headline. The
  armv6 library now exists and is verified, which changes the ask from "please
  support armv6" to "here is a working library, if you want it".
- Confirm the repository location for `pyopen-wakeword`; the package is on PyPI
  but `OHF-Voice/pyopen-wakeword` did not resolve in a repository search, so the
  identical-file claim is attributed to the package rather than a repo.
- Decide whether to comment on #13 (same symptom, closed) or open a new issue
  scoped to the sdist build path. A comment risks being read as a re-litigation
  of a closed report; a new issue with the sdist evidence is cleaner.

## History

- 2026-11-16: found during Pi Zero W bring-up. Artifacts inspected, root cause
  identified. Initial draft claimed "not already reported" — **wrong**, and
  corrected the same day after a proper search of closed issues and PRs.
- 2026-11-16: version range verified by downloading all eight piwheels releases
  (2.0.0–2.5.0) and reading each `.so` header. All x86-64.
- 2026-11-16: upstream history established — #13 (aarch64, closed
  `not_planned`), #2 (ARMv7 request, "no plans for 32-bit ARM"), #18/#19
  (armv7l support merged, ARMv7+NEON only), LVA #158 (closed `completed`, with
  an `arm32` branch). State `evidenced`, not filed.
- 2026-11-16: a working armv6 library was built and verified on a Pi Zero W.
  Three failures were needed to get there: Thumb-1 hard-float (fixed with
  `-marm`), SIGILL from Debian's armv7 crt objects and libgcc (fixed with a
  Raspbian armv6 sysroot), and missing `__sync_*`/`__atomic_*` libcalls (fixed
  with `-march=armv6k`). The bookworm sysroot keeps the glibc floor at 2.34,
  matching `linux_armv7l`. Added to the fork branch as a second commit.
- 2026-11-16: checked whether #18 already fixed it. It did not: it corrected
  the project's own wheel build and the git-checkout fallback, but
  `from_config()` prefers `pymicro_wakeword/lib/`, which the sdist always fills
  with the x86-64 default, so `get_platform()` is dead code in an installed
  wheel. Confirmed against 2.4.1 and 2.5.0, both released after the merge and
  both still x86-64 on piwheels.
- 2026-11-16: fork branch `fix/sdist-platform-library` pushed to
  `Joldiges/pymicro-wakeword` (commit `4d0e8aa`), implementing the sdist fix and
  the loud failure. No pull request opened, per James's instruction. State stays
  `evidenced`; the branch is a proposal, not an accepted fix.
