# Development workspace and upstream reuse

Agreed project direction, 2026-11-14. This guide defines local storage and
contribution practices; it does not authorize live device operations or
publication.

For coordinator/worker roles, task-sized worktrees, required handoffs, review,
and merge gates, follow the [AI workflow](ai-workflow.md). Worktrees separate
edits, not access to the host, credentials, network, or shared Git metadata.

## Keep private and generated material inside the project

Use the ignored **`.local/` at the checkout root**, rather than scattering
project-private records outside the project or placing them in shared memory.
Suggested subdirectories, created only as needed:

| Local path | Contents |
| --- | --- |
| `.local/access/` | Wi-Fi/environment files, device alias-to-address mappings, SSH fingerprints/access records, pairing credentials, and any project-specific private keys |
| `.local/logs/` | Raw diagnostic output and test captures awaiting sanitization |
| `.local/snapshots/` | Personal recovery manifests, exported backups, and credential-bearing snapshots |
| `.local/artifacts/` | Local images, build outputs, downloaded binaries, and provenance/hash records |
| `.local/upstream/` | Exploratory upstream checkouts and local patch experiments, not the sole record of selected build dependencies |

Keep small sanitized templates, source pins, build recipes, test reports, and
redistribution notices in tracked paths. A useful build recipe belongs in Git;
its private inputs and generated output do not. Raw microphone recordings
require specific consent and should not be collected by default.

The current checkout has an owner-only `.local/` directory. Git does not carry
ignored directories into a fresh clone or another worktree. For a fresh checkout
only, create it with:

```bash
umask 077
mkdir -m 700 .local
```

Create subdirectories with mode `0700` and private files with mode `0600`.
`umask 077` protects newly created files, but copied files can retain different
permissions: verify them before use. Do not recursively change an existing
directory without inspecting it, and never print credentials into agent/tool
output just to verify that a file exists.

`.gitignore` excludes `.local/` and common `.env` names. The `.env.example` and
`.env.*.example` exceptions are for **sanitized placeholders only**. Ignore rules
do not untrack existing files, prevent `git add -f`, encrypt data, restrict an
agent's access, or provide backups.

Before staging, inspect the explicit path list and staged diff; never use
force-add for this material. Before image/package/bundle creation, exclude
`.local/` explicitly and audit the resulting artifact. An archive of the whole
checkout can include ignored files even when Git does not. Never copy private
device state into a factory image.

Track sanitized recovery manifests/results in the test report, but keep private
recovery payloads in `.local/`. This does not make a same-disk copy an independent
backup. Agree a protected independent copy and demonstrate restoration before
risky device changes; no backup coverage or restore success is established by
creating this directory. Do not overwrite or prune recovery points.

Workers receive sanitized task context by default. If a device task needs
private access, the coordinator assigns the exact target, operations, and local
record path; do not commit/copy credentials into worktrees just to share them.
The parent checkout's `.local/` is not automatically present in a worktree.

## Reuse-first integration, forks, and upstream contributions

James expects substantial parts of Debra to reuse and combine existing
projects. This is a core design strategy, not merely permission for an
occasional shortcut. Debra's own work should concentrate on the missing
integration, approachable setup/maintenance, recovery, and evidence rather than
replacing good upstream implementations. Scoped forks and upstream
contributions are welcome when they solve relevant gaps. Compare configuration,
a small adapter, and a patch/fork before building a replacement. Respect the
[brief's non-Pi boundary](project-brief.md): comparing another complete product
does not commit Debra to maintaining its firmware.

PiCompose remains an information/reuse candidate, not the selected architecture.
Learning from its image stages, hardware notes, or integration choices does not
require adopting its whole stack. R04 must allow partial reuse, reference-only,
or rejection, with provenance and licensing for any actual reuse.

### Choosing how to bring an upstream project in

The following are project recommendations, not selected dependencies:

| Need | Preferred starting point |
| --- | --- |
| Install/use a released runtime or library | Pinned package or release, with verified provenance/hashes where applicable |
| Integrate an upstream source tree into builds, image stages, or ongoing patch work | A tracked, commit-pinned Git submodule |
| Build from source without a Git checkout | Pinned source archive with a verified hash and license/provenance record |
| Adapt a small portion of upstream code | Deliberate licensed copy with attribution, source revision, and a recorded local delta; compare against a submodule first |
| Investigate a candidate or document an alternative | Source links and, if useful, an ignored exploratory clone under `.local/upstream/` |

A submodule keeps the other repository's history separate while Debra records
the exact commit it uses; it is not a copy of that project's files into Debra's
history. Clone/setup needs an additional submodule initialization step (or a
recursive clone). These are `upstream-documented` behaviors in the
[Git submodules guide](https://git-scm.com/docs/gitsubmodules) and
[command reference](https://git-scm.com/docs/git-submodule), checked 2026-11-14.
Submodules are not a package manager: they do not install dependencies or prove
that a source tree builds/runs on a Pi.

For selected source dependencies, the proposed tracked boundary is
`upstream/<project>/`, with `.gitmodules` recording the fetch URL/path and
Debra's Git entry recording the pinned commit. This is intentionally different
from ignored `.local/upstream/` experiments. No submodules or `upstream/`
directory have been added yet; R04 selects candidates and F03 establishes the
actual layout.

For each selected submodule:

- Record purpose, canonical upstream URL, selected source/fork URL, exact
  commit, license, local changes, and update/test procedure. Prefer public
  HTTPS fetch URLs where public builders should not need an account or key;
  never put credentials or host-local paths in `.gitmodules`.
- Initialize the recorded commit in developer/build/CI instructions. Do not
  use `git submodule update --remote` as the normal build/install path: Git
  documents that it selects a remote-tracking revision instead of Debra's pin.
  Review nested submodules and fetch only the required source trees.
- Treat a pin change as a dependency update: review the upstream delta, test
  the affected integration/architectures, and retain the previous working pin.
  Keep the component manifest and submodule pointer consistent.
- Commit upstream-source changes in their own repository/patch series before
  recording a new parent pointer. Before sharing that pointer, ensure its
  commit is fetchable by the intended builders; uncommitted edits and local-only
  commits do not travel with the parent repository.
- Test the fresh-clone and worker/worktree setup, including missing sources
  and fork/URL changes. Do not overwrite dirty upstream worktrees or hide local
  modifications behind an apparently reproducible parent pin.
- Explicitly include required source trees/notices in source distributions and
  build inputs. Verify the packaged result rather than assuming an archive of
  Debra automatically contains submodule contents. A submodule does not remove
  third-party redistribution obligations.

### Scoped patches and contributions

For a reuse or patch proposal, record:

1. The capability gap, relevant roadmap packet, upstream project/license, and
   alternatives. Check maintained releases and existing issues/patches first.
2. The exact source URL, base commit/tag, toolchain/dependency versions, and
   applicable license/notice obligations. Preserve third-party provenance;
   do not label upstream code as Debra-authored or implicitly relicense it.
3. A bounded patch series separate from Debra-specific service/configuration
   integration. Keep exploratory checkouts under `.local/upstream/`; selected
   source dependencies use the explicit tracked mechanism above rather than
   silently vendoring a nested repository. Preserve reproducible patches/pins
   in the shared deliverables, not only in an ignored clone.
4. Exact verification, supported hardware/architecture scope, failures, and
   remaining uncertainty. A compile on Pi 5 is not an ARMv6 runtime test.
5. Who maintains the delta, how a pinned patched build is reproduced and
   rolled back, and when the patch can be dropped after an upstream release.
   Record patch hashes/base revisions; do not depend on an unpinned fork tip.

For public contributions, prepare a minimal reproducer and sanitized evidence
that follow the upstream project's contribution/license rules. Upstream fixes
should be independently understandable, not require Debra's private fleet or
credentials. Keep Debra's integration tests separate from the upstream test
record.

Local investigation and patch preparation fit bounded repository work.
Creating a remote fork, pushing, opening issues/PRs, publishing artifacts, or
assuming an ongoing maintenance commitment requires an explicit agreed scope;
permission to consider reuse is not blanket publication permission. Upstream
acceptance is never guaranteed.
