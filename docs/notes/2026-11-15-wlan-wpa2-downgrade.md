# The household SSID is now WPA2-only, 2.4 + 5 GHz

**2026-11-15 — a live change to `Oldiges WiFi`, made with James's explicit
approval** ("Downgrade the main SSID"), to unblock the first Zero 2 W join. This
note exists so the change is not silent: it alters the household network for
every wireless client, not just the test board.

Author: OpenCode session, `openrouter/deepseek/deepseek-v4.1-flash-1017`, variant
not exposed by the host. Applied through the UniFi MCP tools.

## Before → after

| Field | Before | After |
| --- | --- | --- |
| `wpa3_support` | `true` | `false` |
| `wpa3_transition` | `true` | `false` |
| `pmf_mode` | `optional` | `disabled` |
| `wlan_bands` | `["2g","5g","6g"]` | `["2g","5g"]` |

Unchanged: `security: wpapsk`, `wpa_mode: wpa2`, `wpa_enc: ccmp`, `enabled`,
`hide_ssid: false`, `no2ghz_oui: true`, `mac_filter_enabled: false`, on network
`Default` (`69a4ebf9dd8c8150c4dee2f6`). Read back after the write: all four
fields persisted, nothing dropped.

## Why all four fields, in one write

The first attempt set only the three WPA3 fields and was rejected whole:

```
400: api.err.Wpa3MandatoryFor6GHzBand
```

6 GHz requires WPA3, so WPA3 cannot be removed while the SSID still advertises
6 GHz. Bands and security therefore had to change together, which is why this is
a real downgrade of the household SSID rather than a security tweak. Every
6 GHz-capable client now associates on 5 GHz, and every client negotiates WPA2.

## Consequence for the Zero 2 W

This addresses the documented failure in
[raspberrypi/linux#7634](https://github.com/raspberrypi/linux/issues/7634):
NetworkManager 1.52.1 on trixie selects SAE against a transition-mode AP, the
BCM43430 cannot complete it, and there is no client-side opt-out in that build —
so `key-mgmt wpa-psk` in the profile did not help. With the AP no longer offering
SAE, that path is not available to select.

Whether the join now succeeds is **not yet known**. If it still fails, the
remaining named suspect is the `wpasupplicant 2:2.10-24+rpt3` regression in
[raspberrypi/trixie-feedback#107](https://github.com/raspberrypi/trixie-feedback/issues/107),
which affects the same board independently of the AP's security mode.

## Reverting

Set `wlan_bands` back to `["2g","5g","6g"]` and `wpa3_support`/`wpa3_transition`
to `true`, `pmf_mode` to `optional`. Bands and security can be restored in one
write for the same reason they had to change together. No other field was
touched, so no other value needs remembering.

## Result

The join then succeeded: the board appeared at `192.168.0.99` as
`debra-lab.local` with key-only SSH, and `wpasupplicant 2:2.10-24+rpt3` was
present throughout without blocking it. See the
[first-join record](../testing/results/2026-11-15-zero2w-first-join.md).

## Unresolved detail

`no2ghz_oui` is `true` and was left alone. What that setting actually filters is
not established in this session; it is recorded here only so that a later 2.4 GHz
failure on this SSID is not investigated from scratch.
