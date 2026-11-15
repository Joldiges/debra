# Lab Pi 5: silent speaker, and a hang with no evidence

**Device-tested, single specimen, 2026-11-15 UTC.** Two faults, one root cause
between them and one that is still a suspect. Both produced the same user
experience — "it hears me and says nothing" and "it stopped working" — and
neither was a software configuration error in the usual sense.

Read with [the voice and Sendspin result](2026-11-15-lab-pi5-lva-sendspin.md);
this note corrects one assumption in it.

## Fault 1: every service healthy, no sound

| Checked | Result |
| --- | --- |
| LVA, Sendspin, PipeWire, WirePlumber | all `active` |
| Default sink | the HAT card, `stereo-fallback` |
| Sink mute / volume | not muted, 65 % (−11 dB) |
| `PCM` (the control PipeWire's volume actually drives) | 105, matching 65 % |
| `HP DAC` | **0 % = −∞ dB** |
| Wake word | detected normally |

`HP DAC` at zero looked like the answer, so it was raised to 0 dB. The device
stayed silent. That is what made the next test worth doing properly.

### Testing the paths instead of guessing

PipeWire holds the card, so `aplay` cannot open it. With the user audio services
stopped and `aplay`/`arecord` talking to `plughw` directly, a 1 kHz tone was
played to each codec output tap in turn and recorded by the HAT's own microphone:

| Tap | 1 kHz at the microphone | Verdict |
| --- | --- | --- |
| `HP` (headphone, 3.5 mm jack) | ≈ −100 dBFS, the noise floor | silent |
| `HPCOM` (composite) | ≈ −90 dBFS | silent |
| `Line` (TPA2005D1 → JST speaker) | **−21 dBFS** | **this is the speaker** |

So the speaker is on `Line`, exactly as the build README says and as the mixer
script sets it. The mixer script was not wrong; the **stored** `alsactl` state
had drifted, and a state saved before the script ran survives every reboot. The
first test tone was also malformed — a truncated WAV — which produced a false
negative that cost a round.

### The fix

| Control | Value | Meaning |
| --- | --- | --- |
| `Line DAC` | 106 | −6 dB fixed codec gain |
| `Line` | 3 | +3 dB output driver |
| `HP DAC` | 0 | headphone tap off; nothing is in the jack |
| `PCM` | follows the sink | 65 % = −11 dB |

`alsactl store` was run, and the values survived the reboot that followed: after
it, `Line DAC` read 106 and `Line` read 3 with no manual step.

**The level was set by ear, not by measurement.** The first proof of the path was
a full-scale tone and it was far too loud; the working setting is about 19 dB
below that. Comfortable loudness for speech has not been measured, and the sink
volume (the slider Home Assistant shows) is the intended user control.

## Fault 2: the board hung, and left nothing behind

At about 03:00 local the device stopped responding to SSH while remaining on the
network:

| Check | Result |
| --- | --- |
| ICMP | 0 % loss, but RTT swinging 4 ms → 263 ms on a LAN |
| TCP port 22 | **accepted** |
| SSH banner | never sent, including after a 30 s wait |
| mDNS | still resolved |

An accepted connection with no banner means sshd was listening but blocked —
almost always a process in uninterruptible sleep on storage. The kernel answered
ping because the kernel was fine.

Two things made this worse than it needed to be:

- **The hardware watchdog never fired.** systemd was already running the BCM2835
  watchdog at 60 s, but systemd pings it from PID 1, and PID 1 was healthy. A
  watchdog that proves "PID 1 is scheduled" cannot see one stuck process.
- **The journal was volatile.** Raspberry Pi OS ships `Storage=volatile` in
  `/usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf` to spare the SD
  card, so after the reboot there was exactly one boot in `journalctl` and no
  evidence of what hung.

The boot log did keep one trace: `EXT4-fs orphan cleanup on readonly fs`, which
means the previous shutdown was unclean. Combined with the documented power
fault, a brownout during a card write is the leading explanation. It is not
proven — no `throttled` bit survived, because the flag resets with the SoC.

## What was changed

| Layer | Setting | Catches |
| --- | --- | --- |
| Persistent journal | `Storage=persistent`, 64 MB cap, Pi OS drop-in masked | a hang that leaves no log |
| Kernel | `hung_task_timeout_secs=120`, `hung_task_panic=1`, `panic=10` | one process stuck in D state → reboot instead of a mystery |
| Hardware watchdog | explicit `RuntimeWatchdogSec=60s` | dead or wedged kernel / PID 1 |
| Service policy | `Restart=always` on LVA and Sendspin | a service that exits |
| `debra-health` timer | every 2 min: user services, default sink, mute, volume, **line gain** | "running but silent" |

The health check was verified by setting `Line DAC` to 0 and running it: it
logged `line output gain is 0: re-applying the known-good mixer` and restored
106. The journal was verified by `journalctl --header` reporting a path under
`/var/log/journal`.

Installed by [`60-watchdog.sh`](../../../tools/device/lab-pi5/60-watchdog.sh) and
[`61-health.sh`](../../../tools/device/lab-pi5/61-health.sh).

## What is still wrong

- **The power fault is not fixed.** James moved the Pi to a different USB port;
  that is a change of supply, not a proven one. The fix is still a 5 V/5 A USB-C
  PD supply and a short thick cable.
- **The hang may recur.** `hung_task_panic` converts it into a reboot, which is
  better than a five-minute outage but still risks the card. Repeated reboots
  after this change would be evidence the card or the rail is failing.
- **Nothing here is measured for loudness.** The gain is by ear.
- **The 3.5 mm jack is untested.** If it shares the line tap rather than the
  headphone tap, "speaker or headphones" is a volume question and not a routing
  one.
- **No backup of the card exists.** A reflash still costs the whole bring-up.

## Next concrete action

Boot it, ask it something, and judge whether the reply is comfortable. Then image
the card before running it for long, and swap the supply.
