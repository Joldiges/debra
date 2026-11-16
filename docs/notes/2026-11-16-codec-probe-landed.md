---
title: The codec probe landed, and the I2C bus is not readable from the page
date: 2026-11-16
type: note
status: unreviewed
kind: observation
author: OpenCode session
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - "Pi 5 `debra-3c6b3f`, Pi Zero 2 W `debra-8518d6`, Pi Zero W `debra-f943dc`, read 2026-11-16"
  - "/sys/bus/i2c/devices/*, /proc/asound/cards on all three boards"
  - "docs/notes/2026-11-16-hat-identification-evidence.md (the earlier evidence)"
---

# The codec probe landed, and the I2C bus is not readable from the page

## What was added

`control/web/hats.py` now carries a `codec` name per board and a
`probe_codec(devices, cards)` function; `server.py` reads
`/sys/bus/i2c/devices/*` and reports the result as `hardware.codec` in the status
payload and `codec` in the Setup payload. It is read-only and pure: the sysfs
read happens in the caller, and the function decides between five states.

| State | Meaning | What it needs |
| --- | --- | --- |
| `bound` | a known codec has its driver bound and its sound card is listed | nothing; the driver works |
| `no_card` | driver bound, no card with that name listed | the ASoC card did not register |
| `present` | the I2C device exists with no driver bound | the module is not loaded or absent |
| `none` | no codec this table knows is configured | nothing to act on here |
| `unknown` | the kernel directory could not be read | nothing can be said |

Measured on the three lab boards on the same day, all `bound`:

- Pi 5 and Zero W: `tlv320aic3104` at `0x18`, driver `tlv320aic3x`, card
  `seeed2micvoicec`, consistent with the ReSpeaker 2-Mics **v2**.
- Zero 2 W: `wm8960` at `0x1a`, driver `wm8960`, card `wm8960soundcard`,
  consistent with the Seeed **v1** HAT **or** the Waveshare WM8960 — the codec
  does not say which, so the payload lists both rather than picking one.

## The correction this note exists to record

Earlier the same day I said a codec would "ACK its address whether or not a
driver is bound, as long as `i2c_arm` is on", and that the page could therefore
distinguish *board fitted, overlay missing* from *no board*. **That is not
available on these images.** `i2c_arm` is on and the bus is running, but
`i2c-dev` is not loaded, so there is no `/dev/i2c-*` and no userspace way to
address a chip. Adding it would mean loading a module and installing tooling on
the device — a boot change, which is not a read-only probe.

So the honest claim is narrower than the one I made:

- `present` is a real and useful state: a device-tree node with no driver means
  the boot configuration describes a codec and nothing drives it.
- `none` is **not** "no board fitted". A fitted board with no overlay configured
  leaves no trace in sysfs, exactly as an empty header does.
- What the probe does establish is the codec family, which is the fact the
  EEPROM could not give: all three boards have no HAT EEPROM at all.

## Verification

Offline: `tests/test_hat_install.py` (pure-function states, including that an
unreadable list is not reported as an absence), `tests/test_web_setup.py` (the
sysfs reader through a fixture root, and that an unrelated `mcp23017` is not an
audio codec), `tests/test_web.py` (the status payload), and one browser check
that the page shows the codec beside the EEPROM line and does not turn `none`
into "no board".

On the devices: all three serve release
`f02e89727cec3990f233bfd82ec6db307aa765d93f993a570696f75039415bd5` with
`hats.py`, `server.py` and `assets/app.js` byte-identical to the committed files,
and `/api/status` and `/api/setup` both report the codec above.

## Still open

- Seeed v1 and Waveshare WM8960 remain indistinguishable; only the person knows
  which board they bought, which is why the page keeps them as two rows.
- A codec this table does not know reads as `none`, not as "unrecognised". That
  is a real limitation for a new HAT, and the note on the page says the state is
  about configuration rather than hardware presence.
- No revision is established for any board: the codec names a part, not a vendor
  or a model.
