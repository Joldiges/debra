# Getting started with Debra

**Development preview, 2026-11-15.** Debra is not yet a downloadable,
ready-to-use appliance. This guide explains what exists, what you can use now
and where each unfinished part fits. It is not an instruction to reflash a
working device.

## What Debra is

Debra aims to turn an assembled, prepared Pi into an affordable Home Assistant
voice **and** music device. Ordinary setup should happen on the device's website:
connect Wi-Fi, choose hardware/features, pair services and later manage updates
and recovery. SSH is a developer/recovery route, not the intended everyday UI.

Home Assistant must already work. Music Assistant is an additional music-server
requirement for the current Sendspin path, not something every HA installation
automatically includes.

```text
Microphones → Linux Voice Assistant → Home Assistant Assist
                                  ← spoken reply

Music Assistant → Sendspin receiver ─┐
Voice reply ────────────────────────┴→ PipeWire → audio HAT → speaker

Device website → selected native output's volume/mute + read-only status
```

Home Assistant's Assist pipeline chooses speech recognition (STT), the
conversation/intent handler and speech synthesis (TTS). Those are separate
choices; changing a device volume cannot repair a misheard command.
PipeWire is the device's shared audio layer. The HAT is the attached audio board
that connects the microphones and speaker. Sendspin is the prioritized music
path; Snapcast remains a planned alternative.

## Current progress

| Area | Exists now | Still TODO / not proven |
| --- | --- | --- |
| Voice and music | One [Pi 5 + ReSpeaker v2 lab device](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md) ran a wake → HA → spoken-reply loop and received Sendspin music | Reliable appliance behavior, repeatable fresh-card setup, independent music interruption and multiroom acceptance |
| Browser controls | [Native-volume prototype](../../control/web/README.md): slider preview + Apply, separate mute, device/resource/service inspection; offline and synthetic Chromium tests | Deployment not yet recorded; full configuration, enrollment and secure transport unfinished |
| Wi-Fi and identity | Requirements and [provisioning investigation](../research/2026-11-15-rpi-preseed.md) | Automatic hotspot onboarding and hardware-derived `debra-<id>` identity |
| Hardware | [Sourced comparisons](../comparisons/devices.md) and one tested lab pairing | Supported product matrix; original Pi Zero W full voice/music remains an engineering goal, not established support |
| Recovery | [Private root/boot archives](device-backup.md) were extracted and selected files matched the device | Device restoration and reusable on-target file capture/restore tooling; web rollback is fixture-tested only |
| Enclosures | [Component models, concepts, tray, case and carrier](../../models/README.md), with renders | No prints/fit tests; reconstruct James's `RPiSpeaker_v17` around the retained square speaker |

James reports that a replacement supply mostly resolved the lab instability.
That is a user report, not a new endurance test. Historical brownout reports
should not be mistaken for a current measurement or a reason to reset on every
voltage warning.

## Choose your starting point

### Newcomer: understand or choose a device

1. Start with the progress table above. There is **no Debra image, installer or
   end-to-end setup** to download — no path in this repository takes a blank
   SD card to a working Debra device.
2. If you want something working now, the closest documented route is the one
   the lab actually used, and it is **manual and upstream**: a Raspberry Pi 5
   with Raspberry Pi OS Lite 64-bit, a ReSpeaker 2-Mics HAT v2.0, PipeWire
   pinned to a 48 kHz clock, then
   [linux-voice-assistant](https://github.com/OHF-Voice/linux-voice-assistant)
   as a Home Assistant satellite and the
   [Sendspin](https://www.music-assistant.io/player-support/sendspin/) client
   for music. Prerequisites: a working Home Assistant, a working Music
   Assistant, and a Pi you are willing to configure by hand. The observations,
   pins and traps are recorded in the
   [lab result](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md) — that is
   a record of what one specimen showed, **not** a complete or verified install
   sequence: the scripts do not fully reproduce the manually corrected device,
   and it is **not** a Debra installer.
3. Read the [device comparisons](../comparisons/devices.md) and
   [music-playback comparison](../comparisons/music-playback.md) before buying
   different hardware. Those pages describe what vendors document and what one
   lab specimen showed; they are not a walkthrough, and Debra does not maintain
   other vendors' firmware.
4. Check the exact board/HAT revision, speaker, power, storage and enclosure
   before buying. Old shopping notes are [archived](../archive/readme-research-before-2026-11-15.md),
   not current prices or compatibility evidence. The roughly $40 target assumes
   some parts are already available; it is not a complete-kit quote.

### James / an existing lab-device owner

1. Do not reflash the working lab device to “start Debra.” Its manually corrected
   state is not fully reproduced by the repository scripts.
2. For browser volume, follow the
   [prototype installation/access/rollback guide](../../control/web/README.md)
   only for a named, authorized device. It requires an existing working
   PipeWire/PulseAudio session and an explicitly selected native sink.
3. The guide's hostname is a placeholder. Use the device's verified existing
   hostname or authorized IP/port; automatic `debra-1234ca.local` naming is
   **TODO**, not an address known to work today.
4. Access needs the device's private bearer key. HTTP is trusted-LAN-only;
   do not expose it to the internet, paste the key into chat or publish it.
   A successful install is not deployment verification.
5. Verify status and unchanged volume/mute first. Moving the slider previews;
   Apply or mute is a deliberate audio change. No deployment check needs a test
   tone, playback, recording or volume increase.
6. Before changing other components, read the [backup limits](device-backup.md).
   Current scope is file-based recovery, not mandatory whole-SD imaging or a
   second destination. Extractable archives alone do not prove device restore.

The browser deliberately does **not** install/restart speech/music, change
Wi-Fi, choose a fallback output, operate LEDs or restore volume on startup.
Service “active” is not proof that it is paired, connected or working end to end.

### Builder: prepare hardware or reproduce the lab

The [lab scripts](../../tools/device/lab-pi5/README.md) document a bring-up,
**not a verified build sequence**. Read their effects and linked test records
before selecting any operation; do not blindly execute scripts in numeric order.

- Bind the target to an exact board/HAT/revision and establish recovery for
  affected files before mutation.
- Use 32-bit OS on 32-bit boards and 64-bit on 64-bit boards. Pi 5 success does
  not establish original Zero W compatibility; see the
  [ARMv6 packaging findings](../research/2026-11-15-armv6-wheels.md).
- Keep Wi-Fi, pairing data, SSH keys and snapshots private. A distributable
  image must generate its own identities and host keys.
- Do not install another Music Assistant server or hardening/watchdog changes
  as an incidental part of a browser-volume installation.
- Treat CAD dimensions/clearances as evidence with limitations, not fit-tested
  instructions. Retain the existing speaker; unknown dimensions need measuring,
  not a replacement recommendation.

### Contributor: work without hardware

Read [AGENTS.md](../../AGENTS.md), the [documentation map](../README.md),
[development guide](../development.md), [AI workflow](../ai-workflow.md) and
relevant [roadmap packet](../roadmap.md). Prepared task-chain dispatch remains
closed pending F05; do not open it to bypass that gate.

Safe checks from the repository root:

```sh
python tools/taskchain.py check
python -B -m unittest discover -s tests -v
```

An optional real-browser check uses an **already-installed** Chromium, its
sandbox enabled, synthetic responses and no audio backend:

```sh
DEBRA_BROWSER_TEST=1 python -B -m unittest discover -s tests -v
```

These checks do not run device scripts or prove audio, hardware fit, ARMv6 or
device restoration. Do not execute historical `backups/*.sh` as tests: they use
destructive root-level rsync.

## What happens next

The [roadmap](../roadmap.md#browser-first-device-control) owns the backlog:
verify the browser slice on its named target; implement bounded file recovery;
advance component state/settings, interruption and three-LED profiles; continue
Zero W engineering and the original enclosure reconstruction. These are
separate tasks—missing household speech-provider details must not block unrelated
documentation or fixture-based work.
