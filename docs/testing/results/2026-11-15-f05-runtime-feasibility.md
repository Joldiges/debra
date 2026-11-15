# F05: what would actually unblock the permission harness

**2026-11-15 UTC — static source trace and a local runtime probe, not an executed
permission test.** F05 remains partial and production editing dispatch remains
closed. This supplements the [source feasibility note](2026-11-15-f05-source-feasibility.md);
it does not replace it, and it authorizes no install or dispatch change.

Author: OpenCode session, `openrouter/deepseek/deepseek-v4.1-flash-1017`,
variant not exposed by the host. Repository baseline `ea40675` with an in-flight
setup change in the working tree, so this is not a candidate revision. Source
baseline remains the pinned tag commit `a6b15d33daf6ab7d35569f6d711fdb630b9f04e7`
(OpenCode v2.3.0), matching the earlier note.

## Why this was reopened

The earlier note recorded "neither `bun` nor `node` was found on this session's
`PATH`" and treated the source-test route as blocked on a runtime. `node` is now
present, so the question was worth asking again.

Observed on this host: `node v22.23.1`, `npm 10.9.8`, `opencode v2.3.0`,
`bwrap` present, **`bun` absent**, and no `deno`, `pnpm`, `yarn`, `corepack` or
`tsx`.

The answer is that the runtime was never the main obstacle. The obstacle is a
**dependency environment**: the real permission service statically reaches most
of the core package.

## Method and limits

Read-only. A blobless `--no-checkout` clone of the pinned tag was sparse-checked
out to six packages (`core`, `util`, `schema`, `plugin`, `ai`, `codemode`,
47 MB), and a small Python tracer followed static `import`/`export … from` and
dynamic `import()` specifiers, resolving `@opencode/<pkg>/<sub>` through the
documented `exports: {"./*": "./src/*.ts"}` map and the `#` specifiers through
each package's `imports` map with the **node** condition.

One local probe ran: a two-line TypeScript module executed by `node` to confirm
type stripping works without a flag.

**No upstream code was executed.** No dependency was installed. No upstream test
file was run. The clone is a reading aid, not a vendored dependency, and the
static trace is not a runtime observation: an import that resolves statically may
still fail at load, and one that looks lazy may still load earlier than the
source suggests.

## Finding 1 — `bun` is required by the tests, not by the core runtime

`packages/core/package.json` resolves six platform-sensitive specifiers by
condition. Every one has a `node` variant:

| Specifier | node target | consequence |
| --- | --- | --- |
| `#sqlite` | `src/database/sqlite.node.ts` → `@effect/sql-sqlite-node` | no `bun:sqlite` needed |
| `#pty` | `src/pty/pty.node.ts` | no `bun-pty` needed |
| `#fff` | `src/filesystem/fff.node.ts` | |
| `#photon-wasm` | `src/image/photon-wasm.node.ts` | |
| `#client-tls` | `src/effect/client-tls/client-tls.node.ts` | |
| `#v1-migration` | `v1-migration.noop.ts` | |

`sqlite.node.ts` also notes that foreign keys default on in `node:sqlite`, which
points at the Node built-in rather than a compiled `better-sqlite3`. The earlier
note's "upstream tests use Bun" is still true — `script/test.ts` spawns through
`Bun.spawn` and every test file imports `bun:test` — but that is a property of
the **test harness**, not of the code the harness would test. `node` cannot
resolve `bun:test`, so upstream's own test files cannot be reused under Node.
A Debra-written harness would have to use `node:test` instead.

Node also executes TypeScript directly. `node a.ts` on a module with an
interface, a type alias and a typed arrow function printed the expected result
with no flag and no warning on this version, so a `.ts` harness needs no
transpiler step.

## Finding 2 — the permission service is not a small unit

The trace is the decisive result. Importing `src/permission.ts` — the module
whose ordered policy evaluation F05 wants to test — statically reaches:

| Entry point | repo modules | source | external packages | files with bun/native markers |
| --- | --- | --- | --- | --- |
| `src/permission.ts` | **980** | 14.2 MB | **63** | 4 |
| `src/tool/runtime.ts` | 136 | 0.6 MB | 4 | 0 |

The 63 externals include `effect`, `zod`, `drizzle-orm`, `undici`, `jose`,
`jsonc-parser`, `htmlparser2`, `gray-matter`, `glob`, `which`, `immer`,
`@modelcontextprotocol/*`, `@ai-sdk/provider`, `@anthropic-ai/claude-agent-sdk`,
`@aws-sdk/credential-providers`, `aws4fetch`, `google-auth-library`,
`gitlab-ai-provider`, `@npmcli/arborist`, `@npmcli/config`, `pacote`,
`npm-package-arg`, and `@parcel/watcher`.

So a "real registry + native leaf + real permission service, seeded only with
synthetic state" composition is not a small file that can be pointed at six
copied sources. Loading the permission service loads the plugin registry, the
provider SDKs and the package-manager code with it. That is consistent with why
upstream's own `permission.test.ts` works: it runs inside the full workspace.

## Finding 3 — the native modules are mostly lazy; the npm tree is not

Three of the four marker hits are harmless at import time, and one is not:

- `src/pty/pty.node.ts` imports `@lydell/node-pty` **as a type** and loads it
  through `createRequire` at call time.
- `src/filesystem/watcher-binding.ts` resolves the platform package through
  `createRequire` inside the function.
- `src/shell/parse.ts` matched only because `bun:` appears as a shell-keyword
  table entry. Not a dependency.
- `src/filesystem/watcher.ts` **does** statically import
  `@parcel/watcher/wrapper.js`, so that package and its Linux prebuild are a
  real install requirement, not an optional one.

`bun.lock` at the pin lists **2206 package entries** in 596 KB. That is the scale
of the environment, whichever package manager installs it.

## Finding 4 — the light seam is real but is not the thing under test

`src/tool/runtime.ts` is 136 modules, 0.6 MB, four externals (`effect`, `zod`,
`@standard-schema/spec`) and no bun or native markers. It is the one place in
this tree where a model-free harness could plausibly load under plain Node.

It sits at the wrong seam. It shows input decoding and executor invocation; it
does not contain the configured-deny/saved-rule/evaluation-hook ordering that
F05 exists to establish. A harness built only there would reproduce the
substitution the earlier note warned against: a passing test about a neighbouring
boundary, presented as evidence about the permission service.

## Options, and what each needs

| Route | What it needs | What it would prove | Honest label |
| --- | --- | --- | --- |
| **A. Full workspace** | `bun` installed (user-local, no root), `bun install` against `bun.lock` (2206 entries, native prebuilds), a Debra-written `bun:test` file composing the real registry, leaf and permission service | The ordered policy outcome F05 actually asks about, against real code | The only faithful route |
| **B. Runtime-seam harness** | `npm install effect zod @standard-schema/spec` in a scratch dir; run under Node with `node:test` | Registry/executor ordering and input decoding | A partial first step, not F05 coverage |
| **C. Source-level only** | nothing further | Call-graph claims already recorded | Current state |

Two details that matter before anyone chooses:

- `npm` cannot honour `bun.lock`, so route B would **re-resolve** the pins
  rather than reproduce them. A result from re-resolved dependencies is weaker
  evidence than one from the lockfile, and should say so.
- Route A runs upstream code with network and filesystem reach. It needs the
  secret-free boundary that F05 also has to demonstrate, so the environment
  question and the isolation question have to be answered together rather than
  one after the other.

## Recommendation

Route A is the only one that produces the evidence F05 asks for. Route B is
worth doing only as an explicitly labelled ordering test, and only if the
cheaper first step is wanted. Neither is authorized here: installing `bun` is a
host change, and `bun install` fetches and builds code. That needs James's
explicit scope, a named install location, and a stated removal path.

The claim to retire is narrower than "no runtime": the missing piece is a
pinned dependency environment of roughly 2200 packages, and the two questions
that remain open are whether that environment can be built secret-free and
whether its construction is worth the cost for one gate.

## What remains unverified

- Whether the 63 externals install cleanly at these pins, and whether
  `@parcel/watcher`'s prebuild is available for this platform.
- Whether `@effect/sql-sqlite-node` uses `node:sqlite` or a compiled binding.
  The source comment implies the former; this was not executed.
- Whether the 980-module graph loads under Node at all. The trace is static, and
  a single non-node-conditional `Bun.` reference at load time would break it.
- Everything about the actual permission outcome. Nothing here adds executed
  F05 coverage.

## Verification and retained evidence

Local probe and trace commands, from the reading copy:

```sh
node a.ts                      # type stripping, no flag: printed the expected result
python3 trace.py               # the table in finding 2
git rev-parse HEAD             # a6b15d33daf6ab7d35569f6d711fdb630b9f04e7 in the clone
```

Ignored, owner-only records: `.local/pilots/f05-runtime-20261115/` holds
`manifest.json` (14 fetched source files with byte counts and SHA256),
`trace.py`, and the fetched sources. The blobless clone and its sparse checkout
remain under `/tmp/opencode/opencode-tree/` and are disposable. No tests,
tooling, permission rules, device settings or dispatch registry were changed.
