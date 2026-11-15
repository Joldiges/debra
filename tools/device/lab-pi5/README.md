# Lab Pi 5 device build

Scripts that turn a fresh 64-bit Raspberry Pi OS install into the Debra audio
lab device: PipeWire, a correctly-mixed ReSpeaker 2-Mics Pi HAT, Linux Voice
Assistant as a Home Assistant satellite, a Sendspin player, and Music Assistant
as the lab's music source.

**These are device scripts.** They run on the Pi as the `debra` user, not on the
host, and they change system packages, systemd user units and Docker state.
None of them is exercised by `python -B -m unittest discover -s tests`.

Run in numeric order, from the checkout copied to the device or from the
matching files in `~/lab/`:

| Script | What it does | Verified |
| --- | --- | --- |
| `10-audio.sh` | Enables PipeWire + WirePlumber for the user, pins the graph to 48 kHz | yes, 2026-11-15 |
| `11-mixer.sh` | Codec mixer: 12 dB capture PGA, AGC off, Line1 routing, unity playback gains, `alsactl store` | yes |
| `12-loopback.sh` | Plays a 1 kHz tone while recording from the HAT; prints capture levels | yes |
| `20-lva.sh` | Clones linux-voice-assistant at a pinned tag, builds its venv, installs the user unit | yes |
| `30-sendspin.sh` | Installs the Sendspin CLI, writes its settings, installs the user unit | yes |
| `40-music-assistant.sh` | Installs Docker and runs the Music Assistant server container on host networking | yes |
| `50-power-watch.sh` | Records the Pi power/throttle flags on a timer | yes |
| `51-power-cap.sh` | Caps the CPU/GPU clock to lower the peak draw on a marginal supply | yes |
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
- **Unity codec, volume in software.** Playback DAC and output stages are set to
  0 dB and loudness is controlled by the PipeWire sink. Mixing codec gain with
  software gain is what made the first test tone inaudible.
- **Two outputs, both live.** The HAT's 3.5 mm jack (HPLOUT/HPROUT) and its JST
  speaker connector (Line Out → TPA2005D1) are both enabled, so either works.
  Measured 2026-11-15 with PipeWire stopped and a 1 kHz tone played to each tap in
  turn: the speaker appears on **Line** (−21 dBFS at the microphone), and HP and
  HPCOM are silent with nothing plugged into the jack. So the speaker path is
  `Line DAC` → `Line`, and **a zero `Line DAC` is silence with every service
  green** — the state the device was found in. `HP DAC` at 0 dB is for headphones
  and is not what makes the speaker work.
- **The stored mixer can drift from the script.** `alsactl store` saves whatever
  is current, so a state saved before `11-mixer.sh` ran survives reboots. Re-run
  the script after any manual `amixer` work, and check `Line DAC` first when the
  device goes quiet.

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

None of these fix a sagging 5 V rail. They turn an unexplained hang into a
reboot and a silent device into a log line.

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
