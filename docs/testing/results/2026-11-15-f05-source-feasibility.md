# F05: deterministic test feasibility at OpenCode 2.3.0

**2026-11-15 UTC — source inspection, not an executed permission test.** A
reusable upstream tool-test entrypoint exists. A safe Debra harness has **not**
been implemented or run; F05 remains partial and production editing dispatch
remains closed. This supplements, rather than replaces, the
[earlier execution evidence](2026-11-14-ai-readiness.md).

Author: OpenCode coordinator, `openrouter/openai/gpt-6.1-sol#flex-xhigh`
(host-reported selection, not proof of underlying snapshot or Flex billing).
Research baseline: Debra `46c02abccc46aac549038975e936cf491b1ff0c1`.

## Version and method

The local CLI reported `opencode v2.3.0`; `/api/info` reported server version
`2.3.0`. The official [v2.3.0 tag reference](https://api.github.com/repos/anomalyco/opencode/git/ref/tags/v2.3.0)
resolved to commit **`a6b15d33daf6ab7d35569f6d711fdb630b9f04e7`**. All source
links below use that commit. This is a version-matched source investigation,
**not** a reproduced-build or installed-binary/source identity verification.

Thirty-one named source/test/metadata files (387,695 bytes) were retrieved as
inert text into ignored owner-only local storage. No upstream TypeScript, test,
plugin, SDK host, mock server or experimental backend was executed. No source
dependencies were installed. The upstream repository was not cloned or vendored
into Debra. Local manifests retain URLs, byte counts and SHA256 hashes.

## Reusable route and important limits

The upstream [`registerToolPlugin` and `executeTool` helpers](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/test/lib/tool.ts#L49-L98)
register a core tool against the real tool registry and execute a registry
snapshot directly. This is a promising **model-free source-test route**: it
does not require paying a model to select a prohibited tool. It is not a public
live-server invocation endpoint or an already verified Debra harness.

Two existing helpers must not be mistaken for the desired boundary:

- [`permissionLayer`](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/test/lib/permission.ts#L4-L5)
  mocks `Permission.Service`. The [patch tests](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/test/tool-patch.test.ts#L64-L83)
  use a custom rejection callback and [replace the service](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/test/tool-patch.test.ts#L115-L140).
  Those tests are useful patterns for tool behavior, not proof that Debra's real
  ordered policy, session rules and saved approvals enforce the same result.
  The separate [permission tests](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/test/permission.test.ts#L23-L79)
  show a real-service setup to investigate for composition, not a completed composition.
- [`recordingEnvironmentLayer`](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/test/fixture/environment.ts#L20-L37)
  records commands **and then really spawns them**. Likewise,
  `transformEnvironmentFiles` wraps a host filesystem. Neither is a harmless
  in-memory replacement merely because it is named a test fixture.

## Source-level call graph and candidate interception points

These are inspected implementation statements, **not runtime observations**.
Any downstream fake must be calibrated by an allowed positive control, preserve
the real permission implementation and fail closed on an unimplemented route.

| Route | Observed ordering at the source pin | Consequence for a later harness |
| --- | --- | --- |
| Registry / hooks | [`Tool.snapshot`](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/tool.ts#L254-L324) filters wholly disabled tools; the before hook precedes the leaf executor. [`runtime.execute`](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/tool/runtime.ts#L31-L47) invokes that executor after input decoding. | Record the advertised snapshot separately from an executed denial. A before-hook count is not a post-permission backend count. Do not replace the leaf with a mock that accidentally removes its permission checks. |
| Real permission service | [`configured` / `evaluateInput`](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/permission.ts#L169-L209) merge agent and session rules; a configured deny returns before saved-rule lookup and the evaluation hook. [`assert`](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/permission.ts#L256-L287) turns denial into failure. | Observe calls around the real service, not only its evaluation hook. Zero evaluation-hook events cannot establish zero attempts. |
| Patch / move | The [patch executor](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/tool/plugin/patch.ts#L94-L250) prepares all changes, includes move source and destination resources, asserts `edit`, then mutates files. Preparation can read original bytes before that edit assertion. | Keep real parsing, path resolution, locks and permission assertion; replace downstream filesystem effects. Test mixed allowed/denied targets in both orders. Permission-denial-before-write is not general rollback: runtime I/O failures can leave completed changes. Do not use confidential files as rejected-patch inputs. |
| Paths / symlinks | [`FileAccess.resolve`](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/file-access.ts#L67-L118) uses lexical path resolution and containment. An upstream [patch test explicitly follows an internal symlink to an external file](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/test/tool-patch.test.ts#L1059-L1090) without external-directory approval. | Do not assume the external-directory permission is a realpath/symlink sandbox. Required target-containment tests remain unexecuted; a hard filesystem boundary is separate. This source behavior also cautions against treating current mutable docs as release-specific guarantees. |
| grep / glob | [grep](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/tool/plugin/grep.ts#L85-L99) and [glob](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/tool/plugin/glob.ts#L67-L81) authorize an external root, then assert their own action against the **pattern**, not each file's `read` rule. | A path allowlist for `read` does not itself establish search-root containment. Synthetic canaries and independent backend observations are needed. Keep these tools denied for current bounded research unless explicitly needed. |
| Shell | The [tool's prepare callback](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/tool/plugin/shell.ts#L292-L319) scans commands, authorizes external directories and asserts shell resources. [`Shell.create`](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/shell.ts#L880-L965) calls that callback before either daemon-backed execution or environment spawning. | Replacing `Shell.create` without calling its callback would bypass the checks being tested. Intercept **both** the persistent-daemon route and the environment spawner, and account for initialization effects before claiming no real process can run. A spawner counter alone misses the daemon route. |
| Code Mode | The registry [removes Code Mode when wholly denied](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/tool.ts#L263-L280); when present its [nested execution](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/codemode/tool.ts#L123-L145) calls the supplied registry executor. Its [runtime also registers an independent HTTP `fetch` extension](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/codemode/tool.ts#L275-L285); nested-tool interception does not cover it. | Distinguish unavailable Code Mode from a nested tool's executed denial. Initially use only the [fetch-free `check` path](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/codemode/tool.ts#L288-L309), disclosing its narrower coverage. Full-runtime fetch permissions, redirects and HTTP backend implementation remain unaudited/unexecuted here; keep that route out of execution until separately reviewed downstream interception and positive/negative controls exist. Upstream [fetch tests](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/test/tool-execute.test.ts#L269-L382) mock permissions and start real local HTTP servers, not a ready safe backend. No production rule is loosened here. |
| MCP tools / resources | The [MCP adapter](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/tool/mcp.ts#L61-L76) asserts the normalized action before `mcp.callTool`; [resource tools](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/tool/plugin/mcp-resource.ts#L32-L71) assert server/URI resources before catalog/read calls. | Supply a fake MCP service/catalog, with no real transport or household server. Discovery/initialization calls need separate counters from tool execution/resource reads. |
| Delegation | The [subagent executor](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/src/tool/plugin/subagent.ts#L129-L223) checks depth/agent, asserts `subagent`, then can switch/create/prompt a child and start its job. | Fake session mutation, child prompting and subagent-job start; calibrate new-child **and continuation** cases. Do not launch actual children as the prohibited-operation test. This is distinct from the coordinator's authorized research delegation. |

## Execution blocker and next bounded assignment

Neither `bun` nor `node` was found on this session's `PATH`; that is not an
inventory of every runtime on the machine. Upstream [core package scripts](https://github.com/anomalyco/opencode/blob/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7/packages/core/package.json#L18-L27)
use Bun, and its tests import `bun:test` plus workspace/native dependencies. A
source-test dependency environment has not been prepared. `bwrap` is present,
but its presence is not evidence that a suitable secret-free boundary exists.
No host installation or improvised shared-server plugin was attempted.

The next useful unit is a reviewed **source-test composition**, not another
paid prompt: real registry + native leaf + real permission service, seeded only
with synthetic session/agent/saved-rule state, and in-memory downstream effects.
Start with allowed versus mixed-target-denied patch/move, then add the other
routes only after their backend seams and initialization are accounted for.
Runtime/dependency provisioning and a demonstrated secret/config/network-isolated
environment need separately agreed scope before execution. Do not run the
upstream suite wholesale or mistake an SDK host for isolation.

The earlier unexplained empty `audit.jsonl` remains preserved and unattributed.
Neither source inspection nor a future clean run explains its historical origin.
Full pre/post fixture inventories and independent audit storage remain required.
Claim-specific production-policy review and an explicit current-base activation
decision are still separate from any successful harness experiment.

## Verification and retained evidence

Safe repository checks at the research baseline: `python tools/taskchain.py check`
passed (19 chains, 63 packets); `python -B -m unittest discover -s tests -v`
passed all 15 tests. These exercise the dispatcher, **not** the inspected OpenCode
code or device recovery. Integration checks for this report are recorded by the
coordinator separately; passing them does not add executed F05 coverage.

Ignored, owner-only records: `.local/pilots/f05-source-review-20261115/`
contains the two source manifests and inert files; the earlier
`.local/pilots/f05-interception-plan-20261115/plan.md` remains an unexecuted plan.
No tests, tooling, permission rules, device settings or dispatch registry were
changed by this investigation.
