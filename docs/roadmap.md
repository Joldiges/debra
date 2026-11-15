# Debra strategy and parallel-agent work plan

Created 2026-11-14 from [James's brief](project-brief.md).
This is a coordinated backlog, **not a claim that any implementation exists**.
Product scope is broad; execute it as independently reviewable work packets.

## Strategy

Run documentation/comparisons, low-cost hardware research, appliance tooling,
and ARMv6 investigation concurrently. Establish one working vertical slice
early, without sacrificing full original Zero W support as a parallel goal.
Reuse-first integration is the expected approach for substantial portions of
Debra. Make existing solutions work together with coherent onboarding,
configuration, and recovery rather than rewriting good implementations.
Scoped forks and upstream contributions are welcome. Evaluate commit-pinned
submodules for source-integrated projects, alongside pinned packages/releases
for runtime dependencies, with licensing, tests, and a maintenance/exit plan;
follow the [development guide](development.md).

The eventual device has these responsibilities, not yet implemented packages:

```text
Prepared standard image
  -> first-boot identity + Wi-Fi/account onboarding
  -> device-specific baseline recovery point
  -> shared configuration / setup-and-maintenance CLI + TUI
       -> HAT and audio configuration
       -> voice adapter -> existing Home Assistant
       -> music adapters -> documented music server(s)
       -> interruption/coexistence policy
       -> updates, diagnostics, snapshots, restore
```

Voice and music server configuration is documented but is not silently changed
by satellite tooling. Identify which settings belong on which side.

## How agents use this plan

1. The coordinator prepares **authorized** packet cards whose dependencies are
   met, supplies current brief/evidence rules, and assigns exclusive output
   paths and device leases. Workers can self-select an eligible prepared
   starter through the [task chains](task-chains.md), after the F05 dispatch
   gate. Task readiness is not live-operation permission.
2. Each worker states its task IDs, inputs, outputs, verification, and scope
   before work. Research can progress without hardware; implementation against
   tentative contracts must be explicitly labeled experimental.
3. Put research in a task-specific note before editing shared conclusions.
   Proposed directories below are ownership boundaries, not folders/tooling
   that already exist. The coordinator can simplify them before implementation.
4. A coordinator/integrator owns `AGENTS.md`, `README.md`, this roadmap, shared
   configuration/contracts, pins, `.gitmodules`/submodule pointers if introduced,
   and merged recommendations. Do not have six workers independently “clean up”
   the same root files.
5. Use separate branches/worktrees for editing tasks from a tracked baseline.
   Worktrees start from commits, not the coordinator's untracked files.
   Commit `39b93fb` now contains the planning foundation; the checkout/index
   were observed clean before task-chain work. Earlier staged-removal warnings
   are historical. Recheck actual state; never sweep user changes into a commit.
6. No two workers mutate one board, shared audio device, or test-server
   configuration concurrently. Research may share sanitized read-only reports.
7. Stop at the packet's acceptance criteria. Report follow-ups as new work,
   not permission to expand device/network scope.
8. Keep private access records, raw logs, snapshots, build outputs, and
   exploratory upstream clones in the checkout's ignored `.local/`, using
   owner-only permissions. Selected source dependencies need tracked pins and
   reproducible inputs, not only ignored clones. Shared reports and handoffs
   are sanitized tracked documents. Ignore rules do not provide backup, and
   worktrees do not inherit the parent's private files; coordinate access
   explicitly without committing credentials.
9. Apply the [coordinator/worker workflow](ai-workflow.md) and
   [filled task template](templates/worker-task.md). Lower-cost models do not
   self-assign architecture or merge their own work. Separate editing worktrees,
   independent capable review, and integration checks are required; F05 pilots
   restricted worker roles before relying on them.
10. Use the [documentation map](README.md) and relevant dated notes to resume
    context. Preserve useful discoveries, assumptions, failures, and handoffs
    within assigned paths using the [learning-note template](templates/learning-note.md).
    Notes are unreviewed evidence, not standing rules or permission. Keep
   canonical reports in their subject area and promote conclusions by review.

The [19-chain dashboard](task-chains.md) groups every packet below and provides
nine concrete starter cards, shared ownership claims, workspace creation, and
handoff commands. This roadmap owns packet state and acceptance; the dispatcher
owns live local claims. Neither advances work merely because a worker submits.

Status meanings: `done` = linked deliverable and verification;
`ready` = can start without another packet, not necessarily authorized;
`blocked` = dependencies outstanding. All implementation/physical validation
below is unstarted.

## First parallel wave

These are useful bounded assignments before any device reconfiguration:

| Lane | Initial packets | Initial exclusive deliverable |
| --- | --- | --- |
| Hardware/value researcher | R01 | `docs/research/R01-hardware.md` |
| Complete-solution researcher | R02 | `docs/research/R02-alternatives.md` |
| Protocol/server researcher | R03 | `docs/research/R03-music-stacks.md` |
| Reuse/image researcher | R04 | `docs/research/R04-reuse.md` |
| Alternative-board researcher | R07 | `docs/research/R07-alternative-boards.md` |
| ARMv6 engineer | Z01 | `docs/research/Z01-armv6.md` |
| Recovery engineer | B01 | `docs/research/B01-recovery.md` |
| Onboarding engineer | N01 | `docs/research/N01-onboarding.md` |
| Test/integration designer | T01 | `docs/testing/acceptance.md` |
| Coordinator | F01, F04 | Working-state assessment and proposed license/provenance note |

Do not launch workers on the assumption that future files or interfaces
already exist. Give each worker this brief and the relevant source register.
The first wave returns evidence and recommendations; it does not run privileged
builders, flash cards, or configure reachable Pis.
Until F01/F05 establish a worker baseline and verify restricted roles, a capable
coordinator can do direct work or arrange bounded read-only reviews; do not
launch lower-cost editing workers. The claim helper is not a substitute for that
pilot, and no workers edit the shared integration checkout.

## Gates and sequencing

| Gate | What it establishes | Work that need not wait |
| --- | --- | --- |
| G0: planning foundation | Brief, evidence conventions, legacy leads, and this backlog exist. **Documentation only, complete in this change.** | All first-wave research |
| G1: agreed contracts | F01–F04, F02's research dependencies, and T01 are complete; interfaces, source layout, test policy, and license proposal are recorded. Licensing approval need not block research. | Hardware comparisons, ARMv6 dependency experiments in isolated environments |
| G2: recoverable lab device | L01, N02/N03/N05, B02/B03, and a baseline A01 check pass on an authorized device. | Control-core fixture tests, image design, sourced alternative guides |
| G3: working integrated slice | Core setup, one HAT, V02, M01, A03, T02, and basic U01 pass. Repeatable install/reconfigure/reboot and a tested rollback exist. | ARMv6 fixes, other HATs, Snapcast, wider comparisons |
| G4: parent-facing candidate | Image/onboarding, usable TUI, recovery/rescue, update choices, compatibility evidence, and T03–T05 pass. | Additional variants and experiments, clearly outside the supported matrix |

Do not call G3/G4 complete for the original Zero W because a Zero 2/Pi 5 passed.
If ARMv6 remains blocked, label any other-board candidate accurately and keep
the full-support track open.

The long-term AI + SolidCraft model/enclosure lane below does not block these
software/device gates. Mechanical and acoustic validation remain separate
from software compatibility.

## Foundation and coordination

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| F00 / done | — | This planning foundation: project brief, agent instructions, evidence register, legacy review, and roadmap. Local links and existing shell syntax checked; no hardware claims. |
| F01 / done | F00 | [Baseline/ownership assessment](testing/results/2026-11-14-ai-readiness.md#f01-deliberate-committed-baseline-and-ownership): clean committed preflight at `88e1fcb…`, remote verified, exclusive worktrees/paths, handoff locations and frozen uncommitted-context handling established. No unrelated changes discarded/staged; this does not approve F05 or live operations. |
| F02 / blocked | R04, N01, B01, Z01 | Minimal architecture decision in `docs/design/architecture.md`: native versus containers by platform, configuration authority, privilege boundary, component lifecycle, audio owner, and image relationship. Choose the smallest suitable stack; do not assume Docker works on ARMv6. Specify lightweight CLI/TUI approach rather than building a generic plugin framework. |
| F03 / blocked | F01, F02, T01 | Establish actual source/test layout, shared component/config interfaces, and developer verification commands. Implement R04's selected dependency mechanism, including tracked submodules where justified, consistent source pins, fresh-clone/worker/CI initialization, and source packaging. Decide test/lint dependencies and command order; safe default checks must never require root, hardware, Wi-Fi, or network mutation. Keep networked dependency setup separate from offline checks. Update AGENTS with commands that really run. |
| F04 / ready | F00 | License/provenance proposal: permissive Debra license (MIT candidate), copyright attribution, and separate obligations for upstream code, scoped patches/forks, models, firmware, wheels, and OS/image distribution. Identify contribution requirements; do not assign unsupported copyrights or relicense third-party files. |
| F05 / ready | F01 | **Partial, not accepted; production dispatch closed.** [Readiness evidence and missing coverage](testing/results/2026-11-14-ai-readiness.md): documentation pilot reviewed/integrated; actual synthetic read/edit/write denials observed, but patch/alternate-route/intercepted-backend evidence and claim-specific policy acceptance remain missing. Finish the low-risk pilot under the [approved coordinator mandate](ai-workflow.md#approved-coordinator-mandate): verify fresh context, branch/worktree/base, permitted edits, prohibited scope/shell/MCP/nested delegation, handoff, separate review and integration checks without credentials/devices. Record effective permissions and limits; fail closed. `ready` means its F01 dependency is met, not that this gate passed or dispatch may open. No automatic routing, isolation or merge enforcement is claimed. |

## Research, inventory, and user documentation

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| R01 / ready | F00 | Source-linked parts inventory: Pi variants, ReSpeaker revisions, WM8960, speaker/output choices, power, microSD, cables, and printed/bought cases. Record US/import prices, quantities, availability, and full-kit versus reused-parts totals; identify a plausible ~$40 route without fabricating compatibility. |
| R02 / ready | F00 | Compare selected complete alternatives, including Voice PE and Atom Echo/EchoS3R. Distinguish documented functionality, practical limits, costs, and maintenance burden. Link upstream bring-up instead of promising Debra-owned firmware. |
| R03 / ready | F00 | Map SendSpin/Snapcast transports, receiver implementations, Music Assistant/Snapserver roles, HA integration, server version requirements, and discovery/pairing. Compare delay/sync, audio backend, ARMv6 viability, interruption control, and coexistence with dated primary sources. |
| R04 / ready | F00 | Audit current LVA/PiCompose/pi-gen and onboarding/recovery reuse opportunities. Reuse-first is the expected outcome wherever suitable, but PiCompose is not preselected: compare whole adoption, partial/information reuse, reference-only, and another approach. For each candidate, recommend its role and package/release, source archive, tracked submodule, or documented-only integration, with canonical/fork URL, revision, license, and rationale. Compare configuration/adapters, scoped upstream patches/forks, and a Debra-owned image builder; identify resource, architecture, and default-policy gaps. Return pinned patch/test/maintenance/upstreaming and clone/build/update/packaging plans where relevant; do not create a remote fork or publish by default. |
| R05 / blocked | R01, R02, R03, R04, R07, T01 | Integrate readable hardware/software tables in `docs/comparisons/` and a “choose your path” guide. Claims carry evidence/date/scope; unknowns remain unknown. No table implies an untested combination is supported. |
| R06 / blocked | T02, R05 | Write beginner prepared-unit walkthrough plus separate builder/developer guides in `docs/guides/`. A reader can identify hardware, provision Wi-Fi, connect, configure/pair, recover, and find alternatives without reading agent plans. Clearly mark unreleased features. |
| R07 / ready | F00 | Screen selected non-Pi SBCs, starting with Orange Pi candidates, without treating a brand as one platform. For exact board/HAT revisions, assess mounting/header fit, pin mapping, electrical/power requirements, audio interfaces, driver/device-tree and maintained OS/kernel support. Consider board-native audio expansions and USB audio alternatives. Compare full usable cost, availability, maintenance, identity/onboarding/recovery implications, and voice/music dependency compatibility. Return primary sources and unknowns, not an untested support promise; physical validation and a maintained Debra port need separate selection and authorization. |

## Lab fleet and access

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| L01 / blocked | F01, T01 | With James, identify exact physical boards/HAT revisions, power/storage, disposable test media, and separate test servers. Establish target-specific access/operation scope and pre-change recovery before mutations. Keep operational access records in `.local/access/`; publish only sanitized aliases/capability inventory. |
| L02 / blocked | L01, F03 | Target selection and test runbook in `docs/testing/fleet.md`: bind SSH host fingerprint to physical alias, verify actual architecture/revision, lease device to one worker, and define reconnect/emergency access. UniFi discovery is corroboration, not authorization or identity proof. |
| L03 / blocked | L02, B03 | Repeatable fresh-device preparation and reset procedure. A worker can begin from a known baseline, record pins, run a packet, restore, and hand off a clean device without inheriting hidden changes or private credentials in Git. |

## First boot, identity, and connectivity

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| N01 / ready | F00 | Compare maintained Wi-Fi portal/hotspot tools and Imager/manual development flows. Specify AP-to-client transition, bad credentials, country/band constraints, single-radio limitations, re-entry, credential storage, account enrollment, and how users find hostname/IP after the AP disappears. Do not choose a package from hearsay alone. |
| N02 / blocked | F03 | Implement/test identity helper: stable hardware-derived `debra-<id>`, friendly-name separation, explicit missing-ID/collision handling, and predictable behavior across reboots, reflashes, and network changes. Cloned machine-id or literal `unknown` must not generate a fleet of indistinguishable devices. |
| N03 / blocked | N02, F03, L01 | Idempotent first-boot identity/account/SSH preparation. Generate unique host keys/machine identities on each device, exclude builder keys/secrets from images, and present clear connection instructions. Define safe user authentication without shipping a universal admin password. |
| N04 / blocked | N01, N03, B03 | Implement selected onboarding on a leased board; test initial connection, wrong password, interrupted setup, existing-network outage, reconfiguration, and AP shutdown after success. Prevent an open unattended administration portal. Never test by changing the household router. |
| N05 / blocked | N03, N01, L01 | Document/test the short-term Imager-to-SSH development path independently of the future portal. Record actual OS/customization behavior and failure recovery, including hostname/mDNS fallback. Do not make portal completion block every other hardware experiment. |

## Shared control core and maintenance UI

Paths `control/` and `components/` below are proposed boundaries pending F03,
not a requirement to choose a particular programming language or framework.

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| C01 / blocked | F03 | Versioned config model with validated hardware, enabled components, routing, interruption, and update options. Define public config versus protected runtime secrets, defaults, migrations, and atomic persistence. Invalid input must not partly change the device. |
| C02 / blocked | C01 | Component lifecycle/operation layer: inspect, plan, install/configure, enable/disable, health, update, and rollback interfaces. Repeating an operation converges rather than appending duplicate config; cancellation/failure leaves an understandable state. Keep privileged effects explicit and mockable. |
| C03 / blocked | C02 | Minimal CLI and plan/dry-run presentation using the same operation layer as the future TUI. Test dependency ordering, configuration diff, partial failure, and nonzero error reporting. Only describe commands after they exist. |
| C04 / blocked | C03, B02, U01 | Lightweight SSH-friendly TUI: feature selection, reconfiguration, status, updates, per-tool update policy, snapshots/restores, and diagnostics. Explain prerequisites/reboots; test small terminals and interrupted sessions. No second implementation of business logic. |
| C05 / blocked | C02, L02 | Sanitized diagnostics/health reporting: active components, pinned versions, services, audio devices, network reachability, and actionable errors. Exclude credentials/recorded microphone content; do not automatically upload bundles. |

## HATs, audio, and interruptions

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| A01 / blocked | R01, R04, T01, L01 | Fresh baseline capture/playback inventory for exact HAT/kernel revisions on authorized boards. Record ALSA/PipeWire/Pulse roles, usable device identifiers, gains, routing, and required reboots. Save a small, safe-volume reproducible smoke procedure. |
| A02 / blocked | A01, C02, B03 | Hardware profiles for tested ReSpeaker V1/V2 and WM8960 combinations, prioritizing what passes first. Separate kernel/overlay dependencies, avoid stale retry/install hacks, and prove boot-without-interactive-login operation. Unsupported revision choices fail with guidance, not guessed writes. |
| A03 / blocked | A02, V02, M01, C01 | Implement/test configurable duck/resume and pause/resume across the actual separate voice/music processes. Preserve user-paused/muted state and changed volume; cover errors, overlapping announcements/timers, and multiroom implications. Upstream LVA internal-player docs are not the test. |
| A04 / blocked | A02, C02, V02 | Optional per-HAT peripheral mapping for status/buttons/mute/volume where hardware supports it. Document actual versus cosmetic microphone mute and unavailable capabilities. A HAT without LEDs/buttons is still a valid profile. |

## Voice integration

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| V01 / blocked | R04, Z01 | Version-scoped LVA dependency/API audit: architecture requirements, wake engines, model/library ABI, audio/session expectations, HA discovery/identity, timers versus alarms, and device/server setting ownership. Explicitly list unsupported/unknown features before implementing an adapter. |
| V02 / blocked | V01, A02, C02, B03 | Install/configure/health adapter for one pinned voice runtime on the first viable board. Verify wake, streaming, HA command/response, announcement, timer, restart, and pairing persistence with exact server versions. No silent HA-server changes. |
| V03 / blocked | V02, C01 | Expose supported wake models/location and satellite options without duplicating HA provider configuration. Probe what exists; unsupported choices explain why. Include performance/resource and microphone-privacy effects in guidance. |
| V04 / blocked | V02, A03 | Close timer/alarm/announcement feature gaps. Test persistence, cancellation, reboot/outage behavior, audibility during music, and overlapping events; document which guarantees depend on HA. Do not advertise alarms solely because countdown timers work. |

## Music adapters and coexistence

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| M01 / blocked | R03, A02, C02, B03 | First pinned SendSpin receiver adapter, with explicit server requirements, pairing, output selection, delay/volume controls, service ownership, and health checks. Preserve client identity/config across restart/update; make first pairing usable without log archaeology. |
| M02 / blocked | M01, L02, T01 | At least two-device synchronization/reconnection test, recording server/client versions, audio paths, conditions, measured skew/uncertainty, and resource use. Demonstrate late join, loss/rejoin, and chosen delay adjustment rather than borrowing upstream numbers. |
| M03 / blocked | R03, C02, A02, B03 | Optional Snapcast receiver adapter and source-linked prerequisite guide. Use tested backend/version choices; expose it as an alternative without making it a mandatory dependency of SendSpin. |
| M04 / blocked | M03, A03, M02 | Coexistence policy for voice plus SendSpin plus Snapcast: exclusive/shared audio ownership, output routing, discovery/ports, volume, priority, and transitions. Detect unsupported combinations; do not promise cross-protocol synchronized groups without evidence. |

## Original Pi Zero W / ARMv6 engineering track

This track remains a first-class goal. It can produce useful fixes independently
of the newer-board vertical slice. Absence of an upstream ARMv6 build is a
constraint to investigate, not a claim that success is impossible.

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| Z01 / ready | F00 | Current ARMv6 dependency/instruction-set matrix for voice, wake runtime, SendSpin, audio libraries, Python, and OS/kernel. Inspect legacy build leads and distinguish ARMv6/Raspbian armhf from ARMv7/AArch64 packages. Rank blockers and likely server-side/offload options without replacing the full-support goal. |
| Z02 / blocked | Z01, F03 | Reproducible isolated build recipe/provenance for only missing required artifacts. Choose native/cross/emulated work per dependency; retain signature verification, exact toolchain/source pins, artifact hashes, and licensing. Pi 5 build success alone is insufficient. Privileged builds require authorized host scope. |
| Z03 / blocked | Z02, L02, B03 | Load/run each needed binary/model on original Zero W, detect illegal instructions/ABI/linker failures, and record imports/runtime behavior. A wheel tag or `file` output does not prove the code executes on ARMv6. |
| Z04 / blocked | Z03, V02, M01, T01 | Profile voice alone, music alone, and combined operation on Zero W: CPU/RAM, wake responsiveness, audio dropouts, temperature, and sustained stability. Investigate one bottleneck at a time; retain measured conditions and raw sanitized evidence. |
| Z05 / blocked | Z04, V03, A03 | Resolve or characterize bottlenecks through appropriate runtime/model/build/offload changes; compare feature consequences explicitly. Repeat full capability tests. If blocked, produce a reproducible issue and next experiment, not an unsupported success claim or silent removal from scope. |

## Snapshots, backups, and restore

Research backend candidates before choosing a filesystem or recreating a
backup product. Speed matters, but incomplete/coherency-unsafe “snapshots”
must not masquerade as restoration guarantees.

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| B01 / ready | F00 | Compare CoW and incremental non-CoW approaches against real Pi layouts: boot/root coupling, storage overhead, consistent capture, live/offline restore, unbootable-root rescue, power loss, secret protection, and minimum-card capacity. Recommend a minimal first backend plus an exit path. |
| B02 / blocked | B01, F03 | Backend interface/manifest and fixture-based capture/list/verify/restore tests. Record what is included/excluded, device compatibility, prerequisites, storage/mount identity checks, and interrupted-operation handling. Tests must not address host `/` or rely on the old rsync scripts. |
| B03 / blocked | B02, L01, N03 | On disposable/authorized media, create and actually restore a pre-feature device baseline after Wi-Fi/hostname setup. Prove networking/SSH, identities, boot files, kernel/modules, and config are coherent afterward. Record duration and recovery path; a snapshot creation message is insufficient. |
| B04 / blocked | B03, C02 | Efficient incremental/pre-change snapshots, named protected baseline, capacity checks, and UI-ready progress/errors. Do not silently prune or overwrite recovery points; insufficient space must give an actionable safe stop. Test failed/interrupted capture and restore. |
| B05 / blocked | B03, N05 | Rescue and off-device backup/export procedure, including dead-card/unbootable-root fallback. Keep local personal snapshot exports in `.local/snapshots/` with protected independent backup coverage; test a representative restoration to the intended target. Explain same-card rollback versus independent backup and identity handling when moving to a different board. |

## Version management and updates

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| U01 / blocked | F03, R03, V01 | Pin/compatibility manifest and update planner: record installed versus selected versions and OS/kernel/HAT/runtime coupling. Default manual; distinguish component updates from OS/firmware changes and identify which combinations are tested. |
| U02 / blocked | U01, C03, B04, V02, M01 | Manual update transaction: inspect, checkpoint, apply, health-test, report, and restore on failure when safe. Prove rollback using a deliberately failed update on disposable/authorized media; include config/schema compatibility. |
| U03 / blocked | U02, C04 | Explicit per-component opt-in auto-update with scheduling, activity/reboot policy, compatibility gates, space checks, diagnostics, and an easy disable path. No “latest on every boot” default or automatic untested kernel/driver jump. |

## Image preparation and delivery

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| I01 / blocked | F02, N01, B01, Z01 | Image design decision: reuse upstream stages/images where suitable, required architecture variants, minimum-card budget, preinstalled tools, first-boot separation, and sanitized factory state. Prefer the lightest supportable route over a custom distribution. |
| I02 / blocked | I01, N03, C03, A02, U01, F04 | Reproducible pinned prepared-image recipe with license/component manifest and hashes. No personal Wi-Fi/keys, baked machine-id, pairing identity, populated snapshot, or unattended shared admin credential. Build only in an explicitly authorized host environment. |
| I03 / blocked | I02, N04, C04, B04 | Flash/boot validation on at least two distinct boards: unique identities/keys, Wi-Fi onboarding, hostname discovery, initial baseline, feature selection, and reboot. Record exact hardware variants; do not infer Zero W support from an ARM64 image. |
| I04 / blocked | I03, B05, T03, F04 | Release-candidate packaging: checksums, artifact provenance, supported matrix, known issues, minimum media, flashing/recovery instructions, and redistribution notices. Publishing requires a separate explicit release/visibility decision. |

## Verification and release readiness

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| T01 / ready | F00 | Acceptance matrix and safe test strategy in `docs/testing/`: fixture/unit checks versus privileged image tests versus physical/fleet tests. Propose measurable latency/sync/reliability thresholds and report format. Parent UX, bad Wi-Fi, no-login audio, full storage, and restore are first-class cases. |
| T02 / blocked | F03, C03, A02, V02, M01, B03 | Reproduce a clean vertical slice from baseline: install/configure, HA pairing, wake/response, timer/announcement, music, reconfigure, reboot, and rollback. Record all versions and repeatability, including unsuccessful cases. |
| T03 / blocked | T02, M02, V04, A03, U02, B05 | Failure/soak suite: audio-server/service crash, missing microphone, network/HA/music-server outage, pairing persistence, storage pressure, interrupted update, and power-loss risk scenarios on sacrificial media. Document what recovery actually guarantees. |
| T04 / blocked | F03, C03, B02 | Add minimal CI for implemented local checks and docs/config validation; keep hardware/privileged tests opt-in and clearly separated. Document exact single-test/focused commands and required fixtures. No secrets or fleet access in ordinary public CI. |
| T05 / blocked | I03, R06, T03 | Fresh-user rehearsal: James or another non-developer follows the prepared-unit guide without undocumented fixes. Record every intervention and resolve blockers. Only mark supported combinations that have the required evidence; original Zero W full-support status remains explicit. |

## Long-term 3D models and enclosures

Work requested by James, using **AI + SolidCraft** for selected Pi + HAT +
speaker + accessory combinations. His expanded
[enclosure requirements](design/enclosures.md) call for a dedicated subagent,
candidate-wide dimensional coverage, reusable parts and a useful variety of
assemblies with wiring, microSD/power access and removable lids/grilles or cloth.
This lane is outside the initial software critical path; no Debra CAD models or
physical validation exist yet. The `models/` paths below are proposed
deliverables, not existing tooling. Read-only dimensional preparation can run
alongside research without marking these prerequisite-gated packets complete.

| ID / state | Depends on | Deliverable and acceptance |
| --- | --- | --- |
| D01 / blocked | R01, F04 | Inventory all concrete candidate Pi/HAT/speaker/accessory identities and prioritize sensible combinations and reusable CAD. Record exact revisions, dimension sources or measurements, mounting/connector clearances, header/stack heights, speaker envelopes/openings, controls/displays, fasteners, and licensing/provenance. Return the coverage/missing-measurement table and shared component/interface parameters required by the [enclosure brief](design/enclosures.md); do not invent fit from photos or merge similar seller listings. |
| D02 / blocked | D01 | Use a dedicated, bounded AI + SolidCraft assignment to develop reusable component envelopes, printable trays/carriers/lids/grilles and a small useful variety of exact assemblies, beginning with one reviewed layout. Proposed `models/` organization and acceptance are in the [enclosure brief](design/enclosures.md). Deliver editable sources, parameter sets, printable exports, BOM/attribution and assembly/print guidance. Verify wiring/plug/service space, powered-off microSD and power access, buttons/covers, optional cloth/mesh retention, cooling and microphone/speaker paths; exercise parameter changes. Distinguish provisional/dimension-sourced geometry from CAD-only/physically tested assemblies. |
| D03 / blocked | D02, L01, A01 | With separately agreed printing/device-test scope, physically check the selected variant's fit, assembly, controls, access, thermal behavior, and microphone/speaker performance against a documented baseline. Record hardware, model revision, material/print settings, measurements, and failures; iterate before marking that exact combination validated. Add further variants incrementally rather than claiming all parameter combinations work. |

## Handoff format

Every packet returns a short report in its assigned area:

```text
Task ID / author / exact model identifier (or unknown):
Scope completed / files or artifact paths:
Dependencies and versions actually used:
Upstream base / patch pins, licensing, and contribution plan, if relevant:
Sources and date checked:
What ran / exact commands / observed results:
Not tested / uncertainties / known failures:
Device alias and scope, if any (no credentials):
Recovery point and restoration result, if relevant:
Interface changes proposed (not silently imposed):
Next independent task / blocker / specific action needed from James:
```

Separate observed results from proposed fixes. Do not mark a packet done on
“should work,” successful compilation alone, or a generic tool success flag.

## Immediate next action

F01's baseline assessment is recorded; finish F05's missing execution evidence
and claim-specific policy review before any production dispatch activation.
The [version-pinned source investigation](testing/results/2026-11-15-f05-source-feasibility.md)
identifies reusable model-free test helpers, but no safe harness has run and no
isolated Bun/dependency environment has been established.
Use the [corrected preliminary research](research/2026-11-14-preliminary-findings.md)
as scoped evidence, not completed packets or dependency selections. Capable
coordinator work and bounded sanitized read-only research may continue.
Hardware implementation starts only after target/access/recovery arrangements,
not by discovering and modifying every Pi on the household Wi-Fi.
