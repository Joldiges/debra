# Browser-first device control

**Requirements and acceptance detail, 2026-11-15; not a supported-product claim.**
James wants ordinary configuration at a device address such as
`debra-1234ca.local`, without SSH. Native volume is the first useful slice.
The [roadmap WEB packets](../roadmap.md#browser-first-device-control) own task
state; this page expands their scope rather than creating a second TODO ledger.

## Immediate slice: Audio, Device, Health, Components

The [prototype](../../control/web/README.md) implements only native selected-sink
volume/mute and read-only inspection. Installation/identity/complete component
management are not implied by a web page existing.

| Section | Required behavior / follow-up |
| --- | --- |
| Audio | Actual native output level, mute, explicit sink identity and availability; preview then Apply; no test sound or startup/poll write; external changes visible |
| Device | Detected board/revision/architecture and detected versus selected HAT; retained speaker label; no automatic speaker identification claim |
| Health | Total/per-core CPU, RAM, storage, uptime, temperature, Wi-Fi strength, CPU-core voltage, current/historical voltage warnings and separate 5 V supply reading where available |
| Compression | Swap used/total and I/O, zram original/compressed/resident bytes and ratio; zswap enabled/pool/hits/rejects when a safe collector exists; distinguish counters from throughput/performance benchmarks |
| Components | LVA, Sendspin, Snapcast and Bluetooth proxy separately; show installed, enabled, configured, running, connected and actually working as different facts with timestamp/evidence |

Missing, unsupported, stale and not-yet-implemented readings must be explicit,
not zero, healthy-green, or silently omitted. A service can run while audio is
silent or pairing is broken. CPU-core voltage is never the 5 V supply. Warnings
alone do not request or justify a reboot/reset.

## Configuration coverage

### Hardware and audio — WEB03/WEB05

- Select exact board/HAT/revision from evidence-backed profiles; display detected
  versus user-selected information, wiring/power constraints, driver/overlay
  state and restart/reboot requirements before applying.
- Retain speaker model/impedance/rating/connector/mounting information when known;
  allow an honest unknown/custom label. Do not recommend replacing James's
  existing square speaker merely to match an earlier CAD concept.
- List outputs with stable identities, connected/present/available distinction,
  current routing, per-output volume/mute, and selected-versus-effective state.
- Separate supported codec taps from PipeWire sinks and network players.
  Headphone routing on the v2 HAT is unverified; no guessed gain writes.
- Offer single-output and eventual user-selected “all” profiles. Investigate
  announcement fan-out independently of the selected music sink; neither fan-out
  nor automatic hotplug-follow is the current default.
- Supported capture gain, software AGC/noise suppression and echo-cancellation
  options must name their layer/runtime and limits. No unsolicited recording,
  playback or volume increase. Hardware mute versus software mute is explicit.

### Voice, music and components — WEB04/WEB05

- Enable/disable/install/remove only supported components with a plan, dependency/
  conflict checks, pinned versions and rollback. Retain multiple installed
  stacks where coexistence is proven; installation is not simultaneous ownership.
- LVA: selected capture/playback devices, supported wake model/location/language,
  AGC/noise suppression, pairing/server address, connection status and failures.
  Expose only real pinned-runtime options, not invented APIs.
- Sendspin: server/discovery/pairing/identity, receiver state, audio backend,
  output, supported delay/volume controls and group effects.
- Snapcast: receiver/server prerequisites, output/latency/identity and coexistence;
  not a mandatory dependency for Sendspin.
- Bluetooth proxy: installation/configuration/server link and actual proxy
  operation; Bluetooth radio presence alone is not a working proxy.
- Explain which choices belong to HA (Assist pipeline, STT/TTS/conversation
  providers) versus the device; link to the effective provider without collecting
  its secrets. TTS speaking speed is provider-specific, not sample rate.
- Select duck/resume **or** pause/resume, attenuation, timeout and recovery policy.
  Preserve pre-existing user pause/mute and intervening volume changes. Track a
  conversation through continued listening, announcements and timers, rather
  than resuming music on every TTS-finished callback.
- Provide supported reply interruption/cancellation with late-callback handling.
  Do not infer that a stop word controls an independent music receiver.

### LEDs, controls and enclosure — WEB06

- Select three-LED profiles: off/dim/default/custom, brightness, color and
  event-to-LED mapping (idle, wake/listen, thinking, speaking, timer, error,
  muted, disconnected). Preview is separately explicit; avoid surprise lighting.
- Show unsupported profiles honestly on other HATs. Distinguish cosmetic mute
  indication from actual microphone capture prevention.
- Supported button/physical-mute/volume actions, press/hold behavior and conflicts;
  validate mappings and restore last working configuration.
- Identify the chosen enclosure/board/speaker variant and assembly guidance;
  no claim of physical fit based only on CAD.

### Maintenance, diagnostics and recovery — WEB07/WEB08

- Selected/installed/available versions; pinned manual updates by default,
  explicit per-component automatic updates, release notes/compatibility and
  component-versus-OS/driver reboot effects.
- Plan/apply/progress/cancel/error/retry with atomic configuration, operation
  ownership and idempotence. Browser reload/disconnect must not leave an
  ambiguous half-applied operation or silently repeat a write.
- Sanitized service logs/recent failures, resource trends, component connection/
  pairing evidence, audio routing/mixer inspection, last health checks and
  manual diagnostic export. No raw microphone content, tokens or Wi-Fi secrets.
- On-device file-based capture/list/verify/restore, named protected baselines,
  coverage/exclusions/space/progress, compatibility and identity checks, and
  demonstrated file restoration. Export/rescue remain future options, not a
  whole-SD/second-destination prerequisite for this first useful slice.
- No automatic pruning, forced reboot, driver change, or automatic backup upload.

## Usability, access and architecture — WEB02/WEB09/WEB10

- Stable hardware-derived hostname plus friendly room name and IP/mDNS fallback;
  Wi-Fi onboarding/re-entry with clear AP-to-client transition. Do not rename a
  live lab device simply to make an example address work.
- Beginner-friendly local browser enrollment; no universal shipped key/password;
  access revocation/rotation, threat model and future secure transport.
- Responsive phone/desktop layout, keyboard/screen-reader labels, focus/error/
  busy states, units/help, contrast and unavailable/stale presentation.
- Common validated operation layer for browser, CLI and maintenance TUI, not
  three competing implementations. Keep the stdlib volume prototype bounded
  until a broader architecture/reuse decision is reviewed.
- Test no-write startup/poll/reconnect, duplicate submissions, stale requests
  across write/pair/disconnect, lost responses after successful writes, offline
  controls, malicious labels/headers, and broken/unavailable collectors.
- Validate each supported OS/architecture, browser class and hardware pairing
  independently. Preserve 32-bit OS on 32-bit boards and 64-bit on 64-bit boards;
  Pi 5/Chromium success does not prove original Zero W/browser support.
