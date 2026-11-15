# Lab Pi 5 device build

Scripts recording the bring-up of one Pi 5 + ReSpeaker 2-Mics Pi HAT v2 lab
device: PipeWire, Linux Voice Assistant, Sendspin and a lab Music Assistant
server. **Reference material, not a verified fresh-card installer.** Some scripts
were written after manual bring-up; replaying them has not demonstrated a
reproducible device.

**These are device scripts.** They run on the Pi as the `debra` user, not on the
host, and they change system packages, systemd user units and Docker state.
None of them is exercised by `python -B -m unittest discover -s tests`.

The numeric names record the intended sequence, **not a command to run the
whole directory**. Review each script against a named target and a bounded
recovery plan. `12-loopback.sh` plays and records audio: it is excluded from
silent investigation, deployment checks and ordinary host tests. Do not install
another Music Assistant server merely because its reference script exists.
The “Verified” column describes historical lab use, not fresh-card replay:

| Script | What it does | Verified |
| --- | --- | --- |
| `10-audio.sh` | Enables PipeWire + WirePlumber for the user, pins the graph to 48 kHz | yes, 2026-11-15 |
| `11-mixer.sh` | Codec mixer: 12 dB capture PGA, AGC off, Line1 routing, recorded playback register values, `alsactl store` | yes |
| `12-loopback.sh` | Plays a 1 kHz tone while recording from the HAT; prints capture levels | yes |
| `20-lva.sh` | Clones linux-voice-assistant at a pinned tag, builds its venv, installs the user unit | yes |
| `30-sendspin.sh` | Installs the Sendspin CLI, writes its settings, installs the user unit | yes |
| `40-music-assistant.sh` | Installs Docker and runs the Music Assistant server container on host networking | yes |
| `50-power-watch.sh` | Records the Pi power/throttle flags on a timer | yes |
| `51-power-cap.sh` | Caps CPU frequency to 1.5 GHz and pins the `powersave` governor; also keeps the journal across boots (restarts `systemd-journald`) and disables `docker.service`/`docker.socket` startup. It sets no GPU clock. It is mitigation, not a supply fix | yes |
| `60-watchdog.sh` | Persistent journal, `hung_task_panic`, explicit hardware watchdog | yes, 2026-11-15 |
| `61-health.sh` | Installs `debra-health` and its 2-minute timer: tests the audio path, not just the service list | yes, 2026-11-15 |

## Why the audio is configured this way

- **One clock rate.** The TLV320AIC3104 in the HAT has `symmetric_rate = 1`, so
  capture and playback must share a rate. Pinning PipeWire to 48 kHz lets voice
  capture at 16 kHz and music at 44.1/48 kHz be resampled in the graph instead of
  fighting over the hardware.
- **Capture gain.** The kernel driver defaults the capture PGA to +16 dB, which
  clips the first loud word. 12 dB (`24`) with AGC off was the level used in the
  first device test.
- **Native volume after a working mixer baseline.** The speaker worked with
  `Line DAC` 106 and `Line` 3; a zero `Line DAC` caused silence even with services
  running. Ordinary volume belongs at the selected PipeWire sink, not a guessed
  codec gain. Percent is not acoustic loudness or a safety limit.
- **Speaker tested; headphone path unverified.** Historical tap tests support
  `Line DAC` → `Line` → amplifier → speaker. Silence at the on-board microphone
  with nothing plugged into the jack does not prove the jack's routing or that
  headphones work. `HP DAC` was recorded as **raw value 0**, not established as
  “0 dB.” Read the [audio corrections](../../../docs/notes/2026-11-15-audio-and-enclosure-corrections.md)
  before interpreting historical tone measurements.
- **The stored mixer can drift from the script.** `alsactl store` saves whatever
  is current, so a state saved before a correction can survive reboots. Inspect
  the current mixer and saved state first; do not replay a script that may
  overwrite deliberate user changes.

## Watchdogs

Three layers, because they catch different failures. They exist because on
2026-11-15 the Pi answered ping, accepted TCP on port 22, and never sent an SSH
banner for five minutes: the kernel was healthy, PID 1 was healthy, and one
process was stuck in uninterruptible sleep. The hardware watchdog never fired
because systemd kept petting it.

| Layer | Catches | Where |
| --- | --- | --- |
| Hardware watchdog, 60 s | dead or wedged kernel or PID 1 | `/etc/systemd/system.conf.d/50-debra-watchdog.conf` |
| `hung_task_panic`, 120 s | one process stuck in D state → panic → reboot after 10 s | `/etc/sysctl.d/60-debra-watchdog.conf` |
| `debra-health` timer, 2 min | "running but silent": dead user service, missing or muted sink, zero line gain | `~/.local/bin/debra-health` |
| `Restart=always` | a service that exits, cleanly or not | the two user units |

These are historical mitigations, not proof of reliability or default Debra
policy. James reports the replacement supply mostly resolved the instability.
An undervoltage warning alone must not cause a reboot/reset; further Pi-5-only
hardening is low priority. See the [current recovery scope](../../../docs/guides/device-backup.md).

## Known limits

- The `debra` user must keep **lingering enabled** (`loginctl enable-linger
  debra`), because PipeWire, LVA and Sendspin are user services.
- Port 8927 on this host belongs to Music Assistant's Sendspin server, so the
  player listens on 8928. A default `sendspin daemon` exits if both use 8927.
- Music Assistant's first run has no passwordless path: `/setup` creates the
  admin account over HTTP. Credentials belong in `.local/`, never in Git.
- Music Assistant discovers players on the whole network. The Chromecast, AirPlay
  and DLNA providers were removed on this instance so the lab server cannot play
  on household speakers; only the Sendspin player is intended here.
