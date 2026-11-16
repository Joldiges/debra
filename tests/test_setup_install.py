"""Installed-artifact checks for control/setup/install.py.

The installer prepares three things on a device: a content-addressed release, a
rendered systemd **system** unit, and private state paths. This module proves
what those artifacts actually are on disk rather than what the installer
intends, and that a second install keeps the previous unit for rollback.

Every test prepares a temporary root under /tmp/opencode. The unit is only read
as text; nothing is loaded by systemd, no service is started, no radio is
touched and no real install path is used. The one port bound is an ephemeral
loopback port inside the process that owns it.

"Interrupted" is not simulated here: install.py has no complete flush protocol,
so power-loss durability is unproven and these tests do not claim it.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "control" / "setup"
sys.path.insert(0, str(SOURCE))

import onboarding  # noqa: E402
import state as state_module  # noqa: E402
from fake_nm import FakeNetwork  # noqa: E402

# The installer also runs directly on a device, where its payload is beside it.
spec = importlib.util.spec_from_file_location("setup_install_artifacts", SOURCE / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

LIB = installer.LIB
VAR = installer.VAR
UNIT = installer.UNIT


def content_address(files):
    """The installer's own release identity: sorted name, bytes, NUL into sha256."""
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode() + b"\0" + files[name] + b"\0")
    return digest.hexdigest()


def file_mode(path):
    return stat.S_IMODE(path.stat().st_mode)


def runner_path(release_id):
    """The runner path the unit names: a device path, whatever --root prepared."""
    return str(Path("/") / LIB / "releases" / release_id / "install.py")


def parse_unit(text):
    """A minimal unit parser: section headers, key=value, comments ignored."""
    sections, headers, current = {}, [], None
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            headers.append(line)
            sections.setdefault(current, {})
            continue
        key, separator, value = line.partition("=")
        if current is None or not separator or not key.strip():
            raise AssertionError(f"line {number} is not a unit setting: {line!r}")
        sections[current][key.strip()] = value.strip()
    return sections, headers


class Fixture(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix="setup-install-", dir="/tmp/opencode")
        self.addCleanup(self._temp.cleanup)
        self.scratch = Path(self._temp.name)
        self.root = self.scratch / "root"
        self.root.mkdir()
        # Raspberry Pi OS Bookworm mounts the boot partition here, so the card
        # note path is chosen deterministically whatever machine runs the test.
        (self.root / "boot/firmware").mkdir(parents=True)
        self.lib = self.root / LIB
        self.releases = self.lib / "releases"
        self.state = self.root / VAR
        self.unit = self.root / UNIT

    def install(self, source=SOURCE, **kwargs):
        return installer.install(self.root, source, "/usr/bin/python3", **kwargs)

    def source_copy(self, label, edit=None):
        """A private, modifiable payload tree that stands in for a later version."""
        copy = self.scratch / ("source-" + label)
        for name in installer.PAYLOAD:
            target = copy / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / name, target)
        if edit:
            edit(copy)
        return copy

    def payload_of(self, release):
        return {name: (release / name).read_bytes() for name in installer.PAYLOAD}

    def installed_files(self, release):
        return sorted(str(path.relative_to(release))
                      for path in release.rglob("*") if path.is_file())


class InstalledArtifactTests(Fixture):
    def test_the_release_is_written_where_the_installer_says_with_the_modes_it_claims(self):
        result = self.install()
        release = Path(result["release_path"])
        self.assertEqual(release.parent, self.releases)
        self.assertRegex(result["release"], r"\A[0-9a-f]{64}\Z",
                         "a release name is a sha256 content address, not a caller string")
        self.assertEqual(release.name, result["release"])
        self.assertEqual(self.installed_files(release), sorted(installer.PAYLOAD),
                         "the release holds exactly the declared payload, nothing else")
        installed = self.payload_of(release)
        for name in installer.PAYLOAD:
            self.assertEqual(installed[name], (SOURCE / name).read_bytes(),
                             f"installed {name} differs from the reviewed source")
        self.assertEqual(content_address(installed), result["release"],
                         "the release address does not match the installed content")

        self.assertEqual(file_mode(self.lib), 0o700)
        self.assertEqual(file_mode(self.releases), 0o700)
        self.assertEqual(file_mode(release), 0o700)
        for name in installer.PAYLOAD:
            self.assertEqual(file_mode(release / name), 0o600,
                             f"installed {name} must not be group/world accessible")
        self.assertEqual(file_mode(self.state), 0o700)
        # No Debra-owned keyfile directory: the Wi-Fi profile is written where
        # NetworkManager's keyfile plugin reads it, so a staging directory here
        # would only be a place a profile could be lost from.
        self.assertFalse((self.state / "keyfiles").exists())
        self.assertEqual(file_mode(self.unit), 0o644,
                         "a system unit carries no secret and is world-readable")
        for path in self.scratch.rglob("*"):
            if path.is_file():
                self.assertFalse(file_mode(path) & 0o002, f"{path} is world-writable")

        # A clean install leaves no staging directory behind.
        self.assertEqual([path.name for path in self.releases.iterdir()], [result["release"]])

    def test_nothing_is_written_outside_the_target_root(self):
        before = {str(path) for path in self.scratch.rglob("*")}
        result = self.install()
        created = [path for path in self.scratch.rglob("*") if str(path) not in before]
        self.assertTrue(created, "the installer wrote nothing")
        for path in created:
            self.assertTrue(path == self.root or self.root in path.parents,
                            f"{path} was written outside the install root {self.root}")
        self.assertTrue(Path(result["release_path"]).is_dir())

    def test_a_second_install_keeps_the_previous_unit_for_rollback(self):
        first = self.install()
        old_release = Path(first["release_path"])
        old_unit = self.unit.read_bytes()

        def change(copy):
            target = copy / "onboarding.py"
            target.write_bytes(target.read_bytes() + b"\n# a later version\n")

        second = self.install(source=self.source_copy("v2", change))
        self.assertTrue(second["changed"])
        self.assertNotEqual(second["release"], first["release"],
                            "changing payload content must change the address")
        self.assertIn(runner_path(second["release"]), self.unit.read_text())
        self.assertNotIn(runner_path(first["release"]), self.unit.read_text())

        previous = Path(second["previous_unit"])
        self.assertEqual(previous.parent, self.lib / "previous-units")
        self.assertEqual(previous.read_bytes(), old_unit,
                         "the previous unit must be kept byte for byte")
        self.assertEqual(file_mode(previous), 0o600)
        self.assertIn(runner_path(first["release"]), previous.read_text())
        # The old release is retained, so the retained unit still names real code.
        self.assertEqual(content_address(self.payload_of(old_release)), first["release"])

    def test_rollback_restores_the_previous_unit(self):
        first = self.install()
        old_unit = self.unit.read_bytes()
        second = self.install(source=self.source_copy("v2", lambda copy: (
            copy / "state.py").write_bytes((copy / "state.py").read_bytes() + b"\n# v2\n")))
        self.assertNotEqual(self.unit.read_bytes(), old_unit)

        restored = installer.restore(self.root, second["previous_unit"])
        self.assertEqual(self.unit.read_bytes(), old_unit, "rollback did not restore the unit")
        self.assertEqual(restored["unit"], str(self.unit))
        self.assertIn(runner_path(first["release"]), self.unit.read_text())
        self.assertEqual(file_mode(self.unit), 0o644)
        # Reinstalling the same payload is now a no-op, so the restored unit is
        # the one the installer would have written.
        self.assertFalse(self.install()["changed"])

    def test_a_failed_install_rename_leaves_the_old_unit_and_no_litter(self):
        # The restore side was covered and the install side was not: replacing
        # the install's `os.replace` with a write in place, or with a copy,
        # passed every test. The unit is the file systemd reads, so an
        # interrupted install must leave exactly one of the two versions.
        first = self.install()
        before = self.unit.read_bytes()
        changed = self.source_copy("v9", lambda copy: (
            copy / "state.py").write_bytes((copy / "state.py").read_bytes() + b"\n# v9\n"))
        with patch.object(installer.os, "replace", side_effect=OSError(5, "Input/output error")):
            with self.assertRaises(OSError):
                self.install(source=changed)
        self.assertEqual(self.unit.read_bytes(), before,
                         "a failed install rewrote the unit in place")
        self.assertEqual(sorted(path.name for path in self.unit.parent.iterdir()),
                         [self.unit.name],
                         "a half-written candidate was left beside the unit")
        # A retry with the rename available completes normally.
        second = self.install(source=changed)
        self.assertIn(runner_path(second["release"]), self.unit.read_text())
        self.assertNotEqual(second["release"], first["release"])

    def test_rollback_publishes_by_rename_not_by_writing_in_place(self):
        # The final bytes are the same either way. What matters is that a
        # service manager reading the unit can never see it half-written, so the
        # last step must be a rename of a complete file.
        first = self.install()
        second = self.install(source=self.source_copy("v3", lambda copy: (
            copy / "state.py").write_bytes((copy / "state.py").read_bytes() + b"\n# v3\n")))
        before = self.unit.read_bytes()
        with patch.object(installer.os, "replace", side_effect=OSError(5, "Input/output error")):
            with self.assertRaises(OSError):
                installer.restore(self.root, second["previous_unit"])
        self.assertEqual(self.unit.read_bytes(), before,
                         "the unit was written in place instead of renamed")
        self.assertEqual(sorted(path.name for path in self.unit.parent.iterdir()),
                         [self.unit.name],
                         "a half-written candidate was left beside the unit")
        # And it still works once the rename can happen.
        installer.restore(self.root, second["previous_unit"])
        self.assertIn(runner_path(first["release"]), self.unit.read_text())

    def test_rollback_refuses_a_file_it_did_not_retain(self):
        self.install()
        outside = self.scratch / "elsewhere.service"
        outside.write_text(installer.MARKER + "[Service]\nExecStart=/bin/true\n")
        with self.assertRaisesRegex(ValueError, "retained under previous-units"):
            installer.restore(self.root, outside)
        with self.assertRaisesRegex(ValueError, "retained under previous-units"):
            installer.restore(self.root, self.root / "etc/systemd/system" / installer.UNIT_NAME)

    def test_an_unchanged_install_writes_nothing_new(self):
        first = self.install()
        unit = self.unit.read_bytes()
        second = self.install()
        self.assertFalse(second["changed"])
        self.assertIsNone(second["previous_unit"])
        self.assertEqual(second["release"], first["release"])
        self.assertEqual(self.unit.read_bytes(), unit)
        self.assertEqual([path.name for path in self.releases.iterdir()], [first["release"]])
        self.assertFalse((self.lib / "previous-units").exists(),
                         "an unchanged install must not create a rollback copy")

    def test_a_unit_the_installer_did_not_write_is_left_alone(self):
        self.unit.parent.mkdir(parents=True)
        self.unit.write_text("[Service]\nExecStart=/bin/true\n")
        with self.assertRaisesRegex(ValueError, "not managed by this installer"):
            self.install()
        self.assertEqual(self.unit.read_text(), "[Service]\nExecStart=/bin/true\n")
        self.assertFalse(self.releases.exists(), "a refused install must not publish a release")

    def test_a_tampered_release_is_refused_and_preserved(self):
        result = self.install()
        release = Path(result["release_path"])
        unit = self.unit.read_bytes()
        tampered = release / "onboarding.py"
        tampered.write_bytes(tampered.read_bytes() + b"\n# not the reviewed file\n")
        with self.assertRaisesRegex(ValueError, "differs from expected payload"):
            self.install()
        self.assertIn(b"not the reviewed file", tampered.read_bytes())
        self.assertEqual(self.unit.read_bytes(), unit)


class EscapeTests(Fixture):
    """No caller-supplied path may leave the root the installer was given."""

    def test_a_relative_path_that_climbs_out_is_refused(self):
        with self.assertRaisesRegex(ValueError, "inside the install root"):
            self.install(lib=Path("../escape"))
        with self.assertRaisesRegex(ValueError, "inside the install root"):
            self.install(var=Path("var/../../escape"))
        self.assertFalse((self.scratch / "escape").exists())
        self.assertFalse(self.releases.exists())

    def test_an_absolute_path_is_refused(self):
        with self.assertRaisesRegex(ValueError, "inside the install root"):
            self.install(unit=Path("/etc/systemd/system/debra-setup.service"))
        self.assertFalse(self.unit.exists())

    def test_a_symlinked_directory_is_refused_before_anything_is_written(self):
        outside = self.scratch / "outside"
        outside.mkdir()
        (self.root / "var").mkdir()
        (self.root / "var/lib").symlink_to(outside)
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual([path.name for path in outside.iterdir()], [],
                         "the installer wrote through a symlinked directory")
        self.assertFalse(self.unit.exists())

    def test_a_symlinked_root_is_refused(self):
        linked = self.scratch / "linked-root"
        linked.symlink_to(self.root)
        with self.assertRaisesRegex(ValueError, "symlinked install root"):
            installer.install(linked, SOURCE, "/usr/bin/python3")
        self.assertFalse(self.releases.exists())


class UnitTests(Fixture):
    def test_the_installed_unit_parses_as_a_system_service(self):
        result = self.install()
        text = self.unit.read_text()
        self.assertTrue(text.startswith(installer.MARKER))
        sections, headers = parse_unit(text)
        self.assertEqual(headers, ["[Unit]", "[Service]", "[Install]"],
                         "the unit has exactly the three sections it claims")
        self.assertEqual(sections["Service"]["Type"], "simple")
        self.assertEqual(sections["Install"]["WantedBy"], "multi-user.target")
        self.assertEqual(sections["Unit"]["Wants"], "NetworkManager.service")
        self.assertIn("NetworkManager.service", sections["Unit"]["After"])
        self.assertEqual(sections["Service"]["Restart"], "on-failure")
        self.assertEqual(sections["Service"]["NoNewPrivileges"], "yes")
        self.assertNotIn("User", sections["Service"],
                         "a system unit runs as root; naming a user would break nmcli")
        self.assertNotIn("ExecStop", sections["Service"])

        argv = shlex.split(sections["Service"]["ExecStart"])
        runner = str(Path("/") / LIB / "releases" / result["release"] / "install.py")
        self.assertEqual(argv, ["/usr/bin/python3", "-B", runner, "--serve",
                                "--state-dir", "/var/lib/debra/setup",
                                "--card-note", "/boot/firmware/debra-setup.txt",
                                "--setup-security", "none"])
        # The unit starts the release that was just published, not a copy of it.
        self.assertTrue((Path(result["release_path"]) / "install.py").is_file())

    def test_a_development_build_installs_the_open_mode_explicitly(self):
        # `none` is the development bypass and the default for now. It still
        # reaches the running unit as a written value, so an open setup network
        # is something the unit says, not a missing argument that a future
        # default change would silently reinterpret.
        result = self.install()
        self.assertEqual(result["security"], "none")
        sections, _ = parse_unit(self.unit.read_text())
        argv = shlex.split(sections["Service"]["ExecStart"])
        self.assertEqual(argv[-2:], ["--setup-security", "none"])

    def test_the_protected_mode_can_still_be_installed(self):
        result = self.install(security="wpa")
        self.assertEqual(result["security"], "wpa")
        sections, _ = parse_unit(self.unit.read_text())
        argv = shlex.split(sections["Service"]["ExecStart"])
        self.assertEqual(argv[-2:], ["--setup-security", "wpa"])

    def test_an_unknown_setup_security_is_refused_before_anything_is_written(self):
        # "off" is a plausible typo for a person and must not mean "open".
        with self.assertRaises(ValueError):
            self.install(security="off")
        self.assertFalse(self.unit.exists(), "a refused mode writes no unit")

    def test_the_unit_carries_no_credential_and_no_reboot(self):
        self.install()
        text = self.unit.read_text()
        lowered = text.lower()
        for forbidden in ("psk", "password", "passphrase", "access.key", "secret",
                          "wifi-psk", "token"):
            self.assertNotIn(forbidden, lowered, f"the unit mentions {forbidden!r}")
        # The device name is `debra-` plus six hex characters, and the setup
        # network's password is now twelve random characters from an alphabet
        # without look-alikes - neither may appear. The pattern stays because
        # the name is the one that could be templated in by mistake.
        self.assertIsNone(re.search(r"debra-[0-9a-f]{6,}", lowered),
                          "a device name or setup password leaked into the unit")
        self.assertNotIn("reboot", lowered, "nothing applies Wi-Fi by rebooting")
        self.assertNotIn("systemctl", lowered, "the unit does not drive systemd")
        for placeholder in installer.PLACEHOLDERS:
            self.assertNotIn(placeholder, text, "every placeholder must be resolved")

    def test_the_template_and_the_installed_unit_agree(self):
        template = (SOURCE / installer.TEMPLATE).read_text()
        for placeholder in installer.PLACEHOLDERS:
            self.assertIn(placeholder, template,
                          "the committed template must still carry every placeholder")
        self.assertIn(installer.TEMPLATE, installer.PAYLOAD,
                      "a re-install from a release needs the template beside it")
        self.install()
        for placeholder in installer.PLACEHOLDERS:
            self.assertNotIn(placeholder, self.unit.read_text())


class NoExternalCommandTests(Fixture):
    """The installer prepares files; it does not run anything."""

    def test_the_installer_invokes_no_command(self):
        calls = []

        def refuse(*args, **kwargs):
            calls.append(args)
            raise AssertionError("the installer ran an external command")

        with patch("subprocess.run", refuse), patch("subprocess.Popen", refuse), \
                patch("subprocess.check_call", refuse), patch("subprocess.check_output", refuse), \
                patch("os.system", refuse), patch("os.execv", refuse), \
                patch("os.execvp", refuse), patch("os.posix_spawn", refuse):
            self.install()
        self.assertEqual(calls, [])

    def test_the_installer_has_no_way_to_run_a_command(self):
        source = Path(installer.__file__).read_text()
        self.assertNotIn("import subprocess", source,
                         "install.py must not gain a command runner by accident")
        self.assertNotIn("os.system", source)


class ServiceTests(Fixture):
    """One boot of the service, against the recorded fake NetworkManager."""

    def boot(self, network, address=("192.0.2.1", 80), **kwargs):
        return installer.serve(self.state, self.scratch / "boot/debra-setup.txt",
                               network=network, address=address,
                               capture_root=self.scratch / "fake-root",
                               uplink_wait=0, **kwargs)

    def test_an_online_device_raises_no_setup_page(self):
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        # An address that cannot be bound here: if the portal were started, the
        # bind would fail and this test would raise instead of returning 0.
        self.assertEqual(self.boot(network), 0)
        self.assertNotIn("start_hotspot", network.phases())
        self.assertEqual(state_module.read(self.state / "setup.json")["phase"], "online")

    def test_the_service_leaves_the_profile_where_network_manager_reads_it(self):
        # The r2 review's blocker: a Debra-owned staging directory was
        # configured and never used, and a profile outside the keyfile plugin's
        # own directories is not one NetworkManager loads again after a reboot.
        # The service must not hand the adapter one.
        seen = {}
        real = installer.onboarding.Onboarder

        def capture(*args, **kwargs):
            seen.update(kwargs)
            return real(*args, **kwargs)

        network = FakeNetwork()
        network.joined = "HomeWiFi"
        with patch.object(installer.onboarding, "Onboarder", side_effect=capture):
            self.assertEqual(self.boot(network), 0)
        self.assertIsNone(seen.get("keyfile_dir"),
                          "the service is staging profiles outside NetworkManager's store")

    def test_a_partial_status_reports_instead_of_raising_a_key_error(self):
        # The access point is up, and the status read for the answer fails. The
        # fallback status is partial; indexing it turned that into `KeyError`
        # out of the boot path instead of a sentence and exit code 1.
        network = FakeNetwork()
        with patch.object(onboarding.Onboarder, "status",
                          side_effect=RuntimeError("synthetic")):
            with self.assertLogs(installer.LOGGER, level="WARNING") as logs:
                self.assertEqual(self.boot(network), 1)
        text = "\n".join(logs.output)
        self.assertIn("The setup access point is not up", text)
        self.assertIn("could not be read", text)

    def test_an_ordinary_boot_names_the_flag_rather_than_the_device(self):
        # A development boot has no stored mode, so the flag decided and the
        # override line must stay out of the journal. Without this, an
        # `if True:` on that line prints a false claim on every boot.
        network = FakeNetwork()
        with patch.object(onboarding, "serve",
                          side_effect=OSError(98, "Address already in use")):
            with self.assertLogs(installer.LOGGER, level="WARNING") as logs:
                self.assertEqual(self.boot(network), 1)
        text = "\n".join(logs.output)
        self.assertNotIn("was set on the device", text,
                         "an ordinary boot claimed the device decided the mode")
        self.assertIn("setup network is OPEN: mode none, from --setup-security", text,
                      "the open network was not attributed to the flag that set it")

    def test_an_upgraded_record_is_named_as_why_the_mode_is_not_the_flag(self):
        # A schema-2 record carries a password, so the boot protects the network
        # even though the unit says `none`. The installer's warning is about the
        # flag it wrote, so the journal has to say which one won, or the only
        # thing anybody reads about the mode is wrong.
        state = self.state / "setup.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps(dict(
            state_module.blank("debra-abc123"), schema=2, phase="hotspot",
            hotspot={"ssid": "Debra-Setup-abc123", "interface": "wlan0"},
            hotspot_password="abcdefghjk2m")), encoding="utf-8")
        network = FakeNetwork()
        # The failed bind below takes the access point back down, so the
        # password is recorded as it is handed to the adapter.
        used = []
        real = network.start_hotspot

        def start_hotspot(name, interface, password=None):
            used.append(password)
            return real(name, interface, password)

        network.start_hotspot = start_hotspot
        with patch.object(onboarding, "serve",
                          side_effect=OSError(98, "Address already in use")):
            with self.assertLogs(installer.LOGGER, level="WARNING") as logs:
                self.assertEqual(self.boot(network, security="none"), 1)
        text = "\n".join(logs.output)
        self.assertIn("mode wpa was set on the device, not by --setup-security none",
                      text)
        self.assertNotIn("setup network is OPEN", text)
        self.assertEqual(used, ["abcdefghjk2m"],
                         "the upgraded device was not protected by its old password")

    def test_a_page_choice_is_named_instead_of_the_flag(self):
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / "setup-security").write_text("none\n", encoding="utf-8")
        network = FakeNetwork()
        with patch.object(onboarding, "serve",
                          side_effect=OSError(98, "Address already in use")):
            with self.assertLogs(installer.LOGGER, level="WARNING") as logs:
                self.assertEqual(self.boot(network, security="wpa"), 1)
        text = "\n".join(logs.output)
        self.assertIn("mode none was set on the device, not by --setup-security wpa",
                      text)
        self.assertIn("from the setup page", text,
                      "an open network chosen on the page was blamed on the flag")

    def test_a_device_with_no_wifi_interface_reports_instead_of_listening(self):
        network = FakeNetwork(interface=None)
        # The address cannot be bound here, so returning rather than raising
        # proves the portal was never started.
        with self.assertLogs(installer.LOGGER, level="ERROR") as logs:
            self.assertEqual(self.boot(network), 1)
        self.assertIn("No Wi-Fi interface was found", "\n".join(logs.output))
        data = state_module.read(self.state / "setup.json")
        self.assertEqual(data["phase"], "failed")
        self.assertIsNone(data["hotspot"])
        self.assertIsNone(network.hotspot)

    def test_a_portal_that_cannot_bind_takes_the_access_point_back_down(self):
        # The access point is already up when the bind happens. Leaving it up
        # with no page gives a beginner a network that answers nothing and no
        # way to find out why.
        network = FakeNetwork()
        with patch.object(onboarding, "serve",
                          side_effect=OSError(98, "Address already in use")):
            with self.assertLogs(installer.LOGGER, level="ERROR") as logs:
                self.assertEqual(self.boot(network), 1)
        self.assertIsNone(network.hotspot, "the setup network stayed up with no page")
        data = state_module.read(self.state / "setup.json")
        self.assertEqual(data["phase"], "failed")
        self.assertIsNone(data["hotspot"])
        self.assertEqual(data["last_error"],
                         "The setup page could not start on this device")
        self.assertIn("could not listen", "\n".join(logs.output))
        self.assertNotIn("Address already in use", "\n".join(logs.output),
                         "the raw error text reached the journal")

    def test_the_portal_stops_once_the_device_is_online(self):
        network = FakeNetwork()
        note = self.scratch / "boot/debra-setup.txt"
        outcome = {}
        thread = threading.Thread(
            target=lambda: outcome.setdefault("code", installer.serve(
                self.state, note, network=network, address=("127.0.0.1", 0),
                capture_root=self.scratch / "fake-root", uplink_wait=0,
                poll=0.05, grace=0.2)),
            daemon=True)
        with self.assertLogs(installer.LOGGER, level="WARNING") as logs:
            thread.start()
            state_path = self.state / "setup.json"
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if state_path.exists() and state_module.read(state_path)["phase"] == "hotspot":
                    break
                time.sleep(0.02)
            else:
                self.fail("the setup page never reached the hotspot phase")
            # The state write and the note are separate steps, so a fast poll
            # can observe `hotspot` in the window before the note exists. Read
            # only once it is there; otherwise this test is a load-dependent
            # FileNotFoundError rather than a measurement.
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and not note.exists():
                time.sleep(0.02)
            self.assertTrue(note.exists(), "the setup note was never written")
            # The service writes the note a person needs before any page loads.
            self.assertIn("Debra-Setup-", note.read_text())
            self.assertEqual(file_mode(state_path), 0o600)
            # And it reprints the note once the socket is bound. The access
            # point here reports no address, so the first note carries the
            # documented default; the printed address must be the one that is
            # actually listening, or the first step of setup is a dead link.
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and "127.0.0.1" not in note.read_text():
                time.sleep(0.02)
            text = note.read_text()
            self.assertIn("127.0.0.1", text,
                          "the note does not name the address the page is bound to")
            self.assertNotIn("10.42.0.1", text)
            # A successful join is what the portal's own worker would record.
            data = state_module.read(state_path)
            data.update(phase="online", ssid="HomeWiFi", address="192.0.2.40",
                        hotspot=None)
            state_module.write(state_path, data)
            thread.join(timeout=10)
        self.assertFalse(thread.is_alive(), "the setup page was left listening")
        self.assertEqual(outcome.get("code"), 0)
        self.assertIn("start_hotspot", network.phases())
        # This fixture never captures a baseline, so the bounded wait says so
        # instead of waiting for ever or exiting mid-capture.
        self.assertIn("No baseline was recorded", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()


class PortalAddressTests(unittest.TestCase):
    """The page binds to the address the access point actually got."""

    class Network:
        def __init__(self, address):
            self.address = address

        def device_address(self, interface):
            return self.address if interface else None

    def test_the_discovered_address_is_used(self):
        status = {"hotspot": {"interface": "wlan0"}}
        self.assertEqual(installer.hotspot_address(self.Network("192.168.4.1"), status),
                         "192.168.4.1")

    def test_the_documented_default_is_only_a_fallback(self):
        status = {"hotspot": {"interface": "wlan0"}}
        self.assertEqual(installer.hotspot_address(self.Network(None), status),
                         installer.PORTAL_ADDRESS)

    def test_an_adapter_that_cannot_answer_falls_back_instead_of_failing(self):
        class Broken:
            def device_address(self, interface):
                raise installer.nm_module.NmError("nmcli timed out")
        status = {"hotspot": {"interface": "wlan0"}}
        with self.assertLogs(installer.LOGGER, level="WARNING"):
            self.assertEqual(installer.hotspot_address(Broken(), status),
                             installer.PORTAL_ADDRESS)

    def test_no_hotspot_means_no_address_to_read(self):
        self.assertEqual(installer.hotspot_address(self.Network("192.168.4.1"), {}),
                         installer.PORTAL_ADDRESS)


class EnableTests(Fixture):
    """A tree prepared from a host, for a card that has no running systemd.

    Without the wants link nothing in this repository makes the setup service
    run on a first boot, and the first boot is the only place the journey is
    ever tried before a person has a console.
    """

    def wants_link(self):
        return self.root / installer.WANTS / installer.UNIT_NAME

    def test_enable_links_the_unit_where_systemd_looks_for_it_at_boot(self):
        result = self.install()
        path = installer.enable(self.root)
        link = Path(path)
        self.assertTrue(link.is_symlink(), "enable did not create a link")
        self.assertEqual(os.readlink(link), os.path.join("..", installer.UNIT_NAME))
        self.assertEqual(link.resolve(), self.unit.resolve(),
                         "the link does not resolve to the installed unit")
        self.assertTrue(self.unit.read_text(encoding="utf-8").startswith(installer.MARKER))
        self.assertEqual(result["changed"], True)

    def test_a_plain_install_still_enables_nothing(self):
        # Preparing files must not decide that a root network service runs from
        # now on; that stays an explicit choice.
        self.install()
        self.assertFalse(self.wants_link().exists())
        self.assertFalse((self.root / installer.WANTS).exists())

    def test_enable_twice_changes_nothing(self):
        self.install()
        first = installer.enable(self.root)
        second = installer.enable(self.root)
        self.assertEqual(first, second)
        self.assertEqual(os.readlink(self.wants_link()), os.path.join("..", installer.UNIT_NAME))

    def test_an_absolute_wants_link_to_the_same_unit_is_accepted(self):
        # `systemctl enable` writes an absolute target for a unit under
        # /etc/systemd/system. Refusing it made `--enable` refuse a tree systemd
        # had already enabled, and exit 2 after installing the files.
        self.install()
        wants = self.root / installer.WANTS
        wants.mkdir(parents=True)
        link = wants / installer.UNIT_NAME
        link.symlink_to("/" + installer.UNIT.as_posix())
        self.assertEqual(installer.enable(self.root), str(link))
        self.assertEqual(os.readlink(link), "/" + installer.UNIT.as_posix(),
                         "enable replaced a link systemd had already made")

    def test_a_wants_link_to_another_unit_is_still_refused(self):
        # A link that resolves somewhere else is the operator's, not ours.
        self.install()
        wants = self.root / installer.WANTS
        wants.mkdir(parents=True)
        link = wants / installer.UNIT_NAME
        link.symlink_to("/etc/systemd/system/something-else.service")
        with self.assertRaisesRegex(ValueError, "not this unit on the device"):
            installer.enable(self.root)
        self.assertEqual(os.readlink(link), "/etc/systemd/system/something-else.service")

    def test_a_link_that_jumps_through_a_symlink_to_a_foreign_unit_is_refused(self):
        # `normpath` removes `jump/..` without looking at `jump`, so a link
        # spelled `../jump/../debra-setup.service` compared equal to the
        # installed unit while the kernel resolved it into another directory.
        # Destination comparison alone did not fix it either: `realpath()` is not
        # strict, so it normalizes through the missing directory and returns a
        # path that names nothing. Only the two spellings an enablement writes
        # are accepted now, so this is refused before anything is resolved.
        self.install()
        system = self.root / "etc/systemd/system"
        foreign = self.root / "foreign"
        (foreign / "directory").mkdir(parents=True)
        (foreign / "debra-setup.service").write_text("not the installed unit\n", encoding="utf-8")
        (system / "jump").symlink_to(foreign / "directory")
        wants = self.root / installer.WANTS
        wants.mkdir(parents=True)
        link = wants / installer.UNIT_NAME
        link.symlink_to("../jump/../debra-setup.service")
        self.assertEqual(link.resolve(), (foreign / "debra-setup.service").resolve(),
                         "the fixture does not resolve to the foreign unit")
        with self.assertRaisesRegex(ValueError, "not this unit on the device"):
            installer.enable(self.root)
        self.assertEqual(os.readlink(link), "../jump/../debra-setup.service",
                         "enable replaced the operator's link")

    def test_a_relative_link_to_another_unit_in_the_same_directory_is_refused(self):
        # R8-03. The plain other-unit case above uses an absolute target, which
        # the spelling check refuses before the landing check is reached. The
        # same operator mistake spelled relatively has to be refused too.
        self.install()
        wants = self.root / installer.WANTS
        wants.mkdir(parents=True)
        (self.root / "etc/systemd/system/something-else.service").write_text(
            "x\n", encoding="utf-8")
        link = wants / installer.UNIT_NAME
        link.symlink_to("../something-else.service")
        with self.assertRaisesRegex(ValueError, "not this unit on the device"):
            installer.enable(self.root)
        self.assertEqual(os.readlink(link), "../something-else.service")

    def test_a_canonical_link_whose_kernel_confirmation_fails_is_refused(self):
        # R9-02: the `samefile` confirmation had no repository defender. Removing
        # it, comparing lexically, or comparing only directories each passed all
        # 44 installer tests, because the spelling gate makes the ordinary cases
        # redundant. These are the two ways the confirmation can say no.
        self.install()
        wants = self.root / installer.WANTS
        wants.mkdir(parents=True)
        link = wants / installer.UNIT_NAME
        link.symlink_to(os.path.join("..", installer.UNIT_NAME))
        with patch.object(installer.os.path, "samefile",
                          side_effect=OSError(5, "I/O error")):
            with self.assertRaisesRegex(ValueError, "does not open"):
                installer.enable(self.root)
        self.assertEqual(os.readlink(link), os.path.join("..", installer.UNIT_NAME),
                         "a refusal replaced the link")
        with patch.object(installer.os.path, "samefile", return_value=False):
            with self.assertRaisesRegex(ValueError, "different link"):
                installer.enable(self.root)
        self.assertEqual(os.readlink(link), os.path.join("..", installer.UNIT_NAME))

    def test_two_units_in_one_directory_are_not_the_same_unit(self):
        # R9-02: comparing only the resolved *directory* passed every installer
        # test. Two different managed units can live in the same directory, and
        # the link has to name the one being enabled.
        self.install()
        other = self.root / "etc/systemd/system/other.service"
        other.write_text(installer.MARKER + "[Service]\nExecStart=\"/bin/true\"\n",
                         encoding="utf-8")
        wants = self.root / installer.WANTS
        wants.mkdir(parents=True)
        link = wants / installer.UNIT_NAME
        link.symlink_to(os.path.join("..", installer.UNIT_NAME))
        with self.assertRaisesRegex(ValueError, "different link"):
            installer.enable(self.root, unit=Path("etc/systemd/system/other.service"))
        self.assertEqual(os.readlink(link), os.path.join("..", installer.UNIT_NAME))

    def test_a_link_through_a_missing_directory_is_refused(self):
        # R8-01. `realpath()` suppresses the error and keeps normalizing, so the
        # link was reported as enabled while the kernel could not open it.
        self.install()
        wants = self.root / installer.WANTS
        wants.mkdir(parents=True)
        link = wants / installer.UNIT_NAME
        link.symlink_to("../absent-directory/../debra-setup.service")
        with self.assertRaisesRegex(ValueError, "not this unit on the device"):
            installer.enable(self.root)
        self.assertEqual(os.readlink(link), "../absent-directory/../debra-setup.service")

    def test_a_link_through_a_regular_file_is_refused(self):
        # R8-01, the ENOTDIR half: a component that is a file, not a directory.
        self.install()
        wants = self.root / installer.WANTS
        wants.mkdir(parents=True)
        (self.root / "etc/systemd/system/ordinary-file").write_text("x\n", encoding="utf-8")
        link = wants / installer.UNIT_NAME
        link.symlink_to("../ordinary-file/../debra-setup.service")
        with self.assertRaisesRegex(ValueError, "not this unit on the device"):
            installer.enable(self.root)

    def test_a_cyclic_link_is_refused(self):
        # R8-01, the ELOOP half.
        self.install()
        wants = self.root / installer.WANTS
        wants.mkdir(parents=True)
        (self.root / "etc/systemd/system/cycle").symlink_to("cycle")
        link = wants / installer.UNIT_NAME
        link.symlink_to("../cycle/../debra-setup.service")
        with self.assertRaisesRegex(ValueError, "not this unit on the device"):
            installer.enable(self.root)

    def test_a_relative_link_that_escapes_to_the_preparing_host_is_refused(self):
        # R8-02. The absolute host-prefix refusal did not cover the relative
        # spelling: `../` repeated out to the host's `/` and back into the card
        # opened the host file and was accepted, while on the device the same
        # text names a path that does not exist.
        self.install()
        wants = self.root / installer.WANTS
        wants.mkdir(parents=True)
        link = wants / installer.UNIT_NAME
        depth = len(wants.parts) - 1
        target = "../" * depth + str(self.unit).lstrip("/")
        link.symlink_to(target)
        self.assertEqual(Path(os.path.join(str(wants), target)).resolve(), self.unit.resolve(),
                         "the fixture does not resolve to the host file")
        with self.assertRaisesRegex(ValueError, "not this unit on the device"):
            installer.enable(self.root)
        self.assertEqual(os.readlink(link), target)

    def test_an_absolute_target_that_names_the_preparing_host_is_refused(self):
        # An absolute target is a path on the device. A path that carries the
        # preparing host's mount point names this unit only on the host, and
        # nothing at all after boot.
        self.install()
        wants = self.root / installer.WANTS
        wants.mkdir(parents=True)
        link = wants / installer.UNIT_NAME
        link.symlink_to(str(self.unit))
        with self.assertRaisesRegex(ValueError, "not this unit on the device"):
            installer.enable(self.root)
        self.assertEqual(os.readlink(link), str(self.unit))

    def test_enable_refuses_a_unit_the_installer_did_not_write(self):
        self.unit.parent.mkdir(parents=True, exist_ok=True)
        self.unit.write_text("[Unit]\nDescription=not ours\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "this installer wrote"):
            installer.enable(self.root)
        self.assertFalse(self.wants_link().exists())

    def test_enable_does_not_replace_a_file_that_happens_to_have_the_name(self):
        self.install()
        wants = self.root / installer.WANTS
        wants.mkdir(parents=True)
        link = wants / installer.UNIT_NAME
        link.write_text("an operator's own file\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "not a link"):
            installer.enable(self.root)
        self.assertEqual(link.read_text(encoding="utf-8"), "an operator's own file\n")

    def test_a_symlinked_wants_directory_is_refused_before_anything_is_written(self):
        self.install()
        elsewhere = self.scratch / "elsewhere"
        elsewhere.mkdir()
        wants = self.root / installer.WANTS
        wants.parent.mkdir(parents=True, exist_ok=True)
        wants.symlink_to(elsewhere)
        # Either refusal is correct: the path resolves out of the root, or it is
        # a symlinked directory on the way in.
        with self.assertRaisesRegex(ValueError, "symlinked|resolves outside"):
            installer.enable(self.root)
        self.assertEqual(list(elsewhere.iterdir()), [],
                         "enable wrote through a symlinked directory")

    def test_the_command_line_enables_only_when_asked(self):
        code = installer.main(["--root", str(self.root), "--python", "/usr/bin/python3"])
        self.assertEqual(code, 0)
        self.assertFalse(self.wants_link().exists())
        code = installer.main(["--root", str(self.root), "--python", "/usr/bin/python3",
                               "--enable"])
        self.assertEqual(code, 0)
        self.assertTrue(self.wants_link().is_symlink())
