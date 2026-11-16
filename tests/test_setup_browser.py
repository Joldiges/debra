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

# The setup page is the first thing a person sees, on a phone, and headless
# Chromium here cannot make a 390 px viewport (it floors the window at 500 CSS
# px). The page is framed at exactly 390 px instead. The portal sends no CSP, so
# nothing has to be relaxed for this; the frame is the real page, served by the
# proxy from the real portal.
PHONE_WRAPPER = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>phone</title>
<link rel="stylesheet" href="/phone.css">
<script src="/phone.js" defer></script></head>
<body>
<iframe id="phone" src="/frame"></iframe>
<pre id="browser-test-result"></pre>
</body></html>
"""

PHONE_CSS = """
html, body { margin: 0; }
#phone { width: 390px; height: 900px; border: 0; }
"""

PHONE_SCRIPT = """
const frame = document.getElementById("phone");
const copy = () => {
  try {
    const inner = frame.contentDocument
      && frame.contentDocument.getElementById("browser-test-result");
    if (inner && inner.textContent) {
      document.getElementById("browser-test-result").textContent = inner.textContent;
    }
  } catch (error) {
    document.getElementById("browser-test-result").textContent = "FAIL: " + error.message;
  }
};
setInterval(copy, 50);
frame.addEventListener("load", copy);
"""

CHECK_PHONE = r"""
"use strict";
const wait = ms => new Promise(resolve => setTimeout(resolve, ms || 40));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    for (let i = 0; i < 60 && document.getElementById("loading").classList.contains("hidden"); i++) {
      await wait();
    }
    await wait(120);
    const width = document.documentElement.clientWidth;
    assert(width === 390, "the frame is not a 390 px phone: " + width);
    const wide = [];
    for (const node of document.querySelectorAll("main *, header *, footer *")) {
      const box = node.getBoundingClientRect();
      if (box.width === 0 && box.height === 0) continue;
      if (box.right > width + 0.5 || box.left < -0.5) {
        wide.push((node.id || node.className || node.tagName) + " right=" + Math.round(box.right));
      }
    }
    assert(wide.length === 0, "content is wider than the 390 px screen: " + wide.slice(0, 4).join(", "));
    assert(document.documentElement.scrollWidth <= width,
           "the setup page scrolls sideways: " + document.documentElement.scrollWidth);
    // The three things a person must reach are all inside the screen.
    for (const id of ["country", "ssid", "psk", "join"]) {
      const box = document.getElementById(id).getBoundingClientRect();
      assert(box.width > 0, id + " is not visible on the phone");
      assert(box.right <= width + 0.5 && box.left >= -0.5, id + " is off the screen");
    }
    result.textContent = "PASS: the setup page fits a 390 px phone";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

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
    } else if (mode === "spaces") {
      // A leading or trailing space is part of the SSID on the air. The page
      // used to trim it, so choosing " Home WiFi " joined a different network.
      assert(await formReady(), "the Wi-Fi form never appeared");
      const typed = " Home WiFi ";
      fill(typed, "correct horse battery");
      byId("join").click();
      assert(await until(() => shown("handover")), "the handover screen never appeared");
      assert(posts.length === 1, "expected one join request, saw " + posts.length);
      assert(posts[0].body.ssid === typed,
             "the network name was rewritten on the way out: "
             + JSON.stringify(posts[0].body.ssid));
      result.textContent = "PASS: a network name keeps its significant spaces";
    } else if (mode === "lost-reply") {
      // The request never gets an answer. That is ambiguous, not a reason to
      // tell the person to leave a setup network the device never touched.
      const before = window.fetch;
      window.fetch = async (path, options = {}) => {
        if (String(path) === "/api/join" && (options.method || "GET").toUpperCase() === "POST") {
          throw new TypeError("Failed to fetch");
        }
        return before(path, options);
      };
      assert(await formReady(), "the Wi-Fi form never appeared");
      fill("HomeWiFi", "correct horse battery");
      byId("join").click();
      assert(await until(() => shown("uncertain")), "the uncertain card never appeared");
      assert(!shown("handover"),
             "a lost reply claimed the access point was about to drop");
      assert(!shown("form-card") && !shown("failed"),
             "another screen is showing after a lost reply");
      assert(textOf("uncertain-ssid") === "HomeWiFi",
             "the uncertain card does not name the network: "
             + JSON.stringify(textOf("uncertain-ssid")));
      assert(textOf("uncertain-network") === "Debra-Setup-demo1",
             "the uncertain card does not name the setup network: "
             + JSON.stringify(textOf("uncertain-network")));
      assert(!byId("join").disabled, "the join button stayed disabled");
      result.textContent = "PASS: a lost reply says it is not known yet, without claiming a handover";
    } else if (mode === "stale-poll") {
      // A status request that started before the submission describes the
      // device as it was before the person pressed the button. Answering it
      // later must not replace the handover card with that older form.
      assert(await formReady(), "the Wi-Fi form never appeared");
      const snapshot = await (await realFetch("/api/status", {cache: "no-store"})).json();
      let release;
      const gate = new Promise(resolve => { release = resolve; });
      const before = window.fetch;
      let held = false;
      window.fetch = async (path, options = {}) => {
        if (!held && String(path) === "/api/status"
            && (options.method || "GET").toUpperCase() === "GET") {
          held = true;
          await gate;
          return new Response(JSON.stringify(snapshot),
                              {status: 200, headers: {"Content-Type": "application/json"}});
        }
        return before(path, options);
      };
      const pending = load();           // starts, and is still unanswered
      fill("HomeWiFi", "correct horse battery");
      byId("join").click();
      assert(await until(() => shown("handover")), "the handover screen never appeared");
      release();                        // the old answer arrives after the submission
      await pending;
      await wait(100);
      assert(shown("handover"),
             "a status answer from before the submission replaced the handover");
      assert(!shown("form-card"), "the older form came back over the handover");
      result.textContent = "PASS: a status answer that started before the submission is ignored";
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
    } else if (mode === "picker") {
      assert(await formReady(), "the Wi-Fi form never appeared");
      assert(shown("ssid-pick"), "the nearby-network picker is hidden although networks were found");
      const options = [...byId("ssid-pick").options].map(option => option.value);
      assert(options[0] === "", "the picker has no empty first option");
      assert(options.includes("HomeWiFi") && options.includes("Cafe"),
             "the scanned networks are missing: " + JSON.stringify(options));
      assert(options.length === 4, "expected three networks and the placeholder, saw " + options.length);
      const cafe = [...byId("ssid-pick").options].find(option => option.value === "Cafe");
      assert(cafe.textContent.includes("no password"),
             "an open network is not marked: " + JSON.stringify(cafe.textContent));
      // Choosing an entry fills the text field; typing still works.
      byId("ssid-pick").value = "HomeWiFi";
      byId("ssid-pick").dispatchEvent(new Event("change"));
      assert(byId("ssid").value === "HomeWiFi",
             "choosing a network did not fill the name field: " + JSON.stringify(byId("ssid").value));
      assert(document.activeElement === byId("psk"), "the password field was not focused after choosing");
      // A hidden network is still joinable by typing it.
      fill("Hidden Network", "correct horse battery");
      byId("join").click();
      const answered = await until(() => posts.length > 0 || shown("handover"));
      assert(answered, "typing a name and joining sent nothing");
      result.textContent = "PASS: the picker offers scanned networks and typing still works";
    } else if (mode === "picker-empty") {
      assert(await formReady(), "the Wi-Fi form never appeared");
      assert(!shown("ssid-pick"),
             "the picker is shown although the scan found nothing");
      assert(!shown("ssid-pick-note"), "the scan note is shown with no scan result");
      assert(shown("ssid"), "the network name field is hidden when there is no picker");
      fill("HomeWiFi", "correct horse battery");
      result.textContent = "PASS: with no scan result the page asks for the name";
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
      // The device page is a different program from this one, and it may not be
      // installed. Calling it the "Setup page" points a person at the page they
      // are already looking at.
      assert(rows.some(row => row.includes("Device page") && row.includes("debra-demo1.local:8787")),
             "the device page address is not named: " + rows.join(" | "));
      assert(!rows.some(row => row.includes("Setup page")),
             "the connected screen still calls the device page the setup page");
      result.textContent = "PASS: the connected screen shows the address and the baseline";
    } else if (mode === "failed") {
      assert(await until(() => shown("failed")), "the failure screen never appeared");
      assert(!shown("form-card") && !shown("online") && !shown("loading"),
             "another screen is showing with the failure");
      assert(textOf("failed-reason") === "Wrong password",
             "the failure reason is not shown: " + JSON.stringify(textOf("failed-reason")));
      assert(!byId("retry").hidden, "the failure screen has no retry control");
      result.textContent = "PASS: the failure screen shows the reason from the device";
    } else if (mode === "country-other") {
      assert(await formReady(), "the Wi-Fi form never appeared");
      byId("country").value = "other";
      byId("country").dispatchEvent(new Event("change"));
      assert(byId("country-code"), "choosing Other did not reveal a code field");
      byId("country-code").value = "is";
      byId("country-code").dispatchEvent(new Event("input"));
      assert(byId("country-code").value === "IS",
             "the typed code was not upper-cased: " + byId("country-code").value);
      // What the 15-second poll does, run directly. It used to rebuild the
      // list from scratch, resetting the select to blank while the code field
      // stayed on screen, so the two disagreed about what would be sent.
      render();
      assert(byId("country").value === "other",
             "the poll reset the country to blank: " + JSON.stringify(byId("country").value));
      assert(byId("country-code") && byId("country-code").value === "IS",
             "the poll lost the typed code");
      fill("HomeWiFi", "correct horse battery");
      byId("join").click();
      assert(await until(() => posts.length > 0 || shown("handover")),
             "nothing was sent after choosing Other");
      assert(posts.length === 1 && posts[0].body.country === "IS",
             "the typed country code was not sent: " + JSON.stringify(posts));
      result.textContent = "PASS: Other and the typed code survive a poll and are sent";
    } else if (mode === "refused") {
      // The device answers with a refusal. That is not a failure screen: the
      // form is still the right thing to show, with the advice on it.
      const before = window.fetch;
      window.fetch = async (path, options = {}) => {
        if (String(path) === "/api/join" && (options.method || "GET").toUpperCase() === "POST") {
          return new Response(
            JSON.stringify({error: "Too many attempts. Wait ten minutes, then try again."}),
            {status: 429, headers: {"Content-Type": "application/json"}});
        }
        return before(path, options);
      };
      assert(await formReady(), "the Wi-Fi form never appeared");
      fill("HomeWiFi", "correct horse battery");
      byId("join").click();
      assert(await until(() => /ten minutes/.test(textOf("form-error"))),
             "the refusal advice was not shown: " + JSON.stringify(textOf("form-error")));
      assert(shown("form-card"), "a refused submission left the form");
      assert(!shown("failed"), "a refused submission showed the failure card");
      assert(byId("ssid").value === "HomeWiFi", "the typed network name was lost");
      // Now the poll: a device that has recorded a failure must not take the
      // form away while the person is reading the advice or typing a retry.
      status.phase = "failed";
      status.last_error = "The Wi-Fi password was refused by the network.";
      render();
      assert(shown("form-card"),
             "the poll replaced the form after a refusal");
      assert(/ten minutes/.test(textOf("form-error")), "the poll wiped the advice");
      assert(byId("ssid").value === "HomeWiFi", "the poll lost the typed network name");
      result.textContent = "PASS: a refusal keeps the form, its advice and what was typed";
    } else if (mode === "baseline-error") {
      assert(await until(() => shown("online")), "the connected screen never appeared");
      assert(!byId("baseline-note").classList.contains("hidden"),
             "the baseline failure is not shown at all");
      assert(/out of disk space/.test(textOf("baseline-note")),
             "the baseline reason is missing: " + JSON.stringify(textOf("baseline-note")));
      assert(/next boot/i.test(textOf("baseline-note")),
             "the page does not say the device tries again");
      const rows = [...document.querySelectorAll("#online-values div")].map(row => row.textContent);
      assert(rows.some(row => row.includes("Baseline") && /not captured/.test(row)),
             "the baseline row claims success: " + rows.join(" | "));
      result.textContent = "PASS: a failed baseline is shown with its reason and the retry";
    } else if (mode === "polling") {
      // The device is mid-join and the page is on the handover card. The only
      // way it can learn that the join worked is by asking again, so the poll
      // must not stop just because the phase is "connecting".
      assert(await until(() => shown("handover")), "the handover screen never appeared");
      window.DEBRA_POLL_MS = 150;
      const before = calls.filter(call => call.path === "/api/status").length;
      const polled = await until(
        () => calls.filter(call => call.path === "/api/status").length > before, 200, 20);
      assert(polled, "the page stopped polling while the device was connecting");
      assert(shown("handover"), "a poll replaced the handover screen");
      result.textContent = "PASS: the page keeps polling while the device is connecting";
    } else if (mode === "open" || mode === "wpa") {
      assert(await formReady(), "the Wi-Fi form never appeared");
      if (mode === "open") {
        assert(shown("open-setup"),
               "an open setup network is not mentioned on the page");
        assert(/development/i.test(textOf("open-setup")),
               "the note does not read as a development warning: "
               + JSON.stringify(textOf("open-setup")));
      } else {
        assert(!shown("open-setup"),
               "a protected setup network is described as open: "
               + JSON.stringify(textOf("open-setup")));
      }
      result.textContent = "PASS: the page says whether the setup network is open";
    } else if (mode === "security-on") {
      // The development build raises an open network. One button turns the
      // password on, without a reinstall: the device answers first, then the
      // radio is cycled, so the page has to say what to reconnect with.
      assert(await formReady(), "the Wi-Fi form never appeared");
      assert(textOf("security-mode") === "Setup network: open (development build)",
             "the page does not say the setup network is open: "
             + JSON.stringify(textOf("security-mode")));
      assert(textOf("security-toggle") === "Require a password",
             "the button does not offer the password: " + JSON.stringify(textOf("security-toggle")));
      const statusesBefore = calls.filter(call => call.path === "/api/status").length;
      // A poll must not be able to replace the handover with the form.
      window.DEBRA_POLL_MS = 150;
      byId("security-toggle").click();
      assert(await until(() => shown("security-handover")), "the change handover never appeared");
      const requests = calls.filter(call => call.path === "/api/security");
      assert(requests.length === 1, "expected one change request, saw " + requests.length);
      assert(requests[0].status === 202,
             "the change was only acknowledged after it ran (status " + requests[0].status + ")");
      const password = textOf("security-password");
      assert(password.length >= 8,
             "the handover does not show the password: " + JSON.stringify(password));
      assert(shown("security-password-line"), "the password line is hidden");
      assert(!shown("security-open-line"), "an open network is still described as having no password");
      assert(textOf("security-ssid") === "Debra-Setup-demo1",
             "the handover does not name the network to reconnect to: "
             + JSON.stringify(textOf("security-ssid")));
      assert(/nothing is rebooted/i.test(document.body.textContent),
             "the handover does not say that nothing is rebooted");
      assert(!shown("form-card") && !shown("failed") && !shown("online"),
             "another screen is showing during the change");
      const polled = await until(
        () => calls.filter(call => call.path === "/api/status").length > statusesBefore, 100, 20);
      assert(polled, "the page stopped polling after the change");
      await wait(400);
      assert(shown("security-handover"),
             "a status poll put the form back over the change handover");
      result.textContent = "PASS: the button turns the password on and the handover survives a poll";
    } else if (mode === "security-off") {
      // The other direction, from a device installed protected: the bypass has
      // to work as well as the protection it bypasses.
      assert(await formReady(), "the Wi-Fi form never appeared");
      assert(textOf("security-mode") === "Setup network: password required",
             "the page does not say the setup network needs a password: "
             + JSON.stringify(textOf("security-mode")));
      assert(textOf("security-toggle") === "Bypass security",
             "the button does not offer the bypass: " + JSON.stringify(textOf("security-toggle")));
      byId("security-toggle").click();
      assert(await until(() => shown("security-handover")), "the change handover never appeared");
      const requests = calls.filter(call => call.path === "/api/security");
      assert(requests.length === 1 && requests[0].status === 202,
             "the bypass was not acknowledged before it ran");
      assert(textOf("security-password") === "",
             "a password was served for an open network: " + JSON.stringify(textOf("security-password")));
      assert(!shown("security-password-line"), "a password line is shown for an open network");
      assert(shown("security-open-line"), "the handover does not say the network will be open");
      assert(textOf("security-ssid") === "Debra-Setup-demo1",
             "the handover does not name the network to reconnect to");
      result.textContent = "PASS: the bypass turns the password off and says the network is open";
    } else if (mode === "security-lost") {
      // The toggle's request never gets an answer. That is ambiguous, not a
      // reason to tell the person the network now demands a password the device
      // may never have set: the device answers before it touches the radio, so
      // a lost reply means the change may not have started at all.
      const before = window.fetch;
      window.fetch = async (path, options = {}) => {
        if (String(path) === "/api/security" && (options.method || "GET").toUpperCase() === "POST") {
          throw new TypeError("Failed to fetch");
        }
        return before(path, options);
      };
      assert(await formReady(), "the Wi-Fi form never appeared");
      byId("security-toggle").click();
      assert(await until(() => shown("security-uncertain")),
             "the uncertain card never appeared for a lost change reply");
      assert(!shown("security-handover"),
             "a lost reply claimed the setup network now requires a password");
      assert(textOf("security-uncertain-network") === "Debra-Setup-demo1",
             "the uncertain card does not name the setup network: "
             + JSON.stringify(textOf("security-uncertain-network")));
      assert(!byId("security-toggle").disabled, "the security button stayed disabled");
      // The page must not latch onto the change. Nothing arrived here, so the
      // next status answer - the device's own word - is still the open mode.
      window.fetch = before;
      render();
      assert(shown("form-card") && !shown("security-uncertain"),
             "the page never went back to the form after a lost reply");
      assert(textOf("security-mode") === "Setup network: open (development build)",
             "the page stopped reporting the mode the device is really in: "
             + JSON.stringify(textOf("security-mode")));
      result.textContent = "PASS: a lost reply says it is not known yet, without claiming the change";
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
        if path == "/phone":
            self._reply(200, PHONE_WRAPPER.encode(), "text/html; charset=utf-8")
            return
        if path == "/phone.css":
            self._reply(200, PHONE_CSS.encode(), "text/css; charset=utf-8")
            return
        if path == "/phone.js":
            self._reply(200, PHONE_SCRIPT.encode(), "text/javascript; charset=utf-8")
            return
        if path == "/frame":
            # The page itself, framed, with the same check script the other
            # cases get. Its own relative requests still go through this proxy.
            status, _, payload = self._portal("GET", "/")
            if status != 200:
                self._reply(status, payload, "application/json")
                return
            page = payload if self.server.page is None else self.server.page
            page = page.replace(b"</body>", b'<script src="/check.js"></script></body>')
            self._reply(200, page, "text/html; charset=utf-8")
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
                # A visible scrollbar inside the frame takes 15 px off the
                # viewport, so a 390 px frame would lay out at 375.
                "--hide-scrollbars",
                "--dump-dom", "--virtual-time-budget=8000",
                "http://" + host + "/" + query
            ], capture_output=True, text=True, timeout=60)
            if result.returncode >= 0:
                return result
            if attempt < attempts:
                time.sleep(0.5 * attempt)
        return result

    def drive(self, case, *arguments, cut=False, page=None, script=CHECK, phone=False):
        """Click through one case, returning Chromium's output, state and files.

        `phone=True` opens the wrapper that holds the real page in a 390 px frame
        instead of the page at the browser's own width.

        The two security files are read while the state directory still exists:
        the password is never in the state, so the only way to compare what the
        page showed with what the device kept is to read it here.
        """
        with DevServer(*arguments) as portal:
            proxy = PortalProxy(("127.0.0.1", 0), portal.host, page=page,
                                script=script, cut_after_join=cut)
            thread = threading.Thread(target=proxy.serve_forever, daemon=True)
            thread.start()
            try:
                with tempfile.TemporaryDirectory(prefix="setup-chromium-",
                                                 dir="/tmp/opencode") as profile:
                    result = self.dump_dom(profile, "127.0.0.1:%d" % proxy.server_port,
                                           "phone" if phone else "?case=" + case)
            finally:
                proxy.shutdown()
                proxy.server_close()
                thread.join()
            files = {}
            for name in ("setup-security", "setup-secret"):
                path = portal.directory / name
                if path.exists():
                    files[name] = path.read_text(encoding="utf-8").strip()
            return result, portal.state(), files

    @staticmethod
    def verdict(html):
        """The PASS/FAIL line the check wrote, so a failure reads as one sentence."""
        marker = '<pre id="browser-test-result">'
        for line in html.splitlines():
            start = line.find(marker)
            if start >= 0:
                return line[start:].split("</pre>")[0]
        return ""

    def assert_verdict(self, result):
        self.assertGreaterEqual(
            result.returncode, 0,
            "Chromium crashed on every attempt (signal %d): %s"
            % (-result.returncode, result.stderr[-1500:]))
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        verdict = self.verdict(result.stdout)
        self.assertTrue(verdict.startswith('<pre id="browser-test-result">PASS:'),
                        (verdict or result.stdout[-2000:]) + "\n" + result.stderr[-1000:])

    def assert_driven(self, case, *arguments, cut=False):
        result, state, _files = self.drive(case, *arguments, cut=cut)
        self.assert_verdict(result)
        return state

    def assert_driven_with_files(self, case, *arguments, cut=False):
        result, state, files = self.drive(case, *arguments, cut=cut)
        self.assert_verdict(result)
        return state, files

    def test_a_development_build_says_the_setup_network_is_open(self):
        # The dev server runs the open mode: the development bypass means there
        # is no password to type. A person who is not told that will hunt for
        # one, so the page has to say it before they try.
        self.assert_driven("open")

    def test_a_secured_setup_network_is_not_described_as_open(self):
        # The same page, installed the other way. Without this the "open" line
        # could be shown always and both tests would still pass.
        self.assert_driven("wpa", "--setup-security", "wpa")

    def test_the_button_turns_the_password_on_and_the_device_keeps_it(self):
        # The bypass is what Debra runs today; this is how the protection it
        # bypasses stays reachable without a reinstall.
        state, files = self.assert_driven_with_files("security-on")
        self.assertEqual(state["phase"], "hotspot")
        self.assertIsNone(state["last_error"])
        self.assertEqual(files.get("setup-security"), "wpa",
                         "the chosen mode was not written down")
        password = files.get("setup-secret") or ""
        self.assertGreaterEqual(len(password), 8,
                                "no setup password was created for the protected network")
        self.assertNotIn(password, json.dumps(state),
                         "the setup password reached the state record")

    def test_the_button_bypasses_the_password_on_a_protected_device(self):
        # The other direction, from a device installed protected. Without it the
        # bypass could be dead code that only the open default hides.
        state, files = self.assert_driven_with_files("security-off",
                                                     "--setup-security", "wpa")
        self.assertEqual(state["phase"], "hotspot")
        self.assertIsNone(state["last_error"])
        self.assertEqual(files.get("setup-security"), "none",
                         "the bypass was not written down")

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

    def test_a_scanned_network_can_be_chosen_instead_of_typed(self):
        self.assert_driven("picker", cut=True)

    def test_with_no_scan_result_the_page_asks_for_the_name(self):
        self.assert_driven("picker-empty", "--behaviour", "scan-fails")

    def test_choosing_other_country_survives_a_poll(self):
        self.assert_driven("country-other")

    def test_a_refused_submission_keeps_the_form_and_its_advice(self):
        self.assert_driven("refused")

    def test_a_failed_baseline_is_shown_with_its_reason(self):
        self.assert_driven("baseline-error", "--phase", "online",
                           "--baseline-error", "The device is out of disk space")

    def test_the_page_keeps_polling_while_connecting(self):
        self.assert_driven("polling", "--phase", "connecting")

    def test_a_network_name_keeps_its_significant_spaces(self):
        state = self.assert_driven("spaces")
        self.assertEqual(state["ssid"], " Home WiFi ",
                         "the device recorded a different network name than was typed")

    def test_a_lost_reply_is_not_reported_as_a_handover(self):
        self.assert_driven("lost-reply")

    def test_a_lost_change_reply_does_not_claim_the_password_was_turned_on(self):
        # The discriminating assertions live in the browser case (`security-lost`):
        # the uncertain card must be shown, the handover must not, and the next
        # status answer must still report the mode the device is really in. This
        # wrapper only runs that case and checks the device was left alone.
        state = self.assert_driven("security-lost")
        self.assertIsNone(state.get("last_error"))
        self.assertNotEqual(state.get("security"), "wpa",
                            "a reply that never arrived changed the stored mode")

    def test_a_status_answer_from_before_the_submission_is_ignored(self):
        self.assert_driven("stale-poll")

    def test_bad_input_is_refused_in_the_page_without_a_request(self):
        self.assert_driven("validation")

    def test_a_phone_width_setup_page_fits(self):
        # This page is read on a phone, at the moment the household Wi-Fi is
        # being set up. Nothing about it was measured at a phone width.
        html = self.drive("phone", script=CHECK_PHONE, phone=True)[0].stdout
        self.assertIn("PASS:", self.verdict(html), self.verdict(html))

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
