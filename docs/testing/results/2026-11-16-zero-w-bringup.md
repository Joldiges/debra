# Pi Zero W + ReSpeaker 2-Mics HAT v2: bring-up result

**Device-tested, single specimen, 2026-11-16.** First evidence that Debra's
software stack runs on the original Pi Zero W (ARMv6). One board, one HAT. It
says nothing about a second specimen, long-run stability, or acoustic quality.

| Item | Value |
| --- | --- |
| Board | Raspberry Pi Zero W Rev 1.1, BCM2835, ARMv6 (ARM1176), serial `bcf943dc` |
| OS | Raspbian GNU/Linux 13 (trixie), 32-bit |
| Kernel | `6.18.50+rpt-rpi-v6` |
| Python | CPython 3.13.5, pip 25.1.1 |
| RAM | 426 MB usable; zram 426 MB (lz4) + 256 MB swapfile at priority −2 |
| HAT | ReSpeaker 2-Mics Pi HAT **v2.0**, TLV320AIC3104 at I²C **0x18** |
| Hostname | `debra-f943dc` (hardware-derived from the serial) |
| Card | `seeed2micvoicec`, ALSA card 0 |

## What had to be built, and why

Three things were missing on this board that exist on the Pi 5:

1. **The codec driver.** `CONFIG_SND_SOC_TLV320AIC3X_I2C is not set` in the
   armv6 kernel, while the arm64 Pi 5 kernel has it `=m`. Built
   `snd-soc-tlv320aic3x.ko` and `snd-soc-tlv320aic3x-i2c.ko` out-of-tree against
   the installed headers in **75 s natively on the board**. See
   [the driver note](../../notes/2026-11-16-armv6-tlv320aic3x-absent.md).
2. **The device-tree overlay.** The image ships `wm8960-soundcard.dtbo`, which is
   the **v1** board. Compiled Seeed's DT-only `respeaker-2mic-v2_0-overlay.dts`
   with `dtc -@`; the result is SHA-256 `ff25ac56…`, **identical** to the Pi 5
   build, so the overlay is bit-reproducible across architectures.
3. **An ARMv6 TensorFlow Lite C runtime.** Both wake-word wheels ship an x86-64
   `libtensorflowlite_c.so` even when tagged `linux_armv6l`. The retained
   historical binary from Git history (`90a4c19:legacy/raspi0/…`) loads and runs.
   The packaging defect and the existing upstream reports are recorded in
   [the upstream report](../../upstream/2026-11-16-pymicro-wakeword-armv6-elf.md).

## Evidence

### HAT identification

```
$ i2cdetect -y 1
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
10: -- -- -- -- -- -- -- -- 18 -- -- -- -- -- -- --
```

0x18 is the TLV320AIC3104 (v2.0). Nothing answers at 0x1a, which is where a v1
WM8960 would be. This is decisive between the two revisions.

### Audio

`tools/audio_selftest.py seeed2micvoicec`, unmodified from the Pi 5 run:

| Measurement | Left | Right |
| --- | --- | --- |
| 1 kHz amplitude before playback | −71.7 dBFS | — |
| 1 kHz amplitude during playback | −48.4 dBFS | −47.5 dBFS |
| 1 kHz amplitude after playback | −113.4 dBFS | — |
| Clipping runs during playback | 0 | 0 |

A 23 dB rise that stops when playback stops: a real speaker→air→microphone path.
The Pi 5 measured 41 dB on the same test; the difference is not explained here
(different speaker, different gain staging, or both).

`silence_clean` was reported false. The cause is a **213 ms full-scale DC burst
at the very start of the capture**, which appears only when the capture follows a
mixer change, not on every stream start (three consecutive plain `arecord` runs
showed no such run). It is the same class as the Pi 5's "recording start
transient", but longer. Any capture path should discard the first ~250 ms.

### Wake word

`pymicro-wakeword` 2.5.0 + `pymicro-features` 2.0.2, both `linux_armv6l` wheels,
with an ARMv6 TFLite library supplied explicitly. The library is now a
TensorFlow Lite C v2.17.1 build for ARM1176JZF-S, cross-compiled against a
Raspbian bookworm armv6 sysroot; see
[the upstream report](../../upstream/2026-11-16-pymicro-wakeword-armv6-elf.md)
for why the build needs `-marm`, `-march=armv6k` and a Raspbian sysroot. It
scores identically to the 2.14.0 binary it replaced.

| Model | Input | Max probability | Result |
| --- | --- | --- | --- |
| `okay_nabu` | espeak-ng "okay nabu", en-us+m3 @190 wpm | 0.8609 | **DETECTED** |
| `okay_nabu` | same phrase repeated 4× | 0.8984 | **DETECTED** |
| `alexa` | espeak-ng "alexa" | 0.8836 | **DETECTED** |
| `hey_jarvis` | espeak-ng "hey jarvis" | 0.0000 | not detected |
| `hey_mycroft` | espeak-ng "hey mycroft" | 0.0148 | not detected |

Realtime factor for continuous scoring: **2.2–2.8×** (69–122 frames in
0.32–0.57 s). The board keeps up with 16 kHz realtime with headroom.

The two models that did not fire are not evidence of a fault: espeak-ng is
synthetic speech and these models are trained on recorded voices. The two that
did fire show the pipeline is sound.

### Identity

`hostname_from_serial("00000000bcf943dc")` → `debra-f943dc`, applied with
Debra's own `Nmcli.set_hostname()` (hostnamectl + `/etc/hosts` loopback alias +
avahi restart). `hostname -f` resolves, so `sudo` does not warn.

The image's cloud-init seed still carries `hostname: debra-lab` and
`manage_etc_hosts: true`, which rewrites `/etc/hosts` on every boot. Neutralised
with `/etc/cloud/cloud.cfg.d/99-debra-identity.cfg`
(`preserve_hostname: true`, `manage_etc_hosts: false`).

### Dashboard

`control/web` installed as a user service, `--bind 0.0.0.0 --port 8787
--auth key`, with `loginctl enable-linger` so it survives logout. Serves
`http://debra-f943dc.local:8787/` (HTTP 200) and reports the live sink:

```
audio: {"available": true, "sink": "alsa_output.platform-soc_sound.stereo-fallback",
        "percent": 65, "muted": false}
```

`detected_hat` is `null`: the Setup card's HAT row reads the HAT EEPROM, and
Seeed HATs do not have one. That is the documented "family match, not
identification" limitation, not a fault.

### Linux Voice Assistant

LVA v1.1.18 installed from the pinned tag into `~/linux-voice-assistant/.venv`
with a constraints file, because `script/setup` runs an unpinned
`pip install -e .` that resolves numpy 2.5.5 and av 19 — neither has an armv6l
wheel, so both become source builds. The constraints pin numpy 2.5.4,
av 16.1.0 and zeroconf 0.151.5; every package then resolved as a wheel.

The bundled `libtensorflowlite_c.so` in both `pymicro_wakeword` and
`pyopen_wakeword` was replaced with the ARMv6 build before first start, because
LVA calls `MicroWakeWord.from_config(config_path=...)` with no library path and
the module directory is searched first.

Running as a user service, `Restart=always`, sink pinned to
`pipewire/alsa_output.platform-soc_sound.stereo-fallback`:

| Check | Result |
| --- | --- |
| Service | `active` |
| Wake models | `Loaded 1 wake models successfully`, active `okay_nabu` |
| Stop model | loaded |
| Audio input | `Opening audio input device: Built-in Audio Stereo` |
| ESPHome API | listening on `192.168.0.70:6053` |
| mDNS | `lva-b827ebac1689._esphomelib._tcp.local.` |
| Peripheral API | `ws://0.0.0.0:6055` |
| CPU / RSS | ~50% of one core, 85 MB |

**Not paired with Home Assistant.** No HA credentials exist in this checkout, and
pairing needs the HA UI. The satellite advertises and runs; it has not completed
a wake → STT → intent → reply cycle on this board.

### Sendspin

Sendspin 9.1.0 installed into a plain venv, not with `uv`: uv publishes no armv6
Linux build, so the Pi 5's `uv tool install` route is unavailable. `sendspin` has
no 32-bit ARM wheel and builds from sdist; its optional C volume extension falls
back to numpy.

| Check | Result |
| --- | --- |
| Service | `active` |
| Listening | `0.0.0.0:8928` |
| mDNS | advertising `_sendspin._tcp.local.` |
| Music Assistant | `Admitted server 'Music Assistant (…-nightly)'` |
| Audio formats | 32 detected (FLAC + PCM) |
| CPU / RSS | ~61% of one core, 47 MB |

The daemon takes roughly 80 s to reach "listening" on this board, almost all of
it module import. `sendspin --version` does not print a version; it starts the
daemon, so a version check must not be used as a readiness probe.

### Baseline

`control/setup/baseline.py` `capture()` wrote
`/var/lib/debra/setup/baseline/baseline-20261116T065749Z.tar.gz` (9069 bytes,
6 files) and `verified()` returns the manifest, so the archive hashes and opens
as a gzip tar.

The first capture on this device held only 5 files and **no Wi-Fi credentials**.
The cause was a real gap in `CAPTURE`, not a capture failure: Raspberry Pi OS
provisions Wi-Fi from a cloud-init seed on the boot partition, so
`etc/NetworkManager/system-connections` is empty and the live profile is a tmpfs
copy under `/run` that is regenerated at boot. `CAPTURE` now also includes
`etc/netplan`, `boot/firmware/network-config` and `boot/network-config`, and the
re-capture contains the access-point block and password. `boot/network-config`
is recorded as missing, which is correct for the Bookworm-and-later layout.

The archive still does not contain `boot/firmware/user-data`, which holds the
user password hash and SSH key. That is deliberate: the baseline is a
configuration baseline, and the network is the part that cannot be recovered
without it.

## What this does not prove

- A second Zero W, or any other ARMv6 board.
- Long-run stability, thermal behaviour, or behaviour under sustained load.
- Acoustic quality, microphone spacing, or which physical mic feeds which channel.
- That the 2.17.1 TFLite library handles every operator in every model.
- That the out-of-tree modules survive a kernel upgrade (they will not; they
  need rebuilding).
- Anything about the Pi 5 or Zero 2 W, which were not touched.
- That LVA completes a voice cycle. It is unpaired, so wake → STT → intent →
  reply has not run on this board.
- That the wake word is reliable for a human voice. The detections above used
  synthetic speech; see the wake-word section.
- That the two services coexist under sustained load. They were measured
  separately, and together they use roughly one core of the single available
  one.

## Reproducing

The build steps are in
[the driver note](../../notes/2026-11-16-armv6-tlv320aic3x-absent.md) and
[the dependency note](../../notes/2026-11-16-armv6-dependency-findings.md).
Device scripts live under `tools/device/`; the Pi 5 versions were used as the
starting point and adapted for the sink name and the missing `uv`.
