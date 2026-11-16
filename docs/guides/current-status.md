# What Debra is today

Debra is working toward an affordable Home Assistant voice and music device a
beginner can set up from a browser. One working lab device, a tested browser-control
prototype, offline-tested setup code that has run on a device for the online
path only, CAD models and research exist; no appliance image, no onboarding that
has ever raised its network or been completed by a phone, no updates screen and
no recovery do. Unchecked claims say unknown, per the [evidence labels](../evidence.md),
as of 2026-11-15. SendSpin is the initial music path, Snapcast the alternative, and
full original Pi Zero W support is still an unproven goal.

## What works on the lab device
There is **one** device. No second device has been built.

- Pi 5 Model B Rev 1.0, 4 GB, Pi OS Lite 64-bit (Debian 13), ReSpeaker 2-Mics
  HAT v2.0, PipeWire 1.4.2, linux-voice-assistant v1.1.18 and Sendspin 9.1.0
  ([lab result](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md), tested, one specimen).
- A spoken wake word, speech to text, Home Assistant intent and spoken reply ran
  end to end ("Okay Nabu" at probability 0.986), and music from the household
  Music Assistant reached the HAT over Sendspin, peaking at −12.5 dBFS.
- Its own page answers at `http://debra-3c6b3f.local:8787/`; volume and mute act
  on one explicitly named sink (`alsa_output.platform-soc_107c000000_sound.stereo-fallback`),
  and the percentage is a control setting, not loudness or a safety limit
  ([quickstart](web-control-quickstart.md), [updates log](../updates/2026-11-15.md) — a logged deployment, not a device record).
- An echo-cancel module loads here; whether cancellation works is untested ([audio outputs](../design/audio-outputs.md)).

Power is reported better, not solved: an earlier supply produced "undervoltage
detected" and resets under load, and mitigation was applied (power-watch timer,
1.5 GHz CPU cap, Docker off at boot). James reports a replacement supply mostly
resolved it — a user report, not a measurement; the earlier fault evidence is
historical ([result record](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md#power-the-supply-is-the-suspect-not-the-board)).
Whether the device runs or is reachable now is **unknown**: nobody checked.

## Tested software on the host
These run on a Fedora development computer, not on the Pi.

- The browser slice in `control/web/` is a standard-library service and local page
  for status, selected-sink volume and mute ([README](../../control/web/README.md)):
  124 tests in `tests/test_web.py` plus 19 installed-artifact tests in
  `tests/test_install.py` on 2026-11-15; the Chromium scenarios are opt-in and
  skip in an ordinary run (23 in `test_web_browser.py` and 27 in
  `test_setup_browser.py`, 50 skipped in total).
- Its installer, `control/web/install.py`, prepares files only: five runtime files
  in a content-addressed release, an owner-only key and a systemd user unit, with
  previous units kept for rollback. No packages, sudo, audio writes or service starts.
- Discovery shares one mDNS parser (`control/web/discovery.py`, `tools/discover.py`)
  and lists announced devices (15 tests). The activity table has 98 tests and its
  notices checklist 24; the task helper and research runner 15 and 9
  ([unattended runner](scheduled-runner.md)).
- The first-boot setup service in `control/setup/` is offline-tested
  ([README](../../control/setup/README.md)): 266 tests for naming, onboarding and
  the baseline, and 46 for its installer. One device run has happened, on the
  other line's tree at `a90cfba`
  ([result](../testing/results/2026-11-15-zero2w-setup-service-first-run.md)):
  the online path, the hardware-derived rename, a baseline, a manual start and
  then a boot with the unit enabled all worked. It left `/etc/hosts` and
  `avahi-daemon` on the old name until the next boot repaired both. The setup
  access point has never been raised, and this branch's tree has not run on a
  device.
- The activity TUI has a **Notices** tab: one checklist of everything worth not
  missing (blockers, confirmations, failed research tasks, a turn running too
  long), ticked off with `x` and kept as a dimmed "checked off" count so a
  mistake is one keystroke to undo. Marks live in `.local/status/notices.json`,
  are owner-only, and are dropped when the notice itself goes away.

**Honest label:** the roadmap files this as WEB01 `/ prototype`. It has been
through ten independent review rounds; the last one (`code-r10`) returned
*changes requested* with five reproduced findings — most seriously, a restore
command that named no release at all was accepted because the check skipped every
argument that did not start with `/`. Those are repaired and `code-r11` is
reviewing the repair. The candidate is **not approved** until that lands, and the
release deployed to the lab device predates all of it
([roadmap](../roadmap.md#browser-first-device-control), [updates log](../updates/2026-11-15.md)).

## Design and models
`models/` holds parametric SolidCraft sources with renders: component envelopes
(Pi 5, three Pi Zero variants, the ReSpeaker HAT, three DWEII modules and
ten driver candidates), the v17 STEP reference, CAD-only assemblies and printable part designs
([models index](../../models/README.md)). Nothing is sliced, printed or fit-tested;
three rebuilt parts reproduce volume and bounding box within 0.1%. Two claims were
withdrawn as never checked: overlap is a mated socket, not a collision test, and
the upright understates connector depth. The v17 body shows no four-screw square
speaker mount in the STEP, but the wider search that tested that is **inconclusive**
rather than a finished negative, and James reports the original has one; a
photograph is still the evidence that would settle it.

## Research and comparisons
`docs/research/`, `docs/notes/` and `docs/comparisons/` hold sourced comparisons,
board screening, parts pricing and onboarding or recovery studies. Most is
unreviewed: a review of four notes returned nine high findings and judged none
usable as written; revision 2 answers those and is itself unreviewed, and the
comparison tables inherit the findings and declare themselves not buying guidance
([review](../notes/2026-11-15-research-notes-review.md), [roadmap](../roadmap.md)). Prices are dated observations, not quotes.

Two documents have since come through independent review: the ARMv6
reconnaissance was **approved** after five rounds as research and
experiment-design evidence ([Z01](../research/Z01-armv6.md)) — it proves no
ARMv6 runtime, and the retained historical binary's build lineage and prior
execution are still unknown — and the acceptance matrix was **accepted** after
four rounds as test design ([acceptance](../testing/acceptance.md)), which
approves no threshold and runs no test: every physical and privileged case in it
is still `not-run`.

## What does not exist
- No appliance image or image build: nothing here turns a blank card into a
  working Debra device.
- No onboarding that has run on a device: the setup portal, the hardware-derived
  `debra-<id>` name and the first baseline exist as offline-tested code, but no
  radio has been raised, no network joined and no name applied by them. There is
  no captive portal. Browser enrollment is **decided but not built**: the device
  password is to be chosen during setup, with development-only provisions (a
  bypass, an uncontested reset and `debra`) that production mode must refuse
  ([decision](../design/browser-enrollment.md)); today the page's access key is
  only obtainable from a terminal, and there is no revocation.
- No updates screen and no per-component update policy.
- No recovery implementation: no on-target capture/restore tool and no verified
  device restore; web rollback is fixture-tested only, imaging deferred
  ([device backup](device-backup.md)).
- No SSH-friendly setup and maintenance TUI, no supported hardware matrix: one
  tested Pi 5 plus ReSpeaker v2 pairing is not a matrix, and Zero W/ARMv6 remain
  unproven.
- No configuration model or component lifecycle layer, no tested duck/pause
  interruption, no multiroom acceptance, no measured echo-cancellation result.

## The intended journey (a destination, not current behavior)

The destination for an assembled device is:

1. Boot a prepared image with Debra's tools already present.
2. Configure Wi-Fi if needed, ideally through a browser flow.
3. Receive a repeatable identity and hostname derived from the board.
4. Capture a recoverable baseline once Wi-Fi and identity work.
5. Connect over SSH and open simple setup and maintenance tooling.
6. Return later to reconfigure, update, diagnose, and restore.

None of these steps works today; this is the destination, not current behavior.

## Historical scripts, not recovery tooling
`backups/backup.sh` and `backups/restore.sh` copy with `sudo rsync --delete`
between `/` and `/mnt/backup/`. They are destructive, omit important paths and
print success unconditionally. Do not run them as tests or treat them as backup
or recovery support.

## How to check this yourself
The first command was run on 2026-11-15 with concurrent working-tree edits. Its
count grows as tests are added, so the command is the authority, not any number
written here. The last needs an installed Chromium
([web README](../../control/web/README.md)).

```sh
python3 -B -m unittest discover -s tests -v          # the authority: passes, browser modules skip
python3 -B -m unittest tests.test_docs -v            # 11 documentation checks
bash -n backups/backup.sh backups/restore.sh         # syntax only
DEBRA_BROWSER_TEST=1 python3 -B -m unittest discover -s tests -p 'test_*browser.py' -v
```

Device claims rest on the [lab result](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md), the
[updates log](../updates/2026-11-15.md) and [quickstart](web-control-quickstart.md); none of
these commands tests audio, hardware, ARMv6 or a live network.

## Status
F05 and production dispatch are not approved by this page. The browser code
candidate is a prototype awaiting acceptance review. A documentation review alone
does not establish worker readiness or approve an implementation.
