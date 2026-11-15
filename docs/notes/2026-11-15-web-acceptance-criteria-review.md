---
title: Review of the WEB02, WEB03, WEB04 and WEB07 acceptance criteria
date: 2026-11-15
type: project-learning
status: unreviewed
task: WEB
author: OpenCode independent reviewer
author_model: openai/gpt-6.1-terra
author_variant: flex-high
sources:
  - docs/design/web-control.md at f2d45801322a7f19f4b0f8da54279dc4af0c6598
  - docs/roadmap.md at f2d45801322a7f19f4b0f8da54279dc4af0c6598
  - control/web/server.py at f2d45801322a7f19f4b0f8da54279dc4af0c6598
  - control/web/assets/app.js at f2d45801322a7f19f4b0f8da54279dc4af0c6598
  - tests/test_web.py at f2d45801322a7f19f4b0f8da54279dc4af0c6598
  - tests/test_web_browser.py at f2d45801322a7f19f4b0f8da54279dc4af0c6598
  - tests/test_docs.py at f2d45801322a7f19f4b0f8da54279dc4af0c6598
  - docs/README.md
  - docs/project-brief.md
  - docs/evidence.md
  - docs/ai-workflow.md
  - docs/templates/learning-note.md
  - AGENTS.md and /home/james/.config/opencode/AGENTS.md
  - /home/james/AI-Work/Memory/AGENTS.md
  - /home/james/AI-Work/Memory/memory/profile.md
  - /home/james/AI-Work/Memory/memory/decisions.md
  - /home/james/AI-Work/Memory/TODO.md
  - /home/james/AI-Work/Memory/memory/notes/fedora/20261114T232804Z-28e401c5c78d.md (Basic Memory search result)
  - /home/james/AI-Work/Memory/memory/notes/fedora/20261114T232228Z-0445e653a2ea.md (Basic Memory search result)
supersedes: []
---

# Independent review: browser acceptance criteria

**Scope and evidence:** static review of the specified files at `f2d4580`,
2026-11-15. These are findings about proposed criteria, not a claim that the
prototype should already implement future packets. A missing current capability
is a comparison point, not itself a defect in future-looking criteria. The
initial working tree was clean; `main` was seven commits ahead of `origin/main`.
During the review, the shared checkout advanced to `15058eb` and acquired
unrelated working-tree changes, including changes to reviewed code. The code
and line references below are to the originally read `f2d4580` versions, not the
later moving checkout; this note does not review those later changes.

## Verdict per packet

| Packet | Verdict | Basis |
| --- | --- | --- |
| WEB02 | **Not yet** | Enrollment/revocation and trustworthy fallback lack testable identity, security and failure contracts (F01–F04, F13, F18). |
| WEB03 | **Usable after 5 fixes** | Good detection/selection separation, but selection/apply and compatibility acceptance need definition (F05–F07, F13, F18). |
| WEB04 | **Not yet** | Six-state separation is good, but working evidence, multiple scopes and complete state coverage can still mislead (F08–F11, F13–F14, F18). |
| WEB07 | **Not yet** | Strong unknown/units examples, but reset detection, freshness, and required diagnostic/metric coverage are incomplete (F12–F18). |

There are **18 findings: 9 high, 9 medium**. A finding is counted once even if
shared by packets. High means a misleading status, security/design ambiguity,
or material untestable packet obligation; medium means an important missing
case or implementer decision. Fix counts above count applicable rows, not
independent code changes. The three highest-risk criteria are F01 (revocation),
F08 (working versus last worked), and F12 (counter resets).

## Findings

Locations below are in `docs/design/web-control.md` unless otherwise named.
Quoted fragments identify the criteria needing work; suggested fixes describe
the missing decision/test, not replacement criteria.

| ID / severity | Location | Criterion | Problem | What would fix it |
| --- | --- | --- | --- | --- |
| F01 / High | 202–206, 129–130 | “Given a browser not enrolled, offer the supported enrollment path”; “Given successful revocation, a subsequent request using the revoked credential is rejected, including from another tab” | The test does not specify enrollment identity, how a browser obtains/recovers its own credential, which credential is revoked, or the authorization boundary. Another tab may share or have a different credential. It does not say how revocation becomes effective or what a failed/lost response means; neither a local tab disconnect nor a read-only collector is revocation. The secure design is explicitly still pending, so this is not yet an implementable security acceptance contract. | Decide an authenticated enrollment/revocation design and a fixture with two named credentials/tabs, both before and after revocation, failure/lost response, and an already-started operation. Specify observable success, verification and recovery without exposing secrets. |
| F02 / High | 196–201, 207–209 | “Given verified hostname and usable IP authorities”; “offer only an independently known IP” | “Verified”, “usable”, “independently known” and “stale addresses” have no defined evidence, age or intended-device binding. A cached address can be reassigned; a network address or manually supplied directory entry is not proof of the intended physical device. The fallback may also use a different browser origin, require a different allowed authority or a new authentication session, and need transport identity verification. A green/reachable link could invite contact with the wrong device. | Specify discovery/binding and reachability evidence, age/invalidation, authority/port and authentication/transport behavior across origins. Test reassigned address, wrong identity, unavailable authority and unverified reachability, with an unknown outcome where proof is unavailable. |
| F03 / Medium | 147–151, 202–209 | “Given no valid key, show `Access required`” | This blanket shared case conflicts with the prototype's explicit `--auth none` development mode, where there is deliberately no key and access is allowed. It also does not define the unauthenticated bootstrap information needed to distinguish unavailable device, not-enrolled browser, invalid/expired credential and denied permission without leaking protected state. | Declare whether the proposed acceptance excludes the development bypass or defines a separate explicit mode; name observable pre-auth failure categories and permitted recovery information. |
| F04 / Medium | 194–195 | “changing the room name by an explicit confirmed action does not rename the hostname” | Named input/output, but no reopening/restart persistence, cancellation, failed write/readback, or competing change case. A temporary browser-only name can pass despite the retained-name outcome. | Define successful persistence and unchanged hostname using before/after readback, plus cancel and failed/uncertain operation fixtures. |
| F05 / High | 224–225, 237–253; roadmap 209 | “Given detected board/HAT evidence and a different user selection, show both values” | Comparison is observable, but none of the five bullets tests selecting a board/HAT/revision, applying a supported choice, or keeping the applied versus pending selection distinct. A read-only mock or a permanently disabled selector could pass while the roadmap calls for selection and actionable driver/reboot state. Writes remain explicitly gated; that is not a reason to leave the final behavior unspecified. | Define fixture-only selection/confirmation, allowed and refused apply, persisted/effective versus pending values, result/readback and reboot-needed transitions; retain A01/A02 and authorized-operation gates. |
| F06 / Medium | 247–250 | “Given missing or conflicting compatibility evidence, show `Compatibility unknown` and disable apply with the missing prerequisite” | Good negative case, but no named exact board/HAT revision, OS/kernel/driver scope or positive evidence case defines when compatibility is supported or an apply control may actually act. “Actionable” does not identify the prerequisite or distinguish incompatible from unknown. | Require version-scoped evidence and examples for supported, evidenced incompatible, unknown, conflicting and missing operation; name the visible prerequisite and enablement outcome. |
| F07 / Medium | 239–242 | “Given no HAT detection or speaker identification, show the exact UI text `Unknown is not auto-detection or a replacement recommendation`” | One exact sentence for either missing fact does not specify which field is unknown or whether an independent successful HAT detection/speaker selection remains visible. `or` also leaves one-missing versus both-missing cases ambiguous. | Test HAT-only missing, speaker-only missing and both missing separately, retaining and identifying each independently known or selected field. |
| F08 / High | 270–282, 300–303, 313–316 | “Working: an explicitly identified end-to-end function succeeded under stated conditions and at a stated time”; “do not claim current working after it becomes stale” | This can be read as `Working: Yes` now merely because an earlier test is less than 30 seconds old. A past successful interaction does not establish that the component still works, and can collapse `working` into connection/running or recent test success. No nonintrusive current-working evidence or negative-evidence rule per function is identified. | Separate current working evidence from `Last worked` regardless of age; define evidence/scope and invalidation for each function, otherwise show current `Unknown`. Test a fresh earlier success followed by a failure/change without running a new intrusive check. |
| F09 / High | 270–273, 307–309 | “Given separate user and system Snapcast units, show each scope and do not collapse conflicting observations into one affirmative state” | The criterion does not decide which of six states belongs to each runtime versus the component as a whole, or how to display aggregate `Yes`/`No`/`Unknown` when scopes differ. A developer could show one aggregate `No`, or derive running/configured/connected from a unit, and still avoid the prohibited affirmative. | Specify per-scope evidence and explicit aggregate/unknown rules, then fixture both opposite scope combinations, incomplete probes and non-systemd runtime. Keep all six facts independent. |
| F10 / Medium | 310–312 | “Given version `x` and a missing compatible server, show exact `x`, the missing server and who owns it” | Missing server evidence does not supply owner identity. The bullet can require inventing ownership; it also omits what proves the server is absent rather than unreachable or unobserved. | State independently evidenced owner or `Unknown`, with separate absent, unreachable and unverified server fixtures and version-specific prerequisites. |
| F11 / High | 270–288, 298–316; roadmap 210 | “For every component, display each state independently as `Yes`, `No` or `Unknown`” | This is an important rule, but the examples do not exercise all six states for each of LVA, Sendspin, Snapcast and Bluetooth proxy, or a complete configured/connected negative/unknown case. Sanitized errors and prerequisites are listed as data but have no concrete acceptance cases. Tests can pass the examples while hiding missing rows or collapsing configured into connected. | Add a component/state evidence matrix with positive, independently proven negative, missing/denied/stale cases and prerequisite/error display; include a real peer versus merely reachable server and no lifecycle action without an operation. |
| F12 / High | 357–360 | “Given a reset counter, show unknown rate until two new valid samples exist” | Good intent, but “reset counter” is unspecified for multi-field `/proc/stat` CPU counters: an individual counter may decrease while the total still increases. Current code checks only total delta and clamps the result (`server.py:93–111`), so it can return a plausible percentage for a reset. Swap is also not explicitly named in this reset example. | Define validity per counter, core appearance/disappearance and reset/rebaseline for CPU and both swap counters, including a reset with a still-increasing aggregate; fixture first sample and two subsequent valid samples. |
| F13 / High | 132–141, 147–148, 161–163, 373–376 | “a reading is fresh through 30 seconds after observation”; “once older than 30 seconds, label it `Stale`” | Threshold is clear, but a developer must guess how collector timestamps and browser clocks are compared, especially clock skew, future timestamps, device reboot/monotonic reset, out-of-order responses, background suspension and disconnection. A browser-receipt timestamp or successful cache response can make old data appear fresh. Also, stale labels must advance without a successful poll. | Define timestamp/age trust and ordering, behavior when age cannot be established, and clock-injected fixtures for exact 30 seconds, 30+ seconds without any response, skew/future time, reconnect, reboot and late old responses. Do not treat arrival time as observation time. |
| F14 / Medium | 140–141, 270–282, 313–315, 346–347, 365–368 | “A historical event is labeled with its actual event time or `time unknown`”; “Given a current or since-boot undervoltage flag, show its scope and raw evidence” | A current read of a latched since-boot flag has a sample time but not the event time. The acceptance example does not explicitly distinguish the two; a developer can display the observation timestamp as when undervoltage occurred. A prior working check similarly has a test time rather than proof of continued operation. | Exercise known/unknown event time separately from flag observation time and identify test time versus current status. |
| F15 / High | 328–377; roadmap 213 | “Given a sample 30 seconds old…” and the five metric examples | The roadmap also requires sanitized diagnostics and trends. None of the WEB07 acceptance bullets defines a diagnostic source, sanitization, trend time window, missing data or observable output; the examples could all pass with neither diagnostics nor trends. | Agree packet ownership with C05/WEB08 and add bounded fixture acceptance for sanitized errors/logs and trends, including absence/stale/secret redaction, or explicitly resolve the roadmap scope. |
| F16 / Medium | 339–353, 355–377 | “All rows use the shared 10-second polling and 30-second freshness rule”; the five examples | The data table is useful, but explicit cases omit RAM formula/missing inputs, storage actual used versus reserved space/mount, uptime, swap I/O interval/rate, zram original/compressed/resident and zswap pool/hits/rejects. The examples can pass while those roadmap metrics are omitted or miscalculated. | Add named fixture inputs and visible unit/value/unknown outputs for each row, including reserved blocks, missing numerator/denominator, independent interfaces/devices and counter reset. |
| F17 / Medium | 344, 369–371 | “Given a signed dBm value with verified unit and interface” | This is honest but “verified unit” has no evidence contract. The current numeric-range check alone is not proof of dBm; a signed relative driver value could pass if developers use `signal_dbm` merely because it is named that. | Define accepted per-driver/source unit evidence and a negative signed-but-relative fixture; otherwise `Unknown`. |
| F18 / Medium | 147–168 | “An unavailable action is disabled or absent, with a reason” | If the action is absent, the criterion does not identify where its reason is visible; nor does it specify which independent controls remain usable when only one field/action fails. A generic error or an unexplained missing control could arguably pass. | Name the associated visible reason and test both absent and disabled controls, affected versus unaffected actions, and no fallback/device write. |

## What the server can already answer

This is **per acceptance bullet**, not a claim of complete implementation. `C`
means current partial payload, `R` means new or extended read-only collector;
`K` means cannot know without independent evidence. Even C needs observation
time/source/availability work for the shared freshness rule. Actions require an
authorized operation layer in addition to any collector. File/line references
are to `control/web/server.py` unless otherwise named.

| Criterion location | Data classification and code evidence |
| --- | --- |
| Shared 147–149, offline | C: request errors are possible; no server response exists offline. R: prior observed value/time and client-side age/connection handling. `app.js:172–196` disables audio on failed refresh but has no sample time. |
| Shared 150–151, access | C: 401 for a missing/wrong key in key mode, `auth` mode on successful status (`373–395`, `405–409`). R plus separate auth operations: enrollment/expiry/revocation state. K: no inferred enrollment from `auth`; explicit no-auth mode differs (F03). |
| Shared 152–154, sink | C: configured `audio.sink` and `available`/error (`194–206`); status separately includes other fields (`291–296`). R: distinguish reasons and timestamp each observation. Current UI disables audio (`app.js:90–96`). |
| Shared 155–157, installation | C: only systemd `unit_found`, `active`, `enabled` for certain units (`230–262`). R: supported installation evidence. K: a missing unit alone cannot establish absence. |
| Shared 158–160, permission | R: field-specific errors; `read_text` swallows `OSError` and Unicode errors (`69–73`), and failed commands become generic unavailable (`58–66`). K: missing data alone cannot prove permission denial or absence. |
| Shared 161–163, staleness | R: per-observation timestamps and trustworthy age; internal sample/cache clocks are not returned (`175`, `284–299`). K: age of an untimed cached observation. |
| Shared 164–168, no writes/actions | C: status is read-only and POST is limited to audio (`284–299`, `397–443`); `tests/test_web.py:81–86,263–267,293–298` assert portions. R/operations as appropriate for future features; current code cannot establish the safety of unimplemented actions. |
| WEB02 194–195, room/hostname | C: `hostname` (`293`); optional manually supplied `/api/devices` names/labels (`491–519`, `403–404`) are not a retained room name. R: retained name; explicit save is a new operation. |
| WEB02 196–198, fallback | C: configured allowed host authorities (`307–315`, `528–549`) and optional directory URLs (`491–519`), not a reachability or identity assertion. R: address/interface, discovery and reachability evidence. K: reachability from a particular browser or physical identity without suitable evidence. |
| WEB02 199–201, identity | C: hostname only (`293`). R: hardware-ID validity/collision evidence. K: stable identity or collision outcome from a hostname/directory alone. |
| WEB02 202–206, enrollment/revocation | C: one server token/auth mode (`307–313`, `386–395`); `app.js:261–273` clears only the current tab. R plus new authorized operations: per-identity enrollment/revocation and verification. K: a revoked credential or completed in-flight operation without evidence. |
| WEB02 207–209, recovery/age | C: generic key rejection (`386–395`), not expiry/enrollment reasons. R and access design: expiry, permissions, address age and recovery path. K: fresh/reachable if untimed/unverified. |
| WEB03 237–238, comparison | C: `model`, `detected_hat`, `architecture`, `selected_hardware.hat` (`156–165`, `291–296`, `564–570`). R: structured board/HAT revisions, sources and mismatch. K: exact physical revision from an unqualified string. |
| WEB03 239–242, unknowns | C: null HAT and optional selected HAT/speaker labels (`157–158`, `564–570`). R: reason/provenance; user selection needs an operation. K: speaker identity or HAT presence from missing readings. |
| WEB03 243–246, retained speaker | C: optional speaker label only (`564–570`). R: retained impedance, rating, connector and mounting; changes need an operation. K: physical values without evidence. |
| WEB03 247–250, driver/apply | R: driver, overlay, pending/reboot and exact-version compatibility evidence; no corresponding fields in `156–165` or `291–296`. K: untested compatibility/reboot effect; apply requires an operation. |
| WEB03 251–253, denied/stale | C: selected labels and sink availability separately (`194–206`, `291–296`). R: per-field permission reasons and observation ages (`69–73`, `284–299`). K: hardware absence from a failed probe. |
| WEB04 300–303, active/unknown | C: raw `active`, `enabled`, `configuration` placeholder (`230–255`). R: independent configuration validity and link/runtime evidence; K: working without scoped evidence. `tests/test_web.py:141–146` checks the placeholder, not six-state UI. |
| WEB04 304–306, installed | C: `unit_found` only (`247–255`). R: supported package/executable detection and negative evidence; K: installation absence from unit absence. |
| WEB04 307–309, scopes/Bluetooth | C: separate named user/system Snapcast probes and Bluetooth placeholder (`31–38`, `230–262`). R: scope-specific component evidence and proxy detector; K: proxy status from radio alone. |
| WEB04 310–312, version/server | C: Music Assistant server placeholder (`259–260`). R: exact versions, prerequisites, server evidence and owner. K: owner, absence or compatible version without independent evidence. |
| WEB04 313–316, last worked/denied | R: scoped historical function evidence, event time and permission reasons. K: current working from an earlier check; current payload has neither (`230–262`). |
| WEB07 357–360, CPU | C: `cpu_percent` by aggregate/core and null on first/nonpositive-total sample (`93–111`, `159`); swap rates `120–128`. R: interval/sample time, per-counter reset and reasons. `tests/test_web.py:163–169` checks ordinary deltas, not the reset case. |
| WEB07 361–364, swap/zram | C: `memory` fields and `zram` bytes (`86–92`, `129–137`, `159–162`); UI derives swap used (`app.js:150–155`). R: distinguish no device from unreadable stats, per-field time/reason. Ratio can be computed only from valid nonzero compressed bytes. |
| WEB07 365–368, voltages/flags | C: `power.supply_voltage_v`, `throttle_flags`, `undervoltage_now`/`undervoltage_since_boot` on parse (`264–282`); tested with fake values in `tests/test_web.py:148–154`. R: core voltage, source/time/reason and available event evidence. K: actual historical event time from a latched flag alone. |
| WEB07 369–372, Wi-Fi/thermal | C: interface and range-checked numeric `wifi.signal_dbm`, `temperature_c` (`138–147`, `160–162`); R: independently verified signal units, sensor identity, permission reason and timestamps. K: dBm from range alone or CPU sensor from zone number alone. |
| WEB07 373–377, freshness/no score | R: per-sample time, age and ordering (`284–299` only keeps internal clocks); K: age with no timestamp. No aggregate score is returned in the current status fields (`156–165`, `291–296`). |

Additional WEB07 row inventory: C `memory.MemTotal`/`MemAvailable`, disk
`storage.total_bytes`/`free_bytes`, `uptime_s`, `zswap_enabled`, and zram
original/compressed/resident bytes are at `server.py:84–166`; R is needed for
actual disk used/mount, zswap pool/hits/rejects, and each source/time/error.
Available-free subtracted from total is not necessarily actual used. CPU-core
voltage is not returned, even though a fake command includes a core value in
`tests/test_web.py:61–65`.

## Contradictions and mismatches

Separate actual specification tensions from expected gaps in the prototype:

1. **Specification tension:** shared offline retention says retain previous
   readings “only with their last-observed time” (`web-control.md:147–149`),
   while the freshness rule expressly permits unknown observation time and
   requires unknown age (`132–137`, `161–163`). It is unclear whether an untimed
   prior value must disappear or may remain labeled time/age unknown (F13).
2. **Specification/mode tension:** blanket no-valid-key case (`150–151`) versus
   deliberately keyless development mode (`server.py:307–313,531–533`;
   `tests/test_web.py:438–477`), which is not a missing credential in key mode
   (F03). The production authentication prerequisite is explicitly unresolved.
3. **Roadmap coverage gap:** WEB03 requires hardware selection and actionable
   driver/compatibility/reboot state (`roadmap.md:209`); the acceptance examples
   only compare preselected values or disable apply (`web-control.md:237–253`),
   not exercise a supported selection or successful operation (F05–F06).
4. **Roadmap coverage gap:** WEB04 requires all states, prerequisites, errors and
   server ownership (`roadmap.md:210`); the examples do not cover the complete
   component/state matrix, error display or unknown ownership (`web-control.md:
   298–316`, F10–F11).
5. **Roadmap coverage gap:** WEB07 requires sanitized diagnostics/trends
   (`roadmap.md:213`), but the packet's acceptance examples contain neither
   (`web-control.md:355–377`, F15). `web-control.md:93–95` mentions them at a
   broader scope, not an executable WEB07 acceptance example.
6. **Prototype deviations, not claims the future requirements are wrong:**
   criteria call for 10-second visible-page polling and per-sample age
   (`web-control.md:132–141`); `app.js:100–105,323–324` reports and schedules
   three-second updates without per-reading timestamps. Untimed readings can
   look current. The existing three-second loop is not evidence of freshness.
7. **Prototype deviations:** reset criterion (`web-control.md:357–360`) versus
   only aggregate-delta detection/clamping (`server.py:93–111`, F12); verified
   dBm criterion (`369–371`) versus a numeric range check (`server.py:138–145`,
   F17); sensor-specific uncertainty (`348`) versus UI label “CPU temperature”
   (`app.js:119`); unknown empty Wi-Fi/zram (`344,352`) versus ambiguous
   “Unavailable / not wireless” and “Not detected / unavailable”
   (`app.js:121,150–154`).
8. **Prototype deviations:** six independent states and unknown-on-incomplete
   evidence (`web-control.md:270–282`) versus unit `active` badge and a startup
   string (`app.js:157–169`), with no six-state payload (`server.py:230–262`).
   WEB02's enrollment/revocation is likewise absent: only the single key and
   tab-local disconnect exist (`server.py:307–313,386–395`; `app.js:261–273`).
   These gaps are also acknowledged in the design and are not implementation
   review findings in their own right.

## Existing tests and verification

- In `/home/james/Projects/debra`, `python3 -B -m unittest tests.test_docs -v`
  initially **passed: 11 tests**, 2026-11-15 at the clean `f2d4580` checkout.
  A repeat after the checkout changed **failed: 1 of 11 tests**:
  `test_every_cited_key_is_defined` reports `docs/comparisons/devices.md` cites
  undefined keys `S53`, `S54`, `S57`–`S64`. That comparison file was among the
  unrelated modified files on the later status check; the failure was not
  repaired within this assignment. These checks cover documentation links/assets
  and source-register structure, not the truth or completeness of the criteria.
- Static inspection only: `tests/test_web.py` exercises fake command parsing,
  null metrics, CPU deltas, power separation, key rejection and read-only status
  (`81–86`, `141–195`, `263–281`); it does not establish the proposed four
  packets. `tests/test_web_browser.py:73–95,227–291,299–345` exercises a
  synthetic browser, including audio, selected offline/disconnect behavior and
  explicit development bypass. It is opt-in (`352–354`); it does not assert
  observation times, six-state evidence, real enrollment/revocation, hardware
  selection or WEB07 diagnostics/trends. Neither web test suite was run here.

## What I did not check

- No device, network service, real enrollment, real browser or physical hardware
  was contacted or tested. No source beyond the named repository/foundation
  context was used to establish hardware, protocol, or security behavior.
- No implementation changes, commits or pushes. This is not a security audit,
  accessibility review, compatibility assessment, proof of a collector's
  feasibility on every board, or independent runtime verification.
- `docs/design/led-profiles.md` was not needed: none of the four reviewed
  packet-specific criteria depends on an LED profile.
- Handoff: coordinator should resolve the high findings and shared contracts,
  then obtain independent review of any revised criteria. This note is
  unreviewed and does not authorize device operations or design changes.
