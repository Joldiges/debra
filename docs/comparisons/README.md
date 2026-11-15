# Device comparisons

**Draft, 2026-11-15 UTC. Compiled from research handoffs that have not each been
re-checked cell by cell, plus one device test.** It answers "what am I actually
choosing between" with tables, and it is deliberately incomplete where the
evidence is.

| Page | What it holds |
| --- | --- |
| [devices.md](devices.md) | The master table, one row per exact variant, plus the capability and open-question tables |
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
- Not proof that any device works in Debra. One row is `T`; the rest are vendor
  claims or third-party reports.
- Not complete. ReSpeaker Lite, Satellite1, AtomS3R with a voice base, Korvo-2
  and ESP-VoCat are named but not yet filled: their research tasks are queued
  and their rows stay `U` until a sourced report lands.

## Updating it

1. Take a reviewed finding, not a raw worker report.
2. Put the claim in a cell with its label and source, or leave it `U`.
3. Add the source to [sources.md](sources.md) with the date checked.
4. If two sources disagree, keep both cells and say so; do not average them.
