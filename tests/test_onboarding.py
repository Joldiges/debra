"""Onboarding: identity, the phase machine, the portal, and the baseline.

Every test here runs offline. The NetworkManager is a recorded double, so a pass
proves the decisions and the HTTP contract, not that a radio works.
"""

import hashlib
import io
import json
import secrets
import logging
import os
import socket
import stat
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "control" / "setup"))

import baseline as baseline_module  # noqa: E402
import nm as nm_module  # noqa: E402
import onboarding  # noqa: E402
import state as state_module  # noqa: E402
from fake_nm import FakeNetwork  # noqa: E402

# GLib is the parser NetworkManager's keyfile plugin uses. Testing our escaping
# against a string assertion proves nothing; testing it against this proves the
# value comes back the way the person typed it.
try:
    import gi
    gi.require_version("GLib", "2.0")
    from gi.repository import GLib
except (ImportError, ValueError):  # pragma: no cover - depends on the host
    GLib = None


def _glib_parse(text):  # noqa: F401 - kept for the GLib-level assertions
    key_file = GLib.KeyFile()
    key_file.load_from_data(text, len(text.encode("utf-8")), GLib.KeyFileFlags.NONE)
    return {"ssid": key_file.get_string("wifi", "ssid"),
            "psk": key_file.get_string("wifi-security", "psk")}


# libnm is the parser NetworkManager's keyfile plugin itself uses. GLib alone is
# not enough: `ssid` has its own reader on top of the GLib value, which is how a
# submitted `65;66;` became `AB`.
def _nm_library():
    import ctypes
    try:
        nm = ctypes.CDLL("libnm.so.0")
        gio = ctypes.CDLL("libgio-2.0.so.0")
        glib = ctypes.CDLL("libglib-2.0.so.0")
    except OSError:  # pragma: no cover - depends on the host
        return None
    glib.g_key_file_new.restype = ctypes.c_void_p
    load = glib.g_key_file_load_from_data
    load.restype = ctypes.c_int
    load.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t,
                     ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
    read = nm.nm_keyfile_read
    read.restype = ctypes.c_void_p
    read.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int,
                     ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    for name in ("nm_connection_get_setting_wireless", "nm_setting_wireless_get_ssid",
                 "nm_connection_get_setting_wireless_security",
                 "nm_setting_wireless_security_get_psk"):
        function = getattr(nm, name)
        function.restype = ctypes.c_void_p
        function.argtypes = [ctypes.c_void_p]
    gio.g_bytes_get_size.restype = ctypes.c_size_t
    gio.g_bytes_get_size.argtypes = [ctypes.c_void_p]
    gio.g_bytes_get_data.restype = ctypes.c_void_p
    gio.g_bytes_get_data.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)]
    return ctypes, nm, gio, glib, load, read


NM_LIBRARY = _nm_library()


def _nm_parse(text, base_dir="/tmp/opencode"):
    """What NetworkManager itself would read out of this keyfile."""
    import ctypes
    _, nm, gio, glib, load, read = NM_LIBRARY
    key_file = glib.g_key_file_new()
    error = ctypes.c_void_p()
    payload = text.encode("utf-8")
    if not load(key_file, payload, len(payload), 0, ctypes.byref(error)):
        raise AssertionError("GLib refused the keyfile")
    connection = read(key_file, base_dir.encode(), 0, None, None, ctypes.byref(error))
    if not connection:
        raise AssertionError("libnm refused the keyfile")
    wireless = nm.nm_connection_get_setting_wireless(connection)
    size = ctypes.c_size_t()
    blob = nm.nm_setting_wireless_get_ssid(wireless)
    pointer = gio.g_bytes_get_data(blob, ctypes.byref(size))
    ssid = ctypes.string_at(pointer, gio.g_bytes_get_size(blob)).decode("utf-8")
    security = nm.nm_connection_get_setting_wireless_security(connection)
    psk = None
    if security:
        value = nm.nm_setting_wireless_security_get_psk(security)
        if value:
            psk = ctypes.cast(value, ctypes.c_char_p).value.decode("utf-8")
    return {"ssid": ssid, "psk": psk}


class Temp(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix="onboard-", dir="/tmp/opencode")
        self.dir = Path(self._temp.name)
        self.state_path = self.dir / "setup.json"
        self.baseline_dir = self.dir / "baseline"

    def tearDown(self):
        self._temp.cleanup()

    def onboarder(self, network=None, **kwargs):
        # A fixed name, a serial path that cannot exist and an empty fake root
        # keep every test independent of the machine it runs on. Without the
        # root, a join would capture this laptop's real keyfiles.
        kwargs.setdefault("hostname", "debra-demo1")
        kwargs.setdefault("serial_paths", (str(self.dir / "no-serial"),))
        root = self.dir / "fake-root"
        root.mkdir(exist_ok=True)
        kwargs.setdefault("root", str(root))
        return onboarding.Onboarder(network or FakeNetwork(), self.state_path,
                                    self.baseline_dir, **kwargs)


class IdentityTests(Temp):
    def test_hostname_comes_from_the_board_serial_and_is_stable(self):
        self.assertEqual(onboarding.hostname_from_serial("00000000abcdef01"), "debra-cdef01")
        self.assertEqual(onboarding.hostname_from_serial("1000000012345678"), "debra-345678")
        self.assertEqual(onboarding.hostname_from_serial("1000000012345678"),
                         onboarding.hostname_from_serial("1000000012345678"))
        self.assertNotEqual(onboarding.hostname_from_serial("1000000012345678"),
                            onboarding.hostname_from_serial("1000000087654321"))

    def test_a_serial_that_cannot_name_a_device_falls_back(self):
        self.assertIsNone(onboarding.hostname_from_serial(""))
        self.assertIsNone(onboarding.hostname_from_serial("abc"))
        self.assertIsNone(onboarding.hostname_from_serial(None))
        # Punctuation is dropped rather than becoming part of a hostname.
        self.assertEqual(onboarding.hostname_from_serial("0000-00ab-cdef"), "debra-abcdef")

    def test_identity_is_chosen_once_and_applied_every_time(self):
        serial = self.dir / "serial"
        serial.write_text("1000000012345678\n")
        network = FakeNetwork()
        onboarder = self.onboarder(network, serial_paths=(str(serial),))
        self.assertEqual(onboarder.ensure_identity(), "debra-345678")
        self.assertEqual(onboarder.ensure_identity(), "debra-345678")
        # The name is chosen once. Applying it is idempotent and repeated,
        # because a first application that failed used to be remembered as done
        # and no later boot repaired it.
        self.assertEqual(network.phases().count("set_hostname"), 2)
        self.assertEqual(state_module.read(self.state_path)["hostname"], "debra-345678")

    def test_a_failed_application_is_retried_on_the_next_boot(self):
        network = FakeNetwork()
        network.fail_hostname = True
        onboarder = self.onboarder(network)
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            onboarder.ensure_identity()
        network.fail_hostname = False
        onboarder.ensure_identity()
        self.assertEqual(network.hostname_applied, "debra-demo1")

    def test_hotspot_name_is_derived_from_the_hostname(self):
        self.assertEqual(onboarding.hotspot_name("debra-345678"), "Debra-Setup-345678")
        self.assertEqual(onboarding.hotspot_name(None), "Debra-Setup-debra")


class StateTests(Temp):
    def test_a_missing_file_is_a_blank_record_not_an_error(self):
        data = state_module.read(self.state_path)
        self.assertEqual(data["phase"], "unconfigured")
        self.assertEqual(data["attempts"], 0)

    def test_written_state_is_owner_only_and_round_trips(self):
        data = state_module.blank("debra-345678")
        data.update(phase="hotspot", hotspot={"ssid": "Debra-Setup-345678",
                                              "interface": "wlan0"})
        state_module.write(self.state_path, data)
        self.assertEqual(stat.S_IMODE(self.state_path.stat().st_mode), 0o600)
        self.assertEqual(state_module.read(self.state_path)["hostname"], "debra-345678")

    def test_unknown_keys_bad_phases_and_bad_values_are_refused(self):
        base = state_module.blank("debra-345678")
        # `schema = SCHEMA + 1` rather than a literal: 3 is the current schema
        # now, and the point of the case is a *newer* record being refused.
        for broken in (dict(base, extra=1), dict(base, phase="sleeping"),
                       dict(base, schema=state_module.SCHEMA + 1),
                       dict(base, attempts=-1),
                       dict(base, country="GBR"), dict(base, hotspot={"ssid": "x"})):
            with self.assertRaises(ValueError, msg=str(broken)[:60]):
                state_module.validate(broken)

    def test_a_record_from_the_previous_schema_is_read_rather_than_refused(self):
        # The previous release kept the setup password inside this record. This
        # one keeps it in its own file, and `validate` refuses keys it did not
        # write - so without a migration an upgraded device raises on its first
        # boot, the unit fails, and there is no setup network at all.
        legacy = dict(state_module.blank("debra-345678"), schema=1,
                      phase="hotspot",
                      hotspot={"ssid": "Debra-Setup-345678", "interface": "wlan0"},
                      hotspot_password="s3cretvalue")
        legacy.pop("attempt_token", None)
        legacy.pop("attempt_claimed", None)
        self.state_path.write_text(json.dumps(legacy), encoding="utf-8")
        data = state_module.read(self.state_path)
        self.assertEqual(data["schema"], state_module.SCHEMA)
        self.assertEqual(data["hostname"], "debra-345678")
        self.assertNotIn("hotspot_password", data)
        self.assertFalse(data["attempt_claimed"])
        # Schema 1 stored no password, so a described access point is one
        # nothing can join: it is dropped and the next boot raises it again.
        self.assertIsNone(data["hotspot"])
        self.assertEqual(data["phase"], "failed")
        self.assertIn("raised again", data["last_error"])
        # And the password did not survive into the record the status reports.
        self.assertNotIn("s3cretvalue", self.state_path.read_text(encoding="utf-8")
                         + json.dumps(data))

    def test_a_schema_one_record_without_the_later_fields_is_migrated(self):
        # The prototype revisions did not all carry the same keys: three of the
        # five records this repository wrote lacked `attempt_token`,
        # `baseline_error` or `last_attempt` as well as the fields added at
        # schema 2. Filling only those refused those records and stopped the
        # service on a device that had merely upgraded.
        old = {"schema": 1, "phase": "hotspot", "hostname": "debra-1",
               "country": "GB", "ssid": "HomeWiFi", "address": None,
               "last_error": None, "attempts": 1,
               "hotspot": {"ssid": "Debra-Setup-1", "interface": "wlan0"},
               "baseline": None}
        self.state_path.write_text(json.dumps(old))
        data = state_module.read(self.state_path)
        self.assertEqual(data["schema"], state_module.SCHEMA)
        self.assertEqual(data["country"], "GB")
        self.assertIsNone(data["attempt_token"])
        self.assertIsNone(data["baseline_error"])
        self.assertIsNone(data["last_attempt"])
        self.assertFalse(data["attempt_claimed"])
        # The described hot spot had no stored password, so it is dropped.
        self.assertIsNone(data["hotspot"])
        self.assertEqual(data["phase"], "failed")

    def test_a_schema_two_record_loses_the_password_it_kept(self):
        # Schema 2 kept the setup password inside this record. It is migrated
        # rather than refused, and the credential must not stay on disk - this
        # is the file the status API reports.
        legacy = dict(state_module.blank("debra-345678"), schema=2,
                      phase="hotspot",
                      hotspot={"ssid": "Debra-Setup-345678", "interface": "wlan0"},
                      hotspot_password="abcdefghjk2m")
        self.state_path.write_text(json.dumps(legacy), encoding="utf-8")
        data = state_module.read(self.state_path)
        self.assertEqual(data["schema"], state_module.SCHEMA)
        self.assertEqual(data["phase"], "hotspot")
        self.assertEqual(data["hotspot"]["ssid"], "Debra-Setup-345678")
        self.assertNotIn("hotspot_password", data)
        self.assertNotIn("abcdefghjk2m", self.state_path.read_text(encoding="utf-8"))

    def test_a_connecting_record_without_a_token_is_resolved_not_refused(self):
        # `validate` refuses `connecting` with no token, and a record like that
        # can be left by a process that died mid-attempt. Refusing it here stops
        # the service before it raises an access point - the outcome the
        # migration exists to prevent.
        legacy = dict(state_module.blank("debra-345678"), schema=2,
                      phase="connecting",
                      hotspot={"ssid": "Debra-Setup-345678", "interface": "wlan0"},
                      hotspot_password="abcdefghjk2m")
        legacy["attempt_token"] = None
        # A worker had claimed the attempt: exactly the residue to clear.
        legacy["attempt_claimed"] = True
        self.state_path.write_text(json.dumps(legacy), encoding="utf-8")
        data = state_module.read(self.state_path)
        self.assertEqual(data["phase"], "failed")
        self.assertFalse(data["attempt_claimed"])
        self.assertIn("did not finish", data["last_error"])

    def test_a_schema_one_connecting_record_without_an_access_point_is_resolved(self):
        legacy = dict(state_module.blank("debra-345678"), schema=1,
                      phase="connecting")
        self.state_path.write_text(json.dumps(legacy), encoding="utf-8")
        data = state_module.read(self.state_path)
        # There was never a hotspot to keep in schema 1, and there is no token
        # either: the attempt did not survive, and the next boot says so.
        self.assertEqual(data["phase"], "failed")
        self.assertIn("did not finish", data["last_error"])

    def test_a_hotspot_phase_with_no_described_network_is_resolved(self):
        legacy = dict(state_module.blank("debra-345678"), schema=2,
                      phase="hotspot", hotspot=None)
        self.state_path.write_text(json.dumps(legacy), encoding="utf-8")
        data = state_module.read(self.state_path)
        self.assertEqual(data["phase"], "failed")
        self.assertIn("raised again", data["last_error"])

    def test_an_online_record_that_still_describes_an_access_point_is_resolved(self):
        legacy = dict(state_module.blank("debra-345678"), schema=2,
                      phase="online", address="192.0.2.40",
                      hotspot={"ssid": "Debra-Setup-345678", "interface": "wlan0"},
                      attempt_claimed=True, attempt_token="stale-token")
        self.state_path.write_text(json.dumps(legacy), encoding="utf-8")
        data = state_module.read(self.state_path)
        self.assertEqual(data["phase"], "online")
        self.assertIsNone(data["hotspot"])
        self.assertIsNone(data["attempt_token"])
        self.assertFalse(data["attempt_claimed"],
                         "a dead claim survived a record that says it is online")

    def test_a_record_missing_a_core_key_is_refused_rather_than_reset(self):
        # Only the keys an earlier build could genuinely lack are filled. A
        # record with no `phase` is a corrupt file, and filling it from a blank
        # one turned it into a fresh device - which `read` promises never to do.
        legacy = dict(state_module.blank("debra-345678"), schema=1)
        legacy.pop("phase")
        self.state_path.write_text(json.dumps(legacy), encoding="utf-8")
        with self.assertRaises(ValueError):
            state_module.read(self.state_path)
        self.assertNotIn("\"phase\"", self.state_path.read_text(encoding="utf-8"),
                         "the corrupt record was silently rewritten")

    def test_a_write_syncs_the_state_directory(self):
        # Replacing the file and fsyncing it is not enough: the directory entry
        # is a write of its own, and a power cut straight after the rename can
        # lose it. The state decides which phase the next boot starts in. That
        # the sync itself reaches `fsync` is `SyncDirectoryTests`.
        calls = []
        real = state_module.sync_directory

        def sync(path):
            calls.append(Path(path))
            return real(path)

        with patch.object(state_module, "sync_directory", sync):
            state_module.write(self.state_path, state_module.blank("debra-1"))
        self.assertEqual(calls, [self.state_path.parent])

    def test_every_write_advances_the_revision(self):
        # The page orders answers by this, not by the time its request started.
        data = state_module.write(self.state_path, state_module.blank("debra-1"))
        first = data["revision"]
        second = state_module.write(self.state_path, dict(data, country="GB"))["revision"]
        self.assertGreater(second, first)

    def test_a_read_only_state_directory_does_not_log_on_every_read(self):
        # `read` is on the status path, which the page polls. A migration that
        # cannot be written back must say so once, not every fifteen seconds.
        legacy = dict(state_module.blank("debra-345678"), schema=1)
        legacy["hotspot_password"] = "s3cretvalue"
        self.state_path.write_text(json.dumps(legacy), encoding="utf-8")
        state_module._WRITE_BACK_FAILED.discard(str(self.state_path))
        with patch.object(state_module, "write",
                          side_effect=OSError(30, "Read-only file system")):
            with self.assertLogs(state_module.LOGGER, level="WARNING") as logs:
                for _ in range(5):
                    self.assertEqual(
                        state_module.read(self.state_path)["schema"],
                        state_module.SCHEMA)
        self.assertEqual(len(logs.output), 1,
                         "the read-only warning repeated on every read")
        state_module._WRITE_BACK_FAILED.discard(str(self.state_path))

    def test_a_schema_that_never_existed_is_refused_not_reset(self):
        # Filling a schema-0 record from `blank()` would validate, and the
        # device would come up as a fresh one - hiding the fact that it had
        # already been configured, which is what `read`'s docstring promises
        # never to do.
        for schema in (0, -1, 99):
            legacy = dict(state_module.blank("debra-345678"), schema=schema)
            legacy["hotspot_password"] = "s3cretvalue"
            self.state_path.write_text(json.dumps(legacy), encoding="utf-8")
            with self.assertRaises(ValueError, msg=f"schema {schema} was accepted"):
                state_module.read(self.state_path)
            self.assertIn("s3cretvalue",
                          self.state_path.read_text(encoding="utf-8"),
                          "a corrupt record was replaced instead of refused")

    def test_a_current_record_is_not_rewritten_by_reading_it(self):
        # `read` is on the status path. Rewriting a current record on every poll
        # would bump `updated` - the page's "last changed" - and write the file
        # once per poll for nothing.
        state_module.write(
            self.state_path, dict(state_module.blank("debra-345678"), phase="hotspot",
                                  hotspot={"ssid": "Debra-Setup-345678",
                                           "interface": "wlan0"}))
        # Not a byte comparison: `updated` has one-second resolution, so a
        # rewrite inside the same second produces identical bytes and would
        # pass. What must not happen is the write at all.
        with patch.object(state_module, "write") as write:
            for _ in range(3):
                self.assertEqual(state_module.read(self.state_path)["schema"],
                                 state_module.SCHEMA)
        write.assert_not_called()

    def test_a_failed_migration_is_retried_on_a_later_read(self):
        # A read-only filesystem is often temporary. Giving up after the first
        # failure would leave the retired password on disk for ever.
        legacy = dict(state_module.blank("debra-345678"), schema=1)
        legacy["hotspot_password"] = "s3cretvalue"
        self.state_path.write_text(json.dumps(legacy), encoding="utf-8")
        state_module._WRITE_BACK_FAILED.discard(str(self.state_path))
        real_write = state_module.write
        failures = [OSError(30, "Read-only file system")]
        calls = []

        def flaky(path, data):
            calls.append(1)
            if failures:
                raise failures.pop()
            return real_write(path, data)

        with patch.object(state_module, "write", flaky):
            with self.assertLogs(state_module.LOGGER, level="WARNING"):
                state_module.read(self.state_path)
            self.assertIn("s3cretvalue",
                          self.state_path.read_text(encoding="utf-8"))
            state_module.read(self.state_path)
        self.assertEqual(len(calls), 2, "the migrated record was not written the second time")
        self.assertNotIn("s3cretvalue",
                         self.state_path.read_text(encoding="utf-8"),
                         "the retried write-back did not remove the retired password")
        state_module._WRITE_BACK_FAILED.discard(str(self.state_path))

    def test_a_write_between_read_and_migration_is_not_clobbered(self):
        # `read` is not under the same lock as every writer. A record saved in
        # between must not be replaced by the older one being migrated.
        legacy = dict(state_module.blank("debra-345678"), schema=1)
        legacy["hotspot_password"] = "s3cretvalue"
        self.state_path.write_text(json.dumps(legacy), encoding="utf-8")
        state_module._WRITE_BACK_FAILED.discard(str(self.state_path))
        real_validate = state_module.validate
        raced = []

        def racing_validate(data):
            # Stands in for another writer finishing between our read and our
            # write-back: `validate` runs after the read and before the write.
            if not raced:
                raced.append(1)
                real_write(self.state_path,
                           dict(state_module.blank("debra-newer"), phase="online"))
            return real_validate(data)

        real_write = state_module.write
        with patch.object(state_module, "validate", racing_validate):
            with self.assertNoLogs(state_module.LOGGER, level="WARNING"):
                state_module.read(self.state_path)
        self.assertEqual(json.loads(self.state_path.read_text())["hostname"],
                         "debra-newer",
                         "the migration replaced a record written after it was read")
        state_module._WRITE_BACK_FAILED.discard(str(self.state_path))

    def test_a_record_from_a_newer_schema_is_still_refused(self):
        # The other direction: a downgraded service must not silently drop a
        # field it does not understand.
        newer = dict(state_module.blank("debra-345678"),
                     schema=state_module.SCHEMA + 1)
        self.state_path.write_text(json.dumps(newer), encoding="utf-8")
        with self.assertRaises(ValueError):
            state_module.read(self.state_path)

    def test_a_record_missing_a_key_is_refused_not_crashed_on(self):
        # A record that validates and then raises KeyError in status() is worse
        # than one refused at the boundary. The review deleted every required
        # key and the old check accepted each one.
        for key in state_module.blank("debra-demo1"):
            broken = dict(state_module.blank("debra-demo1"))
            del broken[key]
            with self.assertRaises(ValueError, msg=key):
                state_module.validate(broken)

    def test_a_bool_is_not_a_schema_version(self):
        # JSON `true` is 1 in Python, so a bare equality check accepted it.
        data = state_module.blank("debra-demo1")
        data["schema"] = True
        with self.assertRaises(ValueError):
            state_module.validate(data)

    def test_a_passphrase_can_never_be_stored(self):
        # The schema is closed, so a keyfile-shaped extra key is rejected rather
        # than quietly persisted next to the state.
        with self.assertRaises(ValueError):
            state_module.validate(dict(state_module.blank("debra-1"), psk="hunter22"))
        self.assertNotIn("psk", json.dumps(state_module.blank("debra-1")))


class SyncDirectoryTests(unittest.TestCase):
    """`sync_directory` itself, because asserting the call proves nothing."""

    def test_it_fsyncs_an_open_directory(self):
        directory = Path(tempfile.mkdtemp(prefix="sync-", dir="/tmp/opencode"))
        seen = []
        real = os.fsync

        def fsync(fd):
            seen.append(os.fstat(fd).st_mode)
            return real(fd)

        try:
            with patch.object(state_module.os, "fsync", fsync):
                state_module.sync_directory(directory)
        finally:
            os.rmdir(directory)
        self.assertEqual(len(seen), 1, "the directory was never fsynced")
        self.assertTrue(stat.S_ISDIR(seen[0]),
                        "the handle synced was not the directory")

    def test_a_missing_directory_is_not_an_error(self):
        state_module.sync_directory(Path("/tmp/opencode") / "no-such-directory")


class HotspotTests(Temp):
    def test_starting_the_hotspot_records_the_name_and_interface(self):
        network = FakeNetwork()
        status = self.onboarder(network).start_hotspot()
        self.assertEqual(status["phase"], "hotspot")
        self.assertEqual(status["hotspot"]["ssid"], "Debra-Setup-demo1")
        self.assertEqual(status["hotspot"]["interface"], "wlan0")
        # A setup network nobody can join is not a setup network: the password
        # has to be somewhere a person can read it, which is the card note.
        self.assertNotIn("password", status["hotspot"])
        # The hostname is applied before the access point is named after it, and
        # an already-set country is read rather than asked for again.
        # The scan sits before the access point is raised, which is the only
        # window where the radio is free enough to look around. The address is
        # part of what the raise reports back, not a second question.
        self.assertEqual(network.phases(),
                         ["set_hostname", "wifi_interface", "country", "scan",
                          "start_hotspot"])

    def test_the_device_name_survives_the_first_hotspot(self):
        # The identity is set in the same record the hotspot then writes. When
        # the write used a record read before the name existed, it erased it.
        status = self.onboarder(FakeNetwork()).start_hotspot()
        self.assertEqual(status["hostname"], "debra-demo1")
        self.assertEqual(state_module.read(self.state_path)["hostname"], "debra-demo1")
        # The portal only admits the address it is served on, so the printed
        # name is that address, not `<hostname>.local`.
        self.assertEqual(status["portal"], "http://10.42.0.1/")

    def test_a_boot_with_no_uplink_keeps_the_name_too(self):
        status = self.onboarder(FakeNetwork()).resume()
        self.assertEqual(status["hostname"], "debra-demo1")
        self.assertEqual(state_module.read(self.state_path)["hostname"], "debra-demo1")

    def test_no_wifi_interface_is_reported_not_ignored(self):
        status = self.onboarder(FakeNetwork(interface=None)).start_hotspot()
        self.assertEqual(status["phase"], "failed")
        self.assertIn("No Wi-Fi interface", status["last_error"])

    def test_a_hotspot_failure_is_reported(self):
        network = FakeNetwork()

        def refuse(*args, **kwargs):
            raise nm_module.NmError("AP mode not supported by this driver")

        network.start_hotspot = refuse
        status = self.onboarder(network).start_hotspot()
        self.assertEqual(status["phase"], "failed")
        self.assertIn("AP mode not supported", status["last_error"])


class JoinTests(Temp):
    def test_a_successful_join_stops_the_hotspot_and_records_the_address(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        status = onboarder.join("HomeWiFi", "correct horse", "GB")
        self.assertEqual(status["phase"], "online")
        self.assertEqual(status["ssid"], "HomeWiFi")
        self.assertEqual(status["address"], "192.0.2.40")
        self.assertIsNone(status["hotspot"])
        # Order matters: the access point goes before the association, because a
        # single radio cannot do both.
        phases = network.phases()
        self.assertLess(phases.index("stop_hotspot"), phases.index("connect"))
        self.assertEqual(network.country_code, "GB")

    def test_a_wrong_password_brings_the_hotspot_back_with_the_reason(self):
        network = FakeNetwork(behaviour="bad-psk")
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        status = onboarder.join("HomeWiFi", "wrong password", None)
        self.assertEqual(status["phase"], "failed")
        self.assertIn("password was refused", status["last_error"])
        # The access point must be back, or the user has no way to try again.
        self.assertEqual(status["hotspot"]["ssid"], "Debra-Setup-demo1")
        self.assertEqual(network.hotspot["ssid"], "Debra-Setup-demo1")

    def test_association_without_an_address_is_a_failure_not_a_success(self):
        network = FakeNetwork(behaviour="no-address")
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        status = onboarder.join("HomeWiFi", "correct horse", None)
        self.assertEqual(status["phase"], "failed")
        self.assertIn("no usable address", status["last_error"])

    def test_the_country_is_only_set_once(self):
        network = FakeNetwork(country="GB")
        onboarder = self.onboarder(network)
        state_module.write(self.state_path, dict(state_module.blank("debra-1"), country="GB"))
        onboarder.start_hotspot()
        onboarder.join("HomeWiFi", "correct horse", "US")
        self.assertNotIn("set_country", network.phases())

    def test_attempts_are_counted_and_capped(self):
        network = FakeNetwork(behaviour="bad-psk")
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        for _ in range(onboarding.MAX_ATTEMPTS):
            onboarder._last_submit = -1000
            onboarder.join("HomeWiFi", "wrong password", None)
        self.assertEqual(state_module.read(self.state_path)["attempts"],
                         onboarding.MAX_ATTEMPTS)
        onboarder._last_submit = -1000
        before = len(network.calls)
        onboarder.join("HomeWiFi", "wrong password", None)
        self.assertEqual(len(network.calls), before, "the cap did not stop the attempt")

    def test_rapid_resubmission_is_ignored(self):
        network = FakeNetwork()
        clock = [0.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()
        onboarder.join("HomeWiFi", "correct horse", None)
        clock[0] = 1.0
        before = len(network.calls)
        onboarder.join("OtherWiFi", "correct horse", None)
        self.assertEqual(len(network.calls), before)


class ResumeTests(Temp):
    def test_an_offline_boot_raises_the_setup_point(self):
        status = self.onboarder(FakeNetwork()).resume()
        self.assertEqual(status["phase"], "hotspot")

    def test_an_online_boot_records_the_current_address(self):
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        status = self.onboarder(network).resume()
        self.assertEqual(status["phase"], "online")
        self.assertEqual(status["address"], "192.0.2.40")
        self.assertNotIn("start_hotspot", network.phases())

    def test_a_failed_attempt_keeps_its_reason_across_the_reboot(self):
        # A person corrects the wrong household password by reading the reason
        # on the page. Only a dead attempt used to be handed its reason on the
        # next boot, so a plain failure came back as a blank form.
        state_module.write(self.state_path, dict(
            state_module.blank("debra-1"), phase="failed",
            hotspot={"ssid": "Debra-Setup-1", "interface": "wlan0"},
            last_error="The Wi-Fi password was not accepted"))
        status = self.onboarder(FakeNetwork()).resume()
        self.assertEqual(status["phase"], "failed")
        self.assertEqual(status["last_error"], "The Wi-Fi password was not accepted")

    def test_a_lost_network_comes_back_as_a_setup_point_with_a_reason(self):
        state_module.write(self.state_path, dict(state_module.blank("debra-1"),
                                                phase="online", address="192.0.2.40"))
        status = self.onboarder(FakeNetwork()).resume()
        self.assertEqual(status["phase"], "failed")
        self.assertIn("not reachable", status["last_error"])


class BaselineTests(Temp):
    def test_a_baseline_captures_the_allowlist_and_records_what_was_missing(self):
        root = self.dir / "root"
        (root / "etc" / "NetworkManager" / "system-connections").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-345678\n")
        (root / "etc" / "NetworkManager" / "system-connections" / "home.nmconnection").write_text(
            "[wifi]\nssid=HomeWiFi\n")
        manifest = baseline_module.capture(self.baseline_dir, root=str(root))
        self.assertIn("etc/hostname", manifest["captured"])
        self.assertIn("etc/NetworkManager/system-connections/home.nmconnection",
                      manifest["captured"])
        self.assertIn("var/lib/debra", manifest["missing"])
        archive = self.baseline_dir / manifest["archive"]
        self.assertEqual(stat.S_IMODE(archive.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.baseline_dir / manifest["archive"].replace(
            ".tar.gz", ".json")).stat().st_mode), 0o600)

    def test_a_baseline_is_taken_once_after_the_first_join(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        status = onboarder.join("HomeWiFi", "correct horse", None)
        self.assertIsNotNone(status["baseline"])
        self.assertTrue(Path(status["baseline"]).exists())
        first = status["baseline"]
        onboarder._last_submit = -1000
        onboarder.join("HomeWiFi", "correct horse", None)
        self.assertEqual(state_module.read(self.state_path)["baseline"], first)

    def test_an_unreadable_file_is_skipped_and_the_rest_still_runs(self):
        root = self.dir / "root"
        (root / "etc" / "NetworkManager" / "system-connections").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-345678\n")
        secret = root / "etc" / "NetworkManager" / "system-connections" / "home.nmconnection"
        secret.write_text("[wifi]\nssid=HomeWiFi\n")
        import builtins
        real_open = builtins.open

        def fake_open(path, *args, **kwargs):
            if str(path).endswith("home.nmconnection"):
                raise PermissionError(13, "Permission denied")
            return real_open(path, *args, **kwargs)

        with patch("builtins.open", fake_open):
            manifest = baseline_module.capture(self.baseline_dir, root=str(root))
        self.assertIn("etc/hostname", manifest["captured"])
        self.assertEqual(manifest["skipped"][0]["path"], str(secret))
        self.assertEqual(manifest["skipped"][0]["reason"], "PermissionError")
        self.assert_in_archive(manifest, ["etc/hostname"])

    def test_a_read_that_fails_partway_does_not_poison_the_archive(self):
        # tar.add() writes a header and part of a body before a read can fail.
        # Catching that left a truncated member that every later file was
        # unreachable behind, while the manifest still claimed they were saved.
        root = self.dir / "root"
        (root / "etc" / "NetworkManager" / "system-connections").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-345678\n")
        profile = root / "etc" / "NetworkManager" / "system-connections" / "home.nmconnection"
        profile.write_bytes(b"x" * 2048)
        import builtins
        real_open = builtins.open

        class Partial:
            def __init__(self, path):
                self._file = real_open(path, "rb")
                self._served = False

            def fileno(self):
                return self._file.fileno()

            def read(self, size=-1):
                if not self._served:
                    self._served = True
                    return self._file.read(17)
                raise OSError(5, "Input/output error")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self._file.close()

        def fake_open(path, *args, **kwargs):
            if str(path).endswith("home.nmconnection"):
                return Partial(path)
            return real_open(path, *args, **kwargs)

        with patch("builtins.open", fake_open):
            manifest = baseline_module.capture(self.baseline_dir, root=str(root))
        self.assertIn("etc/hostname", manifest["captured"])
        self.assertNotIn("etc/NetworkManager/system-connections/home.nmconnection",
                         manifest["captured"])
        # The later file must still be readable out of the published archive.
        self.assert_in_archive(manifest, ["etc/hostname"])

    def assert_in_archive(self, manifest, expected):
        import tarfile as tarfile_module
        archive = self.baseline_dir / manifest["archive"]
        with tarfile_module.open(archive) as tar:
            names = tar.getnames()
        for name in expected:
            self.assertIn(name, names, f"{name} missing from the published archive: {names}")
        self.assertEqual(len(names), len(manifest["captured"]),
                         "the archive and the manifest disagree about what was captured")

    def test_a_failed_baseline_does_not_undo_a_working_network(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        with patch.object(baseline_module, "capture",
                          side_effect=baseline_module.BaselineError("too large")):
            status = onboarder.join("HomeWiFi", "correct horse", None)
        self.assertEqual(status["phase"], "online")
        self.assertIsNone(status["baseline"])


class PortalTests(Temp):
    def setUp(self):
        super().setUp()
        self.network = FakeNetwork()
        self.onboarder = self.onboarder(self.network)
        self.onboarder.start_hotspot()
        self.server = onboarding.Portal(("127.0.0.1", 0), self.onboarder,
                                        onboarding.ASSETS / "setup.html")
        self.host = "127.0.0.1:%d" % self.server.server_port
        self.server.host = self.host
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        super().tearDown()

    def request(self, path, body=None, host=None, method=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            "http://" + self.host + path, data=data, method=method or ("POST" if data else "GET"))
        request.add_header("Host", host or self.host)
        if data:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def test_the_page_and_its_script_are_served(self):
        code, body = self.request("/")
        self.assertEqual(code, 200)
        self.assertIn(b"Set up Wi-Fi", body)
        code, body = self.request("/setup.js")
        self.assertEqual(code, 200)
        self.assertIn(b"/api/join", body)

    def test_status_reports_the_phase_without_either_password(self):
        # Neither credential belongs here. The household passphrase was never
        # this response's business, and the setup network's own password used to
        # be: it was read by anything that had joined, which is the same audience
        # it protects the network from. The mode is reported instead, so the page
        # can say plainly when the setup network is open.
        code, body = self.request("/api/status")
        self.assertEqual(code, 200)
        data = json.loads(body)
        self.assertEqual(data["phase"], "hotspot")
        self.assertNotIn("psk", data)
        self.assertNotIn(b"correct horse", body)
        self.assertNotIn("password", data["hotspot"])
        self.assertIn("security", data)

    def test_another_host_name_is_refused(self):
        code, _ = self.request("/api/status", host="evil.example")
        self.assertEqual(code, 403)
        code, _ = self.request("/", host="evil.example")
        self.assertEqual(code, 403)

    def test_a_join_is_answered_before_the_access_point_stops(self):
        code, body = self.request("/api/join", {"ssid": "HomeWiFi", "psk": "correct horse",
                                                "country": "GB"})
        self.assertEqual(code, 202)
        self.assertEqual(json.loads(body)["status"], "connecting")
        # The worker finishes in the background; wait for it rather than sleep.
        for _ in range(200):
            if state_module.read(self.state_path)["phase"] in ("online", "failed"):
                break
            threading.Event().wait(0.01)
        self.assertEqual(state_module.read(self.state_path)["phase"], "online")

    def test_the_join_runs_only_after_the_page_has_been_answered(self):
        # The whole handover depends on this ordering: the reply is the last
        # thing that can travel over the setup network. A review mutation that
        # completed the join before writing the 202 passed every other test.
        seen = {}
        real_reply = onboarding.PortalHandler._reply

        def reply(handler, code, body, content_type="application/json"):
            if code == 202:
                seen["replied"] = True
            return real_reply(handler, code, body, content_type)

        real_connect = self.network.connect

        def connect(ssid, psk, timeout=60, keyfile_dir=None, interface=None):
            seen["connect_saw_reply"] = seen.get("replied", False)
            return real_connect(ssid, psk, timeout=timeout,
                                keyfile_dir=keyfile_dir, interface=interface)

        # The patches stay in place until the worker has finished: the worker
        # starts after the reply and would otherwise run unpatched.
        with patch.object(onboarding.PortalHandler, "_reply", reply), \
                patch.object(self.network, "connect", connect):
            code, _ = self.request("/api/join", {"ssid": "HomeWiFi",
                                                 "psk": "correct horse"})
            self.assertEqual(code, 202)
            for _ in range(200):
                if state_module.read(self.state_path)["phase"] in ("online", "failed"):
                    break
                threading.Event().wait(0.01)
        self.assertTrue(seen.get("connect_saw_reply"),
                        "the join ran before the page was answered")

    def test_the_access_point_is_still_up_when_the_page_is_answered(self):
        # Answering first is not enough if the access point has already gone:
        # the reply has to travel over the network being torn down. A review
        # mutation stopped the AP before the 202 and kept the worker after it,
        # and every other test still passed, because they only watched
        # `connect()`.
        seen = {}
        real_reply = onboarding.PortalHandler._reply

        def reply(handler, code, body, content_type="application/json"):
            if code == 202:
                seen["hotspot_at_reply"] = self.network.hotspot
                seen["stops_at_reply"] = len(
                    [call for call in self.network.calls if call[0] == "stop_hotspot"])
            return real_reply(handler, code, body, content_type)

        with patch.object(onboarding.PortalHandler, "_reply", reply):
            code, _ = self.request("/api/join", {"ssid": "HomeWiFi",
                                                 "psk": "correct horse"})
            self.assertEqual(code, 202)
            for _ in range(200):
                if state_module.read(self.state_path)["phase"] in ("online", "failed"):
                    break
                threading.Event().wait(0.01)
        self.assertTrue(seen.get("hotspot_at_reply"),
                        "the access point was already down when the page was answered")
        self.assertEqual(seen.get("stops_at_reply"), 0,
                         "the access point was stopped before the page was answered")
        # And it does go down, eventually: the join is what needs the radio.
        self.assertEqual(len([call for call in self.network.calls
                              if call[0] == "stop_hotspot"]), 1)
        self.assertIsNone(self.network.hotspot)

    def test_a_reply_that_cannot_be_delivered_releases_the_reservation(self):
        real_reply = onboarding.PortalHandler._reply

        def reply(handler, code, body, content_type="application/json"):
            if code == 202:
                raise BrokenPipeError(32, "Broken pipe")
            return real_reply(handler, code, body, content_type)

        with patch.object(onboarding.PortalHandler, "_reply", reply):
            with self.assertRaises(OSError):
                self.request("/api/join", {"ssid": "HomeWiFi", "psk": "correct horse"})
        data = state_module.read(self.state_path)
        self.assertEqual(data["phase"], "hotspot",
                         "a lost reply left the device connecting for ever")
        self.assertIsNone(data["attempt_token"])
        self.assertEqual(data["attempts"], 0)
        self.assertNotIn("connect", self.network.phases(),
                         "a join ran although its reply never arrived")

    def test_bad_input_is_refused_without_touching_the_network(self):
        for body, expected in (
            ({"ssid": ""}, 400),
            ({"ssid": "x" * 33}, 400),
            ({"ssid": "ok", "psk": "short"}, 400),
            ({"ssid": "ok", "country": "gb"}, 400),
            ({"ssid": "ok", "extra": 1}, 400),
        ):
            code, _ = self.request("/api/join", body)
            self.assertEqual(code, expected, body)
        self.assertNotIn("connect", self.network.phases())

    def test_a_join_is_refused_when_the_device_is_not_waiting(self):
        state_module.write(self.state_path, dict(state_module.blank("debra-1"), phase="online"))
        code, _ = self.request("/api/join", {"ssid": "HomeWiFi", "psk": "correct horse"})
        self.assertEqual(code, 409)


class SecurityEndpointTests(Temp):
    """`POST /api/security`: answered before the radio changes, like a join."""

    def setUp(self):
        super().setUp()
        self.network = FakeNetwork()
        self.note = self.dir / "boot" / "debra-setup.txt"
        self.onboarder = self.onboarder(self.network, security="none",
                                        card_note_path=self.note)
        self.onboarder.start_hotspot()
        self.server = onboarding.Portal(("127.0.0.1", 0), self.onboarder,
                                        onboarding.ASSETS / "setup.html")
        self.host = "127.0.0.1:%d" % self.server.server_port
        self.server.host = self.host
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        super().tearDown()

    def request(self, path, body=None, host=None, method=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            "http://" + self.host + path, data=data, method=method or ("POST" if data else "GET"))
        request.add_header("Host", host or self.host)
        if data:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def settle(self, calls_before):
        """Wait for the worker: it must have run and finished before we look.

        The reply is delivered before the worker is started, so a plain sleep
        would either be slow or flaky. New calls mean the worker reached the
        radio; the thread name means it finished, which is what the note and the
        state need before they can be read.
        """
        for _ in range(400):
            touched = len(self.network.calls) > calls_before
            running = any(thread.name == "debra-setup-security"
                          for thread in threading.enumerate())
            if touched and not running:
                return
            threading.Event().wait(0.01)
        self.fail("the setup network was never raised again")

    def assert_re_raised(self, calls_before, password):
        """The radio was raised again, and with the mode that was asked for.

        The stop half of the cycle lives in the adapter, which cycles the one
        profile it already has (see AccessPointCheckTests): taking the access
        point down here would delete that profile and hand the device the next
        shared subnet.
        """
        raises = [call for call in self.network.calls[calls_before:]
                  if call[0] == "start_hotspot"]
        self.assertEqual(len(raises), 1,
                         "the access point was not raised again: "
                         + str(self.network.phases()[calls_before:]))
        self.assertEqual(raises[0][3], password,
                         "the access point was raised in the wrong mode")

    def test_turning_the_password_on_answers_first_then_re_raises_the_network(self):
        seen = {}
        real_reply = onboarding.PortalHandler._reply
        calls_before = len(self.network.calls)

        def reply(handler, code, body, content_type="application/json"):
            if code == 202:
                seen["replied"] = True
            return real_reply(handler, code, body, content_type)

        real_start = self.network.start_hotspot

        def start(ssid, interface, password=None):
            seen["start_saw_reply"] = seen.get("replied", False)
            return real_start(ssid, interface, password)

        with patch.object(onboarding.PortalHandler, "_reply", reply), \
                patch.object(self.network, "start_hotspot", start):
            code, body = self.request("/api/security", {"mode": "wpa"})
            self.assertEqual(code, 202)
            payload = json.loads(body)
            self.assertEqual(payload["mode"], "wpa")
            self.assertEqual(payload["ssid"], "Debra-Setup-demo1")
            password = onboarding.setup_secret(self.onboarder.secret_path)
            self.assertEqual(payload["password"], password,
                             "the reply did not carry the password the page needs")
            self.settle(calls_before)
        self.assertTrue(seen.get("start_saw_reply"),
                        "the access point was raised before the page was answered")
        # The radio was actually re-raised, with a password this time.
        self.assert_re_raised(calls_before, True)
        self.assertTrue(self.network.hotspot["password"],
                        "the access point came back open after being told to use a password")
        self.assertEqual(self.onboarder.status()["security"], "wpa")
        # The note is how a person learns the password before any page loads, so
        # it has to be rewritten, not left describing the open network.
        note = self.note.read_text(encoding="utf-8")
        self.assertIn(password, note)
        self.assertNotIn("none (development build)", note)

    def test_turning_the_password_off_answers_without_one(self):
        self.onboarder.set_security("wpa")
        self.onboarder.rearm_hotspot()
        # Raising the access point above stamped the change interval, which is
        # the behaviour this endpoint is throttled by; step past it as a person
        # waiting for the page would.
        self.onboarder._last_security_change = float("-inf")
        self.network.calls.clear()
        calls_before = len(self.network.calls)
        code, body = self.request("/api/security", {"mode": "none"})
        self.assertEqual(code, 202)
        payload = json.loads(body)
        self.assertEqual(payload["mode"], "none")
        self.assertNotIn("password", payload,
                         "a password was served for an open setup network")
        self.settle(calls_before)
        self.assert_re_raised(calls_before, False)
        self.assertFalse(self.network.hotspot["password"],
                         "the access point came back protected after being told to be open")
        self.assertIn("none (development build)",
                      self.note.read_text(encoding="utf-8"))

    def test_the_password_never_reaches_the_journal(self):
        # The root logger rather than `onboarding.LOGGER`, so a message logged
        # from any module on this path is caught. The access point here is
        # raised by the fake adapter, so the adapter's own logger is not
        # exercised; what this proves is that nothing on the reply path, the
        # state write or the note write carries the password.
        calls_before = len(self.network.calls)
        with self.assertLogs(level="DEBUG") as logs:
            code, body = self.request("/api/security", {"mode": "wpa"})
            self.assertEqual(code, 202)
            self.settle(calls_before)
        password = onboarding.setup_secret(self.onboarder.secret_path)
        self.assertNotIn(password, "\n".join(logs.output))
        self.assertTrue(logs.output, "nothing was logged, so this proves nothing")

    def test_a_mode_that_is_not_one_is_refused_and_changes_nothing(self):
        before = len(self.network.calls)
        for body in ({"mode": "open"}, {"mode": ""}, {"mode": None},
                     {"mode": ["wpa"]}, {"mode": "wpa", "extra": 1}, {}):
            code, reply = self.request("/api/security", body)
            self.assertEqual(code, 400, body)
            self.assertTrue(json.loads(reply)["error"], body)
        self.assertEqual(len(self.network.calls), before,
                         "a refused mode touched the radio")
        self.assertEqual(self.onboarder.status()["security"], "none")
        self.assertFalse(self.state_path.with_name("setup-security").exists(),
                         "a refused mode was written down")

    def test_a_change_is_refused_when_there_is_no_access_point(self):
        # `online`: no access point at all. The phase alone has to be enough,
        # because the state can still hold the hotspot dict of a raise that
        # failed, and a check on that dict alone would answer 202 for a network
        # that is not there.
        data = dict(state_module.blank("debra-1"), phase="online", hotspot=None)
        state_module.write(self.state_path, data)
        before = len(self.network.calls)
        code, body = self.request("/api/security", {"mode": "wpa"})
        self.assertEqual(code, 409)
        self.assertIn("not running", json.loads(body)["error"])
        self.assertEqual(len(self.network.calls), before)
        self.assertEqual(state_module.read(self.state_path)["phase"], "online")
        self.assertFalse(self.state_path.with_name("setup-security").exists())

    def test_a_change_is_refused_while_a_join_is_running(self):
        # The radio is mid-association. Cycling it here would take the interface
        # out from under a join the device has already answered 202, and neither
        # would end reliably. The hotspot dict is still present in this state, so
        # a check that only asked whether there is a hotspot would say yes.
        data = state_module.read(self.state_path)
        # A connecting record carries the attempt it belongs to; the validator
        # refuses one without a token, which is a state this module never writes.
        data.update(phase="connecting", attempt_token="during-a-join")
        state_module.write(self.state_path, data)
        self.assertTrue(data["hotspot"], "this test needs a recorded hotspot")
        before = len(self.network.calls)
        code, body = self.request("/api/security", {"mode": "wpa"})
        self.assertEqual(code, 409, "a mode change was allowed during a join")
        self.assertIn("not running", json.loads(body)["error"])
        self.assertEqual(len(self.network.calls), before,
                         "the radio was touched during a join")
        self.assertEqual(state_module.read(self.state_path)["phase"], "connecting")
        self.assertFalse(self.state_path.with_name("setup-security").exists())

    def test_a_join_is_refused_while_the_mode_is_changing(self):
        # The other order: the change owns the radio, and a join that starts in
        # the middle of it would be association racing a re-key. On one radio
        # that is the disruption the change exists to avoid.
        self.assertTrue(self.onboarder.begin_security_change())
        try:
            code, body = self.request(
                "/api/join", {"ssid": "HomeWiFi", "psk": "correct horse"})
            self.assertEqual(code, 409)
            self.assertIn("changing", json.loads(body)["error"])
        finally:
            self.onboarder.abandon_security_change()

    def test_the_password_in_the_reply_is_the_one_the_access_point_uses(self):
        # A state directory that cannot be written is exactly when
        # `setup_secret` returns a password it could not save. The reply, the
        # access point and the card note still have to agree, or the person is
        # told a password the network rejects and can never join it again.
        with patch.object(onboarding, "_store_secret",
                          lambda path, secret: False):
            calls_before = len(self.network.calls)
            code, body = self.request("/api/security", {"mode": "wpa"})
            self.assertEqual(code, 202)
            told = json.loads(body)["password"]
            self.settle(calls_before)
        used = self.network.hotspot["password"]
        self.assertEqual(used, told,
                         "the access point was raised with a different password")
        self.assertIn(told, self.note.read_text(encoding="utf-8"),
                      "the card note carries a password the network does not use")
        self.assertGreaterEqual(len(told), 8)

    def test_a_reply_that_cannot_be_delivered_invents_no_stored_choice(self):
        # The revert puts the mode that was already in force back. Writing it to
        # the mode file would create a "choice" nobody made, and a stored choice
        # outranks the installer's flag for ever after - so a later
        # `--setup-security wpa` would say wpa in the unit and come up open.
        self.assertFalse(self.state_path.with_name("setup-security").exists())
        real_reply = onboarding.PortalHandler._reply

        def reply(handler, code, body, content_type="application/json"):
            if code == 202:
                raise BrokenPipeError(32, "Broken pipe")
            return real_reply(handler, code, body, content_type)

        with patch.object(onboarding.PortalHandler, "_reply", reply):
            with self.assertRaises(OSError):
                self.request("/api/security", {"mode": "wpa"})
        self.assertFalse(self.state_path.with_name("setup-security").exists(),
                         "the failed change left a mode file behind")

    def test_a_lost_reply_restores_a_choice_the_page_had_already_made(self):
        # The revert path asks whether there was a stored choice. The answer
        # decides between writing the old mode back and removing the file, and
        # every other test starts with no file - so an expression that always
        # said "no choice" would pass all of them and delete a real one here.
        stored = self.state_path.with_name("setup-security")
        self.assertEqual(stored, self.dir / "setup-security")
        # A device whose owner chose `wpa` on the page, installed as `none`.
        # `setUp` replaced the helper with the instance it built.
        chosen = Temp.onboarder(self, self.network, security="none",
                                card_note_path=self.note)
        chosen.set_security("wpa")
        chosen.start_hotspot()
        self.server.onboarder = chosen
        self.assertEqual(chosen.security, "wpa")
        real_reply = onboarding.PortalHandler._reply

        def reply(handler, code, body, content_type="application/json"):
            if code == 202:
                raise BrokenPipeError(32, "Broken pipe")
            return real_reply(handler, code, body, content_type)

        with patch.object(onboarding.PortalHandler, "_reply", reply):
            with self.assertRaises(OSError):
                self.request("/api/security", {"mode": "none"})
        self.assertTrue(stored.exists(),
                        "the revert removed a mode the page had chosen")
        self.assertEqual(stored.read_text(encoding="utf-8").strip(), "wpa",
                         "the device was left in the mode whose reply was lost")

    def test_the_radio_is_given_back_when_no_worker_could_be_started(self):
        # `_changing` left set refuses every join and every later change for the
        # life of the process. A thread that cannot be created is the one path
        # where the handler alone can release it.
        #
        # Driven through the handler directly, not over HTTP: patching
        # `threading.Thread` is process-wide, so a live server could not start
        # the thread that would handle the request, and the test would then pass
        # without the handler ever running.
        class NoThread:
            def __init__(self, *arguments, **keywords):
                pass

            def start(self):
                raise RuntimeError("can't start new thread")

        replies = []

        class Handler:
            def __init__(self, onboarder):
                self.server = type("Server", (), {"onboarder": onboarder})()

            def _reply(self, code, body, content_type="application/json"):
                replies.append(code)

        before = len(self.network.calls)
        with patch.object(threading, "Thread", NoThread):
            with self.assertRaises(RuntimeError):
                onboarding.PortalHandler._security(Handler(self.onboarder),
                                                  {"mode": "wpa"})
        self.assertEqual(replies, [202], "the page was not answered before the failure")
        self.assertEqual(len(self.network.calls), before,
                         "the radio was changed although no worker could run")
        admitted, reason = self.onboarder.admit("HomeWiFi")
        self.assertTrue(admitted, f"the radio was never given back: {reason}")
        # And the mode goes back with it. The page was told to reconnect with a
        # password, so leaving `wpa` stored while the access point is still open
        # is a lockout: the next status poll says the network is protected and
        # the phone presents a key the radio never asks for.
        self.assertEqual(self.onboarder.security, "none",
                         "the stored mode was changed although nothing was raised")
        self.assertFalse(self.state_path.with_name("setup-security").exists(),
                         "the failed change froze its mode into a stored choice")

    def test_the_mode_goes_back_when_the_status_cannot_be_read_for_the_reply(self):
        # The other path into the same `finally`: the change is stored, and then
        # building the reply cannot read the state. The page is never answered,
        # so nothing must be left claiming a change is under way.
        replies = []

        class Handler:
            def __init__(self, onboarder):
                self.server = type("Server", (), {"onboarder": onboarder})()

            def _reply(self, code, body, content_type="application/json"):
                replies.append(code)

        real_status = onboarding.Onboarder.status

        def status(onboarder):
            raise OSError(5, "Input/output error")

        with patch.object(onboarding.Onboarder, "status", status):
            with self.assertRaises(OSError):
                onboarding.PortalHandler._security(Handler(self.onboarder),
                                                  {"mode": "wpa"})
        self.assertEqual(replies, [], "a reply was sent for a change that did not happen")
        self.assertEqual(self.onboarder.security, "none")
        self.assertFalse(self.state_path.with_name("setup-security").exists())
        admitted, reason = self.onboarder.admit("HomeWiFi")
        self.assertTrue(admitted, f"the radio was never given back: {reason}")

    def test_reposting_the_mode_in_force_does_not_freeze_a_choice(self):
        # A stale page posts the opposite of the mode it last polled, and that
        # mode may be the one already in force. It still re-raises the access
        # point - that is also how a raise that failed is retried, and how
        # somebody asks to see the password again - but it must not write a
        # stored choice. A stored file outranks the installer's flag for ever
        # after, so this would silently disable a later --setup-security.
        self.assertEqual(self.onboarder.security, "none")
        before = len(self.network.calls)
        code, body = self.request("/api/security", {"mode": "none"})
        self.assertEqual(code, 202)
        self.assertNotIn("password", json.loads(body))
        self.settle(before)
        self.assertFalse(self.state_path.with_name("setup-security").exists(),
                         "a change that changed nothing created a stored choice")
        self.assertGreater(len(self.network.calls), before,
                           "the access point was not re-raised, so a failed raise "
                           "could never be retried")

    def test_reposting_wpa_serves_the_same_password_again(self):
        # The other half, and a real use: the person lost the note and wants the
        # password the device is actually using. It must be the same one, not a
        # new one that strands every phone that already has the old.
        before = len(self.network.calls)
        code, body = self.request("/api/security", {"mode": "wpa"})
        self.assertEqual(code, 202)
        first = json.loads(body)["password"]
        self.settle(before)
        # Step past the interval a real person waiting for the page would, so
        # this measures the password and not the throttle.
        self.onboarder._last_security_change = float("-inf")
        code, body = self.request("/api/security", {"mode": "wpa"})
        self.assertEqual(code, 202)
        self.assertEqual(json.loads(body)["password"], first,
                         "a repeated request drew a different password")

    def test_a_foreign_origin_is_refused_like_the_join_handler(self):
        before = len(self.network.calls)
        code, _ = self.request("/api/security", {"mode": "wpa"}, host="evil.example")
        self.assertEqual(code, 403)
        self.assertEqual(len(self.network.calls), before)
        self.assertEqual(self.onboarder.status()["security"], "none")

    def test_a_reply_that_cannot_be_delivered_leaves_the_radio_alone(self):
        # The mode was written before the reply. If the browser never hears it,
        # the device must not ask for a password nobody was told.
        real_reply = onboarding.PortalHandler._reply

        def reply(handler, code, body, content_type="application/json"):
            if code == 202:
                raise BrokenPipeError(32, "Broken pipe")
            return real_reply(handler, code, body, content_type)

        before = len(self.network.calls)
        with patch.object(onboarding.PortalHandler, "_reply", reply):
            with self.assertRaises(OSError):
                self.request("/api/security", {"mode": "wpa"})
        self.assertEqual(len(self.network.calls), before,
                         "the access point was re-raised for a reply that never arrived")
        self.assertEqual(self.onboarder.status()["security"], "none",
                         "the mode stayed changed although the person was never told")
        self.assertIn("none (development build)",
                      self.note.read_text(encoding="utf-8"))


class SetupPasswordTests(Temp):
    """The setup network has to be joinable, and only by someone with the card."""

    def test_the_password_is_random_rather_than_computed_from_the_device_name(self):
        # The network name is the device name, so a password derived from it -
        # "debra-" plus a hash of "debra-345678" - was the same public
        # information in different letters. Anyone in range could compute it.
        first = onboarding.setup_secret(self.dir / "one" / "secret")
        second = onboarding.setup_secret(self.dir / "two" / "secret")
        self.assertNotEqual(first, second)
        self.assertNotIn(hashlib.sha256(b"debra-demo1").hexdigest()[:8], first)
        self.assertGreaterEqual(len(first), 8)
        self.assertLessEqual(len(first), 63)
        self.assertTrue(set(first) <= set(onboarding.SECRET_ALPHABET))

    def test_an_empty_secret_file_is_repaired_rather_than_redrawn_each_time(self):
        # A power loss between creating the file and writing it leaves exactly
        # this. "The file exists" was taken to mean "there is a password", so
        # every caller got a fresh one and the file was never repaired.
        path = self.dir / "secret"
        path.write_text("", encoding="utf-8")
        first = onboarding.setup_secret(path)
        self.assertEqual(onboarding.setup_secret(path), first)
        self.assertEqual(path.read_text(encoding="utf-8").strip(), first,
                         "the empty file was never repaired")
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_a_truncated_secret_is_replaced_rather_than_served(self):
        # A file damaged to a few characters still reads as non-empty. The
        # profile writer refuses anything under eight characters, so serving it
        # would tell the person a password the access point then declines to use.
        path = self.dir / "secret"
        path.write_text("abc\n", encoding="utf-8")
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            secret = onboarding.setup_secret(path)
        self.assertGreaterEqual(len(secret), 8)
        self.assertTrue(nm_module.valid_psk(secret))
        self.assertEqual(path.read_text(encoding="utf-8").strip(), secret,
                         "the damaged file was not repaired")

    def test_the_password_is_kept_so_a_second_raise_agrees_with_the_note(self):
        # The access point is raised again after a failed join. A fresh
        # password each time would strand a person holding a note already read.
        path = self.dir / "secret"
        first = onboarding.setup_secret(path)
        self.assertEqual(onboarding.setup_secret(path), first)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600,
                         "the setup password must not be world-readable")

    def test_the_adapter_is_given_a_password_rather_than_left_to_invent_one(self):
        # Asking nmcli to invent one produced a WPA2 network whose key nobody
        # was ever shown, so the password has to be ours and has to be long
        # enough to be a valid PSK (8-63).
        network = FakeNetwork()
        onboarder = self.onboarder(network, security="wpa")
        onboarder.start_hotspot()
        hotspot_calls = [call for call in network.calls if call[0] == "start_hotspot"]
        self.assertTrue(hotspot_calls[0][3], "start_hotspot was called without a password")
        self.assertGreaterEqual(len(onboarding.setup_secret(onboarder.secret_path)), 8,
                                "a PSK shorter than eight characters is invalid")

    def test_the_household_passphrase_is_never_written_into_the_setup_state(self):
        # The old version of this test only raised the access point and never
        # submitted anything, so it could not fail on the passphrase at all.
        onboarder = self.onboarder(security="wpa")
        onboarder.start_hotspot()
        status = onboarder.join("HomeWiFi", "correct horse battery", None)
        self.assertEqual(status["phase"], "online")
        stored = self.state_path.read_text(encoding="utf-8")
        password = onboarding.setup_secret(onboarder.secret_path)
        self.assertNotIn(password, stored)
        self.assertNotIn("password", stored)

    def test_the_password_is_not_served_by_the_status_page(self):
        # The status response is read by anything that has joined the network,
        # so it is not a place to keep the credential that let it join.
        onboarder = self.onboarder(security="wpa")
        status = onboarder.start_hotspot()
        self.assertNotIn("password", status["hotspot"])
        self.assertNotIn(onboarding.setup_secret(onboarder.secret_path),
                         json.dumps(status))

    def test_the_card_note_says_the_three_things_needed_before_any_page_loads(self):
        note = self.dir / "boot" / "debra-setup.txt"
        onboarder = self.onboarder(card_note_path=note, security="wpa")
        onboarder.start_hotspot()
        text = note.read_text(encoding="utf-8")
        self.assertIn("Debra-Setup-demo1", text)
        self.assertIn(onboarding.setup_secret(onboarder.secret_path), text)
        self.assertIn("http://", text)

    def test_a_reprinted_note_keeps_the_password_the_access_point_was_raised_with(self):
        # The note is rewritten once the page's real address is known. It has to
        # carry the same password the access point is running with: the status
        # no longer serves it, so the device's own file is the source.
        note = self.dir / "boot" / "debra-setup.txt"
        network = FakeNetwork()
        onboarder = self.onboarder(network, card_note_path=note, security="wpa")
        onboarder.start_hotspot()
        first = onboarding.setup_secret(onboarder.secret_path)
        onboarder.announce_portal("192.0.2.9")
        text = note.read_text(encoding="utf-8")
        self.assertIn(first, text, "the reprinted note lost the password")
        self.assertIn("192.0.2.9", text)


class SetupSecurityTests(Temp):
    """Open is a mode somebody chose, not what happens when nothing was set."""

    def test_the_default_is_the_development_bypass(self):
        # Where Debra is today: the setup network comes up open so nothing has
        # to be read off a card before the page can be reached. This is a
        # deliberate default, kept in one constant, not an absence of one.
        #
        # The assertion is on the behaviour of a device that was told nothing,
        # not on the constant itself: restating `DEFAULT_SETUP_SECURITY == "none"`
        # would pass even if the constructor ignored it.
        network = FakeNetwork()
        status = self.onboarder(network).start_hotspot()
        self.assertEqual(status["security"], "none")
        calls = [call for call in network.calls if call[0] == "start_hotspot"]
        self.assertEqual(calls[0][3], False)

    def test_the_protected_mode_is_one_flag_away(self):
        # The other half of the same decision: the security that is bypassed by
        # default has to keep working, or the bypass quietly becomes the only
        # path and nobody notices until release.
        network = FakeNetwork()
        status = self.onboarder(network, security="wpa").start_hotspot()
        self.assertEqual(status["security"], "wpa")
        calls = [call for call in network.calls if call[0] == "start_hotspot"]
        self.assertTrue(calls[0][3], "wpa mode must give the adapter a password")

    def test_a_development_build_raises_an_open_network_and_says_so(self):
        network = FakeNetwork()
        note = self.dir / "boot" / "debra-setup.txt"
        status = self.onboarder(network, security="none",
                                card_note_path=note).start_hotspot()
        self.assertEqual(status["security"], "none")
        calls = [call for call in network.calls if call[0] == "start_hotspot"]
        self.assertEqual(calls[0][3], False, "an open network carries no password")
        # The note and the page both have to be honest: a person who cannot
        # join will otherwise go looking for a password that does not exist.
        text = note.read_text(encoding="utf-8")
        self.assertIn("none", text)
        self.assertIn("development", text)

    def test_an_unknown_mode_is_refused_rather_than_treated_as_open(self):
        # A typo in an install argument must not quietly widen access.
        with self.assertRaises(ValueError):
            self.onboarder(FakeNetwork(), security="off")

    def test_a_mode_nobody_wrote_yet_is_not_assumed(self):
        with self.assertRaises(ValueError):
            self.onboarder(FakeNetwork(), security="")


class LegacySecretAdoptionTests(Temp):
    """A device that was protected by the previous build stays protected.

    The previous build kept the setup password inside `setup.json`. This one
    keeps it in its own file, and the migration drops the old key. Without a
    deliberate hand-over, an upgrade would open the setup network - and the
    installed default being `none` means nothing else would stop it.
    """

    def legacy(self, **overrides):
        data = dict(state_module.blank("debra-345678"), schema=2,
                    phase="hotspot",
                    hotspot={"ssid": "Debra-Setup-345678", "interface": "wlan0"},
                    hotspot_password="abcdefghjk2m")
        data.update(overrides)
        self.state_path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def test_the_old_password_is_carried_into_its_own_file(self):
        self.legacy()
        network = FakeNetwork()
        # The installer says `none`, which is the development default. The
        # upgrade is the only thing that can keep this device protected, so it
        # has to outrank that default.
        with self.assertLogs(onboarding.LOGGER, level="WARNING") as logs:
            onboarder = self.onboarder(network, security="none")
        self.assertIn("stays protected", "\n".join(logs.output))
        self.assertEqual(onboarder.adopted_security, "wpa")
        self.assertEqual(onboarder.security, "wpa")
        secret = self.state_path.with_name("setup-secret")
        self.assertEqual(secret.read_text(encoding="utf-8").strip(), "abcdefghjk2m")
        self.assertEqual(stat.S_IMODE(secret.stat().st_mode), 0o600)
        stored = self.state_path.with_name("setup-security")
        self.assertEqual(stored.read_text(encoding="utf-8").strip(), "wpa")
        # And the boot that follows raises a protected network with that very
        # password, rather than the open one the installed default asks for.
        status = onboarder.resume()
        self.assertEqual(status["phase"], "hotspot")
        self.assertEqual(network.hotspot["password"], "abcdefghjk2m")

    def test_the_password_is_not_left_in_the_state_after_the_upgrade(self):
        self.legacy()
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            onboarder = self.onboarder(FakeNetwork(), security="none")
        onboarder.resume()
        raw = self.state_path.read_text(encoding="utf-8")
        self.assertNotIn("hotspot_password", raw)
        self.assertNotIn("abcdefghjk2m", raw)
        self.assertEqual(json.loads(raw)["schema"], state_module.SCHEMA)

    def test_a_mode_the_page_chose_is_not_overridden_by_the_old_record(self):
        # The page's decision is later than the record's password. A device
        # whose owner turned the password off before the upgrade must stay open.
        self.legacy()
        (self.dir / "setup-security").write_text("none\n", encoding="utf-8")
        onboarder = self.onboarder(FakeNetwork(), security="none")
        self.assertIsNone(onboarder.adopted_security)
        self.assertEqual(onboarder.security, "none")
        self.assertFalse((self.dir / "setup-secret").exists(),
                         "a password file was created for a network switched off on purpose")

    def test_a_junk_mode_file_is_not_a_choice(self):
        # `_stored_security` reads a junk file as "no usable choice", and the
        # adoption has to agree. Standing down for a file nobody can use would
        # fall back to the installed `none` and drop the password in the same
        # boot - the one direction this function exists to prevent.
        self.legacy()
        (self.dir / "setup-security").write_text("off\n", encoding="utf-8")
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            onboarder = self.onboarder(FakeNetwork(), security="none")
        self.assertEqual(onboarder.adopted_security, "wpa")
        self.assertEqual(onboarder.security, "wpa")
        self.assertEqual((self.dir / "setup-security").read_text(encoding="utf-8").strip(),
                         "wpa", "the unusable mode file was left in place")

    def test_an_unreadable_mode_file_is_not_a_choice(self):
        # `exists()` used to stand adoption down here. A directory where the
        # mode belongs is not a choice; the record's password still has to win,
        # or the device falls back to the installed `none` and opens.
        self.legacy()
        (self.dir / "setup-security").mkdir()
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            onboarder = self.onboarder(FakeNetwork(), security="none")
        self.assertEqual(onboarder.adopted_security, "wpa")
        self.assertEqual(onboarder.security, "wpa")

    def test_a_mode_file_that_is_not_utf8_is_not_a_choice(self):
        self.legacy()
        (self.dir / "setup-security").write_bytes(b"\xff\xfe\x00")
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            onboarder = self.onboarder(FakeNetwork(), security="none")
        self.assertEqual(onboarder.adopted_security, "wpa")
        self.assertEqual(onboarder.security, "wpa")
        self.assertEqual((self.dir / "setup-security").read_text(encoding="utf-8").strip(),
                         "wpa")

    def test_a_password_that_cannot_be_moved_still_keeps_the_boot_protected(self):
        # Writing the mode is what makes the network protected. The password
        # file failing is the narrower failure, and it must not open the
        # network: this boot draws a fresh password and asks for one.
        self.legacy()
        network = FakeNetwork()
        with patch.object(onboarding, "_store_secret", return_value=False):
            with self.assertLogs(onboarding.LOGGER, level="WARNING"):
                onboarder = self.onboarder(network, security="none")
            self.assertEqual(onboarder.security, "wpa")
            status = onboarder.resume()
        self.assertEqual(status["phase"], "hotspot")
        self.assertTrue(network.hotspot["password"],
                        "the access point came up open")
        self.assertNotEqual(network.hotspot["password"], "abcdefghjk2m",
                            "the password survived without being written")
        self.assertEqual(self.state_path.with_name("setup-security")
                         .read_text(encoding="utf-8").strip(), "wpa")

    def test_a_mode_that_cannot_be_stored_still_protects_this_boot(self):
        # The choice cannot outlive the reboot, but opening the network now is
        # worse. The mode is adopted for the running process and the journal
        # says the next boot may fall back.
        self.legacy()
        network = FakeNetwork()
        with patch.object(onboarding, "_write_mode", side_effect=OSError(30, "Read-only")):
            with self.assertLogs(onboarding.LOGGER, level="WARNING") as logs:
                onboarder = self.onboarder(network, security="none")
        self.assertIn("later boot", "\n".join(logs.output))
        self.assertEqual(onboarder.adopted_security, "wpa")
        self.assertEqual(onboarder.security, "wpa")
        status = onboarder.resume()
        self.assertEqual(status["phase"], "hotspot")
        self.assertEqual(network.hotspot["password"], "abcdefghjk2m")

    def test_a_record_without_a_password_is_not_an_upgrade(self):
        # The previous build wrote a password whenever it raised the access
        # point, so a record without one describes a device that never raised
        # one. Nothing was protected, and the installed mode still applies -
        # inferring a choice here would freeze one nobody made.
        self.legacy(hotspot_password=None)
        onboarder = self.onboarder(FakeNetwork(), security="none")
        self.assertIsNone(onboarder.adopted_security)
        self.assertEqual(onboarder.security, "none")

    def test_the_adopted_choice_survives_the_next_boot(self):
        self.legacy()
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            self.onboarder(FakeNetwork(), security="none").resume()
        # A second boot reads a schema-3 record and no longer has a legacy
        # password to move, but the mode and the password file are still there.
        again = self.onboarder(FakeNetwork(), security="none")
        self.assertIsNone(again.adopted_security)
        self.assertEqual(again.security, "wpa")
        self.assertEqual(onboarding.setup_secret(again.secret_path), "abcdefghjk2m")


class SetupSecuritySwitchTests(Temp):
    """The mode is a choice on the page, not only an installer argument."""

    def test_the_chosen_mode_is_kept_and_wins_over_the_installed_default(self):
        onboarder = self.onboarder(security="none")
        onboarder.start_hotspot()
        self.assertEqual(onboarder.status()["security"], "none")
        onboarder.set_security("wpa")
        stored = self.state_path.with_name("setup-security")
        self.assertEqual(stored.read_text(encoding="utf-8").strip(), "wpa")
        self.assertEqual(stat.S_IMODE(stored.stat().st_mode), 0o600,
                         "the chosen mode must not be world-readable")
        # A new process starts from the installed default and still has to come
        # up protected: the person's choice outlives the boot that made it.
        again = self.onboarder(security="none")
        self.assertEqual(again.status()["security"], "wpa")
        # And it is not in the state record, whose schema is closed: a new key
        # there would make every state file written before it unreadable.
        self.assertNotIn("security", json.loads(self.state_path.read_text(encoding="utf-8")))

    def test_the_stored_mode_is_what_the_access_point_is_raised_with(self):
        self.onboarder(security="none").set_security("wpa")
        network = FakeNetwork()
        self.onboarder(network, security="none").start_hotspot()
        calls = [call for call in network.calls if call[0] == "start_hotspot"]
        self.assertTrue(calls[0][3],
                        "the stored mode was ignored: the access point came up open")

    def test_the_mode_and_password_files_sync_the_directory(self):
        # The mode decides whether the next boot opens the network. Losing the
        # rename that turned the password on is the same defect as never having
        # turned it on, so both files are written through a synced rename.
        calls = []
        real = state_module.sync_directory

        def sync(path):
            calls.append(Path(path))
            return real(path)

        onboarder = self.onboarder(security="none")
        with patch.object(state_module, "sync_directory", sync):
            onboarder.set_security("wpa")
            onboarder.hotspot_password()
        self.assertEqual(calls, [self.dir, self.dir],
                         "a mode or password rename was not made durable")

    def test_an_unknown_mode_is_refused_and_writes_nothing(self):
        onboarder = self.onboarder(security="wpa")
        stored = self.state_path.with_name("setup-security")
        with self.assertRaises(ValueError):
            onboarder.set_security("open")
        self.assertFalse(stored.exists(), "a refused mode left a file behind")
        self.assertEqual(onboarder.status()["security"], "wpa")

    def test_a_corrupt_mode_file_is_not_a_choice_somebody_made(self):
        # `has_stored_security` decides whether a revert may write the mode back.
        # `exists()` would answer yes for a hand-edited junk file, and the revert
        # would then turn the junk into a stored choice that outranks the
        # installer's flag for ever - the exact outcome the `had_choice` guard
        # exists to prevent, arriving from a different input.
        stored = self.state_path.with_name("setup-security")
        stored.write_text("wpaa\n", encoding="utf-8")
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            onboarder = self.onboarder(security="none")
        self.assertFalse(onboarder.has_stored_security(),
                         "a corrupt mode file was counted as a choice")
        stored.write_text("wpa\n", encoding="utf-8")
        self.assertTrue(onboarder.has_stored_security())

    def test_a_stored_mode_that_is_not_one_falls_back_to_the_installed_default(self):
        # Installed `none` and a stored value that is not a mode: the installed
        # default is the only answer left, and it is deliberately not the same
        # as the choice the corrupted file looks most like (`wpa`). Written the
        # other way round - installed `wpa`, stored `wpaa` - an implementation
        # that ignored the file entirely would pass this test by accident.
        stored = self.state_path.with_name("setup-security")
        stored.write_text("wpaa\n", encoding="utf-8")
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            onboarder = self.onboarder(security="none")
        self.assertEqual(onboarder.status()["security"], "none")
        self.assertEqual(onboarder.security_source, "install")

    def test_a_stored_mode_that_is_not_utf8_does_not_stop_the_service(self):
        # The file lives in a directory a person can edit. One stray byte used
        # to raise UnicodeDecodeError out of the constructor, and the service
        # then exited with no access point at all.
        stored = self.state_path.with_name("setup-security")
        stored.write_bytes(b"\xff\xfe\x00wpa")
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            onboarder = self.onboarder(security="wpa")
        self.assertEqual(onboarder.status()["security"], "wpa")

    def test_a_second_change_is_refused_while_one_is_running(self):
        # The claim, not the throttle: a second request arriving during a change
        # must not cycle the radio again, whatever the interval says.
        clock = [1000.0]
        network = FakeNetwork()
        onboarder = self.onboarder(network, security="none", clock=lambda: clock[0])
        onboarder.start_hotspot()
        self.assertIs(onboarder.begin_security_change(), True)
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        self.assertEqual(onboarder.begin_security_change(), "busy")
        onboarder.abandon_security_change()
        self.assertIs(onboarder.begin_security_change(), True)
        onboarder.abandon_security_change()

    def test_the_radio_is_released_when_the_change_finishes(self):
        # The sibling of the line above: a claim that is never released turns
        # every later join and change into a refusal.
        clock = [1000.0]
        network = FakeNetwork()
        onboarder = self.onboarder(network, security="none", clock=lambda: clock[0])
        onboarder.start_hotspot()
        self.assertIs(onboarder.begin_security_change(), True)
        generation = onboarder.security_generation()
        onboarder.set_security("wpa")
        onboarder.rearm_hotspot(generation)
        clock[0] += 2 * onboarding.SUBMIT_INTERVAL_S
        self.assertIs(onboarder.begin_security_change(), True,
                      "the change never released the radio")
        onboarder.abandon_security_change()

    def superseded(self, network):
        """An onboarder with a stale generation from an abandoned change.

        The clock is stepped past the interval between the two claims: without
        that the second `begin_security_change` would be throttled and would not
        advance the generation, so there would be nothing stale to compare.
        """
        clock = [1000.0]
        onboarder = self.onboarder(network, security="none", clock=lambda: clock[0])
        onboarder.start_hotspot()
        self.assertIs(onboarder.begin_security_change(), True)
        stale = onboarder.security_generation()
        onboarder.abandon_security_change()
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        self.assertIs(onboarder.begin_security_change(), True)
        return onboarder, stale

    def test_a_superseded_change_is_not_raised(self):
        # Two changes could not both be admitted now, but the guard is what makes
        # that true if the admission rule ever loosens. An older change applied
        # after a newer one leaves the access point in a mode whose password the
        # client that asked for it was never given.
        network = FakeNetwork()
        onboarder, stale = self.superseded(network)
        onboarder.set_security("wpa")
        before = len(network.calls)
        onboarder.rearm_hotspot(stale)
        self.assertEqual(network.calls[before:], [],
                         "a superseded change still cycled the radio")

    def test_a_superseded_revert_is_not_applied(self):
        network = FakeNetwork()
        onboarder, stale = self.superseded(network)
        onboarder.set_security("wpa")
        onboarder.restore_security("none", stale)
        self.assertEqual(onboarder.security, "wpa",
                         "a superseded request undid a later change")
        self.assertEqual(
            self.state_path.with_name("setup-security").read_text().strip(), "wpa")

    def test_a_revert_restores_a_choice_that_was_already_there(self):
        # `restore_security` has two branches: write the previous mode back when
        # the device carried a page-made choice, remove the file when it did
        # not. Both tests for a lost reply take the remove branch, so an
        # implementation that always removed - silently discarding somebody's
        # choice - would pass the suite.
        clock = [1000.0]
        network = FakeNetwork()
        onboarder = self.onboarder(network, security="none", clock=lambda: clock[0])
        onboarder.start_hotspot()
        onboarder.set_security("none")          # a page-made choice, of "none"
        stored = self.state_path.with_name("setup-security")
        self.assertTrue(onboarder.has_stored_security())
        self.assertIs(onboarder.begin_security_change(), True)
        generation = onboarder.security_generation()
        onboarder.set_security("wpa")
        onboarder.restore_security("none", generation, had_choice=True)
        self.assertTrue(stored.exists(),
                        "the revert removed a choice somebody had made")
        self.assertEqual(stored.read_text(encoding="utf-8").strip(), "none")
        self.assertEqual(onboarder.security, "none")

    def test_a_rearm_that_cannot_run_is_recorded_rather_than_raised(self):
        # This runs in a worker thread, where a traceback goes to stderr and
        # nowhere a person will look. The mode is already stored, so what is
        # missing is that anybody was told this raise did not take.
        network = FakeNetwork()
        onboarder = self.onboarder(network, security="none")
        onboarder.start_hotspot()
        onboarder.set_security("wpa")
        with patch.object(onboarding.Onboarder, "start_hotspot",
                          side_effect=OSError(28, "No space left on device")):
            status = onboarder.rearm_hotspot()
        self.assertEqual(status["last_error"],
                         "The setup network did not change on this device")
        # And the radio was given back: the failure must not lock the device out
        # of joining for the life of the process.
        admitted, reason = onboarder.admit("HomeWiFi")
        self.assertTrue(admitted, f"the radio was never given back: {reason}")

    def test_the_interval_is_measured_from_the_end_of_a_change(self):
        # A change that outlasts the interval must still buy the same quiet
        # period afterwards, or the next request is admitted the moment it
        # arrives and the radio is cycled twice in a row.
        clock = [1000.0]
        network = FakeNetwork()
        onboarder = self.onboarder(network, security="none", clock=lambda: clock[0])
        onboarder.start_hotspot()
        self.assertIs(onboarder.begin_security_change(), True)
        generation = onboarder.security_generation()
        onboarder.set_security("wpa")
        clock[0] += 4.0
        onboarder.rearm_hotspot(generation)
        clock[0] += 2.0
        self.assertEqual(onboarder.begin_security_change(), "throttle",
                         "a long change was repeatable as soon as it finished")

    def test_a_second_change_inside_the_interval_is_refused(self):
        # Anybody on the access point can post the toggle, and it is open by
        # default. Without an interval a loop of posts cycles the radio for
        # everyone on it.
        clock = [1000.0]
        network = FakeNetwork()
        onboarder = self.onboarder(network, security="none", clock=lambda: clock[0])
        onboarder.start_hotspot()
        self.assertIs(onboarder.begin_security_change(), True)
        onboarder.abandon_security_change()
        self.assertEqual(onboarder.begin_security_change(), "throttle",
                         "a second change was accepted immediately")
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        self.assertIs(onboarder.begin_security_change(), True)
        onboarder.abandon_security_change()

    def test_the_password_is_never_in_the_status_before_or_after_a_switch(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network, security="none")
        onboarder.start_hotspot()
        self.assertNotIn("password", json.dumps(onboarder.status()))
        onboarder.set_security("wpa")
        onboarder.rearm_hotspot()
        password = onboarding.setup_secret(onboarder.secret_path)
        self.assertEqual(onboarder.status()["security"], "wpa")
        self.assertNotIn(password, json.dumps(onboarder.status()),
                         "the status page became a second place to read the password")

    def test_the_whole_stop_and_raise_happens_in_the_adapter(self):
        # Not in the caller: a stop at this level deletes the profile, and a new
        # shared connection is given the next subnet.
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        before = list(network.calls)
        onboarder.rearm_hotspot()
        added = network.calls[len(before):]
        self.assertNotIn(("stop_hotspot",), added,
                         "the profile was deleted instead of being re-keyed in place")
        self.assertIn("start_hotspot", [call[0] for call in added])

    def test_an_address_that_moved_is_recorded_rather_than_ignored(self):
        # The page is bound when it starts, so an access point that comes back
        # on a different address leaves the socket where nothing answers. That
        # is not a successful change that looks like one.
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        real_start = network.start_hotspot

        def moved(ssid, interface, password=None):
            # Shared mode hands the next shared connection the next subnet, so
            # this is what a delete-and-recreate would have done.
            network.address = "10.43.0.1"
            return real_start(ssid, interface, password)

        network.start_hotspot = moved
        with self.assertLogs(onboarding.LOGGER, level="WARNING") as logs:
            onboarder.rearm_hotspot()
        self.assertIn("moved from 10.42.0.1 to 10.43.0.1",
                      onboarder.status()["last_error"] or "")
        self.assertIn("moved from 10.42.0.1 to 10.43.0.1", "\n".join(logs.output))

    def test_an_unchanged_address_is_not_reported_as_a_failure(self):
        # The other half: a warning that fires every time would be noise, and a
        # state that always carried a last_error would stop meaning anything.
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        status = onboarder.rearm_hotspot()
        self.assertEqual(status["phase"], "hotspot")
        self.assertIsNone(status["last_error"])

    def test_a_re_raise_is_not_attempted_while_a_join_is_in_flight(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        accepted, _ = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)
        before = list(network.calls)
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            onboarder.rearm_hotspot()
        self.assertEqual(network.calls, before,
                         "an access point was raised over a join in progress")
        self.assertEqual(state_module.read(self.state_path)["phase"], "connecting")


class WorkerBoundaryTests(Temp):
    """The two background workers promise not to traceback. Check all of it.

    Both start after the browser has already been answered, so an exception
    escaping their threads goes to stderr and nowhere a person will look, and
    the device is left in a mode nobody was told about.
    """

    def corrupt(self):
        self.state_path.write_text("{not json", encoding="utf-8")

    def test_the_mode_change_worker_does_not_raise_on_a_corrupt_state(self):
        onboarder = self.onboarder(FakeNetwork(), security="wpa")
        onboarder.start_hotspot()
        self.corrupt()
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            status = onboarder.rearm_hotspot(generation=onboarder.security_generation())
        self.assertEqual(status["phase"], "failed")
        self.assertIn("could not be read", status["last_error"])

    def test_a_status_failure_after_the_raise_does_not_claim_nothing_changed(self):
        # The raise succeeded, and then the status read for the answer failed.
        # That is not a failed change, and recording it as one hides the raise
        # that did happen. The second call is the one `_rearm_now` makes after
        # `start_hotspot` has already raised the network.
        network = FakeNetwork()
        onboarder = self.onboarder(network, security="wpa")
        onboarder.start_hotspot()
        real = onboarder.status
        calls = []

        # A plain function replaces the method, so it receives the instance.
        def status(_self):
            calls.append(1)
            if len(calls) > 1:
                raise ValueError("synthetic")
            return real()

        with patch.object(onboarding.Onboarder, "status", status):
            with self.assertLogs(onboarding.LOGGER, level="WARNING"):
                status_dict = onboarder.rearm_hotspot()
        self.assertEqual(len([call for call in network.calls
                              if call[0] == "start_hotspot"]), 2,
                         "the access point was not raised again")
        self.assertEqual(status_dict["phase"], "failed")
        recorded = state_module.read(self.state_path)["last_error"]
        self.assertNotEqual(recorded, "The setup network did not change on this device",
                            "a failed status read was recorded as a failed change")
        self.assertIsNone(recorded, "the raise succeeded, so there is nothing to record")

    def test_a_status_failure_inside_the_raise_is_not_a_failed_change(self):
        # `start_hotspot` ends by reading the status for its answer, and the
        # access point is up by then. If that read fails, `_rearm` must not
        # record "the setup network did not change" for a change that did.
        network = FakeNetwork()
        onboarder = self.onboarder(network, security="wpa")
        onboarder.start_hotspot()
        real = onboarder.status
        calls = []

        # A plain function replaces the method, so it receives the instance.
        def status(_self):
            calls.append(1)
            if len(calls) == 1:
                raise ValueError("synthetic")
            return real()

        with patch.object(onboarding.Onboarder, "status", status):
            with self.assertLogs(onboarding.LOGGER, level="WARNING"):
                status_dict = onboarder.rearm_hotspot()
        self.assertGreaterEqual(len(calls), 2, "the raise path never read the status")
        self.assertEqual(len([call for call in network.calls
                              if call[0] == "start_hotspot"]), 2,
                         "the access point was not raised again")
        self.assertEqual(status_dict["phase"], "hotspot")
        self.assertIsNone(state_module.read(self.state_path)["last_error"],
                          "a status read failed after the raise and was recorded "
                          "as a change that did not happen")

    def test_the_mode_change_worker_does_not_raise_when_status_fails(self):
        # `status()` is the last thing the worker calls, and the state it reads
        # is the state the whole operation depends on.
        onboarder = self.onboarder(FakeNetwork(), security="wpa")
        onboarder.start_hotspot()
        with patch.object(onboarding.Onboarder, "status",
                          side_effect=RuntimeError("synthetic")):
            with self.assertLogs(onboarding.LOGGER, level="WARNING"):
                status = onboarder.rearm_hotspot()
        self.assertEqual(status["phase"], "failed")

    def test_the_join_worker_does_not_raise_when_the_state_cannot_be_read(self):
        # `_safe_status` inside `_join_reserved` covers a failing status read.
        # This fails the state read itself, so only the worker's own boundary
        # can keep the exception out of the thread.
        onboarder = self.onboarder(FakeNetwork())
        onboarder.start_hotspot()
        accepted, token = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)
        with patch.object(state_module, "read", side_effect=RuntimeError("synthetic")):
            with self.assertLogs(onboarding.LOGGER, level="WARNING"):
                status = onboarder.join_reserved("HomeWiFi", "correct horse battery",
                                                 None, token=token)
        self.assertEqual(status["phase"], "failed")

    def test_the_join_worker_does_not_raise_when_status_fails(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        accepted, token = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)
        with patch.object(onboarding.Onboarder, "status",
                          side_effect=RuntimeError("synthetic")):
            with self.assertLogs(onboarding.LOGGER, level="WARNING"):
                status = onboarder.join_reserved("HomeWiFi", "correct horse battery",
                                                 None, token=token)
        self.assertEqual(status["phase"], "failed")


class ModeSourceTests(Temp):
    """The journal has to say whether the page or the flag decided the mode."""

    def test_a_stored_mode_is_attributed_to_the_page(self):
        (self.dir / "setup-security").write_text("none\n", encoding="utf-8")
        onboarder = self.onboarder(FakeNetwork(), security="wpa")
        self.assertEqual(onboarder.security, "none")
        self.assertEqual(onboarder.security_source, "page",
                         "the page's choice was reported as the installer's flag")

    def test_an_adopted_mode_is_never_reported_as_the_flag(self):
        # Adoption writes `wpa` into the mode file before it is read, so the
        # device runs protected under a flag that says `none`. The source is
        # "page" in the narrow sense of "the mode the device carries"; what
        # matters is that it is not "install", because the open-network journal
        # line - the only reader - would then blame the flag.
        self.state_path.write_text(json.dumps(dict(
            state_module.blank("debra-345678"), schema=2, phase="hotspot",
            hotspot={"ssid": "Debra-Setup-345678", "interface": "wlan0"},
            hotspot_password="abcdefghjk2m")), encoding="utf-8")
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            onboarder = self.onboarder(FakeNetwork(), security="none")
        self.assertEqual(onboarder.security, "wpa")
        self.assertEqual(onboarder.security_source, "page",
                         "a carried-over mode was attributed to the unit's flag")


class AccessPointCheckTests(Temp):
    """The access point comes from a profile we wrote, and is then verified.

    `nmcli device wifi hotspot` cannot raise an open network: with no password
    it generates one and never shows it, so the development bypass came up
    protected and the read-back then deleted it, leaving no setup network at
    all. The profile is written the same way a household join is, and what is
    running is read back rather than assumed.
    """

    def setUp(self):
        super().setUp()
        self.profiles = self.dir / "system-connections"
        self.profiles.mkdir()

    def adapter(self, **kwargs):
        kwargs.setdefault("profile_dir", self.profiles)
        return nm_module.Nmcli(runner=Recorder(**kwargs), profiles_dir=self.profiles)

    def test_the_access_point_is_created_from_a_profile_we_wrote(self):
        recorder = Recorder(profile_dir=self.profiles)
        network = nm_module.Nmcli(runner=recorder, profiles_dir=self.profiles)
        raised = network.start_hotspot("Debra-Setup-demo1", "wlan0", "s3cretvalue")
        self.assertEqual(raised, {"key_mgmt": "wpa-psk", "address": "10.42.0.1"})
        # The command that cannot express "open" is not used at all, and the
        # password is in the profile rather than in argv where any process can
        # read it.
        flattened = [" ".join(call) for call in recorder.calls]
        self.assertFalse(any("device wifi hotspot" in call for call in flattened),
                         "nmcli was asked to invent the access point itself")
        self.assertNotIn("s3cretvalue", " ".join(flattened))
        text, mode, path = recorder.contents[-1]
        self.assertEqual(Path(path).parent, self.profiles,
                         "the profile was written where NetworkManager does not read")
        self.assertEqual(mode, 0o600, "the setup profile must be owner-only")
        self.assertIn("mode=ap", text)
        self.assertIn("key-mgmt=wpa-psk", text)
        self.assertIn("psk=s3cretvalue", text)
        self.assertIn("method=shared", text, "the access point would have no address to serve on")
        self.assertIn("autoconnect=false", text,
                      "a setup network that comes up on its own competes with the household one")
        self.assertIn(f"uuid={nm_module.HOTSPOT_UUID}", text)
        # Only the finished profile is there: a staging file would be parsed
        # half written by the plugin that watches the directory.
        self.assertEqual(sorted(item.name for item in self.profiles.iterdir()),
                         ["debra-setup.nmconnection"])

    def test_the_access_point_is_never_delegated_to_nmcli(self):
        # `nmcli device wifi hotspot` chooses the security itself and, without a
        # password, generates one nobody is shown. Even the protected form is
        # that tool's decision rather than ours, so it is not used at all - and
        # this is the test that says so with a message, rather than failing
        # somewhere downstream when the read-back disagrees.
        recorder = Recorder(profile_dir=self.profiles)
        network = nm_module.Nmcli(runner=recorder, profiles_dir=self.profiles)
        network.start_hotspot("Debra-Setup-demo1", "wlan0", "s3cretvalue")
        self.assertFalse(any(call[1:4] == ["device", "wifi", "hotspot"]
                             for call in recorder.calls),
                         "nmcli was asked to invent the access point: " + str(recorder.calls))

    def test_an_open_setup_network_is_a_profile_with_no_key_management(self):
        # The regression this whole path exists for. Asked for an open network
        # without a password, `device wifi hotspot` raises a WPA2 one whose key
        # nobody was shown, and the read-back then deletes it, leaving no setup
        # network at all.
        recorder = Recorder(profile_dir=self.profiles)
        network = nm_module.Nmcli(runner=recorder, profiles_dir=self.profiles)
        raised = network.start_hotspot("Debra-Setup-demo1", "wlan0", None)
        self.assertEqual(raised["key_mgmt"], "none")
        self.assertFalse(any(call[1:4] == ["device", "wifi", "hotspot"]
                             for call in recorder.calls),
                         "a password-less `device wifi hotspot` cannot be an open network")
        text = recorder.contents[-1][0]
        self.assertIn("key-mgmt=none", text)
        self.assertNotIn("psk=", text, "an open setup network carries no password")

    def test_a_running_access_point_is_brought_down_before_it_is_re_keyed(self):
        # A reload updates the stored profile; a running access point keeps the
        # settings it was activated with, so it has to be cycled - but the same
        # profile, or shared mode hands out a new subnet and the page's address
        # moves underneath it.
        recorder = Recorder(profile_dir=self.profiles)
        network = nm_module.Nmcli(runner=recorder, profiles_dir=self.profiles)
        network.start_hotspot("Debra-Setup-demo1", "wlan0", None)
        first_uuid = [line for line in recorder.contents[-1][0].splitlines()
                      if line.startswith("uuid=")]
        recorder.calls.clear()
        network.start_hotspot("Debra-Setup-demo1", "wlan0", "s3cretvalue")
        second_uuid = [line for line in recorder.contents[-1][0].splitlines()
                       if line.startswith("uuid=")]
        self.assertEqual(first_uuid, second_uuid, "the profile identity changed")
        verbs = [" ".join(call[1:]) for call in recorder.calls]
        reload_at = next(i for i, call in enumerate(verbs) if call == "connection reload")
        down_at = next(i for i, call in enumerate(verbs)
                       if call == "connection down id debra-setup")
        up_at = next(i for i, call in enumerate(verbs)
                     if call == "connection up id debra-setup ifname wlan0")
        self.assertLess(reload_at, down_at)
        self.assertLess(down_at, up_at)
        self.assertIn("key-mgmt=wpa-psk", recorder.contents[-1][0])

    def test_an_access_point_that_came_up_open_when_asked_protected_is_taken_down(self):
        recorder = Recorder(profile_dir=self.profiles, key_mgmt="none")
        network = nm_module.Nmcli(runner=recorder, profiles_dir=self.profiles)
        with self.assertRaises(nm_module.NmError) as caught:
            network.start_hotspot("Debra-Setup-demo1", "wlan0", "s3cretvalue")
        self.assertIn("could not be secured", str(caught.exception))
        self.assertIn(["nmcli", "connection", "delete", "debra-setup"], recorder.calls,
                      "an unsecured access point must not be left running")
        self.assertEqual(list(self.profiles.iterdir()), [],
                         "the rejected profile was left for the next reload")

    def test_an_access_point_that_came_up_protected_when_asked_open_is_refused_too(self):
        # Otherwise a development build silently stops being the bypass it says
        # it is, and every test of that path passes against a WPA2 one.
        recorder = Recorder(profile_dir=self.profiles, key_mgmt="wpa-psk")
        network = nm_module.Nmcli(runner=recorder, profiles_dir=self.profiles)
        with self.assertRaises(nm_module.NmError):
            network.start_hotspot("Debra-Setup-demo1", "wlan0", None)
        self.assertIn(["nmcli", "connection", "delete", "debra-setup"], recorder.calls)

    def test_an_open_access_point_whose_security_reads_empty_is_still_open(self):
        # `none` is what a keyfile with `key-mgmt=none` reports, but a build that
        # materialises no security setting at all prints nothing. Treating that
        # as a mismatch would tear down the only setup network the device has -
        # the failure this whole mechanism exists to prevent.
        network = self.adapter(key_mgmt="")
        raised = network.start_hotspot("Debra-Setup-demo1", "wlan0", None)
        self.assertEqual(raised["key_mgmt"], "")
        # The same empty value must still be a failure when a password was asked
        # for: this acceptance is about the open mode only.
        network = self.adapter(key_mgmt="")
        with self.assertRaises(nm_module.NmError):
            network.start_hotspot("Debra-Setup-demo1", "wlan0", "s3cretvalue")

    def test_wep_is_not_accepted_in_place_of_wpa2(self):
        with self.assertRaises(nm_module.NmError):
            self.adapter(key_mgmt="wep-key").start_hotspot(
                "Debra-Setup-demo1", "wlan0", "s3cretvalue")

    def test_an_access_point_that_never_activated_is_not_success(self):
        # The profile can load and `connection up` can be accepted while the
        # radio never activates on it. A network that is not activated has no
        # address and no page.
        with self.assertRaises(nm_module.NmError) as caught:
            self.adapter(ap_never_activates=True).start_hotspot(
                "Debra-Setup-demo1", "wlan0", None)
        self.assertIn("did not come up", str(caught.exception))
        self.assertEqual(list(self.profiles.iterdir()), [],
                         "a profile that never activated was left behind")

    def test_a_driver_that_refuses_ap_mode_is_a_reported_failure(self):
        with self.assertRaises(nm_module.NmError) as caught:
            self.adapter(ap_up_fails=True).start_hotspot(
                "Debra-Setup-demo1", "wlan0", None)
        self.assertIn("AP mode", str(caught.exception))
        self.assertEqual(list(self.profiles.iterdir()), [])

    def test_a_password_that_cannot_be_used_is_refused_before_anything_is_written(self):
        recorder = Recorder(profile_dir=self.profiles)
        network = nm_module.Nmcli(runner=recorder, profiles_dir=self.profiles)
        with self.assertRaises(nm_module.NmError):
            network.start_hotspot("Debra-Setup-demo1", "wlan0", "short")
        self.assertEqual(recorder.calls, [], "an unusable password reached nmcli")
        self.assertEqual(list(self.profiles.iterdir()), [])

    def test_stopping_the_access_point_removes_its_profile(self):
        network = self.adapter()
        network.start_hotspot("Debra-Setup-demo1", "wlan0", None)
        self.assertTrue(nm_module.hotspot_profile_path(self.profiles).exists())
        network.stop_hotspot()
        self.assertFalse(nm_module.hotspot_profile_path(self.profiles).exists(),
                         "a reload would raise the access point again from this file")


class CountryTests(Temp):
    def test_a_country_already_on_the_device_is_adopted_not_asked_for_again(self):
        onboarder = self.onboarder(FakeNetwork(country="GB"))
        status = onboarder.start_hotspot()
        self.assertEqual(status["country"], "GB")
        self.assertEqual(state_module.read(self.state_path)["country"], "GB")

    def test_with_no_country_set_the_page_still_asks(self):
        status = self.onboarder(FakeNetwork(country=None)).start_hotspot()
        self.assertIsNone(status["country"])


class LockoutTests(Temp):
    def test_the_cap_is_a_cooldown_and_not_a_permanent_lockout(self):
        network = FakeNetwork(behaviour="bad-psk")
        clock = [0.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()
        for _ in range(onboarding.MAX_ATTEMPTS):
            clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
            onboarder.join("HomeWiFi", "wrong password", None)
        data = state_module.read(self.state_path)
        self.assertEqual(data["attempts"], onboarding.MAX_ATTEMPTS)
        # Immediately after the cap, another attempt is refused...
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        before = len(network.calls)
        onboarder.join("HomeWiFi", "wrong password", None)
        self.assertEqual(len(network.calls), before, "the cooldown did not hold")
        # ...but not for ever, because a power cycle cannot clear this counter.
        pinned = state_module.read(self.state_path)
        pinned["last_attempt"] = "2020-01-01T00:00:00Z"
        state_module.write(self.state_path, pinned)
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        onboarder.join("HomeWiFi", "wrong password", None)
        self.assertGreater(len(network.calls), before,
                           "an expired cooldown must let the retry through")
        # The allowance starts again from one. It used to stay at the cap, so
        # one wrong password after the cooldown re-armed the whole lockout.
        self.assertEqual(state_module.read(self.state_path)["attempts"], 1,
                         "the expired window did not start again from one")

    def test_a_successful_join_clears_the_failure_count(self):
        network = FakeNetwork(behaviour="bad-psk")
        clock = [0.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()
        for _ in range(3):
            clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
            onboarder.join("HomeWiFi", "wrong password", None)
        self.assertEqual(state_module.read(self.state_path)["attempts"], 3)
        network.behaviour = "ok"
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        status = onboarder.join("HomeWiFi", "correct horse", None)
        self.assertEqual(status["phase"], "online")
        data = state_module.read(self.state_path)
        self.assertEqual(data["attempts"], 0)
        self.assertIsNone(data["last_attempt"])


class BaselineRootTests(Temp):
    def test_the_baseline_reads_the_configured_root_and_not_the_real_one(self):
        # On a laptop, root="/" would copy that machine's real NetworkManager
        # keyfiles into the archive. A test run must never do that.
        fake = self.dir / "fake-root"
        (fake / "etc").mkdir(parents=True)
        (fake / "etc" / "hostname").write_text("debra-demo1\n", encoding="utf-8")
        onboarder = self.onboarder(root=str(fake))
        onboarder.start_hotspot()
        status = onboarder.join("HomeWiFi", "correct horse", None)
        manifest = json.loads((Path(status["baseline"].replace(".tar.gz", ".json"))
                               ).read_text())
        self.assertIn("etc/hostname", manifest["captured"])
        self.assertTrue(all(not path.startswith("var/") for path in manifest["captured"]))


class BaselineExclusionTests(Temp):
    """A baseline is copied off the device; the setup credential must not be in it."""

    def test_the_setup_password_is_not_captured_even_though_it_lives_under_var(self):
        # var/lib/debra is captured because it is device configuration worth
        # recovering. The setup service's own directory is inside it and holds
        # the setup password, so membership of that parent cannot be the rule.
        fake = self.dir / "fake-root"
        (fake / "var" / "lib" / "debra" / "setup").mkdir(parents=True)
        (fake / "var" / "lib" / "debra" / "setup" / "setup-secret").write_text(
            "s3cretvalue\n", encoding="utf-8")
        (fake / "var" / "lib" / "debra" / "setup" / "setup-security").write_text(
            "wpa\n", encoding="utf-8")
        (fake / "var" / "lib" / "debra" / "keep.me").write_text("x", encoding="utf-8")
        # The access point's own NetworkManager profile holds the same password
        # as `psk=` while it is up, and that directory is captured in full.
        profiles = fake / "etc" / "NetworkManager" / "system-connections"
        profiles.mkdir(parents=True)
        (profiles / "debra-setup.nmconnection").write_text(
            "[wifi-security]\npsk=s3cretvalue\n", encoding="utf-8")
        (profiles / "HomeWiFi.nmconnection").write_text(
            "[wifi]\nssid=HomeWiFi\n", encoding="utf-8")
        onboarder = self.onboarder(root=str(fake), security="wpa")
        onboarder.start_hotspot()
        status = onboarder.join("HomeWiFi", "correct horse", None)
        manifest = json.loads(Path(status["baseline"].replace(".tar.gz", ".json"))
                              .read_text())
        captured = manifest["captured"]
        self.assertNotIn("var/lib/debra/setup/setup-secret", captured)
        self.assertNotIn("var/lib/debra/setup/setup-security", captured)
        self.assertIn("var/lib/debra/keep.me", captured,
                      "the exclusion must not swallow the rest of the directory")
        self.assertNotIn(
            "etc/NetworkManager/system-connections/debra-setup.nmconnection",
            captured, "the access point's profile carried the password into the baseline")
        self.assertIn("etc/NetworkManager/system-connections/HomeWiFi.nmconnection",
                      captured,
                      "the exclusion must not swallow the household network's profile")


class Recorder:
    """A stand-in for `_run` that answers like nmcli and remembers argv.

    It tracks the connection id the adapter generates, because a successful
    join is now defined by NetworkManager naming *that* profile as the active
    connection. A double that answers every query with IP fields is exactly the
    bypass the review found: it made an unknown profile look like success.

    The access point half answers from the profile file the adapter wrote, not
    from what the adapter asked for: a reload makes the profile the directory
    holds the one NetworkManager knows, and `device show` reports that device
    as activated. That is the only way the read-back check can fail when the
    security is wrong. `device wifi hotspot` is modelled at its worst - it
    generates a password when none is given and nobody can read it - so the
    old call cannot pass here by being asked nicely.
    """

    def __init__(self, address="192.0.2.40", gateway="192.0.2.1", up_fails=False,
                 active_profile=None, load_fails=False, modify_fails=False,
                 interface="wlan0", profile_dir=None, key_mgmt=None,
                 hotspot_address="10.42.0.1", ap_up_fails=False,
                 ap_never_activates=False):
        self.calls, self.contents = [], []
        self.address, self.gateway, self.up_fails = address, gateway, up_fails
        self.active_profile = active_profile
        self.load_fails = load_fails
        self.modify_fails = modify_fails
        self.interface = interface
        # The directory the keyfile plugin reads. `nmcli connection load` is not
        # an arbitrary-file import, so a profile handed over from anywhere else
        # is refused here the way a real NetworkManager would refuse it.
        self.profile_dir = profile_dir
        self.loaded_id = None
        self.deleted = []
        self.modified = []
        # None means "report what the profile says", which is what a real
        # NetworkManager does. A string is a device that ignored the profile -
        # WEP, or a security that does not match - which is the only way the
        # read-back can be tested at all.
        self.key_mgmt = key_mgmt
        self.hotspot_address = hotspot_address
        self.hotspot_up = False
        self.ap_up_fails = ap_up_fails
        self.ap_never_activates = ap_never_activates

    def _profile(self):
        """The access point's profile as NetworkManager would now read it."""
        if self.profile_dir is None:
            return None
        path = nm_module.hotspot_profile_path(self.profile_dir)
        try:
            return (path.read_text(encoding="utf-8"),
                    stat.S_IMODE(path.stat().st_mode), str(path))
        except OSError:
            return None

    def _profile_key_mgmt(self):
        profile = self._profile()
        if profile is None:
            return ""
        section = None
        for line in profile[0].splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]
            elif section == "wifi-security" and line.startswith("key-mgmt="):
                return line.partition("=")[2].strip()
        return ""

    def __call__(self, argv, timeout=45):
        self.calls.append(list(argv))
        if argv[1:] == ["-t", "-f", "DEVICE,TYPE,STATE", "device", "status"]:
            return f"{self.interface}:wifi:connected\n"
        if argv[1:3] == ["-g", "802-11-wireless-security.key-mgmt"]:
            # `-g/--get-values`: the value alone.
            value = self.key_mgmt if self.key_mgmt is not None else self._profile_key_mgmt()
            return f"{value}\n"
        if argv[1:4] == ["-t", "-f", "802-11-wireless-security.key-mgmt"]:
            # `-t` keeps the property name in front of the value - which is
            # exactly what the real tool does, and what made a stripped
            # comparison never match. Answering this form faithfully is what
            # lets the tests catch a return to it.
            value = self.key_mgmt if self.key_mgmt is not None else self._profile_key_mgmt()
            return f"802-11-wireless-security.key-mgmt:{value}\n"
        if argv[1:3] == ["-t", "-f"] and argv[4:6] == ["device", "show"]:
            name = self.active_profile
            if name is None:
                name = self.loaded_id if not self.up_fails else None
            if self.hotspot_up:
                name = nm_module.SETUP_CONNECTION
            if argv[3] == "GENERAL.CONNECTION":
                return f"GENERAL.CONNECTION:{name or ''}\n"
            if "GENERAL.STATE" in argv[3]:
                activated = bool(name)
                if name == nm_module.SETUP_CONNECTION:
                    # The setup profile can be the loaded one without the device
                    # having activated on it, which is the failure this models.
                    activated = self.hotspot_up
                state, label = ((100, "connected") if activated
                                else (30, "disconnected"))
                lines = [f"GENERAL.STATE:{state} ({label})",
                         f"GENERAL.CONNECTION:{name or ''}"]
                if self.hotspot_up:
                    lines.append(f"IP4.ADDRESS[1]:{self.hotspot_address}/24")
                return "\n".join(lines) + "\n"
            return (f"IP4.ADDRESS[1]:{self.address}/24\n"
                    f"IP4.GATEWAY:{self.gateway}\n")
        if argv[1:4] == ["device", "wifi", "hotspot"]:
            # The real tool, and why it cannot be used for an open network: with
            # no password it generates one that is never shown to anyone.
            self.hotspot_up = True
            self.key_mgmt = "wpa-psk"
            return ""
        if argv[1:3] == ["connection", "load"]:
            if self.load_fails:
                raise nm_module.NmError("NetworkManager refused the profile")
            path = Path(argv[3])
            if self.profile_dir is not None and path.parent != Path(self.profile_dir):
                raise nm_module.NmError(
                    "Error: Cannot load connection profile: file is not in a profile directory")
            self.contents.append((path.read_text(encoding="utf-8"),
                                  stat.S_IMODE(path.stat().st_mode),
                                  str(path)))
            return ""
        if argv[1:3] == ["connection", "reload"]:
            profile = self._profile()
            if profile is not None:
                self.contents.append(profile)
            return ""
        if argv[1:4] == ["connection", "down", "id"]:
            if argv[4] == nm_module.SETUP_CONNECTION:
                self.hotspot_up = False
            return ""
        if argv[1:4] == ["connection", "up", "id"]:
            self.loaded_id = argv[4]
            if self.up_fails:
                raise nm_module.NmError("The Wi-Fi password was refused by the network")
            if argv[4] == nm_module.SETUP_CONNECTION:
                if self.ap_up_fails:
                    raise nm_module.NmError("AP mode is not supported by this driver")
                # `connection up` can be accepted and the device still not be
                # activated on the profile - the second way this path fails.
                self.hotspot_up = not self.ap_never_activates
            return ""
        if argv[1:4] == ["connection", "delete", "id"]:
            self.deleted.append(argv[4])
            if argv[4] == nm_module.SETUP_CONNECTION:
                self.hotspot_up = False
            return ""
        if argv[1:3] == ["connection", "modify"]:
            if self.modify_fails:
                raise nm_module.NmError("NetworkManager refused the change")
            self.modified.append(" ".join(argv[4:]))
            return ""
        if argv[1:3] == ["radio", "wifi"]:
            return "enabled\n"
        return ""


class AdapterTests(Temp):
    def test_the_wi_fi_password_never_appears_in_a_command_line(self):
        recorder = Recorder()
        nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                 keyfile_dir=self.dir)
        flattened = " ".join(" ".join(call) for call in recorder.calls)
        self.assertNotIn("correct horse", flattened,
                         "the password is visible in argv to any other process")
        self.assertEqual(len(recorder.contents), 1)
        text, mode, path = recorder.contents[0]
        self.assertIn("psk=correct horse", text)
        self.assertEqual(mode, 0o600, "the profile must be owner-only")
        # The profile stays where NetworkManager will read it on the next boot.
        # Deleting it, as the previous version did, meant the device forgot its
        # household network the moment the setup network went away.
        self.assertTrue(Path(path).exists(), "the working profile was deleted")
        self.assertEqual(Path(path).parent, self.dir)
        # It must not be allowed to compete until the join is verified.
        self.assertIn("autoconnect=false", text)
        self.assertIn(["nmcli", "connection", "modify", recorder.loaded_id,
                       "connection.autoconnect", "yes"], recorder.calls)

    @unittest.skipUnless(GLib, "GLib is not installed on this host")
    @unittest.skipUnless(NM_LIBRARY, "libnm is not installed on this host")
    def test_the_ssid_survives_network_managers_own_parser(self):
        # GLib is not the whole story: `ssid` has a second reader on top of it.
        # Writing it as text meant `65;66;` joined a network called `AB` and a
        # name containing a backslash lost it. Ask libnm, which is what the
        # keyfile plugin runs.
        for ssid in ("HomeWiFi", "Caf; #1", " Home ", "back\\slash", "65;66;",
                     "A\\;B", "x;y;z;", "123", "Café"):
            with self.subTest(ssid=ssid):
                directory = self.dir / ("rt-" + str(abs(hash(ssid))))
                directory.mkdir()
                recorder = Recorder()
                nm_module.Nmcli(runner=recorder).connect(
                    ssid, "correct horse", keyfile_dir=directory)
                text, _, _ = recorder.contents[0]
                self.assertEqual(_nm_parse(text)["ssid"], ssid,
                                 "NetworkManager would join a different network")

    @unittest.skipUnless(NM_LIBRARY, "libnm is not installed on this host")
    def test_the_passphrase_survives_network_managers_own_parser(self):
        for psk in ("pass;word#1", " space pass ", "back\\slash1", "correct horse"):
            with self.subTest(psk=psk):
                directory = self.dir / ("psk-" + str(abs(hash(psk))))
                directory.mkdir()
                recorder = Recorder()
                nm_module.Nmcli(runner=recorder).connect("Home", psk, keyfile_dir=directory)
                text, _, _ = recorder.contents[0]
                self.assertEqual(_nm_parse(text)["psk"], psk)

    def test_glib_accepts_the_file_at_all(self):
        # GLib is the first reader. A value GLib refuses is a file NetworkManager
        # never gets to. This is weaker than the libnm test above and says so.
        recorder = Recorder()
        nm_module.Nmcli(runner=recorder).connect("Caf; #1", "pass;word#1",
                                                 keyfile_dir=self.dir)
        text, _, _ = recorder.contents[0]
        GLib.KeyFile().load_from_data(text, len(text.encode("utf-8")),
                                      GLib.KeyFileFlags.NONE)

    def test_a_newline_in_a_password_is_refused_not_escaped(self):
        recorder = Recorder()
        with self.assertRaises(nm_module.NmError):
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "abcdefgh\npsk-flags=1",
                                                     keyfile_dir=self.dir)
        self.assertEqual(recorder.calls, [], "a newline password reached nmcli")

    def test_a_network_name_longer_than_32_octets_is_refused(self):
        recorder = Recorder()
        with self.assertRaises(nm_module.NmError):
            nm_module.Nmcli(runner=recorder).connect("é" * 17, "correct horse",
                                                     keyfile_dir=self.dir)
        self.assertEqual(recorder.calls, [])

    def test_an_address_without_a_default_route_is_not_success(self):
        recorder = Recorder(gateway="")
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                     keyfile_dir=self.dir)
        self.assertIn("default route", str(caught.exception))

    def test_a_failed_activation_does_not_leave_a_competing_profile(self):
        recorder = Recorder(up_fails=True)
        with self.assertRaises(nm_module.NmError):
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                     keyfile_dir=self.dir)
        self.assertEqual(len(recorder.deleted), 1, "the failed profile was kept")
        self.assertEqual(list(self.dir.glob("*.nmconnection")), [],
                         "the failed profile file was kept")

    def test_a_link_local_address_is_not_a_usable_uplink(self):
        # The review's mutation removed this check and every test still passed,
        # because the doubles only ever raised their own exceptions. This one
        # goes through the adapter's own decision.
        for address in ("169.254.7.7", ""):
            with self.subTest(address=address):
                recorder = Recorder(address=address)
                with self.assertRaises(nm_module.NmError) as caught:
                    nm_module.Nmcli(runner=recorder).connect(
                        "HomeWiFi", "correct horse", keyfile_dir=self.dir)
                self.assertIn("no usable address", str(caught.exception))
                self.assertEqual(len(recorder.deleted), 1,
                                 "the unusable profile was kept for the next boot")

    def test_the_profile_is_pinned_to_the_radio_the_page_was_reached_over(self):
        recorder = Recorder()
        nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                 keyfile_dir=self.dir, interface="wlan0")
        text, _, _ = recorder.contents[0]
        self.assertIn("interface-name=wlan0", text)

    def test_a_join_that_comes_up_on_another_radio_is_refused(self):
        # Two Wi-Fi interfaces would otherwise let the household network come up
        # on the one nobody reached the page over.
        recorder = Recorder()
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module.Nmcli(runner=recorder).connect(
                "HomeWiFi", "correct horse", keyfile_dir=self.dir, interface="wlan1")
        self.assertIn("different Wi-Fi interface", str(caught.exception))

    def test_an_unknown_active_profile_is_not_success(self):
        # A blank GENERAL.CONNECTION used to pass because the check only
        # rejected a *known different* name.
        recorder = Recorder(active_profile="HomeWiFi-old")
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                     keyfile_dir=self.dir)
        self.assertIn("different saved network", str(caught.exception))

    def test_a_bad_password_length_is_refused_before_anything_runs(self):
        recorder = Recorder()
        with self.assertRaises(nm_module.NmError):
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "short",
                                                     keyfile_dir=self.dir)
        self.assertEqual(recorder.calls, [])


class ProfileStorageTests(Temp):
    """Where the household profile lives, and that it is still there later.

    `nmcli connection load` reads a profile from the keyfile plugin's own
    directories; it does not import an arbitrary file. The r2 acceptance review
    reproduced the old behaviour: the profile went to a process temporary
    directory, NetworkManager refused it, and the file was deleted afterwards
    anyway. A join that only works until the next reboot is not a join.
    """

    def setUp(self):
        super().setUp()
        self.profiles = self.dir / "system-connections"
        self.profiles.mkdir()
        patcher = patch.object(nm_module, "PROFILES_DIR", str(self.profiles))
        patcher.start()
        self.addCleanup(patcher.stop)

    def recorder(self, **kwargs):
        kwargs.setdefault("profile_dir", self.profiles)
        return Recorder(**kwargs)

    def test_the_profile_is_written_where_network_manager_reads_it(self):
        recorder = self.recorder()
        nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        text, mode, path = recorder.contents[0]
        self.assertEqual(Path(path).parent, self.profiles,
                         "the profile was staged somewhere NetworkManager does not read")
        self.assertTrue(path.endswith(".nmconnection"),
                        "the profile has no name the keyfile plugin will read")
        self.assertEqual(mode, 0o600, "the profile must be owner-only")
        self.assertTrue(Path(path).exists(),
                        "the working profile did not survive the join")
        self.assertIn("autoconnect=false", text,
                      "the trial profile may compete before the join is verified")
        self.assertEqual(recorder.modified, ["connection.autoconnect yes"],
                         "the profile was never promoted to autoconnect")

    def test_only_the_finished_profile_is_left_in_the_directory(self):
        recorder = self.recorder()
        nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        names = sorted(item.name for item in self.profiles.iterdir())
        self.assertEqual(len(names), 1, f"a staging file was left behind: {names}")
        self.assertTrue(names[0].endswith(".nmconnection"))

    def test_network_manager_never_sees_a_half_written_profile(self):
        # The keyfile plugin watches this directory. A file created under its
        # final name is parsed while it is still empty or half written, and a
        # crash leaves something that looks like a profile but is not one.
        seen = []
        real_fsync = os.fsync

        def watch(handle):
            seen.append(sorted(item.name for item in self.profiles.iterdir()))
            return real_fsync(handle)

        recorder = self.recorder()
        with patch.object(nm_module.os, "fsync", side_effect=watch):
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        self.assertTrue(seen, "the profile was never made durable")
        self.assertEqual([name for name in seen[0] if name.endswith(".nmconnection")], [],
                         f"a partial profile was visible while it was being written: {seen[0]}")

    def test_a_profile_that_does_not_work_leaves_nothing_behind(self):
        recorder = self.recorder(up_fails=True)
        with self.assertRaises(nm_module.NmError):
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        self.assertEqual(list(self.profiles.iterdir()), [],
                         "a profile that never worked is still in the directory")

    def test_another_network_already_saved_is_not_touched(self):
        existing = self.profiles / "home.nmconnection"
        existing.write_text("[connection]\nid=Home\n", encoding="utf-8")
        recorder = self.recorder(up_fails=True)
        with self.assertRaises(nm_module.NmError):
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        self.assertEqual(existing.read_text(encoding="utf-8"), "[connection]\nid=Home\n")
        self.assertEqual([item.name for item in self.profiles.iterdir()],
                         ["home.nmconnection"])

    def test_a_profile_that_cannot_be_saved_for_the_next_boot_is_a_failed_join(self):
        # Autoconnect off works until the reboot and then strands the device
        # with no network at all, so it is not a success with a warning.
        recorder = self.recorder(modify_fails=True)
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        self.assertIn("could not be saved for the next boot", str(caught.exception))
        self.assertEqual(len(recorder.deleted), 1, "the unsaved profile was kept")
        self.assertEqual(list(self.profiles.iterdir()), [],
                         "a profile that will not autoconnect was left behind")

    def test_the_profile_is_pinned_to_the_radio_that_was_used(self):
        recorder = self.recorder()
        nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                 interface="wlan0")
        text, _, _ = recorder.contents[0]
        self.assertIn("interface-name=wlan0", text)

    def test_a_join_that_comes_up_on_another_radio_is_not_success(self):
        recorder = self.recorder(interface="wlan1")
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse",
                                                     interface="wlan0")
        self.assertIn("different Wi-Fi interface", str(caught.exception))
        self.assertEqual(list(self.profiles.iterdir()), [],
                         "the profile that came up on the wrong radio was kept")

    def test_a_directory_that_cannot_be_written_is_a_sentence_not_a_traceback(self):
        recorder = self.recorder()
        with patch.object(nm_module.tempfile, "mkstemp",
                          side_effect=PermissionError(13, "Permission denied")):
            with self.assertRaises(nm_module.NmError) as caught:
                nm_module.Nmcli(runner=recorder).connect("HomeWiFi", "correct horse")
        self.assertEqual(str(caught.exception),
                         "The Wi-Fi profile could not be saved on this device")
        self.assertEqual(recorder.calls, [], "a profile was loaded that was never written")


class MissingToolTests(unittest.TestCase):
    def test_the_error_names_the_tool_that_is_missing(self):
        # `iw` and `raspi-config` go through the same runner. Telling someone
        # their NetworkManager is absent when it is `raspi-config` that is
        # absent is a false statement about their device, shown on the page.
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module._run(["/nonexistent/debra-test-tool", "--version"])
        self.assertIn("debra-test-tool", str(caught.exception))
        self.assertNotIn("nmcli", str(caught.exception))


class DeviceAddressTests(Temp):
    def test_the_access_point_address_is_read_from_the_device(self):
        recorder = Recorder()
        self.assertEqual(nm_module.Nmcli(runner=recorder).device_address("wlan0"),
                         "192.0.2.40")

    def test_a_device_with_no_address_is_none_rather_than_a_guess(self):
        def runner(argv, timeout=45):
            return ""
        self.assertIsNone(nm_module.Nmcli(runner=runner).device_address("wlan0"))
        self.assertIsNone(nm_module.Nmcli(runner=runner).device_address(None))


class HostnameTests(Temp):
    def test_a_valid_name_is_applied_not_only_recorded(self):
        network = FakeNetwork()
        self.onboarder(network).ensure_identity()
        self.assertIn(("set_hostname", "debra-demo1"), network.calls)

    def test_a_name_that_cannot_resolve_is_refused(self):
        recorder = Recorder()
        adapter = nm_module.Nmcli(runner=recorder)
        for bad in ("", "has space", "two.dots", "-leading", "x" * 64):
            with self.subTest(name=bad):
                with self.assertRaises(nm_module.NmError):
                    adapter.set_hostname(bad)
        self.assertEqual(recorder.calls, [], "an invalid name reached hostnamectl")
        adapter.set_hostname("debra-3c6b3f")
        self.assertEqual(recorder.calls, [["hostnamectl", "set-hostname", "debra-3c6b3f"]])

    def test_a_missing_hostnamectl_is_reported_without_losing_the_name(self):
        class Broken(FakeNetwork):
            def set_hostname(self, hostname):
                raise nm_module.NmError("hostnamectl is not installed")
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            status = self.onboarder(Broken()).start_hotspot()
        self.assertEqual(status["hostname"], "debra-demo1")


class AdmissionTests(Temp):
    """One attempt in flight, enforced before the page is answered."""

    def test_two_requests_cannot_both_be_admitted(self):
        onboarder = self.onboarder()
        onboarder.start_hotspot()
        results = []
        barrier = threading.Barrier(2)

        def attempt():
            barrier.wait()
            results.append(onboarder.admit("HomeWiFi")[0])

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(results), [False, True],
                         "two requests were admitted for one device")

    def test_a_reserved_worker_abandons_if_the_state_moved_on(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        self.assertTrue(onboarder.admit("First")[0])
        # A second network is reserved by someone else in the meantime.
        data = state_module.read(self.state_path)
        data["ssid"] = "Second"
        state_module.write(self.state_path, data)
        before = len(network.calls)
        status = onboarder.join_reserved("First", "correct horse")
        self.assertEqual(len(network.calls), before,
                         "the abandoned worker touched the network")
        self.assertEqual(status["phase"], "connecting")

    def test_a_second_admission_is_refused_while_one_is_in_flight(self):
        onboarder = self.onboarder()
        onboarder.start_hotspot()
        self.assertTrue(onboarder.admit("HomeWiFi")[0])
        self.assertEqual(onboarder.admit("HomeWiFi"), (False, "busy"))


class BaselineRetryTests(Temp):
    def test_an_online_boot_still_takes_the_missing_baseline(self):
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network)
        data = state_module.blank("debra-demo1")
        data.update(phase="online", ssid="HomeWiFi", address="192.0.2.40")
        state_module.write(self.state_path, data)
        status = onboarder.resume()
        self.assertEqual(status["phase"], "online")
        self.assertIsNotNone(status["baseline"],
                             "a device that was already online never took its baseline")

    def test_a_pointer_to_a_missing_baseline_does_not_suppress_a_capture(self):
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network)
        data = state_module.blank("debra-demo1")
        data.update(phase="online", ssid="HomeWiFi", address="192.0.2.40",
                    baseline=str(self.baseline_dir / "baseline-gone.tar.gz"))
        state_module.write(self.state_path, data)
        status = onboarder.resume()
        self.assertIsNotNone(status["baseline"],
                             "a pointer to a deleted archive suppressed the capture")
        self.assertTrue(Path(status["baseline"]).is_file())

    def test_a_capture_failure_is_recorded_and_shown_not_swallowed(self):
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network)
        data = state_module.blank("debra-demo1")
        data.update(phase="online", ssid="HomeWiFi", address="192.0.2.40")
        state_module.write(self.state_path, data)
        # A real ENOSPC carries the path it failed on. The page must say what
        # happened without publishing the device's layout.
        failure = OSError(28, "No space left on device",
                          "/var/lib/debra/setup/baseline/.baseline-1.tar.gz.part")
        with patch.object(baseline_module, "capture", side_effect=failure):
            with self.assertLogs(onboarding.LOGGER, level="WARNING"):
                status = onboarder.resume()
        self.assertIsNone(status["baseline"])
        self.assertEqual(status["baseline_error"], "The device is out of disk space")
        self.assertNotIn("/var/lib/debra", status["baseline_error"])
        # The next boot tries again rather than believing it is done.
        status = onboarder.resume()
        self.assertIsNotNone(status["baseline"])
        self.assertIsNone(status["baseline_error"])


class ErrorBoundaryTests(unittest.TestCase):
    """Raw NetworkManager text never reaches the page or the state."""

    def test_a_passphrase_in_nmcli_output_is_not_reported_back(self):
        class Runner:
            def __call__(self, argv, timeout=45):
                if argv[1:3] == ["connection", "load"]:
                    return ""
                raise nm_module.NmError(
                    nm_module.public_failure(
                        "Error: 802-11-wireless-security.psk: 'SYNTHETIC-SECRET-123' is wrong", 4))

        with tempfile.TemporaryDirectory(prefix="nm-", dir="/tmp/opencode") as directory:
            with self.assertRaises(nm_module.NmError) as caught:
                nm_module.Nmcli(runner=Runner()).connect("HomeWiFi", "SYNTHETIC-SECRET-123",
                                                         keyfile_dir=directory)
        self.assertNotIn("SYNTHETIC-SECRET-123", str(caught.exception))

    def test_an_unknown_failure_is_bounded_and_carries_no_external_text(self):
        message = nm_module.public_failure("Error: something odd with 'a secret'", 10)
        self.assertNotIn("secret", message)
        self.assertIn("failure 10", message)

    def test_the_known_failures_become_sentences_a_person_can_act_on(self):
        self.assertEqual(nm_module.public_failure("Secrets were required, but not provided.", 4),
                         "The Wi-Fi password was refused by the network")
        self.assertEqual(nm_module.public_failure("Error: No network with SSID 'X' found.", 10),
                         "That network was not found")

    def test_multicast_and_broadcast_are_not_device_addresses(self):
        for address in ("224.0.0.1", "255.255.255.255", "0.0.0.0", "169.254.1.1", "127.0.0.1"):
            self.assertFalse(nm_module.routable(address), address)
        for address in ("192.168.1.40", "10.42.0.1"):
            self.assertTrue(nm_module.routable(address), address)


class FailedWithoutHotspotTests(Temp):
    def test_a_join_on_a_failed_device_with_no_access_point_is_refused_not_crashed(self):
        onboarder = self.onboarder()
        data = state_module.blank("debra-demo1")
        data.update(phase="failed", last_error="No Wi-Fi interface was found", hotspot=None)
        state_module.write(self.state_path, data)
        server = onboarding.Portal(("127.0.0.1", 0), onboarder, onboarding.ASSETS / "setup.html")
        host = "127.0.0.1:%d" % server.server_port
        server.host = host
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = urllib.request.Request(
                "http://" + host + "/api/join",
                data=json.dumps({"ssid": "HomeWiFi", "psk": "correct horse"}).encode(),
                method="POST")
            request.add_header("Host", host)
            request.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    code = response.status
            except urllib.error.HTTPError as exc:
                code = exc.code
        finally:
            server.shutdown()
            thread.join()
        # No access point means nothing to hand over to; the page must get a
        # refusal, not a dropped connection from a TypeError in the handler.
        self.assertEqual(code, 409)


class BaselineAtomicityTests(Temp):
    def test_a_full_disk_leaves_no_archive_that_looks_complete(self):
        root = self.dir / "fake-root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-demo1\n")
        real_open = os.open

        def failing_open(path, flags, mode=0o777):
            if str(path).endswith(".part"):
                raise OSError(28, "No space left on device")
            return real_open(path, flags, mode)

        with patch.object(baseline_module.os, "open", side_effect=failing_open):
            with self.assertRaises(OSError):
                baseline_module.capture(self.baseline_dir, root=root, stamp="T1")
        names = sorted(path.name for path in self.baseline_dir.iterdir())
        self.assertEqual(names, [], f"a failed capture left {names}")
        self.assertIsNone(baseline_module.latest(self.baseline_dir))

    def test_a_complete_capture_is_readable_and_owner_only(self):
        root = self.dir / "fake-root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-demo1\n")
        manifest = baseline_module.capture(self.baseline_dir, root=root, stamp="T2")
        self.assertEqual(manifest["captured"], ["etc/hostname"])
        archive = self.baseline_dir / manifest["archive"]
        self.assertEqual(stat.S_IMODE(archive.stat().st_mode), 0o600)
        self.assertEqual(baseline_module.latest(self.baseline_dir)["archive"], manifest["archive"])


class ActiveProfileTests(Temp):
    class Runner:
        """Answers nmcli like a device whose saved profile won the race."""

        def __init__(self, active):
            self.active, self.calls = active, []

        def __call__(self, argv, timeout=45):
            self.calls.append(list(argv))
            if argv[1:3] == ["connection", "load"]:
                return ""
            if argv[1:4] == ["connection", "up", "id"]:
                return ""
            if argv[1:] == ["-t", "-f", "DEVICE,TYPE,STATE", "device", "status"]:
                return "wlan0:wifi:connected\n"
            if argv[1:3] == ["-t", "-f"] and argv[4:6] == ["device", "show"]:
                if "GENERAL.CONNECTION" in argv[3]:
                    return f"GENERAL.CONNECTION:{self.active}\n"
                return "IP4.ADDRESS[1]:192.0.2.40/24\nIP4.GATEWAY:192.0.2.1\n"
            return ""

    def test_a_different_active_profile_is_not_success(self):
        runner = self.Runner("HomeWiFi-old")
        with self.assertRaises(nm_module.NmError) as caught:
            nm_module.Nmcli(runner=runner).connect("HomeWiFi", "correct horse",
                                                   keyfile_dir=self.dir)
        self.assertIn("different saved network", str(caught.exception))

    def test_the_profile_that_was_just_loaded_is_success(self):
        runner = self.Runner("placeholder")
        # The loaded profile id is generated per call, so read it from the argv.
        def answer(argv, timeout=45):
            if argv[1:3] == ["connection", "load"]:
                return ""
            if argv[1:4] == ["connection", "up", "id"]:
                runner.active = argv[4]
                return ""
            return runner(argv, timeout)
        result = nm_module.Nmcli(runner=answer).connect("HomeWiFi", "correct horse",
                                                        keyfile_dir=self.dir)
        self.assertEqual(result["address"], "192.0.2.40")


class ScanTests(Temp):
    """Nearby networks are offered, never required."""

    def test_the_scan_result_reaches_the_page(self):
        status = self.onboarder(FakeNetwork()).start_hotspot()
        self.assertEqual([item["ssid"] for item in status["networks"]],
                         ["HomeWiFi", "Neighbour", "Cafe"])
        self.assertEqual(status["networks"][0]["security"], "WPA2")

    def test_a_failed_scan_is_an_empty_list_not_a_failed_hotspot(self):
        network = FakeNetwork()
        network.behaviour = "scan-fails"
        status = self.onboarder(network).start_hotspot()
        self.assertEqual(status["phase"], "hotspot")
        self.assertEqual(status["networks"], [])

    def test_an_adapter_with_no_scan_at_all_still_raises_the_access_point(self):
        class NoScan(FakeNetwork):
            scan = None  # not a callable: the adapter does not have one
        status = self.onboarder(NoScan()).start_hotspot()
        self.assertEqual(status["phase"], "hotspot")
        self.assertEqual(status["networks"], [])

    def test_no_scan_happens_when_the_access_point_is_already_up(self):
        # Scanning with the AP up can drop the person's phone off it, so a
        # re-raise must not scan.
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        before = [call for call in network.calls if call[0] == "scan"]
        onboarder.start_hotspot()
        after = [call for call in network.calls if call[0] == "scan"]
        self.assertEqual(len(after), len(before), "a re-raise scanned with the AP up")


class ScanParsingTests(unittest.TestCase):
    class Runner:
        def __init__(self, output):
            self.output, self.calls = output, []

        def __call__(self, argv, timeout=45):
            self.calls.append(list(argv))
            return self.output

    def test_an_escaped_colon_in_a_name_is_one_field(self):
        runner = self.Runner("Home\\:WiFi:82:WPA2\n")
        found = nm_module.Nmcli(runner=runner).scan("wlan0")
        self.assertEqual(found, [{"ssid": "Home:WiFi", "signal": 82, "security": "WPA2"}])

    def test_hidden_networks_are_skipped_and_duplicates_keep_the_strongest(self):
        runner = self.Runner("Home:40:WPA2\n:99:WPA2\nHome:88:WPA3\n")
        found = nm_module.Nmcli(runner=runner).scan("wlan0")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["signal"], 88)
        self.assertEqual(found[0]["security"], "WPA3")

    def test_strongest_first_and_bounded(self):
        lines = "".join(f"Net{n}:{n}:WPA2\n" for n in range(30))
        found = nm_module.Nmcli(runner=self.Runner(lines)).scan("wlan0", limit=5)
        self.assertEqual(len(found), 5)
        self.assertEqual([item["signal"] for item in found], [29, 28, 27, 26, 25])

    def test_a_scan_asks_for_a_rescan_on_the_named_interface(self):
        runner = self.Runner("")
        nm_module.Nmcli(runner=runner).scan("wlan0")
        self.assertIn("--rescan", runner.calls[0])
        self.assertEqual(runner.calls[0][-2:], ["ifname", "wlan0"])

    def test_a_failing_scan_returns_nothing(self):
        class Broken:
            def __call__(self, argv, timeout=45):
                raise nm_module.NmError("nmcli did not answer in time")
        self.assertEqual(nm_module.Nmcli(runner=Broken()).scan("wlan0"), [])
        self.assertEqual(nm_module.Nmcli(runner=Broken()).scan(None), [])


class FailurePathScanTests(Temp):
    def test_a_failed_join_does_not_rescan_before_raising_the_access_point(self):
        # The AP is about to come back. A scan can take tens of seconds, and the
        # person would be disconnected with no page for that long.
        network = FakeNetwork(behaviour="bad-psk")
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        scans_before = len([call for call in network.calls if call[0] == "scan"])
        onboarder.join("HomeWiFi", "wrong password")
        scans_after = len([call for call in network.calls if call[0] == "scan"])
        self.assertEqual(scans_after, scans_before,
                         "a failed join scanned before restoring the access point")
        # The first boot's list is still offered.
        self.assertEqual(len(onboarder.status()["networks"]), 3)


class ReservationTests(Temp):
    """One reservation, identified by a token, not by a network name."""

    def test_a_retry_of_the_same_network_supersedes_the_old_worker(self):
        # The same SSID can be tried twice with a corrected password, so the
        # network name cannot identify which attempt a worker belongs to. The
        # token can, and the old worker must lose.
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        accepted, old_token = onboarder.admit("Home")
        self.assertTrue(accepted)
        onboarder.release(old_token)
        onboarder._last_submit = 0.0
        accepted, new_token = onboarder.admit("Home")
        self.assertTrue(accepted)
        self.assertNotEqual(old_token, new_token,
                            "two attempts in one second share a token")
        before = len(network.calls)
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            status = onboarder.join_reserved("Home", "old password", token=old_token)
        self.assertEqual(len(network.calls), before,
                         "the superseded worker touched the network")
        self.assertEqual(status["phase"], "connecting")
        # The current reservation still works.
        status = onboarder.join_reserved("Home", "correct horse", token=new_token)
        self.assertEqual(status["phase"], "online")

    def test_a_reply_that_cannot_be_delivered_releases_the_reservation(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        accepted, token = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)
        self.assertEqual(state_module.read(self.state_path)["attempts"], 1)
        onboarder.release(token)
        data = state_module.read(self.state_path)
        self.assertEqual(data["phase"], "hotspot")
        self.assertIsNone(data["attempt_token"])
        self.assertEqual(data["attempts"], 0, "a released attempt still counted")
        onboarder._last_submit = 0.0
        self.assertTrue(onboarder.admit("HomeWiFi")[0],
                        "the device stayed busy after a lost reply")

    def test_releasing_a_superseded_reservation_changes_nothing(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        _, first = onboarder.admit("Home")
        onboarder.release(first)
        onboarder._last_submit = 0.0
        _, second = onboarder.admit("Home")
        onboarder.release(first)
        self.assertEqual(state_module.read(self.state_path)["attempt_token"], second,
                         "a stale release cancelled the current attempt")


class CountryOrderingTests(Temp):
    """The country is a radio change, so it happens after the page is answered."""

    def test_admitting_never_touches_the_radio(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        before = list(network.calls)
        accepted, _ = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)
        self.assertEqual(network.calls, before,
                         "the radio was touched before the reply was written")
        self.assertIsNone(state_module.read(self.state_path)["country"])

    def test_the_country_is_set_after_the_access_point_is_down(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        _, token = onboarder.admit("HomeWiFi")
        network.calls.clear()
        status = onboarder.join_reserved("HomeWiFi", "correct horse", "GB", token)
        self.assertEqual(status["phase"], "online")
        phases = network.phases()
        self.assertLess(phases.index("stop_hotspot"), phases.index("set_country"),
                        "the country was set while the setup network was still up")
        self.assertLess(phases.index("set_country"), phases.index("connect"))
        self.assertEqual(state_module.read(self.state_path)["country"], "GB")

    def test_a_country_that_cannot_be_set_brings_the_setup_network_back(self):
        class NoCountry(FakeNetwork):
            def set_country(self, code):
                self.calls.append(("set_country", code))
                raise nm_module.NmError("The Wi-Fi radio is switched off")
        network = NoCountry()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        _, token = onboarder.admit("HomeWiFi")
        status = onboarder.join_reserved("HomeWiFi", "correct horse", "GB", token)
        self.assertEqual(status["phase"], "failed")
        self.assertEqual(status["last_error"], "The Wi-Fi radio is switched off")
        self.assertNotIn("connect", network.phases())


class RunnerBoundaryTests(unittest.TestCase):
    """`_run` itself, not a double of it: what actually leaves the boundary."""

    class Result:
        def __init__(self, returncode, stdout="", stderr=""):
            self.returncode, self.stdout, self.stderr = returncode, stdout, stderr

    def test_raw_stderr_never_leaves_the_runner(self):
        result = self.Result(4, stderr="Error: psk: 'SYNTHETIC-SECRET-123' is wrong")
        with patch.object(nm_module.subprocess, "run", return_value=result):
            with self.assertRaises(nm_module.NmError) as caught:
                nm_module._run(["nmcli", "connection", "up", "id", "x"])
        self.assertNotIn("SYNTHETIC-SECRET-123", str(caught.exception))
        self.assertEqual(str(caught.exception), "NetworkManager reported failure 4")

    def test_a_missing_binary_names_the_tool_and_no_path(self):
        failure = FileNotFoundError(2, "No such file or directory", "/usr/bin/nmcli")
        with patch.object(nm_module.subprocess, "run", side_effect=failure):
            with self.assertRaises(nm_module.NmError) as caught:
                nm_module._run(["nmcli", "radio", "wifi"])
        self.assertEqual(str(caught.exception), "nmcli is not installed")
        self.assertNotIn("/usr/bin", str(caught.exception))

    def test_a_permission_failure_names_no_path(self):
        failure = PermissionError(
            13, "Permission denied",
            "/etc/NetworkManager/system-connections/home.nmconnection")
        with patch.object(nm_module.subprocess, "run", side_effect=failure):
            with self.assertRaises(nm_module.NmError) as caught:
                nm_module._run(["nmcli", "radio", "wifi"])
        self.assertEqual(str(caught.exception), "nmcli could not be run")
        self.assertNotIn("system-connections", str(caught.exception))

    def test_a_timeout_carries_no_command_line(self):
        with patch.object(nm_module.subprocess, "run",
                          side_effect=nm_module.subprocess.TimeoutExpired(["nmcli", "x"], 45)):
            with self.assertRaises(nm_module.NmError) as caught:
                nm_module._run(["nmcli", "x"])
        self.assertEqual(str(caught.exception), "nmcli did not answer in time")
        self.assertIsNone(caught.exception.__cause__, "a traceback carries the argv")


class BaselinePublishTests(Temp):
    """A baseline is never overwritten, never archives itself, never lies."""

    def root_with(self, name="hostname", text="debra-demo1\n"):
        root = self.dir / "publish-root"
        (root / "etc").mkdir(parents=True, exist_ok=True)
        (root / "etc" / name).write_text(text)
        return root

    def test_two_captures_in_the_same_second_do_not_overwrite_each_other(self):
        root = self.root_with()
        first = baseline_module.capture(self.baseline_dir, root=root, stamp="SAME")
        second = baseline_module.capture(self.baseline_dir, root=root, stamp="SAME")
        self.assertNotEqual(first["archive"], second["archive"])
        for manifest in (first, second):
            self.assertTrue((self.baseline_dir / manifest["archive"]).is_file())
        # The newest one is the one reported, and its hash still matches.
        self.assertEqual(baseline_module.latest(self.baseline_dir)["archive"],
                         second["archive"])

    def test_a_baseline_never_archives_its_own_directory(self):
        # The capture reads var/lib/debra, which is where the baselines live. A
        # capture that included itself would grow on every retry until the size
        # cap failed for ever.
        root = self.dir / "self-root"
        (root / "var" / "lib" / "debra").mkdir(parents=True)
        (root / "var" / "lib" / "debra" / "note.txt").write_text("hello\n")
        destination = root / "var" / "lib" / "debra" / "baseline"
        first = baseline_module.capture(destination, root=root, stamp="A")
        second = baseline_module.capture(destination, root=root, stamp="B")
        self.assertNotIn("var/lib/debra/baseline", " ".join(first["captured"]))
        self.assertIn("var/lib/debra/note.txt", first["captured"])
        self.assertEqual(first["captured"], second["captured"],
                         "the second capture archived the first baseline")

    def test_latest_ignores_a_manifest_whose_archive_is_damaged(self):
        root = self.root_with()
        manifest = baseline_module.capture(self.baseline_dir, root=root, stamp="C1")
        archive = self.baseline_dir / manifest["archive"]
        archive.write_bytes(b"not the archive the manifest describes")
        self.assertIsNone(baseline_module.latest(self.baseline_dir),
                          "a damaged archive was reported as the known-good point")

    def test_latest_ignores_a_manifest_whose_archive_is_gone(self):
        root = self.root_with()
        manifest = baseline_module.capture(self.baseline_dir, root=root, stamp="C2")
        (self.baseline_dir / manifest["archive"]).unlink()
        self.assertIsNone(baseline_module.latest(self.baseline_dir))

    def test_a_newer_damaged_baseline_falls_back_to_the_older_whole_one(self):
        root = self.root_with()
        good = baseline_module.capture(self.baseline_dir, root=root, stamp="D1")
        damaged = baseline_module.capture(self.baseline_dir, root=root, stamp="D2")
        (self.baseline_dir / damaged["archive"]).write_bytes(b"truncated")
        self.assertEqual(baseline_module.latest(self.baseline_dir)["archive"],
                         good["archive"])

    def test_a_manifest_that_cannot_be_published_removes_its_archive(self):
        root = self.root_with()
        real_link = os.link
        calls = {"n": 0}

        def failing_link(src, dst):
            # The archive is published first; the manifest is the second link.
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError(28, "No space left on device")
            return real_link(src, dst)

        with patch.object(baseline_module.os, "link", side_effect=failing_link):
            with self.assertRaises(OSError):
                baseline_module.capture(self.baseline_dir, root=root, stamp="E1")
        names = sorted(path.name for path in self.baseline_dir.iterdir())
        self.assertEqual(names, [], f"an archive with no manifest was left: {names}")


class CaptivePortalTests(Temp):
    """A phone should offer to open the page instead of being told to type it."""

    def setUp(self):
        super().setUp()
        self.network = FakeNetwork()
        self.onboarder = self.onboarder(self.network)
        self.onboarder.start_hotspot()
        self.server = onboarding.Portal(("127.0.0.1", 0), self.onboarder,
                                        onboarding.ASSETS / "setup.html")
        self.host = "127.0.0.1:%d" % self.server.server_port
        self.server.host = self.host
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        super().tearDown()

    def probe(self, path, host=None, method="GET"):
        request = urllib.request.Request("http://" + self.host + path, method=method)
        request.add_header("Host", host or self.host)
        opener = urllib.request.build_opener(NoRedirect)
        try:
            with opener.open(request, timeout=10) as response:
                return response.status, response.headers.get("Location"), response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers.get("Location"), exc.read()

    def test_every_known_probe_redirects_to_the_page(self):
        for path in sorted(onboarding.CAPTIVE_PROBES):
            with self.subTest(path=path):
                code, location, _ = self.probe(path)
                self.assertEqual(code, 302)
                self.assertEqual(location, f"http://{self.host}/")

    def test_a_probe_with_the_operating_systems_own_host_still_redirects(self):
        # The OS asks for these paths with its own name, so the same-origin
        # check must not apply. It is the page that must stay same-origin.
        code, location, _ = self.probe("/generate_204",
                                       host="connectivitycheck.gstatic.com")
        self.assertEqual(code, 302)
        self.assertEqual(location, f"http://{self.host}/",
                         "the redirect was built from the attacker-controlled Host")

    def test_a_head_probe_gets_the_redirect_and_no_body(self):
        code, location, body = self.probe("/hotspot-detect.html", method="HEAD")
        self.assertEqual(code, 302)
        self.assertEqual(location, f"http://{self.host}/")
        self.assertEqual(body, b"")

    def test_an_unknown_path_is_still_refused(self):
        # Not a probe, so it is not redirected: the redirect is only for the
        # handful of paths an operating system actually asks for.
        code, location, _ = self.probe("/admin", host="connectivitycheck.gstatic.com")
        self.assertEqual((code, location), (404, None))
        code, location, _ = self.probe("/admin")
        self.assertEqual((code, location), (404, None))

    def test_the_page_itself_is_still_same_origin_only(self):
        code, _, _ = self.probe("/", host="evil.example")
        self.assertEqual(code, 403)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Ask for the response itself, not the page it points at."""

    def redirect_request(self, *args, **kwargs):
        return None


class BootRepairTests(Temp):
    """What a real boot does, not what a helper does when called twice."""

    def test_a_boot_retries_a_device_name_that_was_never_applied(self):
        # The name is saved before it is applied. The first boot fails to apply
        # it; the second must try again, because the page advertises that name.
        network = FakeNetwork()
        network.fail_hostname = True
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            self.onboarder(network).resume()
        self.assertEqual(state_module.read(self.state_path)["hostname"], "debra-demo1")
        self.assertIsNone(getattr(network, "hostname_applied", None))
        network.fail_hostname = False
        # A second boot is a new Onboarder over the same state.
        self.onboarder(network).resume()
        applied = [call for call in network.calls if call[0] == "set_hostname"]
        self.assertEqual(len(applied), 2, "the second boot did not retry the name")
        self.assertEqual(network.hostname_applied, "debra-demo1")

    def test_a_boot_that_is_already_online_also_applies_the_name(self):
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        self.onboarder(network).resume()
        self.assertEqual(network.hostname_applied, "debra-demo1",
                         "an online boot skipped applying the device name")
        self.assertEqual(state_module.read(self.state_path)["phase"], "online")


class DamagedBaselineTests(Temp):
    """A saved pointer that does not verify is not a recovery point."""

    def root_with(self):
        root = self.dir / "capture-root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-demo1\n")
        return root

    def capture_with(self, root):
        return baseline_module.capture(self.baseline_dir, root=root, stamp="R1")

    def test_a_damaged_archive_does_not_suppress_the_next_capture(self):
        root = self.root_with()
        manifest = self.capture_with(root)
        archive = self.baseline_dir / manifest["archive"]
        archive.write_bytes(b"")
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network, root=str(root))
        data = state_module.blank("debra-demo1")
        data.update(phase="online", ssid="Home", address="192.0.2.5",
                    baseline=str(archive))
        state_module.write(self.state_path, data)
        status = onboarder.resume()
        self.assertIsNotNone(status["baseline"], "an empty archive was believed")
        self.assertNotEqual(status["baseline"], str(archive))
        self.assertTrue(baseline_module.verified(self.baseline_dir, status["baseline"]))
        self.assertIsNone(status["baseline_error"])

    def test_the_damage_is_reported_while_it_is_still_the_record(self):
        root = self.root_with()
        manifest = self.capture_with(root)
        (self.baseline_dir / manifest["archive"]).write_bytes(b"truncated")
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network, root=str(root))
        data = state_module.blank("debra-demo1")
        data.update(phase="online", address="192.0.2.5",
                    baseline=str(self.baseline_dir / manifest["archive"]))
        state_module.write(self.state_path, data)
        with self.assertLogs(onboarding.LOGGER, level="WARNING") as logs:
            status = onboarder.resume()
        self.assertIn("does not verify", "\n".join(logs.output))
        self.assertIsNotNone(status["baseline"], "no replacement was captured")

    def test_a_whole_baseline_with_no_recorded_pointer_is_adopted(self):
        # A pointer write can fail on a full disk while the archive itself was
        # written. Capturing another one is exactly what that disk cannot afford.
        root = self.root_with()
        existing = self.capture_with(root)
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network, root=str(root))
        data = state_module.blank("debra-demo1")
        data.update(phase="online", address="192.0.2.5")
        state_module.write(self.state_path, data)
        with self.assertLogs(onboarding.LOGGER, level="WARNING") as logs:
            status = onboarder.resume()
        self.assertIn("Adopted", "\n".join(logs.output))
        self.assertEqual(status["baseline"],
                         str(self.baseline_dir / existing["archive"]))
        self.assertEqual(len(list(self.baseline_dir.glob("baseline-*.tar.gz"))), 1,
                         "a second baseline was captured on top of a whole one")


class CaptureIntegrityTests(Temp):
    """A member's size comes from the bytes that were read, not a second stat."""

    def root_with(self, size=2048):
        root = self.dir / "race-root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_bytes(b"A" * size)
        return root

    def test_the_header_is_not_built_from_a_second_stat(self):
        # `gettarinfo()` stats the path again. When a writer truncated the file
        # between the read and that stat, the archive held the old buffer with
        # the new, shorter size: a silently cut member reported as captured.
        root = self.root_with()
        import tarfile as tarfile_module
        with patch.object(tarfile_module.TarFile, "gettarinfo",
                          side_effect=AssertionError("metadata was taken from a second stat")):
            manifest = baseline_module.capture(self.baseline_dir, root=str(root), stamp="S1")
        self.assertIn("etc/hostname", manifest["captured"])
        with tarfile_module.open(self.baseline_dir / manifest["archive"]) as tar:
            member = tar.getmember("etc/hostname")
            self.assertEqual(member.size, 2048)
            self.assertEqual(tar.extractfile(member).read(), b"A" * 2048)

    def test_a_file_truncated_during_the_read_is_skipped_not_cut(self):
        # The other half of the same window: the file shrinks while it is being
        # read, so the bytes and the size disagree. Either it is skipped or it
        # is whole; a member that is neither is the defect.
        root = self.root_with()
        real_open = open
        state = {"done": False}

        class Shrinking:
            def __init__(self, path):
                self._file = real_open(path, "rb")

            def fileno(self):
                return self._file.fileno()

            def read(self, size=-1):
                if not state["done"]:
                    state["done"] = True
                    (root / "etc" / "hostname").write_bytes(b"x")
                return self._file.read(size)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self._file.close()

        def fake_open(path, *args, **kwargs):
            if str(path).endswith("etc/hostname"):
                return Shrinking(path)
            return real_open(path, *args, **kwargs)

        with patch("builtins.open", fake_open):
            manifest = baseline_module.capture(self.baseline_dir, root=str(root), stamp="S2")
        self.assertNotIn("etc/hostname", manifest["captured"],
                         "a file that changed under the read was recorded as whole")
        reasons = {item["path"]: item["reason"] for item in manifest["skipped"]}
        self.assertEqual(reasons.get("etc/hostname"), "changed while being read")


class WorkerOwnershipTests(Temp):
    """Checking a token is not claiming it."""

    def busy_network(self, gate, event, seen):
        class Slow(FakeNetwork):
            def stop_hotspot(slow):
                slow.calls.append(("stop_hotspot",))
                slow.hotspot = None
                seen.append("stopping")
                gate.wait(5)
                event.set()
        return Slow()

    def test_two_workers_with_the_same_token_join_once(self):
        gate = threading.Event()
        event = threading.Event()
        seen = []
        network = self.busy_network(gate, event, seen)
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        _, token = onboarder.admit("HomeWiFi")
        results = []

        def worker():
            results.append(onboarder.join_reserved("HomeWiFi", "correct horse", token=token))

        first = threading.Thread(target=worker)
        first.start()
        for _ in range(500):
            if event.is_set() or len(seen) == 1:
                break
            threading.Event().wait(0.01)
        second = threading.Thread(target=worker)
        second.start()
        threading.Event().wait(0.05)
        gate.set()
        first.join(10)
        second.join(10)
        joins = [call for call in network.calls if call[0] == "connect"]
        self.assertEqual(len(joins), 1, f"the same reservation joined {len(joins)} times")
        self.assertEqual(len(results), 2)

    def test_a_worker_superseded_after_its_check_cannot_settle_the_new_attempt(self):
        gate = threading.Event()
        event = threading.Event()
        seen = []
        network = self.busy_network(gate, event, seen)
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        _, old_token = onboarder.admit("HomeWiFi")
        done = []

        def worker():
            done.append(onboarder.join_reserved("HomeWiFi", "correct horse", token=old_token))

        thread = threading.Thread(target=worker)
        thread.start()
        for _ in range(500):
            if seen:
                break
            threading.Event().wait(0.01)
        # A new generation of the attempt appears while the old worker is still
        # inside `stop_hotspot()`: the same effect a reboot-seeded retry or any
        # other writer of this record would have.
        new_token = secrets.token_hex(8)
        data = state_module.read(self.state_path)
        data.update(phase="connecting", ssid="HomeWiFi", attempt_token=new_token,
                    attempt_claimed=False)
        state_module.write(self.state_path, data)
        gate.set()
        thread.join(10)
        data = state_module.read(self.state_path)
        self.assertEqual(data["attempt_token"], new_token,
                         "the superseded worker cleared the current reservation")
        self.assertEqual(data["phase"], "connecting")

    def test_a_release_cannot_cancel_an_attempt_a_worker_already_took(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network)
        onboarder.start_hotspot()
        _, token = onboarder.admit("HomeWiFi")
        self.assertIsNotNone(onboarder._claim("HomeWiFi", token))
        with self.assertLogs(onboarding.LOGGER, level="WARNING"):
            onboarder.release(token)
        self.assertEqual(state_module.read(self.state_path)["phase"], "connecting")


class JournalBoundaryTests(Temp):
    """The journal is not a place for an exception's own text."""

    def test_a_capture_failure_logs_a_sentence_not_the_error_text(self):
        failure = PermissionError(13, "denied", "/synthetic/SYNTHETIC-SECRET-R3")
        network = FakeNetwork()
        network.joined = "HomeWiFi"
        onboarder = self.onboarder(network)
        data = state_module.blank("debra-demo1")
        data.update(phase="online", ssid="HomeWiFi", address="192.0.2.40")
        state_module.write(self.state_path, data)
        with patch.object(baseline_module, "capture", side_effect=failure):
            with self.assertLogs(onboarding.LOGGER, level="WARNING") as logs:
                status = onboarder.resume()
        text = "\n".join(logs.output)
        self.assertNotIn("SYNTHETIC-SECRET-R3", text, "the journal carried the path")
        self.assertIn("could not be read", text)
        self.assertEqual(status["baseline_error"], "Some device files could not be read")


class ScanSpaceTests(unittest.TestCase):
    """A name's leading and trailing spaces are part of the name."""

    def test_a_scan_does_not_trim_a_network_name(self):
        # `nmcli -t` separates fields with `:` and escapes a literal colon as
        # `\:`. The name is the first field, and its spaces are part of it.
        out = " Home :70:WPA2\nOther:40:WPA2\n"
        adapter = nm_module.Nmcli(runner=lambda argv, timeout=None: out)
        found = adapter.scan("wlan0")
        names = [item["ssid"] for item in found]
        self.assertIn(" Home ", names, f"the scan trimmed the name: {names}")


class SetupPasswordLifetimeTests(Temp):
    """The setup password has to survive a retry and a reboot.

    It used to be regenerated on every raise. Reading it off the card needs a
    reboot, which raised the access point again and invalidated the password
    just read; and one wrong household password replaced the credential the
    phone had saved for the setup network.
    """

    def test_a_wrong_household_password_keeps_the_setup_password(self):
        network = FakeNetwork(behaviour="bad-psk")
        clock = [0.0]
        note = self.dir / "boot" / "debra-setup.txt"
        onboarder = self.onboarder(network, clock=lambda: clock[0], card_note_path=note,
                                   security="wpa")
        onboarder.start_hotspot()
        first = onboarding.setup_secret(onboarder.secret_path)
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        status = onboarder.join("HomeWiFi", "wrong password", None)
        self.assertEqual(status["phase"], "failed")
        self.assertEqual(onboarding.setup_secret(onboarder.secret_path), first,
                         "the recovery access point changed its password")
        self.assertEqual(network.hotspot["password"], first,
                         "the radio was given a different password")
        self.assertIn(first, note.read_text(encoding="utf-8"),
                      "the note no longer names the password the access point uses")

    def test_a_reboot_keeps_the_setup_password(self):
        note = self.dir / "boot" / "debra-setup.txt"
        first = self.onboarder(FakeNetwork(), card_note_path=note,
                               security="wpa").start_hotspot()
        self.assertEqual(first["phase"], "hotspot")
        password = onboarding.setup_secret(self.state_path.with_name("setup-secret"))
        # A card-reader reboot: a new process, a new radio, the same disk.
        network = FakeNetwork()
        status = self.onboarder(network, card_note_path=note, security="wpa").resume()
        self.assertEqual(status["phase"], "hotspot")
        self.assertEqual(network.hotspot["password"], password)
        self.assertIn(password, note.read_text(encoding="utf-8"))

    def test_the_access_point_is_recorded_before_it_is_raised(self):
        # The old order raised first: a state write that failed left a live
        # access point that no state described and no note named. The password
        # has the same property, because the note is the only place it is
        # published.
        network = FakeNetwork()
        onboarder = self.onboarder(network, security="wpa")
        seen = []
        real = network.start_hotspot

        def watching(name, interface, password):
            seen.append((state_module.read(self.state_path)["hotspot"],
                         onboarding.setup_secret(onboarder.secret_path)))
            return real(name, interface, password)

        network.start_hotspot = watching
        onboarder.start_hotspot()
        self.assertEqual(seen, [({"ssid": "Debra-Setup-demo1", "interface": "wlan0"},
                                 onboarding.setup_secret(onboarder.secret_path))],
                         "the access point was raised before it was recorded")

    def test_a_failed_state_write_raises_nothing_to_take_down(self):
        network = FakeNetwork()
        state_module.write(self.state_path, dict(state_module.blank("debra-demo1")))

        def full_disk(path, data):
            raise OSError(28, "No space left on device")

        with patch.object(state_module, "write", full_disk):
            with self.assertRaises(OSError):
                self.onboarder(network).start_hotspot()
        self.assertIsNone(network.hotspot,
                          "an access point was raised with nothing recording it")
        self.assertNotIn("start_hotspot", network.phases())

    def test_a_failed_note_does_not_take_the_access_point_down(self):
        # A write to the boot partition is not the network. If it fails, the
        # person can still use the page; the radio must stay up.
        blocker = self.dir / "boot"
        blocker.write_text("not a directory", encoding="utf-8")
        network = FakeNetwork()
        status = self.onboarder(network, card_note_path=blocker / "note.txt",
                                security="wpa").start_hotspot()
        self.assertIsNotNone(network.hotspot,
                             "the access point was taken down because of the note")
        self.assertEqual(status["phase"], "hotspot")
        # An unreadable note with a password on it is the one failure that can
        # leave a person with no way in, so the state has to say so.
        self.assertEqual(status["last_error"],
                         "The setup network's password could not be written to the "
                         "boot partition")

    def test_two_devices_do_not_share_a_setup_password(self):
        # A fixed same-length password passed a test that only looked at the
        # random helper, not at the value the production path stores.
        first_onboarder = self.onboarder(security="wpa")
        first_onboarder.start_hotspot()
        first = onboarding.setup_secret(first_onboarder.secret_path)
        self.state_path.unlink()
        first_onboarder.secret_path.unlink()
        second_onboarder = self.onboarder(security="wpa")
        second_onboarder.start_hotspot()
        second = onboarding.setup_secret(second_onboarder.secret_path)
        self.assertNotEqual(first, second, "a fixed password was used for every device")
        self.assertTrue(set(first) <= set(onboarding.SECRET_ALPHABET))


class DeadAttemptTests(Temp):
    """A claim belongs to a process, and a reboot is a new process."""

    def claimed(self, onboarder, ssid="HomeWiFi"):
        onboarder.start_hotspot()
        accepted, token = onboarder.admit(ssid)
        self.assertTrue(accepted)
        self.assertIsNotNone(onboarder._claim(ssid, token))
        stored = state_module.read(self.state_path)
        self.assertTrue(stored["attempt_claimed"])
        return token

    def test_a_claimed_attempt_does_not_survive_a_boot(self):
        self.claimed(self.onboarder(FakeNetwork()))
        # The worker's process is gone: a new onboarder over the same disk.
        network = FakeNetwork()
        status = self.onboarder(network).resume()
        stored = state_module.read(self.state_path)
        self.assertFalse(stored["attempt_claimed"], "a dead claim survived the boot")
        self.assertIsNone(stored["attempt_token"])
        self.assertEqual(status["phase"], "failed")
        self.assertIn("did not finish", status["last_error"])
        # And a person can try again without repairing state by hand.
        second = self.onboarder(network, clock=lambda: 1000.0)
        accepted, token = second.admit("HomeWiFi")
        self.assertTrue(accepted, "the device stayed busy after a reboot")
        self.assertEqual(
            second.join_reserved("HomeWiFi", "correct horse", None, token)["phase"], "online")

    def test_an_unexpected_worker_failure_releases_the_attempt(self):
        network = FakeNetwork()
        # A real clock is `time.monotonic`, which is never near zero; the
        # throttle compares against `_last_submit`, so a fake clock starting at
        # zero would look like a submission that had just happened.
        clock = [1000.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()
        accepted, token = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)

        def boom(ssid, psk, **kwargs):
            raise RuntimeError("an unclassified failure in /etc/NetworkManager/x")

        network.connect = boom
        with self.assertLogs("onboarding", level="WARNING") as logs:
            status = onboarder.join_reserved("HomeWiFi", "correct horse", None, token)
        stored = state_module.read(self.state_path)
        self.assertFalse(stored["attempt_claimed"], "the worker left its claim behind")
        self.assertNotEqual(stored["phase"], "connecting")
        self.assertEqual(status["phase"], "failed")
        self.assertNotIn("/etc/NetworkManager", " ".join(logs.output),
                         "the worker log carried a path")
        del network.connect
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        accepted, _ = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted, "the device stayed busy after the worker failed")

    def test_a_state_write_failure_does_not_leave_the_device_busy(self):
        network = FakeNetwork()
        onboarder = self.onboarder(network, clock=lambda: 1000.0)
        onboarder.start_hotspot()
        accepted, token = onboarder.admit("HomeWiFi")
        real_write = state_module.write

        def failing(path, data):
            if data.get("phase") == "online":
                raise OSError(28, "No space left on device")
            return real_write(path, data)

        with patch.object(state_module, "write", failing):
            status = onboarder.join_reserved("HomeWiFi", "correct horse", None, token)
        stored = state_module.read(self.state_path)
        self.assertFalse(stored["attempt_claimed"])
        self.assertEqual(stored["phase"], "failed")
        self.assertNotEqual(status["phase"], "connecting")


class FailureRearmTests(Temp):
    """The failure rearm owns the admission lock until the AP is back."""

    def test_a_new_attempt_cannot_be_admitted_against_a_missing_access_point(self):
        gate = threading.Event()
        entered = threading.Event()
        network = FakeNetwork(behaviour="bad-psk")
        clock = [1000.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()

        real_start = network.start_hotspot
        calls = []

        def gated_start(name, interface, password=None):
            calls.append(name)
            # The first call here is the failure's recovery raise: the initial
            # access point was raised before this patch was installed.
            if len(calls) == 1:
                entered.set()
                gate.wait(5)
            return real_start(name, interface, password)

        network.start_hotspot = gated_start
        accepted, token = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)
        worker = threading.Thread(target=onboarder.join_reserved,
                                  args=("HomeWiFi", "wrong password", None, token))
        worker.start()
        self.assertTrue(entered.wait(5), "the failure rearm never raised the access point")

        # While the rearm is paused, a new request must not be admitted: it
        # would see a device whose access point is still down.
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        admitted = []
        newcomer = threading.Thread(target=lambda: admitted.append(onboarder.admit("Other")))
        newcomer.start()
        newcomer.join(timeout=0.5)
        self.assertTrue(newcomer.is_alive(),
                        "a new attempt was admitted while the access point was down")
        self.assertEqual(admitted, [])

        network.behaviour = "ok"
        gate.set()
        worker.join(timeout=5)
        newcomer.join(timeout=5)
        self.assertFalse(newcomer.is_alive())
        self.assertTrue(admitted and admitted[0][0], "the retry after the rearm was refused")
        # The newer attempt wins. The old worker's rearm must not overwrite it.
        status = onboarder.join_reserved("Other", "correct horse", None, admitted[0][1])
        self.assertEqual(status["phase"], "online")
        self.assertEqual(status["ssid"], "Other")


class BaselineValidationTests(Temp):
    """A hash proves correspondence to metadata, not that it is a baseline."""

    def test_unrelated_matching_bytes_are_not_adopted(self):
        self.baseline_dir.mkdir()
        outside = self.dir / "not-a-baseline.bin"
        outside.write_bytes(b"an ordinary file")
        digest = hashlib.sha256(outside.read_bytes()).hexdigest()
        (self.baseline_dir / "baseline-unrelated.json").write_text(
            json.dumps({"archive": str(outside), "sha256": digest}))
        self.assertIsNone(baseline_module.latest(self.baseline_dir),
                          "an arbitrary file was reported as a baseline")
        self.assertIsNone(baseline_module.verified(self.baseline_dir, outside))

    def test_a_manifest_pointing_outside_the_directory_is_refused(self):
        self.baseline_dir.mkdir()
        outside = self.dir / "elsewhere.tar.gz"
        outside.write_bytes(b"x")
        (self.baseline_dir / "baseline-x.json").write_text(json.dumps({
            "archive": "../elsewhere.tar.gz", "created": "S",
            "sha256": hashlib.sha256(b"x").hexdigest(), "bytes": 1,
            "captured": [], "skipped": [], "missing": [], "note": "x"}))
        self.assertIsNone(baseline_module.latest(self.baseline_dir))

    def test_a_real_capture_validates(self):
        manifest = baseline_module.capture(self.baseline_dir, root=str(self.dir / "empty"),
                                           stamp="S")
        self.assertEqual(baseline_module.latest(self.baseline_dir)["archive"],
                         manifest["archive"])
        self.assertIsNotNone(
            baseline_module.verified(self.baseline_dir,
                                     self.baseline_dir / manifest["archive"]))

    def test_a_manifest_whose_inventory_the_archive_does_not_hold_is_refused(self):
        root = self.dir / "root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-1\n", encoding="utf-8")
        manifest = baseline_module.capture(self.baseline_dir, root=str(root), stamp="S")
        path = self.baseline_dir / (manifest["archive"][:-len(".tar.gz")] + ".json")
        data = json.loads(path.read_text())
        data["captured"] = ["etc/not-there"]
        path.write_text(json.dumps(data))
        self.assertIsNone(baseline_module.latest(self.baseline_dir))

    def test_a_manifest_whose_archive_is_not_a_tar_is_refused(self):
        self.baseline_dir.mkdir()
        archive = self.baseline_dir / "baseline-fake.tar.gz"
        archive.write_bytes(b"not a tarball")
        (self.baseline_dir / "baseline-fake.json").write_text(json.dumps({
            "archive": archive.name, "created": "S",
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "bytes": archive.stat().st_size, "captured": [], "skipped": [],
            "missing": [], "note": "x"}))
        self.assertIsNone(baseline_module.latest(self.baseline_dir))


class BaselineRecordingFailureTests(Temp):
    def test_a_capture_that_cannot_be_recorded_is_reported_in_the_state(self):
        # The pointer write failed but the error write could succeed. The state
        # must say so: a silent gap reads as progress that is not happening.
        onboarder = self.onboarder(FakeNetwork())
        real_write = state_module.write

        def failing(path, data):
            if data.get("baseline"):
                raise OSError(28, "No space left on device")
            return real_write(path, data)

        with patch.object(state_module, "write", failing):
            onboarder._capture_baseline()
        stored = state_module.read(self.state_path)
        self.assertIsNone(stored["baseline"])
        self.assertEqual(stored["baseline_error"], "The device is out of disk space")
        self.assertEqual(onboarder.status()["baseline_error"],
                         "The device is out of disk space")

    def test_a_pointer_that_cannot_be_written_does_not_capture_again(self):
        # A complete capture with no pointer is adopted, not re-captured:
        # capturing again adds another archive on a store refusing writes.
        root = self.dir / "root"
        (root / "etc").mkdir(parents=True)
        (root / "etc" / "hostname").write_text("debra-1\n", encoding="utf-8")
        baseline_module.capture(self.baseline_dir, root=str(root), stamp="S1")
        self.assertEqual(len(list(self.baseline_dir.glob("baseline-*.tar.gz"))), 1)
        onboarder = self.onboarder(FakeNetwork(), root=str(root))
        real_write = state_module.write

        def failing(path, data):
            if data.get("baseline"):
                raise OSError(28, "No space left on device")
            return real_write(path, data)

        with patch.object(state_module, "write", failing):
            onboarder._capture_baseline()
        self.assertEqual(len(list(self.baseline_dir.glob("baseline-*.tar.gz"))), 1,
                         "a second baseline was captured on a store refusing writes")
        self.assertEqual(onboarder.status()["baseline_error"],
                         "The device is out of disk space")

    def test_the_running_page_is_told_even_when_no_state_write_succeeds(self):
        # The file cannot record the failure, so the running page must.
        onboarder = self.onboarder(FakeNetwork())

        def failing(path, data):
            raise OSError(28, "No space left on device")

        with patch.object(state_module, "write", failing):
            onboarder._capture_baseline()
        self.assertEqual(onboarder.status()["baseline_error"],
                         "The device is out of disk space")


class CaptureCoherenceTests(Temp):
    def test_a_same_size_rewrite_during_the_read_is_skipped(self):
        root = self.dir / "race-root"
        (root / "etc").mkdir(parents=True)
        path = root / "etc" / "hostname"
        path.write_bytes(b"A" * (2 << 20))
        real_open = open
        state = {"done": False}

        class Rewriting:
            def __init__(self, target):
                self._file = real_open(target, "rb")

            def fileno(self):
                return self._file.fileno()

            def read(self, size=-1):
                data = self._file.read(size)
                if not state["done"]:
                    state["done"] = True
                    # Same size, different bytes: a length check cannot see it,
                    # so a torn AA/BA mixture was recorded and called verified.
                    with real_open(target_path, "wb") as stream:
                        stream.write(b"B" * (2 << 20))
                return data

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self._file.close()

        target_path = path

        def fake_open(target, *args, **kwargs):
            if str(target).endswith("etc/hostname"):
                return Rewriting(target)
            return real_open(target, *args, **kwargs)

        with patch("builtins.open", fake_open):
            manifest = baseline_module.capture(self.baseline_dir, root=str(root), stamp="S")
        self.assertNotIn("etc/hostname", manifest["captured"],
                         "a file rewritten under the read was recorded as whole")
        reasons = {item["path"]: item["reason"] for item in manifest["skipped"]}
        self.assertEqual(reasons.get("etc/hostname"), "changed while being read")


class SsidLimitTests(unittest.TestCase):
    def test_exactly_32_octets_is_a_valid_name(self):
        self.assertTrue(nm_module.valid_ssid("x" * 32))
        self.assertFalse(nm_module.valid_ssid("x" * 33))
        # The limit is octets, not characters.
        self.assertTrue(nm_module.valid_ssid("\u00e9" * 16))
        self.assertFalse(nm_module.valid_ssid("\u00e9" * 17))


class ClaimLockTests(Temp):
    """Taking ownership is one atomic read-modify-write.

    Checking the token and then setting the marker is not ownership: two workers
    holding the same valid token both passed the check and both joined. The lock
    around the claim is what makes the second one lose, and nothing forced the
    two reads to overlap before.
    """

    def test_only_one_worker_can_claim_when_the_state_read_is_slow(self):
        onboarder = self.onboarder(clock=lambda: 1000.0)
        onboarder.start_hotspot()
        accepted, token = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)
        real_read = state_module.read
        second_read = threading.Event()
        seen = []

        def slow_read(path):
            data = real_read(path)
            if not threading.current_thread().name.startswith("claimer"):
                return data
            seen.append(data["attempt_claimed"])
            if len(seen) == 1:
                # Hold the first claimer inside its read-modify-write for
                # longer than the second needs to arrive. Without the lock the
                # second reads the stale record and both claim the attempt.
                second_read.wait(0.5)
            else:
                second_read.set()
            return data

        results = []

        def claim():
            results.append(onboarder._claim("HomeWiFi", token))

        with patch.object(state_module, "read", slow_read):
            threads = [threading.Thread(target=claim, name=f"claimer-{index}")
                       for index in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
        self.assertEqual(len(results), 2)
        claimed = [result for result in results if result is not None]
        self.assertEqual(len(claimed), 1,
                         "two workers took the same reservation: %d claims" % len(claimed))


class BaselineDurabilityTests(Temp):
    def test_the_new_names_are_made_durable_not_only_the_bytes(self):
        # A capture that is fsynced but whose names are not can still lose both
        # files after a power cut, leaving a manifest that points at nothing.
        self.baseline_dir.mkdir()
        synced = []
        real_fsync = os.fsync

        def watching(fd):
            try:
                info = os.fstat(fd)
                synced.append(stat.S_ISDIR(info.st_mode))
            except OSError:
                pass
            return real_fsync(fd)

        with patch.object(os, "fsync", watching):
            baseline_module.capture(self.baseline_dir, root=str(self.dir / "empty"),
                                    stamp="S")
        self.assertIn(True, synced, "the baseline directory itself was never fsynced")


class RearmWindowTests(Temp):
    """No request may be admitted between the failure and the raised AP.

    The r4 repair settled the failure and then re-raised the access point while
    still holding the admission lock. Pausing inside the raise cannot see that
    window, because the raise is already inside the lock: the old order released
    ownership first, so the gap is between the settlement write and the raise.
    """

    def test_nothing_is_admitted_between_the_failure_and_the_rearm(self):
        network = FakeNetwork(behaviour="bad-psk")
        clock = [1000.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()
        real_write = state_module.write
        entered = threading.Event()
        release = threading.Event()
        gated = []

        def gated_write(path, data):
            if (not gated and data.get("phase") == "failed"
                    and not data.get("attempt_token")):
                # This is the settlement inside `_fail`. Hold the worker here.
                gated.append(True)
                entered.set()
                release.wait(5)
            return real_write(path, data)

        with patch.object(state_module, "write", gated_write):
            accepted, token = onboarder.admit("HomeWiFi")
            self.assertTrue(accepted)
            worker = threading.Thread(target=onboarder.join_reserved,
                                      args=("HomeWiFi", "wrong password", None, token))
            worker.start()
            self.assertTrue(entered.wait(5), "the failure was never recorded")

            clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
            admitted = []
            newcomer = threading.Thread(target=lambda: admitted.append(onboarder.admit("Other")))
            newcomer.start()
            newcomer.join(timeout=0.5)
            self.assertTrue(
                newcomer.is_alive(),
                "a new attempt was admitted while the access point was still down")
            self.assertEqual(admitted, [])

            release.set()
            worker.join(timeout=5)
            newcomer.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertFalse(newcomer.is_alive())
        self.assertTrue(admitted and admitted[0][0], "the retry after the rearm was refused")
        self.assertEqual(onboarder.status()["phase"], "connecting")


class SupersededFailureTests(Temp):
    """A worker that lost its reservation must not record its own failure.

    The settlement already re-checks the token; the failure path reached the
    same state through `start_hotspot()`, which wrote a full record. A worker
    superseded while failing wiped the newer attempt's token, published its own
    stale reason and raised the access point over it.
    """

    def test_a_superseded_worker_cannot_record_its_failure(self):
        network = FakeNetwork(behaviour="bad-psk")
        clock = [1000.0]
        onboarder = self.onboarder(network, clock=lambda: clock[0])
        onboarder.start_hotspot()
        accepted, first = onboarder.admit("HomeWiFi")
        self.assertTrue(accepted)
        # The phone never got the reply, so it retried with a different name.
        # That is the production path to a superseded worker.
        onboarder.release(first)
        clock[0] += onboarding.SUBMIT_INTERVAL_S + 1
        accepted, second = onboarder.admit("Other")
        self.assertTrue(accepted)
        raises = len([call for call in network.calls if call[0] == "start_hotspot"])

        status = onboarder._fail(first, "The Wi-Fi password was refused by the network")

        stored = state_module.read(self.state_path)
        self.assertEqual(stored["phase"], "connecting",
                         "a superseded worker ended the newer attempt")
        self.assertEqual(stored["attempt_token"], second,
                         "a superseded worker cleared the newer attempt's token")
        self.assertEqual(stored["ssid"], "Other")
        self.assertIsNone(stored["last_error"],
                          "a superseded worker published its own stale reason")
        self.assertEqual(len([call for call in network.calls
                              if call[0] == "start_hotspot"]), raises,
                         "a superseded worker raised the access point over the newer attempt")
        self.assertEqual(status["phase"], "connecting")


class HandlerBoundaryTests(Temp):
    """The request handler is a boundary too, not only the join worker."""

    def test_a_state_write_failure_answers_the_phone_instead_of_tracebacking(self):
        # `admit()` writes the state. A full disk there raised inside
        # BaseHTTPRequestHandler: socketserver printed the traceback, with the
        # state path in it, to the journal, and the phone got no reply at all.
        network = FakeNetwork()
        onboarder = self.onboarder(network, clock=lambda: 1000.0)
        onboarder.start_hotspot()
        server = onboarding.Portal(("127.0.0.1", 0), onboarder,
                                   onboarding.ASSETS / "setup.html")
        host = "127.0.0.1:%d" % server.server_port
        server.host = host
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        stderr = io.StringIO()
        real_write = state_module.write

        def full_disk(path, data):
            raise OSError(28, "No space left on device: " + str(self.state_path))

        request = urllib.request.Request(
            "http://" + host + "/api/join",
            data=json.dumps({"ssid": "HomeWiFi", "psk": "correct horse"}).encode(),
            method="POST")
        request.add_header("Host", host)
        request.add_header("Content-Type", "application/json")
        try:
            with patch.object(state_module, "write", full_disk), \
                    redirect_stderr(stderr):
                try:
                    with urllib.request.urlopen(request, timeout=10) as response:
                        code, body = response.status, response.read()
                except urllib.error.HTTPError as exc:
                    code, body = exc.code, exc.read()
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
        self.assertEqual(code, 500)
        self.assertIn(b"could not handle the request", body)
        self.assertNotIn(str(self.state_path), stderr.getvalue(),
                         "the journal received the state path")
        self.assertNotIn("Traceback", stderr.getvalue(),
                         "socketserver printed a traceback for a handled failure")
        self.assertEqual(state_module.read(self.state_path)["phase"], "hotspot")

    def portal(self):
        """A real portal on a loopback port, stopped by this test."""
        onboarder = self.onboarder(FakeNetwork(), clock=lambda: 1000.0)
        onboarder.start_hotspot()
        server = onboarding.Portal(("127.0.0.1", 0), onboarder,
                                   onboarding.ASSETS / "setup.html")
        host = "127.0.0.1:%d" % server.server_port
        server.host = host
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop():
            server.shutdown()
            thread.join()
            server.server_close()

        self.addCleanup(stop)
        return server, onboarder, host

    @staticmethod
    def raw(server, request):
        """One request on a fresh connection, read until the server closes."""
        with socket.create_connection(("127.0.0.1", server.server_port),
                                      timeout=10) as connection:
            connection.sendall(request)
            chunks = []
            while True:
                chunk = connection.recv(4096)
                if not chunk:
                    return b"".join(chunks)
                chunks.append(chunk)

    @staticmethod
    def join_request(host, ssid="HomeWiFi", psk="correct horse"):
        body = json.dumps({"ssid": ssid, "psk": psk}).encode()
        return (("POST /api/join HTTP/1.0\r\nHost: %s\r\n"
                 "Content-Type: application/json\r\n"
                 "Content-Length: %d\r\n\r\n" % (host, len(body))).encode() + body)

    def test_a_state_read_failure_answers_the_poll_instead_of_tracebacking(self):
        # `/api/status` is polled every fifteen seconds. The POST boundary did
        # not cover it, so a failing read escaped socketserver, printed the
        # state path to the journal and closed the connection with no reply.
        server, onboarder, host = self.portal()
        stderr = io.StringIO()
        request = urllib.request.Request("http://" + host + "/api/status")
        request.add_header("Host", host)
        failure = OSError(5, "Input/output error: " + str(self.state_path))
        with patch.object(onboarder, "status", side_effect=failure), \
                redirect_stderr(stderr):
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    code, body = response.status, response.read()
            except urllib.error.HTTPError as exc:
                code, body = exc.code, exc.read()
        self.assertEqual(code, 500)
        self.assertIn(b"could not handle the request", body)
        self.assertNotIn(str(self.state_path), stderr.getvalue(),
                         "the journal received the state path")
        self.assertNotIn("Traceback", stderr.getvalue(),
                         "socketserver printed a traceback for a handled failure")

    def test_a_failure_after_the_reservation_gives_it_back(self):
        # `admit()` has already written `connecting` when `status()` is read for
        # the reply. An exception there answers 500; it must also release the
        # reservation, or every later submission is refused as busy until the
        # process restarts.
        server, onboarder, host = self.portal()
        with patch.object(onboarder, "status",
                          side_effect=OSError(5, "Input/output error")):
            raw = self.raw(server, self.join_request(host))
        self.assertIn(b"500", raw.split(b"\r\n", 1)[0], repr(raw[:500]))
        stored = state_module.read(self.state_path)
        self.assertEqual(stored["phase"], "hotspot",
                         "a failed handler left the device connecting")
        self.assertIsNone(stored["attempt_token"])

    def test_a_release_that_also_fails_still_answers_the_phone(self):
        # Releasing is a state write, and the state store is one of the things
        # that can be failing. A boundary that raises from inside its own
        # except block is the traceback it exists to prevent.
        server, onboarder, host = self.portal()
        stderr = io.StringIO()
        request = urllib.request.Request(
            "http://" + host + "/api/join",
            data=json.dumps({"ssid": "HomeWiFi", "psk": "correct horse"}).encode(),
            method="POST")
        request.add_header("Host", host)
        request.add_header("Content-Type", "application/json")
        with patch.object(onboarder, "status",
                          side_effect=OSError(5, "Input/output error")), \
                patch.object(onboarder, "release",
                             side_effect=OSError(28, "No space: " + str(self.state_path))), \
                redirect_stderr(stderr):
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    code, body = response.status, response.read()
            except urllib.error.HTTPError as exc:
                code, body = exc.code, exc.read()
        self.assertEqual(code, 500)
        self.assertIn(b"could not handle the request", body)
        self.assertNotIn(str(self.state_path), stderr.getvalue(),
                         "the journal received the state path")
        self.assertNotIn("Traceback", stderr.getvalue(),
                         "socketserver printed a traceback for a handled failure")

    def test_a_worker_that_cannot_start_answers_once_and_gives_the_reservation_back(self):
        # The 202 is already on the wire when the thread starts. If starting it
        # raises, the boundary must not put a second response on the same
        # connection, and the reservation must not be left behind.
        server, onboarder, host = self.portal()
        real_thread = threading.Thread

        class Worker:
            def start(self):
                raise RuntimeError("the worker could not start")

        def factory(*args, **kwargs):
            if kwargs.get("name") == "debra-onboarding":
                return Worker()
            return real_thread(*args, **kwargs)

        with patch.object(onboarding.threading, "Thread", factory):
            raw = self.raw(server, self.join_request(host))
        self.assertEqual(raw.count(b"HTTP/1."), 1,
                         "a second response went out on one connection: "
                         + repr(raw[:2000]))
        self.assertIn(b"202 Accepted", raw)
        stored = state_module.read(self.state_path)
        self.assertEqual(stored["phase"], "hotspot",
                         "a worker that never started left the attempt connecting")
        self.assertIsNone(stored["attempt_token"])


class PersistedBaselineFailureTests(Temp):
    """The recorded failure must outlive the process that saw it.

    The in-memory copy is what the running page shows. It is not what the next
    boot reads: without the persisted field the page says only "not captured
    yet" after a reboot, with no reason, and nothing retries visibly. There are
    two ways a baseline attempt fails - the capture itself, and recording a
    capture that succeeded - and each writes its own record, so each needs its
    own test. A write filter keyed on `baseline` only reached the second.
    """

    def test_the_next_process_sees_a_capture_failure(self):
        onboarder = self.onboarder(FakeNetwork())
        failure = OSError(28, "No space left on device")
        with patch.object(baseline_module, "capture", side_effect=failure):
            onboarder._capture_baseline()
        # The running page is told from memory, which is what hid the gap.
        self.assertEqual(onboarder.status()["baseline_error"],
                         "The device is out of disk space")
        # A later process has no memory of the failure, only the file.
        later = self.onboarder(FakeNetwork())
        self.assertEqual(later.status()["baseline_error"],
                         "The device is out of disk space",
                         "the recorded capture failure did not survive the process")

    def test_the_next_process_sees_a_pointer_write_failure(self):
        onboarder = self.onboarder(FakeNetwork())
        real_write = state_module.write

        def failing(path, data):
            if data.get("baseline"):
                raise OSError(28, "No space left on device")
            return real_write(path, data)

        with patch.object(state_module, "write", failing):
            onboarder._capture_baseline()
        self.assertEqual(onboarder.status()["baseline_error"],
                         "The device is out of disk space")
        # A later process has no memory of the failure, only the file.
        later = self.onboarder(FakeNetwork())
        self.assertEqual(later.status()["baseline_error"],
                         "The device is out of disk space",
                         "the recorded failure did not survive the process that saw it")


if __name__ == "__main__":
    # Last, so running this file directly collects every class above it. It used
    # to sit in the middle of the file, and `python tests/test_onboarding.py`
    # then reported success while silently skipping the security and
    # access-point tests declared below it.
    unittest.main()
