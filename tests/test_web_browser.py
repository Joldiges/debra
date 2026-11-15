"""Opt-in real Chromium UI check against synthetic data, never device audio.

DEBRA_BROWSER_TEST=1 python -B -m unittest discover -s tests -p test_web_browser.py -v
Uses an already installed Chromium; never installs it or disables its sandbox.
"""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest

from control.web import server as web


CHROMIUM = shutil.which("chromium-browser") or shutil.which("chromium")
FIXTURE = r"""
"use strict";
window.testState = {
  posts: [], percent: 36, muted: false, delay: false, release: null, fail: false,
  dropWrite: false, dropAfterApply: false, reject: false,
  holdWrite: false, releaseWrite: null, failStatus: 0, sinkGone: false,
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
  if (!state.noAuth && !authorized) {
    return {ok: false, status: 401, json: async () => ({error: "Access key required"})};
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
    uptime_s: 600, cpu_percent: {cpu: 12, cpu0: 24}, memory: {},
    power: {}, wifi: [], zram: [], swap_io: {}, zswap_enabled: null,
    storage: null, temperature_c: null,
    components: [{name: "LVA", active: "active", configuration: "Not yet inspected"}],
    audio
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
    document.getElementById("bypass").click();
    await wait();
    assert(!document.getElementById("dashboard").hidden, "bypass did not connect");
    assert(document.getElementById("pair").hidden, "pairing card stayed after bypass");
    assert(!sessionStorage.getItem("debra-key"), "bypass stored a key");
    assert(testState.posts.length === 0, "bypass wrote audio");
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


@unittest.skipUnless(CHROMIUM and os.environ.get("DEBRA_BROWSER_TEST") == "1",
                     "opt-in; requires an already installed Chromium")
class BrowserTests(unittest.TestCase):
    def run_browser(self, suffix, check_name):
        class Handler(web.Handler):
            def do_GET(self):
                if self.path.split("?")[0] == "/":
                    body = (web.ASSETS / "index.html").read_text().replace(
                        '<script src="/app.js" defer></script>',
                        '<script src="/fixture.js"></script><script src="/app.js" defer></script>'
                        f'<script src="/{check_name}" defer></script>')
                    self.reply(200, body.encode(), "text/html")
                elif self.path in ("/fixture.js", "/check.js", "/check-noauth.js", "/check-key.js"):
                    script = {"/fixture.js": FIXTURE, "/check.js": CHECK,
                              "/check-noauth.js": CHECK_NOAUTH,
                              "/check-key.js": CHECK_KEY}[self.path]
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
                    result = subprocess.run([
                        CHROMIUM, "--headless", "--disable-gpu", "--no-first-run",
                        "--disable-background-networking", "--disable-component-update",
                        "--no-default-browser-check", "--user-data-dir=" + directory,
                        "--dump-dom", "--virtual-time-budget=3000",
                        "http://" + host + "/" + suffix
                    ], capture_output=True, text=True, timeout=30)
                finally:
                    server.shutdown()
                    thread.join()
            self.assertEqual(result.returncode, 0, result.stderr[-2000:])
            self.assertIn('<pre id="browser-test-result">PASS:', result.stdout,
                          result.stdout[-3000:] + result.stderr[-1000:])

    def test_development_bypass_and_device_links(self):
        self.run_browser("?auth=none", "check-noauth.js")

    def test_key_mode_offers_no_bypass(self):
        self.run_browser("?auth=key", "check-key.js")

    def test_real_browser_interactions_with_no_native_audio(self):
        self.run_browser("#key=" + "x" * 40, "check.js")


if __name__ == "__main__":
    unittest.main()
