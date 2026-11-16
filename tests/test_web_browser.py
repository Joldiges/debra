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
  longSink: new URLSearchParams(location.search).get("sink") === "long",
  cores: new URLSearchParams(location.search).get("cores") === "unavailable",
  noAuth: new URLSearchParams(location.search).get("auth") === "none",
  devices: new URLSearchParams(location.search).get("auth") === "none"
    ? [{name: "debra-3c6b3f", url: "http://debra-3c6b3f.local:8787/", label: "Lab Pi 5"}]
    : [],
  // The harness page is served from 127.0.0.1, so this hostname matches nothing
  // and the fixture device is correctly offered as "Switch".
  self: {hostname: "fixture-host", port: 8787},
  discovery: {enabled: false, found: 0, seconds_since_scan: null, error: null, refused: []}
};
const state = window.testState;
const setupPayload = () => ({
  writable: false,
  reason: "This page reports what the device is built to do; it cannot change any of it yet.",
  hardware: {
    detected_hat: "ReSpeaker 2-Mics Pi HAT", detected_source: "fixture",
    retained_label: "ReSpeaker 2-Mics Pi HAT v2", retained_note: "fixture",
    cards: ["seeed2micvoicec", "vc4hdmi0"], cards_source: "/proc/asound/cards",
    selectable: false, reason: "Changing the HAT is a device-tree and driver write (A02).",
    options: [
      {id: "respeaker-2mic-hat-v2", label: "ReSpeaker 2-Mics Pi HAT v2",
       summary: "Two microphones and a codec.", detected: true,
       card: {name: "seeed2micvoicec", present: true}, applied: true,
       caveats: ["Positions are an estimate, not a measurement."]},
      {id: "none", label: "No HAT: 3.5 mm jack or USB audio", summary: "Board output.",
       detected: false, card: {name: null, present: null}, applied: null,
       caveats: ["This page cannot tell which output is in use."]}
    ]
  },
  settings: {
    music: {id: "music", label: "Music player", summary: "Which receiver plays music.",
            value: null, selectable: false,
            options: [{id: "sendspin", label: "SendSpin",
                       observed: {user: {unit_found: true, active: "active", enabled: "enabled"},
                                  system: null}},
                      {id: "snapcast", label: "Snapcast (alternative)",
                       observed: {user: null, system: null}}],
            reason: "No music setting is stored on the device yet (C01)."},
    interruption: {id: "interruption", label: "During an announcement", summary: "Duck or pause.",
                   value: null, selectable: false,
                   options: [{id: "duck", label: "Lower the music"},
                             {id: "pause", label: "Pause the music"}],
                   reason: "Not implemented or tested on a device yet (A03)."},
    update_policy: {id: "update-policy", label: "Update policy", summary: "How versions change.",
                    value: null, selectable: false,
                    options: [{id: "pinned", label: "Pinned versions"}],
                    reason: "Nothing on the device can be pinned yet (U01)."}
  },
  updates: {
    available: false,
    reason: "No update mechanism exists, so none of these buttons can do anything.",
    actions: [{id: "check", label: "Check for updates", enabled: false, reason: "No source (U01)."},
              {id: "update", label: "Install updates", enabled: false, reason: "No transaction (U02)."},
              {id: "rollback", label: "Roll back the last change", enabled: false,
               reason: "No snapshot (B02)."}]
  }
});
window.fetch = async (path, options) => {
  if (path === "/api/setup") {
    if (options && options.method && options.method !== "GET") {
      throw new Error("the page must not write to /api/setup");
    }
    return {ok: true, status: 200, json: async () => setupPayload()};
  }
  if (path === "/api/devices") {
    return {ok: true, status: 200,
            json: async () => ({devices: state.devices, self: state.self, discovery: state.discovery})};
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
  const audio = {available: !state.sinkGone,
    sink: state.longSink
      ? "alsa_output.platform_107c800000_sound.stereo_fallback_1234567890abcdef"
      : "test",
    description: "<img src=x onerror=alert(1)>",
    percent: state.percent, muted: state.muted};
  const cores = state.cores
    ? Object.fromEntries([["cpu", 12], ["cpu0", null], ["cpu1", null]])
    : state.cpu;
  const data = path === "/api/status" ? {
    hostname: "Fixture device", model: "Test board", architecture: "fixture",
    os: "Fixture OS", selected_hardware: {speaker: "<script>untrusted</script>"},
    uptime_s: 600, cpu_percent: cores, memory: {},
    power: {}, wifi: [{interface: "wlan0", signal_dbm: -42}], zram: [],
    swap_io: {}, zswap_enabled: null,
    storage: null, temperature_c: 48.2,
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

CHECK_SETUP = r"""
"use strict";
const wait = () => new Promise(resolve => setTimeout(resolve, 30));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    await wait();
    // Record every request the page makes, not only the ones the fixture
    // accepts: an unauthenticated write is still a write attempt, and the
    // fixture would drop it before counting it.
    const sent = [];
    const realFetch = window.fetch;
    window.fetch = (path, options = {}) => {
      sent.push([String(path), String(options && options.method || "GET").toUpperCase()]);
      return realFetch(path, options);
    };
    await loadSetup();
    const hats = [...document.querySelectorAll("#setup-hats .choice")];
    assert(hats.length === 2, "expected two HAT options, saw " + hats.length);
    assert(hats[0].textContent.includes("ReSpeaker 2-Mics Pi HAT v2"), "HAT label missing");
    assert(hats[0].textContent.includes("an ALSA card named seeed2micvoicec is listed"),
           "detected card not reported");
    assert(hats[1].textContent.includes("no sound card of its own to check"),
           "the no-HAT option claimed a card");
    assert(hats.every(row => row.textContent.includes("Positions are an estimate")
                        || row.textContent.includes("cannot tell which output")),
           "a caveat was dropped");
    const radios = [...document.querySelectorAll("#setup-hats input[type=radio]")];
    assert(radios.length === 2 && radios.every(radio => radio.disabled),
           "a HAT choice is selectable although nothing can change it");
    assert(radios.every(radio => !radio.checked), "a HAT was shown as chosen");
    const selects = [...document.querySelectorAll("#setup-settings select")];
    assert(selects.length === 3, "expected three settings, saw " + selects.length);
    assert(selects.every(select => select.disabled), "a setting is selectable");
    assert(selects.every(select => select.value === ""), "a setting showed a value");
    const buttons = [...document.querySelectorAll("#setup-updates button")];
    assert(buttons.length === 3, "expected three update actions, saw " + buttons.length);
    assert(buttons.every(button => button.disabled), "an update action is usable");
    assert(document.querySelectorAll("#setup .badge.planned").length >= 5,
           "planned controls are not labelled");
    for (const control of [...radios, ...selects, ...buttons]) {
      const id = control.getAttribute("aria-describedby");
      assert(id && document.getElementById(id)?.textContent.length > 10,
             "a disabled control does not explain itself");
    }
    assert(document.getElementById("setup-hardware-source").textContent.includes("seeed2micvoicec"),
           "the ALSA card list is not shown");
    assert(document.getElementById("setup-status").textContent.includes("cannot change"),
           "the read-only reason is missing");
    // A disabled control cannot be clicked by a person, but a handler attached
    // to it would run the moment someone made it selectable, and inspecting the
    // `disabled` property cannot see that handler. Dispatch what a person would
    // generate and prove nothing is written.
    const planned = [...document.querySelectorAll("#setup .choice")]
      .filter(row => row.querySelector(".badge.planned"))
      .flatMap(row => [...row.querySelectorAll("input, select, button")]);
    assert(planned.length === 8, "expected eight planned controls, saw " + planned.length);
    const before = testState.posts.length;
    const beforeSent = sent.length;
    for (const control of planned) {
      // `.click()` is a no-op on a disabled control, and so is a real click,
      // so the event is dispatched directly: a handler that exists still runs.
      control.dispatchEvent(new Event("click", {bubbles: true}));
      control.dispatchEvent(new Event("change", {bubbles: true}));
      control.dispatchEvent(new Event("input", {bubbles: true}));
      if (control.form) {
        control.form.dispatchEvent(new Event("submit", {bubbles: true, cancelable: true}));
      }
    }
    await wait();
    await wait();
    const writes = sent.slice(beforeSent).filter(([, method]) => method !== "GET");
    assert(writes.length === 0,
           "a planned control sent a request that is not a read: " + JSON.stringify(writes));
    assert(testState.posts.length === before,
           "a planned control wrote to the device: "
           + JSON.stringify(testState.posts.slice(before)));
    assert(testState.posts.length === 0, "the setup card wrote to the device");
    result.textContent = "PASS: setup card renders disabled choices with reasons "
      + "and writes nothing when they are clicked";
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
    const first = document.getElementById("device-links").children[0];
    assert(first.querySelector("a.switch")?.href === "http://debra-3c6b3f.local:8787/",
           "device switch target changed");
    assert(first.textContent.includes("Configured"), "configured device source missing");
    // The page must not offer to switch to the server it came from.
    testState.self = {hostname: "debra-3c6b3f", port: 8787};
    await loadDevices();
    const own = document.getElementById("device-links").children[0];
    assert(!own.querySelector("a.switch"), "offered a switch to this same device");
    assert(own.textContent.includes("This device"), "this device not marked");
    testState.self = {hostname: "fixture-host", port: 8787};
    await loadDevices();
    testState.devices.push({name: "new", url: "http://new.local:8787/",
                            label: "<img src=x>", source: "discovered"});
    await loadDevices();
    const discovered = document.getElementById("device-links").children[1];
    assert(discovered.textContent.includes("Discovered"), "discovered device source missing");
    assert(discovered.textContent.includes("<img src=x>"), "discovered label not literal");
    assert(!discovered.querySelector("img"), "discovered label became markup");
    // A discovery start failure must explain itself even with no links.
    testState.devices = [];
    testState.discovery = {enabled: false, found: 0, seconds_since_scan: null,
                           error: "Discovery thread could not start (RuntimeError: no threads)"};
    await loadDevices();
    assert(!document.getElementById("devices").hidden,
           "device section hidden although discovery failed");
    assert(document.getElementById("devices-status").textContent.includes("could not start"),
           "discovery start failure reason not shown");
    // A working discovery with no results keeps the status visible too.
    testState.discovery = {enabled: true, found: 0, seconds_since_scan: 4, error: null};
    await loadDevices();
    assert(!document.getElementById("devices").hidden, "empty discovery hid the status");
    assert(document.getElementById("devices-status").textContent.includes("found 0 devices"),
           "empty discovery result not reported");
    // A refused advertisement is named rather than silently dropped.
    testState.discovery = {enabled: true, found: 0, seconds_since_scan: 4, error: null,
                           refused: ["Port 80 is unsupported"]};
    await loadDevices();
    assert(document.getElementById("devices-status").textContent.includes("Port 80"),
           "refused advertisement reason not shown");
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

# Headless Chromium clamps --window-size to 500 CSS px, so the only reliable
# 390 px viewport here is an iframe of exactly that width. The page's own CSP
# forbids framing (frame-ancestors 'none'), which is correct for the product, so
# the test serves the framed copy with `frame-ancestors 'self'` and keeps every
# other directive. The verdict is posted back to the parent, because --dump-dom
# prints only the top-level document.
# The wrapper is served with the product's own CSP, which forbids inline
# style, so the frame's size has to come from a stylesheet. An inline
# `style="width:390px"` was silently dropped and the frame fell back to its
# 300 px default, which would have tested the wrong width without saying so.
PHONE_WRAPPER = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>phone</title>
<link rel="stylesheet" href="/phone.css">
<script src="/phone.js" defer></script></head>
<body>
<iframe id="phone" src="/frame{suffix}"></iframe>
<pre id="browser-test-result"></pre>
</body></html>
"""

PHONE_CSS = """
html, body { margin: 0; }
#phone { width: 390px; height: 844px; border: 0; }
"""

PHONE_SCRIPT = """
// The frame is same-origin, so its verdict is read straight out of its DOM.
// A message would race the parent's listener: the frame's check can finish
// before this script is even parsed.
const frame = document.getElementById("phone");
const copy = () => {
  try {
    const inner = frame.contentDocument && frame.contentDocument.getElementById("browser-test-result");
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

CHECK_PHONE_WIDTH = r"""
"use strict";
const wait = ms => new Promise(resolve => setTimeout(resolve, ms || 30));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    // A 390 px viewport is the phone this page is meant to be usable on. The
    // check is geometric: nothing may be wider than the screen.
    assert(document.getElementById("pair").hidden === false, "pairing card not shown");
    document.getElementById("bypass").click();
    for (let i = 0; i < 60 && document.getElementById("dashboard").hidden; i++) await wait();
    assert(!document.getElementById("dashboard").hidden, "the dashboard never opened");
    const width = document.documentElement.clientWidth;
    assert(width === 390, "the harness did not emulate a 390 px phone: " + width);
    const overflow = [];
    for (const node of document.querySelectorAll("main *, header *")) {
      const box = node.getBoundingClientRect();
      if (box.width === 0 && box.height === 0) continue;
      if (box.right > width + 0.5 || box.left < -0.5) {
        overflow.push((node.id || node.className || node.tagName) + " right=" + box.right);
      }
    }
    assert(overflow.length === 0,
           "content is wider than the 390 px screen: " + overflow.slice(0, 4).join(", "));
    assert(document.documentElement.scrollWidth <= width,
           "the page scrolls sideways: " + document.documentElement.scrollWidth);
    const output = document.getElementById("output");
    assert(output.getBoundingClientRect().right <= width + 0.5,
           "the sink identity runs off the screen");
    // A grid cell with a fixed width does not widen the page; the text just
    // spills over its neighbour. "Unavailable" did exactly that, so the cell
    // itself is measured, not only the document.
    const spilled = [...document.querySelectorAll(".core > *")]
      .filter(node => node.scrollWidth > node.clientWidth + 0.5)
      .map(node => (node.textContent || "").slice(0, 24) + " (+"
                   + (node.scrollWidth - node.clientWidth) + "px)");
    assert(spilled.length === 0, "a core value overflows its cell: " + spilled.join(", "));
    result.textContent = "PASS: a 390 px phone fits the long identity and an unavailable core";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
  // The harness page holds this one in a 390 px iframe, so the verdict has to
  // travel to the parent document that --dump-dom actually prints.
  parent.postMessage({verdict: result.textContent}, location.origin);
});
"""

CHECK_AUTH_BADGE = r"""
"use strict";
const wait = ms => new Promise(resolve => setTimeout(resolve, ms || 30));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    await wait(60);
    const warning = document.getElementById("auth-mode-warning");
    const dashboard = document.getElementById("dashboard");
    assert(document.getElementById("pair").hidden === false, "pairing card not shown");
    assert(warning.hidden, "the warning showed before anything was connected");
    document.getElementById("bypass").click();
    for (let i = 0; i < 60 && dashboard.hidden; i++) await wait();
    assert(!dashboard.hidden, "the keyless dashboard never opened");
    // The pairing card, and its warning, are hidden now. The dashboard has to
    // carry the fact itself, or the live controls look protected.
    assert(document.getElementById("pair").hidden, "the pairing card stayed visible");
    assert(!warning.hidden, "the keyless dashboard shows no warning");
    assert(/access key switched off/i.test(warning.textContent),
           "the dashboard warning does not say the key is off");
    assert(warning.closest("#dashboard"), "the warning is not inside the dashboard");
    assert(testState.posts.length === 0, "opening the dashboard wrote something");
    result.textContent = "PASS: a keyless dashboard keeps its warning visible";
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
    # A browser drops the default port, so a :80 anchor could never satisfy
    # this service's Host check. Refused by both validators.
    "http://device.local:80/": None,
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
CHECK_LABELS = r"""
"use strict";
const wait = () => new Promise(resolve => setTimeout(resolve, 40));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    await wait();
    document.getElementById("bypass").click();
    for (let i = 0; i < 80 && document.getElementById("dashboard").hidden; i++) await wait();
    const health = document.getElementById("health-values");
    assert(health, "the health table never rendered");
    const labels = [...health.querySelectorAll("dt")].map(node => node.textContent);
    assert(labels.some(text => /^Thermal zone 0 \(sensor not identified\)$/.test(text)),
           "the temperature row does not say which zone it reads: " + JSON.stringify(labels));
    assert(!labels.some(text => /^CPU temperature$/.test(text)),
           "the page still claims the sensor is the CPU");
    assert(labels.some(text => /^RAM used \(total − available\) \/ total$/.test(text)),
           "the RAM row does not say the value is derived: " + JSON.stringify(labels));
    assert(labels.some(text => /^Wi-Fi signal \(driver value, unit not established\)$/.test(text)),
           "the Wi-Fi row does not qualify its unit");
    assert(!/dBm/.test(health.textContent),
           "a unit is still claimed for the driver's Wi-Fi number");
    assert(/not proof that speech and music share it/.test(document.body.textContent),
           "the audio card still claims a shared output path");
    result.textContent = "PASS: labels name the source and the estimate, not more";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

CHECK_SELF = r"""
"use strict";
const wait = () => new Promise(resolve => setTimeout(resolve, 40));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    await wait();
    testState.self = {hostname: "fixture-host", port: 8787};
    testState.devices = [
      {name: "exact", label: "Exact", url: "http://fixture-host:8787/"},
      {name: "local", label: "Local", url: "http://fixture-host.local:8787/"},
      {name: "other", label: "Other", url: "http://other-host:8787/"},
      // Same first label, unrelated domain: this is a different device, and a
      // "This device" badge here hides a working Switch link.
      {name: "elsewhere", label: "Elsewhere",
       url: "http://fixture-host.somewhere-else.example:8787/"},
    ];
    await loadDevices();
    const rows = [...document.querySelectorAll("#device-links .device")];
    assert(rows.length === 4, "expected four rows, saw " + rows.length);
    const state = rows.map(row => ({
      url: row.querySelector(".device-address").textContent,
      self: Boolean(row.querySelector(".badge.this-device")),
      link: Boolean(row.querySelector("a.switch")),
    }));
    const find = text => state.find(row => row.url === text);
    for (const own of ["fixture-host:8787", "fixture-host.local:8787"]) {
      const row = find(own);
      assert(row && row.self && !row.link, own + " is not marked as this device");
    }
    const elsewhere = find("fixture-host.somewhere-else.example:8787");
    assert(elsewhere, "the same-prefix device was dropped from the list");
    assert(!elsewhere.self, "a different domain was marked as this device");
    assert(elsewhere.link, "a different device lost its Switch link");
    const other = find("other-host:8787");
    assert(other && !other.self && other.link, "an unrelated device is not switchable");
    result.textContent = "PASS: only the exact host and its .local alias are this device";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

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
    const links = document.querySelectorAll("#device-links a.switch");
    if (links.length !== Object.values(cases).filter(Boolean).length) throw new Error("wrong URL link count");
    if (document.querySelector("#device-links img, #device-links script")) throw new Error("device label became markup");
    const rows = document.querySelectorAll("#device-links .device");
    if (!rows[0].textContent.includes("<img>")) throw new Error("device label not literal");
    result.textContent = "PASS: browser URL contract and literal labels";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
""".replace("CASES", json.dumps(URL_CASES))


@unittest.skipUnless(CHROMIUM and os.environ.get("DEBRA_BROWSER_TEST") == "1",
                     "opt-in; requires an already installed Chromium")
class BrowserTests(unittest.TestCase):
    def dump_dom(self, directory, host, suffix, attempts=3, window=None, budget=3000):
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
                # A visible scrollbar takes 15 px out of the framed viewport, so
                # a 390 px frame laid out at 375 and the width assertion failed
                # for a reason that had nothing to do with the page.
                "--hide-scrollbars",
                *([f"--window-size={window}"] if window else []),
                "--dump-dom", f"--virtual-time-budget={budget}",
                "http://" + host + "/" + suffix
            ], capture_output=True, text=True, timeout=30)
            if result.returncode >= 0:
                return result
            if attempt < attempts:
                time.sleep(0.5 * attempt)
        return result

    def run_browser(self, suffix, check_name, window=None, wrapper=False):
        class Handler(web.Handler):
            def do_GET(self):
                path = self.path.split("?")[0]
                if wrapper and path == "/":
                    self.reply(200, PHONE_WRAPPER.format(suffix=suffix).encode(), "text/html")
                    return
                if wrapper and path == "/phone.js":
                    self.reply(200, PHONE_SCRIPT.encode(), "text/javascript")
                    return
                if wrapper and path == "/phone.css":
                    self.reply(200, PHONE_CSS.encode(), "text/css")
                    return
                framed = wrapper and path == "/frame"
                if framed:
                    # /frame?auth=none is the page itself: the query is what the
                    # fixture reads to know which data to serve. Dropping the
                    # "?" turned it into a 404 and the frame stayed blank.
                    query = self.path.split("?", 1)[1] if "?" in self.path else ""
                    self.path = "/?" + query if query else "/"
                if self.path.split("?")[0] == "/":
                    body = (web.ASSETS / "index.html").read_text().replace(
                        '<script src="/app.js" defer></script>',
                        '<script src="/fixture.js"></script><script src="/app.js" defer></script>'
                        f'<script src="/{check_name}" defer></script>')
                    if framed:
                        # Same directives as the server, except that this copy
                        # may be framed by its own origin. Nothing else is
                        # relaxed: the page under test is the real one.
                        payload = body.encode()
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.send_header("Content-Length", str(len(payload)))
                        self.send_header("Content-Security-Policy",
                                         "default-src 'self'; script-src 'self'; "
                                         "style-src 'self'; connect-src 'self'; "
                                         "frame-ancestors 'self'; base-uri 'none'; "
                                         "form-action 'self'")
                        self.send_header("Cache-Control", "no-store")
                        self.end_headers()
                        self.wfile.write(payload)
                    else:
                        self.reply(200, body.encode(), "text/html")
                elif self.path in ("/fixture.js", "/check.js", "/check-noauth.js",
                                   "/check-key.js", "/check-probe.js", "/check-urls.js",
                                   "/check-post-401.js", "/check-setup.js",
                                   "/check-auth-badge.js", "/check-phone-width.js",
                                   "/check-self.js", "/check-labels.js"):
                    script = {"/fixture.js": FIXTURE, "/check.js": CHECK,
                              "/check-noauth.js": CHECK_NOAUTH,
                              "/check-key.js": CHECK_KEY, "/check-probe.js": CHECK_PROBE,
                              "/check-urls.js": CHECK_URLS,
                              "/check-post-401.js": CHECK_POST_401,
                              "/check-setup.js": CHECK_SETUP,
                              "/check-auth-badge.js": CHECK_AUTH_BADGE,
                              "/check-phone-width.js": CHECK_PHONE_WIDTH,
                              "/check-self.js": CHECK_SELF,
                              "/check-labels.js": CHECK_LABELS}[self.path]
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
                    # A framed run loads the page twice (wrapper and frame) and
                    # the check itself waits for the dashboard, so it needs a
                    # larger virtual-time budget than a plain page.
                    result = self.dump_dom(directory, host, suffix, window=window,
                                           budget=8000 if wrapper else 3000)
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

    def test_a_phone_width_page_holds_a_long_identity(self):
        # 390 px is the phone width the UI is judged at. A long ALSA sink name
        # and an unavailable core value both used to widen the layout.
        self.run_browser("?auth=none&sink=long&cores=unavailable",
                         "check-phone-width.js", wrapper=True)

    def test_a_keyless_dashboard_keeps_its_warning(self):
        self.run_browser("?auth=none", "check-auth-badge.js")

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

    def test_only_the_exact_host_and_its_local_alias_are_this_device(self):
        # Comparing the first label alone marked `fixture-host.<any domain>` as
        # this device, so a real second Debra lost its Switch link.
        self.run_browser("?auth=none", "check-self.js")

    def test_labels_name_the_source_and_the_estimate(self):
        # "CPU temperature" was thermal zone 0, "RAM used" was total minus
        # available, and a signed kernel integer was called dBm. Each label now
        # says what was actually read.
        self.run_browser("?auth=none", "check-labels.js")

    def test_setup_card_renders_disabled_choices_with_reasons(self):
        self.run_browser("#key=" + "x" * 40, "check-setup.js")

    def test_real_browser_interactions_with_no_native_audio(self):
        self.run_browser("#key=" + "x" * 40, "check.js")


if __name__ == "__main__":
    unittest.main()
