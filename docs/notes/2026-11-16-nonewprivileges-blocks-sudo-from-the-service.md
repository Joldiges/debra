---
title: NoNewPrivileges=yes means a generated systemd unit cannot use sudo at all
date: 2026-11-16
type: project-learning
status: unreviewed
task: none
author: OpenCode agent
author_model: openrouter/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - Observed on debra-3c6b3f (Pi 5), 2026-11-16; see docs/testing/results/2026-11-16-hat-install-through-the-page.md
  - control/web/install.py (unit generator, NoNewPrivileges=yes)
  - man 5 systemd.exec, NoNewPrivileges=
supersedes: []
---

## Summary

A privilege-escalation path that works from an SSH shell can be impossible from
the service that needs it. Debra's web unit is generated with
`NoNewPrivileges=yes`; `sudo` is setuid, and that setting is precisely what stops
a setuid binary from granting privilege. So `sudo -n /path/to/helper` returns a
refusal from the service while succeeding from a shell on the same device, under
the same account, with the same sudoers rule.

This is a property of the sandbox, not a missing sudoers entry, and no `sudoers`
change fixes it. The usable shapes are a socket-activated unit (`Accept=yes`) or
a privileged service with a narrow interface — not a setuid call.

## Claims and evidence

| Kind | Claim | Source / date / hardware-version scope | Verification and limits |
| --- | --- | --- | --- |
| observed | `sudo -n` succeeds as `debra` from an SSH shell and from `systemd-run --user --scope`, and fails for the same call made by `debra-web.service` | `debra-3c6b3f`, 2026-11-16 | The failure was reproduced through the page's own endpoint (409) and by reading the unit; not by instrumenting sudo itself |
| observed | The unit generator writes `NoNewPrivileges=yes` into every generated unit | `control/web/install.py`; `~/.config/systemd/user/debra-web.service` on all three lab boards | Read from the installed unit, not inferred |
| documented | `NoNewPrivileges=` also disables setuid and file capabilities for the whole service | `systemd.exec(5)` | Standard documented behaviour |
| inference | Removing the line would make `sudo` work at the cost of a real hardening measure on a LAN-reachable service | Reasoning from the above, 2026-11-16 | A trade, not a measurement; the hardening value itself was not quantified |

## What replaced it

`debra-hat.socket` + `debra-hat@.service`, `StandardInput=socket` /
`StandardOutput=socket`: one connection starts one root process, which reads one
JSON request and exits. The web service keeps `NoNewPrivileges=yes` and no
passwordless `sudo` rule exists on the device.

## Verification commands used

- `systemctl --user cat debra-web.service` (or read `~/.config/systemd/user/`) for the flags.
- From the host: `ssh debra@<board> 'sudo -n -l /usr/local/sbin/debra-hat-install'` succeeds, while the service's own call fails — the difference is the unit, not the account.

## Handoff

- Reusable rule: when a design needs privilege from a service, read the generated
  unit's sandbox flags **before** designing the transport.
- The same trap applies to any future setuid helper, `pkexec`, or capability
  binary called from a unit that carries this setting.
- Not tested: whether a *system* unit (rather than `--user`) with the same flags
  behaves differently — the flags are per-service, so it should not, but that was
  not run.
