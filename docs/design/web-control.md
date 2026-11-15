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
cannot be established, show `Unknown` age with the reason, not fresh.
The current server caches most status for two seconds but sends no observation
times, so it cannot yet satisfy this rule. For CPU and swap I/O, display the
sampling interval as well. A historical event is labeled with its actual event
time or `time unknown`, never presented as a current measurement.

The following are **future acceptance tests**, not existing capabilities. Use
offline fixtures with fake operations, clocks and credentials; a passing fixture
is not evidence of device support. Each bullet gives expected observable output
or readback; any different result, missing evidence, unexpected write or exposed
secret fails it. Tests requiring a collector, operation or security design wait
for that prerequisite; none authorizes a device operation.

### Shared failure and safety cases

Apply these cases to each packet as well as its specific cases below:

- Given no reachable device, show `Device unavailable`, retain previous readings
  only with last-observed time or `time unknown` and stale/unknown age, and
  disable device actions. Offer retry without silently selecting another device.
- In authenticated mode, given no valid credential, show `Access required`; do
  not show protected data or enable actions. The prototype's explicit `--auth
  none` development bypass is excluded from production acceptance, not a missing
  credential; it must be visibly identified as unauthenticated when tested.
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
- **Future age/order contract:** inject an observation with a provable age of
  exactly 30 seconds, then advance a suspend-aware clock beyond 30 without any
  response; it changes from fresh to stale, including on return from suspension.
  A cached response, background tab or disconnection must not reset age;
  untimed retained values show unknown time/age.
- With a fake clock and visible page, record polling at 10-second intervals; a
  missing or extra poll, write or diagnostic operation fails the fixture.
- Inject browser/device clock skew, a future timestamp or unbounded transit time:
  show unknown age unless a trusted age bound proves freshness or staleness. An
  arrival timestamp alone, or an untrusted wall-clock subtraction, cannot prove it.
- Inject out-of-order responses, reconnect and a new device boot/monotonic epoch:
  reject older observations, invalidate prior-epoch current state and accept only
  ordered evidence from the new epoch. A late prior-boot response or a repeated
  cache response must not overwrite a newer sample or renew its age.
- Page load, refresh, polling and reconnect must not change device settings,
  enroll a browser, revoke access, play audio, reboot, or initiate a diagnostic
  operation. Missing readings must not become invented states, zeros or healthy
  badges. An unavailable action is disabled or absent, with a reason; it must
  never look active if it cannot act.
- For a failed action, show its reason beside the disabled control or in the
  section where an absent control would appear. With one failed action and one
  independently available action, the latter remains usable; action logs show
  no fallback device or unintended write.

### WEB02: address, identity and browser access

**Outcome:** A person can identify and reach the intended device, enroll or
revoke browser access, and perform ordinary supported setup without SSH.

| Data needed | Current payload or gap |
| --- | --- |
| System hostname | Current: `hostname`; it is not proof of a stable hardware-derived identity or a working `.local` address. |
| Hardware-derived identity, identity validity/collision and mDNS reachability | Collector: N02 identity evidence and discovery/reachability; without evidence the identity and collision status cannot be known. |
| Friendly room name | Collector: retained device name; current `/api/devices` names/labels come from configured entries or discovery announcements, not proof of the device's retained room name. |
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

- **Room name — future operation:** start with name A and hostname H; confirm
  name B, reopen and simulate service restart. Authoritative readback must show B
  and unchanged H; browser-only persistence or a changed hostname fails.
- Cancel a name change and inject a rejected write; readback remains A. For a
  lost response or competing update, show an uncertain/conflict result and
  read back the authoritative name before offering retry or claiming B saved.
- **Identity/fallback — future binding and discovery:** a fixture binds device D
  to a hostname and IP:port with independently verified identity, transport,
  authority and browser-side reachability evidence at known times. Show both
  addresses and the IP fallback only while that evidence is current; a directory
  entry, IP alone or hostname alone is not the binding evidence.
- Inject mDNS failure, an IP reassigned to device E, wrong transport identity,
  disallowed authority, stale binding and unreachable IP separately. Show the
  affected fallback as unverified/unavailable with its reason, never as a verified
  link to D; without a known IP show `IP address unknown`.
- Test hostname and IP as different browser origins: each needs its own allowed
  authority, transport identity and an authorized session or explicit enrollment;
  a successful hostname session must not imply IP-origin access.
- Given missing hardware ID or a reported collision, show `Identity unknown` or
  `Identity collision`; neither `debra-unknown` nor a stable-identity claim may
  appear. Show stale address observation time, or unknown age if unavailable.
- **Enrollment/revocation — future authenticated operation:** in a fake secure
  design, explicitly enroll credential A in tabs A1 and A2 and separate credential
  B in tab B; prove protected reads and a harmless fake write work in all three
  and for direct HTTP clients using A and B. Enrollment requires confirmation;
  cancellation or an unauthorized enrollment must leave the access list unchanged.
- Revoke exactly A using authorized B. After confirmed server-side effectiveness,
  A2 and a direct HTTP client using A must each be denied a protected read and a
  new fake write; B's tab and direct client must still succeed. Tab-local clearing,
  a denial caused only by browser state, or any successful A request fails this test.
- Reject an unauthorized revocation and inject server failure: read back that A
  remains authorized and show failure, not `Revoked`. Drop the response after a
  successful revoke: show unknown until independent server readback and A-client
  rejection verify it; do not silently repeat the mutation.
- Start a fake write under A before revocation and release it afterwards: display
  its independently read-back result or `outcome unknown`, not a claim that
  revocation cancelled it; no newly started A write may succeed.
- In authenticated-mode fixtures, distinguish unreachable device, unenrolled,
  invalid/expired credential and denied permission where safely evidenced;
  otherwise show a generic access failure. Pre-auth output contains only the
  reviewed bootstrap/recovery information, never protected state or credentials.
- After a reviewed non-SSH recovery design exists, exercise its recovery fixture
  from an expired credential to a newly authorized browser session. Missing
  recovery instructions, protected data leakage or an SSH-only path fails.

**Open questions:** Which reviewed enrollment, credential recovery and transport
design provides the authorization and revocation boundary? What identity proof,
address lifetime and invalidation method bind an origin to a physical device?
What pre-auth distinctions and non-SSH recovery steps are safe to disclose?
Until decided, those positive paths are blocked, not implemented features.

**Must never happen:** Require SSH for ordinary supported configuration, enroll
or revoke on load, log/display credentials, treat tab disconnect as revocation,
or imply trusted-LAN HTTP protects the key from a hostile peer. A secure
enrollment and transport design remains a prerequisite, not a feature claim.

**Roadmap/code gap:** WEB02 requires browser enrollment and revocation and no
SSH for ordinary operation. The prototype instead uses one shared bearer key;
its guide retrieves it via a device terminal, and disconnect clears only the
current tab. It accepts explicitly configured hostname/IP authorities and the hub
lists configured devices and `_debra._tcp` mDNS discoveries. An announcement is
a claim, not authentication or proof of reachability; stable identity and Wi-Fi
onboarding remain unimplemented. See [discovery](device-discovery.md).

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

- Given differing detected and selected board/HAT revisions, show both with
  sources and a mismatch; fixture readback must show neither was changed.
- Test missing HAT detection only, missing speaker identification only, and both
  missing. Label each missing field `Unknown` independently, retain known detected
  and selected fields, and permit an explicit unknown selection; an inferred
  model or replacement recommendation fails.
- **Structured selection — future operation:** select fixture board B/revision 1
  and HAT H/revision 2; before confirmation show them pending while retained and
  effective selections remain A. Cancel and read back A, with no operation call.
- With a compatible fixture and an authorized operation, confirm and apply B/H;
  operation result and reopened authoritative readback show retained B/H, while
  effective A and a pending reboot remain separate until a simulated reboot and
  effective readback show B/H. A disabled selector or browser-only save fails.
- Inject a refused apply or lost response: retain the last verified effective
  state, show the failure or uncertainty, and read back before retry; never claim
  the pending choice is effective without evidence.
- **Compatibility — future evidence:** fixture evidence names exact board/HAT
  revisions, OS, kernel and driver versions. A supported match plus available
  operation enables apply; evidenced incompatibility, missing/conflicting evidence,
  or absent operation disables it with the specific reason beside the control.
- Show loaded driver, pending overlay and evidence-backed reboot requirement as
  separate sourced fields. An untested pairing is `Compatibility unknown`, not
  supported; A01/A02 evidence and authorized writes remain prerequisites.
- Reopen retained speaker model, ohms, watts, connector and mounting fields;
  supplied values persist and each absent value is `Unknown`. Missing sink,
  permission-denied or stale detection must not erase selections or prove absence.

**Open questions:** Which exact board/HAT/OS/kernel/driver combinations have
adequate compatibility evidence, and which changes require a reboot? No current
fixture choice above asserts a real supported pairing.

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
| Working: current evidence for a specifically identified end-to-end function under stated conditions. A completed test is `Last worked`, not proof of current working, however recent. | Collector: a reviewed, safe, function-specific current-evidence contract and invalidation; absent that, current working is `Unknown`. No automatic recording, playback or intrusive probe. |

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

- **State matrix — future collectors:** for each of LVA, Sendspin, Snapcast and
  Bluetooth proxy, fixture all six rows independently: installed, enabled,
  configured, running, connected and current working. For each row inject its
  own scoped positive, proven negative, missing, permission-denied and stale
  evidence; expect respectively `Yes`, `No`, `Unknown`, `Unknown: permission
  denied` and current `Unknown` with stale value labeled `Stale`, plus source/time.
  Missing rows or a state inferred from a different row fail; unavailable
  current-working evidence must be `Unknown`.
- Validate fixture configuration against that runtime/version: valid is `Yes`,
  independently invalid is `No`, unreadable is `Unknown`. A reachable server
  without evidence of an established link is `Connected: Unknown`, not `Yes`.
- Show raw active unit with `Running: Unknown` if runtime correlation is absent;
  an independently enabled but stopped runtime shows enabled `Yes`, running `No`.
  A verified package without a unit is installed `Yes`; missing unit alone is
  installed `Unknown`, and an authoritative absence is `No`.
- **Current versus history:** inject a scoped success 5 seconds ago without
  current-function evidence; show `Last worked` with test time and scope, and
  current working `Unknown`, not `Yes`. Inject later failure or configuration/
  peer change without a new intrusive check; invalidate current evidence and
  retain history without relabeling the old success as current.
- A simulated reviewed live evidence contract for one named function may yield
  current `Yes` or `No` only with its own valid positive or negative evidence;
  loss, expiry or scope change yields `Unknown`. Fixture signals are not claims
  that any actual component offers such a contract.
- **Multiple runtimes:** show all six rows per discovered runtime/scope, including
  a non-systemd runtime. For each aggregate row, show `Yes` only when complete
  scope enumeration and every applicable scope independently say `Yes`; show
  `No` only when all say `No`; mixed, incomplete, zero or unknown scopes are
  `Unknown` unless an independent component-level negative is established.
- Test Snapcast user/system `Yes`/`No` and `No`/`Yes`, a denied scope and an
  additional non-systemd scope; neither a single unit nor an incomplete scan
  may determine an aggregate. A radio alone leaves Bluetooth proxy installation
  and working `Unknown`.
- For each component show version-scoped prerequisites and sanitized error with
  source/time. Fixture an evidenced absent server, an unreachable server and an
  unverified server separately; label each correctly and show independently
  evidenced ownership or `Owner: Unknown`, never infer it from absence.
- With no version evidence show `Version: Unknown`; with exact fixture version x
  show x and its source. Missing lifecycle operations are disabled or absent with
  a nearby reason, and fake operation logs show no server change or page-load test.

**Open questions:** What nonintrusive, continuously valid end-to-end evidence and
invalidation rules, if any, can each pinned component provide? Which deployment
scopes are enumerable and what independently proves a server absent? Until
reviewed, those answers and current working remain unknown.

**Must never happen:** Treat found, enabled, active or connected as proof of
working; create an end-to-end check on page load; invent versions or server
ownership; present lifecycle actions as enabled without an available operation.

**Roadmap/code gap:** WEB04 requires six component states, versions and
prerequisites. The prototype returns only partial systemd enabled/running
evidence for named user LVA, Sendspin, PipeWire and WirePlumber units and
user/system Snapcast units. It does not detect the Bluetooth proxy,
installed/configured/connected/working state, exact
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

- **CPU — future counter-validity collector:** the first sample for total and
  each core shows `Unknown: waiting for second sample`. For normalized fixture
  counters with total delta 100, idle delta 25 and interval 10 s, show 75% and
  10 s for the applicable total/core; zero or negative elapsed time is unknown.
- Decrease any individual CPU counter while other counters rise enough that their
  sum still rises; show that series' rate `Unknown: counter reset`, not a clamped
  percentage. Rebaseline at the reset and require a second valid sample; unrelated
  cores with valid pairs remain available.
- Remove a core, then add it back with a new counter sequence: show it unavailable
  while absent and unknown on its first new sample, not a rate across the gap.
  An independently new core also waits for its own second sample.
- **RAM/storage:** for total 1024 MiB and available 256 MiB show estimated RAM
  used 768 MiB, labeled `total minus available`; missing either input makes used
  unknown. For root mount total 1000, actual used 600, user-available free 300,
  reserved 100 MiB, show those sourced values and mount; 700 MiB used fails.
- **Uptime/swap:** 3600 seconds displays one hour; an unreadable source is
  unknown, not zero. Swap total 1024 MiB and free 768 MiB shows used 256 MiB;
  either missing input makes used unknown.
- For `pswpin` 100→120 and `pswpout` 200→230 over 10 s, show 2 and 3 pages/s
  and the interval. First/missing samples, nonpositive elapsed time, or a decrease
  in either counter show that rate unknown; test each decrease separately,
  rebaseline the affected counter and require a second valid sample rather than
  treating a reset as continued health.
- **Compression:** for zram0 original/compressed/resident 8/4/5 MiB show each
  value and ratio 2; show zram1 independently. Zero compressed bytes makes ratio
  unknown; a confirmed empty device inventory differs from unreadable stats.
- Show independently sourced zswap enabled, pool MiB, hits and rejects counts;
  for fixture `Y`, 4 MiB, 12, 3 display those values. Missing or denied fields
  show unknown with reason, not zero; decreasing hit/reject counters are labeled
  reset/rebaselined, not a continuous increase or a performance benchmark.
- **Power:** with unavailable core voltage and measured supply 4.8 V show
  `CPU-core voltage: Unknown` and `5 V supply: 4.8 V`. Show current and since-boot
  flag values and raw hexadecimal evidence independently; missing flags are unknown.
- For a latched since-boot flag observed at T, show observation time T and event
  time `unknown` unless separately evidenced; if event time E is supplied, show E
  separately. Neither case triggers a reboot or substitutes T for E.
- **Wi-Fi/temperature:** show -60 dBm for wlan0 only with version-scoped driver or
  collector documentation establishing that source's unit. A signed -60 from a
  relative/undocumented source is unknown, not dBm; show wlan1 independently.
- A denied thermal reading shows `Temperature: Unknown: permission denied` with
  sensor identity if known and preserves other fresh metrics; zone 0 alone does
  not establish a CPU sensor.
- **Diagnostics/trends — future C05 collector:** a fixture error/log excerpt with
  timestamp, source, harmless message, token, Wi-Fi password and microphone data
  shows the useful sanitized message and time without the sensitive values;
  missing/denied source shows its reason, and stale entries retain their
  observation/event times and label.
- For a requested fixture trend window T=0–60 s with CPU samples 10%, 20%, 30%,
  40% at 0, 10, 50 and 60 s, show each value/time and the 10–50 s gap, not
  interpolated health.
  Empty, denied and stale trend data are labeled separately, not plotted as zero.
- Across the metric fixtures, verify source, observation time, availability and
  units; a missing row, an unlabeled stale value, aggregate health score or
  synthetic working badge fails. A fresh ordered sample replaces stale evidence.

**Open questions:** What trustworthy age/ordering protocol handles clock skew,
suspend and boot epochs? Which per-board sources establish units and support,
and which C05 diagnostic sources and trend windows are safe and useful? Until
reviewed collectors exist, these are fixture contracts, not available readings.

**Must never happen:** Write or trigger a test on page load, infer healthy status
from missing data, substitute one voltage for another, show stale data unlabeled,
or offer an action that cannot act. Do not present counters as a performance
benchmark or combine metrics into a synthetic health score.

**Roadmap/code gap:** WEB07 calls for per-board collectors, freshness and units.
The prototype has several partial unprivileged readings but no sample times,
CPU-core voltage or zswap pool/hits/rejects; empty Wi-Fi/zram lists and swallowed
read errors do not distinguish absence from a failed probe. A raw metric payload
is not complete WEB07 coverage.
