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
  holdSetup: false, releaseSetup: null, failSetup: false,
  holdAllSetup: false, heldSetup: [],
  // Every request the page makes, recorded at the entry point it calls. This
  // fixture script runs before app.js, so startup attempts are included, not
  // only what arrives after a check has installed a wrapper of its own.
  requests: [],
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
// `?hold=setup` holds the page's first Setup read, so a check can prove what
// happens to a valid answer that is already in flight when something else
// changes. The read is held once, not for every request.
if (new URLSearchParams(location.search).get("hold") === "setup") state.holdSetup = true;
const setupPayload = () => ({
  writable: false,
  reason: "This page reports what the device is built to do; it cannot change any of it yet.",
  hardware: {
    detected_hat: "ReSpeaker 2-Mics Pi HAT", detected_source: "fixture",
    retained_label: "ReSpeaker 2-Mics Pi HAT v2", retained_note: "fixture",
    cards: ["seeed2micvoicec", "vc4hdmi0"], cards_source: "/proc/asound/cards",
    selectable: false, reason: "Changing the HAT is a device-tree and driver write (A02).",
    // The shape the server really sends: the alternative is not a board the
    // EEPROM can name, so the server reports no verdict for it.
    options: [
      {id: "respeaker-2mic-hat-v2", label: "ReSpeaker 2-Mics Pi HAT v2",
       summary: "Two microphones and a codec.", detected: true,
       card: {name: "seeed2micvoicec", present: true}, applied: true,
       caveats: ["Positions are an estimate, not a measurement."]},
      {id: "none", label: "No HAT: 3.5 mm jack or USB audio", summary: "Board output.",
       detected: null, card: {name: null, present: null}, applied: null,
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
  // Recorded here, before any of the branches below, so a request is counted
  // even when the fixture refuses it later. Startup attempts are included
  // because this script runs before app.js.
  state.requests.push({path: String(path), method: String(options && options.method || "GET").toUpperCase()});
  if (path === "/api/setup") {
    if (options && options.method && options.method !== "GET") {
      throw new Error("the page must not write to /api/setup");
    }
    // One read is held, not every read: a check that holds a read, disconnects
    // and re-pairs needs the new session's read to answer.
    if (state.holdSetup) {
      state.holdSetup = false;
      await new Promise(resolve => { state.releaseSetup = resolve; });
    }
    // `holdAllSetup` holds every read and keeps its resolver, so a check can
    // hold both an old session's read and the new session's read, then release
    // them in either order.
    if (state.holdAllSetup) {
      await new Promise(resolve => { state.heldSetup.push(resolve); });
    }
    if (state.failSetup) throw new Error("old setup failure");
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
    // Every request, not only the accepted posts: the fixture records them from
    // before app.js runs, so a startup write cannot hide behind the counter.
    const startupWrites = testState.requests.filter(request => request.method !== "GET");
    assert(startupWrites.length === 0,
           "startup sent a request that is not a read: " + JSON.stringify(startupWrites));
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
    assert(document.getElementById("audio-notice").textContent === "", "confirmed change still reported as uncertain");
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
    assert(document.getElementById("audio-notice").textContent.length > 0, "unanswered write not reported");
    assert(document.getElementById("audio-notice").closest("#audio"),
           "the write outcome is not inside the Audio card it belongs to");
    assert(document.getElementById("audio-notice").getBoundingClientRect().height > 0,
           "the write outcome has no visible box");
    assert(!document.getElementById("apply").disabled, "cannot deliberately retry after an unanswered write");
    assert(testState.posts.filter(p => p.body.percent === 42).length === 1, "unanswered write replayed itself");
    document.getElementById("apply").click();
    await wait();
    assert(testState.percent === 42 && volume.value === "42", "deliberate retry after an unanswered write failed");
    assert(document.getElementById("audio-notice").textContent === "", "retry left the unanswered notice behind");
    // A refusal is definite: it must stay readable across the next status poll.
    testState.reject = true;
    volume.value = "55";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("apply").click();
    await wait();
    assert(document.getElementById("audio-notice").textContent.includes("fixture rejection"),
           "rejection not shown");
    await refresh();
    assert(document.getElementById("audio-notice").textContent.includes("fixture rejection"),
           "HTTP rejection notice was erased by the status refresh");
    assert(volume.value === "55", "rejection discarded the preview");
    assert(document.getElementById("volume-value").textContent.includes("not applied"),
           "rejected write was not marked as not applied");
    assert(testState.posts.filter(p => p.body.percent === 55).length === 1, "rejected write replayed itself");
    testState.reject = false;
    document.getElementById("apply").click();
    await wait();
    assert(testState.percent === 55, "deliberate retry after a rejection failed");
    assert(document.getElementById("audio-notice").textContent === "", "successful retry left the rejection notice behind");
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
    assert(document.getElementById("audio-notice").textContent === "", "resolved 503 left an uncertainty notice");
    // An unrelated success must not erase a rejection.
    testState.reject = true;
    volume.value = "30";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("apply").click();
    await wait();
    testState.reject = false;
    assert(document.getElementById("audio-notice").textContent.includes("fixture rejection"), "rejection lost");
    const wasMuted = testState.muted;
    document.getElementById("mute").click();
    await wait();
    assert(testState.muted === !wasMuted, "mute did not toggle");
    assert(document.getElementById("audio-notice").textContent.includes("fixture rejection"),
           "an unrelated mute cleared the volume rejection");
    assert(document.getElementById("volume-value").textContent.includes("not applied"),
           "rejected volume no longer marked as not applied");
    document.getElementById("apply").click();
    await wait();
    assert(testState.percent === 30, "volume retry after rejection failed");
    assert(document.getElementById("audio-notice").textContent === "", "volume retry left the rejection notice");
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
    assert(document.getElementById("audio-notice").textContent.includes("fixture rejection"),
           "rejection lost when the follow-up read failed");
    // A failed poll must not hide a rejection the user has not retried.
    testState.fail = true;
    await refresh();
    assert(document.getElementById("audio-notice").textContent.includes("fixture rejection"),
           "a failed poll hid the write-rejection evidence");
    assert(document.getElementById("error").textContent.includes("offline fixture"),
           "a failed poll did not report the read failure");
    assert(!document.getElementById("error").textContent.includes("fixture rejection"),
           "the read failure region repeated the write outcome that has its own notice");
    testState.fail = false;
    await refresh();
    assert(document.getElementById("audio-notice").textContent.includes("fixture rejection"),
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
    // The two rows describe one EEPROM string and must not contradict each
    // other. The alternative is not a board the EEPROM can name, so "the EEPROM
    // does not name it" was the exact opposite of the row above.
    assert(hats[0].textContent.includes("the exact model and revision are not established"),
           "the ReSpeaker row dropped its qualification: " + hats[0].textContent);
    assert(!/exact v2|identified by the HAT EEPROM as/i.test(hats[0].textContent),
           "the ReSpeaker row claims an identification the EEPROM cannot make");
    assert(!/does not name a ReSpeaker/i.test(hats[1].textContent),
           "the No-HAT row states the negation of the ReSpeaker row's evidence");
    assert(/gives no family verdict for this row/.test(hats[1].textContent),
           "the No-HAT row does not say what is actually known about it");
    // What the EEPROM can and cannot say is stated once, above the rows.
    const eepromNotes = [...document.querySelectorAll("#setup p")]
      .filter(node => /can name a board family only/.test(node.textContent));
    assert(eepromNotes.length === 1, "the EEPROM limitation is stated "
           + eepromNotes.length + " times instead of once");
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
    // The fixture's own log, written at the entry point the page calls, is the
    // one a captured pre-wrapper `fetch` cannot evade. The label sweep below
    // already reads it; this sweep read only the late wrapper, so a handler
    // holding the function from before that wrapper was installed wrote and
    // nothing here noticed.
    const beforeEarly = testState.requests.length;
    for (const control of planned) {
      // `.click()` is a no-op on a disabled control, and so is a real click,
      // so the event is dispatched directly: a handler that exists still runs.
      control.dispatchEvent(new Event("click", {bubbles: true}));
      control.dispatchEvent(new Event("change", {bubbles: true}));
      control.dispatchEvent(new Event("input", {bubbles: true}));
      // A phone generates touch events, and a delegated `touchend` handler on
      // a planned control is a write path this sweep could not see until the
      // r10 review built one and it survived every web test.
      control.dispatchEvent(new Event("touchstart", {bubbles: true}));
      control.dispatchEvent(new Event("touchend", {bubbles: true}));
      if (control.form) {
        control.form.dispatchEvent(new Event("submit", {bubbles: true, cancelable: true}));
      }
    }
    await wait();
    await wait();
    const writes = sent.slice(beforeSent).filter(([, method]) => method !== "GET");
    assert(writes.length === 0,
           "a planned control sent a request that is not a read: " + JSON.stringify(writes));
    const earlyWrites = testState.requests.slice(beforeEarly)
      .filter(request => request.method !== "GET");
    assert(earlyWrites.length === 0,
           "a planned control sent a request the page's own log saw but the "
           + "wrapper did not: " + JSON.stringify(earlyWrites));
    assert(testState.posts.length === before,
           "a planned control wrote to the device: "
           + JSON.stringify(testState.posts.slice(before)));
    // A disabled control cannot be clicked by a person, but the <label> that
    // names it is enabled and can be touched, and the label's own click reaches
    // handlers on its row and on the whole card. Row-level and delegated label
    // handlers both survived a control-only sweep, so the labels themselves are
    // activated: the browser's own click plus the touch events a thumb makes.
    const labels = [...document.querySelectorAll("#setup .choice-head label")];
    assert(labels.length === 5, "expected five setup labels, saw " + labels.length);
    for (const label of labels) {
      const control = label.htmlFor ? document.getElementById(label.htmlFor) : null;
      assert(control && control.disabled,
             "a setup label points at a control that is not disabled: " + label.textContent);
    }
    const beforeLabels = testState.requests.length;
    for (const label of labels) {
      label.click();
      label.dispatchEvent(new MouseEvent("click", {bubbles: true, cancelable: true}));
      label.dispatchEvent(new Event("touchstart", {bubbles: true}));
      label.dispatchEvent(new Event("touchend", {bubbles: true}));
    }
    await wait();
    await wait();
    const labelWrites = testState.requests.slice(beforeLabels).filter(r => r.method !== "GET");
    assert(labelWrites.length === 0,
           "touching a planned label sent a request that is not a read: "
           + JSON.stringify(labelWrites));
    assert(testState.posts.length === before,
           "touching a planned label wrote to the device: "
           + JSON.stringify(testState.posts.slice(before)));
    assert(selects.every(select => select.disabled), "touching a label made a setting selectable");
    assert(testState.posts.length === 0, "the setup card wrote to the device");
    // The planned task list is this page's statement of what the appliance
    // will do. It has no control at all, so the lies available are a row that
    // looks usable, a missing badge, or a reason that does not say what it
    // waits on.
    const tasks = [...document.querySelectorAll("#planned-actions .choice")];
    assert(tasks.length === 5, "expected five planned tasks, saw " + tasks.length);
    assert(tasks.every(row => row.querySelector(".badge.planned")),
           "a planned task is not labelled");
    const taskControls = tasks.flatMap(row =>
      [...row.querySelectorAll("input, select, button, a")]);
    assert(taskControls.length === 0,
           "a planned task offers a control: " + taskControls.length);
    assert(tasks.every(row => (row.querySelector(".choice-detail")?.textContent || "").length > 40),
           "a planned task does not say why it is unavailable");
    assert(tasks.every(row => /roadmap [A-Z][0-9]/.test(row.textContent)),
           "a planned task does not cite what it waits on");
    assert(/nothing here can be used/.test(document.getElementById("planned").textContent),
           "the planned section does not say the rows cannot be used");
    result.textContent = "PASS: setup card renders disabled choices with reasons "
      + "and writes nothing when they or their labels are touched, and the planned "
      + "tasks are labelled with what each waits on and offer no control";
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
    // A beginner is asked for a key with no statement of where it comes from.
    // The hint must say the page cannot show it and must not claim a setup
    // screen hands it over yet.
    const hint = document.getElementById("key-source");
    assert(hint && !hint.hidden, "no hint about where the access key comes from");
    assert(/never shows it/.test(hint.textContent), "the hint does not say the page cannot show the key");
    assert(/planned, not built/.test(hint.textContent),
           "the hint promises a setup screen that does not exist");
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
    // Nothing the page did before this check ran may have been a write: the
    // fixture records requests from before app.js executes.
    const startupWrites = testState.requests.filter(request => request.method !== "GET");
    assert(startupWrites.length === 0,
           "startup sent a request that is not a read: " + JSON.stringify(startupWrites));
    assert(testState.requests.some(request => request.path === "/api/status"),
           "the recorder saw no status read, so its silence proves nothing");
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
    // Nothing the page did before this check ran may have been a write. The
    // fixture records requests from before app.js executes, so a startup write
    // is visible here even though the key prompt stayed up.
    const startupWrites = testState.requests.filter(request => request.method !== "GET");
    assert(startupWrites.length === 0,
           "startup sent a request that is not a read: " + JSON.stringify(startupWrites));
    assert(testState.requests.some(request => request.path === "/api/status"),
           "the recorder saw no status read, so its silence proves nothing");
    result.textContent = "PASS: key mode offers no bypass and writes nothing at startup";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

CHECK_TOKEN_NONE = r"""
"use strict";
const wait = () => new Promise(resolve => setTimeout(resolve, 30));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    // The tab holds a key and the device reports `auth:none`. This is the mode
    // where a "write when a key is present" handler would be most likely to
    // slip through: the dashboard opens, so nothing looks wrong.
    for (let i = 0; i < 60 && !testState.requests.some(r => r.path === "/api/setup"); i++) await wait();
    await wait();
    assert(!document.getElementById("dashboard").hidden, "the token-connected dashboard never opened");
    assert(!document.getElementById("auth-mode-warning").hidden,
           "a keyless device opened with no warning although a key is held");
    assert(sessionStorage.getItem("debra-key"), "the tab key was not kept");
    const startupWrites = testState.requests.filter(request => request.method !== "GET");
    assert(startupWrites.length === 0,
           "a token-present keyless session sent a write at startup: "
           + JSON.stringify(startupWrites));
    assert(testState.requests.some(request => request.path === "/api/setup"),
           "the recorder saw no setup read, so its silence proves nothing");
    assert(testState.posts.length === 0, "startup reached the synthetic write path");
    result.textContent = "PASS: a token-present keyless session opened and wrote nothing at startup";
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
    // The pairing card is the first screen a person sees, so it is measured
    // before the dashboard is opened, not after.
    const pairWide = [...document.querySelectorAll("#pair *")]
      .filter(node => {
        const box = node.getBoundingClientRect();
        return (box.width || box.height) && (box.right > document.documentElement.clientWidth + 0.5 || box.left < -0.5);
      })
      .map(node => (node.id || node.tagName) + " right=" + Math.round(node.getBoundingClientRect().right));
    assert(pairWide.length === 0, "the pairing card is wider than the screen: " + pairWide.join(", "));
    document.getElementById("bypass").click();
    for (let i = 0; i < 60 && document.getElementById("dashboard").hidden; i++) await wait();
    assert(!document.getElementById("dashboard").hidden, "the dashboard never opened");
    const width = document.documentElement.clientWidth;
    assert(width === 390, "the harness did not emulate a 390 px phone: " + width);
    // A phone lays the page out at 980 px when the viewport meta tag is gone;
    // the page would still "fit" because the browser shrank it.
    const meta = document.querySelector('meta[name="viewport"]');
    assert(meta && /width=device-width/.test(meta.getAttribute("content") || ""),
           "the page has no device-width viewport");
    // The fixture has to hold the long content this test claims to lay out, or
    // a shorter value would pass and prove nothing about long identities.
    const output = document.getElementById("output");
    assert(/stereo_fallback_1234567890abcdef/.test(output.textContent),
           "the fixture served no long sink name: " + output.textContent);
    assert([...document.querySelectorAll("#cores .core-value")].some(node =>
             node.textContent === "Unavailable"),
           "the fixture has no unavailable core value");
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
    // Text cut off inside its own box is unreadable even when the box fits the
    // screen: a fixed height, or a nowrap line clipped at 80 px, stayed inside
    // the 390 px measurement. Form controls are skipped because a select shows
    // a truncated option by design, not prose.
    const clipped = [];
    for (const node of document.querySelectorAll("main *, header *")) {
      if (/^(INPUT|SELECT|OPTION|TEXTAREA|BUTTON)$/.test(node.tagName)) continue;
      if (!(node.textContent || "").trim()) continue;
      const inside = node.getBoundingClientRect();
      if (!inside.width || !inside.height) continue;
      if (node.scrollHeight > node.clientHeight + 1 || node.scrollWidth > node.clientWidth + 1) {
        clipped.push((node.id || node.className || node.tagName) + " shows "
                     + node.clientWidth + "x" + node.clientHeight + " of "
                     + node.scrollWidth + "x" + node.scrollHeight);
      }
    }
    assert(clipped.length === 0, "an element clips its own text: " + clipped.slice(0, 4).join(", "));
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
    // Present but styled as body text is not a warning: it must be visibly
    // separate from the paragraphs around it.
    const style = getComputedStyle(warning);
    assert(style.backgroundColor !== "rgba(0, 0, 0, 0)", "the warning has no band");
    assert(style.borderTopWidth !== "0px", "the warning has no border");
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
CHECK_AUDIO_NOTICE = r"""
"use strict";
const wait = ms => new Promise(resolve => setTimeout(resolve, ms || 30));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  try {
    document.getElementById("bypass").click();
    for (let i = 0; i < 80 && document.getElementById("dashboard").hidden; i++) await wait();
    // The Setup card is what makes the page long: without it the global #error
    // line would be near Audio anyway and the geometry proves nothing.
    for (let i = 0; i < 80 && !document.querySelector("#setup-settings .choice"); i++) await wait();
    const width = document.documentElement.clientWidth, height = window.innerHeight;
    assert(width === 390, "the harness did not emulate a 390 px phone: " + width);
    const apply = document.getElementById("apply");
    // Scroll Audio into view the way a person following the section link does,
    // then apply a volume the device never answers.
    document.getElementById("audio").scrollIntoView();
    const volume = document.getElementById("volume");
    testState.dropWrite = true;
    volume.value = "42";
    volume.dispatchEvent(new Event("input"));
    apply.click();
    const notice = document.getElementById("audio-notice");
    for (let i = 0; i < 80 && !notice.textContent; i++) await wait();
    testState.dropWrite = false;
    assert(notice.textContent.includes("did not confirm this volume change"),
           "the unanswered volume change was not explained: " + notice.textContent);
    assert(notice.closest("#audio"), "the notice is not inside the Audio card");
    const applyBox = apply.getBoundingClientRect();
    const noticeBox = notice.getBoundingClientRect();
    assert(applyBox.top >= 0 && applyBox.bottom <= height,
           "Apply is not on screen after scrolling to Audio: "
           + [applyBox.top, applyBox.bottom, height].join(", "));
    assert(noticeBox.height > 0, "the notice has no visible box");
    assert(noticeBox.top >= 0 && noticeBox.bottom <= height,
           "the notice is outside the phone viewport: "
           + [noticeBox.top, noticeBox.bottom, height].join(", "));
    assert(noticeBox.top >= applyBox.top && noticeBox.top - applyBox.bottom < 180,
           "the notice is not beside the Apply button: "
           + [applyBox.bottom, noticeBox.top].join(" -> "));
    // The point of moving it: the global line that used to carry this text is
    // more than one screen away from the control it explains.
    const errorBox = document.getElementById("error").getBoundingClientRect();
    assert(errorBox.top > height || errorBox.bottom < 0,
           "the global error line is on screen too, so this proves nothing");
    assert(document.getElementById("error").textContent === "",
           "the write outcome was also written to the distant error line");
    result.textContent = "PASS: an unanswered volume change is explained beside Apply at 390 px";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

CHECK_SETUP_CURRENT = r"""
"use strict";
const wait = () => new Promise(resolve => setTimeout(resolve, 30));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  const rows = () => ["setup-hats", "setup-settings", "setup-updates"]
    .map(id => document.getElementById(id).children.length);
  try {
    // `?hold=setup` holds the page's first Setup read, the one start() makes.
    for (let i = 0; i < 80 && document.getElementById("dashboard").hidden; i++) await wait();
    assert(!document.getElementById("dashboard").hidden, "the dashboard never opened");
    for (let i = 0; i < 40 && !testState.releaseSetup; i++) await wait();
    assert(testState.releaseSetup, "the first setup read was not held");
    assert(rows().every(count => count === 0),
           "the setup rows rendered before the read settled: " + rows());
    // An audio write advances the page's revision. It says nothing about the
    // device's build choices, so the answer already in flight is still valid.
    const volume = document.getElementById("volume");
    volume.value = "21";
    volume.dispatchEvent(new Event("input"));
    document.getElementById("apply").click();
    await wait();
    assert(testState.posts.length === 1 && testState.percent === 21,
           "the audio write did not run while Setup was held: " + JSON.stringify(testState.posts));
    testState.releaseSetup();
    for (let i = 0; i < 40 && !rows().every(count => count > 0); i++) await wait();
    assert(rows().every(count => count > 0),
           "an audio write discarded a valid setup answer: " + rows());
    assert(document.getElementById("setup-status").textContent.includes("cannot change"),
           "the read-only reason is missing: "
           + document.getElementById("setup-status").textContent);
    result.textContent = "PASS: an audio write does not discard a Setup answer already in flight";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

CHECK_DISCONNECT_WRITE = r"""
"use strict";
const wait = () => new Promise(resolve => setTimeout(resolve, 30));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  // An exception thrown inside the write handler's `finally` becomes an
  // unhandled rejection: nothing displays it, so only a listener sees it.
  const failures = [];
  window.addEventListener("unhandledrejection", event => {
    failures.push(String((event.reason && event.reason.message) || event.reason));
  });
  window.addEventListener("error", event => failures.push(String(event.message)));
  try {
    await wait();
    document.getElementById("bypass").click();
    for (let i = 0; i < 80 && document.getElementById("dashboard").hidden; i++) await wait();
    assert(!document.getElementById("dashboard").hidden, "bypass did not connect");
    assert(failures.length === 0, "connecting raised: " + JSON.stringify(failures));
    // Hold the write, disconnect while it is unanswered, then let it settle.
    // Disconnect sets the current audio state to null, and the repaint in the
    // write's `finally` used to read it unconditionally.
    testState.holdWrite = true;
    document.getElementById("apply").click();
    for (let i = 0; i < 40 && !testState.releaseWrite; i++) await wait();
    assert(testState.releaseWrite, "the held audio write never started");
    document.getElementById("disconnect").click();
    testState.releaseWrite();
    await wait();
    await wait();
    assert(failures.length === 0,
           "an audio write settling after Disconnect raised: " + JSON.stringify(failures));
    assert(document.getElementById("dashboard").hidden, "the dashboard reopened after disconnect");
    assert(document.getElementById("pair").hidden === false, "the pairing card did not return");
    assert(document.getElementById("volume").disabled,
           "the volume control is still live after disconnect");
    result.textContent = "PASS: an audio write settling after Disconnect raises nothing and stays disconnected";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

CHECK_SETUP_RACE = r"""
"use strict";
const wait = () => new Promise(resolve => setTimeout(resolve, 30));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  const rows = () => ["setup-hats", "setup-settings", "setup-updates"]
    .map(id => document.getElementById(id).children.length);
  try {
    await wait();
    document.getElementById("bypass").click();
    for (let i = 0; i < 80 && !document.querySelector("#setup-settings .choice"); i++) await wait();
    assert(rows().every(count => count > 0), "the setup rows never rendered: " + rows());
    // Hold one Setup response across a Disconnect and release it afterwards.
    testState.holdSetup = true;
    const pending = loadSetup();
    for (let i = 0; i < 40 && !testState.releaseSetup; i++) await wait();
    assert(testState.releaseSetup, "the held setup read never started");
    document.getElementById("disconnect").click();
    assert(rows().every(count => count === 0), "disconnect did not clear the setup rows: " + rows());
    testState.holdSetup = false;
    testState.releaseSetup();
    await pending;
    await wait();
    assert(rows().every(count => count === 0),
           "a late setup response repopulated the rows after disconnect: " + rows());
    assert(document.getElementById("setup-status").textContent === "",
           "a late setup response wrote its status after disconnect: "
           + document.getElementById("setup-status").textContent);
    assert(document.getElementById("setup-hardware-source").textContent === "",
           "a late setup response repopulated the hardware source line");
    assert(document.getElementById("dashboard").hidden, "a late setup response reopened the dashboard");
    assert(!sessionStorage.getItem("debra-key"), "disconnect retained the key");
    assert(testState.posts.length === 0, "the setup race wrote to the device");
    // A read left pending by the old session must not block the new session's
    // read. One global loading flag did, and because the old answer is
    // correctly discarded, the card stayed empty until the 15-second poll.
    document.getElementById("bypass").click();
    for (let i = 0; i < 80 && !document.querySelector("#setup-settings .choice"); i++) await wait();
    assert(rows().every(count => count > 0), "re-pairing did not render the setup rows: " + rows());
    testState.holdSetup = true;
    const stale = loadSetup();
    for (let i = 0; i < 40 && !testState.releaseSetup; i++) await wait();
    assert(testState.releaseSetup, "the held setup read never started");
    document.getElementById("disconnect").click();
    assert(rows().every(count => count === 0), "disconnect did not clear the setup rows: " + rows());
    document.getElementById("bypass").click();
    for (let i = 0; i < 80 && !document.querySelector("#setup-settings .choice"); i++) await wait();
    assert(rows().every(count => count > 0),
           "a new session could not read while an old read was pending: " + rows());
    testState.releaseSetup();
    await stale;
    await wait();
    assert(rows().every(count => count > 0),
           "the old session's answer cleared the new session's rows: " + rows());
    testState.releaseSetup();
    await stale;
    await wait();
    assert(rows().every(count => count > 0),
           "the old session's answer cleared the new session's rows: " + rows());
    // The error arm of the same guard. The success arm above passes even when
    // only the success path is bound to the session, so a held failure is its
    // own case: it must not write the old device's reason after a disconnect.
    testState.holdSetup = true;
    testState.failSetup = true;
    const failing = loadSetup();
    for (let i = 0; i < 40 && !testState.releaseSetup; i++) await wait();
    assert(testState.releaseSetup, "the held failing setup read never started");
    document.getElementById("disconnect").click();
    testState.releaseSetup();
    await failing;
    await wait();
    assert(document.getElementById("setup-status").textContent === "",
           "a late setup failure wrote its reason after disconnect: "
           + document.getElementById("setup-status").textContent);
    assert(testState.posts.length === 0, "the setup error arm wrote to the device");
    result.textContent = "PASS: a late setup response cannot repopulate cleared rows after disconnect, "
      + "and neither a pending read nor a late failure blocks or paints a new session";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

CHECK_SETUP_MARKER = r"""
"use strict";
const wait = () => new Promise(resolve => setTimeout(resolve, 30));
const assert = (ok, message) => { if (!ok) throw new Error(message); };
window.addEventListener("load", async () => {
  const result = document.createElement("pre");
  result.id = "browser-test-result";
  document.body.append(result);
  const rows = () => ["setup-hats", "setup-settings", "setup-updates"]
    .map(id => document.getElementById(id).children.length);
  try {
    await wait();
    document.getElementById("bypass").click();
    for (let i = 0; i < 80 && !document.querySelector("#setup-settings .choice"); i++) await wait();
    assert(rows().every(count => count > 0), "the setup rows never rendered: " + rows());
    // Hold both reads: the old session's, and the new session's after a
    // re-pair. Releasing only the old one is the case the supplied re-pair test
    // cannot see, because it lets the new read finish first. A `finally` that
    // clears the marker without checking ownership then lets a third read start
    // while the second is still in flight.
    testState.holdAllSetup = true;
    const oldRead = loadSetup();
    for (let i = 0; i < 40 && testState.heldSetup.length < 1; i++) await wait();
    assert(testState.heldSetup.length === 1, "the old session's read was not held");
    document.getElementById("disconnect").click();
    assert(rows().every(count => count === 0), "disconnect did not clear the setup rows: " + rows());
    document.getElementById("bypass").click();
    for (let i = 0; i < 40 && testState.heldSetup.length < 2; i++) await wait();
    assert(testState.heldSetup.length === 2,
           "the new session's read was not held: " + testState.heldSetup.length);
    testState.heldSetup[0]();
    await oldRead;
    await wait();
    assert(rows().every(count => count === 0),
           "the old session's answer painted the cleared rows: " + rows());
    // Do not await this call: with the marker cleared, it starts a read that
    // `holdAllSetup` holds, so awaiting it would hang before the assertion that
    // says what went wrong. Count Setup requests specifically.
    const setupReads = () => testState.requests.filter(r => r.path === "/api/setup").length;
    const beforeThird = setupReads();
    const third = loadSetup();
    await wait();
    await wait();
    const started = setupReads() - beforeThird;
    assert(started === 0,
           "an old read settling cleared the new session's marker and let a third "
           + "read start: " + started);
    if (started > 0) {
      // Release the extra reads so the rest of the check still runs; the
      // assertion above is the failure that should be reported.
      testState.heldSetup.slice(2).forEach(resolve => resolve());
      await third;
    }
    // The new read still owns the marker, and releasing it paints the rows.
    testState.heldSetup[1]();
    for (let i = 0; i < 40 && !rows().every(count => count > 0); i++) await wait();
    assert(rows().every(count => count > 0),
           "the new session's answer never painted the rows: " + rows());
    // Its owner clears the marker, so the next read is allowed through. Stop
    // holding reads first, or this call would be the one held forever.
    testState.holdAllSetup = false;
    const beforeFourth = setupReads();
    await loadSetup();
    await wait();
    assert(setupReads() > beforeFourth,
           "the marker was never cleared, so the card stopped reading");
    result.textContent = "PASS: an old read settling cannot clear a new session's in-flight marker";
  } catch (error) {
    result.textContent = "FAIL: " + error.message;
  }
});
"""

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

    def run_browser(self, suffix, check_name, window=None, wrapper=False, budget=None):
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
                                   "/check-self.js", "/check-labels.js",
                                   "/check-token-none.js", "/check-audio-notice.js",
                                   "/check-setup-race.js", "/check-setup-current.js",
                                   "/check-setup-marker.js",
                                   "/check-disconnect-write.js"):
                    script = {"/fixture.js": FIXTURE, "/check.js": CHECK,
                              "/check-noauth.js": CHECK_NOAUTH,
                              "/check-key.js": CHECK_KEY, "/check-probe.js": CHECK_PROBE,
                              "/check-urls.js": CHECK_URLS,
                              "/check-post-401.js": CHECK_POST_401,
                              "/check-setup.js": CHECK_SETUP,
                              "/check-auth-badge.js": CHECK_AUTH_BADGE,
                              "/check-phone-width.js": CHECK_PHONE_WIDTH,
                              "/check-self.js": CHECK_SELF,
                              "/check-labels.js": CHECK_LABELS,
                              "/check-token-none.js": CHECK_TOKEN_NONE,
                              "/check-audio-notice.js": CHECK_AUDIO_NOTICE,
                              "/check-setup-race.js": CHECK_SETUP_RACE,
                              "/check-setup-marker.js": CHECK_SETUP_MARKER,
                              "/check-setup-current.js": CHECK_SETUP_CURRENT,
                              "/check-disconnect-write.js": CHECK_DISCONNECT_WRITE}[self.path]
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
                    # larger virtual-time budget than a plain page. A check that
                    # waits out several held requests needs a larger one still:
                    # the budget is virtual time, and every `wait()` spends it.
                    result = self.dump_dom(directory, host, suffix, window=window,
                                           budget=budget or (8000 if wrapper else 3000))
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

    def test_an_unanswered_volume_change_is_explained_beside_the_controls(self):
        # The explanation existed but sat in the global error line at the very
        # end of the page: on a 390 px phone that is several screens below the
        # Apply button it describes.
        self.run_browser("?auth=none", "check-audio-notice.js", wrapper=True)

    def test_a_late_setup_response_cannot_repopulate_cleared_rows(self):
        # Setup reads were not bound to the session, so a response already in
        # flight when the tab disconnected painted the old device's choices back
        # into the rows disconnect had just cleared. The check also holds a read
        # across a re-pair and a late failure, so it needs more virtual time.
        self.run_browser("?auth=none", "check-setup-race.js", budget=12000)

    def test_an_old_setup_read_settling_cannot_clear_a_new_session_marker(self):
        # The re-pair check lets the new read finish before the old one is
        # released, so a `finally` that clears the marker unconditionally
        # passes it. Holding both and releasing the old one first shows the
        # marker has to belong to the session that set it.
        self.run_browser("?auth=none", "check-setup-marker.js", budget=12000)

    def test_an_audio_write_does_not_discard_a_setup_answer_in_flight(self):
        # The page's global revision was compared as well, so an audio Apply
        # made a valid Setup answer look stale: the card stayed empty until the
        # next 15-second poll.
        self.run_browser("?hold=setup#key=" + "x" * 40, "check-setup-current.js")

    def test_a_token_held_against_a_keyless_device_writes_nothing_at_startup(self):
        # The mode where a "write only if a key is present" handler hides: the
        # dashboard opens normally, so nothing looks wrong.
        self.run_browser("?auth=none#key=" + "x" * 40, "check-token-none.js")

    def test_a_keyless_dashboard_keeps_its_warning(self):
        self.run_browser("?auth=none", "check-auth-badge.js")

    def test_non_json_post_401_revokes_bypass(self):
        self.run_browser("?auth=none", "check-post-401.js")

    def test_an_audio_write_settling_after_disconnect_raises_nothing(self):
        # Disconnect clears the current audio state; the write's `finally`
        # repainted it unconditionally and threw a TypeError, which nothing
        # displays because the handler is an event listener.
        self.run_browser("?auth=none", "check-disconnect-write.js")

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
