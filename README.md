# Debra

Affordable, configurable Home Assistant voice and synchronized-music devices,
with practical setup tooling and source-linked hardware/software comparisons.

**Status: development preview, 2026-11-15.** One lab Pi has run voice and music.
A browser-volume prototype and tested local tooling exist, but there is **no
supported Debra image, complete installer or ready-to-use appliance** yet.

**[Start here: getting started](docs/guides/getting-started.md)** — what works,
how the components fit, and separate paths for newcomers, existing-device owners,
builders and contributors.

## What is Debra?

Debra brings proven upstream projects together into an approachable Home Assistant
speaker: voice commands and replies, music, understandable hardware choices, and
eventually straightforward setup and recovery.

The intended starting point is **working Home Assistant plus an assembled,
prepared Pi**. Everyday configuration should use the device's website, not SSH
or Linux troubleshooting. Wi-Fi onboarding and a stable address such as
`debra-1234ca.local` are goals, not working setup instructions today.

| Piece | Role |
| --- | --- |
| Home Assistant + Linux Voice Assistant | The Pi sends speech to HA's Assist pipeline and plays its reply; HA owns most speech-provider choices |
| Music Assistant + Sendspin | A separate music server and receiver; Sendspin is the initial priority, with Snapcast retained as an alternative |
| PipeWire + audio HAT + speaker | Shared device audio; ordinary volume controls the explicitly selected native output |
| Debra browser controls | Prototype volume/mute and read-only status now; broader setup, settings and maintenance are TODO |

## Current progress

| Area | Evidence / limits |
| --- | --- |
| Voice and music | One [Pi 5 + ReSpeaker 2-Mics v2](docs/testing/results/2026-11-15-lab-pi5-lva-sendspin.md) ran wake → HA → spoken reply and Sendspin music. Not a supported hardware matrix or endurance result. |
| Browser prototype | [Selected-output volume/mute and status](control/web/README.md), with offline and synthetic Chromium tests. An **earlier** version is deployed on the lab Pi; the current candidate is not deployed and is not approved. Slider movement previews; Apply changes volume. No startup/poll/test sounds. Trusted-LAN HTTP only. |
| First-boot setup | [Device name, Wi-Fi onboarding and first baseline](control/setup/README.md), with offline tests and an installer. **This code has never run on a device**: it has raised no radio, joined no network, applied no name and captured no baseline, and there is no captive portal or access revocation. |
| Hardware/reference | [Sourced device comparisons](docs/comparisons/devices.md) and [music-path explanations](docs/comparisons/music-playback.md), not blanket compatibility or buying promises. |
| Recovery | [Private file archives verified by extraction](docs/guides/device-backup.md); actual device restoration remains unproven. On-target file recovery is the current scope, not mandatory whole-SD imaging. |
| Printable parts | [Editable CAD and renders](models/README.md). Nothing printed or fit-tested; original `RPiSpeaker_v17` reconstruction remains unfinished. |

Full original **Pi Zero W voice/music support remains an engineering goal**.
Pi 5 success does not prove ARMv6 compatibility. Pi Zero 2 W is a candidate, not
a permanent hardware lock-in. Other boards remain investigations.

### Next milestones / TODO

- Verify the browser slice and isolated rollback on its named, authorized target.
- Run the setup service on a device, then add hardware/component settings and honest
  installed/enabled/configured/running/connected/working states. Identity, Wi-Fi
  onboarding and the first baseline are written but have never touched a radio.
- Integrate selectable music duck/pause/resume, reply interruption and three-LED
  profiles without overwriting user volume or paused state.
- Demonstrate on-target file capture/restore and pinned/manual component updates.
- Continue Zero W engineering and reconstruct the original enclosure around the
  retained square speaker, with desktop/wall use and an accessible topper.

The [roadmap](docs/roadmap.md) owns dependencies and acceptance. The parts
inventory gives $59.90 for a complete new-parts build and $16.40 reused-parts
marginal cost, with $31.35 as the cheapest route that lands under $40 and $37.15
as the cheapest one on a board anyone expects to work (that board is out of
stock at the US sellers checked); those are dated estimates, not a current
complete-kit price.

## Use or contribute

| Start here | For |
| --- | --- |
| [Getting started](docs/guides/getting-started.md) | Current options, component diagram, existing-device and builder instructions |
| [Browser prototype guide](control/web/README.md) | Scoped installation, authentication, upgrade verification and rollback; developer access still required |
| [First-boot setup service](control/setup/README.md) | What the setup portal, identity and baseline code does, and exactly what is unproven |
| [Documentation map](docs/README.md) | Comparisons, research, guides, evidence and dated handoffs |
| [Project brief](docs/project-brief.md) / [roadmap](docs/roadmap.md) | Product requirements and bounded next work |
| [Development guide](docs/development.md) / [AI workflow](docs/ai-workflow.md) | Reuse-first work, private storage, ownership and separate review |
| [Task chains](docs/task-chains.md) / [model strategy](docs/ai-model-strategy.md) | Prepared worker assignments and model roles; editing dispatch remains closed pending F05 |

Safe local checks, from the repository root:

```sh
python tools/taskchain.py check
python -B -m unittest discover -s tests -v
```

For the optional sandbox-enabled Chromium check, see
[getting started](docs/guides/getting-started.md#contributor-work-without-hardware).
Host tests do not operate devices or prove audio, ARMv6, physical fit or restore.
Do not execute `backups/*.sh` as tests; their root-level rsync is destructive.

Historical shopping notes are [preserved with provenance](docs/archive/readme-research-before-2026-11-15.md),
not current advice. See [evidence conventions](docs/evidence.md) before relying
on compatibility or price claims. Repository visibility/licensing are unchanged;
publishing images needs separate third-party license review.
