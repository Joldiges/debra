"""Offline checks for the root HAT helper.

Nothing here runs sudo, writes /boot, reboots, or needs root. The helper takes a
root path, a kernel release and a launcher as arguments for exactly this reason:
the interesting behaviour is what it does to a file, and that can be checked on
a copy of a file.
"""

from io import StringIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from control.setup import hat_install
from control.web import hats

RELEASE = "test-release"
STOCK = """\
# For more options and information see
# http://rpf.io/configtxt
[all]
dtparam=audio=on
camera_auto_detect=1
dtoverlay=vc4-kms-v3d
max_framebuffers=2
[pi5]
dtoverlay=nospi10
[all]
"""


class FakeRoot:
    """A directory shaped like a Raspberry Pi's boot and module tree."""

    def __init__(self, config=STOCK, overlays=("wm8960-soundcard", "respeaker-2mic-v2_0"),
                 modules=("snd-soc-wm8960", "snd-soc-tlv320aic3x"),
                 builtin=(), path="boot/firmware/config.txt"):
        self.directory = Path(tempfile.mkdtemp(prefix="debra-hat-"))
        self.root = self.directory
        self.config = self.root / path
        self.config.parent.mkdir(parents=True, exist_ok=True)
        if config is not None:
            self.config.write_text(config)
            os.chmod(self.config, 0o755)
        overlay_dir = self.config.parent / "overlays"
        overlay_dir.mkdir(parents=True, exist_ok=True)
        for name in overlays:
            (overlay_dir / (name + ".dtbo")).write_bytes(b"dtbo")
        codecs = (self.root / "lib/modules" / RELEASE /
                  "kernel/sound/soc/codecs")
        codecs.mkdir(parents=True, exist_ok=True)
        for name in modules:
            (codecs / (name + ".ko.xz")).write_bytes(b"module")
        builtin_file = self.root / "lib/modules" / RELEASE / "modules.builtin"
        builtin_file.write_text("".join(
            "kernel/sound/soc/codecs/%s.ko\n" % name for name in builtin))

    def backups(self):
        return sorted(self.config.parent.glob(self.config.name + ".debra-*"))

    def cleanup(self):
        shutil.rmtree(self.directory, ignore_errors=True)


class HelperTestCase(unittest.TestCase):
    def setUp(self):
        self.pi = FakeRoot()
        self.addCleanup(self.pi.cleanup)

    def install(self, board, **kwargs):
        return hat_install.install(board, root=self.pi.root, release=RELEASE, **kwargs)


class InstallTests(HelperTestCase):
    def test_it_writes_the_overlay_and_enables_i2c(self):
        answer = self.install("respeaker-2mic-hat-v1")
        text = self.pi.config.read_text()
        self.assertTrue(answer["ok"])
        self.assertTrue(answer["changed"])
        self.assertIn("dtoverlay=wm8960-soundcard\n", text)
        self.assertIn("dtparam=i2c_arm=on\n", text)

    def test_every_unrelated_line_survives_byte_for_byte(self):
        # config.txt decides whether the device boots. A "clean up" that drops a
        # comment or reorders a section is a change nobody asked for.
        before = self.pi.config.read_text().splitlines()
        self.install("respeaker-2mic-hat-v1")
        after = self.pi.config.read_text().splitlines()
        kept = [line for line in before if line != ""]
        for line in kept:
            self.assertIn(line, after)
        # Only two lines are new: the dtparam and the overlay.
        added = [line for line in after if line not in kept]
        self.assertEqual(added, ["dtparam=i2c_arm=on", "dtoverlay=wm8960-soundcard"])

    def test_the_graphics_and_usb_overlays_are_not_managed(self):
        self.install("respeaker-2mic-hat-v1")
        text = self.pi.config.read_text()
        self.assertIn("dtoverlay=vc4-kms-v3d\n", text)
        self.assertIn("dtoverlay=nospi10\n", text)

    def test_a_second_audio_overlay_is_replaced_not_stacked(self):
        # Two audio HAT overlays at once is a conflict, not a configuration.
        self.pi.config.write_text(STOCK + "dtoverlay=wm8960-soundcard\n")
        answer = self.install("respeaker-2mic-hat-v2")
        text = self.pi.config.read_text()
        self.assertEqual(answer["dropped"], ["wm8960-soundcard"])
        self.assertNotIn("dtoverlay=wm8960-soundcard", text)
        self.assertIn("dtoverlay=respeaker-2mic-v2_0\n", text)
        self.assertEqual(text.count("dtoverlay=respeaker-2mic-v2_0"), 1)

    def test_installing_twice_writes_once(self):
        self.install("respeaker-2mic-hat-v1")
        first = self.pi.config.read_bytes()
        answer = self.install("respeaker-2mic-hat-v1")
        self.assertFalse(answer["changed"])
        self.assertEqual(self.pi.config.read_bytes(), first)
        self.assertEqual(len(self.pi.backups()), 1, "a no-op install made another backup")

    def test_each_change_keeps_its_own_backup(self):
        self.install("respeaker-2mic-hat-v1")
        self.install("respeaker-2mic-hat-v2")
        backups = self.pi.backups()
        self.assertEqual(len(backups), 2, [str(path) for path in backups])
        self.assertNotEqual(backups[0].read_text(), backups[1].read_text())
        # The oldest backup is the stock file, untouched.
        self.assertEqual(sorted(backups)[0].read_text(), STOCK)

    def test_the_backup_is_taken_before_the_change(self):
        self.install("respeaker-2mic-hat-v1")
        backup = self.pi.backups()[0]
        self.assertEqual(backup.read_text(), STOCK)
        self.assertNotEqual(self.pi.config.read_text(), STOCK)

    def test_the_file_keeps_its_mode(self):
        os.chmod(self.pi.config, 0o755)
        self.install("respeaker-2mic-hat-v1")
        self.assertEqual(self.pi.config.stat().st_mode & 0o777, 0o755)

    def test_no_temporary_file_is_left_behind(self):
        self.install("respeaker-2mic-hat-v1")
        leftovers = [path.name for path in self.pi.config.parent.iterdir()
                     if ".pending" in path.name or "debra-new" in path.name]
        self.assertEqual(leftovers, [])

    def test_a_conditional_tail_gets_an_all_section(self):
        # A file ending inside [pi5] would make the new line apply to one model.
        self.pi.config.write_text("[all]\ndtparam=audio=on\n[pi5]\ndtoverlay=nospi10\n")
        self.install("respeaker-2mic-hat-v1")
        lines = self.pi.config.read_text().splitlines()
        self.assertEqual(lines[-2:], ["[all]", "dtoverlay=wm8960-soundcard"])

    def test_an_existing_all_section_is_not_repeated(self):
        before = self.pi.config.read_text().count("[all]")
        self.install("respeaker-2mic-hat-v1")
        self.assertEqual(self.pi.config.read_text().count("[all]"), before)

    def test_a_commented_i2c_line_is_uncommented_not_duplicated(self):
        self.pi.config.write_text("#dtparam=i2c_arm=on\ndtparam=audio=on\n[all]\n")
        self.install("respeaker-2mic-hat-v1")
        text = self.pi.config.read_text()
        self.assertEqual(text.count("i2c_arm"), 1)
        self.assertTrue(text.startswith("dtparam=i2c_arm=on\n"), text)

    def test_a_missing_final_newline_does_not_join_two_settings(self):
        self.pi.config.write_text("[all]\ndtparam=audio=on")
        self.install("respeaker-2mic-hat-v1")
        lines = self.pi.config.read_text().splitlines()
        self.assertIn("dtparam=audio=on", lines)
        self.assertIn("dtoverlay=wm8960-soundcard", lines)

    def test_choosing_no_hat_removes_the_managed_overlay(self):
        self.pi.config.write_text(STOCK + "dtoverlay=wm8960-soundcard\n")
        answer = self.install("none")
        text = self.pi.config.read_text()
        self.assertTrue(answer["changed"])
        self.assertNotIn("dtoverlay=wm8960-soundcard", text)
        self.assertIn("dtparam=audio=on", text)

    def test_the_answer_says_the_running_system_is_unchanged(self):
        answer = self.install("respeaker-2mic-hat-v1")
        self.assertIn("restart", answer["note"])
        self.assertNotIn("rebooting", answer)


class RefusalTests(HelperTestCase):
    def test_an_unknown_board_writes_nothing(self):
        before = self.pi.config.read_bytes()
        with self.assertRaises(hat_install.Refused) as caught:
            self.install("respeaker-8mic")
        self.assertIn("not a board this helper knows", str(caught.exception))
        self.assertEqual(self.pi.config.read_bytes(), before)
        self.assertEqual(self.pi.backups(), [])

    def test_an_overlay_the_image_lacks_writes_nothing(self):
        pi = FakeRoot(overlays=("wm8960-soundcard",))
        self.addCleanup(pi.cleanup)
        before = pi.config.read_bytes()
        with self.assertRaises(hat_install.Refused) as caught:
            hat_install.install("respeaker-2mic-hat-v2", root=pi.root, release=RELEASE)
        self.assertIn("respeaker-2mic-v2_0", str(caught.exception))
        self.assertEqual(pi.config.read_bytes(), before)

    def test_a_missing_codec_module_writes_nothing(self):
        pi = FakeRoot(modules=("snd-soc-tlv320aic3x",))
        self.addCleanup(pi.cleanup)
        before = pi.config.read_bytes()
        with self.assertRaises(hat_install.Refused) as caught:
            hat_install.install("respeaker-2mic-hat-v1", root=pi.root, release=RELEASE)
        self.assertIn("snd-soc-wm8960", str(caught.exception))
        self.assertEqual(pi.config.read_bytes(), before)

    def test_a_built_in_module_counts_as_present(self):
        pi = FakeRoot(modules=(), builtin=("snd-soc-wm8960",))
        self.addCleanup(pi.cleanup)
        answer = hat_install.install("respeaker-2mic-hat-v1", root=pi.root,
                                     release=RELEASE)
        self.assertTrue(answer["changed"])

    def test_no_boot_configuration_writes_nothing(self):
        pi = FakeRoot(config=None)
        self.addCleanup(pi.cleanup)
        with self.assertRaises(hat_install.Refused) as caught:
            hat_install.install("respeaker-2mic-hat-v1", root=pi.root, release=RELEASE)
        self.assertIn("No boot configuration", str(caught.exception))

    def test_a_read_only_configuration_is_refused(self):
        os.chmod(self.pi.config, 0o444)
        if os.access(self.pi.config, os.W_OK):
            self.skipTest("running as a user that ignores file modes")
        with self.assertRaises(hat_install.Refused) as caught:
            self.install("respeaker-2mic-hat-v1")
        self.assertIn("not writable", str(caught.exception))


class VerifyTests(unittest.TestCase):
    def test_a_file_that_lost_the_overlay_is_caught(self):
        with self.assertRaises(hat_install.Refused):
            hat_install.verify("[all]\ndtoverlay=vc4-kms-v3d\n", "wm8960-soundcard",
                               True, hats.MANAGED_OVERLAYS)

    def test_two_managed_overlays_are_caught(self):
        text = "dtoverlay=wm8960-soundcard\ndtoverlay=respeaker-2mic-v2_0\n"
        with self.assertRaises(hat_install.Refused):
            hat_install.verify(text, "respeaker-2mic-v2_0", False, hats.MANAGED_OVERLAYS)

    def test_a_missing_i2c_line_is_caught(self):
        with self.assertRaises(hat_install.Refused) as caught:
            hat_install.verify("dtoverlay=wm8960-soundcard\n", "wm8960-soundcard",
                               True, hats.MANAGED_OVERLAYS)
        self.assertIn("I2C", str(caught.exception))

    def test_a_commented_i2c_line_does_not_count(self):
        with self.assertRaises(hat_install.Refused):
            hat_install.verify("#dtparam=i2c_arm=on\ndtoverlay=wm8960-soundcard\n",
                               "wm8960-soundcard", True, hats.MANAGED_OVERLAYS)

    def test_an_unmanaged_overlay_is_not_mistaken_for_the_board(self):
        with self.assertRaises(hat_install.Refused):
            hat_install.verify("dtoverlay=vc4-kms-v3d\n", "wm8960-soundcard",
                               False, hats.MANAGED_OVERLAYS)

    def test_a_removal_leaving_a_managed_overlay_is_caught(self):
        with self.assertRaises(hat_install.Refused):
            hat_install.verify("dtoverlay=wm8960-soundcard\n", None, False,
                               hats.MANAGED_OVERLAYS)


class FailedWriteTests(unittest.TestCase):
    def test_a_write_that_does_not_verify_is_rolled_back(self):
        # The one failure that matters: a config that says something other than
        # what was asked for must not survive the request.
        pi = FakeRoot()
        self.addCleanup(pi.cleanup)
        real_verify = hat_install.verify
        calls = {"n": 0}

        def verify_then_fail(text, overlay, needs_i2c, managed):
            calls["n"] += 1
            if calls["n"] == 1:
                return real_verify(text, overlay, needs_i2c, managed)
            raise hat_install.Refused("pretend the file came out wrong")

        with patch.object(hat_install, "verify", verify_then_fail):
            with self.assertRaises(hat_install.Refused) as caught:
                hat_install.install("respeaker-2mic-hat-v1", root=pi.root,
                                    release=RELEASE)
        self.assertIn("restored", str(caught.exception))
        self.assertEqual(pi.config.read_text(), STOCK, "the old config was not put back")


class RunTests(unittest.TestCase):
    def setUp(self):
        self.pi = FakeRoot()
        self.addCleanup(self.pi.cleanup)

    def test_a_known_board_is_accepted(self):
        answer = hat_install.run({"verb": "install", "board": "respeaker-2mic-hat-v1"},
                                 root=self.pi.root, release=RELEASE)
        self.assertTrue(answer["ok"])

    def test_an_unknown_verb_is_refused(self):
        with self.assertRaises(hat_install.Refused) as caught:
            hat_install.run({"verb": "reflash"}, root=self.pi.root, release=RELEASE)
        self.assertIn("not one of", str(caught.exception))

    def test_an_extra_field_is_refused(self):
        # The request shape is part of the boundary: a field nobody reads is a
        # sign the caller thinks this program does something it does not.
        with self.assertRaises(hat_install.Refused):
            hat_install.run({"verb": "remove", "overlay": "anything"},
                            root=self.pi.root, release=RELEASE)

    def test_a_request_that_is_not_an_object_is_refused(self):
        with self.assertRaises(hat_install.Refused):
            hat_install.run(["install"], root=self.pi.root, release=RELEASE)

    def test_install_needs_a_board_id(self):
        with self.assertRaises(hat_install.Refused):
            hat_install.run({"verb": "install"}, root=self.pi.root, release=RELEASE)

    def test_a_board_id_must_be_a_string(self):
        with self.assertRaises(hat_install.Refused):
            hat_install.run({"verb": "install", "board": 671}, root=self.pi.root,
                            release=RELEASE)

    def test_reboot_is_started_only_by_the_reboot_verb(self):
        started = []
        answer = hat_install.run({"verb": "reboot"}, root=self.pi.root,
                                 launch=started.append)
        self.assertEqual(started, [2], "the reboot was not delayed")
        self.assertTrue(answer["rebooting"])

    def test_install_never_starts_a_reboot(self):
        started = []
        hat_install.run({"verb": "install", "board": "respeaker-2mic-hat-v1"},
                        root=self.pi.root, release=RELEASE)
        self.assertEqual(started, [])


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.pi = FakeRoot()
        self.addCleanup(self.pi.cleanup)

    def call(self, text, argv=(), root=None):
        out = StringIO()
        with patch.object(hat_install.os, "geteuid", return_value=0):
            code = hat_install.main(stdin=StringIO(text), stdout=out, argv=list(argv))
        return code, json.loads(out.getvalue() or "{}")

    def test_arguments_are_refused(self):
        # sudoers allows exactly this program with no arguments. A call with
        # arguments is not the call that was reviewed.
        code, answer = self.call('{"verb": "remove"}', argv=["--force"])
        self.assertEqual(code, 2)
        self.assertFalse(answer["ok"])
        self.assertIn("no arguments", answer["reason"])

    def test_a_body_that_is_not_json_is_refused(self):
        code, answer = self.call("not json")
        self.assertEqual(code, 2)
        self.assertFalse(answer["ok"])

    def test_running_without_root_changes_nothing(self):
        out = StringIO()
        with patch.object(hat_install.os, "geteuid", return_value=1000):
            code = hat_install.main(stdin=StringIO(
                '{"verb": "install", "board": "respeaker-2mic-hat-v1"}'), stdout=out,
                argv=[])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(out.getvalue())["ok"])
        self.assertIn("must run as root", json.loads(out.getvalue())["reason"])

    def test_a_refusal_is_an_answer_not_a_crash(self):
        # The page shows the reason, so a refusal must arrive as JSON on stdout
        # with a success exit status: it is an answer, not a broken pipe.
        code, answer = self.call('{"verb": "install", "board": "nope"}', root=None)
        self.assertEqual(code, 0)
        self.assertFalse(answer["ok"])
        self.assertIn("not a board", answer["reason"])


class EnrollTests(unittest.TestCase):
    """Enrolment: four files, two systemd calls, and nothing else."""

    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="debra-enroll-"))
        self.addCleanup(shutil.rmtree, self.directory, True)
        self.root = self.directory
        self.source = self.root / "source-helper.py"
        self.source.write_text("# the helper as it was run\n")
        self.systemd = []

    def runner(self, argv, **kwargs):
        self.systemd.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    def enroll(self, **kwargs):
        arguments = {"user": "debra", "source": self.source, "runner": self.runner}
        arguments.update(kwargs)
        return hat_install.enroll(root=self.root, **arguments)

    def test_it_installs_the_helper_the_table_and_both_units(self):
        answer = self.enroll()
        helper = self.root / hat_install.INSTALLED_HELPER
        table = self.root / hat_install.INSTALLED_TABLE
        socket = self.root / hat_install.INSTALLED_SOCKET
        service = self.root / hat_install.INSTALLED_SERVICE
        for path in (helper, table, socket, service):
            self.assertTrue(path.is_file(), path)
        self.assertEqual(helper.stat().st_mode & 0o777, 0o755)
        self.assertEqual(socket.stat().st_mode & 0o777, 0o644)
        self.assertEqual(answer["group"], "debra")
        # The table installed is the one the page reads, not a copy of a copy.
        self.assertEqual(table.read_bytes(),
                         Path(hat_install.table_file()).read_bytes())

    def test_the_socket_is_opened_for_the_pages_group_only(self):
        self.enroll(group="debra")
        text = (self.root / hat_install.INSTALLED_SOCKET).read_text()
        self.assertIn("ListenStream=/run/debra-hat/control.sock", text)
        self.assertIn("SocketGroup=debra", text)
        self.assertIn("SocketMode=0660", text)
        self.assertIn("Accept=yes", text)
        self.assertNotIn("@GROUP@", text)

    def test_the_service_reads_the_connection_as_standard_input(self):
        self.enroll()
        text = (self.root / hat_install.INSTALLED_SERVICE).read_text()
        self.assertIn("StandardInput=socket", text)
        self.assertIn("StandardOutput=socket", text)
        self.assertIn(hat_install.INSTALLED_HELPER, text)
        # The helper runs as root by the unit, and must not be able to gain more.
        self.assertIn("NoNewPrivileges=yes", text)

    def test_it_tells_systemd_and_starts_the_socket(self):
        self.enroll()
        self.assertEqual(self.systemd, [["systemctl", "daemon-reload"],
                                        ["systemctl", "enable", "--now",
                                         "debra-hat.socket"]])

    def test_it_can_write_the_files_without_activating(self):
        answer = self.enroll(activate=False)
        self.assertEqual(self.systemd, [])
        self.assertIn("not told", answer["note"])

    def test_a_systemd_refusal_is_reported(self):
        def refuse(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 1, "", "Unit not found")

        with self.assertRaises(hat_install.Refused) as caught:
            hat_install.enroll(root=self.root, user="debra", source=self.source,
                               runner=refuse)
        self.assertIn("systemd refused", str(caught.exception))

    def test_it_refuses_without_the_invoking_user(self):
        with self.assertRaises(hat_install.Refused) as caught:
            self.enroll(user="")
        self.assertIn("sudo", str(caught.exception))

    def test_it_refuses_to_open_the_socket_for_root(self):
        with self.assertRaises(hat_install.Refused):
            self.enroll(user="root")

    def test_a_name_that_is_not_a_name_is_refused(self):
        for bad in ("debra\nALL=(ALL) NOPASSWD: ALL", "de bra", "a/b"):
            with self.subTest(name=bad):
                with self.assertRaises(hat_install.Refused):
                    self.enroll(user=bad)
                with self.assertRaises(hat_install.Refused):
                    self.enroll(group=bad)

    def test_enrolling_twice_changes_nothing_the_second_time(self):
        self.enroll()
        answer = self.enroll()
        self.assertFalse(answer["changed"])
        self.assertEqual(answer["installed"], [])

    def test_it_writes_no_sudoers_file(self):
        # The transport is a socket precisely so that no passwordless sudo rule
        # exists on the device for anyone to widen.
        self.enroll()
        self.assertEqual(list(self.root.rglob("*sudoers*")), [])

    def test_it_retires_the_unreleased_sudo_rule(self):
        # An earlier enrolment on a lab device wrote this rule. It grants root
        # for a call the page no longer makes, so enrolment takes it away.
        legacy = self.root / hat_install.LEGACY_SUDOERS
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(hat_install.LEGACY_MARKER + "\ndebra ALL=(root) NOPASSWD: x \"\"\n")
        answer = self.enroll()
        self.assertFalse(legacy.exists())
        self.assertEqual(answer["retired"], [str(legacy)])

    def test_it_leaves_a_sudoers_file_it_did_not_write(self):
        # Only a file with our own first line is ours to remove.
        legacy = self.root / hat_install.LEGACY_SUDOERS
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text("# somebody else's rule\nroot ALL=(ALL) ALL\n")
        self.enroll()
        self.assertTrue(legacy.exists())
        self.assertEqual(legacy.read_text(),
                         "# somebody else's rule\nroot ALL=(ALL) ALL\n")


class TableAgreementTests(unittest.TestCase):
    def test_every_board_has_an_install_answer(self):
        # The page offers a button per board, so every board must say what
        # installing it means — including the ones that mean "remove".
        for entry in hats.HAT_OPTIONS:
            self.assertIn("overlay", entry)
            self.assertIn("modules", entry)
            self.assertIn("needs_i2c", entry)
            self.assertTrue(entry["install_note"])

    def test_the_managed_set_is_exactly_the_overlays_the_table_names(self):
        named = {entry["overlay"] for entry in hats.HAT_OPTIONS if entry["overlay"]}
        self.assertEqual(set(hats.MANAGED_OVERLAYS), named)

    def test_the_page_and_the_helper_read_the_same_table(self):
        # Two answers to "which overlay is this board" is how a root helper and
        # a web page drift apart. There is one file.
        self.assertEqual(Path(hat_install.table_file()).resolve(),
                         Path(hats.__file__).resolve())

    def test_every_module_named_is_a_real_module_name(self):
        for entry in hats.HAT_OPTIONS:
            for name in entry["modules"]:
                self.assertRegex(name, r"^[a-z0-9-]+$")


if __name__ == "__main__":
    unittest.main()
