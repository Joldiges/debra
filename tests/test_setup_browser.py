"""Opt-in real Chromium drive of the Wi-Fi setup page, against the fake NetworkManager.

    DEBRA_BROWSER_TEST=1 python3 -B -m unittest tests.test_setup_browser -v

Every test starts control/setup/devserver.py — the real portal and the real phase
machine — on an ephemeral port with a temporary state directory, then clicks the
page in an already installed Chromium. The fake NetworkManager is the only
backend: no radio, no root, no real network, no audio.

The portal serves the page straight from the committed assets, so the test cannot
rewrite it the way tests/test_web_browser.py rewrites its own fixture page. A thin
proxy in front of the portal adds one script tag and, for the happy path, drops
the connection after the join reply — which is what the single radio does. The
HTML, setup.js, /api/status, /api/join and the state machine are the real ones.
"""

import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ROOT = Path(__file__).resolve().parent.parent
DEVSERVER = ROOT / "control" / "setup" / "devserver.py"
CHROMIUM = shutil.which("chromium-browser") or shutil.which("chromium")

CHECK = r"""
"use strict";
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
const byId = id => document.getElementById(id);
const shown = id => !byId(id).classList.contains("hidden");
const textOf = id => (byId(id).textContent || "").trim();
const until = async (check, tries = 250, step = 20) => {
  for (let i = 0; i < tries; i++) {
    if (await check()) return true;
    await wait(step);
  }
  return Boolean(await check());
};

// The test watches the page's own requests; it never replaces them, so what the
// browser sends is exactly what the page would send on a device.
const calls = [];
const posts = [];
const realFetch = window.fetch.bind(window);
window.fetch = async (path, options = {}) => {
  const response = await realFetch(path, options);
  const method = (options.method || "GET").toUpperCase();
  calls.push({path: String(path), method, status: response.status});
  if (method === "POST") posts.push({path: String(path), body: JSON.parse(options.body || "{}")});
  return response;
};

const fill = (ssid, psk) => { byId("ssid").value = ssid; byId("psk").value = psk; };

window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    const mode = new URLSearchParams(location.search).get("case");
    const formReady = () => until(() => shown("form-card"));

    if (mode === "form" || mode === "form-gb") {
      assert(await formReady(), "the Wi-Fi form never appeared");
      assert(!shown("loading"), "the page is still showing its loading card");
      assert(!shown("handover") && !shown("failed") && !shown("online"),
             "another screen is showing instead of the form");
      assert(textOf("device-name") === "debra-demo1",
             "the device name is missing: " + JSON.stringify(textOf("device-name")));
      assert(byId("device-name").closest("section").textContent.includes("debra-demo1"),
             "the form does not name the device");
      if (mode === "form-gb") {
        assert(!shown("country"), "the country list is shown although the country is already set");
        assert(byId("country").value === "GB",
               "the saved country is not selected: " + byId("country").value);
        assert(textOf("step-label") === "ONE STEP",
               "the step label still counts two steps: " + JSON.stringify(textOf("step-label")));
        assert(shown("ssid"), "the network name field is hidden");
        result.textContent = "PASS: a known country is not asked for again";
      } else {
        const label = document.querySelector('label[for="country"]');
        assert(label && !label.classList.contains("hidden"), "the country label is hidden");
        assert(shown("country"), "the country list is hidden although the radio needs a country");
        const codes = [...byId("country").options].map(option => option.value);
        assert(codes.includes(""), "the country list has no blank choice");
        assert(codes.includes("GB") && codes.includes("US"),
               "the country list is missing common countries: " + codes.join(","));
        assert([...byId("country").options].some(option => option.textContent === "United Kingdom"),
               "the country names are not readable");
        assert(textOf("step-label") === "STEP 1 OF 2",
               "the step label does not ask for the country: " + JSON.stringify(textOf("step-label")));
        assert(!byId("ssid").classList.contains("hidden")
               && !byId("psk").classList.contains("hidden"), "the network fields are hidden");
        assert(!byId("join").disabled, "the join button is disabled before anything was submitted");
        assert(calls.every(call => call.path !== "/api/join"), "the page submitted without the user");
        assert(textOf("form-error") === "", "the form shows an error before anything was submitted");
        result.textContent = "PASS: the Wi-Fi form, the device name and the country list are on screen";
      }
    } else if (mode === "happy") {
      assert(await formReady(), "the Wi-Fi form never appeared");
      fill("HomeWiFi", "correct horse battery");
      const before = calls.length;
      byId("join").click();
      assert(await until(() => shown("handover")), "the handover screen never appeared");
      const joins = calls.filter(call => call.path === "/api/join");
      assert(joins.length === 1, "expected one join request, saw " + joins.length);
      assert(joins[0].status === 202,
             "the join was only acknowledged after it ran (status " + joins[0].status + ")");
      // Exactly one request — the join — stands between the click and the
      // handover: the page did not wait for a poll to find out what to say.
      assert(calls.length === before + 1,
             "the page made " + (calls.length - before) + " requests before answering: "
             + JSON.stringify(calls.slice(before).map(call => call.path)));
      assert(posts.length === 1 && posts[0].body.ssid === "HomeWiFi",
             "the page did not send the chosen network");
      assert(textOf("join-name") === "HomeWiFi", "the handover does not name the network being joined");
      assert(textOf("hotspot-name") === "Debra-Setup-demo1",
             "the handover does not name the setup network being left");
      assert(/your phone is about to leave this network/i.test(document.body.textContent),
             "the handover does not warn that this page is about to disconnect");
      assert(!shown("form-card") && !shown("failed") && !shown("online"),
             "another screen is showing during the handover");
      // The proxy has now dropped the connection, as the radio does. The page
      // must already be on the handover screen, without a follow-up request.
      await wait(500);
      assert(shown("handover"), "the handover screen did not survive the network going away");
      assert(calls.slice(calls.indexOf(joins[0]) + 1).length === 0,
             "the page needed another request before it could answer");
      result.textContent = "PASS: the page answers with the handover before the access point drops";
    } else if (mode === "bad-psk") {
      assert(await formReady(), "the Wi-Fi form never appeared");
      fill("HomeWiFi", "wrong password");
      byId("join").click();
      assert(await until(() => shown("handover")), "the handover screen never appeared");
      const joins = calls.filter(call => call.path === "/api/join");
      assert(joins.length === 1 && joins[0].status === 202,
             "the join was not acknowledged before it ran");
      // Wait for the device to record the failure, then use the page's own
      // refresh — the same call its 15 s poll makes when the setup network returns.
      const settled = await until(async () => {
        try {
          const response = await realFetch("/api/status", {cache: "no-store"});
          return (await response.json()).phase === "failed";
        } catch { return false; }
      });
      assert(settled, "the device never recorded the failed attempt");
      await load();
      assert(shown("failed"), "the failure screen never appeared");
      assert(!shown("handover") && !shown("form-card") && !shown("online"),
             "another screen is showing with the failure");
      assert(/password was refused/.test(textOf("failed-reason")),
             "the failure reason is not shown: " + JSON.stringify(textOf("failed-reason")));
      byId("retry").click();
      await wait(50);
      assert(shown("form-card"), "the retry button did not return to the form");
      assert(!shown("failed"), "the retry button left the failure on screen");
      assert(textOf("form-error") === "", "the retry left an error message behind");
      assert(textOf("device-name") === "debra-demo1", "the form lost the device name after retry");
      assert(byId("country").options.length > 2, "the form lost the country list after retry");
      // The 15-second poll must not put the failure back over a form being
      // filled in. Calling render() is what that poll does, without the wait.
      const typed = byId("ssid");
      typed.value = "HomeWiFi";
      render();
      assert(shown("form-card") && !shown("failed"),
             "a status poll replaced the form with the old failure");
      assert(typed.value === "HomeWiFi", "a status poll cleared what had been typed");
      assert(byId("psk").value === "", "the retry did not clear the password");
      result.textContent = "PASS: a wrong password ends on the reason and retry returns to the form";
    } else if (mode === "validation") {
      assert(await formReady(), "the Wi-Fi form never appeared");
      fill("HomeWiFi", "short");
      byId("join").click();
      await wait(80);
      assert(/at least 8 characters/.test(textOf("form-error")),
             "a too-short password was not refused in the page: "
             + JSON.stringify(textOf("form-error")));
      assert(calls.every(call => call.path !== "/api/join"),
             "a too-short password was sent to the device");
      assert(shown("form-card") && !shown("handover"), "a refused password still left the form");
      assert(!byId("join").disabled, "the join button stayed disabled after a refused password");
      fill("   ", "correct horse battery");
      byId("join").click();
      await wait(80);
      assert(/name of your Wi-Fi/i.test(textOf("form-error")),
             "an empty network name was not refused in the page: "
             + JSON.stringify(textOf("form-error")));
      assert(calls.every(call => call.path !== "/api/join"),
             "an empty network name was sent to the device");
      assert(shown("form-card") && !shown("handover"), "an empty network name still left the form");
      assert(byId("join").textContent === "Join network",
             "the button is not ready to try again: " + JSON.stringify(byId("join").textContent));
      result.textContent = "PASS: a too-short password and an empty network name are refused without a request";
    } else if (mode === "online") {
      assert(await until(() => shown("online")), "the connected screen never appeared");
      assert(!shown("form-card") && !shown("failed") && !shown("handover") && !shown("loading"),
             "another screen is showing when online");
      assert(textOf("online-ssid") === "HomeWiFi",
             "the network name is missing: " + JSON.stringify(textOf("online-ssid")));
      const rows = [...document.querySelectorAll("#online-values div")].map(row => row.textContent);
      assert(rows.length >= 4, "the connected screen shows no detail rows: " + rows.length);
      assert(rows.some(row => row.includes("Address") && row.includes("192.0.2.40")),
             "the address is not shown: " + rows.join(" | "));
      assert(rows.some(row => row.includes("Device name") && row.includes("debra-demo1")),
             "the device name row is missing: " + rows.join(" | "));
      assert(rows.some(row => row.includes("Baseline") && /captured/.test(row)
                              && !/not captured/.test(row)),
             "the baseline line is missing: " + rows.join(" | "));
      result.textContent = "PASS: the connected screen shows the address and the baseline";
    } else if (mode === "failed") {
      assert(await until(() => shown("failed")), "the failure screen never appeared");
      assert(!shown("form-card") && !shown("online") && !shown("loading"),
             "another screen is showing with the failure");
      assert(textOf("failed-reason") === "Wrong password",
             "the failure reason is not shown: " + JSON.stringify(textOf("failed-reason")));
      assert(!byId("retry").hidden, "the failure screen has no retry control");
      result.textContent = "PASS: the failure screen shows the reason from the device";
    } else {
      throw new Error("unknown case " + JSON.stringify(mode));
    }
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class DevServer:
    """The real devserver on an ephemeral port, killed by PID and never by name."""

    def __init__(self, *arguments):
        self.arguments = list(arguments)
        self.directory = None
        self.port = None
        self.host = None
        self.process = None
        self.output = ""
        self._temp = None

    def __enter__(self):
        self._temp = tempfile.TemporaryDirectory(prefix="setup-browser-", dir="/tmp/opencode")
        self.directory = Path(self._temp.name)
        for _ in range(3):
            self.port = free_port()
            self.host = "127.0.0.1:%d" % self.port
            self.process = subprocess.Popen(
                [sys.executable, "-B", str(DEVSERVER), "--port", str(self.port),
                 "--state-dir", str(self.directory)] + self.arguments,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if self._ready():
                return self
            self.output = self._stop()
        raise AssertionError("the devserver never answered on %s: %s"
                             % (self.host, self.output[-2000:]))

    def _ready(self, timeout=20):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                return False
            connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
            try:
                connection.request("GET", "/api/status", headers={"Host": self.host})
                response = connection.getresponse()
                response.read()
                if response.status == 200:
                    return True
            except OSError:
                time.sleep(0.05)
            finally:
                connection.close()
        return False

    def _stop(self):
        if self.process is None:
            return ""
        if self.process.poll() is None:
            self.process.terminate()
        try:
            output = self.process.communicate(timeout=10)[0] or ""
        except subprocess.TimeoutExpired:
            self.process.kill()
            output = self.process.communicate()[0] or ""
        self.process = None
        return output

    def state(self):
        return json.loads((self.directory / "setup.json").read_text(encoding="utf-8"))

    def __exit__(self, *exception):
        self.output = self._stop()
        self._temp.cleanup()
        return False


class PortalProxy(ThreadingHTTPServer):
    """Serve the portal's own bytes to Chromium, with the check script added.

    `cut_after_join` models the single radio: once the join reply has reached the
    browser, nothing else on this address answers.
    """

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, portal_host, page=None, script=CHECK, cut_after_join=False):
        self.portal_host = portal_host
        self.portal_port = int(portal_host.rsplit(":", 1)[1])
        self.page = page
        self.script = script
        self.cut_after_join = cut_after_join
        self.cut = False
        super().__init__(address, ProxyHandler)


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "DebraSetupBrowserTest/1"
    sys_version = ""

    def log_message(self, fmt, *args):
        pass

    def _portal(self, method, path, body=None, content_type=None):
        headers = {"Host": self.server.portal_host}
        if content_type:
            headers["Content-Type"] = content_type
        connection = http.client.HTTPConnection("127.0.0.1", self.server.portal_port, timeout=20)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return (response.status, response.getheader("Content-Type") or "application/json",
                    response.read())
        finally:
            connection.close()

    def _reply(self, status, payload, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()

    def _gone(self):
        if not self.server.cut:
            return False
        # Close without a reply: the browser sees the access point disappear.
        self.close_connection = True
        return True

    def do_GET(self):
        if self._gone():
            return
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            status, _, payload = self._portal("GET", "/")
            if status != 200:
                self._reply(status, payload, "application/json")
                return
            page = payload if self.server.page is None else self.server.page
            page = page.replace(b"</body>", b'<script src="/check.js"></script></body>')
            self._reply(200, page, "text/html; charset=utf-8")
            return
        if path == "/check.js":
            self._reply(200, self.server.script.encode(), "text/javascript; charset=utf-8")
            return
        if path in ("/setup.js", "/api/status"):
            status, content_type, payload = self._portal("GET", self.path)
            self._reply(status, payload, content_type)
            return
        self._reply(404, b'{"error": "Not found"}', "application/json")

    def do_POST(self):
        if self._gone():
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        status, content_type, payload = self._portal(
            "POST", self.path, body, self.headers.get("Content-Type") or "application/json")
        self._reply(status, payload, content_type)
        if (self.server.cut_after_join and status == 202
                and self.path.split("?")[0] == "/api/join"):
            self.server.cut = True


@unittest.skipUnless(CHROMIUM and os.environ.get("DEBRA_BROWSER_TEST") == "1",
                     "opt-in; requires an already installed Chromium")
class SetupBrowserTests(unittest.TestCase):
    def dump_dom(self, profile, host, query, attempts=3):
        """Run headless Chromium, retrying a browser crash but never a verdict.

        A crashed Chromium exits on a signal (a negative code) and leaves no PASS
        in the DOM, so retrying cannot turn a failing check into a passing one.
        """
        result = None
        for attempt in range(1, attempts + 1):
            result = subprocess.run([
                CHROMIUM, "--headless", "--disable-gpu", "--no-first-run",
                "--disable-background-networking", "--disable-component-update",
                "--no-default-browser-check", "--user-data-dir=" + profile,
                "--dump-dom", "--virtual-time-budget=8000",
                "http://" + host + "/" + query
            ], capture_output=True, text=True, timeout=60)
            if result.returncode >= 0:
                return result
            if attempt < attempts:
                time.sleep(0.5 * attempt)
        return result

    def drive(self, case, *arguments, cut=False, page=None, script=CHECK):
        """Click through one case and return Chromium's output and the device state."""
        with DevServer(*arguments) as portal:
            proxy = PortalProxy(("127.0.0.1", 0), portal.host, page=page,
                                script=script, cut_after_join=cut)
            thread = threading.Thread(target=proxy.serve_forever, daemon=True)
            thread.start()
            try:
                with tempfile.TemporaryDirectory(prefix="setup-chromium-",
                                                 dir="/tmp/opencode") as profile:
                    result = self.dump_dom(profile, "127.0.0.1:%d" % proxy.server_port,
                                           "?case=" + case)
            finally:
                proxy.shutdown()
                proxy.server_close()
                thread.join()
            return result, portal.state()

    @staticmethod
    def verdict(html):
        """The PASS/FAIL line the check wrote, so a failure reads as one sentence."""
        marker = '<pre id="browser-test-result">'
        for line in html.splitlines():
            start = line.find(marker)
            if start >= 0:
                return line[start:].split("</pre>")[0]
        return ""

    def assert_driven(self, case, *arguments, cut=False):
        result, state = self.drive(case, *arguments, cut=cut)
        self.assertGreaterEqual(
            result.returncode, 0,
            "Chromium crashed on every attempt (signal %d): %s"
            % (-result.returncode, result.stderr[-1500:]))
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        verdict = self.verdict(result.stdout)
        self.assertTrue(verdict.startswith('<pre id="browser-test-result">PASS:'),
                        (verdict or result.stdout[-2000:]) + "\n" + result.stderr[-1000:])
        return state

    def test_the_form_shows_the_device_name_and_the_country_list(self):
        state = self.assert_driven("form")
        self.assertEqual(state["phase"], "hotspot")
        self.assertEqual(state["attempts"], 0)

    def test_a_known_country_is_not_asked_for_again(self):
        self.assert_driven("form-gb", "--country", "GB")

    def test_a_valid_network_answers_before_the_access_point_drops(self):
        state = self.assert_driven("happy", cut=True)
        # The click really drove the real state machine, not just the page.
        self.assertEqual(state["phase"], "online")
        self.assertEqual(state["ssid"], "HomeWiFi")
        self.assertEqual(state["address"], "192.0.2.40")
        # A working network clears the failure count, so a device that was
        # retried six times is not one attempt from the cap for ever.
        self.assertEqual(state["attempts"], 0)
        self.assertIsNone(state["hotspot"])
        self.assertIsNotNone(state["baseline"])

    def test_a_wrong_password_ends_on_the_reason_and_retry_returns_to_the_form(self):
        state = self.assert_driven("bad-psk", "--behaviour", "bad-psk")
        self.assertEqual(state["phase"], "failed")
        self.assertIn("password was refused", state["last_error"])
        self.assertEqual(state["attempts"], 1)
        # The setup network must be back, or there is no way to try again.
        self.assertEqual(state["hotspot"]["ssid"], "Debra-Setup-demo1")

    def test_bad_input_is_refused_in_the_page_without_a_request(self):
        self.assert_driven("validation")

    def test_an_online_device_shows_its_address_and_baseline(self):
        state = self.assert_driven("online", "--phase", "online", "--ssid", "HomeWiFi")
        self.assertEqual(state["phase"], "online")
        self.assertEqual(state["address"], "192.0.2.40")

    def test_a_failed_device_shows_the_reason_it_recorded(self):
        state = self.assert_driven("failed", "--phase", "failed", "--error", "Wrong password")
        self.assertEqual(state["phase"], "failed")
        self.assertEqual(state["last_error"], "Wrong password")


if __name__ == "__main__":
    unittest.main()
