# Upstream report template

Copy to `docs/upstream/YYYY-MM-DD-project-short-topic.md`. Fill every field
honestly; use `unknown` rather than guessing. A report that cannot fill
"Minimal reproduction" is a `candidate`, not `evidenced`.

```yaml
---
title: One-line statement of the defect
date: YYYY-MM-DD
type: upstream-report
state: candidate | evidenced | filed | acknowledged | fixed | withdrawn
project: owner/repo
component: package, file or subsystem
affected_versions: exact versions or commit range
fixed_in: version, or unknown
environment: OS, kernel, architecture, runtime versions
author: Agent or person
author_model: Exact host-reported provider/model or unknown
author_variant: Exact host-reported variant or unknown
sources:
  - Repository path/commit, upstream URL, or attributed statement
links:
  issue: URL or none
  pull_request: URL or none
  related: URLs
---
```

## Summary

What is wrong, in two or three sentences, and who it affects.

## Impact

Who is affected, how badly, and whether there is a workaround. Separate "cannot
work at all" from "works but is inconvenient".

## Minimal reproduction

The smallest set of commands or files a maintainer can run. State the expected
result and the actual result.

## Evidence

| Kind | Claim | Source / version scope | Verification |
| --- | --- | --- | --- |
| observed / upstream-documented / reported / hypothesis | One claim per row | Specific citation | What was actually run or read |

## Root cause (if known)

Where the defect originates, and how confident that is.

## Proposed direction

What would fix it. Mark it as a suggestion.

## What is still missing before filing

The gaps that keep this at `candidate`, if any.

## History

Dated entries: what was checked, what upstream said, what changed.
