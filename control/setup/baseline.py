"""A small, honest first baseline: the configuration, not the whole device.

This is not whole-device recovery and does not pretend to be. It captures the
files that make this device *this device* — its NetworkManager profiles and the
few small system files in `CAPTURE` — into one timestamped archive with a
manifest, so a later change can be compared against a known point. Two things
are deliberately left out (see `NEVER_CAPTURE`): the setup service's own state
directory, which holds the setup-network password and the chosen mode, and the
setup network's own access-point profile, which holds the same password a second
time. It captures no package list and builds no hardware inventory; a path that
does not exist is recorded as missing rather than produced.

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
import re
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

# Paths that are never captured, whatever CAPTURE says. Both are the setup
# network's password, which must not travel in an archive that gets copied to a
# laptop and attached to a report:
#
# - `var/lib/debra/setup` holds it in an owner-only file (and the chosen mode);
#   it is inside `var/lib/debra`, which is captured because the rest of that
#   directory is device configuration worth recovering.
# - the access point's own NetworkManager profile holds the same password as
#   `psk=` while the access point is up, and `etc/NetworkManager/
#   system-connections` is captured in full. The join deletes the access point
#   before it captures, so this only matters after a power loss mid-raise - which
#   is exactly when a baseline is taken on the next boot.
NEVER_CAPTURE = (
    (Path("var/lib/debra/setup"), "the setup service's own state directory"),
    (Path("etc/NetworkManager/system-connections/debra-setup.nmconnection"),
     "the setup network's own access-point profile"),
)

MAX_BYTES = 32 * 1024 * 1024


class BaselineError(Exception):
    pass


class _Changed(Exception):
    """The source file changed while it was being read."""


def _same_file(before, after):
    """Whether two descriptor snapshots describe an unchanged file.

    Size, modification and status-change times, inode and device: a same-size
    rewrite moves the mtime and ctime, which a length check could not see.
    Best effort by design - a writer that also restores the timestamps is not
    detected, and nothing here is a transactional snapshot across files.
    """
    return (before.st_size == after.st_size
            and before.st_mtime_ns == after.st_mtime_ns
            and before.st_ctime_ns == after.st_ctime_ns
            and before.st_ino == after.st_ino
            and before.st_dev == after.st_dev)


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
            relative = resolved.relative_to(self.root)
        except (OSError, ValueError):
            self.skipped.append({"path": str(path), "reason": "resolves outside the capture root"})
            return
        for private, reason in NEVER_CAPTURE:
            if relative == private or private in relative.parents:
                # The reason travels with the entry, so a manifest somebody
                # inspects says which credential was held back and why.
                self.skipped.append({"path": str(relative), "reason": reason})
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
            data, info = self._read(path)
        except OSError as exc:
            # A root-only keyfile read by a non-root run is the common case.
            self.skipped.append({"path": str(path),
                                 "reason": exc.__class__.__name__})
            return
        except _Changed:
            # The file changed while it was being read. Recording it would put
            # bytes in the archive that never all existed at once - a torn
            # configuration - and the matching hash would then call it verified.
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

    def _read(self, path):
        """Read a file and return its bytes only if it did not change.

        Reading the whole file before touching the tar stream keeps a failed
        read from leaving a truncated member. Metadata is taken from the
        descriptor that was read, never from a second `stat` of the path, so a
        truncation between the read and the header cannot produce a cut member.

        The metadata is compared again after the read. A length check alone
        missed a same-size in-place rewrite: the saved bytes could be the first
        half from before the write and the second half from after, which is a
        configuration that never existed. A changed file is skipped rather than
        retried: a baseline is a point in time, and the next boot captures again.
        """
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
            after = os.fstat(stream.fileno())
        data = b"".join(chunks)
        if len(data) != info.st_size or not _same_file(info, after):
            raise _Changed()
        return data, info


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


ARCHIVE_NAME = re.compile(r"\Abaseline-[0-9A-Za-z-]+\.tar\.gz\Z")
DIGEST = re.compile(r"\A[0-9a-f]{64}\Z")
MANIFEST_KEYS = frozenset({"archive", "created", "sha256", "bytes", "captured",
                           "skipped", "missing", "note"})


def _manifest_for(destination, manifest_path):
    """Read and fully validate one manifest, or return None.

    A hash proves only that the archive matches the metadata beside it. It does
    not prove the metadata describes a Debra baseline: a two-key JSON object
    pointing at an unrelated file matched the old check. This validates the
    manifest's own shape, that the archive is a direct child of this baseline
    directory with the generated name, that its size and digest agree, that it
    opens as a gzip tar, and that the members it claims to have recorded are
    actually in it.
    """
    destination = Path(destination)
    manifest_path = Path(manifest_path)
    if manifest_path.is_symlink() or not manifest_path.is_file():
        return None
    if manifest_path.parent.resolve() != destination.resolve():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS:
        return None
    archive_name = manifest.get("archive")
    if not isinstance(archive_name, str) or not ARCHIVE_NAME.match(archive_name):
        return None
    stem = archive_name[:-len(".tar.gz")]
    if manifest_path.name != stem + ".json":
        return None
    if not isinstance(manifest.get("created"), str) or len(manifest["created"]) > 64:
        return None
    if not isinstance(manifest.get("note"), str) or len(manifest["note"]) > 500:
        return None
    digest = manifest.get("sha256")
    if not isinstance(digest, str) or not DIGEST.match(digest):
        return None
    size = manifest.get("bytes")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        return None
    captured = manifest.get("captured")
    if not isinstance(captured, list) or not all(isinstance(name, str) for name in captured):
        return None
    for key in ("skipped", "missing"):
        if not isinstance(manifest.get(key), list):
            return None
    archive = destination / archive_name
    if archive.is_symlink() or not archive.is_file():
        return None
    try:
        if archive.parent.resolve() != destination.resolve():
            return None
        if archive.stat().st_size != size:
            return None
        if hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
            return None
    except OSError:
        return None
    try:
        with tarfile.open(archive, "r:gz") as tar:
            members = {member.name for member in tar.getmembers()}
    except (OSError, tarfile.TarError):
        return None
    for name in members:
        if name.startswith("/") or ".." in Path(name).parts:
            return None
    if not set(captured) <= members:
        return None
    return manifest


def verified(destination, archive):
    """The manifest for one specific archive, or None if it does not verify.

    `latest()` answers "what is the best baseline here"; a saved pointer answers
    "what did this device record". They must not disagree: a pointer to an empty
    or truncated file used to be trusted because the path existed, so the page
    reported a recovery point that `latest()` already knew was unusable.
    """
    destination = Path(destination)
    archive = Path(archive)
    if not ARCHIVE_NAME.match(archive.name):
        return None
    if archive.parent.resolve() != destination.resolve():
        return None
    manifest = _manifest_for(destination, destination / (archive.name[:-len(".tar.gz")] + ".json"))
    if manifest is None or manifest.get("archive") != archive.name:
        return None
    return manifest


def latest(destination):
    """The most recent usable manifest, or None.

    A manifest is only a baseline if it validates: the archive beside it exists
    as a direct child of this directory, still hashes to what the manifest says,
    opens as a gzip tar, and contains the members it claims. Without that a
    damaged or half-written file is reported as the device's known-good point.
    It does not prove the archive is *this device's*: a manifest that claims no
    captured files admits any gzip tar that hashes to it, and nothing here
    records which device the state came from. The validator also reads the
    archive whole, so it is not a size bound on what it is willing to hash.
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
        manifest = _manifest_for(destination, path)
        if manifest is not None:
            return manifest
    return None
