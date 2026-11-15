# Lab Pi 5: voice satellite and Sendspin player result

**Device-tested, single specimen, 2026-11-15 UTC.** Linux Voice Assistant runs on
the lab Pi 5 as a Home Assistant satellite, and a Sendspin player on the same Pi
plays music server-side. Two upstream projects, both pinned to released versions,
both installed without a container except where upstream requires one.

Read with [the audio bring-up result](2026-11-15-pi5-respeaker-v2-audio.md): the
card, overlay and mixer findings there are the foundation for this. The scripts
are in [tools/device/lab-pi5/](../../../tools/device/lab-pi5/README.md).

| Item | Value |
| --- | --- |
| Board | Raspberry Pi 5 Model B Rev 1.0, 4 GB |
| OS | Debian 13 (trixie), Raspberry Pi OS Lite 64-bit, Python 3.13.5 |
| Audio HAT | ReSpeaker 2-Mics Pi HAT v2.0 (TLV320AIC3104) |
| Audio server | PipeWire 1.4.2 + WirePlumber, user services, clock pinned to 48 kHz |
| Satellite | linux-voice-assistant `v1.1.18`, as `linux-voice-assistant.service` (user) |
| Player | `sendspin` 9.1.0 CLI, daemon mode, as `sendspin.service` (user) |
| Music server | Household Music Assistant 2.11.0.dev2026111103 (HA app on the HA host) |

## What works, with the evidence for each claim

| Claim | Evidence |
| --- | --- |
| PipeWire exposes the HAT as one sink and one source named `alsa_*platform-soc_107c000000_sound.stereo-fallback` | `pactl list short sinks/sources`, both present after a reboot |
| Audio survives a 16 kHz voice-capture stream and 44.1 kHz music at the same time | PipeWire is pinned to 48 kHz; both services ran concurrently |
| The HAT plays and captures through PipeWire | `12-loopback.sh`: 1 kHz tone → capture max −12.4 dBFS, mean −36.4 dBFS, no clipping |
| linux-voice-assistant starts, listens and serves the ESPHome API | `Server started (host=192.168.0.8, port=6053)`; an established TCP session from the HA host (192.168.0.61) |
| Home Assistant accepted the satellite | HA connected, and LVA logged syncing its wake-word and stop-word entities to Home Assistant |
| Music Assistant sees the satellite as a player | MA log: `Setting active output protocol on Debra Lab to Sendspin` |
| Sendspin carries audio from a server to the HAT | `Stream started with codec flac`, `Audio format: flac 44100Hz/24-bit/2ch`, `Stream STARTED`; capture during playback peaked at −12.5 dBFS |
| The player reconnects after reboot | After a cold boot, MA log: `Admitted server 'Music Assistant (d5369777-music-assistant-nightly)'` |
| Wake-word detection by voice | **not tested.** Nobody spoke to it. The audio path to it is measured; the detector is not |

## Traps worth remembering

1. **`symmetric_rate = 1`.** The codec cannot capture at 16 kHz while playing
   44.1 kHz. A single 48 kHz PipeWire clock is what makes a voice satellite and a
   music player coexist on one card.
2. **The driver's capture default clips.** `PGA Capture Volume` defaults to
   +16 dB; 12 dB (raw `24`) with AGC off is the working level here.
3. **Mixer control names are not the ones in older guides.** This kernel exposes
   `PGA Capture Volume`, `PCM Playback Volume`, `HP DAC Playback Volume`,
   `Left PGA Mixer Line1L Switch` … and `amixer sset` fails on several of them
   because they are capture controls or because the simple name differs. Use
   `amixer cset name='…'`. `amixer sset PGA 24` returns `Invalid command!`.
4. **A codec at −23.5 dB plus a software volume is silent.** Set the codec to
   unity and let PipeWire own the loudness.
5. **Two Sendspin servers collide on port 8927.** Music Assistant's server
   binds 8927; a default `sendspin daemon` exits when it cannot. The player here
   listens on 8928.
6. **`libportaudio2` is a hard runtime dependency** of the Sendspin CLI that its
   guided installer installs and a manual `uv tool install` does not. Without it
   the daemon exits with `PortAudio library not found`.
7. **systemd reads `%` in `ExecStart` as a specifier.** A unit containing
   `printf "%s\n"` fails with "Unit configuration has fatal error"; the sampler
   here is a small script instead of an inline shell.
8. **`Environment=CLIENT_NAME=Debra Lab` loses the second word.** systemd splits
   it into two assignments. Quote the whole assignment.
9. **Music Assistant's first run has no passwordless path.** `/setup` creates the
   admin account over HTTP; unauthenticated `/api` returns 503 `Setup required`.
   `/api` is JSON-RPC (`POST` with `{command, args}`), not REST — every REST-style
   path returns 404.
10. **`player_queues/play_media` rejects a display name.** It needs a URI
    (`builtin://radio/https://…`); a friendly name produces
    `MediaNotFoundError: No playable items found`.
11. **Docker is not the only place Music Assistant lives.** This HA instance runs
    it as an app, visible on port 8095 of the HA host but invisible to container
    listings elsewhere. Checking "no MA container on the NAS" was not evidence of
    "no Music Assistant".

## Power: this device browns out

The Pi reset twice inside three minutes during this work, and the operator saw
"undervoltage detected" at boot. `vcgencmd get_throttled` reads `0x0` when idle,
so the fault is a sag under load, not a continuous under-voltage.

Mitigations applied, and their limits:

| Mitigation | Effect |
| --- | --- |
| Persistent journal (`/var/log/journal`) | Keeps the evidence that a reset previously erased |
| `debra-powerwatch.timer` | Samples `get_throttled` 20 s after boot and every 5 min into `/var/log/debra-power.log` |
| CPU capped at 1.5 GHz, `powersave` governor | Removes the top-end current spike |
| Docker disabled at boot | No container runtime competing for current and memory |

**None of this fixes a marginal supply.** The likely fix is a supply rated 5V/5A
with USB-C PD (the official 27W Raspberry Pi supply) and a short, thick cable.
Until then, resets are expected and the microSD card is at risk.

## Not done

- No voice commanded end-to-end (wake word → STT → intent → TTS). The satellite is
  connected and the audio path is measured; the conversation is untested.
- The satellite's placement in Home Assistant (area, pipeline assignment, exposed
  entities) was left to the operator.
- Music Assistant here is the household instance, not a Debra component. Debra has
  no opinion yet on whether the Pi should host one; `40-music-assistant.sh` exists
  for an isolated lab server and is not enabled.
- No Pi Zero 2 W or Pi Zero W work. Nothing here is evidence for ARMv6.
- Acoustic quality, far-field pickup and echo cancellation are unmeasured.

## Next concrete action

Stand in front of the Pi, say "Okay Nabu", then ask it something. Record what the
LVA log and the HA device page show, and whether the answer is audible. That is
the one claim this result deliberately leaves open.
