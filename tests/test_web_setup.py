"""Offline checks for the Setup card: what it reports, and what it refuses.

Commands are fakes and HTTP is loopback. Nothing here proves a HAT works, a
service is configured, or that a device can be changed: the point of these tests
is that the page tells the truth about what it cannot do.
"""

import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from control.web import server as web


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "control/web"
SINK = "alsa_output.test.stereo-fallback"
TOKEN = "test_" + "a" * 40

# The documented shape. Exact sets on purpose: an added field is a contract
# change and should fail here rather than surprise the page.
SETUP_KEYS = {"writable", "reason", "hardware", "settings", "updates"}
HARDWARE_KEYS = {"detected_hat", "detected_source", "retained_label", "retained_note",
                 "cards", "cards_source", "selectable", "reason", "options"}
OPTION_KEYS = {"id", "label", "summary", "detected", "card", "applied", "caveats"}
CARD_KEYS = {"name", "present"}
SETTING_KEYS = {"id", "label", "summary", "value", "options", "selectable", "reason"}
UPDATE_KEYS = {"available", "reason", "actions"}
ACTION_KEYS = {"id", "label", "enabled", "reason"}


class SetupCommands:
    """Only the probes the setup payload may issue: `systemctl show`."""

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
        self.assertEqual([option["id"] for option in payload["hardware"]["options"]],
                         ["respeaker-2mic-hat-v2", "none"])
        for option in payload["hardware"]["options"]:
            self.assertEqual(set(option), OPTION_KEYS)
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
        self.assertFalse(payload["hardware"]["selectable"])
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
        respeaker, none = hardware["options"]
        self.assertTrue(respeaker["detected"])
        self.assertTrue(respeaker["card"]["present"])
        self.assertTrue(respeaker["applied"])
        # "No HAT" is not detected merely because another HAT is.
        self.assertFalse(none["detected"])
        # An absent option has no card name to look for, so it cannot be applied
        # or ruled out: no sound card is proof of nothing.
        self.assertIsNone(none["card"]["name"])
        self.assertIsNone(none["applied"])

    def test_an_unknown_hat_is_not_claimed_as_the_respeaker(self):
        self.put("/sys/firmware/devicetree/base/hat/product", "Some Other HAT\0")
        self.put("/proc/asound/cards", " 0 [Headphones     ]: bcm2835 - bcm2835\n")
        hardware = self.backend().setup()["hardware"]
        respeaker = hardware["options"][0]
        self.assertFalse(respeaker["detected"])
        self.assertFalse(respeaker["card"]["present"])
        self.assertFalse(respeaker["applied"])

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
            self.assertEqual(call[-1], "--property=Id,LoadState,ActiveState,UnitFileState")
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


class PageTests(unittest.TestCase):
    """The page must reference the controls the card claims to have."""

    def setUp(self):
        self.html = (SOURCE / "assets/index.html").read_text()
        self.js = (SOURCE / "assets/app.js").read_text()
        self.css = (SOURCE / "assets/style.css").read_text()

    def test_page_has_the_setup_card_and_its_containers(self):
        for identifier in ("setup", "setup-hats", "setup-settings", "setup-updates",
                           "setup-hardware-source", "setup-hardware-note", "setup-status"):
            self.assertIn(f'id="{identifier}"', self.html, identifier)
        self.assertIn('href="#setup"', self.html)

    def test_page_loads_the_setup_endpoint(self):
        self.assertIn('"/api/setup"', self.js)
        self.assertIn("loadSetup", self.js)

    def test_planned_controls_are_disabled_and_labelled(self):
        # The three groups each build a disabled control and a visible badge.
        self.assertIn("radio.disabled = true", self.js)
        self.assertIn("select.disabled = setting.selectable !== true", self.js)
        self.assertIn("button.disabled = action.enabled !== true", self.js)
        self.assertIn('badge.className = "badge planned"', self.js)
        self.assertIn('badge.textContent = "Planned"', self.js)

    def test_disabled_controls_stay_readable_and_described(self):
        # A dimmed control with dimmed text would hide the reason it exists.
        self.assertIn(".choice input:disabled", self.css)
        self.assertIn(".badge.planned", self.css)
        self.assertIn("aria-describedby", self.js)
        self.assertIn("addReason", self.js)

    def test_page_renders_every_control_the_payload_can_carry(self):
        for name in ("hatChoice", "settingChoice", "updateAction", "renderSetup"):
            self.assertIn(f"function {name}", self.js, name)
        # The page must not hard-code an enabled state for a future action.
        self.assertNotIn("setup-update-check", self.html)


if __name__ == "__main__":
    unittest.main()
