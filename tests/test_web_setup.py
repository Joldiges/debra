"""Offline checks for the Setup card: what it reports, and what it refuses.

Commands are fakes and HTTP is loopback. Nothing here proves a HAT works, a
service is configured, or that a device can be changed: the point of these tests
is that the page tells the truth about what it cannot do.
"""

import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from control.web import server as web


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "control/web"
SINK = "alsa_output.test.stereo-fallback"
TOKEN = "test_" + "a" * 40

# The documented shape. Exact sets on purpose: an added field is a contract
# change and should fail here rather than surprise the page.
SETUP_KEYS = {"writable", "reason", "hardware", "settings", "updates"}
HARDWARE_KEYS = {"detected_hat", "detected_source", "retained_label", "retained_note",
                 "cards", "cards_source", "selectable", "choice", "installed",
                 "reason", "choice_note", "options", "boot", "helper"}
OPTION_KEYS = {"id", "label", "summary", "detected", "card", "applied", "selected",
               "caveats", "installable", "configured", "overlay"}
BOOT_KEYS = {"path", "readable", "overlays", "i2c"}
HELPER_KEYS = {"path", "present", "enrol_note"}
INSTALLABLE_KEYS = {"ok", "reason"}
CARD_KEYS = {"name", "present"}
SETTING_KEYS = {"id", "label", "summary", "value", "options", "selectable", "reason"}
UPDATE_KEYS = {"available", "reason", "actions"}
ACTION_KEYS = {"id", "label", "enabled", "reason"}


class SetupCommands:
    """Only the probes the setup payload may issue: `systemctl show`.

    Reaching the install helper is a socket connection, not a command, so a
    device with no helper never runs anything.
    """

    def __init__(self):
        self.calls = []

    def __call__(self, argv, *, timeout=web.COMMAND_TIMEOUT):
        self.calls.append(list(argv))
        if argv[0] != "systemctl":
            raise AssertionError(f"Unexpected command: {argv}")
        return "\n\n".join(
            f"Id={unit}\nLoadState=loaded\nActiveState=active\nUnitFileState=enabled"
            for unit in argv if unit.endswith(".service"))


class SetupPayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="web-setup-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.commands = SetupCommands()

    def put(self, path, text):
        target = self.root / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def backend(self, metadata=None):
        return web.Backend(SINK, metadata or {}, self.commands, self.root)

    def test_payload_shape_is_the_documented_one(self):
        payload = self.backend().setup()
        self.assertEqual(set(payload), SETUP_KEYS)
        self.assertEqual(set(payload["hardware"]), HARDWARE_KEYS)
        # Four boards a person might actually have fitted. The two that this
        # page cannot tell apart are listed apart rather than merged into one
        # vague row: the person knows which board they bought.
        self.assertEqual([option["id"] for option in payload["hardware"]["options"]],
                         ["respeaker-2mic-hat-v2", "respeaker-2mic-hat-v1",
                          "waveshare-wm8960", "none"])
        self.assertEqual(set(payload["hardware"]["boot"]), BOOT_KEYS)
        self.assertEqual(set(payload["hardware"]["helper"]), HELPER_KEYS)
        for option in payload["hardware"]["options"]:
            self.assertEqual(set(option), OPTION_KEYS)
            self.assertEqual(set(option["installable"]), INSTALLABLE_KEYS)
            self.assertEqual(set(option["card"]), CARD_KEYS)
        self.assertEqual(list(payload["settings"]), ["music", "interruption", "update_policy"])
        for setting in payload["settings"].values():
            self.assertEqual(set(setting), SETTING_KEYS)
        self.assertEqual(set(payload["updates"]), UPDATE_KEYS)
        for action in payload["updates"]["actions"]:
            self.assertEqual(set(action), ACTION_KEYS)
        json.dumps(payload, allow_nan=False)

    def test_nothing_on_the_card_can_be_changed(self):
        payload = self.backend().setup()
        self.assertFalse(payload["writable"])
        # No state directory means no place to record a choice, so this backend
        # offers no control rather than one that forgets what was chosen.
        self.assertFalse(payload["hardware"]["selectable"])
        self.assertIsNone(payload["hardware"]["choice"])
        for setting in payload["settings"].values():
            self.assertFalse(setting["selectable"])
            # No value is reported, because none is stored anywhere yet.
            self.assertIsNone(setting["value"])
        self.assertFalse(payload["updates"]["available"])
        self.assertEqual([action["enabled"] for action in payload["updates"]["actions"]],
                         [False, False, False])

    def test_missing_evidence_is_unknown_not_absent(self):
        # No device tree, no /proc: the card must say unknown rather than claim
        # the board has no HAT and no sound card.
        payload = self.backend().setup()
        hardware = payload["hardware"]
        self.assertIsNone(hardware["detected_hat"])
        self.assertIsNone(hardware["cards"])
        self.assertIsNone(hardware["retained_label"])
        for option in hardware["options"]:
            self.assertIsNone(option["detected"])
            self.assertIsNone(option["applied"])
        self.assertIn("unreadable", hardware["detected_source"])

    def test_detected_hat_and_listed_card_are_reported(self):
        self.put("/sys/firmware/devicetree/base/hat/product", "ReSpeaker 2-Mics Pi HAT\0")
        self.put("/proc/asound/cards", " 0 [seeed2micvoicec]: simple-card - seeed2micvoicec\n"
                                      " 1 [vc4hdmi0      ]: vc4-hdmi - vc4-hdmi-0\n")
        hardware = self.backend({"hat": "ReSpeaker 2-Mics Pi HAT v2"}).setup()["hardware"]
        self.assertEqual(hardware["detected_hat"], "ReSpeaker 2-Mics Pi HAT")
        self.assertEqual(hardware["cards"], ["seeed2micvoicec", "vc4hdmi0"])
        self.assertEqual(hardware["retained_label"], "ReSpeaker 2-Mics Pi HAT v2")
        respeaker, v1, waveshare, none = hardware["options"]
        self.assertTrue(respeaker["detected"])
        self.assertTrue(respeaker["card"]["present"])
        self.assertTrue(respeaker["applied"])
        # "No HAT" is not detected merely because another HAT is.
        self.assertFalse(none["detected"])
        # An absent option has no card name to look for, so it cannot be applied
        # or ruled out: no sound card is proof of nothing.
        self.assertIsNone(none["card"]["name"])
        self.assertIsNone(none["applied"])
        # The two WM8960 boards report no card here, and neither of them claims
        # to be detected: this device has not said it is either of them.
        for option in (v1, waveshare):
            self.assertFalse(option["card"]["present"])
            self.assertFalse(option["detected"],
                             f"{option['id']} was identified from a codec name")

    def test_a_wm8960_card_is_consistent_with_two_boards_and_names_neither(self):
        # A codec name is not a vendor. Reporting this card as the Seeed v1 HAT
        # would be equally a claim for the Waveshare board.
        self.put("/proc/asound/cards",
                 " 0 [wm8960soundcard]: simple-card - wm8960-soundcard\n")
        hardware = self.backend().setup()["hardware"]
        by_id = {option["id"]: option for option in hardware["options"]}
        for name in ("respeaker-2mic-hat-v1", "waveshare-wm8960"):
            self.assertTrue(by_id[name]["card"]["present"], name)
            self.assertFalse(by_id[name]["detected"], name)
            self.assertTrue(by_id[name]["applied"], name)
        self.assertFalse(by_id["respeaker-2mic-hat-v2"]["card"]["present"])

    def test_the_update_policy_reason_is_scoped_to_debras_own_mechanism(self):
        # "Nothing on the device can be pinned or updated yet" was false: apt and
        # hand edits exist. What is true is that Debra has no update mechanism of
        # its own, so there is no policy to record here.
        settings = self.backend().setup()["settings"]
        reason = settings["update_policy"]["reason"]
        self.assertIn("Debra has no update mechanism", reason)
        self.assertNotIn("Nothing on the device", reason)

    def test_an_unknown_hat_is_not_claimed_as_the_respeaker(self):
        self.put("/sys/firmware/devicetree/base/hat/product", "Some Other HAT\0")
        self.put("/proc/asound/cards", " 0 [Headphones     ]: bcm2835 - bcm2835\n")
        hardware = self.backend().setup()["hardware"]
        respeaker = hardware["options"][0]
        self.assertFalse(respeaker["detected"])
        self.assertFalse(respeaker["card"]["present"])
        self.assertFalse(respeaker["applied"])

    def test_another_board_from_the_same_makers_is_not_this_one(self):
        # One vendor word was treated as an identification. A four-microphone
        # array and an unrelated Seeed sensor HAT are neither of them this
        # two-microphone board, and neither is a v2.
        for product in ("ReSpeaker 4 Mic Array", "Seeed unrelated sensor HAT",
                        "ReSpeaker 2-Mics Pi HAT v2 (demonstration)"):
            with self.subTest(product=product):
                label = " %s\0" % product
                self.put("/sys/firmware/devicetree/base/hat/product", label)
                self.put("/proc/asound/cards", " 0 [Headphones     ]: bcm2835\n")
                respeaker = self.backend().setup()["hardware"]["options"][0]
                if product.startswith("ReSpeaker 2-Mics"):
                    self.assertTrue(respeaker["detected"],
                                    "a two-mic ReSpeaker product was not recognised at all")
                else:
                    self.assertFalse(respeaker["detected"],
                                     f"{product} was reported as this board")

    def test_the_revision_is_never_claimed_from_the_eeprom(self):
        # The family match is all the evidence supports, and the page must say
        # so rather than telling a person their board is the v2.
        self.put("/sys/firmware/devicetree/base/hat/product", "ReSpeaker 2-Mics Pi HAT\0")
        self.put("/proc/asound/cards", " 0 [seeed2micvoicec]: simple-card\n")
        respeaker = self.backend().setup()["hardware"]["options"][0]
        self.assertTrue(respeaker["detected"])
        self.assertNotIn("revision", (respeaker.get("summary") or "").lower())

    def test_card_list_that_cannot_be_read_leaves_applied_unknown(self):
        self.put("/sys/firmware/devicetree/base/hat/product", "ReSpeaker 2-Mics Pi HAT\0")
        (self.root / "proc/asound").mkdir(parents=True)
        (self.root / "proc/asound/cards").mkdir()
        # A directory where the file should be: readable path, unreadable file.
        hardware = self.backend().setup()["hardware"]
        self.assertIsNone(hardware["cards"])
        self.assertIsNone(hardware["options"][0]["applied"])

    def test_service_state_is_reported_but_is_not_a_setting(self):
        payload = self.backend().setup()
        music = payload["settings"]["music"]
        sendspin = next(option for option in music["options"] if option["id"] == "sendspin")
        self.assertEqual(sendspin["observed"]["user"]["active"], "active")
        self.assertIsNone(sendspin["observed"]["system"])
        snapcast = next(option for option in music["options"] if option["id"] == "snapcast")
        self.assertEqual(snapcast["observed"]["system"]["unit_found"], True)
        self.assertIsNone(music["value"])

    def test_only_systemctl_show_is_invoked(self):
        self.backend().setup()
        self.assertTrue(self.commands.calls)
        for call in self.commands.calls:
            self.assertEqual(call[0], "systemctl")
            self.assertEqual(call[-1],
                             "--property=Id,LoadState,ActiveState,UnitFileState,MainPID")
            self.assertIn("show", call)
            self.assertFalse({"start", "stop", "restart", "enable", "disable"} & set(call))
        self.assertFalse(any("pactl" in call for call in self.commands.calls))

    def test_caveats_name_the_unmeasured_layout(self):
        caveats = " ".join(self.backend().setup()["hardware"]["options"][0]["caveats"])
        self.assertIn("estimate", caveats)
        self.assertIn("not a measurement", caveats)
        self.assertIn("APA102", caveats)

    def test_every_unavailable_choice_explains_itself(self):
        payload = self.backend().setup()
        self.assertTrue(payload["reason"])
        self.assertTrue(payload["hardware"]["reason"])
        for setting in payload["settings"].values():
            self.assertTrue(setting["reason"], setting["id"])
        self.assertTrue(payload["updates"]["reason"])
        for action in payload["updates"]["actions"]:
            self.assertTrue(action["reason"], action["id"])


class HatChoiceTests(unittest.TestCase):
    """Recording which board a person has: a note, not an installation.

    The four options are a question this page can ask and remember. Applying a
    choice means a device-tree overlay and a driver, which is a privileged write
    this server never performs, so what these tests hold is that a choice is
    recorded truthfully, kept private, and never presented as installed.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="web-hat-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "state"
        self.state.mkdir(mode=0o700)
        self.state.chmod(0o700)
        self.root = Path(self.temp.name) / "root"
        self.root.mkdir()
        self.commands = SetupCommands()
        self.backend = web.Backend(SINK, {}, self.commands, self.root, state=self.state)

    def test_a_choice_is_remembered_and_reported_back(self):
        self.assertEqual(self.backend.choose_hat({"choice": "respeaker-2mic-hat-v2"}),
                         {"choice": "respeaker-2mic-hat-v2"})
        hardware = self.backend.setup()["hardware"]
        self.assertEqual(hardware["choice"], "respeaker-2mic-hat-v2")
        selected = [option["id"] for option in hardware["options"] if option["selected"]]
        self.assertEqual(selected, ["respeaker-2mic-hat-v2"])
        # A fresh backend reads the file, so the choice is on the device and not
        # only in memory.
        again = web.Backend(SINK, {}, self.commands, self.root, state=self.state)
        self.assertEqual(again.setup()["hardware"]["choice"], "respeaker-2mic-hat-v2")

    def test_a_choice_is_not_an_installation(self):
        self.backend.choose_hat({"choice": "waveshare-wm8960"})
        hardware = self.backend.setup()["hardware"]
        self.assertIsNone(hardware["installed"])
        self.assertIn("separate step", hardware["choice_note"])
        option = next(o for o in hardware["options"] if o["id"] == "waveshare-wm8960")
        self.assertFalse(option["applied"], "a recorded choice was reported as applied")

    def test_choosing_writes_nothing_outside_the_state_directory(self):
        before = sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*"))
        self.backend.choose_hat({"choice": "none"})
        self.assertEqual(sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*")),
                         before, "a choice touched something on the device")
        self.assertEqual(self.commands.calls, [], "a choice ran a command")

    def test_the_choice_file_is_private_and_atomic(self):
        self.backend.choose_hat({"choice": "none"})
        path = self.state / "hardware.json"
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        # Nothing interrupted is left behind: staging is renamed over the file.
        self.assertEqual([p.name for p in self.state.iterdir()], ["hardware.json"])

    def test_an_unknown_or_malformed_choice_is_refused(self):
        for payload in ({"choice": "respeaker-9mic"}, {"choice": 3}, {"choice": None},
                        {}, {"choice": "none", "apply": True}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.backend.choose_hat(payload)
        self.assertFalse((self.state / "hardware.json").exists(), "a refused choice was written")

    def test_an_empty_choice_clears_a_previous_one(self):
        self.backend.choose_hat({"choice": "none"})
        self.assertEqual(self.backend.choose_hat({"choice": ""}), {"choice": None})
        self.assertIsNone(self.backend.setup()["hardware"]["choice"])

    def test_another_retained_field_survives_a_choice(self):
        (self.state / "hardware.json").write_text('{"speaker": "8 ohm 5 W"}\n')
        self.backend.choose_hat({"choice": "respeaker-2mic-hat-v2"})
        stored = json.loads((self.state / "hardware.json").read_text())
        self.assertEqual(stored, {"speaker": "8 ohm 5 W",
                                  "hat_choice": "respeaker-2mic-hat-v2"})

    def test_the_file_this_writes_is_one_the_server_can_start_from(self):
        # The first version of this wrote `hat_choice` into a file whose startup
        # check allowed only the label keys, so the next restart of the service
        # refused the file the server itself had just written. On a device that
        # is a service that stops coming back.
        self.backend.choose_hat({"choice": "respeaker-2mic-hat-v2"})
        stored = json.loads((self.state / "hardware.json").read_text())
        self.assertIsNone(web.metadata_problem(stored), stored)
        # And a retained label alongside it survives both.
        (self.state / "hardware.json").write_text('{"speaker": "8 ohm 5 W"}\n')
        self.backend.choose_hat({"choice": "none"})
        stored = json.loads((self.state / "hardware.json").read_text())
        self.assertIsNone(web.metadata_problem(stored), stored)

    def test_the_startup_check_refuses_a_file_it_cannot_use(self):
        # What it is for: a file the server cannot act on stops startup with a
        # reason, rather than being half-read or tracebacking into a restart loop.
        self.assertIsNone(web.metadata_problem({}))
        self.assertIsNone(web.metadata_problem({"hat": "ReSpeaker 2-Mics Pi HAT v2",
                                                "hat_choice": "none"}))
        for bad, expected in (
                ({"hat_choice": "respeaker-9mic"}, "hat_choice"),
                ({"hat_choice": None}, "hat_choice"),
                ({"hat": "x" * 161}, "hat"),
                ({"speaker": 8}, "speaker"),
                ({"hat": "a", "unknown": "b"}, "unknown"),
                ([], "object")):
            with self.subTest(bad=bad):
                problem = web.metadata_problem(bad)
                self.assertTrue(problem, f"{bad!r} was accepted")
                self.assertIn(expected, problem)

    def test_a_choice_is_never_written_into_a_state_directory_others_can_read(self):
        self.state.chmod(0o755)
        with self.assertRaises(ValueError) as caught:
            self.backend.choose_hat({"choice": "none"})
        self.assertIn("owner-only", str(caught.exception))
        self.assertFalse((self.state / "hardware.json").exists())


class StartupWithAChoiceTests(unittest.TestCase):
    """The service has to start from the file the service wrote.

    The first version of the board choice wrote `hat_choice` into hardware.json
    while the startup check allowed only the label keys, so the next restart
    refused the file: on the lab Pi 5 the unit failed three times and stopped.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="web-start-hat-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "state"
        self.state.mkdir(mode=0o700)
        self.state.chmod(0o700)

    def serve(self):
        argv = ["server.py", "serve", "--state-dir", str(self.state), "--sink", SINK,
                "--auth", "none"]
        with patch.object(sys, "argv", argv), patch.object(web, "DiscoveryCache"), \
                patch.object(web, "Server"), patch("builtins.print"):
            web.main()

    def test_a_recorded_choice_does_not_stop_the_next_start(self):
        web.store_hardware_choice(self.state, "respeaker-2mic-hat-v2")
        self.serve()  # Raises SystemExit if the file it wrote is refused.

    def test_a_file_the_server_cannot_use_stops_it_with_a_reason(self):
        (self.state / "hardware.json").write_text('{"hat_choice": "respeaker-9mic"}\n')
        with self.assertRaises(SystemExit) as caught:
            self.serve()
        self.assertNotEqual(caught.exception.code, 0)


class SetupHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="web-setup-http-", dir="/tmp/opencode")
        root = Path(cls.temp.name)
        (root / "sys/firmware/devicetree/base/hat").mkdir(parents=True)
        (root / "sys/firmware/devicetree/base/hat/product").write_text("ReSpeaker 2-Mics Pi HAT\0")
        (root / "proc/asound").mkdir(parents=True)
        (root / "proc/asound/cards").write_text(
            " 0 [seeed2micvoicec]: simple-card - seeed2micvoicec\n")
        cls.commands = SetupCommands()
        cls.backend = web.Backend(SINK, {"hat": "ReSpeaker 2-Mics Pi HAT v2"}, cls.commands, root)
        cls.server = web.Server(("127.0.0.1", 0), cls.backend, TOKEN, [])
        cls.host = f"127.0.0.1:{cls.server.server_port}"
        cls.server.hosts = frozenset([cls.host])
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def setUp(self):
        self.commands.calls.clear()

    def request(self, method="GET", path="/api/setup", body=None, **headers):
        defaults = {"Host": self.host, "Authorization": "Bearer " + TOKEN}
        if method == "POST":
            defaults.update({"Origin": "http://" + self.host, "Content-Type": "application/json"})
        defaults.update(headers)
        defaults = {name: value for name, value in defaults.items() if value is not None}
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, path, body, defaults)
        response = connection.getresponse()
        data = response.read()
        result = response.status, dict(response.getheaders()), data
        connection.close()
        return result

    def test_setup_requires_the_access_key(self):
        for auth in (None, "", "Bearer wrong"):
            with self.subTest(auth=auth):
                self.assertEqual(self.request(Authorization=auth)[0], 401)

    def test_setup_returns_the_documented_shape(self):
        code, headers, raw = self.request()
        self.assertEqual(code, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("application/json", headers["Content-Type"])
        payload = json.loads(raw)
        self.assertEqual(set(payload), SETUP_KEYS)
        self.assertFalse(payload["writable"])
        self.assertTrue(payload["hardware"]["options"][0]["applied"])

    def test_setup_carries_no_secret_or_state_path(self):
        _, _, raw = self.request()
        text = raw.decode()
        for forbidden in ("access.key", ".config", "/var/lib/debra", "devices-", TOKEN):
            self.assertNotIn(forbidden, text)

    def test_only_get_is_accepted_for_setup(self):
        # Every write path is a 404 rather than a quiet success, so a caller
        # cannot believe a choice was recorded when nothing stores it.
        self.assertEqual(self.request("POST", "/api/setup", "{}")[0], 404)
        self.assertEqual(self.request("POST", "/api/setup/hardware", '{"hat": "none"}')[0], 404)
        self.assertEqual(self.request("POST", "/api/setup/settings", '{"music": "sendspin"}')[0], 404)
        self.assertEqual(self.request("POST", "/api/setup/updates", '{"action": "check"}')[0], 404)
        for method in ("PUT", "DELETE", "PATCH"):
            self.assertEqual(self.request(method, "/api/setup")[0], 501, method)

    def test_a_refused_write_changes_nothing(self):
        before = json.loads(self.request()[2])
        code, _, raw = self.request("POST", "/api/setup/hardware", '{"hat": "none"}')
        self.assertEqual(code, 404)
        self.assertIn("Not found", json.loads(raw)["error"])
        self.assertEqual(json.loads(self.request()[2]), before)
        self.assertFalse(any("pactl" in call for call in self.commands.calls))
        self.assertFalse(any("set-sink" in " ".join(call) for call in self.commands.calls))

    def test_unknown_paths_and_the_host_check_still_apply(self):
        self.assertEqual(self.request(path="/api/setup/")[0], 404)
        self.assertEqual(self.request(path="/api/setup?x=1")[0], 404)
        self.assertEqual(self.request(Host="attacker.test:8787")[0], 403)
        self.assertEqual(self.request(**{"Sec-Fetch-Site": "cross-site"})[0], 403)


class HatChoiceHTTPTests(unittest.TestCase):
    """The one write the Setup card offers, over real HTTP on loopback."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="web-hat-http-", dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.state = base / "state"
        self.state.mkdir(mode=0o700)
        self.state.chmod(0o700)
        root = base / "root"
        root.mkdir()
        self.backend = web.Backend(SINK, {}, SetupCommands(), root, state=self.state)
        self.server = web.Server(("127.0.0.1", 0), self.backend, TOKEN, [])
        self.host = f"127.0.0.1:{self.server.server_port}"
        self.server.hosts = frozenset([self.host])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method="POST", path="/api/setup/hat", body='{"choice": "none"}', **headers):
        defaults = {"Host": self.host, "Authorization": "Bearer " + TOKEN,
                    "Origin": "http://" + self.host, "Content-Type": "application/json"}
        defaults.update(headers)
        defaults = {name: value for name, value in defaults.items() if value is not None}
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, path, body, defaults)
        response = connection.getresponse()
        data = response.read()
        connection.close()
        return response.status, json.loads(data or b"{}")

    def test_a_valid_choice_is_recorded_and_reported(self):
        code, body = self.request(body='{"choice": "respeaker-2mic-hat-v1"}')
        self.assertEqual((code, body), (200, {"choice": "respeaker-2mic-hat-v1"}))
        code, setup = self.request("GET", "/api/setup", None)
        self.assertEqual(code, 200)
        self.assertEqual(setup["hardware"]["choice"], "respeaker-2mic-hat-v1")

    def test_the_choice_needs_the_access_key(self):
        code, _ = self.request(Authorization=None)
        self.assertEqual(code, 401)
        self.assertFalse((self.state / "hardware.json").exists())

    def test_a_cross_site_write_is_refused(self):
        code, _ = self.request(Origin="http://evil.example")
        self.assertEqual(code, 403)
        self.assertFalse((self.state / "hardware.json").exists())

    def test_an_invalid_choice_is_refused_with_a_reason(self):
        code, body = self.request(body='{"choice": "something-else"}')
        self.assertEqual(code, 400)
        self.assertIn("choice", body["error"].lower())
        self.assertFalse((self.state / "hardware.json").exists())

    def test_a_choice_cannot_be_read_with_get(self):
        code, _ = self.request("GET", "/api/setup/hat", None)
        self.assertIn(code, (404, 405))


class PageTests(unittest.TestCase):
    """The page must reference the controls the card claims to have."""

    def setUp(self):
        self.html = (SOURCE / "assets/index.html").read_text()
        self.js = (SOURCE / "assets/app.js").read_text()
        self.css = (SOURCE / "assets/style.css").read_text()

    def test_page_has_the_setup_card_and_its_containers(self):
        for identifier in ("setup", "hat-install", "hat-install-button",
                           "hat-remove-button", "hat-restart-button", "hat-install-state",
                           "hat-enrol-note", "setup-settings", "setup-updates",
                           "setup-hardware-source", "setup-hardware-note", "setup-status"):
            self.assertIn(f'id="{identifier}"', self.html, identifier)
        self.assertIn('href="#setup"', self.html)

    def test_the_install_control_starts_hidden(self):
        # A control that cannot work yet is a promise, and this page keeps that
        # promise in words. The row is in the markup so the renderer can reveal
        # it, and it is hidden until the device says the helper is allowed.
        row = self.html.split('id="hat-install"')[1].split(">")[0]
        self.assertIn("hidden", row)

    def test_the_enrolment_note_names_the_one_command(self):
        # A person who cannot install from the page needs the exact step, not a
        # reference to a guide they have not been given.
        self.assertIn("--enroll", self.html)
        self.assertIn("sudo python3 -B control/setup/hat_install.py", self.html)

    def test_page_loads_the_setup_endpoint(self):
        self.assertIn('"/api/setup"', self.js)
        self.assertIn("loadSetup", self.js)

    def test_planned_choices_are_static_text_with_badges(self):
        # The cardinal rule of this page: a capability that does not exist is
        # text, not a control. A disabled control still promises a shape, still
        # has to explain itself, and any handler on it runs the moment anything
        # enables it. The eight planned rows live in the markup and carry a
        # badge and a sentence; the renderer builds none of them.
        # The three update rows became one sentence and one component-level
        # row: "Check for updates", "Install updates" and "Roll back" all
        # described the same absent mechanism, and none of them was per
        # component, which is where a person looks for it.
        # Choosing a HAT stopped being a planned row: it is a real control now,
        # because recording a choice is something this page can do honestly.
        # Installing that board's driver stopped being a row too: it is a real
        # control, written by a root helper, and it is hidden until it can work
        # rather than shown as a disabled button.
        rows = [
            "Choose the music receiver",
            "Choose whether music becomes quieter or pauses",
            "Choose when component versions change",
            "Each component gets its own update",
        ]
        chunks = self.html.split('<div class="choice">')
        for sentence in rows:
            chunk = next((c for c in chunks if sentence in c), None)
            self.assertIsNotNone(chunk, sentence)
            # The badge must be in the same row as the sentence, not merely
            # somewhere on the page.
            self.assertIn('<span class="badge planned">Planned</span>',
                          chunk.split("</div>")[0], sentence)

    def test_the_setup_card_builds_no_control_except_the_hat_choice(self):
        # The card has exactly one control: the board a person says they fitted.
        # Everything else it shows is text, and a builder for any other control
        # would be the old card returning under a new name.
        for gone in ("hatChoice", "settingChoice", "updateAction", "setupRow",
                     "addReason", "plannedBadge"):
            self.assertNotIn(f"function {gone}", self.js, gone)
        # The switch links elsewhere on the page build anchors; nothing builds a
        # form control. The HAT select is declared in the markup, and only its
        # options are created.
        for built in ('createElement("input")', 'createElement("button")',
                      'createElement("textarea")', 'createElement("form")'):
            self.assertNotIn(built, self.js, built)
        # The select is declared in the markup and filled with options; the
        # options are the only elements the renderer creates for it.
        self.assertIn('id="hat-select"', self.html)
        self.assertIn('el("hat-select")', self.js)
        self.assertIn('createElement("option")', self.js)
        # What the device reports is rendered as evidence, in its own container.
        self.assertIn("function observationRow", self.js)
        self.assertIn("setup-observations", self.js)
        self.assertIn("setup-observations", self.html)

    def test_page_reports_everything_the_payload_can_carry(self):
        for name in ("hatStatus", "observedLine", "observationRow", "renderSetup"):
            self.assertIn(f"function {name}", self.js, name)
        # The page must not hard-code an enabled state for a future action.
        self.assertNotIn("setup-update-check", self.html)
        # And the notice that a planned row cannot be used is still visible
        # without opening anything.
        self.assertIn("Anything marked", self.html)
        self.assertIn("cannot be touched from this page", self.html)


if __name__ == "__main__":
    unittest.main()


class FakeHelper:
    """Stands in for the root helper: records the request, returns an answer."""

    def __init__(self, answer=None, raises=None):
        self.calls = []
        self.answer = {"ok": True, "changed": True,
                       "note": "Written. It applies after the next restart."}
        if answer is not None:
            self.answer = answer
        self.raises = raises

    def __call__(self, request, *, timeout):
        self.calls.append((dict(request), timeout))
        if self.raises is not None:
            raise self.raises
        return dict(self.answer)


class HatInstallTests(unittest.TestCase):
    """Installing a board: the page asks a root helper and writes nothing itself.

    The helper is a fake here, so what these tests hold is the contract between
    the page and that boundary: which board is sent, what is refused before
    anything is asked, and what the card reports about the file it never touches.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="web-hat-install-",
                                                dir="/tmp/opencode")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.state = base / "state"
        self.state.mkdir(mode=0o700)
        self.root = base / "root"
        self.root.mkdir()
        self.socket = base / "control.sock"
        self.socket.write_text("")
        self.use_helper(self.socket)
        self.commands = SetupCommands()
        self.helper = FakeHelper()
        self.put("boot/firmware/config.txt", "[all]\ndtparam=audio=on\n")
        self.put_image()

    def use_helper(self, path):
        patcher = patch.object(web, "HELPER_SOCKET", str(path))
        patcher.start()
        self.addCleanup(patcher.stop)

    def put(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def put_image(self, overlays=("wm8960-soundcard", "respeaker-2mic-v2_0"),
                  modules=("snd-soc-wm8960", "snd-soc-tlv320aic3x")):
        import platform
        for name in overlays:
            self.put("boot/firmware/overlays/%s.dtbo" % name, "dtbo")
        for name in modules:
            self.put("lib/modules/%s/kernel/sound/soc/codecs/%s.ko.xz"
                     % (platform.release(), name), "module")

    def backend(self, helper=None):
        return web.Backend(SINK, {}, self.commands, self.root, state=self.state,
                           helper=helper or self.helper)

    def choose(self, board, backend=None):
        (backend or self.backend()).choose_hat({"choice": board})

    def test_install_sends_the_recorded_choice_and_nothing_else(self):
        backend = self.backend()
        self.choose("respeaker-2mic-hat-v1", backend)
        answer = backend.install_hat({})
        self.assertTrue(answer["changed"])
        self.assertEqual([request for request, _ in self.helper.calls],
                         [{"verb": "install", "board": "respeaker-2mic-hat-v1"}])

    def test_install_without_a_choice_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            self.backend().install_hat({})
        self.assertIn("Choose a board first", str(caught.exception))
        self.assertEqual(self.helper.calls, [], "the helper was asked with no choice")

    def test_install_does_not_accept_a_board_in_the_request(self):
        # The board is the recorded one. A request body that names a board is a
        # caller expecting to choose the overlay, which is not this endpoint.
        backend = self.backend()
        self.choose("respeaker-2mic-hat-v1", backend)
        with self.assertRaises(ValueError):
            backend.install_hat({"board": "waveshare-wm8960"})
        self.assertEqual(self.helper.calls, [])

    def test_the_helpers_refusal_reaches_the_page(self):
        self.helper.raises = web.HelperRefused("This image has no such overlay.")
        backend = self.backend()
        self.choose("respeaker-2mic-hat-v1", backend)
        with self.assertRaises(web.HelperRefused) as caught:
            backend.install_hat({})
        self.assertIn("no such overlay", str(caught.exception))

    def test_a_device_without_the_helper_says_so_instead_of_failing_quietly(self):
        self.use_helper(Path(self.temp.name) / "not-installed")
        backend = self.backend()
        self.choose("respeaker-2mic-hat-v1", backend)
        with self.assertRaises(web.HelperRefused) as caught:
            backend.install_hat({})
        self.assertIn("not running on this device", str(caught.exception))

    def test_install_writes_nothing_on_the_device(self):
        backend = self.backend()
        self.choose("respeaker-2mic-hat-v1", backend)
        before = sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*"))
        backend.install_hat({})
        after = sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*"))
        self.assertEqual(after, before, "the page wrote to the device itself")

    def test_restart_needs_the_word(self):
        backend = self.backend()
        for body in ({}, {"confirm": True}, {"confirm": "yes"}):
            with self.subTest(body=body):
                with self.assertRaises(ValueError):
                    backend.restart_device(body)
        self.assertEqual(self.helper.calls, [])

    def test_restart_asks_for_one_thing(self):
        self.backend().restart_device({"confirm": "restart"})
        self.assertEqual([request for request, _ in self.helper.calls],
                         [{"verb": "reboot"}])

    def test_install_never_asks_for_a_restart(self):
        backend = self.backend()
        self.choose("respeaker-2mic-hat-v1", backend)
        backend.install_hat({})
        self.assertNotIn({"verb": "reboot"}, [request for request, _ in self.helper.calls])

    def test_the_card_reports_what_the_boot_configuration_says(self):
        self.put("boot/firmware/config.txt",
                 "[all]\ndtparam=i2c_arm=on\ndtoverlay=wm8960-soundcard\n")
        hardware = self.backend().setup()["hardware"]
        self.assertEqual(hardware["boot"]["overlays"], ["wm8960-soundcard"])
        self.assertTrue(hardware["boot"]["i2c"])
        by_id = {option["id"]: option for option in hardware["options"]}
        self.assertTrue(by_id["respeaker-2mic-hat-v1"]["configured"])
        self.assertFalse(by_id["respeaker-2mic-hat-v2"]["configured"])

    def test_no_hat_is_configured_when_a_managed_overlay_is_in_the_way(self):
        self.put("boot/firmware/config.txt", "[all]\ndtoverlay=wm8960-soundcard\n")
        by_id = {option["id"]: option for option in
                 self.backend().setup()["hardware"]["options"]}
        self.assertTrue(by_id["none"]["configured"])

    def test_a_commented_overlay_is_not_configured(self):
        self.put("boot/firmware/config.txt", "[all]\n#dtoverlay=wm8960-soundcard\n")
        hardware = self.backend().setup()["hardware"]
        self.assertEqual(hardware["boot"]["overlays"], [])

    def test_an_unreadable_boot_configuration_is_reported_not_invented(self):
        (self.root / "boot/firmware/config.txt").unlink()
        hardware = self.backend().setup()["hardware"]
        self.assertFalse(hardware["boot"]["readable"])
        self.assertIsNone(hardware["boot"]["path"])
        self.assertIsNone(hardware["boot"]["i2c"])

    def test_a_board_this_image_lacks_is_not_installable(self):
        (self.root / "boot/firmware/overlays/respeaker-2mic-v2_0.dtbo").unlink()
        by_id = {option["id"]: option for option in
                 self.backend().setup()["hardware"]["options"]}
        self.assertFalse(by_id["respeaker-2mic-hat-v2"]["installable"]["ok"])
        self.assertIn("respeaker-2mic-v2_0",
                      by_id["respeaker-2mic-hat-v2"]["installable"]["reason"])
        self.assertTrue(by_id["respeaker-2mic-hat-v1"]["installable"]["ok"])

    def test_a_missing_codec_module_is_named(self):
        import platform
        path = (self.root / "lib/modules" / platform.release() /
                "kernel/sound/soc/codecs/snd-soc-wm8960.ko.xz")
        path.unlink()
        by_id = {option["id"]: option for option in
                 self.backend().setup()["hardware"]["options"]}
        self.assertIn("snd-soc-wm8960",
                      by_id["respeaker-2mic-hat-v1"]["installable"]["reason"])

    def test_the_helper_is_reported_by_its_socket(self):
        hardware = self.backend().setup()["hardware"]["helper"]
        self.assertTrue(hardware["present"])
        self.assertEqual(hardware["path"], str(self.socket))
        # Reading the card runs no command at all: reaching the helper is a
        # socket connection, and the card only says whether the socket is there.
        self.assertEqual([call for call in self.commands.calls if "sudo" in call], [])

    def test_a_device_with_no_socket_says_the_helper_is_absent(self):
        self.use_helper(Path(self.temp.name) / "no-such.sock")
        hardware = self.backend().setup()["hardware"]["helper"]
        self.assertFalse(hardware["present"])

    def test_the_helper_is_given_a_budget_inside_the_request(self):
        backend = self.backend()
        self.choose("respeaker-2mic-hat-v1", backend)
        backend.install_hat({})
        _, timeout = self.helper.calls[0]
        self.assertLessEqual(timeout, web.REQUEST_TIMEOUT)


class HatInstallHTTPTests(unittest.TestCase):
    """The three setup writes over HTTP, including the refusal codes."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="web-hat-http-", dir="/tmp/opencode")
        base = Path(cls.temp.name)
        state = base / "state"
        state.mkdir(mode=0o700)
        sock = base / "control.sock"
        sock.write_text("")
        cls.helper_patch = patch.object(web, "HELPER_SOCKET", str(sock))
        cls.helper_patch.start()
        cls.commands = SetupCommands()
        cls.helper = FakeHelper()
        cls.backend = web.Backend(SINK, {}, cls.commands, base / "root", state=state,
                                  helper=cls.helper)
        cls.backend.choose_hat({"choice": "respeaker-2mic-hat-v1"})
        cls.server = web.Server(("127.0.0.1", 0), cls.backend, TOKEN, [])
        cls.host = f"127.0.0.1:{cls.server.server_port}"
        cls.server.hosts = frozenset([cls.host])
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.helper_patch.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.helper.calls.clear()
        self.helper.raises = None

    def post(self, path, body):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request("POST", path, body,
                           {"Host": self.host, "Authorization": "Bearer " + TOKEN,
                            "Origin": "http://" + self.host,
                            "Content-Type": "application/json"})
        response = connection.getresponse()
        data = response.read()
        connection.close()
        return response.status, json.loads(data or b"{}")

    def test_install_is_reachable_and_answers(self):
        code, payload = self.post("/api/setup/hat/install", "{}")
        self.assertEqual(code, 200)
        self.assertTrue(payload["changed"])
        self.assertEqual(self.helper.calls[0][0]["verb"], "install")

    def test_a_refusal_is_409_not_a_broken_request(self):
        # The request was understood and refused. 400 would tell a person their
        # browser sent nonsense, which is not what happened.
        self.helper.raises = web.HelperRefused("This image has no such overlay.")
        code, payload = self.post("/api/setup/hat/install", "{}")
        self.assertEqual(code, 409)
        self.assertIn("no such overlay", payload["error"])

    def test_a_body_with_a_board_is_400(self):
        code, payload = self.post("/api/setup/hat/install", '{"board": "none"}')
        self.assertEqual(code, 400)
        self.assertTrue(payload["error"])

    def test_restart_without_confirmation_is_400(self):
        code, _ = self.post("/api/setup/restart", "{}")
        self.assertEqual(code, 400)
        self.assertEqual(self.helper.calls, [])

    def test_restart_with_confirmation_asks_the_helper(self):
        code, payload = self.post("/api/setup/restart", '{"confirm": "restart"}')
        self.assertEqual(code, 200)
        self.assertEqual(self.helper.calls[0][0], {"verb": "reboot"})

    def test_remove_is_reachable(self):
        code, _ = self.post("/api/setup/hat/remove", "{}")
        self.assertEqual(code, 200)
        self.assertEqual(self.helper.calls[0][0], {"verb": "remove"})

    def test_an_unknown_setup_write_is_404(self):
        self.assertEqual(self.post("/api/setup/hat/reflash", "{}")[0], 404)

    def test_every_setup_write_needs_the_access_key(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request("POST", "/api/setup/hat/install", "{}",
                           {"Host": self.host, "Origin": "http://" + self.host,
                            "Content-Type": "application/json"})
        response = connection.getresponse()
        response.read()
        connection.close()
        self.assertEqual(response.status, 401)
        self.assertEqual(self.helper.calls, [])
