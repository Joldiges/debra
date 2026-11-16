"""Installed-artifact checks for control/web/install.py.

The installer prepares four things on a device: a content-addressed release, an
owner-only key, a generated systemd user unit, and a retained previous unit for
rollback. This module proves what those artifacts actually are on disk, rather
than what the installer intends.

Every test installs into a fresh temporary home under /tmp/opencode. The unit is
only read as text and never loaded by systemd; no service is started, no audio is
touched and no real install path is used.

"Interrupted" here means an injected OSError at a real write or publication
point, not abrupt power loss. install.py has no complete flush protocol, so
power-loss durability is unproven and these tests do not claim it.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

from control.web import server as web


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "control/web"
SINK = "alsa_output.test.stereo-fallback"

# The installer also runs directly on a device, where server.py is beside it.
spec = importlib.util.spec_from_file_location("web_install_artifacts", SOURCE / "install.py")
installer = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"server": web}):
    spec.loader.exec_module(installer)

BASE = Path(".local/share/debra/web")
RELEASES = BASE / "releases"
STATE = Path(".config/debra/web")
UNIT = Path(".config/systemd/user/debra-web.service")


def content_address(files):
    """The installer's own release identity: sorted name, bytes, NUL into sha256."""
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode() + b"\0" + files[name] + b"\0")
    return digest.hexdigest()


def file_mode(path):
    return stat.S_IMODE(path.stat().st_mode)


class InstalledArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="install-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.scratch = Path(self.temp.name)
        self.home = self.scratch / "home"
        self.home.mkdir()
        self.base = self.home / BASE
        self.releases = self.home / RELEASES
        self.state = self.home / STATE
        self.unit = self.home / UNIT

    def install(self, source=SOURCE, hosts=None, home=None, **kwargs):
        return installer.install(home or self.home, source, SINK, "127.0.0.1", 8787,
                                 hosts or ["device.local:8787"], "/usr/bin/python3", **kwargs)

    def source_copy(self, label):
        """A private, modifiable payload tree that stands in for a later version."""
        copy = self.scratch / ("source-" + label)
        for name in installer.PAYLOAD:
            target = copy / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / name, target)
        return copy

    def payload_of(self, release):
        """The declared payload as it exists inside an installed release."""
        return {name: (release / name).read_bytes() for name in installer.PAYLOAD}

    def installed_files(self, release):
        return sorted(str(path.relative_to(release))
                      for path in release.rglob("*") if path.is_file())

    def assert_releases_are_addressable_and_complete(self):
        """Every non-staging directory under releases matches its own name."""
        for path in self.releases.iterdir():
            if path.name.startswith(".pending-"):
                self.assertEqual(file_mode(path), 0o700,
                                 f"{path} is abandoned staging and must stay private")
                continue
            self.assertRegex(path.name, r"\A[0-9a-f]{64}\Z",
                             f"{path} is not a content address")
            self.assertEqual(content_address(self.payload_of(path)), path.name,
                             f"{path} is addressable but does not match its address")

    # 1. Installed bytes -------------------------------------------------

    def test_installed_bytes_are_the_release_and_the_address_matches_them(self):
        result = self.install()
        release = self.releases / result["release"]
        self.assertRegex(result["release"], r"\A[0-9a-f]{64}\Z",
                         "a release name is a sha256 content address, not a caller string")
        self.assertEqual(self.installed_files(release), sorted(installer.PAYLOAD),
                         "the release holds exactly the declared payload, nothing else")
        installed = self.payload_of(release)
        for name in installer.PAYLOAD:
            self.assertEqual(installed[name], (SOURCE / name).read_bytes(),
                             f"installed {name} differs from the reviewed source")
        # The directory name is the content address of the bytes inside it, not
        # just a label copied from the source.
        self.assertEqual(content_address(installed), result["release"],
                         "the release address does not match the installed content")
        self.assertEqual(content_address({name: (SOURCE / name).read_bytes()
                                          for name in installer.PAYLOAD}),
                         result["release"],
                         "the release address does not match the source it came from")
        # The unit starts that exact directory and never carries the key.
        text = self.unit.read_text()
        self.assertIn(str(release / "server.py"), text)
        self.assertIn(str(self.state), text)
        self.assertNotIn(web.load_key(self.state), text)
        # A clean install leaves no staging directory behind.
        self.assertEqual([path.name for path in self.releases.iterdir()], [result["release"]])

    def test_every_installed_path_stays_inside_the_install_root(self):
        before = {str(path) for path in self.scratch.rglob("*")}
        result = self.install(devices=[{"name": "debra-1", "url": "http://debra-1.local:8787/"}])
        created = [path for path in self.scratch.rglob("*") if str(path) not in before]
        self.assertTrue(created, "the installer wrote nothing")
        for path in created:
            self.assertTrue(path == self.home or self.home in path.parents,
                            f"{path} was written outside the install root {self.home}")
        self.assertTrue((self.releases / result["release"]).is_dir())

    def test_different_content_gets_a_different_address_and_both_are_retained(self):
        first = self.install(hosts=["first.local:8787"])
        old_release = self.releases / first["release"]
        old_payload = self.payload_of(old_release)
        source = self.source_copy("v2")
        changed = source / "assets/app.js"
        changed.write_bytes(changed.read_bytes() + b"\n// later version\n")
        second = self.install(source=source, hosts=["second.local:8787"])
        self.assertNotEqual(second["release"], first["release"],
                            "changing payload content must change the address")
        new_release = self.releases / second["release"]
        self.assertEqual(content_address(self.payload_of(new_release)), second["release"])
        self.assertIn(str(new_release / "server.py"), self.unit.read_text())
        # The old release stays byte-identical so the previous unit can still run.
        self.assertEqual(self.payload_of(old_release), old_payload)
        self.assertIn(str(old_release / "server.py"),
                      Path(second["previous_unit"]).read_text())
        self.assert_releases_are_addressable_and_complete()

    # 2. Modes -----------------------------------------------------------

    def test_installed_modes_are_owner_only_and_the_unit_is_readable(self):
        result = self.install(devices=[{"name": "debra-1", "url": "http://debra-1.local:8787/"}])
        release = self.releases / result["release"]
        stored = next(self.state.glob("devices-*.json"))
        key = self.state / "access.key"
        staged = sorted(self.state.glob(".access-key.staged-*"))
        staged_devices = sorted(self.state.glob(".devices.staged-*"))
        self.assertTrue(staged, "the key publication artifact should be retained")

        self.assertEqual(file_mode(key), 0o600, "the device key must be owner-only")
        for path in (self.state, self.base, self.releases, release):
            self.assertEqual(file_mode(path), 0o700, f"{path} must be owner-only")
        for name in installer.PAYLOAD:
            self.assertEqual(file_mode(release / name), 0o600,
                             f"installed {name} must not be group/world accessible")
        for path in (stored, *staged, *staged_devices):
            self.assertEqual(file_mode(path), 0o600, f"{path} carries private state")

        # The unit contains no secret but must still be readable by its owner.
        self.assertEqual(file_mode(self.unit), 0o600)
        self.assertTrue(os.access(self.unit, os.R_OK), "the owner cannot read the unit")
        self.assertIn("ExecStart=", self.unit.read_text())

        # Nothing created here is world-writable, and no credential artifact is
        # readable or writable by group or other.
        for path in (self.state, self.base, self.releases, release, self.unit,
                     *self.state.iterdir(), *self.releases.iterdir(),
                     *(path for path in release.rglob("*"))):
            self.assertFalse(file_mode(path) & 0o002, f"{path} is world-writable")
        for path in (key, stored, *staged, *staged_devices):
            self.assertEqual(file_mode(path) & 0o077, 0,
                             f"{path} is not owner-only ({oct(file_mode(path))})")

    # 3. A tampered release ----------------------------------------------

    def test_a_corrupted_or_substituted_installed_file_is_refused(self):
        result = self.install()
        release = self.releases / result["release"]
        original = self.payload_of(release)
        unit = self.unit.read_bytes()
        cases = {
            "one extra byte": ("assets/app.js", original["assets/app.js"] + b"\n"),
            "truncated": ("server.py", original["server.py"][:100]),
            "another payload file substituted":
                ("assets/app.js", original["assets/style.css"]),
        }
        for label, (name, data) in cases.items():
            with self.subTest(label):
                target = release / name
                target.write_bytes(original[name])
                self.assertEqual(content_address(self.payload_of(release)), result["release"],
                                 "fixture did not start from a matching release")
                target.write_bytes(data)
                self.assertNotEqual(content_address(self.payload_of(release)), result["release"],
                                    "the content address must no longer match")
                with self.assertRaisesRegex(ValueError, "differs from expected payload"):
                    self.install()
                self.assertEqual(target.read_bytes(), data,
                                 "tampered bytes must be preserved, not silently repaired")
                self.assertEqual(self.unit.read_bytes(), unit,
                                 "a refused install must not touch the unit")
                target.write_bytes(original[name])
        # A release that is merely incomplete is refused too, as an OSError the
        # installer's main() reports instead of a traceback.
        missing = release / "discovery.py"
        missing.rename(release / "discovery.py.moved")
        with self.assertRaises(OSError):
            self.install()
        self.assertFalse((release / "discovery.py").exists())
        self.assertEqual(self.unit.read_bytes(), unit)
        (release / "discovery.py.moved").rename(missing)
        self.assertFalse(self.install()["changed"])

    def test_a_symlinked_payload_file_inside_the_release_is_refused(self):
        result = self.install()
        release = self.releases / result["release"]
        target = release / "discovery.py"
        target.rename(release / "discovery.py.saved")
        target.symlink_to(self.scratch / "elsewhere.py")
        with self.assertRaisesRegex(ValueError, "differs from expected payload"):
            self.install()
        self.assertTrue(target.is_symlink(), "the substituted link must be left in place")
        target.unlink()
        (release / "discovery.py.saved").rename(target)
        self.assertFalse(self.install()["changed"])

    # 4. Interrupted publication and rollback ----------------------------

    def test_interrupted_copy_leaves_no_addressable_release(self):
        first = self.install(hosts=["first.local:8787"])
        old_release = self.releases / first["release"]
        old_unit = self.unit.read_bytes()
        source = self.source_copy("v2")
        (source / "server.py").write_bytes((source / "server.py").read_bytes() + b"\n# v2\n")

        real_create = installer.create_private
        calls = []

        def dying_create(path, data):
            calls.append(path)
            if len(calls) == 2:
                # The first file exists; the process dies before the second.
                raise OSError("simulated process death during the copy")
            return real_create(path, data)

        with patch.object(installer, "create_private", dying_create):
            with self.assertRaises(OSError):
                self.install(source=source, hosts=["second.local:8787"])

        # The unit still names the old, complete release: the device starts the
        # old version, not a mixture.
        self.assertEqual(self.unit.read_bytes(), old_unit)
        self.assertIn(str(old_release / "server.py"), self.unit.read_text())
        self.assertEqual(content_address(self.payload_of(old_release)), first["release"])
        # The abandoned copy has no content address, so no unit can name it.
        staged = [path for path in self.releases.iterdir() if path.name.startswith(".pending-")]
        self.assertEqual(len(staged), 1, "the interrupted copy should be retained")
        self.assertEqual(file_mode(staged[0]), 0o700,
                         "staging must be private, whatever mode its files have")
        self.assertEqual(sorted(path.name for path in self.releases.iterdir()
                                if not path.name.startswith(".")),
                         [first["release"]])
        self.assertLess(len([path for path in staged[0].rglob("*") if path.is_file()]),
                        len(installer.PAYLOAD), "the copy should be incomplete")
        # The directory is 0700, but the files themselves must not depend on the
        # umask: `open("xb")` created them 0644 until the later chmod ran.
        for path in staged[0].rglob("*"):
            if path.is_file():
                self.assertEqual(file_mode(path), 0o600,
                                 f"{path.name} was created readable by others")
        self.assert_releases_are_addressable_and_complete()

        # Retry publishes a complete release, then moves the unit.
        second = self.install(source=source, hosts=["second.local:8787"])
        self.assertTrue(second["changed"])
        new_release = self.releases / second["release"]
        self.assertEqual(content_address(self.payload_of(new_release)), second["release"])
        self.assertIn(str(new_release / "server.py"), self.unit.read_text())
        self.assert_releases_are_addressable_and_complete()

    def test_a_damaged_retained_release_is_reported_and_never_restored(self):
        # A release is named by the digest of its payload, and rollback runs a
        # retained release. A corrupted one still exists, so the old check passed
        # and the rollback produced a service that fails at startup.
        first = self.install()
        v2 = self.source_copy("v2")
        (v2 / "server.py").write_bytes((v2 / "server.py").read_bytes() + b"\n# v2\n")
        second = self.install(source=v2, hosts=["second.local:8787"])
        self.assertNotEqual(first["release"], second["release"])
        self.assertEqual(second["damaged_releases"], [])

        old = self.releases / first["release"]
        (old / "server.py").write_bytes((old / "server.py").read_bytes() + b"\n# corrupted\n")

        v3 = self.source_copy("v3")
        (v3 / "server.py").write_bytes((v3 / "server.py").read_bytes() + b"\n# v3\n")
        third = self.install(source=v3, hosts=["third.local:8787"])
        self.assertEqual(third["damaged_releases"], [first["release"]],
                         "a corrupted retained release was not reported")
        with self.assertRaisesRegex(ValueError, "no longer match"):
            installer.restore_unit(self.home, second["previous_unit"])
        # The refusal changed nothing.
        self.assertIn(third["release"], self.unit.read_text())

    def test_the_unit_stops_restarting_after_repeated_failures(self):
        # Without a start limit, a unit that cannot start restarts every three
        # seconds for ever and the only trace is a journal line.
        self.install()
        text = self.unit.read_text()
        unit_section = text.split("[Unit]", 1)[1].split("[", 1)[0]
        service_section = text.split("[Service]", 1)[1].split("[", 1)[0]
        self.assertIn("StartLimitIntervalSec=300", unit_section)
        self.assertIn("StartLimitBurst=4", unit_section)
        self.assertNotIn("StartLimit", service_section,
                         "the start limit belongs in [Unit]")
        self.assertIn("Restart=on-failure", service_section)

    def test_interrupted_publication_leaves_the_old_version_runnable(self):
        first = self.install(hosts=["first.local:8787"])
        old_release = self.releases / first["release"]
        old_unit = self.unit.read_bytes()
        source = self.source_copy("v2")
        (source / "assets/app.js").write_bytes(
            (source / "assets/app.js").read_bytes() + b"\n// v2\n")
        with patch.object(Path, "rename", side_effect=OSError("simulated process death")):
            with self.assertRaises(OSError):
                self.install(source=source, hosts=["second.local:8787"])
        self.assertEqual(self.unit.read_bytes(), old_unit)
        self.assertIn(str(old_release / "server.py"), self.unit.read_text())
        self.assertEqual(content_address(self.payload_of(old_release)), first["release"])
        self.assert_releases_are_addressable_and_complete()

    def test_interrupted_upgrade_leaves_exactly_one_complete_unit(self):
        first = self.install(hosts=["first.local:8787"])
        old_unit = self.unit.read_bytes()
        old_release = self.releases / first["release"]
        # A real upgrade changes the payload as well as the unit, so both
        # publication points are exercised.
        source = self.source_copy("v2")
        (source / "server.py").write_bytes((source / "server.py").read_bytes() + b"\n# v2\n")
        known = {first["release"],
                 content_address({name: (source / name).read_bytes()
                                  for name in installer.PAYLOAD})}
        # Every publication point an upgrade uses, one at a time.
        for label, target, name in (("release rename", Path, "rename"),
                                    ("unit replace", installer.os, "replace")):
            with self.subTest(label), \
                    patch.object(target, name, side_effect=OSError("simulated process death")):
                with self.assertRaises(OSError):
                    self.install(source=source, hosts=["second.local:8787"])
                self.assertEqual(self.unit.read_bytes(), old_unit,
                                 f"{label}: the unit is neither the old nor the new version")
                # The candidate is written beside the unit before it is renamed.
                # An interrupted install must not leave it there: the folder is
                # systemd's, and nothing ever removes an unexplained file from it.
                self.assertEqual(sorted(path.name for path in self.unit.parent.iterdir()),
                                 [self.unit.name],
                                 f"{label}: a half-written candidate was left beside the unit")
                self.assertIn(str(old_release / "server.py"), self.unit.read_text(),
                              f"{label}: the retained unit must still name a real release")
                self.assertEqual(content_address(self.payload_of(old_release)),
                                 first["release"], f"{label}: the old release was disturbed")
                self.assert_releases_are_addressable_and_complete()
                for path in self.releases.iterdir():
                    if not path.name.startswith("."):
                        self.assertIn(path.name, known,
                                      f"{label}: an unexpected release was published")
        # The retry completes both publications and the unit names the new release.
        final = self.install(source=source, hosts=["second.local:8787"])
        self.assertTrue(final["changed"])
        self.assertIn(str(self.releases / final["release"] / "server.py"),
                      self.unit.read_text())
        self.assert_releases_are_addressable_and_complete()

    def test_documented_rollback_copy_is_not_crash_atomic(self):
        """Finding: the README rolls back with an in-place `cp`, which truncates.

        The installer's own unit replacement is atomic, but the documented
        rollback is `cp -- previous_unit debra-web.service`. A copy interrupted
        partway leaves a truncated unit: neither the old nor the new version, and
        not startable. This test records the real behaviour instead of asserting
        a guarantee the installer does not make.
        """
        self.install(hosts=["first.local:8787"])
        old_unit = self.unit.read_bytes()
        upgrade = self.install(hosts=["second.local:8787"])
        new_unit = self.unit.read_bytes()
        backup = Path(upgrade["previous_unit"])
        self.assertEqual(backup.read_bytes(), old_unit)

        # `cp` truncates the destination before writing: 40 bytes is a plausible
        # interruption point, past the marker and into the [Unit] section.
        self.unit.write_bytes(old_unit[:40])
        partial = self.unit.read_bytes()
        self.assertNotEqual(partial, old_unit)
        self.assertNotEqual(partial, new_unit)
        self.assertNotIn(b"ExecStart=", partial,
                         "the truncated unit cannot start the service")

        # With the marker intact the installer still repairs it atomically.
        self.assertTrue(partial.startswith(installer.MARKER.encode()))
        self.assertTrue(self.install(hosts=["first.local:8787"])["changed"])
        self.assertEqual(self.unit.read_bytes(), old_unit,
                         "re-running the installer should restore the exact old unit")

        # Interrupted inside the marker line, the installer refuses to touch it
        # and the device needs a manual repair. That is the real limit.
        self.unit.write_bytes(old_unit[:10])
        with self.assertRaisesRegex(ValueError, "not managed by this installer"):
            self.install(hosts=["first.local:8787"])
        self.assertEqual(self.unit.read_bytes(), old_unit[:10])

    def test_a_corrupted_retained_release_is_not_rechecked(self):
        """Finding: only the release about to be used is verified, never a retained one.

        The previous unit keeps naming the old release, so the documented
        rollback can restore a unit that runs corrupted code and the installer
        will not say so. Recorded as a gap, not asserted as a guarantee.
        """
        first = self.install(hosts=["first.local:8787"])
        old_release = self.releases / first["release"]
        source = self.source_copy("v2")
        (source / "assets/app.js").write_bytes(
            (source / "assets/app.js").read_bytes() + b"\n// v2\n")
        second = self.install(source=source, hosts=["second.local:8787"])
        self.assertNotEqual(second["release"], first["release"])

        tampered = self.payload_of(old_release)
        tampered["assets/app.js"] += b"\n// corrupted after install\n"
        (old_release / "assets/app.js").write_bytes(tampered["assets/app.js"])
        # Neither noticed nor repaired, by this or any later identical install.
        self.assertFalse(self.install(source=source, hosts=["second.local:8787"])["changed"])
        self.assertEqual((old_release / "assets/app.js").read_bytes(),
                         tampered["assets/app.js"])
        # Restoring the previous unit now names content that no longer matches
        # the address in its own path.
        self.unit.write_bytes(Path(second["previous_unit"]).read_bytes())
        self.assertIn(str(old_release / "server.py"), self.unit.read_text())
        self.assertNotEqual(content_address(self.payload_of(old_release)), first["release"])

    # 5. No escape from the install root ---------------------------------

    def test_a_release_cannot_escape_the_install_root(self):
        result = self.install()
        release = self.releases / result["release"]
        outside = self.scratch / "outside"
        outside.mkdir()
        (outside / "server.py").write_text("# planted outside the install root\n")
        before = sorted(str(path.relative_to(outside)) for path in outside.rglob("*"))

        # The release name is a content address the caller cannot choose, and it
        # names a direct child of the release directory.
        self.assertRegex(result["release"], r"\A[0-9a-f]{64}\Z")
        self.assertEqual(release.resolve().parent, self.releases.resolve())
        self.assertEqual(release.name, result["release"])

        # A release directory that is really a symlink out of the root is refused.
        saved = self.scratch / "saved-release"
        release.rename(saved)
        release.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "differs from expected payload"):
            self.install()
        self.assertEqual(sorted(str(path.relative_to(outside)) for path in outside.rglob("*")),
                         before, "the installer wrote through the release symlink")
        release.unlink()
        saved.rename(release)

        # So is a symlinked install directory anywhere in the chain, refused
        # before any write.
        other = self.scratch / "other-home"
        (other / ".config").mkdir(parents=True)
        (other / ".local").mkdir(parents=True)
        (other / ".config/debra").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlinked install"):
            self.install(home=other)
        self.assertEqual(sorted(str(path.relative_to(outside)) for path in outside.rglob("*")),
                         before)
        self.assertFalse((other / BASE).exists(), "a refused install must write nothing")
        self.assertFalse((other / STATE).exists())

        # A home reached through a symlink is refused as well, so a path that
        # tries to leave the named root cannot become the install root.
        linked = self.scratch / "linked-home"
        linked.symlink_to(self.home)
        with self.assertRaisesRegex(ValueError, "symlinked install"):
            self.install(home=linked)

    def test_an_invalid_device_list_is_refused_before_anything_is_written(self):
        # Only main() validated the list. A programmatic caller could install a
        # list the server then refused at startup, leaving a unit that cannot
        # serve. The list is now validated before the first write.
        for devices, reason in (
                ([{"name": "../../../../etc/passwd", "url": "http://debra-1.local:8787/"}],
                 "Device name"),
                ([{"name": "debra-1", "url": "http://debra-1.local:80/"}], "port"),
                ([{"name": "x"}] * 51, "at most 50")):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(ValueError, reason):
                    self.install(devices=devices)
        self.assertFalse(self.unit.exists(), "a refused list still wrote the unit")
        self.assertFalse(self.state.exists(), "a refused list still wrote state")
        self.assertFalse(self.releases.exists(), "a refused list still published a release")

    def test_device_list_path_comes_from_its_content_not_the_caller(self):
        # A caller-controlled name never becomes a path: the stored file is named
        # by a hash of the list's bytes, inside the private state directory.
        devices = [{"name": "debra-1", "url": "http://debra-1.local:8787/",
                    "label": "not a path"}]
        outside = self.scratch / "outside"
        outside.mkdir()
        self.install(devices=devices)
        stored = list(self.state.glob("devices-*.json"))
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].parent, self.state)
        self.assertRegex(stored[0].name, r"\Adevices-[0-9a-f]{64}\.json\Z")
        # The list is normalised by the same validator the server uses, so the
        # stored bytes are what the server would accept, not what a caller typed.
        self.assertEqual(json.loads(stored[0].read_text()),
                         [installer.validate_device(devices[0])])
        self.assertEqual([str(path.relative_to(outside)) for path in outside.rglob("*")], [])
        # Everything the list produced sits in the private state directory.
        expected = {"access.key", stored[0].name}
        for pattern in (".access-key.staged-*", ".devices.staged-*"):
            expected |= {path.name for path in self.state.glob(pattern)}
        self.assertEqual(sorted(path.name for path in self.state.iterdir() if path.is_file()),
                         sorted(expected))
        # install() validates the list itself, so what is stored is what the
        # server accepts at startup. This used to raise: a programmatic caller
        # could install a list the server then refused.
        self.assertEqual(web.load_devices(stored[0]),
                         [installer.validate_device(devices[0])])


if __name__ == "__main__":
    unittest.main()


class RestoreTests(unittest.TestCase):
    """The rollback path itself, which the installer now performs.

    A copy truncates the destination before writing, so an interruption partway
    leaves a unit that is neither version and cannot start. These tests hold the
    restore to the same standard as the install.
    """

    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix="restore-", dir="/tmp/opencode")
        self.home = Path(self._temp.name)
        self.unit = self.home / ".config" / "systemd" / "user" / "debra-web.service"
        self.unit.parent.mkdir(parents=True)
        self.unit.write_text("[Service]\nExecStart=/usr/bin/new\n", encoding="utf-8")
        self.previous = self.home / "previous.service"
        self.previous.write_text("[Service]\nExecStart=/usr/bin/old\n", encoding="utf-8")

    def tearDown(self):
        self._temp.cleanup()

    def test_a_restore_replaces_the_unit_with_a_complete_file(self):
        installer.restore_unit(self.home, self.previous)
        self.assertEqual(self.unit.read_text(encoding="utf-8"),
                         "[Service]\nExecStart=/usr/bin/old\n")
        self.assertEqual(stat.S_IMODE(self.unit.stat().st_mode), 0o600)

    def test_an_interrupted_restore_leaves_the_old_unit_untouched(self):
        before = self.unit.read_bytes()
        with patch.object(installer.os, "replace", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                installer.restore_unit(self.home, self.previous)
        # Neither truncated nor half-written: still exactly the old unit.
        self.assertEqual(self.unit.read_bytes(), before)
        self.assertEqual(list(self.unit.parent.glob("*.restore")), [],
                         "a failed restore must not leave a staging file behind")

    def test_a_file_that_is_not_a_unit_is_refused_before_anything_is_replaced(self):
        before = self.unit.read_bytes()
        junk = self.home / "junk.service"
        junk.write_text("not a unit\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            installer.restore_unit(self.home, junk)
        self.assertEqual(self.unit.read_bytes(), before)
