"""Opt-in real Chromium UI check against synthetic data, never device audio.

DEBRA_BROWSER_TEST=1 python -B -m unittest discover -s tests -p test_web_browser.py -v
Uses an already installed Chromium; never installs it or disables its sandbox.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest

from control.web import server as web


CHROMIUM = shutil.which("chromium-browser") or shutil.which("chromium")
FIXTURE = r"""
"use strict";
window.testState = {
  posts: [], percent: 36, muted: false, delay: false, release: null, fail: false,
  dropWrite: false, dropAfterApply: false, reject: false,
  holdWrite: false, releaseWrite: null, failStatus: 0, sinkGone: false,
  probe: new URLSearchParams(location.search).get("probe"), probes: 0, html401: false,
  cpu: {cpu: 12, cpu0: 24},
  noAuth: new URLSearchParams(location.search).get("auth") === "none",
  devices: new URLSearchParams(location.search).get("auth") === "none"
    ? [{name: "debra-3c6b3f", url: "http://debra-3c6b3f.local:8787/", label: "Lab Pi 5"}]
    : []
};
const state = window.testState;
window.fetch = async (path, options) => {
  if (path === "/api/devices") {
    return {ok: true, status: 200, json: async () => ({devices: state.devices})};
  }
  const authorized = Boolean(options.headers && options.headers.Authorization);
  if (path === "/api/status" && !authorized && state.probe) {
    state.probes++;
    if (state.probe === "html") return {ok: true, status: 200, json: async () => { throw new SyntaxError("HTML"); }};
    if (state.probe === "key") return {ok: true, status: 200, json: async () => ({auth: "key"})};
    if (state.probe === "201") return {ok: true, status: 201, json: async () => ({auth: "none"})};
    if (state.probe === "network") throw new Error("network failure");
    if (state.probe === "503" || (state.probe === "retry" && state.probes === 1))
      return {ok: false, status: 503, json: async () => ({error: "transient"})};
  }
  if (!state.noAuth && !authorized) {
    return {ok: false, status: 401, json: async () => {
      if (state.html401) throw new SyntaxError("HTML");
      return {error: "Access key required"};
    }};
  }
  if (options.method === "POST") {
    const body = JSON.parse(options.body);
    state.posts.push({path, body});
    if (state.reject) {
      return {ok: false, status: 400, json: async () => ({error: "fixture rejection"})};
    }
    if (state.dropWrite) throw new Error("response lost before the device applied it");
    if (state.holdWrite) await new Promise(resolve => { state.releaseWrite = resolve; });
    if (path.endsWith("/volume")) state.percent = body.percent;
    if (path.endsWith("/mute")) state.muted = body.muted;
    if (state.dropAfterApply) throw new Error("response lost after the device applied it");
    if (state.failStatus) {
      // Applied, then failed: exactly the case HTTP 503 cannot distinguish.
      return {ok: false, status: state.failStatus, json: async () => ({error: "fixture failure"})};
    }
  }
  const audio = {available: !state.sinkGone, sink: "test", description: "<img src=x onerror=alert(1)>",
    percent: state.percent, muted: state.muted};
  const data = path === "/api/status" ? {
    hostname: "Fixture device", model: "Test board", architecture: "fixture",
    os: "Fixture OS", selected_hardware: {speaker: "<script>untrusted</script>"},
    uptime_s: 600, cpu_percent: state.cpu, memory: {},
    power: {}, wifi: [], zram: [], swap_io: {}, zswap_enabled: null,
    storage: null, temperature_c: null,
    components: [{name: "LVA", active: "active", configuration: "Not yet inspected"}],
    audio, auth: state.noAuth ? "none" : "key"
  } : audio;
  if (state.delay && path === "/api/status") {
    await new Promise(resolve => { state.release = resolve; });
  }
  if (state.fail) throw new Error("offline fixture");
  return {ok: true, status: 200, json: async () => data};
};
"""
CHECK = r"""
"use strict";
const wait = () => new Promise(resolve => setTimeout(resolve, 30));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    await wait();
    assert(!document.getElementById("dashboard").hidden, "dashboard not connected");
    assert(location.hash === "", "key fragment retained");
    assert(sessionStorage.getItem("debra-key"), "key not retained in tab");
    assert(document.getElementById("volume").value === "36", "native volume not displayed");
    assert(!document.querySelector("#output img"), "untrusted description became markup");
    assert(document.getElementById("output").textContent.includes("<img"), "label not literal");
    assert(document.getElementById("output").textContent.includes("test"), "native sink name hidden");
    assert(testState.posts.length === 0, "startup wrote audio");
    const cores = document.querySelectorAll("#cores .core");
    assert(cores.length === 1, "per-core rows not rendered as separate rows");
    assert(cores[0].querySelector(".core-name").textContent === "CPU0", "core label missing");
    assert(cores[0].querySelector(".core-value").textContent === "24%", "core reading missing");
    assert(cores[0].querySelector(".core-bar").style.width === "24%", "core bar does not match the reading");
    testState.cpu = {cpu: 150, cpu0: -1, cpu1: 150, cpu2: NaN, cpu3: Infinity, cpu4: "42"};
    await refresh();
    assert(document.querySelector("#health-values dd").textContent === "150% · out of range", "total CPU out-of-range reading was hidden or clamped");
    const readings = [...document.querySelectorAll("#cores .core")];
    assert(readings[0].querySelector(".core-value").textContent === "-1% · out of range", "negative CPU reading was hidden or clamped");
    assert(readings[0].querySelector(".core-bar").style.width === "0%", "negative CPU bar was not clamped");
    assert(readings[1].querySelector(".core-value").textContent === "150% · out of range", "high CPU reading was hidden or clamped");
    assert(readings[1].querySelector(".core-bar").style.width === "100%", "high CPU bar was not clamped");
    for (const row of readings.slice(2)) {
      assert(row.querySelector(".core-value").textContent === "Unavailable", "invalid CPU reading not unavailable");
      assert(row.querySelector(".core-bar").style.width === "0px", "invalid CPU bar was not empty");
    }
    testState.cpu.cpu = "42";
    await refresh();
    assert(document.querySelector("#health-values dd").textContent === "Unavailable", "invalid total CPU reading not unavailable");
    testState.cpu = {cpu: 12, cpu0: 24};
    const volume = document.getElementById("volume");
    volume.value = "24";
    volume.dispatchEvent(new Event("input"));
    await refresh();
    assert(volume.value === "24", "poll discarded volume preview");
    assert(testState.posts.length === 0, "slider preview wrote audio");
    document.getElementById("apply").click();
    await wait();
    assert(testState.posts.length === 1 && testState.posts[0].body.percent === 24, "apply not explicit");
    assert(testState.muted === false, "volume unexpectedly unmuted or muted");
    volume.value = "23";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("mute").click();
    await wait();
    assert(testState.posts.length === 2 && testState.muted, "mute did not work");
    assert(testState.percent === 24, "mute changed level");
    assert(volume.value === "23", "mute discarded volume preview");
    assert(document.getElementById("volume-value").textContent.includes("not applied"), "preview label lost");
    // Finish this local preview before checking external changes.
    document.getElementById("apply").click();
    await wait();
    assert(testState.posts.length === 3 && testState.percent === 23, "preview did not apply");
    testState.percent = 19;
    await refresh();
    assert(volume.value === "19", "external volume change hidden");
    testState.delay = true;
    const stale = refresh();
    await wait();
    volume.value = "18";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("apply").click();
    await wait();
    testState.delay = false;
    testState.release();
    await stale;
    assert(volume.value === "18", "pre-write poll overwrote successful write");
    // A lost response must never claim the change was not applied.
    testState.dropAfterApply = true;
    volume.value = "31";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("apply").click();
    await wait();
    testState.dropAfterApply = false;
    assert(volume.value === "31", "applied change lost after a dropped response");
    assert(!document.getElementById("volume-value").textContent.includes("not applied"),
           "dropped response claimed the change was not applied");
    assert(document.getElementById("error").textContent === "", "confirmed change still reported as uncertain");
    assert(testState.posts.filter(p => p.body.percent === 31).length === 1, "dropped response replayed the write");
    testState.dropWrite = true;
    volume.value = "42";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("apply").click();
    await wait();
    testState.dropWrite = false;
    assert(volume.value === "42", "preview lost after an unanswered write");
    assert(document.getElementById("volume-value").textContent.includes("device reports 31%"),
           "unanswered write hid the device reading");
    assert(!document.getElementById("volume-value").textContent.includes("not applied"),
           "unanswered write claimed the change was not applied");
    assert(document.getElementById("error").textContent.length > 0, "unanswered write not reported");
    assert(!document.getElementById("apply").disabled, "cannot deliberately retry after an unanswered write");
    assert(testState.posts.filter(p => p.body.percent === 42).length === 1, "unanswered write replayed itself");
    document.getElementById("apply").click();
    await wait();
    assert(testState.percent === 42 && volume.value === "42", "deliberate retry after an unanswered write failed");
    assert(document.getElementById("error").textContent === "", "retry left the unanswered notice behind");
    // A refusal is definite: it must stay readable across the next status poll.
    testState.reject = true;
    volume.value = "55";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("apply").click();
    await wait();
    assert(document.getElementById("error").textContent.includes("fixture rejection"),
           "rejection not shown");
    await refresh();
    assert(document.getElementById("error").textContent.includes("fixture rejection"),
           "HTTP rejection notice was erased by the status refresh");
    assert(volume.value === "55", "rejection discarded the preview");
    assert(document.getElementById("volume-value").textContent.includes("not applied"),
           "rejected write was not marked as not applied");
    assert(testState.posts.filter(p => p.body.percent === 55).length === 1, "rejected write replayed itself");
    testState.reject = false;
    document.getElementById("apply").click();
    await wait();
    assert(testState.percent === 55, "deliberate retry after a rejection failed");
    assert(document.getElementById("error").textContent === "", "successful retry left the rejection notice behind");
    // 503 after the command ran may mean applied: never claim otherwise.
    testState.failStatus = 503;
    volume.value = "24";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("apply").click();
    await wait();
    testState.failStatus = 0;
    assert(testState.percent === 24, "503 fixture did not apply the change");
    assert(volume.value === "24", "applied change hidden after a 503");
    assert(!document.getElementById("volume-value").textContent.includes("not applied"),
           "503 was treated as proof the change was not applied");
    assert(document.getElementById("error").textContent === "", "resolved 503 left an uncertainty notice");
    // An unrelated success must not erase a rejection.
    testState.reject = true;
    volume.value = "30";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("apply").click();
    await wait();
    testState.reject = false;
    assert(document.getElementById("error").textContent.includes("fixture rejection"), "rejection lost");
    const wasMuted = testState.muted;
    document.getElementById("mute").click();
    await wait();
    assert(testState.muted === !wasMuted, "mute did not toggle");
    assert(document.getElementById("error").textContent.includes("fixture rejection"),
           "an unrelated mute cleared the volume rejection");
    assert(document.getElementById("volume-value").textContent.includes("not applied"),
           "rejected volume no longer marked as not applied");
    document.getElementById("apply").click();
    await wait();
    assert(testState.percent === 30, "volume retry after rejection failed");
    assert(document.getElementById("error").textContent === "", "volume retry left the rejection notice");
    // A submitted write must not keep claiming "not applied" while pending.
    testState.holdWrite = true;
    volume.value = "40";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("apply").click();
    await wait();
    assert(document.getElementById("volume-value").textContent.includes("applying"),
           "pending write still claimed not applied");
    assert(volume.disabled, "controls active while a write is pending");
    testState.holdWrite = false;
    testState.releaseWrite();
    await wait();
    assert(testState.percent === 40, "held write did not finish");
    // An unavailable readback is unknown, not proof of non-application.
    testState.sinkGone = true;
    volume.value = "45";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("apply").click();
    await wait();
    assert(!document.getElementById("volume-value").textContent.includes("not applied"),
           "unavailable readback claimed the change was not applied");
    assert(/not confirmed|outcome unknown/.test(document.getElementById("volume-value").textContent),
           "unavailable readback not shown as unknown");
    testState.sinkGone = false;
    await refresh();
    // A settled write must not keep saying "applying…" when the read then fails.
    testState.reject = true;
    testState.fail = true;
    volume.value = "24";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("apply").click();
    await wait();
    testState.reject = false;
    testState.fail = false;
    const settled = document.getElementById("volume-value").textContent;
    assert(!settled.includes("applying"), "settled write still labelled applying after a failed read");
    assert(document.getElementById("error").textContent.includes("fixture rejection"),
           "rejection lost when the follow-up read failed");
    // A failed poll must not hide a rejection the user has not retried.
    testState.fail = true;
    await refresh();
    assert(document.getElementById("error").textContent.includes("fixture rejection"),
           "a failed poll hid the write-rejection evidence");
    assert(document.getElementById("error").textContent.includes("offline fixture"),
           "a failed poll did not report the read failure");
    testState.fail = false;
    await refresh();
    assert(document.getElementById("error").textContent.includes("fixture rejection"),
           "recovery poll lost the rejection");
    // Reconciling an old request must not discard a newer preview.
    testState.dropWrite = true;
    volume.value = "24";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("apply").click();
    await wait();
    testState.dropWrite = false;
    assert(document.getElementById("volume-value").textContent.includes("device reports 45%"),
           "unanswered write did not show the device reading");
    volume.value = "50";
    volume.dispatchEvent(new Event("input"));
    testState.percent = 24;
    await refresh();
    assert(volume.value === "50", "reconciliation discarded a newer preview");
    assert(document.getElementById("volume-value").textContent.startsWith("50%"),
           "newer preview not shown after reconciliation");
    testState.fail = true;
    await refresh();
    assert(volume.disabled && document.getElementById("apply").disabled, "offline controls active");
    testState.fail = false;
    testState.delay = true;
    const pending = refresh();
    await wait();
    document.getElementById("disconnect").click();
    testState.release();
    await pending;
    assert(document.getElementById("dashboard").hidden, "late poll reconnected after disconnect");
    assert(!sessionStorage.getItem("debra-key"), "disconnect retained key");
    assert(testState.posts.length === 17, "read/disconnect restored volume");
    result.textContent = "PASS: browser native-volume UI, preview/apply, mute, external changes, lost responses, rejections, 503 uncertainty, pending and unavailable states, offline and disconnect races";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

CHECK_NOAUTH = r"""
"use strict";
const wait = () => new Promise(resolve => setTimeout(resolve, 30));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    await wait();
    assert(!document.getElementById("pair").hidden, "pairing card not shown without a key");
    assert(document.getElementById("dashboard").hidden, "dashboard opened before choosing");
    assert(!document.getElementById("bypass").hidden,
           "bypass control hidden although the device runs without a key");
    assert(!document.getElementById("bypass-note").hidden, "no warning about the open device");
    assert(document.getElementById("device-links").children.length === 1, "device link not rendered");
    assert(document.getElementById("device-links").children[0].href ===
           "http://debra-3c6b3f.local:8787/", "device link target changed");
    assert(document.getElementById("device-links").children[0].textContent.includes("Configured"),
           "configured device source missing");
    testState.devices.push({name: "new", url: "http://new.local:8787/",
                            label: "<img src=x>", source: "discovered"});
    await loadDevices();
    const discovered = document.getElementById("device-links").children[1];
    assert(discovered.textContent.includes("Discovered"), "discovered device source missing");
    assert(discovered.textContent.includes("<img src=x>"), "discovered label not literal");
    assert(!discovered.querySelector("img"), "discovered label became markup");
    document.getElementById("bypass").click();
    await wait();
    assert(!document.getElementById("dashboard").hidden, "bypass did not connect");
    assert(document.getElementById("pair").hidden, "pairing card stayed after bypass");
    assert(!sessionStorage.getItem("debra-key"), "bypass stored a key");
    assert(testState.posts.length === 0, "bypass wrote audio");
    testState.noAuth = false;
    await refresh();
    assert(document.getElementById("dashboard").hidden, "401 left bypass dashboard open");
    assert(!document.getElementById("pair").hidden, "401 did not restore pairing");
    assert(document.getElementById("bypass").hidden, "401 did not revoke bypass control");
    assert(document.getElementById("bypass-note").hidden, "401 did not revoke bypass warning");
    assert(!bypass, "401 retained active bypass");
    assert(testState.posts.length === 0, "mode change wrote audio");
    result.textContent = "PASS: development bypass and one-stop device links";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

CHECK_KEY = r"""
"use strict";
const wait = () => new Promise(resolve => setTimeout(resolve, 30));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    await wait();
    assert(!document.getElementById("pair").hidden, "pairing card not shown without a key");
    assert(document.getElementById("bypass").hidden,
           "bypass offered although the device still requires a key");
    assert(document.getElementById("bypass-note").hidden, "open-device warning shown in key mode");
    result.textContent = "PASS: key mode offers no bypass";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

CHECK_PROBE = r"""
"use strict";
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    await wait(30);
    const mode = testState.probe;
    if (mode === "retry") {
      assert(document.getElementById("bypass").hidden, "503 showed bypass before retry");
      await wait(300);
      assert(testState.probes >= 2, "503 was not retried");
      assert(!document.getElementById("bypass").hidden, "successful retry did not offer bypass");
    } else if (mode === "none") {
      assert(!document.getElementById("bypass").hidden, "explicit auth none did not offer bypass");
    } else {
      await wait(700);
      assert(document.getElementById("bypass").hidden, `${mode} incorrectly offered bypass`);
      assert(document.getElementById("bypass-note").hidden, `${mode} incorrectly showed warning`);
      assert(testState.probes === 3, `${mode} did not stop after three attempts`);
    }
    assert(testState.posts.length === 0, "probe wrote audio");
    result.textContent = "PASS: explicit auth probe " + mode;
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

CHECK_POST_401 = r"""
"use strict";
const wait = () => new Promise(resolve => setTimeout(resolve, 30));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    await wait();
    document.getElementById("bypass").click();
    await wait();
    assert(!document.getElementById("dashboard").hidden, "bypass did not connect");
    testState.noAuth = false;
    testState.html401 = true;
    document.getElementById("mute").click();
    await wait();
    assert(document.getElementById("dashboard").hidden, "POST 401 left dashboard open");
    assert(document.getElementById("bypass").hidden && !bypass, "POST 401 retained bypass");
    assert(document.getElementById("mute").disabled, "POST 401 left controls enabled");
    assert(testState.posts.length === 0, "unauthorized write reached synthetic backend");
    result.textContent = "PASS: non-JSON POST 401 revokes bypass";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

URL_CASES = {
    "HTTP://DEVICE.Local:08787": "http://device.local:8787/",
    "http://127.0.0.1:1/": "http://127.0.0.1:1/",
    "http://device.local:65535": "http://device.local:65535/",
    "http://device.local:80/": "http://device.local:80/",
    "http://device.local:0/": None,
    "http://device.local:65536/": None,
    "http://device.local:99999/": None,
    " http://device.local:8787/": None,
    "http://device.local:87\t87/": None,
    "http://device.local:8787/\n": None,
    "http://device.local:8787/?": None,
    "http://device.local:8787/#": None,
    "http://user@device.local:8787/": None,
    "http://device.local:8787/path": None,
    "https://device.local:8787/": None,
    "http://127.01.0.1:8787/": None,
    "http://127.1:8787/": None,
    "http://0x7f:8787/": None,
    "http://bad-.local:8787/": None,
    "http://a..local:8787/": None,
}
CHECK_URLS = r"""
"use strict";
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    const cases = CASES;
    for (const [url, expected] of Object.entries(cases)) {
      if (canonicalDeviceUrl(url) !== expected) throw new Error(`URL contract disagrees for ${JSON.stringify(url)}`);
    }
    testState.devices = Object.keys(cases).map(url => ({name: "<img>", label: "<script>", url}));
    await loadDevices();
    const links = document.querySelectorAll("#device-links a");
    if (links.length !== Object.values(cases).filter(Boolean).length) throw new Error("wrong URL link count");
    if (document.querySelector("#device-links img, #device-links script")) throw new Error("device label became markup");
    if (!links[0].textContent.includes("<img>")) throw new Error("device label not literal");
    result.textContent = "PASS: browser URL contract and literal labels";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
""".replace("CASES", json.dumps(URL_CASES))


@unittest.skipUnless(CHROMIUM and os.environ.get("DEBRA_BROWSER_TEST") == "1",
                     "opt-in; requires an already installed Chromium")
class BrowserTests(unittest.TestCase):
    def dump_dom(self, directory, host, suffix, attempts=3):
        """Run headless Chromium, retrying a browser crash but never a verdict.

        A crashed Chromium exits on a signal (a negative code) and leaves no
        PASS in the DOM, so retrying cannot turn a failing check into a
        passing one. Under load its renderer does abort occasionally, and a
        red from that says nothing about the page.
        """
        for attempt in range(1, attempts + 1):
            result = subprocess.run([
                CHROMIUM, "--headless", "--disable-gpu", "--no-first-run",
                "--disable-background-networking", "--disable-component-update",
                "--no-default-browser-check", "--user-data-dir=" + directory,
                "--dump-dom", "--virtual-time-budget=3000",
                "http://" + host + "/" + suffix
            ], capture_output=True, text=True, timeout=30)
            if result.returncode >= 0:
                return result
            if attempt < attempts:
                time.sleep(0.5 * attempt)
        return result

    def run_browser(self, suffix, check_name):
        class Handler(web.Handler):
            def do_GET(self):
                if self.path.split("?")[0] == "/":
                    body = (web.ASSETS / "index.html").read_text().replace(
                        '<script src="/app.js" defer></script>',
                        '<script src="/fixture.js"></script><script src="/app.js" defer></script>'
                        f'<script src="/{check_name}" defer></script>')
                    self.reply(200, body.encode(), "text/html")
                elif self.path in ("/fixture.js", "/check.js", "/check-noauth.js", "/check-key.js", "/check-probe.js", "/check-urls.js", "/check-post-401.js"):
                    script = {"/fixture.js": FIXTURE, "/check.js": CHECK,
                              "/check-noauth.js": CHECK_NOAUTH,
                              "/check-key.js": CHECK_KEY, "/check-probe.js": CHECK_PROBE,
                              "/check-urls.js": CHECK_URLS,
                              "/check-post-401.js": CHECK_POST_401}[self.path]
                    self.reply(200, script.encode(), "text/javascript")
                elif self.path.startswith("/api/"):
                    raise AssertionError("Browser fixture must not reach a real backend")
                else:
                    super().do_GET()

        with tempfile.TemporaryDirectory(prefix="web-browser-", dir="/tmp/opencode") as directory:
            # No backend exists here: even a fixture failure cannot control host audio.
            with web.Server(("127.0.0.1", 0), None, "x" * 40, []) as server:
                server.RequestHandlerClass = Handler
                host = f"127.0.0.1:{server.server_port}"
                server.hosts = frozenset([host])
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    result = self.dump_dom(directory, host, suffix)
                finally:
                    server.shutdown()
                    thread.join()
            self.assertGreaterEqual(
                result.returncode, 0,
                "Chromium crashed on every attempt (signal %d): %s"
                % (-result.returncode, result.stderr[-1500:]))
            self.assertEqual(result.returncode, 0, result.stderr[-2000:])
            self.assertIn('<pre id="browser-test-result">PASS:', result.stdout,
                          result.stdout[-3000:] + result.stderr[-1000:])

    def test_development_bypass_and_device_links(self):
        self.run_browser("?auth=none", "check-noauth.js")

    def test_key_mode_offers_no_bypass(self):
        self.run_browser("?auth=key", "check-key.js")

    def test_html_200_does_not_offer_bypass(self):
        self.run_browser("?auth=none&probe=html", "check-probe.js")

    def test_json_auth_key_does_not_offer_bypass(self):
        self.run_browser("?auth=none&probe=key", "check-probe.js")

    def test_json_auth_none_offers_bypass(self):
        self.run_browser("?auth=none&probe=none", "check-probe.js")

    def test_transient_503_retries_and_offers_bypass(self):
        self.run_browser("?auth=none&probe=retry", "check-probe.js")

    def test_network_error_does_not_offer_bypass(self):
        self.run_browser("?auth=none&probe=network", "check-probe.js")

    def test_non_200_success_does_not_offer_bypass(self):
        self.run_browser("?auth=none&probe=201", "check-probe.js")

    def test_persistent_503_does_not_offer_bypass(self):
        self.run_browser("?auth=none&probe=503", "check-probe.js")

    def test_non_json_post_401_revokes_bypass(self):
        self.run_browser("?auth=none", "check-post-401.js")

    def test_browser_and_server_url_contract_and_literal_labels(self):
        for url, expected in URL_CASES.items():
            with self.subTest(url=url):
                if expected is None:
                    with self.assertRaises(ValueError):
                        web.canonical_device_url(url)
                else:
                    self.assertEqual(web.canonical_device_url(url), expected)
        self.run_browser("?auth=key", "check-urls.js")

    def test_real_browser_interactions_with_no_native_audio(self):
        self.run_browser("#key=" + "x" * 40, "check.js")


if __name__ == "__main__":
    unittest.main()
