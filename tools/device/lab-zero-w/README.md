# Lab device: original Pi Zero W (ARMv6)

Reproducible install of Linux Voice Assistant on the 1-core ARM1176 board, as
one released upstream tag plus **two pinned local workarounds**. Every pin lives
in [`pins.env`](pins.env); the hash of the ARMv6 library is checked at install
time, so a pin cannot silently drift.

This directory covers the voice runtime only. The HAT overlay, mixer levels and
speaker checks come from the
[driver note](../../../docs/notes/2026-11-16-armv6-tlv320aic3x-absent.md) and are
not repeated here, so this file does not imply an audio setup that has not been
run on the board.

## The two workarounds

| Workaround | Why it exists | Upstream | Retire when |
| --- | --- | --- | --- |
| ARMv6 `libtensorflowlite_c.so` (`21-armv6-tflite.sh`) | Every piwheels ARM wheel of `pymicro-wakeword` and `pyopen-wakeword` contains an **x86-64** library, so the engines import and then fail to load a model. The script copies a pinned ARMv6 build over both | [pymicro-wakeword#22](https://github.com/OHF-Voice/pymicro-wakeword/pull/22) | A `pymicro-wakeword` release ships `lib/linux_armv6l`. **`pyopen-wakeword` has no equivalent fix**, so that half needs its own upstream change or stays local |
| Stop-word gating (`22-stop-word-gate.sh`) | The stop model was inferred on every audio frame although it can only act while a reply, announcement or timer plays. Gating it took idle LVA from 41.9% to 30.9% of the single core | [linux-voice-assistant#526](https://github.com/OHF-Voice/linux-voice-assistant/pull/526) | A `linux-voice-assistant` release contains the gate. Then delete this script and its patch |

Dependency pins in [`constraints-armv6.txt`](constraints-armv6.txt) are a third,
smaller workaround: the newest releases of `numpy`, `av` and `zeroconf` have no
`armv6l` wheel. Those retire when piwheels publishes wheels, which is not
tracked by a PR.

## Install

Everything runs as the user that owns the PipeWire session; nothing here needs
root.

```sh
cd tools/device/lab-zero-w
./20-lva.sh              # clone v1.1.18, build, apply both workarounds, enable the service
```

The clone, build and virtualenv are skipped on a second run; the two workaround
steps are re-run and are idempotent.

## Verify

```sh
systemctl --user is-active linux-voice-assistant
readelf -h ~/linux-voice-assistant/.venv/lib/python3*/site-packages/pymicro_wakeword/lib/libtensorflowlite_c.so \
  | grep Machine                     # expect: ARM
git -C ~/linux-voice-assistant diff --stat   # expect: one file, from the patch only
```

A functional check needs the speaker and microphone: play a positive wake-word
clip through the HAT and look for `Detected wake word` in `~/lab/lva.log`, then
play a "stop" clip during the reply and look for `Stop word detected`.

## Revert

The patch is one file:

```sh
git -C ~/linux-voice-assistant checkout -- linux_voice_assistant/__main__.py
systemctl --user restart linux-voice-assistant
```

The library replacement is overwritten by `script/setup` the next time the
virtualenv is rebuilt.

## Migrating to the upstream releases

The goal is an unmodified upstream install. The steps, in order:

1. **MicroWakeWord**: when `pymicro-wakeword` ships `lib/linux_armv6l` and
   piwheels serves that wheel, drop `21-armv6-tflite.sh` for that package and
   install from the release instead of copying a library.
2. **pyopen-wakeword**: this needs its own upstream change. Until then, keep the
   copy for that package only, and say so rather than claiming the runtime is
   clean.
3. **LVA**: when a release contains the stop-word gate, delete
   `22-stop-word-gate.sh` and `patches/`, and pin the release tag in `pins.env`.
4. **Dependency pins**: re-check `constraints-armv6.txt` whenever the interpreter
   or Raspberry Pi OS release changes; drop a pin once a wheel exists.

`pins.env` records the exact commits, so a migration is a diff of that file plus
the deletion of one script and one patch.
