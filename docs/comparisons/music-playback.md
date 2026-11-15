# How each device actually plays music

**Draft, 2026-11-15 UTC.** The master table in [devices.md](devices.md) has one
`Music playback` cell per device. This page is the detail behind those cells:
what the transport is, what version turns it on, and what has to exist on the
server. Source keys are in [sources.md](sources.md).

Debra's premise is one box that is both a voice satellite and a music player, so
"can it play music" is not a nice-to-have row. The table is ordered by how close
each device is to doing it with vendor firmware alone.

## The table

| Device | Transport | Turned on by | Stream | Server side | Evidence |
| --- | --- | --- | --- | --- | --- |
| Satellite1.1 HAT / Dev Kit / Smart Speaker | **Sendspin** (Snapcast before v0.2.0) | firmware **v0.2.0**, 2026-05-28 | 48 kHz | Music Assistant, no provider setup | `D` [S15][S33] |
| HA Voice PE | **Sendspin** | firmware **25.12.0**, 2025-12-17, "public preview" | 48 kHz FLAC `media_pipeline` in the dev YAML | Music Assistant | `D` [S20][S21] |
| M5Stack Atom VoiceS3R | **Sendspin**, in vendor YAML only | ESPHome **2026.10.0** per the YAML; the vendor's prose says 2026.1.0 | 48 kHz stereo `speaker_source`, FLAC or PCM | Music Assistant | `D` (code, not prose) [S22] |
| ReSpeaker Lite (XIAO ESP32-S3) | **Sendspin** | XMOS I2S firmware ≥ **1.1.0** at 48 kHz, then a community ESPHome config | 48 kHz | Music Assistant | `D` + `R` [S25][S26] |
| ESP32-S3-BOX-3 | none in stock firmware | — | — | — | `D` [S23]; one third-party firmware claims a player `R` [S24] |
| Pi + ReSpeaker 2-Mics HAT (Debra's lab) | host software only: Sendspin client (**the one the lab ran**), Snapcast client, squeezelite, shairport-sync, or MA Local Audio | depends on which one you install | 48 kHz card, host-decoded | Music Assistant **or** a Snapcast/Shairport server | `D` [S29][S30][S31][S32]; Sendspin observed on the lab unit `T` |
| ReSpeaker Lite (USB) | UAC2 sound card, no protocol | plug in | the Pi 5 guide pins a 16 kHz clock — a **configuration**, not a published hardware maximum | host software, as above | `D` [S28] |

"Transport" means the device speaks a music protocol itself. A USB sound card or
a Pi HAT with an ALSA card has no transport: something on the host has to
receive the stream and decode it.

## The five ways a Pi can play music

| Way | What it is | Why you would | Why you would not |
| --- | --- | --- | --- |
| **Sendspin** | The protocol Music Assistant is moving to; also what the ESPHome devices above use | One path for both the ESP32 devices and a Pi, so a mixed house is one system | Newest of the five; MA's support is beta [S21]; the Pi side is the least demonstrated |
| **Snapcast** | Mature synchronised multi-room client/server [S30] | Real multi-room sync today, well understood, runs on a Pi Zero | A second server to run; Satellite1 dropped it for Sendspin [S33] |
| **squeezelite** | Lyrion/Squeezebox client | Very light, well trodden on Pi hardware | Ties you to the LMS ecosystem |
| **shairport-sync** | AirPlay receiver [S31] | iPhone users can just send audio | Single-source, no multi-room, no MA control |
| **MA Local Audio** | Music Assistant's own player app on the host | No extra server | It is the successor to "Local Audio Out", which MA retired, and is still experimental [S32] |

Debra's stated direction is Sendspin first with room left for Snapcast, and this
table is the reason that order makes sense: Sendspin is where both upstream
projects are heading, and Snapcast is the fallback that already works.

## Traps

- **"Ready-made" is not "demonstrated".** Only the Voice PE and Satellite1 ship a
  music transport in vendor firmware [S20][S33]. The VoiceS3R has it in vendor
  YAML while its own documentation still describes wake word and announcements
  [S22]; the BOX-3 has no audio pipeline at all in the stock configuration [S23].
- **Version gates are sharp.** Sendspin needs a recent ESPHome and a Sendspin
  server (MA 2.11 beta; stable was 2.10.12 when this was written). The Snapcast →
  Sendspin move on Satellite1 is breaking: old players have to be deleted, not
  upgraded [S33].
- **Sendspin is not the only path, and the HA player path cannot sync.** Music
  Assistant's Home Assistant player provider defaults to MP3 and explicitly
  cannot synchronise with other players [S32].
- **A HAT is not a player by itself.** With Local Audio Out retired, the 2-Mics
  HAT needs a receiver on the host: the Sendspin client — the one the lab
  actually ran [T] — or Snapcast, squeezelite, shairport-sync, or MA Local Audio
  [S29][S30][S31][S32].
- **The USB ReSpeaker Lite is configured at 16 kHz by the Pi 5 guide.** That is a
  sample-rate choice in that guide, not a published maximum for the Lite — the
  source that states a 16 kHz ceiling describes the separate USB 4-Mic Array
  [S27][S28]. Fine for voice; music capability is unproven either way.
- **Two codec names for one HAT.** Seeed documents WM8960 for the 2-Mics HAT
  while its own v2 `aplay` output shows `tlv320aic3x`; the lab unit enumerates as
  TLV320AIC3104 [S29][T].
- **Wrong product.** M5Stack's documented "Media Playback" application is
  AtomS3R + Atomic Audio-3.5 Base, not the VoiceS3R.

## What is not established

- **No listening test, latency measurement or captured sample rate exists for any
  of the seven.** Every row is a documentation claim except the lab Pi row, which
  is `T` only for "streams FLAC from the household Music Assistant to the HAT",
  not for sound quality.
- No published Sendspin audio pipeline exists for a stock ESP32-S3-BOX-3.
- No music-specific report exists for either ReSpeaker Lite variant or the 2-Mics
  HAT.
- Satellite1 HAT firmware for a Pi host is described by the vendor as still in
  development [S15].
- Whether a Pi Zero 2 W can host a Sendspin client plus a voice satellite at the
  same time is untested; the audio stack is the expensive part, not the protocol.

## The one cheap check

Take a single ESP32-S3-BOX-3, add the VoiceS3R's `sendspin` and `speaker_source`
blocks to the stock YAML [S22][S23], and see whether Music Assistant discovers it
and plays 60 seconds without dropouts. That is about half an hour, it touches no
other device, and it settles the largest unknown row in the table.

## Verification note

The M5Stack YAML and the Voice PE 25.12.0 release note were re-read directly on
2026-11-15 while writing this page: the YAML contains a `sendspin` hub, a
`sendspin` media source with `codecs: [FLAC, PCM]` and a 48 kHz `speaker_source`;
the release note says "Add support for Sendspin multi-room audio protocol (public
preview, works with Music Assistant)". The Seeed and FutureProofHomes rows come
from the research report that produced [S25]–[S34] and were checked only for
reachability, not re-read line by line.
