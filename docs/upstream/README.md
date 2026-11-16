# Upstream defects, gaps and contributions

A register of problems Debra has found **in other people's projects**, and the
issues or pull requests we intend to raise about them. It exists so that a
finding made during device work is not lost in a session log, and so that we do
not file a report we cannot defend.

This is not a bug tracker for Debra's own code. Our defects belong in
`docs/notes/` or the work queue.

## Why a separate section

Debra is reuse-first: it depends on upstream projects and expects to contribute
back. A defect found while integrating is evidence about the upstream project,
not about Debra, and it usually outlives the session that found it. Keeping it
here means:

- the evidence is collected once, in one place, with the versions it applies to;
- a report is only filed when it can be reproduced and explained;
- a fix or a rejection is recorded against the original claim.

## The bar before filing

Do not open an upstream issue from a single unverified observation. Before a
report leaves this repository it should have:

1. **A named environment.** Exact project version or commit, OS, kernel,
  architecture, and the command that failed. "It doesn't work on ARM" is not a
  report; "`pymicro-wakeword` 2.5.0, `linux_armv6l` wheel, Raspbian 13, CPython
  3.13, `ctypes.CDLL` raises wrong ELF class" is.
2. **A minimal reproduction.** The smallest command or file set that shows the
  problem, runnable by a maintainer who does not have our hardware.
3. **An impact statement.** Who is affected and how badly. Distinguish "this
  package cannot work on this platform" from "this is inconvenient".
4. **A check that it is not already known.** Search the project's issues and
  recent commits. Link anything related.
5. **A proposed direction, not a demand.** Say what would fix it if we know;
  leave room for the maintainer to know better.
6. **No Debra-private material.** No credentials, no device serials, no
  household network details, no raw recordings.

If any of those is missing, the entry stays `candidate` and says what is
missing.

## States

| State | Meaning |
| --- | --- |
| `candidate` | Found, not yet reproduced cleanly or not yet checked against upstream issues |
| `evidenced` | Meets the bar above; ready to file |
| `filed` | An issue or PR exists; link it |
| `acknowledged` | Upstream has responded |
| `fixed` | A release contains the fix; record the version |
| `withdrawn` | We were wrong, or it was already fixed; say why, keep the record |

Never delete an entry. A withdrawn report is still useful: it records that we
checked and what we learned.

## Naming

`docs/upstream/YYYY-MM-DD-project-short-topic.md`, for example
`2026-11-16-pymicro-wakeword-armv6-elf.md`.

## Relationship to other documents

- The device or research evidence behind a report stays where it was produced
  (`docs/testing/results/`, `docs/notes/`, `docs/research/`) and is linked, not
  copied.
- A report that changes what Debra can support should also update the relevant
  guide or roadmap row, through the coordinator.
- Evidence labels follow [the evidence rules](../evidence.md).
