"use strict";
const el = id => document.getElementById(id);
// AbortSignal.timeout is newer than the rest of this page. A browser without it
// threw before `fetch` ever ran, which left the welcome card with no bypass
// button and no explanation. Fall back to a controller and a timer.
function timeoutSignal(ms) {
  if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function") {
    return AbortSignal.timeout(ms);
  }
  if (typeof AbortController !== "undefined") {
    const controller = new AbortController();
    setTimeout(() => controller.abort(), ms);
    return controller.signal;
  }
  return undefined;
}
let token = sessionStorage.getItem("debra-key") || "";
// bypass: this tab deliberately connected without a key because the device is
// running `--auth none`. It is never persisted; a reload asks again.
let bypass = false;
let bypassAvailable = false;
// draft: the slider holds a value the user has not submitted.
// volumeOp/muteOp: the last write for that control and what is known about it —
// pending (sent, no answer yet), uncertain (may or may not have applied), or
// rejected (the device refused before doing anything). They are separate so a
// successful mute cannot erase a volume problem, and vice versa.
let draft = false;
let currentAudio = null;
let volumeOp = null;
let muteOp = null;
let busy = false;
let refreshing = false;
let session = 0;
let revision = 0;
// When the device last answered. A failed read leaves the previous readings on
// screen, and they are only honest if the page says how old they are.
let lastReadAt = null;
// True when the last keyless probe never reached the device. A page that says
// "waiting for the access key" against a device that never answered tells a
// person to keep typing into a device that is not there.
let probeFailed = false;
// Only these mean "the device refused and changed nothing". Anything else,
// including 503, may have run the native command before failing.
const DEFINITE = new Set([400, 401, 403, 404, 405, 413]);
// Read both before either rewrites the address: replaceState below changes what
// location.search and location.hash report.
const query = new URLSearchParams(location.search);
const fragment = new URLSearchParams(location.hash.slice(1));
if (fragment.has("key")) {
  // Held in memory only. refresh() persists it once the device has accepted it,
  // so a key that was never checked cannot be replayed by the next reload.
  token = fragment.get("key");
  history.replaceState(null, "", location.pathname);
}
// A form submitted natively (Enter before this script ran, or scripting off)
// sends the key as a query. It is not accepted there, and saying so is better
// than the raw 404 the server used to return for /?key=...
if (query.has("key")) {
  showPairStatus("A key in the address is not accepted. Type it in the box below.");
  history.replaceState(null, "", location.pathname + location.hash);
}
const fmt = (value, suffix = "") => value == null ? "Unavailable" : `${value}${suffix}`;
const bytes = value => value == null ? "Unavailable" : `${(value / 1048576).toFixed(1)} MiB`;
const cpuReading = value => typeof value !== "number" || !Number.isFinite(value) ? "Unavailable" :
  `${value}%${value < 0 || value > 100 ? " · out of range" : ""}`;
function rows(id, entries) {
  const list = el(id);
  list.replaceChildren();
  for (const [label, value] of entries) {
    const row = document.createElement("div");
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = value;
    row.append(dt, dd);
    list.append(row);
  }
}
async function api(path, body) {
  const headers = body ? {"Content-Type": "application/json"} : {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(path, {
    headers,
    ...(body ? {method: "POST", body: JSON.stringify(body)} : {}),
    cache: "no-store",
    signal: timeoutSignal(20000)
  });
  let data;
  try { data = await response.json(); } catch (error) {
    if (response.ok) throw error;
    data = {};
  }
  if (!response.ok || (path === "/api/status" && response.status !== 200)) {
    const error = new Error(data?.error || "Device request failed");
    error.status = response.status;
    throw error;
  }
  return data;
}
// The sections the navigation bar points at, in document order. Kept here
// rather than read from the DOM so the two cannot disagree about the order.
const SECTIONS = ["audio", "health", "device", "components", "setup", "planned"];
// How close to the bar a heading must be before it counts as arrived. Anchoring
// with scroll-padding parks a heading a little *below* the bar rather than
// under it, so a strict "has crossed" test said nobody had arrived at the
// section they had just asked for. One line of tolerance fixes that without
// letting a section further down claim to be current.
const SECTION_ARRIVED_PX = 48;
let navTimer = 0;
function updateCurrentSection() {
  // Exactly one entry is current: the last section whose heading has passed
  // under the bar. Above the first one, and on a page too short to scroll,
  // that is the first section, which is what the person is looking at.
  const nav = el("section-nav");
  // Not offsetParent: a position:sticky element reports null for it, so the bar
  // looked hidden and the marker never moved. getClientRects asks the question
  // that was meant: is this element laid out at all?
  if (!nav || nav.getClientRects().length === 0) return;
  const bar = nav.getBoundingClientRect().bottom;
  let current = SECTIONS[0];
  for (const id of SECTIONS) {
    const section = el(id);
    if (section && section.getBoundingClientRect().top <= bar + SECTION_ARRIVED_PX) current = id;
  }
  for (const link of nav.querySelectorAll("a")) {
    const here = link.getAttribute("href") === `#${current}`;
    if (here && link.getAttribute("aria-current") !== "location") {
      link.setAttribute("aria-current", "location");
    } else if (!here && link.hasAttribute("aria-current")) {
      link.removeAttribute("aria-current");
    }
  }
}
function scheduleCurrentSection() {
  // A scroll fires far more often than the marker needs to move, so the layout
  // reads are throttled. A timer rather than requestAnimationFrame: rAF does
  // not run in the headless browser that checks this, and a marker that only
  // moves in a browser nobody tests is not verified behaviour.
  if (navTimer) return;
  navTimer = setTimeout(() => { navTimer = 0; updateCurrentSection(); }, 50);
}
function watchSections() {
  // A tap is an explicit arrival. Waiting for the scroll to settle before moving
  // the marker made the bar look unresponsive for the length of the animation.
  for (const link of document.querySelectorAll("#section-nav a")) {
    link.addEventListener("click", () => {
      for (const other of document.querySelectorAll("#section-nav a")) {
        if (other !== link) other.removeAttribute("aria-current");
      }
      link.setAttribute("aria-current", "location");
    });
  }
  window.addEventListener("scroll", scheduleCurrentSection, {passive: true});
  window.addEventListener("resize", scheduleCurrentSection);
  // An anchor that lands on a section — typed, pasted or reloaded — is the same
  // arrival as a tap, and the bar must agree with it.
  window.addEventListener("hashchange", scheduleCurrentSection);
}
function setBypassAvailable(available) {
  bypassAvailable = available;
  el("bypass").hidden = !available;
  el("bypass-note").hidden = !available;
}
function showPairStatus(message) {
  // Pairing failures belong next to the key box, inside the welcome card. The
  // global #error is a page-level region after the dashboard: once the
  // dashboard is open it is far from the controls, and it never identifies
  // which credential was refused.
  // The node is never hidden, only emptied: a live region that is display:none
  // is not reliably announced when it later gains text. `:empty` removes the
  // spacing instead.
  const node = el("pair-status");
  if (!node) return;
  node.textContent = message || "";
}
function showPairCheck(message) {
  // A neutral line, not the refusal region: "still finding out" and "that key
  // was wrong" are different messages and only one of them is a fault.
  const node = el("pair-check");
  if (node) node.textContent = message || "";
}
function forgetKey(message) {
  // A key the device refused is not a key to retry on every reload. Clearing it
  // is what lets the keyless probe run and what stops a dead credential from
  // looking like a device that never offers a way in.
  token = "";
  sessionStorage.removeItem("debra-key");
  bypass = false;
  setBypassAvailable(false);
  // Nothing read with the refused key is still current, and a read error from
  // that session must not linger in the page-level error region.
  currentAudio = null;
  draft = false;
  volumeOp = null;
  muteOp = null;
  lastReadAt = null;
  el("error").textContent = "";
  el("stale-notice").textContent = "";
  el("retry").hidden = true;
  el("pair").hidden = false;
  el("dashboard").hidden = true;
  el("connection").textContent = "Not connected";
  showPairStatus(message);
  showNotices();
}
function revokeBypass(message) {
  setBypassAvailable(false);
  bypass = false;
  el("pair").hidden = false;
  el("dashboard").hidden = true;
  // Nothing read under the bypass is still current once the device wants a key.
  currentAudio = null;
  lastReadAt = null;
  el("stale-notice").textContent = "";
  el("retry").hidden = true;
  if (message) showPairStatus(message);
}
function setOp(isVolume, value) {
  if (isVolume) volumeOp = value; else muteOp = value;
}
function notices() {
  return [volumeOp?.message, muteOp?.message].filter(Boolean).join(" ");
}
function showNotices() {
  // A write outcome belongs beside the control that caused it. The global
  // #error sits after every other card, which on a phone is several screens
  // below Apply: a beginner could retry an unanswered change without ever
  // seeing why it may not have applied. #error keeps the read failures; a
  // refused key is named on the welcome card instead. The element is never
  // hidden, only emptied, so the live region exists when its text changes. It
  // is assigned on every refresh, including when the text is unchanged;
  // whether a screen reader announces an identical re-assignment is not
  // established here.
  const message = notices();
  el("audio-notice").textContent = message;
}
function reconcile(data) {
  // An unanswered write is resolved only by a fresh reading that matches it.
  if (volumeOp?.status === "uncertain" && data.available && data.percent === volumeOp.target) {
    const submitted = String(volumeOp.target);
    volumeOp = null;
    if (el("volume").value === submitted) draft = false;
  }
  if (muteOp?.status === "uncertain" && data.available && data.muted === muteOp.target) {
    muteOp = null;
  }
}
function volumeLabel(data) {
  const selected = el("volume").value;
  if (volumeOp?.status === "pending") return `${selected}% · applying…`;
  if (volumeOp?.status === "uncertain") {
    return data.available
      ? `${selected}% selected · device reports ${data.percent}%`
      : `${selected}% · outcome unknown`;
  }
  // With no usable output there is no level to show. "50% · not confirmed" was
  // the browser's own default slider position dressed up as a reading: a number
  // the device never sent.
  if (!data.available) return "No level";
  return draft ? `${selected}% · not applied` : `${data.percent}%`;
}
function audio(data) {
  currentAudio = data;
  for (const id of ["volume", "apply", "mute"]) el(id).disabled = !data.available || busy;
  if (data.available) {
    el("output").textContent = data.description ? `${data.description} (${data.sink})` : data.sink;
    el("audio-status").textContent = data.muted ? "Muted" : "Output unmuted";
  } else {
    // The device named a sink it cannot use. Which one, and why, belongs where
    // the sink is named — above the controls — not in the small line beside a
    // disabled button, where the only evidence a person gets is that nothing
    // responds.
    el("output").textContent = `No usable output${data.error ? `: ${data.error}` : ""} (${data.sink}).`;
    el("audio-status").textContent = "Unavailable";
  }
  el("mute").textContent = data.muted ? "Unmute" : "Mute";
  reconcile(data);
  if (data.available && !draft) el("volume").value = Math.min(100, data.percent);
  el("volume-value").textContent = volumeLabel(data);
  // The level is printed in the accent colour. "No level" in the same colour
  // read as a value at a glance, which is the one thing it must not do.
  el("volume-value").classList.toggle("muted", !data.available);
}
function buildLabel(version) {
  // The short digest is the same string the installer names a release
  // directory by, so two devices can be compared by eye. A process whose files
  // changed underneath it says so rather than claiming the edit is live.
  if (!version || !version.short) {
    return `Build: unknown${version && version.error ? ` (${version.error})` : ""}`;
  }
  const base = `Build ${version.short}`;
  return version.restart_required ? `${base} · files changed on disk, restart to apply` : base;
}
function render(data) {
  el("pair").hidden = true;
  showPairStatus("");
  el("dashboard").hidden = false;
  updateCurrentSection();
  el("build").textContent = buildLabel(data.version);
  // The full digest is what a person compares between devices; the short form
  // is what fits. Hovering gives the whole thing without widening the footer.
  el("build").title = (data.version && data.version.release) || "";
  el("hostname").textContent = data.hostname;
  el("model").textContent = data.model || "Board model unavailable";
  // The polling interval is not state a person needs, and it made the header
  // taller than the brand at phone width. The state is the word.
  el("connection").textContent = "Connected";
  // The browser tab is part of the page: "Debra · Device" on every device makes
  // two tabs impossible to tell apart.
  document.title = `${data.hostname} · Debra`;
  // The warning must not live only on the pairing card: that card is hidden as
  // soon as the dashboard opens, so a person could believe the live controls
  // were protected by the key they may never have been asked for.
  el("auth-mode-warning").hidden = data.auth !== "none";
  audio(data.audio);
  rows("device-values", [
    ["Board", data.model || "Unavailable"], ["Architecture", data.architecture],
    ["Kernel", data.os], ["Detected HAT", data.detected_hat || "No EEPROM identification"],
    ["Selected HAT", data.selected_hardware.hat || "Not selected"],
    ["Speaker (retained label)", data.selected_hardware.speaker || "Not selected"],
    ["Uptime", data.uptime_s == null ? "Unavailable" : `${(data.uptime_s / 3600).toFixed(1)} hours`]
  ]);
  const m = data.memory;
  const p = data.power;
  rows("health-values", [
    ["CPU total", cpuReading(data.cpu_percent.cpu)],
    // Both of these are weaker than their old labels said. The RAM figure is
    // total minus available, not a measured "used"; the temperature is thermal
    // zone 0, and nothing in the collector establishes which sensor that is.
    ["RAM used (total − available) / total", `${bytes(m.MemTotal == null || m.MemAvailable == null ? null : m.MemTotal - m.MemAvailable)} / ${bytes(m.MemTotal)}`],
    ["Thermal zone 0 (sensor not identified)", fmt(data.temperature_c, " °C")],
    ["Storage free", bytes(data.storage?.free_bytes)],
    // The kernel reports an integer here; some drivers return a relative value
    // rather than dBm, so the number is shown as reported, with no unit claimed.
    ["Wi-Fi signal (driver value, unit not established)", data.wifi.length ? data.wifi.map(w => `${w.interface}: ${fmt(w.signal_dbm)}`).join(", ") : "Unavailable / not wireless"],
    ["5 V supply (PMIC)", fmt(p.supply_voltage_v, " V")],
    ["Undervoltage now", p.undervoltage_now == null ? "Unavailable" : p.undervoltage_now ? "Warning" : "Not flagged"],
    ["Undervoltage since boot", p.undervoltage_since_boot == null ? "Unavailable" : p.undervoltage_since_boot ? "Recorded" : "Not flagged"],
    ["Throttle flags", p.throttle_flags || "Unavailable"]
  ]);
  el("cores").replaceChildren();
  for (const [name, value] of Object.entries(data.cpu_percent)) {
    if (name === "cpu") continue;
    const valid = typeof value === "number" && Number.isFinite(value);
    const percent = valid ? Math.max(0, Math.min(100, value)) : null;
    const row = document.createElement("div");
    row.className = "core";
    const label = document.createElement("span");
    label.className = "core-name";
    label.textContent = name.toUpperCase();
    const track = document.createElement("span");
    track.className = "core-track";
    const bar = document.createElement("span");
    bar.className = "core-bar";
    // A bar is a comparison aid, not a measurement: the number is authoritative.
    bar.style.width = percent == null ? "0" : `${percent}%`;
    track.append(bar);
    const reading = document.createElement("span");
    reading.className = "core-value";
    reading.textContent = cpuReading(value);
    row.append(label, track, reading);
    el("cores").append(row);
  }
  const zram = data.zram.map(z => `${z.device}: ${bytes(z.original_bytes)} data → ${bytes(z.memory_bytes)} RAM`).join("; ");
  rows("swap-values", [
    ["Swap used / total", `${bytes(m.SwapTotal == null || m.SwapFree == null ? null : m.SwapTotal - m.SwapFree)} / ${bytes(m.SwapTotal)}`],
    ["zram", zram || "Not detected / unavailable"],
    ["zswap enabled", data.zswap_enabled == null ? "Unavailable" : data.zswap_enabled ? "Yes" : "No"],
    ["Swap in / out", `${fmt(data.swap_io.pswpin_pages_per_s)} / ${fmt(data.swap_io.pswpout_pages_per_s)} pages/s`]
  ]);
  el("component-list").replaceChildren();
  for (const component of data.components) {
    const row = document.createElement("div");
    row.className = "component";
    const name = document.createElement("strong");
    name.textContent = component.name;
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = component.unit_found === false ? "Unit not found" : component.active || "Unknown";
    const detail = document.createElement("small");
    detail.textContent = `${component.enabled ? `Startup: ${component.enabled} · ` : ""}${component.configuration}`;
    row.append(name, badge, detail);
    el("component-list").append(row);
  }
}
// The Setup card reports the device's build choices. Everything on it is
// read-only in this build, so each control is disabled and carries its reason
// beside it: a control that looked usable would be the lie this page exists to
// avoid. The server decides what is enabled; the page never assumes it.
function detailLine(text, className = "choice-detail") {
  // A sentence with no control: the only thing a planned capability may carry.
  const line = document.createElement("p");
  line.className = className;
  line.textContent = text;
  return line;
}
function observationRow(title, status, caveat) {
  // What the device itself reports, as text. No field, button or switch is
  // built here on purpose: a disabled control is still a control, and a person
  // reading this card cannot tell a promise from a capability.
  const row = document.createElement("div");
  row.className = "choice";
  const head = document.createElement("div");
  head.className = "choice-head";
  const name = document.createElement("span");
  name.className = "choice-title";
  name.textContent = title;
  head.append(name);
  row.append(head);
  if (status) {
    const line = document.createElement("p");
    line.className = "choice-status";
    line.textContent = status;
    row.append(line);
  }
  if (caveat) row.append(detailLine(caveat, "choice-caveat"));
  return row;
}
function hatStatus(option) {
  // A family match, not an identification. The EEPROM product string does not
  // carry a model or revision, so saying "identified" was stronger than the
  // evidence and would have told a person their board was this exact one.
  //
  // Only a verdict the device actually made is stated. "No HAT: 3.5 mm jack or
  // USB audio" is an alternative rather than a board the EEPROM can name, and
  // reporting that the EEPROM "does not name" it said the exact opposite of
  // what the ReSpeaker row had just established from the same string. What the
  // EEPROM can and cannot say is described once, in the card's source line.
  let detected;
  if (option.detected === true) {
    detected = "the HAT EEPROM product names a ReSpeaker/Seeed two-mic board — the exact model and revision are not established";
  } else if (option.detected === false) {
    detected = "the HAT EEPROM product does not name a ReSpeaker/Seeed two-mic board";
  } else {
    detected = "the HAT EEPROM gives no family verdict for this row";
  }
  let applied;
  if (!option.card || !option.card.name) {
    applied = "there is no sound card of its own to check";
  } else if (option.applied === true) {
    applied = `an ALSA card named ${option.card.name} is listed`;
  } else if (option.applied === false) {
    applied = `no ALSA card named ${option.card.name} is listed`;
  } else {
    applied = "unknown, because the sound-card list could not be read";
  }
  return `Status: ${detected}; ${applied}.`;
}
function observedLine(option) {
  if (!option.observed) return null;
  const parts = [];
  for (const [scope, state] of Object.entries(option.observed)) {
    if (!state) continue;
    const active = state.active || "unknown";
    parts.push(`${scope === "user" ? "user" : "system"} service: ${active}`
      + (state.enabled ? `, startup ${state.enabled}` : ""));
  }
  if (!parts.length) return null;
  return `${option.label} on this device now — ${parts.join("; ")}.`
    + " Service state is not proof it is configured or working.";
}
function renderSetup(data) {
  const hardware = data?.hardware, settings = data?.settings, updates = data?.updates;
  if (!hardware || !settings || !updates) {
    el("setup-status").textContent = "This device did not report its build choices.";
    return;
  }
  const detected = hardware.detected_hat
    ? `HAT EEPROM: ${hardware.detected_hat}` : "HAT EEPROM: no product recorded";
  const retained = hardware.retained_label
    ? `retained label: ${hardware.retained_label}` : "no retained label";
  const cards = Array.isArray(hardware.cards)
    ? `ALSA cards: ${hardware.cards.length ? hardware.cards.join(", ") : "none listed"}`
    : "ALSA cards: unknown";
  el("setup-hardware-source").textContent = `${detected} · ${retained} · ${cards}`;
  el("setup-hardware-note").textContent = hardware.reason || "";
  // Everything the renderer contributes is evidence about this device. The
  // planned choices below it are static text in index.html and are never
  // touched from here, so a device answer cannot add a control to the page.
  const observations = [];
  for (const option of hardware.options || []) {
    observations.push(observationRow(option.label, hatStatus(option),
      (option.caveats || []).join(" ")));
  }
  for (const setting of Object.values(settings)) {
    for (const option of setting.options || []) {
      const observed = observedLine(option);
      if (observed) observations.push(observationRow(setting.label, observed));
    }
  }
  if (updates.reason) observations.push(observationRow("Updates", updates.reason));
  el("setup-observations").replaceChildren(...observations);
  el("setup-status").textContent = data.reason || "";
}
// The session whose Setup read is in flight, or null. It is per session rather
// than one global flag: a read left pending by a session that ended must not
// block the new session's read, which is the only way the card gets filled.
let setupLoading = null;
async function loadSetup() {
  // Separate from the status poll: a failed read here must not look like a
  // device with no choices, and must not disturb the audio notices.
  if ((!token && !bypass) || setupLoading === session) return;
  // Bound to the session only. A response that was already in flight when the
  // person disconnected used to paint the previous device's build choices back
  // into the rows that disconnect had just cleared, so the session is checked.
  // The page's global revision is deliberately not: an audio write advances it,
  // and a valid answer to a Setup read that was already in flight is still this
  // device's build choices. Rejecting it left the card empty until the next
  // 15-second poll.
  const started = session;
  setupLoading = started;
  try {
    const result = await api("/api/setup");
    if (started !== session) return;
    renderSetup(result);
  } catch (error) {
    if (started !== session) return;
    el("setup-status").textContent = `Build choices unavailable: ${error.message}`;
  } finally {
    // Only the session that started this read clears it; a newer session has
    // already replaced the marker with its own.
    if (setupLoading === started) setupLoading = null;
  }
}
async function refresh() {
  if ((!token && !bypass) || busy || refreshing) return false;
  const started = revision;
  refreshing = true;
  try {
    const result = await api("/api/status");
    if (started !== revision || busy) return false;
    if (bypass && result.auth !== "none") {
      revokeBypass("This device now requires its access key.");
      throw new Error("Device no longer reports keyless access");
    }
    if (bypass) setBypassAvailable(true);
    render(result);
    lastReadAt = Date.now();
    // A successful read makes the readings current again, so the staleness
    // warning goes with them.
    el("stale-notice").textContent = "";
    // Only a key the device has just accepted is persisted. A credential that
    // could not be checked is kept in memory for the retry but never written to
    // the tab, so a reload cannot start by replaying it.
    if (token) sessionStorage.setItem("debra-key", token);
    // A successful read clears the read failure; a write's own outcome stays
    // next to its control until a reading agrees with it.
    el("error").textContent = "";
    showNotices();
    // The device answered, so there is nothing left to try again.
    el("retry").hidden = true;
    return true;
  } catch (error) {
    if (started !== revision || busy) return false;
    if (error.status === 401) {
      // The stored key is dead: a rotation, a reinstall, or a typo. Forget it so
      // the three-second poll cannot keep retrying it, name the refusal where
      // the key was entered, and still look for keyless access.
      const wasBypass = bypass;
      forgetKey(wasBypass
        ? "This device now requires its access key. Enter it to continue."
        : "The device refused that key. It has been forgotten; enter it again.");
      const available = await probeKeyless();
      if (available && !wasBypass) {
        showPairStatus("The device refused that key. It has been forgotten; " +
                       "continue without one, or enter a different key.");
      }
      return false;
    }
    setBypassAvailable(false);
    // A read failure is not a write outcome: it is named here, and the write's
    // rejection or uncertainty stays in its own region rather than replacing
    // or being replaced by it.
    el("error").textContent = error.message;
    showNotices();
    el("retry").hidden = false;
    el("connection").textContent = "Not connected · readings may be stale";
    // The numbers below are the last ones the device sent. Leaving them
    // unlabelled is how "36%" reads as current when the device has been gone
    // for a minute.
    // Receipt time, said as receipt time. When the device *measured* these
    // numbers is a different fact the payload does not carry, and dressing our
    // clock up as an observation time would be exactly the invented confidence
    // this page exists to avoid.
    el("stale-notice").textContent = lastReadAt
      ? `The device is not answering. These are the last readings it sent — this page received them at ${
          new Date(lastReadAt).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})} and the device does not report when it measured them.`
      : "";
    for (const id of ["volume", "apply", "mute"]) el(id).disabled = true;
    return false;
  } finally {
    refreshing = false;
    // A pre-write/pre-pair response is stale even if the write already finished.
    if (started !== revision && token && !busy) await refresh();
  }
}
async function change(path, body) {
  if (busy || !currentAudio?.available || (!token && !bypass)) return;
  const started = session;
  const isVolume = path === "/api/audio/volume";
  const target = isVolume ? body.percent : body.muted;
  revision++;
  busy = true;
  setOp(isVolume, {status: "pending", target, message: ""});
  audio(currentAudio);
  try {
    const result = await api(path, body);
    if (started !== session) return;
    if (!result.available) {
      // The request was accepted but the device could not report the output,
      // so whether it took effect is unknown. Treating this as settled is how
      // an unreadable readback became "not applied", which is a different and
      // stronger claim than the evidence supports.
      setOp(isVolume, {status: "uncertain", target,
        message: `The device accepted this ${isVolume ? "volume" : "mute"} change but could not report the output, so it may or may not have taken effect.`});
    } else {
      setOp(isVolume, null);
      if (isVolume && el("volume").value === String(target)) draft = false;
    }
    audio(result);
  } catch (error) {
    if (started !== session) return;
    if (error.status === 401) revokeBypass("The device refused this tab's access. Enter its key again.");
    if (DEFINITE.has(error.status)) {
      setOp(isVolume, {status: "rejected", target,
        message: `${error.message} Read the current state before retrying.`});
    } else {
      // No answer, or a failure the server could not place before the command:
      // the change may have been applied, so it stays unresolved until a reading
      // agrees with it.
      setOp(isVolume, {status: "uncertain", target,
        message: `The device did not confirm this ${isVolume ? "volume" : "mute"} change. Its reported state is shown; check it before trying again.`});
    }
    showNotices();
  } finally {
    busy = false;
    // The POST has settled: repaint the controls from the state we now know,
    // before the follow-up read. A failed read must not leave "applying…"
    // standing on a write that has already finished.
    //
    // Disconnect clears `currentAudio` and bumps the session, so a write that
    // settles afterwards has no state to repaint: `audio(null)` threw a
    // TypeError on a legitimate Disconnect during an unanswered write.
    if (currentAudio) audio(currentAudio);
    if (!token && !bypass) {
      for (const id of ["volume", "apply", "mute"]) el(id).disabled = true;
    }
    showNotices();
    await refresh();
  }
}
el("pair-form").addEventListener("submit", async event => {
  event.preventDefault();
  // refresh() returns early while a read is in flight or a write is pending.
  // Clearing the box and the message first would make the click look ignored,
  // so say what is happening and keep what the person typed.
  if (busy || refreshing) {
    showPairStatus("Still checking the device. Wait a moment, then press Connect again.");
    return;
  }
  const candidate = el("key").value.trim();
  el("key").value = "";
  if (!candidate) {
    showPairStatus("Enter the device access key, or continue without one if the device offers that.");
    return;
  }
  token = candidate;
  bypass = false;
  session++;
  revision++;
  draft = false;
  volumeOp = null;
  muteOp = null;
  showPairStatus("");
  el("error").textContent = "";
  showNotices();
  if (await refresh()) await loadSetup();
  // A failed read has already been named: forgetKey() reports a refusal, and
  // the non-401 branch names the read failure and keeps the candidate in
  // memory for the retry.
});
el("bypass").addEventListener("click", async () => {
  // Only reachable when the device itself reported that it runs without a key.
  if (!bypassAvailable) return;
  token = "";
  bypass = true;
  sessionStorage.removeItem("debra-key");
  session++;
  revision++;
  draft = false;
  volumeOp = null;
  muteOp = null;
  showPairStatus("");
  showNotices();
  await refresh();
  await loadSetup();
});
el("disconnect").addEventListener("click", () => {
  sessionStorage.removeItem("debra-key");
  token = "";
  bypass = false;
  session++;
  revision++;
  draft = false;
  volumeOp = null;
  muteOp = null;
  currentAudio = null;
  showPairStatus("");
  showNotices();
  // Clear the previous device's own answers so a reconnect cannot show them for
  // a different device, even for one frame. The planned rows are static text
  // about the appliance, not about this device, so they are left alone.
  el("setup-observations").replaceChildren();
  el("setup-hardware-source").textContent = "";
  el("setup-hardware-note").textContent = "";
  el("setup-status").textContent = "";
  el("dashboard").hidden = true;
  el("pair").hidden = false;
  el("connection").textContent = "Disconnected";
});
el("retry").addEventListener("click", async () => {
  // A read, and only a read: a write whose outcome was uncertain is never
  // repeated automatically, and this button must not become that retry.
  el("retry").disabled = true;
  try { await refresh(); } finally { el("retry").disabled = false; }
});
el("volume").addEventListener("input", () => {
  draft = true;
  el("volume-value").textContent = volumeLabel(currentAudio || {available: false});
});
el("apply").addEventListener("click", () => change("/api/audio/volume", {percent: Number(el("volume").value)}));
el("mute").addEventListener("click", () => change("/api/audio/mute", {muted: !currentAudio.muted}));

function canonicalDeviceUrl(url) {
  if (typeof url !== "string" || url.length > 200) return null;
  const match = /^(?:http):\/\/([A-Za-z0-9.-]+):([0-9]{1,5})\/?$/i.exec(url);
  if (!match || match[0] !== url) return null;
  const host = match[1].toLowerCase(), port = Number(match[2]);
  const labels = host.split(".");
  // Port 80 is refused to match the server: a browser would drop the default
  // port from the anchor and the real host check would then reject it.
  if (host.length > 253 || port < 1 || port > 65535 || port === 80 ||
      labels.some(label => !/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(label))) return null;
  if (/^(?:[0-9]+|0x[0-9a-f]*)$/.test(labels[labels.length - 1]) &&
      (labels.length !== 4 || labels.some(label => !/^(?:0|[1-9][0-9]{0,2})$/.test(label) || Number(label) > 255))) return null;
  const canonical = `http://${host}:${port}/`;
  return canonical.length <= 200 ? canonical : null;
}
let loadingDevices = false;
// Is this row the server the page came from? Matching the origin is exact. The
// name comparisons cover the usual case where the page was opened by IP but the
// device advertises a .local name (or the other way round), and they are
// deliberately narrow: the exact reported host, or its .local alias.
//
// Comparing only the first label used to mark any `debra-x.<anything>` as this
// device, so a real second Debra at `debra-x.somewhere-else.example` lost its
// Switch link and was labelled "This device". A wrong "This device" hides a
// working device; a needless Switch link only opens a page that looks the same.
function isSelfDevice(url, self) {
  const authority = url.slice("http://".length).replace(/\/$/, "");
  if (authority.toLowerCase() === location.host.toLowerCase()) return true;
  const hostname = String(self?.hostname || "").toLowerCase();
  if (!hostname || self?.port == null) return false;
  const port = authority.slice(authority.lastIndexOf(":") + 1);
  if (port !== String(self.port)) return false;
  const host = authority.slice(0, authority.lastIndexOf(":")).toLowerCase();
  return host === hostname || host === `${hostname}.local`;
}
const DEVICE_SOURCES = {configured: "Configured", discovered: "Discovered",
                        "configured+discovered": "Configured + discovered"};
function deviceRow(device, self) {
  const url = canonicalDeviceUrl(device?.url);
  if (!url) return null;
  const row = document.createElement("div");
  row.className = "device";
  const identity = document.createElement("div");
  identity.className = "device-id";
  const name = document.createElement("span");
  name.className = "device-name";
  name.textContent = device.label && device.label !== device.name
    ? `${device.name} · ${device.label}` : String(device.name);
  const address = document.createElement("small");
  address.className = "device-address";
  address.textContent = url.replace(/^http:\/\//i, "").replace(/\/$/, "");
  identity.append(name, address);
  row.append(identity);
  if (isSelfDevice(url, self)) {
    // Never offer to switch to the page you are already on.
    const badge = document.createElement("span");
    badge.className = "badge this-device";
    badge.textContent = "This device";
    row.append(badge);
  } else {
    const link = document.createElement("a");
    link.className = "switch";
    link.href = url;
    link.textContent = "Switch";
    link.title = `Open ${url} in this tab`;
    row.append(link);
  }
  const source = document.createElement("span");
  source.className = "badge source";
  source.textContent = DEVICE_SOURCES[device.source] || "Configured";
  row.append(source);
  return row;
}
async function loadDevices() {
  // A slow response must not overlap later refreshes or block the dashboard.
  if (loadingDevices) return;
  loadingDevices = true;
  try {
    const response = await fetch("/api/devices", {cache: "no-store", signal: timeoutSignal(20000)});
    if (!response.ok) return;
    const data = await response.json();
    const list = el("device-links");
    list.replaceChildren();
    for (const device of data.devices || []) {
      const row = deviceRow(device, data.self);
      if (row) list.append(row);
    }
    // Discovery that finds nothing looks identical to discovery that is broken,
    // so say what it did and when; that is the difference the eye needs.
    const discovery = data.discovery || {};
    let summary;
    // An error outranks "off": a discovery that failed to start is not a
    // deliberate choice, and reporting only "off" hides the reason.
    if (discovery.error) summary = `Discovery problem: ${String(discovery.error)}.`;
    else if (!discovery.enabled) summary = "Discovery is off on this server; the list is the configured file.";
    else if (discovery.seconds_since_scan === null || discovery.seconds_since_scan === undefined)
      summary = "Discovery has not finished its first scan yet.";
    else summary = `Discovery found ${discovery.found || 0} device${(discovery.found || 0) === 1 ? "" : "s"},`
                   + ` last scan ${discovery.seconds_since_scan}s ago.`;
    if (Array.isArray(discovery.refused) && discovery.refused.length)
      summary += ` Refused ${discovery.refused.length} discovery record`
                 + `${discovery.refused.length === 1 ? "" : "s"}: ${discovery.refused.join("; ")}.`;
    el("devices-status").textContent = summary;
    // Keep the status visible even with no links: a hidden section with no
    // explanation is the silent failure this replaces.
    el("devices").hidden = list.children.length === 0 && !discovery.enabled && !discovery.error;
  } catch {
    // Keep the last visible list on a temporary HTTP failure.
  } finally {
    loadingDevices = false;
  }
}

async function probeKeyless() {
  // True when the device says it runs without a key. A probe that cannot
  // complete is named on the welcome card: an unexplained missing button is the
  // failure this page exists not to have. Whatever the card already says (a
  // refused key, for example) is kept in front of that failure rather than
  // replaced by it.
  const started = revision;
  const before = el("pair-status")?.textContent || "";
  let failure = "";
  // Whether the device ever answered at all. A probe that never completes is
  // not the same situation as one the device refused, and the header says so.
  probeFailed = false;
  for (let attempt = 0; attempt < 3; attempt++) {
    let available = false, refused = false;
    failure = "";
    try {
      const probe = await fetch("/api/status", {cache: "no-store", signal: timeoutSignal(20000)});
      refused = probe.status === 401;
      if (probe.status === 200) {
        try {
          const auth = (await probe.json())?.auth;
          if (auth === "none") available = true;
          // A definite "key" answer is not a transient failure: the device has
          // said it wants a key, so retrying cannot change the answer.
          else if (auth === "key") refused = true;
          else failure = "The device's answer did not name its access mode.";
        } catch { failure = "The device's answer could not be read."; }
      } else if (!refused) {
        failure = `The device answered ${probe.status}.`;
      }
    } catch {
      failure = "The device did not answer.";
      probeFailed = true;
    }
    if (started !== revision) return false;
    setBypassAvailable(available);
    if (available || refused) { probeFailed = false; return available; }
    if (attempt < 2) await new Promise(resolve => setTimeout(resolve, 200 * (attempt + 1)));
  }
  showPairStatus((before ? before + " " : "") + failure +
                 " Could not check whether this device offers keyless access; " +
                 "reload the page, or enter the key.");
  return false;
}

function showAddress() {
  // The address is what the person typed. It is not an identity: nothing here
  // proves the device at that address is the one they meant, which is worth
  // saying before they type a key into it.
  const node = el("pair-address");
  if (node) node.textContent = `You opened ${location.host}. This page cannot verify that it is the device you meant.`;
}
async function start() {
  showAddress();
  loadDevices();
  watchSections();
  // A device that is slow to answer used to show the key prompt with nothing
  // saying anything was happening: on a keyless device the card asked for a key
  // it does not want, and "waiting" looked exactly like "broken".
  el("connection").textContent = "Checking this device…";
  if (token) {
    if (await refresh()) {
      await loadSetup();
      return;
    }
    // A refused key was forgotten and already probed. A read that failed for
    // another reason keeps the key, but the probe still runs so a device that
    // offers keyless access is not hidden behind a dead token.
    if (token) await probeKeyless();
  } else {
    el("pair").hidden = false;
    showPairCheck("Checking whether this device needs an access key…");
    await probeKeyless();
    showPairCheck("");
  }
  // Anything still on the welcome card is waiting for a choice. Saying so beats
  // leaving "checking" on screen for ever, and it must not ask for a key the
  // device has just said it does not want.
  if (!el("pair").hidden) {
    // Three different reasons to be on this card, said differently: the device
    // answered and wants a key, it answered and offers keyless access, or it
    // never answered at all — and in that last case it is not waiting for a
    // key, it is unreachable.
    el("connection").textContent = bypassAvailable
      ? "Not connected · choose how to continue"
      : probeFailed
        ? "Not connected · no answer from the device"
        : "Not connected · waiting for the access key";
  }
}

start();
setInterval(refresh, 3000);
setInterval(loadDevices, 5000);
// Build choices change only when someone changes the device, so this is slower
// than the status poll and never overlaps itself.
setInterval(loadSetup, 15000);
