# Pi 5 + ReSpeaker 2-Mics Pi HAT v2.0: audio bring-up result

**Device-tested, single specimen, 2026-11-15 UTC.** First evidence that Debra's
lab hardware produces and captures audio on Raspberry Pi OS Trixie with a
stock kernel, and the first repeatable self-test. This is one Pi 5 Model B
Rev 1.0 with one HAT; it says nothing about Pi Zero W, other revisions, or
acoustic quality.

| Item | Value |
| --- | --- |
| Board | Raspberry Pi 5 Model B Rev 1.0, 4 GB |
| OS | Debian 13 (trixie), Raspberry Pi OS Lite 64-bit, image dated 2026-10-06 |
| Kernel | `6.18.50+rpt-rpi-2712` (package `1:6.18.50-1+rpt1`) |
| HAT | ReSpeaker 2-Mics Pi HAT v2.0, TLV320AIC3104 at I²C address 0x18 |
| Hostname | `debra-3c6b3f` (hardware-derived; see the public guide for the scheme) |
| Card | `seeed2micvoicec`, playback and capture device 0, one substream each |

## What made it work

The kernel **already ships** the codec driver. This contradicts the
defconfig-only analysis that reached the coordinator before the device was
reachable:

```
$ grep -E 'TLV320AIC3X|WM8960' /boot/config-6.18.50+rpt-rpi-2712
CONFIG_SND_SOC_TLV320AIC3X=m
CONFIG_SND_SOC_TLV320AIC3X_I2C=m
CONFIG_SND_SOC_WM8960=m
$ find /lib/modules/6.18.50+rpt-rpi-2712 -name '*tlv320*'
.../kernel/sound/soc/codecs/snd-soc-tlv320aic3x.ko.xz
.../kernel/sound/soc/codecs/snd-soc-tlv320aic3x-i2c.ko.xz
```

So no out-of-tree build, DKMS package or kernel change was needed. Only a
device-tree overlay was missing, because the Pi kernel ships
`wm8960-soundcard.dtbo` but no ReSpeaker overlay. The overlay is Seeed's
DT-only `respeaker-2mic-v2_0-overlay.dts`
(`Seeed-Studio/seeed-linux-dtoverlays`, `overlays/rpi/`, MIT), compiled with
the `dtc` already installed on the image:

| Artefact | SHA-256 |
| --- | --- |
| `respeaker-2mic-v2_0-overlay.dts` as fetched 2026-11-15 | `32fad2570bc9e864d19365137a64c28614a1b7be9d816d78bf40043d73d0782c` |
| `respeaker-2mic-v2_0.dtbo` built from it, installed at `/boot/firmware/overlays/` | `ff25ac5619114dae165377dc15139719a17fb8ab0973ecdf892b58ba30037253` |

`dtoverlay=respeaker-2mic-v2_0` was appended under `[all]` in
`/boot/firmware/config.txt` (previous file backed up to `~/debra-backup/`).
The overlay applied cleanly at runtime with `dtoverlay` **and** survived a
reboot, after which the card appears at boot as card 0 without any manual
`modprobe`. The overlay's `compatible` list does not name `brcm,bcm2712`; the
firmware applied it on Pi 5 anyway, but that mismatch is worth an upstream
report.

## Evidence

Sanitised excerpts; full captures stay in the untracked `.local/` tree.

```
$ cat /proc/asound/cards
 0 [seeed2micvoicec]: simple-card - seeed2micvoicec
 1 [vc4hdmi0       ]: vc4-hdmi - vc4-hdmi-0
 2 [vc4hdmi1       ]: vc4-hdmi - vc4-hdmi-1
```

```
[    4.142083] tlv320aic3x 1-0018: supply IOVDD not found, using dummy regulator
[    4.142185] tlv320aic3x 1-0018: supply DVDD not found, using dummy regulator
[    4.142211] tlv320aic3x 1-0018: supply AVDD not found, using dummy regulator
[    4.142225] tlv320aic3x 1-0018: supply DRVDD not found, using dummy regulator
[    4.142237] tlv320aic3x 1-0018: Invalid supply voltage(s) AVDD: -22, DVDD: -22
```

The regulator messages are expected for a DT-only overlay that does not
declare supplies; the codec probes and works. They are not a fault.

Self-test run (kernel `6.18.50+rpt-rpi-2712`, mixer `PGA` +12 dB, `AGC` off,
`PCM` 0 dB, `HP DAC` 0 dB, `HP` +5 dB, 48 kHz stereo, 1 kHz tone at −20 dBFS
played while recording):

| Measurement | Left | Right |
| --- | --- | --- |
| Capture RMS, 3 s room noise | −21.0 dBFS | −18.4 dBFS |
| Capture peak, same window, clipping runs | −4.3 dBFS, 0 | −2.3 dBFS, 0 |
| 1 kHz amplitude before playback | −81.5 dBFS | — |
| 1 kHz amplitude during playback | −40.3 dBFS | −36.3 dBFS |
| 1 kHz amplitude after playback | −89.2 dBFS | — |
| Clipping runs during playback | 0 | 0 |

A 41 dB rise in the 1 kHz bin that stops when playback stops. **James
confirmed by ear, in the same session, that the tone was audible from the
speaker**, so this is an acoustic speaker→air→microphone path and not
electrical crosstalk inside the codec.

## Traps found on the device

- **The capture PGA defaults to +16 dB and clips immediately.** The first
  capture at factory defaults measured RMS −6.9 dBFS with a maximum clipping
  run of 28 469 consecutive samples. At 0 dB the same room measured −29.8 dBFS
  with no clipping. Any Debra capture path must set `PGA` explicitly; do not
  trust the driver defaults.
- **Playback defaults are far below useful output**: `PCM` −33.5 dB,
  `HP DAC` −23.5 dB and `HP` at minimum made a −20 dBFS tone inaudible and
  undetectable. Unity (`PCM` 127, `HP DAC` 118) is required before judging
  "no sound".
- **`/usr/sbin` is not on the PATH of a non-login SSH session**, so `alsactl`
  appears missing while being installed. Use `/usr/sbin/alsactl` or an
  absolute path in scripts.
- **Recording start produces a transient**: one full-scale sample run in the
  first 100 ms. Measure the noise floor after about 0.5 s, not from the very
  first sample.
- `alsactl restore` prints `failed to import hw:0 use case configuration -2`.
  It is the ALSA use-case manager looking for a UCM profile, not a restore
  failure; the restore returns 0.
- Applying the overlay at runtime with `dtoverlay` emits many
  `memory leak will occur if overlay removed` warnings. Harmless, but persist
  the overlay in `config.txt` and reboot rather than leaving a runtime-applied
  state.

## What this does not prove

- Loudness, distortion, intelligibility, microphone spacing/beamforming,
  speaker-to-microphone leakage margins, or how the fan and case change them.
- Which physical microphone feeds which channel; the HAT exposes stereo
  capture but the mapping was not verified.
- `RPi.GPIO`/APA102 LED control, the user button, or Seeed's demo scripts.
- Anything about Pi Zero W, Pi Zero 2 W, or the v1.0/v1.1 HATs.
- That a music/voice stack (LVA, Sendspin, Music Assistant) works on top.

## Reproducing

`tools/audio_selftest.py` is the script used here. It saves mixer state,
applies bounded settings, records room noise, plays a synthesised 1 kHz tone
while recording, reports RMS/peak/clipping and a Goertzel 1 kHz amplitude, and
restores the mixer. It needs only `alsa-utils` and the Python standard library.

```sh
scp tools/audio_selftest.py debra@<host>:/tmp/
ssh debra@<host> 'python3 /tmp/audio_selftest.py seeed2micvoicec'
```

Author: coordinator session `openrouter/deepseek/deepseek-v4.1-flash-1017#high`.
The self-test design came from a bounded read-only worker
(`AUD02-SELFTEST`, same model family); its proposed thresholds were not
adopted unchanged, and its claim that the capture path needed numpy was wrong:
standard-library `wave`/`struct` was sufficient.
