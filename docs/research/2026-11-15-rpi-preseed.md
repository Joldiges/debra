# rpi-preseed: is it time to replace cloud-init?

**Research result, not a device test, 2026-11-15.** Nothing was installed, no card
was written and no Pi was contacted. Produced by the unattended runner as task
`N06`; kept here because the raw working file was in a temporary directory.

The question matters because Debra's first-boot story is currently cloud-init,
and the lab Pi's 2026-11-15 provisioning failed in a way that looked like
cloud-init never being consumed. If Raspberry Pi's own TOML-based customiser
worked on the image Debra already uses, it would be simpler and deterministic.

## The answer

**Keep cloud-init now. Do not adopt rpi-preseed yet. Wait for an image that ships
it.** Three facts decide it:

| Fact | Status | Source |
| --- | --- | --- |
| `rpi-preseed` is a real, Raspberry Pi Ltd project, Apache-2.0, Debian maintainer "Raspberry Pi OS Team" | `upstream-documented` | [S1][S4][S14] |
| It describes itself as a **prototype, "not yet production-hardened"**; the binary says `0.2.1-prototype`; 0.1.0's changelog entry is still UNRELEASED; there are no git tags | `upstream-documented` | [S1][S6][S13] |
| **No current Raspberry Pi OS image advertises it.** The Imager only offers the format when the image manifest sets `init_format: "rpi-preseed"`, and every 2026-10-06 image is `cloudinit-rpi` or `systemd` | `upstream-documented` | [S7][S9] |

So the format is promising and unusable today: dropping a TOML on a stock Trixie
card does nothing, because the package is not in the image and cloud-init ignores
a file it does not know.

## What it is, precisely

| Item | Value |
| --- | --- |
| Format | one TOML file at the root of the FAT boot partition, `/boot/firmware/rpi-preseed.toml` (legacy `/boot/rpi-preseed.toml`), override with `rpi_preseed.config=` on the kernel cmdline |
| Schema | `config_version` "MAJOR.MINOR" is required; unknown keys are warned and skipped; only `\\` and `\"` escapes; single-line strings; up to config 1.1, and Imager writes 1.0 |
| Keys | `[system] hostname`; `[user] name, password, password_encrypted, passwordless_sudo, groups`; `[ssh] enabled, authorized_keys, ssh_import_id, password_authentication`; `[wlan] ssid, ssid_hex, password, hidden, country, key_mgmt`; `[locale] lang, locales, keymap, timezone` |
| Re-apply | no. Units are gated on stamps in `/var/lib/rpi-preseed`; an edited config only logs a warning until `rpi-preseed apply` |
| Secrets | the TOML's `password`/`token` values are overwritten in place with `<redacted by rpi-preseed>` **after a successful apply**; a read-only boot partition skips redaction |
| Imager support | 2.0.11 and later (2.0.11.1, 2.0.12). 2.0.10 and all 1.x lack it |
| Coexistence | the package declares `Conflicts: cloud-init`, so installing it removes cloud-init |

## Traps

- **A cloud-init-shaped file is silently ignored.** The key is `[ssh] enabled`,
  not cloud-init's `enable_ssh`. A plausible-looking file does nothing.
- **`apt install rpi-preseed` removes cloud-init** while Imager keeps writing
  unused `user-data` — strictly worse than today, not a partial migration.
- **It has to be baked into the image.** Installing it after first boot is too
  late; the unit has already run.
- **Plaintext on the FAT card until first boot.** Redaction only follows a
  successful apply, so a card that never boots keeps the Wi-Fi passphrase in the
  clear. That is the same exposure cloud-init has, and it is worth stating for
  Debra's images rather than assuming either tool fixes it.
- **An old Imager on a future preseed image** assumes `systemd` and writes
  `firstrun.sh`, which the image would ignore.

## What would change the decision

One of:

- `init_format: "rpi-preseed"` appearing in Raspberry Pi's image manifest, or
- a Raspberry Pi OS release note shipping 0.2.x, or
- upstream leaving prototype status with a tagged release.

**Next bounded check:** re-fetch the manifest and grep for `rpi-preseed`. If it
appears, run upstream's `make qemu-check SCENARIO=00-happy-path` on a scratch
image — no card, no device — before any Debra change.

## What this does not say

- It does not say cloud-init is working. Debra's 2026-11-15 provisioning failure
  is unexplained, and the same "file silently not consumed" shape would look
  identical. Verify by inspecting the mounted card and by a control flash with
  the vendor AppImage, not by assumption.
- No hardware test exists on any Debra target board; upstream's QEMU suite covers
  Pi OS Lite arm64 only.
- Whether the community Flatpak build exposes the format is unverified.

## Sources

| Key | Source | URL |
| --- | --- | --- |
| S1 | rpi-preseed repository | https://github.com/raspberrypi/rpi-preseed |
| S2 | rpi-preseed schema | https://raw.githubusercontent.com/raspberrypi/rpi-preseed/main/schema/rpi-preseed.schema |
| S3 | `rpi-preseed(5)` manual | https://raw.githubusercontent.com/raspberrypi/rpi-preseed/main/doc/rpi-preseed.5 |
| S4 | Debian `control` (declares `Conflicts: cloud-init`) | https://raw.githubusercontent.com/raspberrypi/rpi-preseed/main/debian/control |
| S5 | `rpi-preseed.service` unit | https://raw.githubusercontent.com/raspberrypi/rpi-preseed/main/systemd/rpi-preseed.service |
| S6 | `src/rpi-preseed` | https://raw.githubusercontent.com/raspberrypi/rpi-preseed/main/src/rpi-preseed |
| S7 | rpi-imager — OS customisation formats | https://raw.githubusercontent.com/raspberrypi/rpi-imager/main/doc/os_customisation_formats.md |
| S8 | rpi-imager v2.0.11 release | https://github.com/raspberrypi/rpi-imager/releases/tag/v2.0.11 |
| S9 | Raspberry Pi image manifest | https://downloads.raspberrypi.com/os_list_imagingutility_v4.json |
| S10 | Raspberry Pi — cloud-init on Raspberry Pi OS | https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/ |
| S11 | Trixie `main/arm64` package index | https://archive.raspberrypi.com/debian/dists/trixie/main/binary-arm64/Packages.gz |
| S12 | rpi-imager PR 1659 | https://github.com/raspberrypi/rpi-imager/pull/1659 |
| S13 | rpi-preseed changelog | https://raw.githubusercontent.com/raspberrypi/rpi-preseed/main/debian/changelog |
| S14 | rpi-preseed copyright | https://raw.githubusercontent.com/raspberrypi/rpi-preseed/main/debian/copyright |
| S15 | rpi-imager v2.0.12 release | https://github.com/raspberrypi/rpi-imager/releases/tag/v2.0.12 |

All read 2026-11-15. These keys are local to this note; the comparison register
in [../comparisons/sources.md](../comparisons/sources.md) is a separate numbering
for device claims.
