"""Applying the device name: the two consumers `hostnamectl` does not tell.

Every test here runs offline. The point is the contract, not a radio: a rename
must leave `/etc/hosts` and the running mDNS responder naming the device the
state file and the page claim it is called.

Observed on the Zero 2 W (`docs/testing/results/2026-11-15-zero2w-setup-service-first-run.md`):
after a rename, `hostname -f` answered "Name or service not known", every `sudo`
printed `unable to resolve host <new name>`, and `avahi` still answered the old
`<name>.local` until it was restarted.
"""

import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "control" / "setup"))

import nm as nm_module  # noqa: E402


DEBIAN_HOSTS = """\
# Your system has configured 'manage_etc_hosts' as True.
# a.) make changes to the master file in /etc/cloud/templates/hosts.debian.tmpl
127.0.1.1 debra-lab debra-lab
127.0.0.1 localhost

# The following lines are desirable for IPv6 capable hosts
::1 localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
"""


class Recorder:
    """A stand-in for `_run` that answers the hostname and systemctl commands."""

    def __init__(self, mdns="active", rename_fails=False, mdns_fails=False):
        self.calls = []
        self.mdns = mdns
        self.rename_fails = rename_fails
        self.mdns_fails = mdns_fails

    def __call__(self, argv, timeout=None):
        self.calls.append(list(argv))
        if argv[:2] == ["hostnamectl", "set-hostname"]:
            if self.rename_fails:
                raise nm_module.NmError("hostnamectl could not be run")
            return ""
        if argv[:3] == ["systemctl", "is-active", nm_module.MDNS_UNIT]:
            if self.mdns == "absent":
                # `systemctl is-active` exits non-zero for a unit that is not
                # running and for one that does not exist.
                raise nm_module.NmError("systemctl could not be run")
            return self.mdns + "\n"
        if argv[:2] == ["systemctl", "try-restart"]:
            if self.mdns_fails:
                raise nm_module.NmError("systemctl could not be run")
            return ""
        return ""

    def commands(self):
        return [" ".join(call) for call in self.calls]


class Temp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.hosts = self.dir / "hosts"
        self.addCleanup(self._tmp.cleanup)

    def write_hosts(self, text=DEBIAN_HOSTS, mode=0o644):
        self.hosts.write_text(text, encoding="utf-8")
        self.hosts.chmod(mode)

    def adapter(self, recorder, hosts_path=None):
        return nm_module.Nmcli(runner=recorder,
                               hosts_path=hosts_path or self.hosts)


class HostsNamingTests(Temp):
    def test_the_alias_is_replaced_and_everything_else_keeps_its_text(self):
        updated = nm_module.hosts_naming(DEBIAN_HOSTS, "debra-8518d6")
        self.assertIn("127.0.1.1 debra-8518d6 debra-8518d6\n", updated)
        self.assertNotIn("debra-lab", updated)
        for untouched in ("# Your system has configured",
                          "127.0.0.1 localhost",
                          "::1 localhost ip6-localhost ip6-loopback",
                          "ff02::2 ip6-allrouters"):
            self.assertIn(untouched, updated)

    def test_a_second_name_on_the_alias_line_is_dropped(self):
        # What cloud-init left after the observed rename: the current name as the
        # fully qualified one, the previous device name as the short one. Keeping
        # `debra-lab` means the device still resolves a name it no longer has.
        text = "127.0.1.1 debra-8518d6 debra-lab\n127.0.0.1 localhost\n"
        self.assertEqual(nm_module.hosts_naming(text, "debra-8518d6"),
                         "127.0.1.1 debra-8518d6 debra-8518d6\n127.0.0.1 localhost\n")

    def test_a_second_alias_line_is_removed_rather_than_left_stale(self):
        text = "127.0.1.1 old old\n127.0.0.1 localhost\n127.0.1.1 also-old also-old\n"
        self.assertEqual(nm_module.hosts_naming(text, "new"),
                         "127.0.1.1 new new\n127.0.0.1 localhost\n")

    def test_an_alias_is_added_beside_localhost_when_there_is_none(self):
        text = "127.0.0.1 localhost\n::1 localhost ip6-localhost ip6-loopback\n"
        self.assertEqual(
            nm_module.hosts_naming(text, "debra-8518d6"),
            "127.0.0.1 localhost\n127.0.1.1 debra-8518d6 debra-8518d6\n"
            "::1 localhost ip6-localhost ip6-loopback\n")

    def test_a_file_with_an_alias_but_no_localhost_gains_one(self):
        # A truncated file must not come back unable to resolve localhost.
        updated = nm_module.hosts_naming("127.0.1.1 debra-lab debra-lab\n", "debra-8518d6")
        self.assertEqual(updated,
                         "127.0.1.1 debra-8518d6 debra-8518d6\n127.0.0.1 localhost\n")

    def test_an_empty_file_becomes_a_resolvable_one(self):
        self.assertEqual(nm_module.hosts_naming("", "debra-8518d6"),
                         "127.0.0.1 localhost\n127.0.1.1 debra-8518d6 debra-8518d6\n")

    def test_applying_the_same_name_twice_changes_nothing_the_second_time(self):
        once = nm_module.hosts_naming(DEBIAN_HOSTS, "debra-8518d6")
        self.assertEqual(once, nm_module.hosts_naming(once, "debra-8518d6"))

    def test_a_crlf_file_is_rewritten_with_lf_and_keeps_its_lines(self):
        text = "127.0.1.1 old old\r\n127.0.0.1 localhost\r\n::1 localhost\r\n"
        self.assertEqual(nm_module.hosts_naming(text, "new"),
                         "127.0.1.1 new new\n127.0.0.1 localhost\n::1 localhost\n")

    def test_a_commented_alias_is_not_the_alias(self):
        text = "#127.0.1.1 old old\n127.0.0.1 localhost\n"
        self.assertEqual(nm_module.hosts_naming(text, "new"),
                         "#127.0.1.1 old old\n127.0.0.1 localhost\n127.0.1.1 new new\n")

    def test_tabs_between_fields_are_accepted(self):
        text = "127.0.1.1\told\told\n127.0.0.1\tlocalhost\n"
        self.assertEqual(nm_module.hosts_naming(text, "new"),
                         "127.0.1.1 new new\n127.0.0.1\tlocalhost\n")


class SetHostnameTests(Temp):
    def test_a_rename_rewrites_the_alias_and_restarts_the_responder(self):
        self.write_hosts()
        recorder = Recorder()
        self.adapter(recorder).set_hostname("debra-8518d6")

        self.assertIn("127.0.1.1 debra-8518d6 debra-8518d6", self.hosts.read_text())
        self.assertIn("hostnamectl set-hostname debra-8518d6", recorder.commands())
        self.assertIn("systemctl try-restart avahi-daemon.service", recorder.commands())

    def test_the_alias_is_written_after_the_rename_never_before(self):
        # The write records no command, so the file is inspected at the moment
        # the rename is issued. Writing the alias first would name a hostname the
        # machine does not have if `hostnamectl` then failed.
        self.write_hosts()
        recorder = Recorder()
        original = recorder.__call__
        seen = []

        def watching(argv, timeout=None):
            if argv[:2] == ["hostnamectl", "set-hostname"]:
                seen.append(self.hosts.read_text())
            return original(argv, timeout)

        self.adapter(watching).set_hostname("debra-8518d6")
        self.assertEqual(len(seen), 1)
        self.assertIn("127.0.1.1 debra-lab debra-lab", seen[0],
                      "the alias was already rewritten when the rename was issued")

    def test_a_failed_rename_leaves_the_alias_alone(self):
        # Writing the alias first would name a hostname the machine does not have.
        self.write_hosts()
        recorder = Recorder(rename_fails=True)
        with self.assertRaises(nm_module.NmError):
            self.adapter(recorder).set_hostname("debra-8518d6")
        self.assertEqual(self.hosts.read_text(), DEBIAN_HOSTS)

    def test_a_stopped_responder_is_left_stopped(self):
        # `restart` would start a responder somebody deliberately turned off.
        self.write_hosts()
        recorder = Recorder(mdns="inactive")
        self.adapter(recorder).set_hostname("debra-8518d6")
        self.assertNotIn("systemctl try-restart avahi-daemon.service", recorder.commands())
        self.assertIn("127.0.1.1 debra-8518d6 debra-8518d6", self.hosts.read_text())

    def test_a_device_without_mdns_is_not_reported_as_a_failure(self):
        self.write_hosts()
        recorder = Recorder(mdns="absent")
        self.adapter(recorder).set_hostname("debra-8518d6")
        self.assertNotIn("systemctl try-restart avahi-daemon.service", recorder.commands())
        self.assertIn("127.0.1.1 debra-8518d6 debra-8518d6", self.hosts.read_text())

    def test_the_responder_is_restarted_even_when_the_name_is_already_correct(self):
        # Another tool can have set the name, leaving the responder stale. The
        # static name is no proof of what is being advertised.
        self.write_hosts("127.0.1.1 debra-8518d6 debra-8518d6\n127.0.0.1 localhost\n")
        recorder = Recorder()
        self.adapter(recorder).set_hostname("debra-8518d6")
        self.assertIn("systemctl try-restart avahi-daemon.service", recorder.commands())

    def test_a_stale_alias_is_repaired(self):
        self.write_hosts("127.0.1.1 debra-8518d6 debra-lab\n127.0.0.1 localhost\n")
        self.adapter(Recorder()).set_hostname("debra-8518d6")
        self.assertEqual(self.hosts.read_text(),
                         "127.0.1.1 debra-8518d6 debra-8518d6\n127.0.0.1 localhost\n")

    def test_a_changed_alias_is_published_by_rename_not_written_in_place(self):
        # An in-place write opens the file with O_TRUNC, so a power cut between
        # the truncation and the write leaves a device that cannot resolve
        # `localhost` - every `sudo` fails. The fixture therefore has to notice
        # the *rename*: the inode changes on a rename and not on a rewrite, so
        # replacing `os.replace` in `_replace_text` with `path.write_text(...)`
        # fails here while every other test in this file still passes.
        self.write_hosts("127.0.1.1 debra-8518d6 debra-lab\n127.0.0.1 localhost\n")
        before = self.hosts.stat().st_ino
        self.adapter(Recorder()).set_hostname("debra-8518d6")
        self.assertEqual(self.hosts.read_text(),
                         "127.0.1.1 debra-8518d6 debra-8518d6\n127.0.0.1 localhost\n")
        self.assertNotEqual(self.hosts.stat().st_ino, before,
                            "the alias was written in place; a cut there loses the file")

    def test_an_invalid_name_is_refused_before_anything_runs(self):
        self.write_hosts()
        recorder = Recorder()
        for bad in ("", "has space", "two.dots", "-leading", "x" * 64):
            with self.subTest(name=bad):
                with self.assertRaises(nm_module.NmError):
                    self.adapter(recorder).set_hostname(bad)
        self.assertEqual(recorder.calls, [], "an invalid name reached hostnamectl")
        self.assertEqual(self.hosts.read_text(), DEBIAN_HOSTS)

    def test_an_already_correct_file_is_not_replaced(self):
        self.write_hosts("127.0.1.1 debra-8518d6 debra-8518d6\n127.0.0.1 localhost\n")
        before = self.hosts.stat().st_ino
        self.adapter(Recorder()).set_hostname("debra-8518d6")
        self.assertEqual(self.hosts.stat().st_ino, before, "the file was rewritten for nothing")

    def test_the_file_keeps_its_mode(self):
        self.write_hosts(mode=0o644)
        self.adapter(Recorder()).set_hostname("debra-8518d6")
        self.assertEqual(stat.S_IMODE(self.hosts.stat().st_mode), 0o644)

    def test_a_symlinked_hosts_file_stays_a_symlink(self):
        real = self.dir / "real-hosts"
        real.write_text(DEBIAN_HOSTS, encoding="utf-8")
        self.hosts.symlink_to(real)
        self.adapter(Recorder()).set_hostname("debra-8518d6")
        self.assertTrue(self.hosts.is_symlink(), "the symlink was replaced by a file")
        self.assertIn("127.0.1.1 debra-8518d6 debra-8518d6", real.read_text())

    def test_a_hosts_file_that_cannot_be_read_does_not_fail_the_rename(self):
        missing = self.dir / "absent"
        recorder = Recorder()
        self.adapter(recorder, hosts_path=missing).set_hostname("debra-8518d6")
        self.assertIn("hostnamectl set-hostname debra-8518d6", recorder.commands())

    def test_an_undecodable_hosts_file_does_not_fail_the_rename(self):
        # A non-UTF-8 byte in a comment must not raise through a `except OSError`.
        self.hosts.write_bytes(b"# caf\xe9\n127.0.1.1 old old\n127.0.0.1 localhost\n")
        self.adapter(Recorder()).set_hostname("debra-8518d6")
        data = self.hosts.read_bytes()
        self.assertIn(b"# caf\xe9", data, "the undecodable line was not preserved")
        self.assertIn(b"127.0.1.1 debra-8518d6 debra-8518d6", data)

    def test_a_responder_that_will_not_restart_does_not_fail_the_rename(self):
        self.write_hosts()
        recorder = Recorder(mdns_fails=True)
        self.adapter(recorder).set_hostname("debra-8518d6")
        self.assertIn("127.0.1.1 debra-8518d6 debra-8518d6", self.hosts.read_text())


class AdapterSignatureTests(Temp):
    def test_the_default_hosts_path_is_the_system_one(self):
        # A device install must not need an argument to find the real file.
        self.assertEqual(nm_module.Nmcli()._hosts_path, Path("/etc/hosts"))


if __name__ == "__main__":
    unittest.main()
