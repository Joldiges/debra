---
title: Corrections to the music transport and control map (R03)
date: 2026-11-15
type: project-learning
status: unreviewed
task: R03
author: OpenCode subagent
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - docs/notes/2026-11-15-research-notes-review-round-2.md, section "R03 — music transport and control map" (the finding list)
  - docs/notes/2026-11-15-music-transport-and-control-map.md (read at 466 lines, preserved unchanged)
  - docs/work/cards/R03.md; docs/evidence.md; docs/roadmap.md (A03)
  - docs/comparisons/music-playback.md; docs/design/first-boot.md; docs/design/audio-outputs.md
  - docs/research/2026-11-15-armv6-wheels.md; docs/notes/2026-11-15-armv6-audio-stack.md
  - docs/notes/2026-11-15-sendspin-client-requirements.md; docs/notes/2026-11-15-license-and-provenance-proposal.md
  - docs/testing/results/2026-11-15-lab-pi5-lva-sendspin.md; tools/device/lab-pi5/11-mixer.sh
  - https://api.github.com/repos/Sendspin/spec/git/ref/tags/1.0.0-rc1 and .../git/commits/671a34d4 — tag resolution, fetched 2026-11-15
  - https://raw.githubusercontent.com/Sendspin/spec/671a34d408581fc25ea56b3528a4a3f13e3be901/messaging.md and roles/player/v1.md — fetched 2026-11-15
  - https://raw.githubusercontent.com/badaix/snapcast/master/doc/json_rpc_api/control.md and doc/configuration.md — fetched 2026-11-15
  - https://www.music-assistant.io/player-support/snapcast/ — fetched 2026-11-15
supersedes: []
---

# Corrections to the music transport and control map

The protocol content of [R03](2026-11-15-music-transport-and-control-map.md) holds
up: on re-checking, the controller role, the `(v/100)^1.5` volume curve, the
`stream/end`-on-pause rule, Snapcast's `Stream.Control` forwarding, the ALSA-first
volume ordering and the HA-only-reaches-MA path are all as the note states. What
must not be relied on until corrected is (a) the revision provenance — the header
binds one hash to another commit's date, and most links resolve to a moving branch
— and (b) the split between `client/hello` and `client/state`, which the note's
prose merges and its own table only half-separates. Two card-required deliverables
are also absent: a source-backed ARMv6 constraint list and a licence line per
project. One review claim is overstated: Music Assistant's source entry does carry
a commit (line 26), it is just not used in the links.

## Findings

| id | sev | Current text (line) | Replacement | Verified how |
| --- | --- | --- | --- | --- |
| H1 | High | L11: "`main` @ 9d2f15ee8f172c67ce00dc0d9f6603c3b1030d9f, tag `1.0.0-rc1` (commit dated 2026-09-17)"; L124: "Spec tag `1.0.0-rc1` (commit dated 2026-09-17); `main` still moving (updated 2026-11-14)"; refs L439–443 all `.../main/...` | Split into two revisions and use one per project (form and inventory below). Spec claims rest on tag `1.0.0-rc1` = `671a34d408581fc25ea56b3528a4a3f13e3be901` (2026-09-17); the `9d2f15ee` hash is `main` HEAD, a different revision, and must not carry the rc1 date. Every `[sp-*]` link resolves to the pinned commit. | GitHub API: tag `1.0.0-rc1` → commit `671a34d4`, authored 2026-09-17. `docs/notes/2026-11-15-sendspin-client-requirements.md` L79/L451 records `main` HEAD as `9d2f15e`, dated 2026-11-11. So hash and date in L11 belong to two revisions. The review's description of `9d2f15ee`'s subject line was not re-fetched and is not load-bearing. |
| M1a | Medium | L131–134: "it advertises codecs/rates/bit depth, a buffer capacity, an `output_delay_ms`, `required_lead_time_ms`, `min_buffer_ms`, and `supported_commands`" | "The player role, in two messages: `client/hello`'s `player@v1_support` object carries `supported_formats` (codec, channels, sample rate, bit depth) and `buffer_capacity`; the `player` object in `client/state` carries `volume`, `muted`, `output_delay_ms`, `required_lead_time_ms`, `min_buffer_ms`, `supported_commands` and an optional `format` preference." | Read at `1.0.0-rc1`: `roles/player/v1.md` defines the hello support object with exactly two fields and the state object with the rest; `messaging.md` places `player@v1_support` in `client/hello` and `player` in `client/state`. |
| M1b | Medium | L146: "\| Client → Server \| `client/state` → `player` \| `volume`, `muted`, `output_delay_ms`, `supported_commands`, format preference \|" | Add the missing `required_lead_time_ms` and `min_buffer_ms` to this row, and add a `client/hello` → `player@v1_support` row for `supported_formats` and `buffer_capacity`. | Same read. The review said "the note's own table says so"; the table is only partly right — it puts `output_delay_ms`/`supported_commands` in `client/state` correctly but omits both timing fields from either row. |
| M2 | Medium | L90–92: "in daemon mode the Sendspin CLI's "hardware volume" is on by default and writes the *system sink* volume, not a per-stream gain" | "in daemon mode the Sendspin CLI's "hardware volume" is on by default, and which object it writes depends on the backend it selects: ALSA mixer first (`amixer`, elements `Digital`/`Master`/`PCM`), PulseAudio/PipeWire only when no ALSA element is found — and only that path writes the *system sink*. On the lab HAT the ALSA backend is the likely one, so the write lands on a card mixer element (`PCM Playback Volume` is what the lab's own mixer scripts set): card-wide, so the blast radius is unchanged, but it is not the sink." | R03's own L179–181 gives the ALSA-first order; `docs/testing/results/2026-11-15-lab-pi5-lva-sendspin.md` trap 3 lists the codec controls; `tools/device/lab-pi5/11-mixer.sh` sets `PCM Playback Volume`; `2026-11-15-armv6-audio-stack.md` L212: mixer elements belong to the card. Which backend the lab daemon chose is unrecorded. |
| M3 | Medium | L230–231: "Pause: **not through a documented interface**; closest mechanism is MA's stop+resume, or moving the group to a silent stream." | "Pause: **no receiver-level pause**. `Stream.Control` is documented and forwards `play`/`pause`/`stop`/`next`/`seek` to the stream's control script; a pause is refused with error 5, "Stream property canPause is false", when the source plugin does not offer it. The stream itself is continuous, so the closest mechanism when the source is not controllable is MA's stop+resume or a silent stream." | Fetched `doc/json_rpc_api/control.md` (a source R03 already lists): `Stream.Control` is "Same request as in Plugin.Stream.Player.Control" and its error table includes `canPause is false`. R03's own table row at L207 already says this, so the sentence contradicts the note. |
| M4 | Medium | L393–398: "lines 14–28 say ... are "unverified""; L399–403: "A03 states "no verified Sendspin pause/resume or independent attenuation interface exists yet (MPRIS is disabled)"" | Replace both bullets with: the correction has landed — `music-playback.md` L14–24 now says pause/resume and per-player volume are specified interfaces and that the device test is what is missing; `roadmap.md` A03 now says "The control interface exists; the device test does not." What remains: the curated page's Snapcast row (L30) still reads "R03 reports no receiver-level pause" and inherits M3, and its `stream/end`-in-practice cell is `U`, which M7 also fixes. | Read both current files. R03's quoted wording is no longer in either, so the section describes superseded text. |
| M5 | Medium | absent: no ARMv6 constraint list (§"Not verified" L430–433 defers it to the wheels note) and no licence line in 466 lines | Insert the two drafts in the next section. | `docs/work/cards/R03.md` L16–18 requires both; `docs/evidence.md` L64–68 requires licensing per software row. |
| M6a | Medium | L19: "release 10.3.0 (2026-11-02), protocol library used by MA and the CLI"; L127–128: "`aiosendspin` 10.3.0 (2026-11-02, Python, used by both MA and the CLI)" | "`sendspin-python-cli` 9.1.0 (2026-10-27) declares `aiosendspin[server]~=10.2.2`; the repository's wheel note records 10.2.2 as the resolved pin, so 10.3.0 is not what a 9.1.0 install gets. `aiosendspin` 10.3.0 (2026-11-02) is the newest release; its use by the household MA was not established." | `docs/research/2026-11-15-armv6-wheels.md` L80/L108 records the constraint and the 10.2.2 resolution. PEP 440 `~=10.2.2` admits 10.2.x only. Note a repository conflict I cannot edit: `2026-11-15-sendspin-client-requirements.md` L85/L226/L362–364 says the same range "resolves to 10.3.0", which that semantics contradicts; needs a coordinator fix there. |
| M6b | Medium | L125–127: "ESPHome states the device "needs a Sendspin 1.0.0-rc1 server, such as Music Assistant 2.11.0b4 or newer"" | Keep the ESPHome figure but label it ESPHome's: "ESPHome's hub requires a Sendspin 1.0.0-rc1 server and names MA 2.11.0b4 or newer. The Python CLI's own floor is lower: its README says MA 2.10.7+, its 9.0.0 release note says 2.10.8 — use 2.10.8 as the safe floor for the lab install." | `2026-11-15-sendspin-client-requirements.md` L80 and L360–361 record both CLI figures and the conflict; the ESPHome figure is R03's own citation. |
| M7 | Medium | L57–59: "Music Assistant receives that, pauses its own queue, and — per the same spec — ends the audio stream to the device (`stream/end`), restarting it with `stream/start` on resume" | "...pauses its own queue. The spec requires the server to end the player stream and send a new `stream/start` on resume; whether MA does that in practice was not observed (this note's own "Not verified" section; `music-playback.md` marks it `U`). The receiver holds no paused buffer either way." | R03 L415–418 says the wire behaviour is unobserved; `music-playback.md` L28 marks it `U`. The summary asserts what the note lists as unverified. |
| M8 | Medium | L226–227: "(`send_to_muted`, default `false` — [configuration.md][sc-conf])" | "(`send_to_muted` — Snapcast's page defines it as `true`/`false` and states no default; MA's Snapcast page says "Send audio to muted clients. Off by default", which is where `false` comes from)" | Fetched both pages: Snapcast `doc/configuration.md` lists the option with no default; MA's Snapcast page states "Off by default" for the built-in Snapserver. The value is right, the citation is not. |
| L1 | Low | L76–77: "with a defined perceptual curve, `amplitude = (volume/100)^1.5`" | "with a defined perceptual curve — the spec says clients SHOULD convert as `amplitude = (volume/100)^1.5`, so a compliant player may differ — and requires (MUST) the player to report every change". Also qualify L342's "`^1.5` curve" as SHOULD. | Read at rc1: "Clients SHOULD convert volume to a linear amplitude ... as `amplitude = (volume / 100)^1.5`"; the reporting rule is MUST. |
| L2 | Low | L249–250: "a client with a hardware MAC address that MA has seen before "joins the player of its device when there is one, as an audio output"" | Reword to MA's actual condition, which the reviewer reads as the *first* sighting of that MAC, not a repeat sighting; quote the sentence verbatim with its file and symbol. | **Unverified.** Not in any repository record; needs a source check against the pinned MA `providers/sendspin/README.md` before publishing. Do not adopt either wording from this table alone. |
| L3 | Low | L227–228: "Local changes are reported back (`notifyVolumeChange`), so the server's view stays truthful." | "On the PulseAudio backend, local changes are reported back (`notifyVolumeChange`); whether the ALSA, script and software modes report back the same way was not checked." | **Unverified** for the other modes; the PulseAudio scoping is the reviewer's reading of `player.cpp`/`pulse_player.cpp`, which I did not fetch. The correction is a narrowing, so it is safe to apply only after that check. |
| L4 | Low | L69–71: "The Python CLI only adds `controller@v1` when MPRIS is enabled, and MPRIS is on by default" | "The Python CLI adds `controller@v1` and `metadata@v1` only when MPRIS is enabled (on by default), and the gate is an import of `mpris_api` on Linux, not a session-bus probe — so a headless image can advertise the role with no working MPRIS service." | `2026-11-15-sendspin-client-requirements.md` L230 and L254–257; `armv6-wheels` trap 6 (no D-Bus session, `mpris-api` declares no dependencies). Both are repository records of upstream code. |
| L5 | Low | L54–56 summary: "A client that lists the `controller@v1` role can send `client/command` with `command: 'pause'`" | Add: "nothing is usable until the server sends `server/activate` after the Noise handshake, and the spec requires it within 30 s of a provisional connection." | `messaging.md` at rc1: "The server MUST NOT send other Sendspin messages until it sends the initial `server/activate`"; the 30 s figure is repository-recorded (`sendspin-client-requirements.md` L203), not re-fetched. |
| L6 | Low | L102–103: "The org's own summary is "an open standard for the complete music listening experience: listen, control & see"" | Attach the URL the sentence came from (sendspin-audio.com or the spec README) and mark the quote `upstream-documented` with its page date. | **Unverified:** the quote is not in the spec files I fetched, and the note gives no URL. Needs a source check; if no page carries it, drop the quote and use `SCOPE.md`'s own wording, which the note already cites. |
| L7 | Low | refs L449 `[ma-ss-player]` and L451 `[ma-vol]` name whole files | Cite the symbol: e.g. `providers/sendspin/player.py` `set_player_volume` / `play_announcement`, and the group-volume snapshot in `controllers/players/volume.py`. | The better pattern already exists in the repository (`sendspin-client-requirements.md` cites `set_hass_announce_entity`, `_on_stream_end`). Which of these two files is 3,154 lines was not checked, so the finding's "3,154-line file" detail is unverified. |

## H1: the revision question needs a coordinator decision

A note cannot pick the pin for a packet that says "select no pins"
(`docs/work/cards/R03.md` L20). What it can do is stop mixing revisions. The
corrected header form is one revision per project, and every link in the note
resolving to that revision:

```yaml
sources:
  - https://github.com/Sendspin/spec — tag 1.0.0-rc1 = commit 671a34d408581fc25ea56b3528a4a3f13e3be901 (2026-09-17); every spec link resolves to this commit, checked 2026-11-15
  - https://github.com/Sendspin/sendspin-python-cli — tag 9.1.0 (2026-10-27); every CLI link resolves to the tag, checked 2026-11-15
  - <one line per project, same shape>
```

| Project | What the repository records | Status |
| --- | --- | --- |
| Sendspin spec | rc1 = `671a34d4` (2026-09-17), resolved by API this session; `main` HEAD `9d2f15e` (2026-11-11) per the client-requirements note | Resolved: pin rc1, relink |
| sendspin-python-cli | 9.1.0 released 2026-10-27; `main` commit `e9a80e6` (2026-10-29) recorded in the wheels note, two days after the release | needs coordinator decision — pin per project (tag 9.1.0 is the obvious choice; the repository already cites `blob/9.1.0/...` elsewhere) |
| aiosendspin | 10.3.0 released 2026-11-02; `main` commit `2174cdc` (2026-11-12) in the wheels note; CLI constraint `~=10.2.2` | needs coordinator decision — pin per project (release or the resolved 10.2.2, not both) |
| aiosendspin-mpris | 2.1.1; inspected from the sdist, "not a tagged commit" | needs coordinator decision — pin per project |
| Snapcast | R03 cites release v0.35.0 but reads `master`; no commit recorded anywhere in the repository; the licence record is for v0.31.0 | needs coordinator decision — pin per project |
| Music Assistant | `dev` @ `ecb5f3562faf37abb6b06676f758943d26ecc38a` is given at L26 but the links resolve to `dev`; household build is `2.11.0.dev2026111103` | Consistency only: put the commit in the links. No new decision needed |
| HA core | `dev`, no commit | needs coordinator decision — pin per project |
| ESPHome | Mutable documentation site, not a repository file | No pin possible; cite the page with its read date |

Two adjacent facts worth carrying into A03 while the pin is decided. MA documents
that an external Snapcast server must be 0.27.0 or newer, that 0.28.0 is 64-bit
only and that 0.30.0 "cannot be used" — so "Snapcast v0.35.0" is a release note,
not a supported floor, and the architecture caveat matters for a Zero W. And the
household MA being a dev build means the `dev`-branch reading in R03 §3 may not
describe the server that is actually running; that is already in R03's open
questions and stays open.

## M5: the two missing deliverables, drafted

### ARMv6 constraint list (draft, from repository records)

A constraint list, not a support promise: nothing here was run on an ARMv6 board.

| Constraint | What the record says | Source | Label |
| --- | --- | --- | --- |
| Instruction set of the OS packages | Debian armhf requires ARMv7 + VFPv3-D16 and its PipeWire/WirePlumber objects are tagged v7; the Raspbian armhf rebuild is v6/VFPv2 with NEON chosen at runtime from `/proc/cpuinfo` | [armv6 audio stack](2026-11-15-armv6-audio-stack.md) §2 | `observed` (ELF inspection), not run |
| Python client on 32-bit ARM | 9.1.0 publishes no `armv7l` or `armv6l` wheel; the maintainer declines official 32-bit support; a 32-bit install is a source build | [client requirements](2026-11-15-sendspin-client-requirements.md) §5 | `upstream-documented` + `reported` |
| Dependency ceilings for a 32-bit target | Pin `av==16.1.0`, `numpy<=2.2.1`, `zeroconf==0.151.5`; `linux_armv6l` is an ABI label, not an instruction-set promise | [ARMv6 wheels](../research/2026-11-15-armv6-wheels.md) | `observed` (wheel/sdist inspection) |
| System libraries | `libportaudio2` is a hard runtime dependency; `libpulse0` for the volume path; LVA's `soundcard` needs the unversioned `libpulse.so` from `libpulse-dev` | lab result trap 6; [ARMv6 wheels](../research/2026-11-15-armv6-wheels.md) | `upstream-documented` / `observed` |
| The pause path is the weakest one | The controller role needs MPRIS; `mpris-api` declares no dependencies (so `dbus-next` can be missing) and nothing probes for a session bus, which a headless image may not have | wheels trap 6; client requirements L230, L254–257 | `upstream-documented` (code) + `hypothesis` |
| Only upstream ARMv6 binary | `sendspin-cpp-cli` v0.4.0 ships `linux-armv6`; it is a different program with its own config, not a drop-in for the pinned 9.1.0 | client requirements §5 | `upstream-documented` |
| Memory | 512 MB board; LVA's own documented floor is 512 MB; the audio stack's share (35–70 MB) is arithmetic on desktop data, unmeasured on ARMv6 | [armv6 audio stack](2026-11-15-armv6-audio-stack.md) §4 | `hypothesis` / `unknown` |
| Snapcast on ARMv6 | Nothing in the repository records it; MA's docs constrain server versions, not architectures | — | `unknown` |
| Music Assistant on ARMv6 | Not applicable to the device: MA runs as an app on the household HA host, not on the Pi | lab result trap 11 | `reported` (repository record) |

### Licence line per project (draft, from repository records)

No licence value is invented here. "Not recorded" means the repository contains
no licence statement for that project, not that it has none.

| Project | Licence as recorded | Where | Label |
| --- | --- | --- | --- |
| Sendspin spec | not recorded | — | `unknown` |
| sendspin-python-cli | Apache-2.0 (LICENSE at `e9a80e6`) | [licence proposal](2026-11-15-license-and-provenance-proposal.md) L61 | `upstream-documented` |
| aiosendspin | not recorded | — | `unknown` |
| aiosendspin-mpris | not recorded | — | `unknown` |
| Snapcast | GPL-3.0-or-later, with named LGPL-2.1-or-later, zlib and MIT/Expat exceptions — recorded for **v0.31.0**, while R03 cites v0.35.0 | licence proposal L62 | `upstream-documented`, version mismatch to re-check |
| Music Assistant server | not recorded | — | `unknown` |
| HA core | not recorded | — | `unknown` |
| ESPHome | not recorded | — | `unknown` |
| PipeWire (device layer, §4) | MIT except its ALSA plugin (LGPL) and JACK server (GPL2) | licence proposal L64 | `upstream-documented` |
| PulseAudio / `pactl` (device layer) | not recorded | — | `unknown` |
| Linux Voice Assistant (co-resident on the lab device) | Apache-2.0; its code licence does not clear its models or sounds | licence proposal L61 | `upstream-documented` |

Consequence to state in the map, not just the table: Snapcast is the one
copyleft component in this set, so shipping `snapclient` unmodified in an image
already carries notice and corresponding-source obligations, and patching it adds
more. That is F04's territory, but R03's own recommendation order (Sendspin first,
Snapcast as fallback) should not read as licence-neutral.

## What remains unknown

- Which commit each project's claims rest on, and therefore which links in R03
  must be rewritten: the coordinator's decision, listed per project above.
- Whether MA emits `stream/end` on pause in practice — unobserved, and now stated
  as unobserved rather than asserted.
- Which hardware-volume backend the lab daemon selected, and therefore whether the
  lab device's "hardware volume" writes a codec element or the sink.
- Whether the CLI republishes a sink-input change as player volume (`hypothesis`).
- Whether 9.1.0 installs at all on armv7/armv6 without a source build: no resolver
  run was performed.
- Which `aiosendspin` the household MA actually uses.
- The reviewer's MAC-registration condition (L2), the `notifyVolumeChange` scope
  beyond PulseAudio (L3), the org quote's URL (L6) and the 3,154-line file (L7) —
  all need a source check, and none is applied here.
- Whether the household MA dev build matches the `dev` branch R03 read.
- Snapcast's behaviour on ARMv6, and its version floor on a 64-bit-only release.

## What I did not do

I edited no tracked file except this one; I ran no git command, contacted no
device, installed nothing, played nothing, and did not re-review R03 on an
independent model — the review round that produced these findings shares R03's
author model, so these corrections are source-checked, not model-independent.
