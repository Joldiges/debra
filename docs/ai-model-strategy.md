# AI model and provider strategy

Recorded from James's model/spending discussion and request to commit it,
2026-11-14. This is Debra's **selection policy**, not automatic routing or a
change to live OpenCode settings. The [AI workflow](ai-workflow.md) controls
authority, permissions, review, and integration.

## Role selections

These are coordinator-selected starting points reflecting James's preferences,
not universal model rankings. A model being available does not qualify it for
a role; retain task evidence and change selections deliberately.

| Role | Starting selection | Conditions |
| --- | --- | --- |
| Coordinator, architecture, integration | Recorded selection `openai/gpt-6.1-sol#xhigh`; the host may run a cheaper session instead (see [Cost revision](#cost-revision-2026-11-16)) | Reserve enough allowance for supervision, decisions, and integration. James identifies Sol `xhigh` as the first tier he sufficiently trusts for this role; this is his judgment, not a benchmark result. |
| Separate acceptance reviewer, ordinary slice | A fresh `openai/gpt-6-luna#flex-high` session | Review the exact frozen candidate and original sources. Separate context and a different model family from the DeepSeek coordinator are what make it independent; it is not an enforced merge gate, and the coordinator still reproduces checks. |
| Separate acceptance reviewer, contract or new interface | A fresh `openai/gpt-6.1-terra#flex-high` session | For the question "is this the right contract", not "did these findings close". Also the escalation when Luna's report is vague or misses a reproduced defect. |
| Separate acceptance reviewer, trust boundary | A fresh `openai/gpt-6.1-sol#flex-high` session | Credentials, identity, the restore/rollback boundary, recovery. Reserved because a miss there is silent and remote. |
| Inexpensive bounded research/documentation worker | `openrouter/deepseek/deepseek-v4.1-flash-1017#high` | Preferred inexpensive worker, subject to the F01/F05 gates and verified task permissions. One documentation pilot is evidence for that narrow task, not general coding or architecture qualification. |
| Allowance-funded alternative worker | `openai/gpt-6-luna#high` | Luna is acceptable for bounded work; prefer useful included allowance over paid calls when coordinator capacity permits. Its role still needs task-specific evidence and the same permission/review gates. |
| Copilot-funded work, pending discovery | No exact model selected yet | Use suitable included models strategically after account connection, entitlement, current model IDs, allowance, and any premium multipliers are established. Do not assume a model available elsewhere is included here. |

For non-urgent **paid GPT** work when included allowance is unavailable or best
reserved, prefer the corresponding existing OpenRouter Flex variant:
`openrouter/openai/gpt-6-luna#flex-high`,
`openrouter/openai/gpt-6.1-terra#flex-xhigh` for an explicitly assigned evaluation,
or `openrouter/openai/gpt-6.1-sol#flex-xhigh` for capable work. These are fallback
choices, not permission to start more work or change a running session silently.

## Cost revision, 2026-11-16

James reported that recent spending was too high and asked for Terra in place of
Sol some of the time, and for `high` rather than `xhigh`. The measured picture
agrees with the request but says the round count matters more than the tier.

The local session database (its provider-reported `cost` column; 294 sessions)
showed about **$50.17 total**, of which **$24.98 started on 2026-11-15** and
**$10.54 on 2026-11-16**. On 2026-11-16 that was `gpt-6.1-sol` **$7.93 across 14
sessions** and DeepSeek Flash **$2.49 across 24**. No single review exceeded
$1.09; the spend is many rounds of the same two slices — `code-r8` through
`code-r12` and `setup-r7` through `setup-r9` on one day — not one expensive run.
DeepSeek's own total ($21.49) is far above what the listed per-token prices imply
for its token counts, so either that listing is stale or reasoning tokens are
billed differently; "cheap model" does not mean "cheap session".

The session that wrote this ran `deepseek/deepseek-v4.1-flash-1017#high` per the
host, not the Sol coordinator selection recorded above. That is the practical
reason the independence rule below is about **families**, not tiers: a DeepSeek
reviewer shares the author's blind spots.

The policy from here is a **ladder by consequence**, not "start cheap and escalate
if it finds something". A cheap reviewer that finds nothing is weak evidence, and
a cheap reviewer that finds something is not a reason to pay for a second opinion
— the coordinator can reproduce it. What the tier buys is independence and
judgement, and neither is monotonic in price.

| Tier | Who | Used for | Not used for |
| --- | --- | --- | --- |
| 0 | No model: tests, mutation kills, blob freeze, docs/schema checks | Every change. The coordinator runs these. | — |
| 1 | `opencode/deepseek-v4.1-flash-free` ($0) | Mechanical questions about a diff: does each pin fail under its reverted guard; does the README claim something the diff does not do | Anything that gates a trust boundary; anything whose miss would be silent |
| 2 | `openrouter/openai/gpt-6-luna#flex-high` ($0.10 / $0.50) | Re-review of named findings; the first review of an ordinary slice | Credentials, identity, recovery, rollback |
| 3 | `openrouter/openai/gpt-6.1-terra#flex-high` ($1 / $5) | Contract-level review; a new interface; a trust-boundary **re-review** whose counterexamples the coordinator has reproduced; when Luna's report is vague or misses a defect the coordinator reproduced | Routine re-reviews; a trust boundary's first review |
| 4 | `openrouter/openai/gpt-6.1-sol#flex-high` ($2 / $10) | The **first** review of a trust-boundary slice (credentials, identity, restore/rollback, recovery); a design change on one; or a Terra review that missed a reproduced defect | Routine work; a re-review of cases already reproduced |

Prices are the model catalog's standard rates per million input/output tokens,
checked 2026-11-16; Flex is about half. The `-pro` variants cost double and are
not selected.

1. **Independence is cross-family.** The coordinator and the repair workers run
   DeepSeek V4.1 Flash, so a DeepSeek reviewer is **not independent** for their
   repairs — independence starts at Luna. A DeepSeek review is acceptable for an
   OpenAI-authored change, or for a mechanical question with an objective check
   (a mutation that must die).
2. **Sometimes no model review.** A prose-only change, a test-only pin whose
   mutation kill the coordinator has demonstrated, or a repair that is exactly
   the named findings with no new interface needs Tier 0 only. Record "no model
   review" and why, rather than implying one certified it.
3. **At most two model reviews per slice per day.** After the second, either
   accept with the open findings recorded or re-scope with James.
4. **Budget the prompt, not only the model.** Name the diff, the findings, the
   commands and a time limit; forbid re-deriving the design and re-reading the
   whole repository. A cheap model given a 40k-token prompt and an unbounded
   command list costs more than an expensive model given a tight one.
5. **Record the tier and its outcome** in the verdict row, including "no model
   review".

The first Luna re-review is an **experiment**, not an assumption: if it misses a
defect the coordinator can reproduce, that is evidence to move the ordinary floor
to Terra, and it gets recorded.

### Applied evidence, 2026-11-16 web-auth slice

Recorded because the practice did not match the table above. A coordinator
session fixing the device page's key handling ran **three** reviews, all
`openrouter/deepseek/deepseek-v4.1-flash-1017#high`, at $0.032 + $0.035 + $0.056.
That is Tier 1, the same model and family as the author, so by rule 1 none of
them was an independent acceptance review — the slice has had **zero**
independent reviews, not three expensive ones. Two causes are worth keeping
visible:

1. `.opencode/agents/debra-review.md` sets no `model`, so every review silently
   inherits the parent session's model. The coordinator must pass `model`
   explicitly and say which tier it is buying; otherwise "independent review"
   quietly becomes self-review.
2. Round count, not tier, drove the cost. The coordinator session itself was
   $0.702 against $0.123 of review. Every extra round costs a full re-read and
   repair cycle on the author's side, so batching findings into one round is the
   larger lever.

The reviewer still caught a real regression the coordinator had introduced
(`urlsplit` on a malformed request target). Cheap and non-independent is not
worthless; it is just not an acceptance review, and the record must say so.

### Open question: is Sol the right *first* review?

James's 2026-11-16 position, recorded rather than resolved because it contests
the table above: in rapid development he would rather have **tests** carry the
validation, keep cheap models for ordinary changes, and reserve expensive models
for work genuinely complex enough to justify them; documenting or tweaking
something should not buy a big review. He is not convinced Sol should be a
*first* review, on the grounds that a cheap model may surface the items a
Sol review would have to be paid to find anyway.

That is in direct tension with the ladder's "no start-cheap-and-escalate" rule.
It is unresolved: either the rule stays (independence is the product, so buy it
first) or the ladder becomes cheap-first with a stated escalation trigger. Until
someone decides, this section records the disagreement instead of silently
picking a side. Note that this paragraph is a user statement, not a reviewed
change to the tiers above.

This changes no provider default, account billing, or host configuration, and it
does not authorize new work. It is a selection policy for work already approved.

Other model recommendations are welcome. Compare a small representative task,
including source accuracy, defects, repair burden, review cost, latency, and
permission compliance. A different model family can add review diversity, but
must demonstrate adequate capability; cheap review is not an acceptance goal.
There is no automatic model-upgrade ladder or routing: the tiers above are a
selection the coordinator applies deliberately and records, and a cheaper tier is
never used to make a hard change look reviewed.

## Allowances first, without waste

1. Prefer deterministic scripts/checks for mechanical work. Do not spend tokens
   merely to consume an allowance.
2. Use the OpenAI five-hour and weekly allowances on useful authorized work
   before they reset, while preserving capable-coordinator/reviewer capacity.
   Choose available Copilot allowance similarly once verified. There is no
   fixed OpenAI-versus-Copilot ordering independent of suitability and expiry.
3. Minimize direct OpenRouter spending. DeepSeek remains the preferred paid
   low-cost worker; an included Luna task can be the better marginal-cost choice.
   Use Flex rather than standard paid GPT when slower execution is acceptable.
4. An unavailable provider, exhausted allowance, or Flex capacity error is a
   reason to reassess, defer, or make a recorded bounded fallback choice—not to
   silently increase spend, lower review quality, or broaden permissions.
5. Do not replenish credit, enable renewal/overage billing, buy another plan,
   or make another paid commitment without James's approval.

**Unknown as of 2026-11-14:** actual remaining OpenAI/Copilot allowances and
their exact reset timestamps/time zones. James's approximate OpenAI weekly
reset report (“early Saturday”) is not a verified schedule. Empty OpenAI cost
fields in the local catalog do not mean unlimited usage. No automatic quota
monitor or enforced per-run spending cap is established; the queued research
runner (`tools/scheduled_runner.py`, see the [unattended runner](guides/scheduled-runner.md))
exists, but it reports to a git-ignored queue and is not a quota meter either.
Do not treat an unrelated OpenCode usage-limits endpoint as an account quota
meter without verifying what it measures.

## Flex: cheaper capacity, not a guaranteed bill

`upstream-documented`, checked 2026-11-14:
[OpenRouter service tiers](https://openrouter.ai/docs/guides/features/service-tiers)
describe Flex as lower-priority, lower-price capacity, not the asynchronous
Batch API. Allow for slower execution/capacity failures; do not promise a
completion time.

Public endpoint listings checked on that date showed an `openai/flex` endpoint
for all three models. Listed USD per **million uncached input / output tokens**:

| OpenRouter model | Below 272,000 prompt tokens | Listed tier from 272,000 prompt tokens | Direct endpoint source |
| --- | --- | --- | --- |
| `openai/gpt-6-luna` | $0.05 / $0.25 | $0.10 / $0.375 | [Luna endpoints](https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints) |
| `openai/gpt-6.1-terra` | $0.50 / $2.50 | $1.00 / $3.75 | [Terra endpoints](https://openrouter.ai/api/v1/models/openai/gpt-6.1-terra/endpoints) |
| `openai/gpt-6.1-sol` | $1.00 / $5.00 | $2.00 / $7.50 | [Sol endpoints](https://openrouter.ai/api/v1/models/openai/gpt-6.1-sol/endpoints) |

These are dated endpoint listings, not an inference test or future quote.
Recheck prices, context thresholds, cache-read/write charges, reasoning/output
usage, optional tool charges, and applicable fees. Model-catalog prices alone
do not establish a request's actual tier or charge; cache reuse is not assured.

OpenRouter documents price-bounded fallback **when Flex endpoints exist**:
fallback input and output rates must both be no higher than a Flex endpoint's.
If the model has **no Flex endpoint**, `service_tier: "flex"` can instead route
normally at standard rates. A selectable variant name is therefore insufficient.
Verify the effective request's tier/provider restrictions; when relying on
Flex-only pricing, use a verified tier-specific endpoint restriction such as
`provider.only: ["openai/flex"]`, rather than a tier label alone. Record the
response's actual tier and billing evidence when available.

Earlier local request/mock and session-cost evidence also warns that auxiliary
requests such as session titles may use a different tier, and long-context
cache writes can dominate a small output bill. See the
[evidence register below](#evidence-and-current-gaps). This documentation changes
no provider defaults, fallback settings, account billing, or host configuration.

## Bounded execution and reporting

- Follow the workflow's **one submission plus one bounded repair** default.
  Then the coordinator takes over, re-scopes, or stops. This is a work-attempt
  budget, not a claim that the client makes only two billable HTTP requests.
- Record the actual provider/model/variant for worker and reviewer, candidate
  identity, verification, and any deliberate model/provider fallback. Record
  `unknown` where the host does not expose a value.
- At milestones, report useful results and total available worker, repair,
  review, and coordinator costs separately. State exclusions, token/cache
  uncertainty, and allowance usage/reset information when known. A missing
  price or subscription dollar charge is not evidence of zero resource use.
- Keep parallel tasks bounded by review capacity and shared dependencies.
  Do not run retry loops or launch more workers merely because credit exists.
- Evaluate **accepted-result cost**, not worker token price alone. The
  [DeepSeek pilot](notes/2026-11-14-deepseek-documentation-pilot.md#cost-and-evidence-retention)
  recorded about $0.02209 for the worker and $0.28431 for two Gemini reviews,
  excluding coordinator/setup/integration. It does not establish total savings.

## Evidence and current gaps

| Kind / date | Source and finding | Limit / next action |
| --- | --- | --- |
| User requirements, 2026-11-14 | James's conversation: preserve the discussed model strategy in Git; prefer useful subscription/Copilot allowance, inexpensive DeepSeek, sufficiently trusted Sol `xhigh`, and slower paid GPT Flex where suitable. Luna acceptable; Terra worth evaluating. | Preferences authorize this documentation, not new account commitments or live operations. |
| Local discovery, 2026-11-14 | OpenCode model tool returned the named OpenAI models/variants, DeepSeek `high`, and the listed OpenRouter Flex variants. Copilot provider lookup returned no models in this project. | Availability is not an execution/quality test. Copilot entitlement/connection remains unresolved; an empty inventory does not prove no subscription exists. |
| Upstream documentation, checked 2026-11-14 | [OpenCode providers: ChatGPT](https://opencode.ai/docs/providers#chatgpt) describes subscription-plan usage; [Copilot](https://opencode.ai/docs/providers#copilot) describes device OAuth, required Chat access, and account-specific model discovery. | James can use `/connect` → GitHub Copilot and then `/models`; no connection or sign-in is performed by this change. Check account quotas and premium billing before selecting work. |
| Prior local evidence, 2026-11-08 | Foundation notes `memory/notes/fedora/20261108T072448Z-8fdf949c342a.md` and `20261108T073939Z-4dc41d1efcc5.md`: Flex request mock and later selected-variant/session-cost evidence, with cache/title caveats. | Historical host-specific observations, not reproduced here or independent provider billing confirmation. Public tier/price sources above stand independently of those private foundation notes. |
| Narrow pilot, 2026-11-14 | [DeepSeek pilot report](notes/2026-11-14-deepseek-documentation-pilot.md): useful documentation output after one repair, separate Gemini review, coordinator verification, and scoped denial evidence. | No broad model qualification or exhaustive alternate-tool isolation proof. The note's uncommitted-state statements describe its original handoff; its deliverables are now present in Git at `0e0d03b`. |
| Readiness, 2026-11-14 | [F01/F05](roadmap.md#foundation-and-coordination) and [closed-dispatch gate](task-chains.md#current-availability) remain authoritative. | This policy does not finish readiness, enable persistent worker profiles/routing, enforce reviews, or open production dispatch. Complete the separate evidence assessment before dispatch. |
