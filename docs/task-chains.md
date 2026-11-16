# Task chains: pick work, claim it, hand it back

**Worker entrypoint for “work on any task chain” or “work on this taskchain.”**
The [roadmap](roadmap.md) remains the canonical backlog and acceptance criteria.
This dashboard groups **65** of its packets into **19 streams**, not 19 competing
TODOs; the ten browser packets (`WEB01`–`WEB10`) are not in the registry yet.
The [machine-readable catalog](work/chains.json) assigns every registered packet
once.

## Quick prompts

From this repository, James can tell a worker:

> Work on any task chain. Read AGENTS.md and docs/task-chains.md. Use the
> dispatcher to claim one eligible starter, create your workspace, announce
> ownership, follow its assignment, and submit for capable review. If dispatch
> is closed, stop with the reported prerequisite; do not open it yourself.

Or:

> Work on task chain `alternative-boards` using the same workflow.

“Work on a chain” means **one reviewable packet at a time**, not permission to
run through future blocked tasks. A capable coordinator advances the chain
after integration, prepares the next bounded card, and opens the new baseline.
Workers never mark their own packet done or choose new architecture.

## Current availability

- Nine source-research starters have concrete [cards](work/cards/R01.md), named
  output paths, acceptance criteria, and no device access.
- The dispatcher is implemented with offline fixture tests. **Production
  dispatch is closed by default.** The tooling is committed and F01 is complete;
  [F05 remains partial](testing/results/2026-11-14-ai-readiness.md), not accepted.
  Finish missing execution coverage, validate a claim-specific role policy and
  obtain capable review before activation. An observed documentation pilot is
  not an approved production lower-cost editing role.
- Future implementation, physical tests, architecture, and curated shared
  conclusions require new coordinator cards and the roadmap prerequisites.
  All 65 registered packets are mapped below; the ten browser packets are not in
  the registry, and only the nine starters are self-selectable.
- A worker without permission to run the dispatcher asks its trusted
  coordinator to execute the exact startup/status/submission operations.
  Do not enable shell or infrastructure access to bypass a denied tool.

## Stream dashboard

“Starter” means card prepared, **not** permission/pilot complete. Later packets
retain **all** cross-chain dependencies in the roadmap; listed order is a
direction, not a replacement dependency graph.

| Chain ID | Direction / packets | First independent result or next gate |
| --- | --- | --- |
| `hardware-value` | R01: parts, revisions, three cost tiers | [Starter](work/cards/R01.md) → `docs/research/R01-hardware.md`; feeds audio, comparisons, enclosures |
| `complete-alternatives` | R02: Voice PE, Atom Echo, EchoS3R | [Starter](work/cards/R02.md) → `docs/research/R02-alternatives.md`; upstream setup, not new firmware |
| `music-research` | R03: protocols, receivers, servers | [Starter](work/cards/R03.md) → `docs/research/R03-music-stacks.md`; feeds SendSpin/Snapcast and updates |
| `upstream-reuse` | R04: LVA, PiCompose, pi-gen and partial reuse | [Starter](work/cards/R04.md) → `docs/research/R04-reuse.md`; input to architecture, not architecture authority |
| `alternative-boards` | R07: exact Orange Pi/other SBC and audio options | [Starter](work/cards/R07.md) → `docs/research/R07-alternative-boards.md`; no inferred HAT support |
| `zero-w` | Z01 → Z02 → Z03 → Z04 → Z05: dependency matrix, builds, actual execution, profile, fixes | [Starter](work/cards/Z01.md) → `docs/research/Z01-armv6.md`; later build/device scope separate |
| `recovery` | B01 → B02 → B03 → B04/B05: candidates, fixtures, proven restore, incremental/rescue | [Starter](work/cards/B01.md) → `docs/research/B01-recovery.md`; no host snapshots/restores |
| `onboarding` | N01 → N02/N03 → N05/N04: research, identity/keys, development fallback, portal | [Starter](work/cards/N01.md) → `docs/research/N01-onboarding.md`; no household-router changes |
| `verification` | T01 → T02 → T03/T04 → T05: acceptance, vertical slice, fault/CI, fresh-user trial | [Starter](work/cards/T01.md) → `docs/testing/acceptance.md`; numeric thresholds remain proposals |
| `foundation` | F00 → F01/F04/F05 → F02 → F03: baseline, license proposal, pilot, contracts, tooling | Coordinator-owned; F01 baseline assessment recorded, F05 permission pilot remains partial and dispatch closed; no applied license yet |
| `lab-fleet` | L01 → L02 → L03: inventory/scope, target binding, clean reset | Requires named hardware, authorized operations, recovery; no automatic device leasing here |
| `control-ui` | C01 → C02 → C03 → C04/C05: config, operations, CLI, SSH TUI, diagnostics | Requires F03 and reviewed contracts; don't invent a plugin framework |
| `audio` | A01 → A02 → A03/A04: baseline, HAT profiles, interruption, controls | Requires exact revisions, R01/R04/T01/L01; hardware permission separate |
| `voice` | V01 → V02 → V03/V04: LVA audit, adapter, options, timer/alarm gaps | Requires R04/Z01; later adapter uses tested audio/recovery/core |
| `music-adapters` | M01 → M02 plus M03 → M04: SendSpin, multi-device test, Snapcast, coexistence | Requires R03/A02/C02/B03; no implied cross-protocol sync |
| `updates` | U01 → U02 → U03: pins/planner, rollback transaction, opt-in automation | Requires F03/R03/V01; manual defaults and proven recovery |
| `images` | I01 → I02 → I03 → I04: reuse/design, pinned recipe, multi-board boot, packaging | Requires research/architecture and authorized build host; publication still separate |
| `guides-comparisons` | R05 → R06: sourced choose-your-path, beginner/builder guides | Requires research including R07 and T01; usable walkthrough depends on T02 |
| `enclosures` | D01 → D02 → D03: dimensional/provenance inventory, SolidCraft model, physical fit/audio | Requires R01/F04; modeling doesn't prove physical fit or acoustic quality |

## Worker startup

Run from the clean checkout containing the committed dispatcher. Examples use
sanitized labels; replace the owner with a unique session ID and the model with
the exact host-reported identifier/variant verified for the role.

```bash
python tools/taskchain.py list
python tools/taskchain.py start --chain any --owner session-unique --model provider/model#variant
```

For a named stream, replace `any` with its ID. `any` chooses the first eligible,
unowned starter in catalog order. It excludes gated streams, incomplete
dependencies, live claims, and already integrated starters. If nothing is
eligible it stops, rather than loosening scope or silently switching tasks.

Successful startup returns a claim ID, branch, absolute workspace, base, exact
allowed paths, and the generated **`.local/assignment.md` in that workspace**.
It checks committed dispatch inputs and a clean source, reserves the chain,
creates `work/<claim>` and an owner-only `.local/worktrees/<claim>` beneath the
main checkout, verifies branch/base/cleanliness, then writes the assignment.
Private files from the main checkout are not copied.

1. **Move the worker's session/working directory to that absolute workspace.**
   Creating a worktree does not move a running AI session automatically.
2. Read `.local/assignment.md` and its required inputs. Announce, for example:
   `CLAIM <id> | alternative-boards/R07 | owner <session> | workspace <absolute path>`.
3. Acknowledge objective, allowed paths, checks, and stop conditions. Write only
   the named report, claim-specific handoff, and optional claim-specific note.
   Each starter permits new files, not edits to root docs, pins, tests, or rules.
4. Research current primary sources. Record exact scope/date/revisions and
   distinguish requirements, upstream facts, observations, assumptions, and
   unanswered questions. Unavailable sources produce `unknown`, not invention.
5. Fill the generated handoff path using the
   [handoff fields](templates/worker-task.md#required-handoff). Run only permitted
   checks. No worker Git staging/commits, merges, pushing, self-review approval,
   or host/device changes are authorized.
6. Submit using the claim and owner, from either registered checkout:

```bash
python tools/taskchain.py submit CLAIM --owner session-unique
```

Submission requires the named output and handoff, exact base/branch, no staged
changes, and no changed/untracked non-ignored files outside the allowed paths.
It fingerprints all candidate files. **Stop editing after submission.** The
claim remains owned while awaiting capable review; it is not ready for another
worker and does not advance the chain. The helper checks scope/bytes, **not**
truth, secrets, citations, semantic correctness, or actual tool permissions.

## Resume, blockers, stale owners, and review

```bash
python tools/taskchain.py resume CLAIM --owner session-unique
python tools/taskchain.py block CLAIM --owner session-unique --reason "Primary source unavailable; need coordinator decision"
```

- Resume the same active/blocked claim, base, branch, and workspace. Do not make
  a new claim to bypass an existing owner. If fresh context cannot establish
  ownership or there are unexplained edits, ask the coordinator.
- Blocked, submitted, starting, and workspace-failed claims **keep ownership**.
  Updated timestamps aid supervision but are not leases. No automatic expiry,
  takeover, pruning, branch removal, or worktree deletion occurs.
- The coordinator confirms a stale worker stopped, preserves its files and
  handoff, then records `close CLAIM --outcome released --evidence "..."` if
  reassignment is appropriate. A new claim gets a new workspace. Never resume
  editing a closed claim, even though its files remain.
- A creation crash/failure leaves a reservation; inspect the branch/worktree
  before releasing it. Missing workspace ≠ permission to discard Git metadata.
- Submission stays frozen. For requested changes, the coordinator records a
  release/reassignment with the reviewed findings as new input; this version
  deliberately has no automatic repair/advance loop. Preserve the old candidate.
- Independent capable review examines the actual diff, card and primary sources;
  the integrator independently reproduces safe checks. Review approval names the
  candidate hash. Later changes invalidate it. The coordinator integrates using
  explicit paths, checks the result, records review and integration evidence,
  then calls `close CLAIM --outcome integrated --evidence "..." --integration COMMIT`.
  The helper verifies frozen bytes and that the commit contains those files;
  it does **not** perform a merge or prove independent review happened.
- The coordinator updates the roadmap and prepares/approves the next card in a
  new committed baseline. Implemented automation dispatches **starters only**;
  future tasks are not magically safe because they share a chain name.

## Coordinator setup and limits

After the actual F05 pilot, from a clean committed baseline:

```bash
python tools/taskchain.py open --coordinator coordinator-session --reviewer capable-reviewer --model provider/model#variant --evidence docs/testing/F05-worker-pilot.md
```

The evidence path must exist in that commit and contain sanitized pilot results,
selected model/variant, effective allowed/denied tool checks, limitations, and
review. `open` records a human/agent decision; it cannot validate the report's
truth or enforce coordinator identity. Do not run it merely because this
example exists. A new base or different model requires coordinator revalidation.
`python tools/taskchain.py pause` closes new dispatch without dropping claims.

**Coordination boundary:** the shared registry is
`<git-common-dir>/debra-work/state.json`, protected by a POSIX `flock` over the
entire claim/workspace transaction and atomic state replacement. Linked
worktrees share it; manually edited Markdown status rows would not be race-safe.
Startup parses eligibility, output paths, and card text from the immutable
approved commit inside that transaction, not a pre-lock working-tree snapshot.
`list` reads the authoritative local snapshot and shows owners/workspaces.
No tracked mutable assignment ledger is maintained; sanitize handoffs/reviews
into `docs/work/results/` instead. Keep registry and claims local, not credentials.
If the registry is missing/corrupt after work began, stop dispatch and reconcile
all retained worktrees/branches with the coordinator before reconstructing it.
Missing metadata does not prove nobody owns the work; registry backup/recovery
has not been demonstrated by the fixture tests.

This version is for **one Linux/POSIX host and one local clone with linked
worktrees**. It fails closed without `flock`. Independent clones/machines,
network-filesystem lock semantics, hostile workers, infrastructure/device
leases, and effective tool isolation are **not solved**. Do not dispatch the
same chains on another clone concurrently; use one coordinator/dispatch host
until a shared remote claim service is explicitly designed and tested.

Worktrees, owner strings, coordinator command names, and model labels are not
security boundaries. A worker with broad shell access could bypass all of them.
F05 must verify the real tool policy; a trusted dispatcher may create the
workspace while the research model itself remains unable to mutate Git or use
shell/MCP. This helper neither installs OpenCode profiles nor routes models.
See the [AI workflow](ai-workflow.md#opencode-support-versus-a-safety-boundary).

## Verification

Safe, offline commands from the repository root:

```bash
python tools/taskchain.py check
python -B -m unittest discover -s tests -v
```

Tests use throwaway local Git fixtures, no remotes, devices, infrastructure,
dependency installation, backup scripts, or actual model/permission pilot.
Fixtures live under `/tmp/opencode/debra-taskchain-tests-*`; each run keeps the
newest few and prunes older ones ([tmpfixtures.py](../tools/tmpfixtures.py)),
because unlimited retention exhausts the tmpfs inode table and then fails
unrelated work with "No space left on device". No branch, worktree or failed
result is deleted from the run you just made.
