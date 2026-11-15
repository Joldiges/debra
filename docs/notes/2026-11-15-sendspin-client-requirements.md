---
title: What the Sendspin client requires of a device
date: 2026-11-15
type: project-learning
status: unreviewed
task: none (ad-hoc research, coordinator-requested)
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - PyPI sendspin 9.1.0 metadata, https://pypi.org/pypi/sendspin/json, checked 2026-11-15
  - Sendspin/sendspin-python-cli tag 9.1.0 source tree (README, pyproject, sendspin/*), checked 2026-11-15
  - Sendspin/spec main @ 9d2f15e (connection.md, messaging.md, roles/player/v1.md), checked 2026-11-15
  - sendspin-audio.com implementation guide (client, roles, use-cases, SDK pages), checked 2026-11-15
  - aiosendspin 10.3.0 source (client/connection.py, client/client.py, clock.py), checked 2026-11-15
  - Sendspin/sendspin-cpp-cli v0.4.0 README, wiki and release assets, checked 2026-11-15
  - Sendspin issue tracker #56, #113, #216, checked 2026-11-15
supersedes: []
---

# What the Sendspin client requires of a device

Scope: the **receiver** side, meaning the thing Debra installs on a Pi that plays
what Music Assistant sends. Server behaviour is covered only where the client
depends on it. Read-only research: no device was contacted, nothing was
installed, nothing was played, no Home Assistant / Music Assistant / network
service was touched. All upstream pages and pinned source were read on
2026-11-15. Debra's own files are cited by repository path.

Claim labels, used per row rather than per page:

| Label | Meaning |
| --- | --- |
| `D` | Upstream-documented: the linked upstream page, release note, specification text or source file states it |
| `D (code)` | Only present in upstream source code, not in prose documentation; file cited |
| `R` | Reported: an issue-thread statement, a maintainer comment, or a Debra record; context and limits given |
| `H` | Hypothesis or inference by this note's author, including arithmetic |
| `U` | Unknown; insufficient evidence |
| `T` | Debra test record naming hardware, version and observed result |

Mapping to [docs/evidence.md](../evidence.md): `D` = upstream-documented,
`R` = reported, `H` = hypothesis, `U` = unknown, `T` = tested. `D (code)` is
still `upstream-documented`, with the caveat that only source code carries it.

## Summary

- Debra's installer pins **`sendspin==9.1.0`**, which is the current PyPI
  release (uploaded 2026-10-27). The 9.x line is the current line; there is no
  10.x CLI.
- A device must supply three things the client does not: **Python ≥ 3.12 on a
  platform with published wheels**, **PortAudio plus an output device that
  accepts the negotiated format**, and **a quiet local network with working
  mDNS multicast** so the time filter can converge before the client reports
  itself available.
- Clock synchronisation is a Kalman filter over `client/time` bursts, mapped to
  `CLOCK_MONOTONIC_RAW`. The observable consequence for a device is that it
  plays silence, not an error, when chunks stop, and that a fresh connection is
  a fresh `stream/start` with a new lead time.
- **Sendspin has no ducking, duck command or announcement role.** The official
  guide says announcements and chimes are not roles yet. Ducking a voice
  assistant over a Sendspin receiver is Debra's own problem; the protocol only
  offers `available`, `client/leave`, `player.volume`, and pause through the
  controller role.
- **32-bit ARM is not supported upstream.** The Python client publishes no
  `armv7l`/`armv6l` wheel, the maintainer declined to support 32-bit, and a
  32-bit install is a source build. The C++ client is the only upstream path
  with `armv6`/`armv7` binaries.

## 1. Release line, the pin, and dates

| Claim | Label | Source | Limits |
| --- | --- | --- | --- |
| The current Python CLI release is **9.1.0**, published 2026-10-27 (GitHub release 15:58Z; PyPI files 16:00Z) | `D` | [S1], [S2] | PyPI "latest" and the newest Git tag agree on 2026-11-15; both can move |
| 9.0.0 (2026-10-26) is the breaking release: aiosendspin 10.2.1, "Requires Music Assistant 2.10.8", `--id` removed, new per-install identity | `D` | [S2] | Release-note wording, not independently tested |
| 9.1.0 is a bugfix release over 9.0.0 (audio gaps in `serve`, `--allow-unencrypted`, aiosendspin bump to 10.2.2) | `D` | [S2] | Nothing in 9.1.0 changes the client-side requirements below |
| 7.6.0 was never published to PyPI; 8.0.0 (2026-10-12) added encryption and pairing | `D` | [S2] | Historical context for upgrade notes only |
| Debra's lab installer pins `sendspin==9.1.0` (`SENDSPIN_VERSION`, default in the script) | `D` | repo `tools/device/lab-pi5/30-sendspin.sh` lines 6–14 | This is the pin the project intends; it is installed manually, not an appliance default |
| The lab device ran 9.1.0 and streamed FLAC 44.1 kHz/24-bit/2 ch to the HAT | `T` | repo `docs/testing/results/2026-11-15-lab-pi5-lva-sendspin.md` | One specimen, one session; proves delivery, not control or endurance |
| Protocol status is **1.0 Release Candidate 1**; the site says the protocol is frozen and only clarifications will land before final | `D` | [S15], [S18] | The newest spec tag is still `1.0.0-rc1`; `main` is at 9d2f15e (2026-11-11) ([S32]) |
| The CLI needs a server on Sendspin 1.0 / aiosendspin 10; README names "Music Assistant 2.10.7 or newer" | `D` | [S3] | Conflicts with the 9.0.0 note's "2.10.8" ([S2]); treat 2.10.8 as the safe floor |
| The official SDK page calls the **C++** CLI the recommended reference player and describes the Python client as "mainly a test and reference client" | `D` | [S18], [S15] | Standing/positioning statement; says nothing about whether 9.1.0 works |

**Debra pin answered:** `sendspin==9.1.0`, released 2026-10-27. Pin the
aiosendspin range too if reproducibility matters: 9.1.0 declares
`aiosendspin[server]~=10.2.2` ([S4]), which today resolves to **10.3.0**
(2026-11-02) — a moving transitive dependency behind a fixed top-level pin.

## 2. How a device is configured

### 2.1 Configuration file

| Claim | Label | Source | Limits |
| --- | --- | --- | --- |
| Settings are JSON in `~/.config/sendspin/`: `settings-tui.json`, `settings-daemon.json`, `settings-serve.json` | `D` | [S3] | Documented path; no system-wide or `/etc` location |
| The path is hard-coded as `Path.home()/".config"/"sendspin"`; **`XDG_CONFIG_HOME` is not consulted**. `--settings-dir` moves it | `D (code)` | [S5] | Code inspection only; on a systemd unit the value of `HOME` therefore decides the path |
| Every CLI argument can also be a config key; CLI wins over the file | `D` | [S3] | "Available settings" table lists 24 keys |
| Daemon defaults in code: `player_volume` 25, `use_mpris` true, `unpaired_access` true, `output_delay_ms` 0 (clamped 0–5000 on load) | `D (code)` | [S5] | README's example shows 50, not the default; do not copy the example as a default |
| The client's Noise identity lives in `identity-daemon.json`, created mode 0600, and its public key is the `client_id` | `D (code)` | [S5] | Losing this file makes the device a stranger to Music Assistant; pairing records live beside it in `pairing-store-daemon.json` |
| A pre-8.0 `client_id` in settings triggers a one-time "new device" warning | `D (code)` | [S5] | Consequence for upgrades: re-add to groups/automations |

Two consequences worth stating plainly. First, a Debra image that runs the
client as its own system user must give that user a writable home, because
identity, pairing store and settings all live under `~/.config/sendspin`.
Second, an image that writes settings from a config-management tool has to write
`settings-daemon.json` and leave `identity-daemon.json` alone after first boot,
or the device re-pairs every flash.

### 2.2 Command-line flags (daemon)

| Group | Flags | Label |
| --- | --- | --- |
| Connection | `--url`, `--port`, `--interface` | `D` ([S6]) |
| Identity | `--name`, `--manufacturer`, `--product-name`, `--settings-dir` | `D` ([S6]) |
| Audio | `--audio-device`, `--audio-format`, `--output-delay-ms` (deprecated alias `--static-delay-ms`) | `D` ([S6]) |
| Control | `--disable-mpris`, `--hardware-volume {true,false}`, `--unpaired-access {true,false}` | `D` ([S6]) |
| Integration | `--hook-start`, `--hook-stop`, `--hook-set-volume` | `D` ([S3], [S6]) |
| Diagnostics | `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}` | `D` ([S6]) |

`--port` is the *listening* port for server-initiated mode only; it is not the
port used with `--url`.

### 2.3 Discovery versus being told

| Claim | Label | Source | Limits |
| --- | --- | --- | --- |
| With no `--url`, the daemon listens for incoming servers and advertises `_sendspin._tcp.local.`; the spec recommends port **8928** and requires a TXT `path` (recommended `/sendspin`) | `D` | [S12], [S3], [S6] | This is the mode the lab uses (MA connects to the Pi) |
| With `--url`, the client connects out to `ws://host:8927/sendspin` (server's port) and must not advertise `_sendspin._tcp` | `D` | [S12], [S3] | Client-initiated mode gives up multi-server arbitration |
| Client-initiated discovery of servers uses `_sendspin-server._tcp.local.`; the client may also be told a URL directly | `D` | [S12], [S10] | `sendspin servers list` is the diagnostic command ([S3]) |
| Connections are plain `ws://` with Noise inside the WebSocket payload; mDNS-discovered endpoints must not use `wss://` | `D` | [S12] | Implies no TLS certificate management on the device |
| The client rejects an upgrade request carrying an `Origin` header | `D` | [S12] | Security-relevant for anything proxying the port |
| The daemon's default listen port is **8928** | `D (code)` | [S6] line 879, [S7] line 45 | README's settings table says "default: 8927" — that is the *serve* default ([S6] line 693). Trust the code, and set `--port` explicitly |
| `--interface <IP>` restricts both the mDNS advertisement and the listening socket to that address | `D` | [S3], [S6] | Requires a stable, already-assigned address; see §4 |
| The daemon hands incoming sockets to aiosendspin, which arbitrates between servers and displaces the loser with `client/goodbye` reason `another_server` | `D (code)`, `D` | [S7], [S12] | Log line in the lab record ("Admitted server …") matches this path |

The practical reading: on a Debra device, mDNS is not optional plumbing. It is
the default and recommended discovery path, and it is also the path whose
failure mode is "silent, device simply never appears".

## 3. Clock synchronisation and buffering

### 3.1 What the protocol requires

| Claim | Label | Source | Limits |
| --- | --- | --- | --- |
| The client sends `client/time` bursts: each message after the previous reply, at least **8 messages per burst**, bursts starting **no more than 10 s apart**; the server answers with four timestamps | `D` | [S13] | Server may drop a request while an earlier reply is outstanding |
| The client must translate server timestamps with the **time filter**: a two-dimensional Kalman filter over offset and drift; a C++ reference implementation exists | `D` | [S13], [S18] | Not optional — the spec's accuracy targets are defined against the filter |
| A player must not send its initial `client/state` until the filter has at least one measurement | `D` | [S13] | Combined with the availability rule below, this is the "device appears late" behaviour |
| Steady state: error within **±1 ms** (aim ±0.5 ms), speed within **±0.5%**, soft-correct when it can be fixed within 10 s, otherwise snap in one shot on start/underrun | `D` | [S14] | Measured at the audio output, against the filter's prediction |
| Late chunks should be dropped; partly late chunks may be decoded with the late prefix dropped | `D` | [S14], [S15] | Both strategies keep codec state; the guide discusses the trade-off |
| `output_delay_ms` compensates delay *after* the audio port (amplifier, speakers), not DAC/buffer latency, which the client compensates itself; it must persist across reboots | `D` | [S14] | 0–5000 ms |
| The client must report `required_lead_time_ms` (start trigger to first fully playable chunk) and `min_buffer_ms` (ongoing jitter buffer, from the upper tail of arrival delay) | `D` | [S14], [S15] | Server treats lead time as a hint; `min_buffer_ms` is what keeps live streams fed |

### 3.2 What the client actually does (9.1.0 / aiosendspin 10.3.0)

| Claim | Label | Source | Limits |
| --- | --- | --- | --- |
| Time measurements use **`CLOCK_MONOTONIC_RAW` on Linux**, chosen because NTP/adjtime slewing would poison the filter | `D (code)` | [S20] | Consequence: wall-clock discipline on the device is irrelevant to sync, but suspend/resume is not handled by that clock (see §9) |
| Burst interval adapts: 0.2 s while unsynchronised, then 0.2–3 s depending on measured error | `D (code)` | [S19] | Code only; no prose equivalent |
| "Synchronised" means filter count ≥ 2 with finite covariance; until then the player is reported **unavailable** on the wire | `D (code)` | [S19], [S20] | So a Music Assistant player can be connected and still show unavailable for the first seconds |
| While unsynchronised, play-time mapping falls back to "now + **500 ms** lead − output delay" | `D (code)` | [S19] | Fallback only; it is not a sync guarantee |
| Reported timing defaults are `required_lead_time_ms` **250 ms** and `min_buffer_ms` **250 ms** | `D (code)` | [S21] | CLI does not override them, so 250/250 is what a Debra device advertises |
| The CLI advertises `buffer_capacity` **32 000 000 bytes** | `D (code)` | [S7] | ~111 s at 48 kHz/24-bit stereo by arithmetic (`H`) |
| Playback starts once the queue holds **16 chunks or 200 ms** of audio, whichever comes first | `D (code)` | [S8] | Chunk duration is server-chosen. A `_MIN_CHUNKS_TO_MAINTAIN = 8` constant exists but is never referenced, so the "keep 8 in hand" comment is not enforced code |
| PortAudio stream: blocksize **2048 frames**, `latency="high"`, opened at the negotiated rate/depth/channels | `D (code)` | [S8] | ~46 ms per block at 44.1 kHz; "high" is the client's deliberate choice |
| Sync correction: ±0.2% speed, 2 ms deadband, 750 ms grace after start, re-anchor above 500 ms error | `D (code)` | [S8] | Tighter than the spec's ±0.5%; a Debra device gets the stricter implementation |
| Buffer exhaustion pads with **silence**; a PortAudio underflow requests re-anchor and clears the queue | `D (code)` | [S8] | No error is raised to the server and the stream stays "active" |

### 3.3 What that demands of the network and the audio device

- **Network:** working multicast DNS on the playback VLAN, TCP to the listening
  port (8928 by default), and enough sustained throughput for the negotiated
  format. The spec sizes `min_buffer_ms` from the upper tail of arrival delay
  and explicitly says to "factor expected network delay/jitter (small on LAN/
  Wi-Fi, larger for remote or high-latency clients)" into it (`D`, [S14]).
- **Network hygiene matters more than raw bandwidth.** A reported Pi Zero 2 W
  case chased constant underflows through Wi-Fi power saving, CPU governor and
  a USB adapter before finding an access point saturated by mDNS traffic from a
  Homebridge instance; changing the advertiser fixed it (`R`, [S26]). That is
  one user's diagnosis, but it is consistent with the protocol's
  jitter-tail sizing and with mDNS being the discovery mechanism.
- **Audio device:** an output PortAudio can open, at the negotiated rate and bit
  depth, without resampling surprises. The client probes 44.1/48/96/192 kHz and
  16/24-bit, mono and stereo, then advertises the Cartesian product, assuming
  the sound server converts (`D (code)`, [S9]). A preferred format that the
  device cannot open is a **startup error**, not a fallback (`D (code)`, [S6]).
- **Exclusive access is not required, but sharing needs care.** The Python
  client opens the device for the stream and closes it on `stream/end`
  (`D (code)`, [S33] `_on_stream_end`), which is roughly the C++
  client's documented `--release-device` behaviour (`D`, [S22]).
- **A device that cannot switch sample rates without a gap should advertise one
  rate** and let the server resample (`D`, [S15] step 4). For a HAT codec this
  is usually the honest choice.

## 4. When the server disappears and comes back

| Claim | Label | Source | Limits |
| --- | --- | --- | --- |
| If chunks simply stop while the socket stays open, the client plays **silence** as the queue drains and then re-anchors; it does not stop, log a stream stop, or run the stop hook | `D (code)` | [S8], repo `tools/device/lab-pi5/sendspin.service` uses `Restart=always` for the process case | Code-derived; not observed on the wire |
| On an actual disconnect the daemon stops the audio worker, closes the device, resets format state and fires the `hook_stop` hook | `D (code)` | [S7], [S33] `handle_disconnect` | Hook fires only if `--hook-stop` is configured |
| Client-initiated mode reconnects forever with exponential backoff starting at **1 s**, capped at **300 s**, and resets the backoff on success | `D (code)` | [S7] lines 334–341 | Code only |
| The official guide instead specifies a **30 s** cap ("one second and doubling to a 30 second cap, with no limit on retries") | `D` | [S15] step 11 | Conflict with the implementation above; the guide is explicitly non-normative |
| Server-initiated mode has no client-side redial loop: the daemon listens, and the *server* reconnects | `D (code)` | [S7], [S15] step 11 | This is the lab's mode |
| A client admits one connection at a time by default, MAY admit more, displaces a lower-ranked server, and requires `server/activate` within 30 s of a provisional connection | `D` | [S12] | Multi-server behaviour is defined only in server-initiated mode |
| Time-filter state persists across a **re-handshake**, and open streams keep buffered data | `D` | [S12] | Whether a full TCP reconnect resets the filter was not inspected; do not assume re-handshake behaviour carries over |
| Resume is always a fresh `stream/start`, which clears the queue; the client holds no paused position | `D` | [S13], [S14] | Expect `required_lead_time_ms`-scale silence on resume, not a click |
| The shipping checklist says the device must "survive a server restart and a network drop, and come back without help" | `D` | [S15] step 14 | Acceptance criterion, not a Debra result |
| Debra's unit file carries ExecStartPre waiting for an IPv4 route because "if it starts before the link has a route it advertises nothing" | `R` | repo `tools/device/lab-pi5/sendspin.service` | Debra's own observation; not re-verified this run and not stated upstream |
| On the lab device the daemon is `Restart=always` with a 10 s delay, so a crash-loop is masked as slow recovery | `R` | repo `tools/device/lab-pi5/sendspin.service` | Debra configuration choice, not upstream default (`Restart=on-failure`, [S11]) |

Two behaviours a supervisor or UI must not misread:

1. **"Playing but silent"** is a legitimate state. If the server's process is
   wedged rather than closed, the client can sit in silence indefinitely with
   the stream still active.
2. **"Available false" at startup** is normal for the first seconds, because the
   player withholds availability until the time filter converges (`D (code)`,
   [S19]). A Debra health check that treats unavailable-at-boot as a fault will
   produce false alarms.

## 5. Platform assumptions

| Claim | Label | Source | Limits |
| --- | --- | --- | --- |
| Requires **Python ≥ 3.12**; classifiers list only 3.12 and 3.13 | `D` | [S4], [S1] | No statement about 3.14 |
| 10 wheels for 9.1.0: CPython 3.12/3.13 × manylinux x86_64, manylinux aarch64, macOS x86_64, macOS arm64, win_amd64, plus an sdist | `D` | [S1] | No `armv7l`, no `armv6l`, no musllinux |
| Runtime dependencies: `aiosendspin[server]~=10.2.2`, `aiosendspin-mpris~=2.1.1`, `av>=15`, `numpy>=1.26`, `pillow>=10`, `pulsectl-asyncio` (Linux only), `qrcode`, `readchar`, `rich`, `sounddevice`, `textual-image` | `D` | [S4] | Upper bounds are loose; today's resolution is aiosendspin 10.3.0, av 19.x |
| **PortAudio is a system dependency**; without it the client exits with "PortAudio library not found" and an apt hint | `D (code)`, `D` | [S6] lines 44–47, [S3] | Debra's installer comment says the same (repo `tools/device/lab-pi5/30-sendspin.sh` lines 3–4) |
| The C volume extension is **optional**: if it fails to compile the client falls back to numpy | `D (code)` | [S36] | So a missing compiler degrades CPU cost, not functionality |
| The upstream systemd installer creates a `sendspin` user, adds it to group `audio`, and runs with `SupplementaryGroups=audio`, `Restart=on-failure`, `After=network-online.target sound.target`, `XDG_RUNTIME_DIR=/run/user/<uid>` | `D` | [S11] | System service, not a user service; the lab deliberately differs |
| MPRIS integration needs Linux and the `mpris_api` package; the daemon adds the `controller` and `metadata` roles only when `use_mpris` is on | `D (code)` | [S7], [S35] | The availability check is an import check, not a D-Bus probe — see §6.3. Claim read from the 2.1.1 sdist, not a tagged commit |
| Hardware volume on Linux needs ALSA mixer access or a reachable PulseAudio/PipeWire; otherwise the client falls back to software volume, which is CPU-expensive | `D`, `R` | [S3], [S26] | Maintainer attributes underruns on small boards to software volume |
| `libpulse0` may be required in addition to PortAudio when PulseAudio libraries are present | `R` | [S24] | Reported install failure and fix; upstream later discussed handling it |

### 32-bit ARM

| Claim | Label | Source | Limits |
| --- | --- | --- | --- |
| Maintainer position: "I don't want to officially support 32-bit, as it's a dying arch and we cannot guarantee that it will always keep compiling" | `R` | [S24] (comment 2026-02-13) | A maintainer statement in an issue, not a README/spec statement |
| The 32-bit request issue was closed without support | `R` | [S25] | Closed 2026-01-23; includes a third-party armhf Docker workaround and Debra's own operator saying it worked on a Pi Zero W |
| A 32-bit install needs build dependencies (ffmpeg dev headers, libffi, python3-dev, jpeg/png/zlib) because dependencies compile | `R` | [S24] | Same issue reports `av` had no 32-bit wheels at the time |
| Today `av` 19.0.2 does ship a `manylinux_2_31_armv7l` wheel, but `numpy` 2.5.4, `pillow` 13.0.0 and `cffi` 2.1.1 publish **no** `armv7l` wheel, and nothing publishes `armv6l` | `D` | [S30] plus the same PyPI JSON query per package, checked 2026-11-15 | Latest-version snapshots only; an older pin could resolve differently. piwheels may fill gaps — third party, not Sendspin |
| `pip`/`uv` therefore either builds from source on armv7 or fails; `av` needs recent glibc (manylinux_2_31) | `H` | Derived from [S30] | Not executed in this run |
| The C++ client is the upstream 32-bit path: v0.4.0 (2026-10-15) publishes `linux-armv6`, `linux-armv7`, `linux-arm64`, `linux-x86_64`, `macos-arm64` | `D` | [S31] | Different program: different config, different features |
| Its Pi guide documents the mapping `armv6l` → `linux-armv6` (build on an emulated Raspbian container), `armhf` → `linux-armv7`, and that `linux-armv7` needs glibc 2.38 (trixie) while `linux-armv6` loads on bookworm | `D` | [S23] | Explicit ARMv6/32-bit documentation that the Python client does not have |

**Answer for Debra's Zero W goal:** the Python client has no supported 32-bit
path. Reaching it means source builds on ARMv6 with no upstream promise, or
switching the receiver to `sendspin-cpp-cli`, which is a different component
with its own configuration and integration work. Neither is a drop-in for the
pinned 9.1.0 lab install.

Two platform facts that are easy to miss and matter for a Debra image:

- `aiosendspin-mpris` gates on `sys.platform == "linux"` and an import
  (`D (code)`, [S35]). It does **not** verify a session
  bus. A headless image without D-Bus can therefore still advertise the
  `controller` role, with MPRIS failing at runtime.
- The Python client's `CLOCK_MONOTONIC_RAW` choice (`D (code)`, [S20]) means an
  NTP step or a wall-clock jump does not disturb sync — but it also means the
  device must not suspend mid-playback; see §9.

## 6. Coexisting with a voice assistant: ducking and resuming

### 6.1 What Sendspin documents

| Claim | Label | Source | Limits |
| --- | --- | --- | --- |
| There is **no duck command, duck level, announcement message or announcement role** anywhere in the specification | `D` | [S12], [S13], [S14] full text search for "duck"/"announce" | Only one occurrence of "ducking" exists, quoted next |
| The single documented mention is cleanup: on role removal the client must "release temporary output effects applied by that role, such as ducking" | `D` | [S13] | This presupposes an implementation-defined duck, it does not define one |
| The official guide lists "announcements and chimes" among things the specification "deliberately leaves out" and that "may arrive as new roles" | `D` | [S16] | Strongest available statement that ducking/announcements are out of scope today |
| `player.volume` is a 0–100 **perceived loudness**, converted as `(volume/100)^1.5`, applied over a ramp, with mute independent; every change, including a device-side one, must be reported to the server | `D` | [S14] | A duck implemented as player volume is therefore a *published, persistent* state change, not a private trim |
| The protocol's coexistence mechanism is `available`: `false` means "in use by an external system and will not yield"; the server moves the client to a solo group, sends `stream/end`, and must not auto-rejoin or restart it on return | `D` | [S13] | Returning requires an explicit `switch` |
| `client/leave` is the softer variant: leave the group but stay available, for interruptible activity | `D` | [S13], [S15] step 10 | Ends no stream by itself |
| Pause exists only through the controller role, as a *request to the server*; the server then ends the player stream and sends a new `stream/start` on resume | `D` | [S13], [S14] | Not a device-side pause |
| The guide advises `available: false` only when the device will not yield, and `client/leave` when Sendspin may take it back at any moment | `D` | [S15] step 10 | Written for HDMI/Bluetooth input takeover, not for ducking |
| A voice satellite that plays nothing can be a **controller-only** client, acting on the group it is in (play/pause/volume) | `D` | [S17] | That is a separate protocol client; LVA is not one today, and it does not give a duck |

### 6.2 What the pinned client offers in practice

| Claim | Label | Source | Limits |
| --- | --- | --- | --- |
| The Python CLI exports exactly three integration hooks: `hook_start`, `hook_stop` (with `SENDSPIN_*` env vars) and `hook_set_volume` (effective level 0–100) | `D` | [S3], [S6] | No duck hook, no "external playback" hook |
| With `--hardware-volume true` (daemon default) on PulseAudio/PipeWire the client writes the **sink** volume, not a per-stream gain | `D (code)`, `D` | [S34], [S3] | This is the same control a voice assistant's replies use on the lab device |
| The CLI never calls `send_available`/`client/leave`; nothing in it reports "an external system is using the output" | `D (code)` | [S7], [S33], [S6] | So `available:false` and `client/leave` are protocol features the pinned CLI does not expose |
| MPRIS enables the `controller` role, which is the only device-side pause/next/previous path in the CLI | `D (code)` | [S7] | Disabling MPRIS removes the device's only pause, as the earlier transport map concluded |
| Music Assistant's Sendspin provider has no duck: announcements relay through a Home Assistant media-player entity when one is configured, and the provider drops its volume support while relaying | `D (code)` | [S29] `set_hass_announce_entity`, `announcement_features` | The docstring's "ducking" refers to ESPHome devices, not Sendspin clients |
| Linux Voice Assistant ducks **its own** mpv music player to 50% during a conversation and pauses it for `announce: true` media announcements | `D` | [S27] | LVA's music player exists only to play media sent by Home Assistant |
| LVA's behaviour guide never mentions Sendspin, Snapcast or any external player; its music player is mpv with `--music-output-device` | `D` | [S27], [S28] | So LVA has no path today to duck a separate receiver |
| LVA targets x64 and ARM64 only, with PulseAudio and libmpv | `D` | [S28] | Relevant to any combined device plan; a Zero W cannot run both |

### 6.3 What a music receiver must do (analysis)

This subsection is `H` unless a row says otherwise. It is a design conclusion
from the documented mechanisms above, not an upstream statement.

1. **Keep a duckable gain stage that is not the protocol's player volume.**
   Player volume is reported, persisted and used for group-volume arithmetic;
   ducking through it rewrites Music Assistant's view and, with hardware volume
   enabled, moves the shared sink that the assistant's replies also use. A local
   sink-input gain or a filter node is invisible to the server and does not
   corrupt its state. The lab record already documents the shared-sink failure
   mode: an assistant reply inaudible because the one sink was at 9 % (`T`,
   repo `docs/testing/results/2026-11-15-lab-pi5-lva-sendspin.md` lines 99–109).
2. **Prefer duck over pause for short utterances.** A protocol pause ends the
   stream; resuming costs a new `stream/start` and a lead time on the order of
   the client's advertised 250 ms plus buffer, and the client keeps no paused
   position. Ducking keeps the timeline continuous.
3. **Own the trigger.** Nothing upstream will tell the receiver that a wake word
   fired. Debra needs its own signal (LVA event, PipeWire node activity
   detection, or an explicit hook) and its own restore, because LVA will not
   touch a separate receiver's volume.
4. **Release temporary effects when roles change.** If a duck is implemented
   inside a Sendspin-adjacent component, dropping the role must restore the
   level — that is the one ducking-related rule the spec does state.
5. **If the receiver must surrender the output**, report `available: false` and
   expect to be parked in a solo group with no automatic return. Do not use that
   for a duck: it is a stop with extra steps.

### 6.4 Traps specific to duck/resume

- **Hardware volume turns the receiver into a second master-volume writer.**
  Daemon mode defaults it on. On the lab device, `PULSE_SERVER` and a shared
  PipeWire session mean Music Assistant's volume slider moves the assistant's
  reply level (`D (code)` + `T` above).
- **MPRIS's availability check is an import, not a bus probe.** A headless
  image can advertise a controller role whose MPRIS service never appears; the
  device then has a pause capability on paper and none in practice.
- **`available:false` is not a duck.** It stops the group and requires an
  explicit `switch` to come back; a coordinator that treats it as "quiet for a
  moment" will strand the player.
- **A duck written through `hook_set_volume` becomes the reported volume.** The
  hook receives the effective level and the setting is persisted; restoring
  "after" needs the pre-duck value stored somewhere Debra controls.
- **Do not assume ESPHome's ducking behaviour transfers.** Music Assistant's
  comment about native ducking is about ESPHome devices reached through a Home
  Assistant entity, a different code path from a Sendspin client (`D (code)`,
  [S29]).

## 7. Consolidated device requirement checklist

| Requirement | Detail | Label | Source |
| --- | --- | --- | --- |
| OS/runtime | Linux with Python ≥ 3.12 (3.12/3.13 supported), 64-bit x86_64 or aarch64 for wheels | `D` | [S1], [S4] |
| Audio stack | PortAudio (`libportaudio2`), plus ALSA mixer or PulseAudio/PipeWire for hardware volume | `D` | [S3], [S6] |
| Output device | Opens at 44.1/48 kHz, 16/24-bit, 2 ch (1 ch optional); accepts 2048-frame blocks | `D (code)` | [S8], [S9] |
| Clock | Stable monotonic clock; `CLOCK_MONOTONIC_RAW` used on Linux; no suspend during playback | `D (code)`, `H` | [S20] |
| Network | Working mDNS multicast; inbound TCP on the listen port in server-initiated mode; steady throughput with low jitter | `D` | [S12], [S14] |
| Storage | Writable `~/.config/sendspin` for settings, 0600 identity and pairing store | `D (code)` | [S5] |
| Service | Runs as a user service with a session bus for MPRIS, or a system service with group `audio` | `D`, `D (code)` | [S11], [S7] |
| Time source | No dependency on NTP correctness (raw clock), but NTP is still wanted for logs/TLS | `D (code)` | [S20] |
| Supervision | Restart policy, and a route-wait before advertising | `R` | repo `tools/device/lab-pi5/sendspin.service` |
| 32-bit ARM | Not supported for the Python client; C++ client has armv6/armv7 binaries | `D`, `R` | [S1], [S24], [S31] |
| Duck interface | None in Sendspin; Debra must build or bridge one | `D` | [S16], [S13] |

## 8. Traps found while reading

1. **The README's port table contradicts the code.** `listen_port` is
   documented as "default: 8927" for daemon *and* serve ([S3]); the code uses
   8927 for `serve` and 8928 for `daemon` ([S6]). Set `--port` explicitly.
2. **The version floor disagrees with itself.** README says Music Assistant
   2.10.7+, the 9.0.0 release note says 2.10.8 ([S3], [S2]).
3. **A fixed `sendspin==9.1.0` pin does not fix `aiosendspin`.** The declared
   range allows 10.3.0 today ([S4], [S1] of aiosendspin). Behaviour lives in
   the library, not the wrapper.
4. **`XDG_CONFIG_HOME` is ignored.** Image-building assumptions that "config
   goes where XDG says" are wrong for this client ([S5]).
5. **Silence is not a failure signal.** If the server stops sending without
   closing, the client pads with silence and keeps the stream open ([S8]).
6. **Underflow logs are the client's, not the network's.** The reported Pi Zero
   2 W thread shows underflows from software volume CPU cost and from mDNS
   flooding, not only from weak signal ([S26]).
7. **The reconnect cap is 300 s in code, 30 s in the guide.** A health check
   tuned to the guide will call a healthy client dead ([S7], [S15]).
8. **`available:false` has a one-way door** — no auto-rejoin, no restart
   ([S13]).
9. **MPRIS "available" is an import check**; a bus-less image can advertise
   capabilities it cannot serve ([S35]).
10. **32-bit advice in issues is stale in both directions.** The "no av wheels"
    statement from 2026-02 is no longer true for `av` at 19.x, while `numpy`,
    `pillow` and `cffi` still have no `armv7l` wheels today ([S24], [S30]).
11. **The upstream installer still writes a `client_id` key** that 9.1.0 no
    longer reads (identity comes from the keypair). Harmless, but it makes a
    config look authoritative when it is not ([S11], [S5]).
12. **`--port 8927` collides with Music Assistant's own Sendspin server** on a
    single-box lab layout; the lab moved the player to 8928 (repo
    `tools/device/lab-pi5/sendspin.service` line 14).

## 9. Unknowns and not verified

- `U` — No measurement of the lab device against any of the timing numbers in
  §3. The 250 ms/250 ms figures are what the client *advertises*, not what a Pi
  achieves.
- `U` — Whether a sink-input volume change on the Sendspin stream is republished
  to Music Assistant as player volume. Code suggests the PulseAudio backend
  monitors the sink, not its own sink-input, but this was not tested.
- `U` — Whether a duck can be triggered reliably from LVA today. Nothing in
  LVA's behaviour documentation describes an external-player signal, and no
  PipeWire event source was examined in this run.
- `U` — How the time filter behaves across suspend/resume. `CLOCK_MONOTONIC_RAW`
  excludes suspend time, so the server↔client mapping should be wrong on wake
  until the filter reconverges; undocumented upstream and untested here (`H`
  that a full reconnect or re-anchor is needed).
- `U` — Whether 9.1.0 installs today on armv7 without building; the PyPI wheel
  metadata says it will not, but no resolver run was performed (see §10).
- `U` — Whether the household Music Assistant (a dev build) matches the `dev`
  branch inspected for §6.2, and whether its announce path is configured with a
  Home Assistant entity.
- Blocked: none. The Raspberry Pi documentation site was not needed; no page
  used here returned 403.
- `H` — The claim that a duck "must" sit below the protocol is design judgement
  from the documented volume/persistence semantics, not an upstream statement.

## 10. Source register

All URLs read 2026-11-15. Mutable pages are `main`/`dev` unless a tag or commit
is given.

| Key | URL | What it is |
| --- | --- | --- |
| S1 | https://pypi.org/pypi/sendspin/json | PyPI metadata and file list for sendspin 9.1.0 (version, requires-python, dependencies, wheel tags, upload times) |
| S2 | https://github.com/Sendspin/sendspin-python-cli/releases | Release notes for 9.1.0, 9.0.0, 8.0.0, 7.6.0 (also read via `api.github.com/repos/Sendspin/sendspin-python-cli/releases`) |
| S3 | https://github.com/Sendspin/sendspin-python-cli/blob/9.1.0/README.md | Install, configuration, flags, discovery, pairing, ports, hooks, systemd install |
| S4 | https://github.com/Sendspin/sendspin-python-cli/blob/9.1.0/pyproject.toml | Python floor, dependency ranges, classifiers |
| S5 | https://github.com/Sendspin/sendspin-python-cli/blob/9.1.0/sendspin/settings.py | Config path, defaults, identity and pairing files, migration warnings |
| S6 | https://github.com/Sendspin/sendspin-python-cli/blob/9.1.0/sendspin/cli.py | Argument definitions, port defaults (lines 693, 879), PortAudio error text, format validation |
| S7 | https://github.com/Sendspin/sendspin-python-cli/blob/9.1.0/sendspin/daemon/daemon.py | Roles, buffer capacity, connection loop, backoff, disconnect handling, port default |
| S8 | https://github.com/Sendspin/sendspin-python-cli/blob/9.1.0/sendspin/audio.py | Buffer thresholds, PortAudio stream settings, sync correction, silence padding, underflow |
| S9 | https://github.com/Sendspin/sendspin-python-cli/blob/9.1.0/sendspin/audio_devices.py | Format probing and advertised format matrix |
| S10 | https://github.com/Sendspin/sendspin-python-cli/blob/9.1.0/sendspin/discovery.py | mDNS service types and URL construction |
| S11 | https://github.com/Sendspin/sendspin-python-cli/blob/9.1.0/scripts/systemd/install-systemd.sh | Upstream systemd unit, user/group, dependency checks, config write |
| S12 | https://github.com/Sendspin/spec/blob/9d2f15ee8f172c67ce00dc0d9f6603c3b1030d9f/connection.md | mDNS records, ports, admission/arbitration, client-initiated mode, re-handshake state |
| S13 | https://github.com/Sendspin/spec/blob/9d2f15ee8f172c67ce00dc0d9f6603c3b1030d9f/messaging.md | Clock synchronisation, time filter, `client/state` availability, external source handling, `client/leave`, role-removal cleanup |
| S14 | https://github.com/Sendspin/spec/blob/9d2f15ee8f172c67ce00dc0d9f6603c3b1030d9f/roles/player/v1.md | Player state fields, volume curve, timing parameters, sync accuracy, buffer accounting |
| S15 | https://www.sendspin-audio.com/build/guide/client/ | Non-normative client implementation guide: components, persistence, convergence, timing, sync, reconnect, checklist |
| S16 | https://www.sendspin-audio.com/build/guide/roles/ | Shared role foundations; "roles that do not exist yet" (announcements, chimes) |
| S17 | https://www.sendspin-audio.com/build/guide/use-cases/ | Yield semantics for input takeover; controller-only voice satellite case |
| S18 | https://www.sendspin-audio.com/build/sdks/ | SDK/reference-player status, spec 1.0 at RC1, time-filter and conformance tools |
| S19 | https://github.com/Sendspin/aiosendspin/blob/10.3.0/aiosendspin/client/connection.py | Time-sync loop and interval, `is_synchronized`, unsynchronised lead, wire availability |
| S20 | https://github.com/Sendspin/aiosendspin/blob/10.3.0/aiosendspin/clock.py | `CLOCK_MONOTONIC_RAW` choice, monotonic/loop clock separation |
| S21 | https://github.com/Sendspin/aiosendspin/blob/10.3.0/aiosendspin/client/client.py | Default `required_lead_time_ms` / `min_buffer_ms` (250 ms each) |
| S22 | https://github.com/Sendspin/sendspin-cpp-cli/blob/main/README.md | C++ client: config file locations, ALSA/PortAudio, `--release-device`, hooks, service |
| S23 | https://github.com/Sendspin/sendspin-cpp-cli/blob/main/docs/wiki/Getting-Started-on-a-Raspberry-Pi.md | Documented armv6/armv7/arm64 selection and glibc constraints |
| S24 | https://github.com/Sendspin/sendspin-python-cli/issues/113 | 32-bit/ARM install dependency gaps; maintainer declines official 32-bit support; `libpulse0` |
| S25 | https://github.com/Sendspin/sendspin-python-cli/issues/56 | 32-bit request, closed without support; third-party armhf container workaround |
| S26 | https://github.com/Sendspin/sendspin-python-cli/issues/216 | Pi Zero 2 W underflows; software volume CPU; mDNS flooding as underlying cause |
| S27 | https://github.com/OHF-Voice/linux-voice-assistant/blob/main/docs/behavior.md | LVA ducking to 50%, announcement pause/resume, its own mpv music player |
| S28 | https://github.com/OHF-Voice/linux-voice-assistant/blob/main/README.md | LVA platform statement (x64/ARM64, PulseAudio, libmpv), device flags |
| S29 | https://github.com/music-assistant/server/blob/dev/music_assistant/providers/sendspin/player.py | MA Sendspin provider: announcement relay, volume-feature handling |
| S30 | https://pypi.org/pypi/av/json (and .../numpy/json, .../pillow/json, .../cffi/json) | Armv7l/armv6l wheel availability, checked 2026-11-15 |
| S31 | https://github.com/Sendspin/sendspin-cpp-cli/releases | C++ client v0.4.0 assets including `linux-armv6`, `linux-armv7` |
| S32 | https://github.com/Sendspin/spec (tags/commits) | Newest tag `1.0.0-rc1`; `main` HEAD 9d2f15e dated 2026-11-11 |
| S33 | https://github.com/Sendspin/sendspin-python-cli/blob/9.1.0/sendspin/audio_connector.py | Audio worker attach/start, stream start/end/clear handling, disconnect reset, format-change callback |
| S34 | https://github.com/Sendspin/sendspin-python-cli/blob/9.1.0/sendspin/hardware_volume.py | ALSA/PulseAudio hardware volume backends and sink monitoring |
| S35 | https://github.com/abmantis/aiosendspin-mpris | MPRIS adapter; the 2.1.1 sdist `aiosendspin_mpris/adapter.py` was inspected (no tag used) |
| S36 | https://github.com/Sendspin/sendspin-python-cli/blob/9.1.0/setup.py | Optional C extension build with numpy fallback |

## Handoff

Current state: read-only findings, no device or service touched, nothing
promoted. The pin is `sendspin==9.1.0` (2026-10-27) and it is the current
release. The device contract is Python ≥ 3.12 with 64-bit wheels, PortAudio, a
format-compatible output device, a writable `~/.config/sendspin`, working mDNS
and TCP, and a monotonic clock. Ducking is not a Sendspin feature: the protocol
offers published `player.volume`, a controller-role pause that ends the stream,
`client/leave`, and `available:false` with no auto-return, and the official
guide says announcements are not a role yet.

Next concrete check (bounded, no device): resolve the 9.1.0 dependency set for
an armv7 target offline-ish on a host, e.g.
`pip download --only-binary=:all: --platform manylinux_2_31_armv7l --python-version 3.12 --implementation cp sendspin==9.1.0 -d /tmp/opencode/ss-armv7`,
and record which packages fail. That settles §5's `H` without installing
anything on a Pi. It needs coordinator approval as normal work, not as a
consequence of this note.

Authorization: none implied. A ducking implementation, an MPRIS/bus probe, and
any 32-bit receiver decision remain design proposals for review.
