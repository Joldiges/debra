---
title: Independent review of seven research notes, round 2
date: 2026-11-15
type: project-learning
status: unreviewed
task: review
author: OpenCode review subagents (seven independent sessions)
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: high
sources:
  - docs/notes/2026-11-15-parts-inventory.md (R01, reviewed 2026-11-15)
  - docs/notes/2026-11-15-complete-alternatives-comparison-revision.md (R02 rev 2, reviewed 2026-11-15)
  - docs/notes/2026-11-15-music-transport-and-control-map.md (R03, reviewed 2026-11-15)
  - docs/notes/2026-11-15-upstream-reuse-audit-revision.md (R04 rev 2, reviewed 2026-11-15)
  - docs/notes/2026-11-15-alternative-board-screen-revision.md (R07 rev 2, reviewed 2026-11-15)
  - docs/notes/2026-11-15-storage-durability.md (B01, reviewed 2026-11-15)
  - docs/notes/2026-11-15-wifi-onboarding-options-revision.md (N01 rev 2, reviewed 2026-11-15)
  - docs/notes/2026-11-15-research-notes-review.md (the round-1 review, 28 findings)
  - docs/evidence.md; docs/project-brief.md; docs/development.md
  - docs/work/cards/{R01,R02,R03,R04,R07,B01,N01}.md
  - .local/reviews/setup-r3-20261115/verdict.md (cited by the N01 review)
supersedes: []
---

## Summary and verdicts

Independent desk reviews of the seven notes that carried `status: unreviewed`
after the round-1 review of four notes. Each note was read by a separate review
session with fresh context, which re-fetched the cited sources rather than
trusting the note's confidence. The notes under review are preserved unchanged;
this note records what the reviews found.

| Note | Verdict | High | Medium | Low |
| --- | --- | ---: | ---: | ---: |
| [R01 parts inventory](2026-11-15-parts-inventory.md) | **Minor revision** — not usable for a buying decision as it stands | 2 | 6 | 14 |
| [R02 complete alternatives rev 2](2026-11-15-complete-alternatives-comparison-revision.md) | **Minor revision** — no High findings; residual sentences and one wrong citation | 0 | 8 | 10 |
| [R03 music transport map](2026-11-15-music-transport-and-control-map.md) | **Changes required** before it informs A03/M01 | 1 | 8 | 7 |
| [R04 upstream reuse audit rev 2](2026-11-15-upstream-reuse-audit-revision.md) | **Minor revision** — substance holds, verification apparatus does not | 0 | 5 | 4 |
| [R07 alternative board screen rev 2](2026-11-15-alternative-board-screen-revision.md) | **Minor revision** — one card-required dimension silently deleted | 1 | 3 | 7 |
| [B01 storage durability](2026-11-15-storage-durability.md) | **Major revision** before it informs the recovery design | 4 | 9 | 5 |
| [N01 Wi-Fi onboarding rev 2](2026-11-15-wifi-onboarding-options-revision.md) | **Major revision** — diverges from the implemented flow | 5 | 9 | 6 |
| **Total** | | **13** | **48** | **53** |

Severity: **High** can misdirect a buying, recovery, security or implementation
decision. **Medium** needs correction or qualification before the affected claim
is relied on. **Low** is a traceability or editorial defect.

**None of these verdicts approves a hash.** No review was given a frozen commit,
and every reviewer said so; each verdict binds only to the file content read.

## Independence, stated plainly

Every reviewer ran on `deepseek/deepseek-v4.1-flash-1017`, which is also the
recorded author of R01, R03 and B01. Their findings rest on citations that were
re-checked against live sources, so they are source-checked — but they are not
model-independent, which is what the workflow expects of an acceptance review.
The three notes that feed decisions (R01 buying, B01 recovery, R03
implementation) should be re-reviewed by a different, stronger model before
their corrections are accepted. Earlier rounds used `openai/gpt-6.1-sol` and
`gpt-6.1-terra` for that role.

## What the reviews agreed on

Two patterns recur across five of the seven notes, and they are the reason
several verdicts are "minor revision" despite sound research:

1. **A verification claim that was never recorded.** R04 cites "the exact
   result" of a test run that its handoff does not contain; R07 says a test
   result "is reported in the handoff below" and the handoff reports none; N01
   says it "ran the offline documentation test suite (below)" and there is no
   below. R04 and R07 also both misdescribe what `tests/test_docs.py` covers —
   it does walk `docs/notes/`, so the check they propose extending already
   exists.
2. **A fix claimed but absent.** R04 reports a link correction that is not in
   the text and a defect that does not reproduce; R02's change log says "the
   brief's other goals retained" when the revision contains no reasons-to-build
   content at all; R07 marks R07-6 addressed after deleting the power column it
   refers to.

Three notes also describe text that has since changed underneath them: R03's
"corrections to earlier notes" section describes `music-playback.md` and roadmap
A03 wording that has already been corrected, and the index rows for R02 and R07
in `docs/README.md` now describe earlier revisions rather than the files they
link to.

## R01 — parts inventory and build cost

**Verdict: minor revision — do not use for a buying decision yet.** Arithmetic is
correct: every total reproduces ($59.90, $68.35, $62.49, $16.40, $17.35, $93.95,
$139.00, $176.85, $281.85, $417.00). Most vendor prices were re-fetched and match.

### High

**H1 — the headline build pairs a speaker that cannot plug into the HAT.** The
$59.90 total prices the DWEII 701715520462 ($3.50), whose connector the note
records as **JST-PH 2.5** (line 153), into a ReSpeaker 2-Mics HAT whose speaker
out is documented as **JST 2.0**. Both facts are in the note's own source rows;
the mating question is never asked. `models/parts/dweii-462-case/README.md`
already flags that "PH normally denotes 2.0 mm pitch, so the 2.5 mm description
needs checking". *Correction:* state the HAT's JST 2.0 socket, that the 462 is
described as 2.5 pitch and does not mate, that the 671/664 (JST-PH 2.0) do, or
price a ~$1 adapter; mark the 462's pitch unconfirmed.

**H2 — "Honest recommendation for a first unit: Buy…" is a purchase instruction
with no test behind it.** Lines 317–321 recommend a board that the note itself
records as out of stock at both US sellers, for a combination never run (the only
`[T]` row is Pi 5 + 2-Mics v2), and the recommendation contradicts the note's
closing line, "No supported combination is claimed by this inventory."
*Correction:* label it a provisional decision for coordinator approval, name the
tested combination, and price the UK import or state duty as unknown.

### Medium

- **M1** — the ~$40 conclusion contradicts itself: line 62 says "$40 is plausible
  only in the reused-parts sense" while lines 289–296 present three under-$40
  routes that buy a new board. "Reused" means "Pi also owned" in table B and
  "accessory reuse" in the brief. Define both once.
- **M2** — the $68.35 second-supply line rests on the **deprecated v1 wiki**; the
  v2 page documents no POWER port. Also never asked: whether two supplies on one
  5 V rail may be connected at once.
- **M3** — four SD-card and reader rows cite [P14], a PiShop page that does not
  contain them; two rows have no citation at all. No total depends on them.
- **M4** — the "$11.95 Official Raspberry Pi 27 W" is PiShop's own ETL supply;
  the official unit is $12.95 on the same page. Used in the $135.90 dev total.
- **M5** — the brief-required 3.5 mm external-speaker path has no part, no cost,
  and only negative evidence (headphone tap ≈ −100 dBFS on the lab specimen).
- **M6** — evidence labels are not applied per claim; value judgments ("false
  economy", "better value") read as findings.

### Low

Fourteen, all editorial or traceability: "four sellers" where six are used; the
PiShop Zero W and Zero 2 W both at $17.25 from one search page; a quoted "Notify
Me" the page does not show; "the 671 is not [a 4-pack]" when [P18] says the 664
is the same 4-pack family; $31.35 silently includes the $0.95 header; "the WH
variants and the Pi 5 do not [ship with a header]" reads backwards; the mating
socket question is asked of Waveshare but not Seeed; "no second power supply" for
the WM8960 ignores that its amplifier draws on the Pi's rail; a case-fit claim
asserted without a source; "$8 ReSpeaker is a V1 or a clone" when [P19]
identifies a Keyestudio V1; "bought Zero cases" contradicting "no part was
bought"; an unconfirmed $19.80 Adafruit price; correction attribution naming a
different model from the correction note's author; two uncited rows.

## R02 — complete alternatives comparison, revision 2

**Verdict: minor revision.** All seven R02 findings are substantially addressed
and no High defect remains. Every derived figure was recalculated against R01 and
reproduces; all 31 reference definitions resolve.

### Medium

- **M-1** — both headline totals price a **Pi Zero 2 W that R01 records as out of
  stock at both US sellers** on the stated date, inside a block headed "US
  sellers", then rank it against products that were buyable. `devices.md` already
  carries this caveat for its copy of the table.
- **M-2** — the replacement ranking compares parts-only totals with assembled
  device prices, which the note's own "Not comparable" section forbids two
  sections later.
- **M-3** — the amplifier is stated present, absent and unknown in four places,
  including one bullet asserting both "this build needs no extra amplifier line"
  and "whether any DWEII module needs one is unknown". This is the item the docs
  index flagged in the previous revision, reintroduced in the cost table.
- **M-4** — the Google Home price is cited to an Engadget article that says
  **$100**, not $99.99, and is about the Nest discontinuation, not launch pricing.
- **M-5** — "Complete purchase" and "listed" are wrong labels for totals that
  exclude the printed enclosure and contain an undated historical speaker price.
- **M-6** — "tested-hardware route" implies a pairing never tested; only Pi 5 +
  2-Mics v2 is `[T]`.
- **M-7** — the surviving "only" (Satellite1.1) is false against the note's own
  Google and HomePod rows unless "for Home Assistant" is added.
- **M-8** — the change log claims "the brief's other goals retained"; the
  revision contains no reasons-to-build content, and the card's microphone
  topology, alarms, privacy and update-ownership dimensions are absent.

### Low

Ten, mostly citation and labelling: "browser onboarding" is new and unsupported;
the maintenance claim ignores the ESPHome dashboard; a correction link points at
a file that does not carry it; $417.00 should be ≈$417; VoiceS3R prices lack the
`unknown` marker `devices.md` uses; the HA server is required but unpriced; no
`## Verification` block and a missing provider prefix in `author_model`; the
`docs/README.md` row now misdescribes the file; EUR is unlisted in the currency
note; a fourth distributor is omitted from a section about sellers.

## R03 — music transport and control map

**Verdict: changes required.** The protocol analysis is sound and unusually well
bounded — transport, controller and player roles, pause semantics, Snapcast's
control surface and mixer modes, the CLI's hook precedence, MA's volume routing
and the HA/ESPHome limits were all matched to the pinned sources.

### High

**H1 — the revision pin is misleading.** Line 11 gives `main @ 9d2f15ee…` and
tag `1.0.0-rc1`, but `9d2f15ee` is **not** the rc1 commit — it is a November
commit ("Stop players from snapping on small sync errors #359"). Line 124 then
names the tag as the version the claims rest on while every reference link
resolves to `main`. Snapcast (`master`), the Python CLI (`main`), HA core (`dev`)
and MA carry no resolvable revision at all. *Correction:* one revision per
project, every link resolving to it, or drop the "inspected revisions" claim.

### Medium

- **M1** — `client/hello` advertises only `supported_formats` and
  `buffer_capacity`; `output_delay_ms`, `required_lead_time_ms`, `min_buffer_ms`
  and `supported_commands` are `client/state`. The note's own table says so.
- **M2** — the "most consequential detail" names the wrong object: the CLI's
  hardware-volume backend tries ALSA first, so on the lab HAT it would write a
  codec mixer element, not the sink. The blast radius survives; the mechanism is
  conditional.
- **M3** — "Pause: not through a documented interface" contradicts the note's own
  table and `stream_plugin.md`, which documents `Plugin.Stream.Player.Control`
  with `pause`, gated on `canPause`.
- **M4** — the "corrections to earlier project notes" section describes text that
  has already been corrected in `music-playback.md` and roadmap A03.
- **M5** — two card-required deliverables are missing: the source-backed **ARMv6
  constraint list** (deferred with a pointer) and **licensing** (absent from 466
  lines).
- **M6** — `sendspin` 9.1.0 pins `aiosendspin~=10.2.2`, not 10.3.0, and the CLI's
  own stated server requirement (MA 2.10.7+) differs from the ESPHome figure the
  note presents as general.
- **M7** — the summary asserts MA ends the stream on pause, which the note's own
  "Not verified" section lists as unobserved.
- **M8** — `send_to_muted`'s default is cited to Snapcast's configuration page,
  which states no default; MA's page does.

### Low

Seven: `^1.5` is SHOULD, not a protocol guarantee; the MAC-registration trigger is
inverted ("seen before" vs "for the first time"); `notifyVolumeChange` is scoped to
the PulseAudio backend; the controller gate omits the importability condition; the
activation requirement is missing from the summary; the org quote has no URL; two
file-level citations point into a 3,154-line file.

## R04 — upstream reuse audit, revision 2

**Verdict: minor revision.** Six of seven findings are genuinely closed, and the
reviewer verified the underlying sources rather than the note's confidence — the
rpi-image-gen armhf layers, pi-gen's `STAGE_LIST` and cloud-init defaults,
PiCompose's `pi`/`raspberry` workflow inputs, and LVA's compose defaults all match.

### Medium

- **M1** — the revision repeats a review finding that **does not reproduce**
  (R04-5's "broken relative links": the original's `../research/…` paths resolve)
  and claims a correction that is not in the text.
- **M2** — the verification section cites a test result its handoff does not
  contain, and claims `tests/test_docs.py` does not cover `docs/notes/` when it
  does — so the check it proposes extending already exists.
- **M3** — R04's acceptance criteria are not met: no mechanism, pin,
  initialisation, test, maintenance exit or rollback per selected reuse, though
  the note recommends two adoptions.
- **M4** — two rows refer to "reuse target 12" and "reuse target 10" that the
  revision does not contain.
- **M5** — "none recorded in the output" asserts the contents of an image the
  note says was never inspected.

### Low

Four: "Actions pinned by commit" overstates the LVA workflow (four actions are
major-version tags); UID 1000 is a default, not a hardcode; a pi-gen tag is
described as a published image; "blocked" should carry F04's "pending maintainer
clarification".

## R07 — alternative board screen, revision 2

**Verdict: minor revision.** Every pin-table claim re-retrieved matched, the
withdrawn pull-up inference was correctly withdrawn, and the "3B image-only table"
claim is exactly right (three PNGs).

### High

**H-1 — the revision deletes card-required dimensions and then claims to compare
power.** Line 180 says the screen "compares all the signals a HAT needs — I2S,
MCLK, I2C, SPI, a GPIO at 11, **and power**". There is no power column. Revision
1's sourced power-input, maintained-OS/kernel and maintenance columns were removed
without a note, as was the onboarding/identity/recovery trap — both required by
`docs/work/cards/R07.md` and by `docs/evidence.md`. The finding table still marks
R07-6 as addressed. *Correction:* restore one sourced column and one bullet, or
declare the deferral in the table rather than marking the finding done.

### Medium

- **M-1** — Orange Pi Zero 2W is still excluded as "not a HAT candidate on current
  evidence" while the same cell rates the I2S routing `U`; `devices.md` renders
  this revision as "'not demonstrated', which is not 'not usable'".
- **M-2** — "No board in this screen has a Pi ID bus" generalises from three read
  tables to six boards, two of which are `U`.
- **M-3** — the "Libre kernel 6.18.68" correction cites a forum topic that contains
  no mention of 6.18.68, Alta or Solitude.

### Low

Seven, including: the $15 launch-price correction omits the Radxa Zero 3W figure;
the Zero 2W 24-pin board is said to carry a mic input the source does not state;
a test-result pointer dangles again; the 26-pin alignment is an unstated physical
inference; "None documented" for ROCK 3C reads as "no audio" though it has HDMI;
`docs/README.md`'s row for this note needs authorship as well as wording checked;
a section titled "quoted rather than interpreted" interprets without a label.

**Side observation for the coordinator, not a defect in this note:**
`docs/comparisons/devices.md:103` says header soldering is `U` for the Zero 2W,
but the vendor page states it is not soldered by default. The curated table is
the one that needs correcting there.

## B01 — storage durability

**Verdict: major revision before it informs the recovery design.** The note
separates NAND wear, write abort, retroactive corruption, FTL behaviour,
counterfeit capacity, temperature and supply voltage better than most treatments,
and its account of `fsck` is correct and useful.

### High

**H1 — the Music Assistant container is not on the device.** Line 115 and the
recommendation at 263 are premised on "Music Assistant container, images are
2.2 GB on the device". `device-backup.md` records MA on the household HA host,
`tools/device/lab-pi5/README.md` says the Pi is a client, and `51-power-cap.sh`
disables Docker at boot. *Correction:* make the row conditional on the optional
lab extra and mark the size unverified.

**H2 — an unproven cause becomes "the documented cause".** Lines 78, 245 and 267
call the supply fault "the documented cause/trigger" of the corruption already
seen, while the lab result says "a brownout during a card write is the leading
explanation. It is not proven — no `throttled` bit survived", and the note's own
open questions agree with the lab. This is the most consequential overclaim: it
can turn an inference into "fix the power path" as *the* fix.

**H3 — "filesystem rollback" is redefined as whole-system rollback.** The note
concludes that no-intervention rollback "is only achievable as an A/B slot
switch". That contradicts the project's stated ordering — filesystem rollback
first because it works live without user intervention, imaging last — and it
collapses the same-card / off-device / rescue split the B01 card requires. Its own
table lists btrfs snapshot rollback as a real rollback, then the summary denies a
same-card snapshot can be one. *Correction:* A/B is the only automatic *whole-OS*
fallback; file-level rollback is a separate, cheaper layer; name which failure
mode each row addresses.

**H4 — the card's acceptance criteria are largely unmet.** No CoW vs incremental
non-CoW comparison (btrfs as a Pi root is explicitly not evaluated), no
source-backed backend decision table, no first-backend recommendation with exit
path, no consistent-capture or live-vs-offline restore analysis, no minimum-card
sizing against the recorded 5.7 GB root (the A/B example uses rpi-image-gen's
512 MB default), no credential-protection analysis although the archive holds
Wi-Fi credentials and SSH host keys and the queued B13 `0644` defect applies, and
no restoration-test design.

### Medium

- **M1** — the journald masking rule is wrong as a general statement: a
  later-named `/etc` drop-in is documented to override a vendor file; masking is
  an alternative, and the repo's local anomaly needs its own explanation.
- **M2** — `raspi-config`'s overlay is labelled `upstream-documented` in the table
  but listed as unverified in the open questions.
- **M3** — the A/B cost example uses a 512 MB system default against a 5.7 GB
  recorded root, understating the card requirement.
- **M4** — the lab hang is attributed to ext4 `errors=remount-ro` without
  evidence; the volatile journal recorded no remount.
- **M5** — "all root changes are lost at reboot" conflates a plain `ro` mount
  (writes fail) with an overlay tmpfs upper (writes appear to succeed).
- **M6** — "the lab device uses 2 GiB zram" is labelled `observed` with no
  repository record found.
- **M7** — "1.1 GB archive" understates the recorded 1.19 GiB / 4.08 GB
  decompressed.
- **M8** — the DAC 2011 paper is attributed to "M. Zheng et al."; the authors are
  Tseng, Grupp and Swanson.
- **M9** — §6's "cost" column is technical, not beginner-facing: no time, money,
  spare card, reader, downtime or risk, and no scheme has a demonstrated restore.

### Low

Five: relatime is simplified; "117 TBW" appears without its arithmetic; "verified
media" does not address the B13 retained-release gap; the SMART cell should keep
its qualifier visible; the summary reads more settled than the status line.

## N01 — Wi-Fi onboarding options, revision 2

**Verdict: major revision.** The central impossibility is genuinely fixed and
three findings are closed, but five are only partly closed and the note now
diverges from the implemented `control/setup/` in its recovery, credential and
security claims. It does not acknowledge that implementation or the separate
setup review that returned changes requested.

### High

**H1 — the "same SSID and passphrase" recovery contract is not what the code
does.** The note says the hotspot returns "with the *same* SSID and passphrase"
so a retry is "one tap rather than a password". `onboarding.py` generates a new
twelve-character password on every `start_hotspot()`, including the failure path,
and rewrites the card note — so the saved credential stops working and the user
must re-read the boot partition. The implementation chose the opposite trade-off.

**H2 — "never writes the PSK to a temporary file" is false.** `nm.py` writes the
keyfile including `psk=` to a `.part` file via `tempfile.mkstemp` in
`/etc/NetworkManager/system-connections`, chmods it `0600`, then renames it. A
crash before the rename leaves a root-only credential file, and the note's copy
map omits exactly that copy.

**H3 — the note still reads as pre-implementation.** It says "no implementation
selected; no hardware touched", but `control/setup/` implements the flow and the
separate review requested changes, including the predictable AP secret with no
expiry, NM SSID corruption, a corrupt saved baseline trusted forever, and no
baseline restore. None of that is cited.

**H4 — "every failure path has a listening surface" is false for AP/bind
failure.** `control/setup/README.md` records that a bind failure takes the AP back
down and leaves a console-only recovery; `start_hotspot()` can fail with no AP at
all.

**H5 — "a card pulled from a half-configured device cannot leak the passphrase" is
false after a successful join.** The first baseline captures
`/etc/NetworkManager/system-connections` and stores it on the card, so the archive
contains the household PSK. The note's own copy-map row says so.

### Medium

- **M1** — Machine A conflates single-radio AP+managed with two physical radios;
  the Comitup row drops its "on one radio" qualifier.
- **M2** — the state table promises a 15-minute timer, pinned channel,
  `debra-address.txt`, mDNS, a boot counter and a Continue button that the
  implementation does not have; its rate limit and `autoconnect-retries` differ.
- **M3** — the cloud-init instance-data row says "Yes" on evidence about
  user-data retention, not `network-config`, which the note's own open questions
  mark unknown.
- **M4** — NetworkManager's SSID byte-list corruption is not acknowledged.
- **M5** — the baseline's missing restore path is not acknowledged.
- **M6** — the generated AP password is passed to `nmcli` in argv, so it is
  briefly in `/proc/<pid>/cmdline`; the note's "never log" claim does not cover it.
- **M7** — "bind to the hotspot interface only" is not enforcement; the code binds
  the AP address and there is no firewall.
- **M8** — "seven-row copy map" is eight rows.
- **M9** — "ran the offline documentation test suite (below)" has no below.

### Low

Six: the hotspot name is `Debra-Setup-<suffix>`, not `Debra-<id>`; the device URL
omits the `:8787` port; "the full device UI is served on the LAN" describes the
separate web prototype; "all pages checked 2026-11-15" conflicts with "per N01"
cells; RFC 6762 §9 is stated more strongly than the RFC does; the handover promise
is conditional on web control being installed.

## Next actions

1. **Correct R01 and B01 before anything quotes them.** They are already quoted:
   `docs/comparisons/devices.md` carries the R01 totals and renders the R07
   revision, so a correction has to land in the note, the curated table and the
   index together.
2. **Re-review R01, B01 and R03 on an independent model** before accepting their
   corrections, because this round shared the authors' model.
3. **Fix the verification apparatus across the set** — dangling test-result
   pointers, claimed-but-absent fixes, and index rows describing earlier
   revisions. One pass, not seven.
4. **Reconcile N01 with `control/setup/`.** The note and the code now describe
   different recovery contracts, and the code is what a device would run.
5. **Re-run the round-1 reviewer's disposition table** once the corrections land,
   so each closed finding is closed against the text rather than against the
   change log.

## What these reviews did not do

No reviewer edited a tracked file, ran a test suite, contacted a device, made a
radio or audio call, or bought anything. Every one noted that it could not verify
its own candidate hash. Prices and stock were checked against live pages on the
same date as the notes, which confirms wording but not that the original reading
was identical. The RP-003610-WP PDF would not fetch in full. ARMv6, device and
power behaviour remain untested throughout.
