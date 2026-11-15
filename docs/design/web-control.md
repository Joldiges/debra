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

## Packet acceptance detail

These are proposed, checkable requirements, not descriptions of completed
features. `Current` below means present in the inspected
[`server.py`](../../control/web/server.py) status payload, not that the value is
complete or accurate on every device. `Collector` means a new read-only
collector or an extension of an existing one is needed. `Cannot know` means no
available evidence proves the fact; present it as unknown rather than guessing.
New edits and enrollment/revocation also need a separate authorized operation
layer; a collector does not perform writes.

For these packets, each observed field needs its source, observation time and
availability. Proposed test threshold: poll every 10 seconds while the page is
visible; a reading is fresh through 30 seconds after observation and
stale thereafter, including while disconnected. A timestamp must be from the
collector's observation, not the browser's receipt of a cached response. If age
cannot be established, show `Unknown: observation time unavailable`, not fresh.
The current server caches most status for two seconds but sends no observation
times, so it cannot yet satisfy this rule. For CPU and swap I/O, display the
sampling interval as well. A historical event is labeled with its actual event
time or `time unknown`, never presented as a current measurement.

### Shared failure and safety cases

Apply these cases to each packet as well as its specific cases below:

- Given no reachable device, show `Device unavailable`, retain any previous
  readings only with their last-observed time and stale/unknown age, and disable
  device actions. Offer retry without silently selecting another device.
- Given no valid key, show `Access required`; do not show protected device data
  or enable device actions. A previously cached value must not appear current.
- Given the selected sink is missing, show its identity and `Selected output
  unavailable`; disable audio actions, do not use another sink, and continue to
  show independently available identity, hardware, component and metric data.
- Given authoritative evidence a service is not installed, show `Not installed`
  for that component; a missing unit or failed probe alone instead shows
  `Unknown`. Do not erase independent facts about the other components.
- Given permission denied, show `Unknown: permission denied` for the affected
  field and leave independently collected fields available. Do not treat it as
  absence or request elevated access on page load.
- Given a reading older than 30 seconds, show `Stale`, its value and observation
  time, and do not use it to establish current status. If no time is known, show
  unknown age instead. A successful new observation replaces that label.
- Page load, refresh, polling and reconnect must not change device settings,
  enroll a browser, revoke access, play audio, reboot, or initiate a diagnostic
  operation. Missing readings must not become invented states, zeros or healthy
  badges. An unavailable action is disabled or absent, with a reason; it must
  never look active if it cannot act.

### WEB02: address, identity and browser access

**Outcome:** A person can identify and reach the intended device, enroll or
revoke browser access, and perform ordinary supported setup without SSH.

| Data needed | Current payload or gap |
| --- | --- |
| System hostname | Current: `hostname`; it is not proof of a stable hardware-derived identity or a working `.local` address. |
| Hardware-derived identity, identity validity/collision and mDNS reachability | Collector: N02 identity evidence and discovery/reachability; without evidence the identity and collision status cannot be known. |
| Friendly room name | Collector: retained device name; current optional `/api/devices` list names/labels are manually supplied directory entries, not the device's retained room name. |
| Current IP addresses, interface and port, plus reachable fallback | Collector: addresses and browser-usable advertised authority/reachability. An address alone cannot prove the browser can reach it or that it identifies the intended board. |
| Browser enrollment status, authorized access identities and revocation result | Collector for non-secret access state and operation result; no current enrollment or revocation API. `auth` currently reports `key` or `none`, not enrollment. Never expose key material in status. |

Before N02/N04, implement and fixture-test display, explicit room-name editing
and access-flow interfaces against a verified existing lab hostname and supplied
addresses, without asserting stable identity or completed onboarding. Final
identity and Wi-Fi onboarding depend on N02/N04; their prerequisites and a
reviewed authentication/transport design still apply. No lab operation follows
from this specification. The [alternatives note](../notes/2026-11-15-complete-alternatives-comparison.md)
describes phone onboarding and physical controls on other devices, but contains
no hands-on comparison and does not establish any Debra feature.

**Acceptance:**

- Given a retained room name and hostname, show both separately; changing the
  room name by an explicit confirmed action does not rename the hostname.
- Given verified hostname and usable IP authorities, show both with port and
  identify the IP as a fallback. Given mDNS failure, offer only an independently
  known IP; if none is known, show `IP address unknown` rather than invent one.
- Given missing hardware ID or an identity collision, show `Identity unknown`
  or `Identity collision` respectively; do not derive `debra-unknown` or claim
  stability. A directory entry alone must not prove physical device identity.
- Given a browser not enrolled, offer the supported enrollment path; explicit
  user confirmation is required. Given successful revocation, a subsequent
  request using the revoked credential is rejected, including from another tab;
  report separately that an already-started operation may have completed. If
  revocation fails or cannot be verified, show the failure, not `Revoked`.
- Given no key, expired enrollment or permission denied, show the relevant
  access failure and a recovery path that does not require SSH for ordinary
  operation. Given stale addresses, label them stale and do not claim reachability.

**Must never happen:** Require SSH for ordinary supported configuration, enroll
or revoke on load, log/display credentials, treat tab disconnect as revocation,
or imply trusted-LAN HTTP protects the key from a hostile peer. A secure
enrollment and transport design remains a prerequisite, not a feature claim.

**Roadmap/code gap:** WEB02 requires browser enrollment and revocation and no
SSH for ordinary operation. The prototype instead uses one shared bearer key;
its guide retrieves it via a device terminal, and disconnect clears only the
current tab. It accepts explicitly configured hostname/IP authorities, but does
not discover addresses, create stable identity or provide Wi-Fi onboarding.

### WEB03: board, HAT and speaker

**Outcome:** A person can compare detected and selected hardware, retain speaker
details, and see evidence-backed compatibility, driver and reboot requirements.

| Data needed | Current payload or gap |
| --- | --- |
| Detected board model and CPU architecture | Current: device-tree `model` and `architecture`; exact revision is available only if evidenced by the model string. Collector: independent revision/evidence if needed. |
| Detected HAT product | Current: `detected_hat` device-tree product or null; not proof of an exact revision or physical presence. Collector: evidence for any stronger claim. |
| Selected board, HAT and revisions | Current: `selected_hardware.hat` is an optional retained string, not verified hardware; no selected board/revision. Collector: structured selection and its provenance. |
| Speaker model, impedance, rating, connector and mounting | Current: optional `selected_hardware.speaker` label only. Collector: retained structured details; physical characteristics cannot be auto-detected without evidence. |
| Driver/overlay, compatibility, evidence, pending change and reboot state | Collector: actual driver/overlay and boot state plus evidence-backed exact-version compatibility and change plan. Untested compatibility or reboot effect cannot be known. |

**Acceptance:**

- Given detected board/HAT evidence and a different user selection, show both
  values, their sources and the mismatch; do not change either selection.
- Given no HAT detection or speaker identification, show the exact UI text
  `Unknown is not auto-detection or a replacement recommendation` and retain
  any independently selected HAT and speaker information. Unknown is selectable
  as an honest value, not an automatically detected model.
- Given retained speaker model, impedance in ohms, rating in watts, connector and
  mounting details, show each supplied field after reopening; show `Unknown` for
  each absent field. Never recommend replacing the existing speaker merely to
  match a model or enclosure.
- Given a driver loaded, a pending overlay and evidence that reboot is needed,
  show each separately with its source and the pending reboot. Given missing or
  conflicting compatibility evidence, show `Compatibility unknown` and disable
  apply with the missing prerequisite; an untested pairing is not supported.
- Given permission denied or stale detection, label the affected observation
  rather than claiming hardware is absent; a missing sink does not delete the
  retained hardware or speaker selection.

**Must never happen:** Save or apply hardware choices on page load, infer a
speaker or exact HAT revision from an empty reading, recommend replacement from
unknown information, or present unavailable driver/apply controls as usable.
Hardware writes remain gated by A01/A02 evidence and an authorized operation.

**Roadmap/code gap:** WEB03 calls for structured selection and actionable
driver/compatibility/reboot state. The prototype only reads device-tree model
and HAT product plus optional HAT/speaker labels; it does not select hardware,
inspect drivers or establish compatibility.

### WEB04: component state and prerequisites

**Outcome:** A person can see LVA, Sendspin, Snapcast and Bluetooth proxy as
separate components with six distinct evidence-backed states and prerequisites.

For every component, display each state independently as `Yes`, `No` or
`Unknown`, with evidence and observation time; do not propagate one state into
another. `No` requires evidence for that particular negative; an inaccessible or
incomplete probe is `Unknown`.

| State and definition | Current payload or gap |
| --- | --- |
| Installed: the component's actual executable/package or equivalent runtime is present in the supported location. | Collector: inspect supported installation types. Current `unit_found` only says the named systemd unit loaded, not that the component is installed; missing unit does not prove absence. |
| Enabled: the component is configured to start automatically in its relevant service scope. | Current partial: `enabled` is a raw systemd `UnitFileState` for named units, not a complete component answer. Collector: map scope and non-systemd installations; handle static, masked and unknown states explicitly. |
| Configured: required device-side settings are present and valid for the pinned runtime and chosen deployment, without exposing secrets. | Collector: version-specific validation. Current `configuration` is a placeholder, not inspection. |
| Running: the component's relevant runtime is currently executing. | Current partial: `active` is systemd `ActiveState` for named units, not proof of a running component in every deployment. Collector: correlate actual runtime and scope, including non-systemd cases. |
| Connected: the component has a current established link to its required named peer, such as HA, Music Assistant or Snapserver. | Collector: component-specific link evidence. A running process or reachable server alone does not prove connection. |
| Working: an explicitly identified end-to-end function succeeded under stated conditions and at a stated time. | Collector: safe, component-specific evidence and timestamp. Current operation cannot be known from an old test or without evidence; no automatic recording, playback or intrusive probe. |

| Other data needed | Current payload or gap |
| --- | --- |
| Exact installed/selected versions, version source and runtime identity | Collector; an unavailable version is `Unknown`, not a guessed pin. |
| Component prerequisites, missing/failed requirements, sanitized errors and server ownership | Collector plus version-scoped prerequisite evidence. Current unit names and scope distinguish user/system Snapcast probes only; Music Assistant server location is explicitly not inspected. |
| Time and evidence for every state, including last successful end-to-end check | Collector; the current payload has no observation timestamps or working evidence. |

Read-only detection can be developed independently; lifecycle writes depend on
C02. Check prerequisites separately: LVA needs the applicable HA link and
capture/playback path; Sendspin needs its compatible music server and output;
Snapcast needs its compatible server and output, not Sendspin; Bluetooth proxy
needs a supported proxy runtime, radio and HA link. Exact version compatibility
and server ownership require evidence, not assumptions that HA supplies every
service.

**Acceptance:**

- Given an active LVA unit but no configuration, connection or end-to-end
  evidence, show the unit active and those three states `Unknown`, not working.
  Given an enabled but stopped component, show `Enabled: Yes` and `Running: No`
  only when both are independently established.
- Given a verified package without a unit, show `Installed: Yes` and the unit
  missing, not `Not installed`. Given a missing unit without package evidence,
  show `Installed: Unknown`; given a confirmed absent installation, show `No`.
- Given separate user and system Snapcast units, show each scope and do not
  collapse conflicting observations into one affirmative state. Given only a
  Bluetooth radio, show proxy installation and working as `Unknown`.
- Given version `x` and a missing compatible server, show exact `x`, the missing
  server and who owns it; given no version evidence, show `Version: Unknown`.
  Do not imply the page changed the server.
- Given successful end-to-end evidence from an earlier time, show `Last worked`
  with its time and test scope; do not claim current working after it becomes
  stale. Given permission denied, show `Unknown: permission denied` for the
  affected state, not `No`.

**Must never happen:** Treat found, enabled, active or connected as proof of
working; create an end-to-end check on page load; invent versions or server
ownership; present lifecycle actions as enabled without an available operation.

**Roadmap/code gap:** WEB04 requires six component states, versions and
prerequisites. The prototype returns only partial systemd enabled/running
evidence for named LVA, Sendspin and user/system Snapcast units. It does not
detect the Bluetooth proxy, installed/configured/connected/working state, exact
versions or prerequisites. No full six-state answer exists today.

### WEB07: metrics and freshness

**Outcome:** A person can inspect individually labeled resource, network and
power readings, with units, observation age and honest availability.

All rows use the shared 10-second polling and 30-second freshness rule above;
the timestamp is for each actual sample, not a cache response. A null, missing,
unreadable, unsupported or unimplemented field displays `Unknown` with the
reason when known; never display zero unless zero was measured. `Collector`
includes adding timestamps and distinguishing absence from read failure.

| Metric and unit | Availability rule and current payload or gap |
| --- | --- |
| Total and per-core CPU, percent (%) | Current: `cpu_percent` from two `/proc/stat` samples; first sample, missing core or nonpositive delta is unknown. Collector: sample times, interval and core availability. |
| RAM estimated used/available/total, bytes (display MiB/GiB) | Current: raw `memory.MemTotal` and `MemAvailable` from `/proc/meminfo`; estimate used as total minus available only when both exist and label the formula. Collector: timestamps and reason for missing fields. |
| Storage used/free/total, bytes (MiB/GiB) | Current: `storage` free/total from disk usage of the server's root path. Collector: actual used, mount identity and timestamps; other mounts are unknown. Total minus user-available free includes reserved space, so do not label it used. |
| Wi-Fi signal, dBm per interface | Current: `wifi` from `/proc/net/wireless`, with null for values outside its accepted signed range. Collector: interface/link context, timestamps and trustworthy units. An empty list or a driver with relative/ambiguous signal is unknown, not 0 dBm or no Wi-Fi. |
| CPU-core voltage, volts (V) | Collector: board-specific supported core-voltage reading and source; current server does not return it. If unavailable, `Unknown: unsupported or unreadable`, not 5 V supply. |
| 5 V supply voltage, volts (V) | Current: `power.supply_voltage_v` only when a supported `EXT5V_V` PMIC reading parses; otherwise unknown. Collector: source, timestamp and reason. Do not equate this with CPU-core voltage. |
| Undervoltage now and since boot, yes/no; raw throttle flags as hexadecimal, unitless | Current: `power` flags when `vcgencmd get_throttled` parses; missing flags are unknown. Collector: sample time and event time if available. `Since boot` is historical and is not a measured event time. |
| Temperature, degrees Celsius (°C) | Current: `temperature_c` from thermal zone 0 when readable. Collector: zone/sensor identity and timestamp; do not call it CPU temperature without evidence. |
| Uptime, seconds (display days/hours/minutes) | Current: `uptime_s` when `/proc/uptime` parses; collector adds observation time. |
| Swap used/total, bytes (MiB/GiB) | Current: `memory.SwapTotal` and `SwapFree`; derive used only when both are available. Collector: timestamp and reason. |
| Swap input/output rate, pages per second | Current: `swap_io.pswpin_pages_per_s` and `pswpout_pages_per_s` require two monotonic counter samples and elapsed time; reset/missing data is unknown. Collector: interval and timestamps; pages are not bytes unless page size is known. |
| zram original/compressed/resident, bytes (MiB/GiB), per device; compression ratio, unitless | Current: `zram` entries with `original_bytes`, `compressed_bytes`, `memory_bytes`; ratio original/compressed only if compressed is nonzero. Collector: timestamp and distinction between no device and unreadable stats; an empty list alone is unknown. |
| zswap enabled, yes/no; pool bytes (MiB/GiB), hits/rejects counts | Current: `zswap_enabled` only for readable Y/N. Collector: pool and counters, support/permission state and timestamps; a missing counter is unknown, not zero. |

**Acceptance:**

- Given only the first CPU sample, show total and each discovered core as
  `Unknown: waiting for second sample`; given two valid samples, show separate
  total/per-core percentages and the interval. Given a reset counter, show unknown
  rate until two new valid samples exist.
- Given `SwapTotal` and `SwapFree`, show used and total in MiB/GiB; given either
  missing, show used as `Unknown`. Given no readable zram stats, distinguish
  confirmed no zram devices from `Unknown: stats unavailable`; never infer one
  from an empty list. Given compressed bytes zero, show ratio `Unknown`, not 0.
- Given core voltage unavailable and measured 5 V supply 4.8 V, show `CPU-core
  voltage: Unknown` and `5 V supply: 4.8 V` separately. Given a current or
  since-boot undervoltage flag, show its scope and raw evidence; do not order a
  reboot. Given no flag evidence, show unknown, not `No undervoltage`.
- Given a signed dBm value with verified unit and interface, show it with the
  interface; given a relative or unknown unit, show `Signal: Unknown` rather
  than relabeling it as dBm. Given a denied thermal reading, show
  `Temperature: Unknown: permission denied` and retain other fresh metrics.
- Given a sample 30 seconds old, show it as fresh; once older than 30 seconds,
  label it `Stale` with its sample time even if the page is still receiving
  cached responses. Given no observation time, show unknown age; given a fresh
  sample, replace the stale reading. No aggregate health score or synthetic
  working badge appears for any combination of readings.

**Must never happen:** Write or trigger a test on page load, infer healthy status
from missing data, substitute one voltage for another, show stale data unlabeled,
or offer an action that cannot act. Do not present counters as a performance
benchmark or combine metrics into a synthetic health score.

**Roadmap/code gap:** WEB07 calls for per-board collectors, freshness and units.
The prototype has several partial unprivileged readings but no sample times,
CPU-core voltage or zswap pool/hits/rejects; empty Wi-Fi/zram lists and swallowed
read errors do not distinguish absence from a failed probe. A raw metric payload
is not complete WEB07 coverage.
