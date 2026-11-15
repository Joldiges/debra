# F05: the real permission service, run against the real registry

**2026-11-15 UTC — executed, offline, model-free, and calibrated.** A Debra-owned
harness now composes the real tool registry with the real permission service and
shows that a configured deny stops a tool before its effect runs. This is the
first executed F05 evidence. It is **not** acceptance: the leaf under test is a
synthetic probe rather than the real patch executor, the claim-specific role
policy is still unvalidated, and production dispatch stays closed.

Author: OpenCode session, `openrouter/deepseek/deepseek-v4.1-flash-1017`,
variant not exposed by the host. Upstream baseline: OpenCode v2.3.0, tag commit
`a6b15d33daf6ab7d35569f6d711fdb630b9f04e7`. Debra baseline `600fc37`.

## Why this was run

The [runtime note](2026-11-15-f05-runtime-feasibility.md) concluded that the
blocker was a pinned dependency environment rather than a missing runtime, and
named route A — a full workspace install — as the only faithful option. James
authorized the install, so it was built and tested.

## What was installed, and how it is removed

| Item | Value |
| --- | --- |
| Bun | v1.4.4, `bun-linux-x64.zip`, SHA256 `bf8ccbfb…95c` verified after download |
| Location | `.local/f05-env/` inside this checkout, owner-only, git-ignored |
| Upstream | shallow clone of tag `v2.3.0` at `a6b15d33…`, 252 MB |
| Install | `bun install --frozen-lockfile --ignore-scripts` — 1595 packages, 20.9 s |
| Lifecycle scripts | **not run.** `bun pm untrusted` lists six packages with scripts that stayed blocked |
| Total size | 3.3 GB |

Removal is `rm -rf .local/f05-env`. Nothing was installed outside that directory,
no shell profile was edited, `bun` is not on `PATH`, and no system package was
touched.

## What was executed

Three runs, all from `packages/core`:

1. **Calibration against upstream's own permission tests** —
   `bun test test/permission.test.ts`: **122 pass, 0 fail, 603 expect() calls,
   1.71 s.** This is the positive control that the environment is real rather
   than a stub.
2. **The Debra harness** — `bun test test/debra-f05-harness.test.ts`:
   **5 pass, 0 fail, 11 expect() calls, 0.60 s.**
3. **The same harness inside a `bwrap` jail** — 5 pass, no network.

The harness builds `Tool.node`, `PluginHooks.node`, `Permission.node`,
`Agent.node`, `SessionStore.node`, `PermissionSaved.node`, `Bus.node` and an
in-memory `Database`, replacing only `Location` with a synthetic `/project`.
There is **no mock permission layer**. The leaf is a probe tool whose only effect
is a push onto an array, so "ran" and "did not run" are observable without
touching a real file, and the array is the canary.

| Case | Result |
| --- | --- |
| Rule allows the action | tool runs, effect recorded |
| Rule denies the action | tool returns an error, **effect never happened** |
| Mixed batch: one allowed target, one denied | allowed runs, denied does not; the allow does not rescue it |
| No rule, nobody answers | request held, tool not run, one pending request listed |
| `snapshot()` with a wholly denied tool | tool absent from the advertised registry |

## The calibration that matters

A passing harness proves nothing on its own, so two mutations were applied to a
scratch copy and both were caught:

| Mutation | Result | What it shows |
| --- | --- | --- |
| Remove `permission.assert` from the probe | **3 of 5 fail** | the deny result comes from the assertion, not from the test's shape |
| Replace the real service with `permissionLayer()` — the mock upstream's tool tests use | **3 of 5 fail** | the harness genuinely distinguishes the real service from the mock |

The second is the substantive finding. Upstream's `test/tool-patch.test.ts` runs
the real patch executor against `Layer.mock(Permission.Service)`, so it cannot
show that a deny stops a write. That mock is exactly what hides the behaviour
F05 is about, and a harness built on it would have produced confident, wrong
evidence.

## The isolation boundary, and a correction

`testEffect` in `test/lib/effect.ts` provides a `refuseNetwork` fetch that fails
a test which reaches the network. **It does not cover a raw global `fetch`.** A
mutation adding `fetch("https://example.com/canary")` to the probe still passed
all five tests, because the refusal is attached to Effect's `HttpClient` service
rather than to the process. Anyone reading that helper as a network boundary
should not.

The boundary used here is `bwrap` instead, and it was demonstrated in both
directions:

```sh
bwrap --unshare-net --die-with-parent \
  --ro-bind /usr /usr --symlink usr/bin /bin --symlink usr/sbin /sbin \
  --symlink usr/lib /lib --symlink usr/lib64 /lib64 \
  --ro-bind /etc/ssl /etc/ssl --ro-bind /etc/passwd /etc/passwd \
  --ro-bind /etc/group /etc/group --ro-bind /etc/nsswitch.conf /etc/nsswitch.conf \
  --ro-bind /etc/resolv.conf /etc/resolv.conf --ro-bind /etc/hosts /etc/hosts \
  --ro-bind /etc/localtime /etc/localtime \
  --dev /dev --proc /proc --tmpfs /tmp \
  --bind .local/f05-env .local/f05-env --chdir <packages/core> \
  --setenv HOME /tmp .local/f05-env/bun-linux-x64/bun test test/debra-f05-harness.test.ts
```

- The harness passes inside the jail.
- The same `fetch` mutation **fails** inside the jail and passes outside it, so
  the network namespace is doing the work rather than a cooperative helper.
- Inside the jail, `~/.ssh`, the memory repository and `/var/lib/debra` are
  absent; `curl https://example.com` is blocked. `/home/james` appears as an
  empty mount-point directory because the bind target lives beneath it — the
  directory exists, its contents do not.
- `/etc` is not bound wholesale: only `ssl`, `passwd`, `group`, `nsswitch.conf`,
  `resolv.conf`, `hosts` and `localtime` are visible, read-only.

## What this does not establish

- **The real patch/move leaf.** The probe is a Debra-written tool. The mixed
  target case that F05 asked for first — one allowed file and one denied file in
  a single patch — is not yet exercised against `PatchTool` with the real
  permission service.
- **The claim-specific role policy.** This tests the service's ordering, not
  whether a particular agent configuration denies the right tools to a
  lower-cost editing worker.
- **Any activation decision.** Dispatch remains closed, and no rule was loosened.
- **Device, radio, or household state.** Nothing outside `.local/f05-env/` and
  the scratch jail was touched.
- **Secret-free in the strong sense.** The jail hides the paths checked above;
  it was not audited for every possible leak, and the upstream tree itself is
  untrusted third-party code that was only executed through its own test files
  and this harness.

## Next bounded step

Swap the synthetic probe for the real `PatchTool` with the same real permission
graph, and reproduce the mixed-target case: a patch touching one allowed and one
denied file must write nothing. That is the smallest change that turns this from
an ordering demonstration into the tool-level evidence F05 wants, and it reuses
this environment unchanged.

## Verification and retained evidence

```sh
bun test test/permission.test.ts                    # 122 pass, 0 fail
bun test test/debra-f05-harness.test.ts             # 5 pass, 0 fail
bun test test/debra-f05-harness.test.ts             # under bwrap: 5 pass, 0 fail
```

Owner-only records in `.local/pilots/f05-harness-20261115/`: `harness.test.ts`,
`upstream-permission-mock.ts` (the mock the second mutation substituted), and
`manifest.json` with byte counts and SHA256 for both. The 3.3 GB environment is
disposable and reproducible from the lockfile.
