# Learning note template

Use for a new dated note under `docs/notes/`, not for private raw logs. Follow the
[documentation/memory guide](../README.md). Fill fields honestly; use `unknown`
or `not-run` instead of guessing. Review status and evidence are distinct.

```yaml
---
title: Short factual topic
date: YYYY-MM-DD
type: project-learning
status: unreviewed
task: Task ID or none
author: Agent or person
author_model: Exact host-reported provider/model or unknown
author_variant: Exact host-reported variant or unknown
sources:
  - Repository path/commit, source URL/version, or attributed user statement
supersedes: []
---
```

## Summary

The useful result, its evidence status, and the main limitation in a few lines.
Link to the canonical report or implementation rather than duplicating it.

## Claims and evidence

| Kind | Claim | Source / date / hardware-version scope | Verification and limits |
| --- | --- | --- | --- |
| user-requirement / observed / upstream-documented / hypothesis / open-question / proposed-decision | One claim per row | Specific citation | Actual result, not confidence alone |

## Verification

- Exact safe commands/procedure and working directory:
- Observed results: pass / fail / partial / not-run:
- Not tested, conflicting evidence, and remaining uncertainty:
- Sanitized artifact references, if any:

## Handoff and correction links

- Current state and relevant base/candidate revision:
- Concrete next action and prerequisites:
- Authorization needed; do not treat this suggestion as permission:
- Earlier claim superseded, if this is a correction:
- Reviewed report/decision that later adopts this finding, if known:

Once handed off, preserve this note. Record later corrections/reviews in a
new dated note that cites it; update curated conclusions only through the
coordinator's review. Do not turn one failed attempt into a universal rule.
