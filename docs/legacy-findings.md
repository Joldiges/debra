# Legacy investigation leads

Read-only review of selected files at Git commit **`bc81d9b`**
(`2026-01-11`, subject `Bleg`), performed 2026-11-14.
Author: OpenCode, `openai/gpt-6.1-sol`; variant not exposed.

These observations are from code, not from running it. Nothing here establishes
a working image, a successful build, or supported hardware. The fresh-start
plan may replace all of these implementations.

Recover a historical source without restoring/deleting working files:

```bash
git show bc81d9b:scripts/debra-setup.sh
```

## Findings to investigate

| Historical source | Observed implementation | Useful follow-up |
| --- | --- | --- |
| `scripts/debra-setup.sh` | Root-run sequential modules: prerequisites, hostname, updates, audio, ReSpeaker, Snapcast, SendSpin, LVA, finish/reboot. | Recover integration requirements, not the assumption that every component should share one privileged installer. |
| `scripts/lib/common.sh` | Derives `PROJECT_ROOT` from Git in the caller's working directory when possible; hostname is `debra-` plus a six-hex ID. | Do not accidentally select an unrelated repository when invoked outside Debra. Preserve the idea of repeatable identity, but define collision and failure behavior. |
| `scripts/python/get_unique_id.py` | SHA-256 of first available Pi serial, CPU serial, DMI UUID, machine-id, or MAC; falls back to literal `unknown`. | Hardware-backed identity is a useful lead. A cloned machine-id, unstable interface selection, or common `unknown` fallback cannot guarantee unique/stable boards; test failure and clone cases. |
| `scripts/modules/55_respeaker.sh` | Separates ReSpeaker V1/V2. V1 uses a kernel-version branch of HinTak/seeed-voicecard, invokes installation twice as an acknowledged workaround, and attempts kernel holds. V2 compiles/installs a device-tree overlay. | Exact revision/kernel/overlay coupling matters. The second install is explicitly unverified; do not encode it as a universal requirement. Verify current vendor/upstream paths. |
| `scripts/modules/65_sendspin.sh` | Installs Python 3.13/FFmpeg/build dependencies, downloads an unpinned upstream installer, and modifies its install command on ARMv6 to use local wheels/piwheels. | Establish the actual present dependency chain and trustworthy artifact sources. An installer text rewrite is brittle; no proof that those wheels solve runtime compatibility. |
| `legacy/wheelbuilder/Dockerfile` | Bootstraps a Raspbian `trixie` armhf rootfs, uses QEMU `arm1176`, and includes native/Rust build tools. Foreign bootstrap uses `--no-check-gpg`. | Cross/emulated build environment is a lead for ARMv6 work, not a verified reproducible or secure supply chain. Restore package-signature verification and audit artifact provenance before reuse. |
| `legacy/tflitebuilder/tfbuild.sh` | Tries TensorFlow Lite C `v2.14.0` with ARMv6/VFP hard-float flags and XNNPACK disabled; gives a Python-3.13-specific destination for a shared library. | Determine the current wake runtime ABI and actual CPU instruction requirements. Inspect/load/run on real ARMv6; successful compilation or `file` output alone is insufficient. |
| `scripts/modules/70_linux_voice_assistant.sh` | Uses `/opt/debra`, an unpinned upstream clone, Python venv, PipeWire/user systemd services, and lingering. Contains repeated pulls and older audio CLI flags. | Recheck current CLI/API, service ownership, runtime dependencies, boot-without-login behavior, and audio-session policy. Do not transplant obsolete flags or assume the user service is healthy. |

## What the old material cannot tell us

- Whether any listed ARMv6 binary was successfully exercised with microphone,
  wake model, voice streaming, and simultaneous music.
- Which exact board/HAT/kernel combination was reliable.
- Whether first-boot network setup, stack coexistence, or restore was tested.
- Whether committed binary artifacts have reproducible builds and complete
  redistribution rights.

The old README retains hardware links and historical prices as research leads.
Its support tables and availability statements need fresh sources.

## Existing backup scripts

The working-tree `backups/backup.sh` and `backups/restore.sh` use
`sudo rsync -aAXv --delete` in opposite directions between `/` and
`/mnt/backup/`. They construct a command with `eval`, print a success message
unconditionally, and do not establish mount identity or consistent snapshots.
Their exclusion list omits `/root/*`, users' `.ssh` contents, and
`/home/*/git/*`, among other state.

Do not run them to validate this project or declare them a recovery path.
Recovery work must first use isolated fixtures/disposable media, then a
specifically authorized device with a demonstrated restore procedure.
