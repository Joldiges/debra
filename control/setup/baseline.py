"""A small, honest first baseline: the configuration, not the whole device.

This is not whole-device recovery and does not pretend to be. It captures the
files that make this device *this device* — its setup state, its hardware choice,
its NetworkManager profiles and its package list — into one timestamped archive
with a manifest, so a later change can be compared against a known point.

Wi-Fi keyfiles are included because they are part of the device's configuration,
and the archive is created 0600. That is still a secret on disk: the archive must
never be copied into Git, a log, or a support bundle.

A file that cannot be read is recorded as skipped and the rest still runs. A
baseline that quietly stopped at the first unreadable keyfile would look complete
while missing the one thing that matters.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path

# Relative to /, in capture order. A missing path is recorded, not fatal: a
# device with no Bluetooth or no Music Assistant is normal.
CAPTURE = (
    "etc/NetworkManager/system-connections",
    "etc/hostname",
    "etc/timezone",
    "etc/wpa_supplicant",
    "var/lib/debra",
)

MAX_BYTES = 32 * 1024 * 1024


class BaselineError(Exception):
    pass


class _Collector:
    def __init__(self, tar, root):
        self.tar = tar
        self.root = Path(root).resolve()
        self.captured, self.skipped, self.total = [], [], 0

    def add(self, path):
        path = Path(path)
        try:
            resolved = path.resolve()
            resolved.relative_to(self.root)
        except (OSError, ValueError):
            self.skipped.append({"path": str(path), "reason": "resolves outside the capture root"})
            return
        if path.is_symlink():
            # Recorded as a symlink; the target is never followed.
            self.tar.addfile(self.tar.gettarinfo(str(path), arcname=str(path.relative_to(self.root))))
            self.captured.append(str(path.relative_to(self.root)))
            return
        if path.is_dir():
            try:
                children = sorted(path.iterdir())
            except OSError as exc:
                self.skipped.append({"path": str(path), "reason": exc.__class__.__name__})
                return
            for child in children:
                self.add(child)
            return
        if not path.is_file():
            return
        try:
            info = path.stat()
        except OSError as exc:
            self.skipped.append({"path": str(path), "reason": exc.__class__.__name__})
            return
        if info.st_size > MAX_BYTES or self.total + info.st_size > MAX_BYTES:
            raise BaselineError(f"baseline would exceed {MAX_BYTES} bytes")
        try:
            self.tar.add(str(path), arcname=str(path.relative_to(self.root)), recursive=False)
        except (OSError, PermissionError) as exc:
            # A root-only keyfile read by a non-root run is the common case.
            self.skipped.append({"path": str(path), "reason": exc.__class__.__name__})
            return
        self.total += info.st_size
        self.captured.append(str(path.relative_to(self.root)))


def capture(destination, paths=CAPTURE, root="/", stamp=None):
    """Write one baseline archive and return its manifest.

    `destination` is a directory. The archive is named by timestamp so repeated
    captures never overwrite each other; nothing is ever pruned here.
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = destination / f"baseline-{stamp}.tar.gz"
    missing = []
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz", compresslevel=6) as tar:
        collector = _Collector(tar, root)
        for relative in paths:
            path = Path(root) / relative
            if not path.exists():
                missing.append(relative)
                continue
            collector.add(path)
    payload = buffer.getvalue()
    if len(payload) > MAX_BYTES:
        raise BaselineError(f"compressed baseline would exceed {MAX_BYTES} bytes")
    manifest = {
        "archive": archive.name,
        "created": stamp,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "captured": collector.captured,
        "skipped": collector.skipped,
        "missing": missing,
        "note": "Configuration baseline, not whole-device recovery. Contains secrets.",
    }
    # Write under a name nothing reads, then rename. A full disk partway through
    # then leaves a .part file, never a final-named archive that looks complete;
    # the manifest is the last thing to appear, so "a manifest exists" means the
    # archive beside it is whole.
    _write(destination / f".baseline-{stamp}.tar.gz.part", payload)
    _write(destination / f".baseline-{stamp}.json.part",
           (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    os.replace(destination / f".baseline-{stamp}.tar.gz.part", archive)
    os.replace(destination / f".baseline-{stamp}.json.part",
               destination / f"baseline-{stamp}.json")
    return manifest


def _write(path, payload):
    """Write one owner-only file and flush it to disk, or leave nothing."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    return path


def latest(destination):
    """The most recent manifest, or None. Used to say whether a baseline exists."""
    destination = Path(destination)
    if not destination.is_dir():
        return None
    manifests = sorted(destination.glob("baseline-*.json"))
    if not manifests:
        return None
    try:
        return json.loads(manifests[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
