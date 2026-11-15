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
import secrets
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
    def __init__(self, tar, root, exclude=None):
        self.tar = tar
        self.root = Path(root).resolve()
        # The directory this baseline is being written into. Without it, a
        # capture of var/lib/debra archives the previous baselines, so each
        # retry is bigger than the last until the size cap fails for ever.
        self.exclude = Path(exclude).resolve() if exclude else None
        self.captured, self.skipped, self.total = [], [], 0

    def add(self, path):
        path = Path(path)
        try:
            resolved = path.resolve()
            resolved.relative_to(self.root)
        except (OSError, ValueError):
            self.skipped.append({"path": str(path), "reason": "resolves outside the capture root"})
            return
        if self.exclude is not None:
            try:
                resolved.relative_to(self.exclude)
                self.skipped.append({"path": str(path.relative_to(self.root)),
                                     "reason": "this baseline's own directory"})
                return
            except ValueError:
                pass
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
        # Read the whole file before touching the tar stream. `tar.add()` writes
        # the header and part of the body before a read can fail, and catching
        # that failure left a truncated member in the archive that every later
        # member was unreachable behind. A file that cannot be read is skipped
        # without mutating the stream at all.
        #
        # The metadata comes from the descriptor that was read, never from a
        # second `stat` of the path. Asking `gettarinfo()` to stat again left a
        # window in which a writer could truncate the file between the size
        # check and the header: the archive then held the old buffer with the
        # new, shorter size, so the member was silently cut and reported
        # captured.
        try:
            with open(path, "rb") as stream:
                info = os.fstat(stream.fileno())
                if info.st_size > MAX_BYTES or self.total + info.st_size > MAX_BYTES:
                    raise BaselineError(f"baseline would exceed {MAX_BYTES} bytes")
                chunks, size = [], 0
                while True:
                    chunk = stream.read(1 << 20)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise BaselineError(f"baseline would exceed {MAX_BYTES} bytes")
                    chunks.append(chunk)
        except OSError as exc:
            # A root-only keyfile read by a non-root run is the common case.
            self.skipped.append({"path": str(path),
                                 "reason": exc.__class__.__name__})
            return
        data = b"".join(chunks)
        if len(data) != info.st_size:
            # The file changed while it was being read. Recording it would put
            # a size in the header that the body does not fill.
            self.skipped.append({"path": str(path.relative_to(self.root)),
                                 "reason": "changed while being read"})
            return
        if self.total + len(data) > MAX_BYTES:
            raise BaselineError(f"baseline would exceed {MAX_BYTES} bytes")
        member = tarfile.TarInfo(str(path.relative_to(self.root)))
        member.size = len(data)
        member.mtime = int(info.st_mtime)
        member.mode = 0o600 if info.st_mode & 0o077 == 0 else 0o644
        member.uid = member.gid = 0
        member.uname = member.gname = "root"
        self.tar.addfile(member, io.BytesIO(data))
        self.total += len(data)
        self.captured.append(str(path.relative_to(self.root)))


def capture(destination, paths=CAPTURE, root="/", stamp=None):
    """Write one baseline archive and return its manifest.

    `destination` is a directory. The archive is named by timestamp so repeated
    captures never overwrite each other; nothing is ever pruned here.
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    missing = []
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz", compresslevel=6) as tar:
        collector = _Collector(tar, root, exclude=destination)
        for relative in paths:
            path = Path(root) / relative
            if not path.exists():
                missing.append(relative)
                continue
            collector.add(path)
    payload = buffer.getvalue()
    if len(payload) > MAX_BYTES:
        raise BaselineError(f"compressed baseline would exceed {MAX_BYTES} bytes")
    # One-second timestamps are not unique. A same-second retry, or two
    # captures racing, must not overwrite the earlier baseline: an old manifest
    # left beside a new archive is a backup that reports the wrong hash.
    stem = _unique_stem(destination, f"baseline-{stamp}")
    archive_name, manifest_name = f"{stem}.tar.gz", f"{stem}.json"
    manifest = {
        "archive": archive_name,
        "created": stamp,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "captured": collector.captured,
        "skipped": collector.skipped,
        "missing": missing,
        "note": "Configuration baseline, not whole-device recovery. Contains secrets.",
    }
    # Each file is written under a name nothing reads, flushed, and then linked
    # to its final name. `os.link` refuses to replace an existing file, so a
    # baseline is never overwritten, and the final name only ever refers to a
    # complete file. The manifest is published last, so "a manifest exists"
    # means the archive beside it was already whole.
    token = secrets.token_hex(4)
    _publish(destination, archive_name, payload, token)
    try:
        _publish(destination, manifest_name,
                 (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode("utf-8"),
                 token)
    except BaseException:
        # Never leave an archive with no manifest: `latest()` would ignore it and
        # a later retry would capture again on top of unexplained files.
        try:
            os.unlink(destination / archive_name)
        except OSError:
            pass
        raise
    _fsync_dir(destination)
    return manifest


def _unique_stem(destination, stem):
    """A name nothing in the directory already uses."""
    candidate, index = stem, 0
    while ((destination / f"{candidate}.tar.gz").exists()
           or (destination / f"{candidate}.json").exists()):
        index += 1
        candidate = f"{stem}-{index}"
    return candidate


def _publish(destination, name, payload, token):
    """Put one file at its final name without ever replacing an existing one."""
    part = destination / f".{name}.{token}.part"
    _write(part, payload)
    try:
        os.link(part, destination / name)
    finally:
        try:
            os.unlink(part)
        except OSError:
            pass
    return destination / name


def _fsync_dir(directory):
    """Make the new names durable, not just the file contents."""
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


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


def verified(destination, archive):
    """The manifest for one specific archive, or None if it does not verify.

    `latest()` answers "what is the best baseline here"; a saved pointer answers
    "what did this device record". They must not disagree: a pointer to an empty
    or truncated file used to be trusted because the path existed, so the page
    reported a recovery point that `latest()` already knew was unusable.
    """
    destination = Path(destination)
    archive = Path(archive)
    if not archive.is_file():
        return None
    try:
        manifest = json.loads(
            archive.with_suffix("").with_suffix(".json").read_text(encoding="utf-8"))
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    except (OSError, ValueError):
        return None
    if not isinstance(manifest, dict) or manifest.get("archive") != archive.name:
        return None
    if digest != manifest.get("sha256"):
        return None
    return manifest


def latest(destination):
    """The most recent usable manifest, or None.

    A manifest is only a baseline if the archive beside it exists and still
    hashes to what the manifest says. Without that check a damaged or
    half-written archive is reported as the device's known-good point.
    """
    destination = Path(destination)
    if not destination.is_dir():
        return None
    # Order by when each manifest was published, not by its name. A same-second
    # collision gets a "-1" suffix, and "-" sorts before ".", so name order
    # reports the older baseline as the newest.
    found = []
    for path in destination.glob("baseline-*.json"):
        try:
            found.append((path.stat().st_mtime_ns, path.name, path))
        except OSError:
            continue
    for _, _, path in sorted(found, reverse=True):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            archive = destination / manifest["archive"]
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if digest == manifest.get("sha256"):
            return manifest
    return None
