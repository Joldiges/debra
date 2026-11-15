# Debra project brief

Intentions captured from James's project-planning answers, 2026-11-14.
These are product requirements, not claims that the software already exists.
Implementation proposals and external evidence are identified separately.

## Purpose: consolidate what already exists

People moving from Google Home, Alexa, and similar products to Home Assistant
face too many disconnected options, unclear comparisons, and difficult bring-up.
Debra should make choosing, assembling/preparing, configuring, and maintaining a
complete affordable solution understandable.

The project has several equal, concurrent responsibilities:

1. A practical Raspberry Pi hardware/software pathway, eventually including a
   prepared image and straightforward first-run/maintenance tools.
2. Source-linked documentation of alternative complete solutions.
3. Hardware and software inventories, comparison tables, limitations, costs,
   compatibility, and buying guidance.
4. Explanations of how components fit together, including SendSpin versus
   Snapcast and their server-side requirements.

Do not turn these into a software-only project with documentation deferred to
the end, or into a comparison site without a usable supported pathway.

## Intended user journey

Home Assistant is already running. A builder prepares an assembled device and
hands it to the end user; beginner instructions start at power-on.

The destination:

1. Boot a customized standard image with the necessary Debra tools already there.
2. If Wi-Fi is not configured, offer an understandable way to configure it,
   ideally through a temporary hotspot/browser flow.
3. Establish a repeatable board-derived identity and hostname; clearly explain
   the hostname, connection details, and next action to the user.
4. Once Wi-Fi and identity work, capture a recoverable pre-feature baseline.
5. Open the device website, for example `debra-1234ca.local`, for ordinary setup
   and maintenance. SSH/CLI/TUI remain developer/recovery alternatives, not a
   requirement for normal configuration.
6. Select hardware, enabled features, audio routing, supported wake-word options,
   music interruption behavior, and update preferences.
7. Pair with the relevant Home Assistant/music services and run guided checks.
8. Return to the same interface later for reconfiguration, component updates,
   diagnostics, snapshots, and restores.

James refined this to **browser-first operation on 2026-11-15**; the earlier
SSH/TUI-first journey is superseded for everyday use. The user should not need to debug
drivers, Python dependencies, audio-server sessions, or network configuration.
A KIAUH-like experience was an analogy for approachable tooling, not a request
to copy its implementation or architecture.

Native speaker volume is the immediate browser priority. Audio, Device, Health
and Components form the initial page; preserve the thorough
[web-configuration scope](design/web-control.md), including hardware selection,
LED mapping, component settings/status, diagnostics, updates and recovery.
Installed/enabled/configured/running/actually working must be distinguished.

During development, Raspberry Pi Imager is an acceptable starting point.
James reports previous Wi-Fi provisioning failures; investigate those rather
than promising that Imager alone solves onboarding.

**Proposed naming detail:** use DNS-friendly `debra-<id>`, not an underscore.
Choose ID length, collision handling, and hardware fallback behavior through
the identity task. A friendly room name is separate from device identity.

## Capabilities and configuration

Required scope includes:

- Hands-free wake word and Home Assistant voice commands.
- Timers **and alarms**, spoken responses, and announcements.
- Single-room music and synchronized multiroom music.
- Configurable duck/resume or pause/resume behavior during voice interactions.
- Multiple hardware/audio-output choices, including external speakers through
  supported 3.5 mm outputs.
- Buttons, visible status, and physical mute where the chosen HAT supports them;
  not every hardware tier must have the same peripherals.

Home Assistant drives most speech, conversation, and cloud/local decisions.
Debra must describe dependencies and expose supported satellite-side choices,
including wake processing where feasible, without forcing a new backend.

SendSpin is the initial music priority. Snapcast remains an alternative, and
multiple installed stacks should eventually be possible where coexistence can
be made reliable. “Installed together” does not automatically mean they can
simultaneously own one sound device or synchronize across protocols.

Document Music Assistant, Snapserver, or other server prerequisites explicitly;
do not assume that “Home Assistant installed” means every music service exists.
Changes to those servers are outside an individual satellite installation unless
separately authorized.

## Hardware and cost

- The original Pi Zero W is an important full-support target. ARMv6 issues are
  work to investigate, not grounds to silently redefine it as music-only.
- Use 32-bit OS variants for 32-bit boards and 64-bit for 64-bit boards.
  Prefer pixi where suitable; uv is acceptable. A stdlib-only component need
  not acquire a dependency manager just for uniformity.
- Pi Zero 2 W is a leading candidate, not an irrevocable baseline. Availability
  is a selection factor.
- A Pi 5 can accelerate development/builds, but success there is not evidence of
  performance or binary compatibility on a Zero W.
- Investigate non-Raspberry-Pi single-board computers too, such as selected
  Orange Pi models, where they offer a useful complete solution. Check exact
  board/HAT revisions, mechanical fit, pin mapping, electrical requirements,
  audio interfaces, drivers, and maintained OS support; also consider their
  own compatible audio boards or USB audio. This is research scope, not a
  compatibility claim or a commitment to maintain every platform.
- Research upcoming boards only as a watchlist until primary sources establish
  specifications and availability. James's mention of a possible future board
  is not a verified product announcement.
- James reports access to the Pi families and HATs discussed in the historical
  README, plus Voice PE and Atom Echo/EchoS3R comparison devices. Exact model,
  revision, quantity, and current condition still need inventory.

Maintain an inventory of boards, HATs, microphones/speakers, power/cables,
microSD cards, and enclosures, with compatibility, metrics, costs, and links.
There is no single audio-quality promise across all combinations.

Use several price tiers and aim very low. Approximately **$40** is a goal for
an economical unit when users already have some of the USB cable, power source,
microSD, and access to a 3D printer. Never present that marginal cost as a fully
inclusive retail kit price.

Anchor shopping in the US; imports and bulk AliExpress-style purchases are
acceptable. Cheap commodity parts are legitimate options. Record quality,
capacity, power, shipping, and reliability evidence rather than assuming that
expensive parts are necessary or that every bargain is dependable.

For non-Pi complete solutions, document comparisons and link upstream. Debra
does not initially promise to maintain their firmware or installers.

## Long-term 3D models and enclosures

James wants 3D models for the different hardware solutions, developed with
**AI + SolidCraft**. Cover selected combinations of Pi model, HAT revision,
speaker, and other fitted parts such as controls, displays, and connectors.
Prefer reusable, parameter-driven designs over an unrelated case for every
combination; do not promise every possible parts permutation.

This is a long-term workstream, not a prerequisite for initial software or
device bring-up. Start from the parts inventory and measured or sourced
dimensions, reusing existing models where suitable and license-compatible.
Keep editable CAD sources, printable exports, exact component/revision lists,
assembly guidance, and provenance together. Check mounting, access, wiring,
ventilation, microphone/speaker placement, and serviceability.

James clarified on 2026-11-14 that a dedicated subagent should inventory the
candidate components and their dimensions, create reusable component/printed
parts, then combine them into a useful variety of SolidCraft enclosures. Allow
actual wiring/plug space, powered-off microSD access and reachable power, with
appropriate removable tops, buttons or covers. Keep speaker output unobstructed
and provide an optional replaceable speaker-cloth/mesh arrangement. Track every
concrete candidate, but prioritize sensible exact combinations rather than
promising the Cartesian product of all parts. See the
[enclosure requirements](design/enclosures.md) for dimensional evidence,
deliverables and separate fit/thermal/acoustic maturity labels.

Distinguish modeled, physically fit-tested, and thermally/acoustically tested
variants. A plausible render or successful CAD operation does not prove fit or
audio quality. Component/concept CAD exists; printing and physical fit tests do not.
see the [long-term model packets](roadmap.md#long-term-3d-models-and-enclosures).

James's 2026-11-15 direction is to reconstruct `RPiSpeaker_v17`, retaining the
existing square speaker and four-screw mounting, forward-facing speaker and
microphones, desktop/wall use and an accessible topper. Earlier claims that a
different speaker is required are not an accepted requirement or proven finding.

## Updates, snapshots, and recovery

- Default to known pinned component versions and manual updates.
- Offer explicit auto-update choices per component; avoid an all-or-nothing
  switch that hides OS/kernel/HAT-driver coupling.
- Keep a completely fresh reference point and a device-specific baseline after
  Wi-Fi/identity setup, before uncertain feature changes.
- Make creating a pre-change snapshot and rolling back quick enough for
  iterative development and ordinary maintenance.
- Copy-on-write snapshots are desirable, not mandatory. An incremental
  non-CoW implementation is acceptable if consistency and restoration are
  demonstrated.
- Account for the boot partition, kernel/modules, overlays, root filesystem,
  configuration, services, and identities as a coherent recoverable state.
- Never silently prune protected baselines or snapshots.
- Reflashing is a fallback, not the main everyday rollback experience.
- A same-card snapshot is not an independent backup and cannot repair a dead
  card. Clearly distinguish rollback, exported backup, and rescue/reflash.
- Personal recovery points contain credentials; protect them and never
  distribute them as factory images.

**Current scope, clarified 2026-11-15:** implement quick on-target file-based
backup/restore and demonstrate the files can be restored. Whole-SD imaging,
replacement-media boot tests and a second destination are deferred; they must
not block browser controls or unrelated work. Keep the same-card/dead-card
limitations visible without reinstating those deferred gates.

James reports the changed supply mostly resolved the lab instability.
Undervoltage is health information, not itself an instruction to reset.
Extensive Pi-5-only hardening is low priority. Preserve earlier fault evidence
as historical; do not describe it as a current measurement.

The two existing rsync scripts are historical, destructive utilities, not an
approved implementation of this recovery design.

## AI-driven development and working with James

James wants strong agents to create and follow a substantial, coordinated plan,
with many bounded activities progressing in parallel. He grants broad freedom
to reshape repository content and replace old design choices.

Use a capable coordinator/reviewer to make architecture and integration
decisions, and give lower-cost models small, explicit assignments they can
demonstrably handle. Editing workers use separate branches/worktrees, cannot
self-approve or merge, and return evidence for independent review. James
should not have to supervise every worker prompt or resolve their conflicts.
See the [AI workflow](ai-workflow.md) for task briefs, stop conditions, review
gates, and the distinction between guidance and enforced controls.

Keep durable learning and handoffs in the project repository so new sessions
can recover context. Use a clear documentation map, dated notes with sources
and uncertainty, and reviewed guides/decisions/test evidence; do not maintain
competing human/AI versions or treat an unstructured dump as established truth.
Preserve corrections and provenance, and keep private operational payloads out
of Git. See [documentation and project memory](README.md).

Start fresh operationally. Preserve useful old findings as research leads, but
do not inherit unknown device state or turn attempted workarounds into rules.

Agents should do investigation, implementation, and analysis. Ask James for
specific physical actions or observations when needed, with short instructions
that identify the board, purpose, commands/effects, expected result, and what
to send back. Several Pi/HAT combinations can be tested in parallel.

Reuse-first integration is a core strategy: James expects substantial portions
of Debra to pull from and combine existing projects, not reinvent good solutions.
Scoped forks and upstream contributions are welcome ways to close relevant
gaps. Consider tracked Git submodules when Debra needs an upstream source tree;
use pinned packages/releases when those are the simpler fit. Keep patches
separate from Debra integration, with pinned sources, provenance, license
obligations, tests, and a maintenance/upstream exit plan. See the
[development workspace guide](development.md); remote publication still needs
an agreed scope.

PiCompose is worth studying and learning from, but is **not a selected
foundation or dependency**. R04 should compare using it, reusing selected
ideas/components where licensing allows, treating it as reference-only, and
choosing another approach. Reuse-first does not mean adopting this particular
project or its deployment choices.

Remote SSH and UniFi-assisted discovery are anticipated development tools, not
existing verified access. Before mutations, bind a physical board to an exact
target and agreed operations; controller labels or an IP alone are not identity.
Do not modify a production Home Assistant instance, network, or unrelated
client simply because it is reachable.

Keep Wi-Fi/access details, private device records, raw logs, and personal
recovery artifacts inside this project's ignored `.local/`, with owner-only
permissions. Never track them in Git or copy them into public examples, factory
images, diagnostic bundles, or shared memory. Keep sanitized templates and
reports in tracked paths. Ignore rules do not encrypt or back up the local
material; see the [storage and recovery boundaries](development.md).

## Documentation, evidence, and publishing

GitHub Markdown is the initial documentation platform. Comparisons need actual
source links and separate personally tested, upstream-documented,
independently reported, exploratory, and unknown claims. Record dates and
version/hardware scope; see [evidence rules](evidence.md).

Do not copy old prices or blanket support claims into a new buying guide without
checking them. Separate functional availability from usability, performance,
maintenance burden, and the effort required to reach that state.

James prefers a very permissive license. **Proposal: MIT for Debra-authored
code and documentation**, subject to copyright/provenance review. This does not
relicense copied upstream code, models, firmware, or bundled OS packages.
No repository license has been applied by this planning update.

James wants low-noise development before promoting unfinished work. GitHub has
no unlisted-public repository mode: public is internet-accessible; private is
restricted. Leave current visibility unchanged until that distinction is
resolved. Do not publish images, create releases, or change visibility as an
incidental part of planning.

## Decisions deliberately left open

- Exact OS release, kernel, 32/64-bit variants, and first validated HAT pairing.
- Reuse/adaptation of an existing prepared image versus our own image stages.
- Lightweight implementation language/UI and the minimal component contract.
- Wi-Fi portal package and account/key enrollment flow.
- Snapshot backend, storage budget, off-device destination, and rescue design.
- Exact test devices, SSH accounts/keys, authorized actions, and test-server
  availability.
- Final license text/copyright attribution and publishing/visibility policy.

Research agents should return recommendations and evidence, not block all work
until every detail is decided. Keep tentative choices visibly tentative.
