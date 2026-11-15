---
title: Music transport and control map
date: 2026-11-15
type: project-learning
status: unreviewed
task: R03
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - https://github.com/Sendspin/spec — normative protocol spec, `main` @ 9d2f15ee8f172c67ce00dc0d9f6603c3b1030d9f, tag `1.0.0-rc1` (commit dated 2026-09-17), checked 2026-11-15
  - https://raw.githubusercontent.com/Sendspin/spec/main/roles/player/v1.md — player role, volume/mute/supported_commands, checked 2026-11-15
  - https://raw.githubusercontent.com/Sendspin/spec/main/roles/controller/v1.md — controller role, pause/play/seek/volume, checked 2026-11-15
  - https://raw.githubusercontent.com/Sendspin/spec/main/messaging.md — client/state, server/command, stream/end, checked 2026-11-15
  - https://raw.githubusercontent.com/Sendspin/spec/main/connection.md — mDNS, WebSocket, Noise, server- vs client-initiated, checked 2026-11-15
  - https://raw.githubusercontent.com/Sendspin/spec/main/SCOPE.md — scope includes group volume and control roles, checked 2026-11-15
  - https://github.com/Sendspin/sendspin-python-cli — release 9.1.0 (2026-10-27, the version the lab ran); `sendspin/daemon/daemon.py`, `audio.py`, `hardware_volume.py`, `alsa_volume.py`, `hook_volume.py`, `cli.py`, `README.md`, checked 2026-11-15
  - https://github.com/abmantis/aiosendspin-mpris — `aiosendspin_mpris/adapter.py` (MPRIS pause → `send_group_command`), checked 2026-11-15
  - https://github.com/Sendspin/aiosendspin — release 10.3.0 (2026-11-02), protocol library used by MA and the CLI
  - https://github.com/Sendspin/sendspin-cpp-cli — release v0.4.0 (2026-10-15)
  - https://raw.githubusercontent.com/badaix/snapcast/master/doc/json_rpc_api/control.md — Client.SetVolume, Group.SetMute, Stream.Control, checked 2026-11-15
  - https://raw.githubusercontent.com/badaix/snapcast/master/doc/configuration.md — stream sources, `send_to_muted`, "client is fully controlled from the server", checked 2026-11-15
  - https://raw.githubusercontent.com/badaix/snapcast/master/client/player/player.cpp — mixer modes, volume application, checked 2026-11-15
  - https://raw.githubusercontent.com/badaix/snapcast/master/client/player/pulse_player.cpp — PulseAudio mixer writes sink-input volume, checked 2026-11-15
  - https://github.com/badaix/snapcast — release v0.35.0 (2026-03-10)
  - https://github.com/music-assistant/server — `dev` @ ecb5f3562faf37abb6b06676f758943d26ecc38a; `providers/sendspin/{README,player,playback}.py`, `providers/snapcast/{provider,player,control}.py`, `controllers/players/volume.py`, checked 2026-11-15
  - https://raw.githubusercontent.com/music-assistant/server/dev/tests/providers/sendspin/test_reported_volume.py — volume command reaches the client as `PlayerCommand.VOLUME`, checked 2026-11-15
  - https://raw.githubusercontent.com/music-assistant/server/dev/tests/providers/snapcast/test_player_volume_routing.py — volume routing to the active output protocol, checked 2026-11-15
  - https://www.music-assistant.io/player-support/sendspin/ — "control from the device", technical preview, checked 2026-11-15
  - https://www.music-assistant.io/player-support/snapcast/ — "MA issues a STOP and RESUME command to achieve the pause effect", checked 2026-11-15
  - https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/music_assistant/media_player.py — HA media_player → MA commands, checked 2026-11-15
  - https://esphome.io/components/sendspin/ — hub, 8928, requires Sendspin 1.0.0-rc1 server / MA 2.11.0b4+, checked 2026-11-15
  - https://esphome.io/components/media_player/sendspin/ — group player "only sends playback and volume commands to the Sendspin server", checked 2026-11-15
  - https://docs.pipewire.org/page_module_filter_chain.html and https://docs.pipewire.org/page_module_loopback.html — virtual sinks / gain nodes, PipeWire 1.6.11 docs, checked 2026-11-15
  - https://man.archlinux.org/man/pactl.1.en — `set-sink-volume` vs `set-sink-input-volume`, checked 2026-11-15
  - docs/comparisons/music-playback.md (lines 14–28), docs/roadmap.md (A03), docs/design/audio-outputs.md, docs/testing/results/2026-11-15-lab-pi5-lva-sendspin.md — earlier conclusions corrected or qualified below
supersedes: []
---

# Music transport and control map

Answers two questions the project kept guessing at: **can Debra pause the music
without stopping it, and can it attenuate it independently of the master
volume?** No device was contacted, nothing was played, nothing was installed.
Everything below is reading upstream code and specification documents, dated
2026-11-15. The household Music Assistant is `2.11.0.dev2026111103`; the source
inspected is the MA `dev` branch, so version drift is possible.

## Summary

**Pause without stopping: yes for Sendspin, no for Snapcast — and in neither case
is it the receiver that pauses.**

- Sendspin has a documented control channel. A client that lists the `controller@v1`
  role can send `client/command` with `command: 'pause'`, and `'play'` to resume
  from the current position ([controller role][sp-controller], checked
  2026-11-15). Music Assistant receives that, pauses its own queue, and — per the
  same spec — ends the audio stream to the device (`stream/end`), restarting it
  with `stream/start` on resume ([messaging][sp-msg] §`stream/end`). So the music
  keeps its place, but the receiver holds no paused buffer.
- Snapcast has no pause at all. Its control API exposes per-client volume, group
  mute, group stream switching and a `Stream.Control` that forwards to the
  *source* plugin ([snapcast control API][sc-rpc], checked 2026-11-15). MA says so
  itself: "Pausing has been implemented as best as can be achieved with the
  limitations of Snapcast. MA issues a STOP and RESUME command to achieve the pause
  effect but this means the resulting player state never changes to paused"
  ([MA Snapcast docs][ma-snap], checked 2026-11-15).
- The receiver's own ability to pause depends on whether it declares the
  controller role. The Python CLI only adds `controller@v1` when MPRIS is enabled,
  and MPRIS is on by default ([daemon.py][cli-daemon], [MPRIS adapter][mpris],
  checked 2026-11-15).

**Independent attenuation: yes on both transports, but it is not invisible.**

- Sendspin makes volume a first-class per-player field with a defined perceptual
  curve, `amplitude = (volume/100)^1.5`, and requires the player to report every
  change, *including changes made at the device* ([player role][sp-player],
  checked 2026-11-15). MA sends it as a real protocol message — a MA test asserts
  the client receives `PlayerCommand.VOLUME, 40` after `players/cmd_volume_set`
  ([test_reported_volume.py][ma-test-vol], checked 2026-11-15).
- Snapcast likewise has per-client volume and mute, applied locally by snapclient
  through a mixer (`hardware`, `software`, `script` or `none`), with local changes
  reported back to the server ([player.cpp][sc-player], checked 2026-11-15).
- Neither is an *independent* trim. Both are the player's own volume as the server
  knows it: visible in MA and Home Assistant, persisted, and the reference point
  for group-volume arithmetic. A truly independent attenuation has to sit below
  the protocol, in PipeWire or ALSA, and is then a local gain change the sender
  cannot see.

**The single most consequential detail:** in daemon mode the Sendspin CLI's
"hardware volume" is on by default and writes the *system sink* volume, not a
per-stream gain ([hardware_volume.py][cli-hw], [README][cli-readme], checked
2026-11-15). On the lab device that is the same control the voice assistant's
replies use, which is the class of bug already recorded in the lab result (sink at
9 %, assistant silent).

## 1. Sendspin

**What it is.** A multi-room music protocol from the Open Home Foundation, with a
normative specification at `github.com/Sendspin/spec`. Not a README-level
description: the repo contains `connection.md`, `messaging.md`, `pairing.md`, and
seven versioned role documents. The org's own summary is "an open standard for the
complete music listening experience: listen, control & see", and `SCOPE.md` puts
"the role definitions (player, source, controller, metadata, artwork, visualizer,
color) … including playback synchronization, correction, group volume" inside the
standard ([SCOPE.md][sp-scope], checked 2026-11-15).

**Transport and who connects.** WebSocket carrying a Noise `KKpsk2` encrypted
stream; two standard connection modes, and servers MUST support both
([connection.md][sp-conn], checked 2026-11-15):

| Mode | Who initiates | Discovery | Port |
| --- | --- | --- | --- |
| Server-initiated (**RECOMMENDED**) | Server connects to the client | client advertises `_sendspin._tcp.local.` | client listens on 8928 (recommended) |
| Client-initiated | Client connects to the server | client discovers `_sendspin-server._tcp.local.` | server listens on 8927 (recommended) |

The **server is always the Noise initiator**, whichever side opened the socket.
The client admits one connection at a time by default and arbitrates multiple
servers; a displaced server gets `client/goodbye` reason `another_server`. The
lab's setup is the server-initiated mode (MA connected to the Pi), which matches
the lab log line "Admitted server 'Music Assistant (…)'" in
[the lab result](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md).

**Version.** Spec tag `1.0.0-rc1` (commit dated 2026-09-17); `main` still moving
(updated 2026-11-14). ESPHome states the device "needs a Sendspin 1.0.0-rc1
server, such as Music Assistant 2.11.0b4 or newer" ([ESPHome sendspin][esp-hub],
checked 2026-11-15). Client implementations: `aiosendspin` 10.3.0 (2026-11-02,
Python, used by both MA and the CLI), `sendspin-python-cli` 9.1.0 (2026-10-27),
`sendspin-cpp-cli` v0.4.0 (2026-10-15).

**What the receiver implements.** The player role: it advertises codecs/rates/bit
depth, a buffer capacity, an `output_delay_ms`, `required_lead_time_ms`,
`min_buffer_ms`, and `supported_commands` (a subset of `volume`, `mute`,
`set_output_delay`) ([player role][sp-player]). It schedules each audio chunk by
server timestamp, converts volume to amplitude with the `^1.5` curve, applies
changes over a short ramp to avoid clicks, and keeps `volume` and `muted`
independent.

**Control messages the protocol defines — explicitly.**

| Direction | Message | What it carries |
| --- | --- | --- |
| Client → Server | `client/command` → `controller` | `play`, `pause`, `stop`, `next`, `previous`, `volume`, `mute`, `seek`, `seek_relative`, repeat/shuffle, `switch` (group cycling) — only those the server advertised in `server/state.controller.supported_commands` |
| Server → Client | `server/state` → `controller` | `supported_commands`, group `volume`, `muted`, `repeat`, `shuffle`, `seek_max_ms` |
| Server → Client | `server/command` → `player` | `volume` (0–100), `mute` (bool), `set_output_delay` |
| Client → Server | `client/state` → `player` | `volume`, `muted`, `output_delay_ms`, `supported_commands`, format preference |
| Server → Client | `stream/start`, `stream/clear`, `stream/end` | stream configuration, buffer clear (seek/track jump, optional `from_timestamp`), stream termination |

So the protocol does **not** only deliver a stream. It defines pause, resume, stop,
seek, next/previous, per-player volume, per-player mute, and group volume — in
two separate role documents. Any earlier statement that Sendspin has no control
API is wrong.

Two semantics worth internalising:

- **Pause is not a stream-level message.** "When a group pauses, the server MUST
  end the active `player` and `visualizer` streams … and MUST send a new
  `stream/start` when playback resumes" ([messaging.md][sp-msg] §`stream/end`).
  The device is told to stop output and clear buffers; the position lives at the
  server.
- **Group volume is derived, not stored.** Reported group volume is the average of
  the volumes of players that support `volume`; players without volume support are
  excluded and receive no volume command. The server must preserve relative levels
  when setting group volume, clamping at 0–100 and redistributing lost delta
  ([controller role][sp-controller]). A per-player volume is therefore a real,
  addressable value that is *not* the group average.

**Answers.** Pause without stopping: **yes, through `controller@v1` `pause`**,
which is a request to the server, not a device-side pause. Attenuation independent
of the group/master: **yes at the protocol level** — `server/command` `player.volume`
sets that one player; but it is the player's own published volume, not a private
trim.

**What the receiver does with volume in practice (Python CLI 9.1.0).** Three
backends, chosen at startup ([cli.py][cli-cli], checked 2026-11-15):

1. `--hook-set-volume <script>` — highest precedence; script receives the effective
   level 0–100.
2. `--hardware-volume true` — tries ALSA mixer first (`amixer`, elements `Digital`
   / `Master` / `PCM`), then PulseAudio/PipeWire. **Default on for `daemon`, off for
   the TUI.**
3. software (default fallback) — `_apply_volume` in the audio worker.

The PulseAudio path calls `client.volume_set_all_chans(sink, volume/100)` — it
sets the **sink**, i.e. the system output volume, not a per-application stream
([hardware_volume.py][cli-hw]). The CLI also monitors that sink and republishes
external changes to the server as its player volume, so this is a bidirectional,
shared control.

## 2. Snapcast

**What it is.** A server/client synchronised transport: `snapserver` reads a
source (pipe, process, ALSA, PipeWire, TCP, file, meta-mux), encodes it, and sends
timestamped chunks to `snapclient`s. The client "is fully controlled from the
server so clients don't have to persist any state"
([configuration.md][sc-conf], checked 2026-11-15).

**Control surface.** JSON-RPC 2.0 over raw TCP 1705, or HTTP/WebSocket 1780
([control API][sc-rpc], checked 2026-11-15):

| Method | Effect |
| --- | --- |
| `Client.SetVolume` | `{muted, percent}` for one client |
| `Client.SetLatency` | per-client sync delay |
| `Group.SetMute` | mute a whole group |
| `Group.SetStream` | point a group at a different stream (MA switches to the stream named `default` to stop a player) |
| `Stream.Control` | `play`/`pause`/`stop`/`next`/`seek` — **forwarded to the stream's control script**, i.e. only works if the source is a controllable player |

There is no client-side or protocol-level pause. The stream is continuous; a
client can be muted or volume-set, and its group can be moved to another stream.
Pause exists only if the *source* exposes it through `Stream.Control`.

**snapclient's own volume.** `Player::setVolume` dispatches by mixer mode
([player.cpp][sc-player], checked 2026-11-15):

- `software` — multiplies samples: `volume_.mute ? 0 : volume_.volume`, times a
  drift correction factor; polynomial (`^3` by default) or exponential mapping.
- `hardware` — calls `setHardwareVolume`; on the PulseAudio backend that is
  `pa_context_set_sink_input_volume(...)` on the client's own playback stream
  ([pulse_player.cpp][sc-pulse]) — a **per-stream** gain, not the sink.
- `script` — runs an external mixer script with `--volume`/`--mute`.
- `none` — no local attenuation.

It is independent of the stream in the sense that it never changes what is
received: muting or attenuating a client does not stop delivery unless the server
is configured not to send to muted clients (`send_to_muted`, default `false` —
[configuration.md][sc-conf]). Local changes are reported back
(`notifyVolumeChange`), so the server's view stays truthful.

**Answer.** Pause: **not through a documented interface**; closest mechanism is
MA's stop+resume, or moving the group to a silent stream. Attenuation independent
of the group: **yes** — `Client.SetVolume`, or the local mixer, which on the
PulseAudio backend is already a per-stream gain.

## 3. Music Assistant's role

**Which protocols it speaks.** Both. `music_assistant/providers/sendspin/` is a
full Sendspin **server** (listens on 8927, `ws://<ma>:8927/sendspin`) with WebRTC
bridging for browsers; `music_assistant/providers/snapcast/` embeds a Snapserver
and a control script, or connects to an external one
([sendspin README][ma-ss-readme], [MA Snapcast docs][ma-snap], checked
2026-11-15). MA's own docs call Sendspin "Music Assistant's own way of sending
audio to a player" and still label it a **technical preview**.

**What "player" means in MA.** MA separates a *player* (the thing with a queue,
volume and name in the UI) from a *protocol* (the transport attached to it). The
Sendspin provider README is explicit: "Every Sendspin client is a protocol
(`SendspinBasePlayer`) whose id is its client id", and a client with a hardware
MAC address that MA has seen before "joins the player of its device when there is
one, as an audio output" — so one MA player can have several protocols, and the
active one decides where audio goes. A Snapcast provider test enforces the
consequence: native Snapcast volume is hidden while a foreign protocol (Sendspin)
is the active output, and `_volume_control` redirects to it
([test_player_volume_routing.py][ma-test-snap]).

**Registration.** Sendspin clients are discovered by mDNS and appear
automatically; unpaired devices are usable when they allow guest access, otherwise
the player shows "Setup required" until paired ([MA Sendspin docs][ma-ss]).
Snapcast clients are discovered from the server: MA calls `Server.GetStatus` and
turns each snapclient into a `SnapCastPlayer`.

**What MA can command on a Sendspin client.** `server/command` `player.volume` /
`player.mute` / `player.set_output_delay`; `stream/start`, `stream/clear`,
`stream/end`; and metadata/artwork/visualizer role payloads. `volume_set` on the
player calls `role.set_player_volume(...)` for every active player role
([player.py][ma-ss-player], checked 2026-11-15). In the other direction, controller
events from the device are executed as MA queue commands — `ControllerPauseEvent`
→ `self.mass.players.cmd_pause(player_id)`, and the same for play, stop,
next/previous, seek, repeat, shuffle.

**What MA does on pause.** It pauses the queue. For Sendspin that ends the player
stream (per spec); for Snapcast MA's docs describe a STOP + RESUME, and note the
player state never reports paused.

**Announcements are not a duck.** MA's Sendspin `play_announcement` relays through
the Home Assistant announce pipeline, drops `SUPPORTS_VOLUME` while relaying, and
logs that "the HA announce pipeline plays at its own volume; a requested level is
applied through the builtin path instead" ([player.py][ma-ss-player]). There is no
"duck the music by N dB" call in this provider.

## 4. PipeWire / PulseAudio at the device

Where an attenuation independent of MA's volume would have to live, in increasing
order of isolation:

| Stage | Mechanism | Independent of MA's volume? | Sender knows? |
| --- | --- | --- | --- |
| Codec mixer element | `amixer cset name='PCM Playback Volume'` — what the CLI's ALSA backend and the lab's mixer scripts write | Yes | Only if the CLI is using that backend (it then republishes it as player volume) |
| Sink (master) | `pactl set-sink-volume`, `wpctl set-volume @DEFAULT_AUDIO_SINK@` — what the CLI's PulseAudio backend writes | No, this *is* the master | Yes, the CLI monitors the sink and reports changes |
| Per-stream (sink-input) | `pactl set-sink-input-volume <index>` | **Yes** — a separate node gain under the sink | **No**, unless the client watches its own node |
| Filter / loopback node | `module-filter-chain`, `module-loopback` virtual sink with its own gain ([PipeWire docs][pw-filter], [loopback][pw-loop]) | Yes | No |

Two facts make the middle rows concrete:

- `pactl` distinguishes sink volume from sink-input volume; they are different
  objects in the graph ([pactl(1)][pactl]).
- The Sendspin CLI labels its stream for the sound server:
  `PULSE_PROP_application.name = "Sendspin"`, `application.id = org.sendspin.cli`,
  `media.role = music` ([cli.py][cli-cli]). That is what makes
  `pactl list sink-inputs | grep -i sendspin` plausible as an identification route
  — but only when the audio path goes through the ALSA `pulse`/`pipewire` plug or
  pipewire-pulse, which is a hypothesis for the lab stack, not an observation.

**Is that a real control or just a local gain change?** It is a real control of
what leaves the speaker, and it is invisible to the sender. It is not a transport
control: MA will keep streaming, its progress bar will keep advancing, and the
volume it displays will be wrong. On a device that also runs a voice assistant on
the same sink, a *sink* change moves both; a *sink-input* change moves only the
music stream. That distinction is the whole design question, and it is why the
earlier note's rule — music on one sink, announcements on a combine sink — still
holds ([audio-outputs.md](../design/audio-outputs.md)).

## 5. Home Assistant

HA has no Sendspin integration and never speaks the protocol. Two separate paths
exist, and only one of them applies to a Pi:

1. **MA integration (`homeassistant/components/music_assistant/media_player.py`,
   in HA core).** `async_media_pause` → `mass.players.player_command_pause`,
   `async_set_volume_level` → `player_command_volume_set`, `async_mute_volume` →
   `player_command_volume_mute`, `async_media_seek` → `player_command_seek`
   ([media_player.py][ha-ma], checked 2026-11-15). Every one of these stops at
   **MA**. MA then decides: a pause becomes a queue pause (Sendspin: stream ends;
   Snapcast: stop+resume), a volume becomes a `server/command` to the device or a
   `Client.SetVolume` to snapclient. The entity's `volume_level` is read back from
   `player.volume_level` (or `group_volume` for a group player).
2. **ESPHome's "Sendspin Group Media Player"** — an ESP32-only entity that "only
   sends playback and volume commands to the Sendspin server, which applies them
   to every player in the active group", with play/pause/stop/next/previous/
   volume/mute/shuffle/repeat forwarded, and "playing arbitrary media and
   announcements are not supported" ([ESPHome group player][esp-mp], checked
   2026-11-15). On this path HA → ESPHome device → `client/command` → MA.

So on the lab Pi: HA's pause and volume reach MA and stop there as decisions; the
device only ever sees `stream/end`, `server/command`, or nothing at all. A Pi has
no HA entity that speaks Sendspin directly.

## Control surface table

| Layer | Pause | Resume | Volume / attenuation | Evidence |
| --- | --- | --- | --- | --- |
| Sendspin protocol | `controller@v1` `client/command` `pause` (client → server). Server then sends `stream/end` | `play` resumes from current position; server sends a new `stream/start` | `server/command` `player.volume` (0–100, `^1.5` curve), `player.mute`; group volume = average of supporting players | `upstream-documented` [sp-controller], [sp-player], [sp-msg] |
| Sendspin receiver, Python CLI 9.1.0 | Only with MPRIS enabled (adds `controller@v1` + `metadata@v1`); MPRIS `Pause()` → `send_group_command(PAUSE)` | MPRIS `Play()` → controller `play` | Software gain (TUI default), ALSA mixer, PulseAudio **sink**, or hook script (daemon default = hardware) | `upstream-documented` code + README [cli-daemon], [cli-hw], [cli-cli], [mpris] |
| Sendspin receiver, ESP32/ESPHome | via `sendspin` group media player entity → server | same | group volume/mute to the server; no local trim exposed | `upstream-documented` [esp-mp] |
| Snapcast protocol | **None.** Closest: `Group.SetMute`, `Group.SetStream` to silence, or `Stream.Control` if the source plugin supports it | `Stream.Control` `play` only via the source plugin | `Client.SetVolume` `{muted, percent}`; per-client, server-authoritative | `upstream-documented` [sc-rpc], [sc-conf] |
| snapclient | Not applicable — no pause concept | — | `hardware` (PulseAudio: **sink-input** volume), `software` (sample multiply, `^3`/`^10`), `script`, `none`; local changes reported to server | `upstream-documented` [sc-player], [sc-pulse] |
| Music Assistant | Pauses the queue. Sendspin: stream ends. Snapcast: STOP+RESUME, state never shows paused | Resumes the queue | `players/cmd/volume_set` → active protocol; group volume interpolates members' relative balance from a snapshot | `upstream-documented` [ma-ss-player], [ma-snap], [ma-vol], [ma-test-vol] |
| PipeWire / PulseAudio | Not a pause — a gain change only | — | Sink volume (shared), sink-input volume (**per stream, independent**), filter/loopback node, ALSA mixer element | `upstream-documented` [pactl], [pw-filter]; sink-input identification on the lab stack is `hypothesis` |
| Home Assistant | `media_player.media_pause` → MA only | `media_play` → MA only | `volume_set`/`mute_volume` → MA only | `upstream-documented` [ha-ma], [esp-mp] |

## Traps

1. **"Pause" in Sendspin ends the stream.** Do not expect the receiver to hold a
   paused buffer or to resume from its own state. If Debra wants an instant resume,
   the resume is a fresh `stream/start` with a new lead time — expect the
   `required_lead_time_ms` + `min_buffer_ms` gap, not a click.
2. **A device-side duck implemented as player volume rewrites MA's balance.**
   MA caches a per-member volume snapshot for group interpolation and invalidates
   it when a member's individual volume changes ([volume.py][ma-vol], checked
   2026-11-15). Ducking one member therefore becomes the new reference for later
   group-volume moves, and clamping at 0/100 can lose the offset entirely.
3. **The Python CLI's daemon default changes the system sink volume.** "Hardware
   volume is on by default in daemon mode" and on PulseAudio it sets the sink
   ([README][cli-readme], [hardware_volume.py][cli-hw]). On a box that also runs
   LVA, MA's volume slider then moves the assistant's reply level. This is the
   same failure family as the lab's "reply inaudible because the sink was at 9 %".
4. **Snapclient's and Sendspin's "hardware volume" are not the same thing.**
   snapclient writes a *sink-input* volume; the Sendspin CLI writes the *sink*.
   Copying a config from one to the other silently changes the blast radius.
5. **Disabling MPRIS removes the device's only pause.** The controller role is
   added only when MPRIS is enabled ([daemon.py][cli-daemon]). A03's premise
   ("MPRIS is disabled") describes a configuration with no device-side pause,
   next, or previous at all — the fix is to enable MPRIS or to send controller
   commands another way, not to conclude the protocol lacks them.
6. **`available: false` is a stop, not a duck.** A client that reports itself
   unavailable is moved to a solo group, gets `stream/end`, and the server "MUST
   NOT auto-rejoin it … or restart playback" ([messaging.md][sp-msg]). Useful for
   yielding the speaker to a local source; not a pause.
7. **Announcements are not a duck in MA's Sendspin provider.** They relay through
   HA's announce pipeline and the requested level is ignored
   ([player.py][ma-ss-player]).
8. **Muting in Snapcast does not stop the stream by default** (`send_to_muted:
   false`), which is why MA's docs warn about muted clients drifting out of sync
   ([configuration.md][sc-conf], [MA Snapcast docs][ma-snap]).
9. **Snapcast pause is stop+resume.** Any UI that shows "paused" is lying; MA's own
   docs say the state never becomes paused.
10. **`stream/clear` with `from_timestamp` is not a pause or a duck.** It is how a
    server splices an announcement into a running stream or rewrites a buffered
    next track ([messaging.md][sp-msg] §`stream/clear`).

## Corrections to earlier project notes

- [music-playback.md](../comparisons/music-playback.md) lines 14–28 say playback
  interruption, independent attenuation and pause/resume of a separate receiver
  are "unverified". That was right about *Debra's device*, and wrong if read as
  "undocumented": pause/resume, per-player volume and mute are specified in the
  Sendspin protocol and implemented in MA and the CLI. The remaining unknown is a
  named-device test, not the existence of an interface.
- [roadmap.md](../roadmap.md) A03 states "no verified Sendspin pause/resume or
  independent attenuation interface exists yet (MPRIS is disabled)". The interface
  exists and is documented; MPRIS being disabled is precisely what removes it from
  the Python CLI. A03's "settling test" should be re-scoped to *which* interface
  Debra uses, not whether one exists.
- [audio-outputs.md](../design/audio-outputs.md) concludes music must stay on one
  sink because the protocols do their own clock sync. That still holds. What it
  does not say, and should, is that the receiver may itself be writing the sink
  volume — so "music on one sink" and "voice on a combine sink" can still collide
  at the sink gain stage.

## Not verified / open questions

- **No Debra device test of any of this.** The lab result proves stream delivery
  and nothing about control. `unknown` whether the lab's `sendspin.service` ran
  with hardware volume on (the daemon default) or off.
- Whether MA emits `stream/end` on pause in practice, or simply stops sending
  chunks, was not observed on the wire. The spec requires the former; the MA code
  path shows a playback-session cancel with a buffer drain before `stream/end`
  ([playback.py][ma-playback]).
- Whether the Sendspin CLI's PortAudio stream appears as an identifiable
  PipeWire/Pulse sink-input on the lab stack (it depends on which ALSA device
  PortAudio opens). `hypothesis`.
- Whether a PipeWire sink-input volume change is picked up and republished by the
  CLI as player volume. Code inspection says the PulseAudio backend monitors the
  *sink*, not its own sink-input, so probably not — `hypothesis`, untested.
- Snapcast resume-after-stop position behaviour is documented by MA as "best as
  can be achieved"; not tested.
- Whether the household MA (`2.11.0.dev2026111103`) matches the `dev` branch
  inspected here. Different commits may differ in group-volume arithmetic and
  controller-command handling.
- ARMv6/ARMv7 implications of running the controller role or MPRIS are out of
  scope for this note; MPRIS needs a session D-Bus, which a headless image may not
  have ([armv6-wheels](2026-11-15-armv6-wheels.md) already flags `mpris-api`
  packaging gaps).
- Nothing here selects a pin or authorises a device change. The next concrete
  step is a named-device probe on the lab Pi: enable MPRIS, confirm
  `controller@v1` appears in MA, press pause at the device, and record whether MA
  reports paused and where the position resumes.

[sp-scope]: https://raw.githubusercontent.com/Sendspin/spec/main/SCOPE.md
[sp-conn]: https://raw.githubusercontent.com/Sendspin/spec/main/connection.md
[sp-msg]: https://raw.githubusercontent.com/Sendspin/spec/main/messaging.md
[sp-player]: https://raw.githubusercontent.com/Sendspin/spec/main/roles/player/v1.md
[sp-controller]: https://raw.githubusercontent.com/Sendspin/spec/main/roles/controller/v1.md
[sc-rpc]: https://raw.githubusercontent.com/badaix/snapcast/master/doc/json_rpc_api/control.md
[sc-conf]: https://raw.githubusercontent.com/badaix/snapcast/master/doc/configuration.md
[sc-player]: https://raw.githubusercontent.com/badaix/snapcast/master/client/player/player.cpp
[sc-pulse]: https://raw.githubusercontent.com/badaix/snapcast/master/client/player/pulse_player.cpp
[ma-ss-readme]: https://raw.githubusercontent.com/music-assistant/server/dev/music_assistant/providers/sendspin/README.md
[ma-ss-player]: https://raw.githubusercontent.com/music-assistant/server/dev/music_assistant/providers/sendspin/player.py
[ma-playback]: https://raw.githubusercontent.com/music-assistant/server/dev/music_assistant/providers/sendspin/playback.py
[ma-vol]: https://raw.githubusercontent.com/music-assistant/server/dev/music_assistant/controllers/players/volume.py
[ma-test-vol]: https://raw.githubusercontent.com/music-assistant/server/dev/tests/providers/sendspin/test_reported_volume.py
[ma-test-snap]: https://raw.githubusercontent.com/music-assistant/server/dev/tests/providers/snapcast/test_player_volume_routing.py
[ma-ss]: https://www.music-assistant.io/player-support/sendspin/
[ma-snap]: https://www.music-assistant.io/player-support/snapcast/
[cli-daemon]: https://raw.githubusercontent.com/Sendspin/sendspin-python-cli/main/sendspin/daemon/daemon.py
[cli-hw]: https://raw.githubusercontent.com/Sendspin/sendspin-python-cli/main/sendspin/hardware_volume.py
[cli-cli]: https://raw.githubusercontent.com/Sendspin/sendspin-python-cli/main/sendspin/cli.py
[cli-readme]: https://raw.githubusercontent.com/Sendspin/sendspin-python-cli/main/README.md
[mpris]: https://raw.githubusercontent.com/abmantis/aiosendspin-mpris/main/aiosendspin_mpris/adapter.py
[esp-hub]: https://esphome.io/components/sendspin/
[esp-mp]: https://esphome.io/components/media_player/sendspin/
[ha-ma]: https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/music_assistant/media_player.py
[pactl]: https://man.archlinux.org/man/pactl.1.en
[pw-filter]: https://docs.pipewire.org/page_module_filter_chain.html
[pw-loop]: https://docs.pipewire.org/page_module_loopback.html
