---
title: What the headless browser cannot do, and what the keyfile reader actually parses
date: 2026-11-15
type: project-learning
status: unreviewed
task: code-r7
author: OpenCode coordinator
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - /tmp/opencode/ probes described below, run 2026-11-15 against Chromium at /usr/bin/chromium-browser
  - tests/test_web_browser.py (the 390 px harness), control/setup/nm.py `_keyfile_ssid`
  - .local/reviews/setup-r3-20261115/verdict.md and .local/reviews/code-r7-20261115/verdict.md
supersedes: []
---

## Summary

Two findings from the r3/r7 repair rounds that will otherwise be rediscovered:
headless Chromium here cannot produce a narrow viewport by any flag, and
NetworkManager's keyfile reader is not GLib's. Both were found by a probe, not by
reading documentation, and both changed a test's design.

## Claims and evidence

| Kind | Claim | Source / date / hardware-version scope | Verification and limits |
| --- | --- | --- | --- |
| observed | `--window-size=390,844` lays out at 500 CSS px, with or without `--force-device-scale-factor`, in headless mode. 500 is a floor on the window, not on the viewport | Chromium at `/usr/bin/chromium-browser`, 2026-11-15, this host | `document.documentElement.clientWidth` reported 500 in a page that printed it; `--headless=new` behaved the same |
| observed | An iframe of `width:390px` lays out its document at exactly 390 CSS px | same host, same day | three frames of 390/500/320 reported 390/500/320 |
| observed | A visible scrollbar inside that frame removes 15 px, so the framed layout viewport is 375 | same host | 390 px frame reported `clientWidth` 375; `--hide-scrollbars` restored 390 |
| observed | An inline `style="width:390px"` is dropped when the wrapper document is served with `style-src 'self'`, and the iframe falls back to its 300 px default | same host | the frame's `getBoundingClientRect().width` was 304 while the attribute said 390 |
| observed | The product page's own CSP (`frame-ancestors 'none'`) prevents it being framed, so a framed test copy must relax exactly that directive | `control/web/server.py` `reply()` | the framed copy keeps every other directive |
| observed | `nm_keyfile_read` (libnm, `/usr/lib64/libnm.so.0`) reads the historical semicolon-separated integer SSID form: `65;66;` becomes `AB`, and `A\;B` loses its backslash | this host's installed libnm, 2026-11-15 | the probe needs an **absolute** `base_dir` and `[ipv4]`/`[ipv6]` groups or libnm asserts; the byte list `_keyfile_ssid` round-trips every name tested |
| hypothesis | A GLib-escaped string round-tripping through `GKeyFile` does not prove the keyfile plugin will read the same bytes, because the plugin uses NetworkManager's reader | inferred from the two observations above | not tested against a real NetworkManager loading a profile; that is still the open device question |

## Verification

- Exact safe commands/procedure and working directory: the probes were standalone
  scripts under `/tmp/opencode/` (`width_probe.py`, `dsf_probe.py`,
  `iframe_probe2.py`, `phone_probe.py`, `core_probe.py`) that start a loopback
  HTTP server and run Chromium with `--dump-dom`; the libnm probe is described in
  the r3 verdict.
- Observed results: pass for the harness findings (the 390 px test fails when the
  CSS fix is reverted, and passes with it).
- Not tested, conflicting evidence, and remaining uncertainty: nothing here is a
  phone, and nothing here is a real NetworkManager. The harness proves a 390 px
  *layout viewport* in this Chromium, not a touch device's behaviour.
- Sanitized artifact references: `tests/test_web_browser.py` `PHONE_WRAPPER`,
  `PHONE_CSS`, `PHONE_SCRIPT` and the `--hide-scrollbars` argument.
