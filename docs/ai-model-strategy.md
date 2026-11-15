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
| Coordinator, architecture, integration | `openai/gpt-6.1-sol#xhigh` through the existing OpenAI subscription connection | Reserve enough allowance for supervision, decisions, and integration. James identifies Sol `xhigh` as the first tier he sufficiently trusts for this role; this is his judgment, not a benchmark result. |
| Separate capable acceptance reviewer | A fresh `openai/gpt-6.1-sol#xhigh` session | Review the exact frozen candidate and original sources. Separate context is useful but is not cross-model independence or an enforced merge gate. The coordinator still reproduces checks. |
| Inexpensive bounded research/documentation worker | `openrouter/deepseek/deepseek-v4.1-flash-1017#high` | Preferred inexpensive worker, subject to the F01/F05 gates and verified task permissions. One documentation pilot is evidence for that narrow task, not general coding or architecture qualification. |
| Allowance-funded alternative worker | `openai/gpt-6-luna#high` | Luna is acceptable for bounded work; prefer useful included allowance over paid calls when coordinator capacity permits. Its role still needs task-specific evidence and the same permission/review gates. |
| Intermediate candidate, not promoted | `openai/gpt-6.1-terra` | Evaluate on a bounded comparison before promotion; select and record a variant for the experiment. Do not silently replace Sol for coordination or acceptance. |
| Copilot-funded work, pending discovery | No exact model selected yet | Use suitable included models strategically after account connection, entitlement, current model IDs, allowance, and any premium multipliers are established. Do not assume a model available elsewhere is included here. |

For non-urgent **paid GPT** work when included allowance is unavailable or best
reserved, prefer the corresponding existing OpenRouter Flex variant:
`openrouter/openai/gpt-6-luna#flex-high`,
`openrouter/openai/gpt-6.1-terra#flex-xhigh` for an explicitly assigned evaluation,
or `openrouter/openai/gpt-6.1-sol#flex-xhigh` for capable work. These are fallback
choices, not permission to start more work or change a running session silently.

Other model recommendations are welcome. Compare a small representative task,
including source accuracy, defects, repair burden, review cost, latency, and
permission compliance. A different model family can add review diversity, but
must demonstrate adequate capability; cheap review is not an acceptance goal.
There is no standing Haiku default or automatic model-upgrade ladder.

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
