# Lab Pi Zero 2 W device build

Scripts recording the bring-up of one **Pi Zero 2 W (aarch64, 415 MiB usable
RAM) + Seeed ReSpeaker 2-Mics Pi HAT v1 (WM8960)**: PipeWire, Linux Voice
Assistant and a Sendspin player. **Reference material, not a verified fresh-card
installer.** These scripts were replayed on one hand-built card on 2026-11-16;
that is one run, not a reproducible image.

The Pi 5 build next door ([`../lab-pi5/`](../lab-pi5/)) is the fuller reference:
it also carries the power, watchdog and health layers. This directory is
deliberately smaller because the board is smaller.

**The device is a client, not a server.** Home Assistant and Music Assistant stay
on the household server. Nothing here installs Docker or a Music Assistant
server; a Pi Zero 2 W could not usefully run one.

**These are device scripts.** They run on the Pi as the `debra` user, not on the
host, and they change system packages and systemd user units. None of them is
exercised by `python -B -m unittest discover -s tests`.

## Package prerequisites

The web installer installs no packages, so a card built by hand lacks these
until something asks for them. `00-packages.sh` records the set; **run it once
on a fresh card**:

| Package | Needed by | Why |
| --- | --- | --- |
| `git` | LVA | clone the pinned release |
| `avahi-utils` | web page discovery | `avahi-browse`; the daemon alone is not enough |
| `libportaudio2` | Sendspin | `sounddevice` exits without it |
| `libmpv2` | LVA | `python-mpv` plays announcements and music |
| `python3-venv`, `build-essential` | LVA | venv and the wake-word extension build |

This is the declaration the web and setup installers deliberately do not make.

## Scripts

The numeric names record the intended sequence, **not a command to run the whole
directory**. `11-mixer.sh` changes the codec and stores the state; review it
before replaying if the mixer has been tuned by hand.

| Script | What it does | Verified |
| --- | --- | --- |
| `00-packages.sh` | Installs the package set above | yes, 2026-11-16 |
| `10-audio.sh` | Enables PipeWire + WirePlumber for the user, pins the graph to 48 kHz | yes, 2026-11-16 |
| `11-mixer.sh` | WM8960 capture gain and routing, `alsactl store` | yes, 2026-11-16 |
| `20-lva.sh` | Clones LVA at a pinned tag, builds its venv, installs the user unit | yes, 2026-11-16 |
| `30-sendspin.sh` | Installs the Sendspin CLI via `uv`, writes settings, installs the user unit | yes, 2026-11-16 |

## Why the audio is configured this way

- **One clock rate (48 kHz).** Voice capture is 16 kHz and music is 44.1/48 kHz;
  resampling in the graph avoids the codec renegotiating mid-session.
- **Capture gain is fixed, and it was measured.** With the codec's capture PGA at
  its maximum (+30 dB, value `63`) and the ADC digital volume at 0 dB (value
  `195`), room noise in a quiet room peaks around −42 dBFS. Enabling the input
  mixer boost stage instead added roughly +30 dB and clipped on room noise alone
  (peak 17k–32k of 32 767), so it is **off**. `ADC PCM` 225 (+15 dB digital)
  also measured too hot for speech peaks.
- **The ADC high-pass filter is off.** Enabling `ADC High Pass Filter` produced a
  near-constant full-scale offset (peak 238, RMS 216 on a stereo capture) instead
  of removing DC. That is either a driver inversion or a broken control; it is
  recorded, not diagnosed.
- **ALC is off.** It would adapt to speech level, but automatic gain pumping is a
  poor match for a wake-word engine and nothing here measured it.
- **The DAC was not connected to any output.** The overlay leaves both output
  mixer PCM switches off, so the card was silent with a healthy service, a
  moving volume slider and no error anywhere. `11-mixer.sh` enables them and the
  class-D speaker stages. Measured with a 1 kHz tone at 40% sink volume recorded
  from the HAT's own microphone: output mixer off gave no tone, headphone path
  gave no tone, and the class-D speaker path gave a clear 1 kHz peak. **The
  board's speaker is on the class-D output, not the 3.5 mm jack.**
- **Microphone level is a starting point, not a tune.** The ReSpeaker 2-Mics HAT
  v1 codec is much weaker than the v2's TLV320. If Home Assistant transcribes
  poorly, try `MIC_AUTO_GAIN=1` in the LVA unit before changing the codec.

## Known limits

- **512 MiB is LVA's stated minimum and this board has 415 MiB usable.** LVA and
  Sendspin fit, but there is little headroom. Watch `free -m` before adding
  anything else; zram swap is active and is not a substitute for memory.
- The `debra` user must keep **lingering enabled** (`loginctl enable-linger
  debra`), because PipeWire, LVA and Sendspin are user services.
- **No power cap or watchdog layer here.** `51-power-cap.sh` on the Pi 5 caps a
  1.5 GHz-capable CPU; the Zero 2 W runs at 1 GHz and that script does not apply.
  The watchdog and `debra-health` layer have not been ported. A board that hangs
  will stay hung until it is power-cycled.
- **`debra-health` on the Pi 5 checks a Line DAC control this codec does not
  have.** Porting it needs WM8960-specific checks, not a copy.
- **No speaker AEC.** The HAT has no echo cancellation, so `REFACTORY_SECONDS=3`
  stops the tail of a reply starting a second run. A real echo-cancel sink is
  the fix and is not implemented.
- Port 8928 is used for Sendspin here as well, so the same settings work on both
  boards even though this one does not host Music Assistant on 8927.
