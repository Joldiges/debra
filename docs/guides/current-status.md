# What Debra is today

Debra is a planning and reference documentation project. It also contains local
tooling that coordinates AI work tasks across separate Git worktrees. It is not
a working appliance image, installer, or text interface. This checkout provides
documentation and coordination tooling, not a validated end-to-end appliance, a
supported hardware matrix, or a recovery implementation. The page reflects the
repository baseline of 2026-11-14.

## Available now

- Written guidance: the [project brief](../project-brief.md), the
  [roadmap](../roadmap.md), the [AI workflow](../ai-workflow.md), evidence
  rules, development guidance, and a documentation map.
- Dated learning notes and handoff conventions.
- A standard-library Python helper that records local task claims and creates
  task worktrees for one clone.
- Historical backup scripts, described below.

These establish project direction and working conventions. They are not
evidence that any appliance component works.

## Planned, not validated

The roadmap's planning foundation is marked done. Its planned device
implementation work is a backlog: prepared image, onboarding, configuration
interface, voice and music adapters, snapshots, and enclosure models. None of
those packets has produced a validated capability, and no date is promised.

## The intended journey (a destination, not current behavior)

The destination for an assembled device is:

1. Boot a prepared image with Debra's tools already present.
2. Configure Wi-Fi if needed, ideally through a browser flow.
3. Receive a repeatable identity and hostname derived from the board.
4. Capture a recoverable baseline once Wi-Fi and identity work.
5. Connect over SSH and open simple setup and maintenance tooling.
6. Return later to reconfigure, update, diagnose, and restore.

None of these steps works today; this is the destination, not current behavior.

## Music and hardware priorities

SendSpin is the initial music priority. Snapcast is retained as an alternative.
Supporting the original Pi Zero W fully is an engineering goal, and it is
unproven. No compatibility, price, release, performance, device-access, or
recovery outcome is promised.

## Historical scripts, not recovery tooling

`backups/backup.sh` and `backups/restore.sh` are old utilities that copy with
`sudo rsync --delete` between `/` and `/mnt/backup/`. They are destructive, they
omit important paths, and they print success unconditionally. Do not run them as
tests or treat them as backup or recovery support.

## Status

F05 and production dispatch are not approved by this page. A documentation
review alone does not establish worker readiness.
