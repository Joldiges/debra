# Device comparisons

**Draft, 2026-11-15 UTC. Compiled from research handoffs that have not each been
re-checked cell by cell, plus one device test.** It answers "what am I actually
choosing between" with tables, and it is deliberately incomplete where the
evidence is.

**These tables are not buying guidance yet.** This page said its R02, R04, R07 and
N01 rows inherit the findings of the
[independent review](../notes/2026-11-15-research-notes-review.md), which asked for
major revision before any purchase or shortlisting decision. Each of those four
notes now has a revision 2 that answers the review, and each revision is itself
unreviewed:

| Said before, 2026-11-15 | Corrected | Support |
| --- | --- | --- |
| Complete costs are not established | Dated listed totals with named exclusions; total A is a floor, not a price | [R02 revision 2](../notes/2026-11-15-complete-alternatives-comparison-revision.md) |
| Some exclusions are stronger than their sources | "Not documented in the source checked" replaces "absent"; every price ranking is removed | [R07 revision 2](../notes/2026-11-15-alternative-board-screen-revision.md) |
| N01's onboarding flow is "internally impossible on one radio" | Only the stop-hotspot-then-show-the-address sequence is impossible; one radio is the chosen flow | [N01 revision 2](../notes/2026-11-15-wifi-onboarding-options-revision.md) |
| The implied reading: onboarding needs two radios | Machine A is an optional concurrent mode, untested `U` on every Debra board | [N01 revision 2](../notes/2026-11-15-wifi-onboarding-options-revision.md) |
| R04's reuse, boot and image verdicts stand as first written | Restated at the strength of the pinned sources; no table here draws on it | [R04 revision 2](../notes/2026-11-15-upstream-reuse-audit-revision.md) |

That N01 revision also replaces the "credentials live only in NetworkManager
keyfiles" claim with a copy map, and makes the WLAN country a builder input. The
transport control rows come from
[R03](../notes/2026-11-15-music-transport-and-control-map.md), which is unreviewed.

| Page | What it holds |
| --- | --- |
| [devices.md](devices.md) | Buying table, cost totals, board HAT screen, master device table, capability summary and open questions |
| [music-playback.md](music-playback.md) | The detail behind every `Music playback` cell: transport, version gate, stream format, and what the server has to run |
| [sources.md](sources.md) | The numbered source register; a `[S#]` with no entry here is a bug |

Conventions and label meanings live in [evidence.md](../evidence.md). The short
version, used in every cell:

| Tag | Meaning |
| --- | --- |
| `D` | upstream-documented — a linked primary source states it; Debra has not reproduced it |
| `R` | reported — a linked third-party report or attributed observation, with its limits |
| `T` | tested — a linked Debra test record names the hardware, versions and result |
| `H` | hypothesis — an inference, not a capability claim |
| `U` | unknown — not established; an empty cell is never "no" |

A cell reads `value [S1 D]` or `value [T]` for our own measurements. Prices
always carry currency, market, seller and the date checked.

## What this page is not

- Not a buying recommendation. Price and availability cells are snapshots from
  the date shown and move.
- Not proof that any device works in Debra. One row is `T`; other rows carry `D`,
  `R`, `H` and `U`, and both ReSpeaker Lite rows are `H` pending a re-run.
- Not complete. This page listed ReSpeaker Lite, Satellite1, AtomS3R with a voice
  base, Korvo-2 and ESP-VoCat as "named but not yet filled". Satellite1 is now
  filled from the [S10]–[S19] report; ReSpeaker Lite is `H` awaiting `CMP02B`; the
  other three stay `U` in [devices.md](devices.md).

## Updating it

1. Take a reviewed finding, not a raw worker report.
2. Put the claim in a cell with its label and source, or leave it `U`.
3. Add the source to [sources.md](sources.md) with the date checked.
4. If two sources disagree, keep both cells and say so; do not average them.
