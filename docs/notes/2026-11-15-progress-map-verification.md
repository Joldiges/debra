---
title: Progress map browser rendering and verification
date: 2026-11-15
type: project-learning
status: unreviewed
task: progress-map
author: OpenCode coordinator
author_model: openai/gpt-6.1-sol
author_variant: unknown
sources:
  - "Progress map integration: 636a195fc0d59da064369a99628bd51fb783c9c3"
  - "Clean validation: 5956db4 and 0bc3723580f9740e0fb9e96cdf244a5fdcdc45ce"
  - "tools/progress.py and tests/test_progress.py"
  - "Local Chromium and Mermaid rendering records described below"
supersedes:
  - "docs/updates/2026-11-15.md, progress-map report: not browser-rendered limitation only"
---

## Summary

The [whole-product progress map](../progress.md) contains 17 Mermaid diagrams
covering all 75 roadmap packets. Every diagram rendered in installed Chromium
with Mermaid 11.4.1, both at the landed map revision and at the later validation
snapshot `0bc3723`. This supersedes only the earlier report's
[not-browser-rendered limitation](../updates/2026-11-15.md#a-progress-map-that-cannot-drift-into-a-second-backlog);
phone layout and GitHub's renderer remain untested.

This is verification evidence, not product acceptance or a live activity
monitor. Independent review of the frozen landed map was still pending when
this note was written.

## Claims and evidence

| Kind | Claim | Source and scope | Verification and limits |
| --- | --- | --- | --- |
| user-requirement | Show the whole product's steps, dependencies and progress using colour and text | James's progress-map request; [implementation](../../tools/progress.py), [map](../progress.md) | Simplified overview, parallel tracks and expandable packet diagrams; not just software |
| observed | The map was already committed by another session; the original candidate was not reapplied | Integration `636a195`; frozen revision r2 below | Generator, tests, roadmap and both README files match r1; r2 also records queue-context/fingerprint changes and the added report |
| observed | All 17 graphs render with expected node counts and positive SVG dimensions | Chromium `156.0.8078.79`, Mermaid `11.4.1`; two version-bound artifact folders below | Checks SVG creation and completeness, not phone usability, screen-reader behaviour or GitHub rendering |
| observed | Later roadmap maintenance reached the generated map | `94afb72`, included in `0bc3723`: T03 now depends on B04 instead of deferred B05 | The later snapshot was separately rendered; its graphs are not byte-identical to r2 |
| observed | Default-environment offline checks pass at the later clean snapshot | Worktree `coord/progress-map-20261115` at `0bc3723` | 654 tests run, 43 skipped; progress drift and taskchain checks pass |
| observed | One existing web test depends on the process file-creation mask | [test_insecure_state_rejected](../../tests/test_web.py), lines 1264–1268 at `0bc3723` | Under `umask 0077`, its requested `0755` directory becomes `0700`, so the expected rejection does not occur; the full suite passes under `0022`. No test or web code was changed here |

## Verification

Safe checks from the repository root:

```bash
python3 tools/progress.py --check
python3 tools/taskchain.py check
python3 -B -m unittest tests.test_progress tests.test_docs -v
python3 -B -m unittest discover -s tests -v
```

- At `5956db4`, the clean worktree's full offline suite passed: 654 tests,
  43 skipped. The progress and taskchain checks also passed.
- At `df41481`, progress drift and the 24 progress/documentation tests passed.
- At `0bc3723`, the clean worktree's progress and taskchain checks passed.
  The full offline run under `0077` had one failure described above; its
  separate rerun under `0022` passed all 654 tests, with 43 skipped. Logs were
  created with mode `0600` independently of the test process's mask.
- Taskchain validation reports 19 chains covering 65 packets. The progress
  map's 75-packet inventory also includes WEB01–WEB10, outside that catalog.
- Browser procedure: extract the version-bound page's 17 fenced Mermaid
  blocks, load the locally retained Mermaid asset in a localhost-only HTML
  harness, render each graph in headless Chromium, and compare SVG node counts
  with the graph declarations. Require positive SVG extents and a PASS record.
- No tooling was installed. No lab device, radio, household service, backup
  or restore script was operated. The ordinary suite skips opt-in browser
  cases; the Mermaid harness is separate from those application tests.

Version-bound local artifacts, retained under ignored owner-only storage:

| Artifact | Identity / result |
| --- | --- |
| `.local/coord/progress-map-20261115-r2/` | Frozen eight-file landed candidate, base `3423f71`, candidate `636a195`; patch SHA256 `12dc446e088d037dd492437ae9f8ca03717bde660f750d08cef4290f27322fe4` |
| `clean-full-suite.log` in that folder | Passing clean run at `5956db4` |
| `clean-full-suite-0bc3723.log` in that folder | Preserved `0077` run with the single fixture failure |
| `clean-full-suite-0bc3723-default-umask.log` in that folder | Passing `0022` run at `0bc3723` |
| `.local/artifacts/progress-render-final-64xotzf1/` | r2 browser harness, rendered HTML and `result.json`; page SHA256 `9f58561aac11266f814fb0726e65fd17e302848f9a2e34643d1f4b0f1f9e5db2`; 17/17 PASS |
| `.local/artifacts/progress-render-0bc3723-cq5uhwjt/` | Later page, browser harness, rendered HTML and `result.json`; page SHA256 `c09a6607c238d68de4dcbd81b1cd5e99a44bd5c9517ab58720357285407a96e9`; 17/17 PASS |

Mermaid asset:
`https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js`,
SHA256 `a43bc1afd446f9c4cc66ac5dd45d02e8d65e26fc5344ec0ef787f88d6ddb6f9e`.
Raw artifacts are local evidence, not an independent backup or files available
in a fresh clone.

## Handoff and correction links

- Independent reviewer session: `ses_e1d64af01ffexFoII19cxh5VX0`, role
  `debra-review`; exact reviewer model/variant awaits its report. Its assignment
  is frozen r2, not mutable main or the later T03 dependency edit. The review is
  post-landing; it must not be presented as approval preceding integration.
- Next: receive that report, record its verdict separately, and address any
  actionable findings without overwriting concurrent work. The restrictive-mask
  fixture issue is evidence for the web-test owner, not authorization to edit
  unrelated tests in this task.
- Routine maintenance remains deterministic: edit
  [roadmap](../roadmap.md)/[work queue](../work-queue.md), then run
  `python3 tools/progress.py`; `--check` detects drift. No unattended updater
  or live monitoring was added.
