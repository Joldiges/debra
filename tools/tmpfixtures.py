"""Throwaway fixture directories that do not accumulate for ever.

    import tools.tmpfixtures as tmpfixtures
    FIXTURES = tmpfixtures.root("debra-taskchain-tests-")

A repeated test run creates hundreds of small Git repositories, and an
unlimited retention policy on a tmpfs eventually exhausts the inode table, not
just space — a full ``/tmp`` then fails unrelated work with "No space left on
device" while ``df -h`` still shows free gigabytes. So a fixture root prunes
earlier runs when it is created.

The rules are deliberately narrow:

- only directories whose name starts with the prefix it was given;
- symlinks are skipped, never followed, so a planted link cannot redirect a
  delete;
- a run younger than ``grace`` seconds is kept, because another checkout may be
  running the same suite right now;
- at most ``keep`` recent runs are kept regardless of age.

The current run is never a candidate: pruning happens before it is created.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path

BASE = Path(os.environ.get("DEBRA_FIXTURE_DIR", "/tmp/opencode"))
KEEP = 6
GRACE_SECONDS = 3600


def prune(prefix: str, base: Path | None = None, keep: int = KEEP,
          grace: float = GRACE_SECONDS, now: float | None = None) -> list[Path]:
    """Remove old run directories matching ``prefix``; return what was removed."""
    base = Path(base) if base is not None else BASE
    current = time.time() if now is None else now
    runs = []
    try:
        entries = list(base.iterdir())
    except OSError:
        return []
    for entry in entries:
        if not entry.name.startswith(prefix) or entry.is_symlink():
            continue
        try:
            if not entry.is_dir():
                continue
            age = current - entry.stat().st_mtime
        except OSError:
            continue
        runs.append((age, entry))
    runs.sort(key=lambda item: item[0])
    removed = []
    for index, (age, entry) in enumerate(runs):
        if index < keep and age <= grace:
            continue
        try:
            shutil.rmtree(entry)
        except OSError:
            continue
        removed.append(entry)
    return removed


def root(prefix: str, base: Path | None = None, keep: int = KEEP,
         grace: float = GRACE_SECONDS) -> Path:
    """Prune earlier runs, then create and return this run's fixture root."""
    base = Path(base) if base is not None else BASE
    base.mkdir(parents=True, exist_ok=True)
    prune(prefix, base, keep, grace)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=base))
