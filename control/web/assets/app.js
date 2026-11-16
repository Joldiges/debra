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
// draft: the slider holds a value the device has not confirmed, so a status
// poll must not move it back under the person's finger.
// volumeOp/muteOp: the last write for that control and what is known about it —
// pending (sent, no answer yet), uncertain (may or may not have applied), or
// rejected (the device refused before doing anything). They are separate so a
// successful mute cannot erase a volume problem, and vice versa.
let draft = false;
let currentAudio = null;
let volumeOp = null;
let muteOp = null;
// The slider writes without an Apply button. `queuedVolume` is the level the
// person last chose that the page has not sent yet: it replaces any earlier
// queued level, so dragging across forty values sends one command rather than
// forty, and the newest value is always the one that is sent.
let queuedVolume = null;
// One audio test at a time: a tone still playing or a capture still running is
// not something to start again, and pressing twice must not stack up either.
let testing = false;
// Writing a HAT choice takes a round trip; a second change while it is in
// flight would race the first.
let hatBusy = false;
// A boot-configuration change is not in effect until the device restarts, and
// the page offers that restart in two situations only. The first is this tab
// having just written the file, which is the reason a person has; the second is
// the device showing the change is still unapplied -- the file names a board
// whose sound card is not listed. The second matters because the first is lost
// on reload: write the line, reload, and the restart prompt used to vanish
// while the driver silently stayed the old one.
let hatNeedsRestart = false;
let hatRestarting = false;
let volumeTimer = 0;
// Long enough that a drag is one command, short enough that a person who let go
// does not wonder whether it took.
const VOLUME_SETTLE_MS = 120;
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
// What the kernel did with an audio codec. Four outcomes, kept apart because
// they need different actions, and "unavailable" is never shown as "none".
const codecReading = codec => {
  if (!codec) return "Unavailable";
  if (codec.state === "bound") {
    return `${codec.name} at ${codec.address} · driver bound, ${codec.card} listed`;
  }
  if (codec.state === "present") {
    return `${codec.name} at ${codec.address} · no driver bound`;
  }
  if (codec.state === "no_card") {
    return `${codec.name} at ${codec.address} · ${codec.driver} bound, no sound card listed`;
  }
  if (codec.state === "none") return "No audio codec configured";
  return "Unavailable";
};
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
// Sections whose real content lives behind a disclosure open it when the
// section is chosen. Tapping "Tasks" and being shown a heading and a plus sign
// answers a different question than the one asked. Audio and Health are left
// out on purpose: their readings are already visible and their disclosures are
// extra detail rather than the section itself.
const SECTION_DISCLOSURES = {
  device: "hardware-details", components: "components-details",
  setup: "setup-details", planned: "tasks-details",
};
function revealSection(hash) {
  const details = SECTION_DISCLOSURES[String(hash || "").replace("#", "")];
  if (details && el(details)) el(details).open = true;
}
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
      revealSection(link.getAttribute("href"));
    });
  }
  window.addEventListener("scroll", scheduleCurrentSection, {passive: true});
  window.addEventListener("resize", scheduleCurrentSection);
  // An anchor that lands on a section — typed, pasted or reloaded — is the same
  // arrival as a tap, and the bar must agree with it.
  window.addEventListener("hashchange", () => {
    scheduleCurrentSection();
    revealSection(location.hash);
  });
}
function setBypassAvailable(available) {
  bypassAvailable = available;
  el("bypass").hidden = !available;
  el("bypass-note").hidden = !available;
  el("keyless-lead").hidden = !available;
  // A field that cannot change the outcome is worse than no field: with the
  // key switched off, any key is accepted and none is needed. The form and the
  // explanation of where a key comes from belong to key mode.
  el("pair-form").hidden = available;
  el("key-source").hidden = available;
  // The line above the form says to enter a key. Left in place beside "there is
  // nothing to type", the card contradicted itself in its own first screen.
  el("pair-intro").hidden = available;
}
function focusCard() {
  // Whichever control the welcome card is actually offering. Focusing a hidden
  // field silently does nothing, which left focus on the device name after a
  // disconnect on a keyless device. #bypass is the visible action there.
  const target = el("pair-form").hidden ? el("bypass") : el("key");
  if (target && !target.hidden) target.focus({preventScroll: true});
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
function forgetQueuedVolume() {
  // A level queued for a device this tab no longer talks to must not be sent to
  // whatever it connects to next.
  queuedVolume = null;
  if (volumeTimer) { clearTimeout(volumeTimer); volumeTimer = 0; }
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
  forgetQueuedVolume();
  lastReadAt = null;
  el("error").textContent = "";
  el("stale-notice").textContent = "";
  el("retry").hidden = true;
  el("pair").hidden = false;
  el("dashboard").hidden = true;
  el("page-footer").hidden = true;
  // A write that settles after this never repaints (currentAudio is cleared), so
  // the busy flag would otherwise stay set for the next time the card is shown.
  el("audio-controls").setAttribute("aria-busy", "false");
  el("connection").textContent = "Not connected";
  showPairStatus(message);
  showNotices();
}
function revokeBypass(message) {
  setBypassAvailable(false);
  bypass = false;
  el("pair").hidden = false;
  el("dashboard").hidden = true;
  el("page-footer").hidden = true;
  // A write that settles after this never repaints (currentAudio is cleared), so
  // the busy flag would otherwise stay set for the next time the card is shown.
  el("audio-controls").setAttribute("aria-busy", "false");
  // Nothing read under the bypass is still current once the device wants a key.
  currentAudio = null;
  forgetQueuedVolume();
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
  // The deliberate retry exists only while there is a write to deliberately
  // retry, so the card never carries a button that does nothing.
  el("retry-volume").hidden = !(volumeOp &&
    (volumeOp.status === "uncertain" || volumeOp.status === "rejected"));
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
  if (queuedVolume !== null || volumeOp?.status === "pending") return `${selected}% · applying…`;
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
  // Announced as busy only while a write is in flight; the controls are already
  // disabled, and this tells assistive technology that the region is changing
  // rather than that the device is refusing input.
  el("audio-controls").setAttribute("aria-busy", busy ? "true" : "false");
  for (const id of ["volume", "mute"]) el(id).disabled = !data.available || busy;
  // A test needs a failure worth running, not more: enabling these with no
  // usable output would only repeat a reason the card already shows.
  for (const id of ["test-output", "test-input"]) el(id).disabled = busy || testing;
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
  const firstPaint = el("dashboard").hidden;
  el("dashboard").hidden = false;
  el("page-footer").hidden = false;
  updateCurrentSection();
  if (firstPaint) {
    // The button a person just pressed is gone. Left alone, focus falls back to
    // the top of the document and a keyboard or screen-reader user has to find
    // the page again. Focus goes to the device's name instead, which is also the
    // first thing they need to hear.
    el("hostname").focus({preventScroll: true});
  }
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
    ["Audio codec", codecReading(data.codec)],
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
  renderComponents(data.components);
  renderProcesses(data.processes);
}
// Which of the three groups a component belongs in. The evidence is systemd's
// own answer, and the three answers are genuinely different: a unit it does not
// know is not installed, a unit it knows is installed whether or not it is
// running right now, and a component with no detector at all is neither — which
// is a real third answer, not a gap to paper over.
function componentGroup(component) {
  if (component.unit_found === false) return "missing";
  if (component.unit_found === true) return "installed";
  return "unknown";
}
function componentRow(component) {
  const row = document.createElement("div");
  row.className = "component";
  const name = document.createElement("strong");
  name.textContent = component.name;
  const badge = document.createElement("span");
  badge.className = "badge";
  badge.textContent = component.unit_found === false ? "Unit not found"
    : component.active || "Unknown";
  const detail = document.createElement("small");
  const parts = [];
  if (component.enabled) parts.push(`Startup: ${component.enabled}`);
  // What this utility is using, when systemd named its process and the sample
  // contains it. An absent figure is left out rather than printed as zero: a
  // stopped utility uses nothing, which is not the same as not being told.
  if (typeof component.cpu_percent === "number") parts.push(`CPU ${component.cpu_percent}%`);
  if (typeof component.memory_bytes === "number") parts.push(bytes(component.memory_bytes));
  if (component.configuration) parts.push(component.configuration);
  detail.textContent = parts.join(" · ");
  row.append(name, badge, detail);
  return row;
}
function renderComponents(components) {
  const groups = {installed: [], missing: [], unknown: []};
  for (const component of components || []) groups[componentGroup(component)].push(componentRow(component));
  for (const [group, rows] of Object.entries(groups)) {
    const title = el(`components-${group}-title`);
    const list = el(`components-${group}`);
    if (!title || !list) continue;
    // The count is part of the answer: "Not installed (0)" says more than a
    // heading over nothing, which reads as a failure to render.
    const label = group === "missing" ? "Not installed" : group[0].toUpperCase() + group.slice(1);
    title.textContent = `${label} (${rows.length})`;
    list.replaceChildren(...rows);
  }
  // Said once, here, instead of on every row it used to be attached to.
  const total = (components || []).length;
  const note = el("components-note");
  if (note) {
    note.textContent = total
      ? `Systemd's own state for ${total} component${total === 1 ? "" : "s"}. A unit that is running does not mean the component is configured or working, and a unit that is present does not mean it is in use.`
      : "This device did not report any components.";
  }
}
function renderProcesses(processes) {
  const list = el("processes");
  if (!list) return;
  const rows = Array.isArray(processes) ? processes : [];
  if (!rows.length) {
    // "Nothing is running" and "this device did not say" are different answers.
    const line = document.createElement("p");
    line.className = "detail";
    line.textContent = "This device did not report process figures.";
    list.replaceChildren(line);
    return;
  }
  list.replaceChildren(...rows.map(entry => {
    const row = document.createElement("div");
    row.className = "process";
    const name = document.createElement("span");
    name.className = "process-name";
    name.textContent = entry.pids > 1 ? `${entry.name} (${entry.pids})` : entry.name;
    const cpu = document.createElement("span");
    cpu.className = "process-cpu";
    // A blank reading is a reading not yet available, not zero.
    cpu.textContent = typeof entry.cpu_percent === "number" ? `${entry.cpu_percent}%` : "—";
    const memory = document.createElement("span");
    memory.className = "process-memory";
    memory.textContent = bytes(entry.memory_bytes);
    row.append(name, cpu, memory);
    return row;
  }));
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
// The one control on the Setup card. It records which board a person has; it
// installs nothing, and the note underneath says so in the same breath.
function renderHatChoice(hardware) {
  const select = el("hat-select"), row = el("hat-choice");
  if (!select || !row) return;
  const options = hardware.options || [];
  const chosen = hardware.choice || "";
  const wanted = [["", "Not chosen yet"], ...options.map(o => [o.id, o.label])];
  // A poll must not rebuild a control a person is using: replacing the options
  // under an open dropdown closes it and takes the choice with it. The next
  // poll after they let go redraws from what the device kept.
  if (document.activeElement !== select) {
    select.replaceChildren(...wanted.map(([value, label]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      return option;
    }));
    select.value = chosen;
  }
  // An unselectable card keeps its control hidden rather than showing a
  // dropdown whose answer nobody keeps.
  row.hidden = !hardware.selectable;
  select.disabled = !hardware.selectable || hatBusy;
  const current = options.find(option => option.selected);
  const parts = [];
  parts.push(hardware.detected_hat
    ? `Detected at setup: ${hardware.detected_hat}.`
    : "Detected at setup: this device did not name a HAT.");
  // None of these boards has a HAT EEPROM, so the codec is the only thing that
  // identifies the board at all -- and it is a fact about software, not about
  // which vendor sold the board. The note says what it cannot tell apart.
  if (hardware.codec) parts.push(`Audio codec: ${hardware.codec.note}`);
  parts.push(current
    ? `Chosen here: ${current.label}.`
    : "Chosen here: nothing yet.");
  if (current) {
    // Three separate facts, so a person can see which one is missing when the
    // speaker stays silent: what was detected, what was recorded, and whether
    // the driver's sound card is there at all.
    parts.push(!current.card || !current.card.name
      ? "Driver: this choice has no sound card of its own to check."
      : current.applied === true
        ? `Driver: an ALSA card named ${current.card.name} is present.`
        : current.applied === false
          ? `Driver: no ALSA card named ${current.card.name} is present yet.`
          : "Driver: the sound-card list could not be read.");
  }
  el("hat-state").textContent = parts.join(" ");
  el("hat-note").textContent = hardware.choice_note || "";
  renderHatInstall(hardware);
}
// The Install control follows the recorded choice: it installs what the person
// chose, including "No HAT", which removes the overlay rather than adding one.
// It is hidden rather than disabled when it cannot work, because a control that
// does nothing is a worse answer than a sentence saying why.
function renderHatInstall(hardware) {
  const row = el("hat-install"), button = el("hat-install-button"),
        remove = el("hat-remove-button"), restart = el("hat-restart-button"),
        state = el("hat-install-state"), enrol = el("hat-enrol-note");
  if (!row || !button || !remove || !restart || !state || !enrol) return;
  const choice = (hardware.options || []).find(option => option.selected);
  const helper = hardware.helper || {};
  const boot = hardware.boot || {};
  // The socket exists when the helper is installed and started. Whether it
  // answers is what pressing the button finds out, in one round trip.
  const allowed = helper.present === true;
  // A device that has not been enrolled says so in words, once, and shows no
  // control: there is nothing this page can do about it from here.
  enrol.hidden = allowed || !choice;
  if (!choice) {
    row.hidden = true;
    restart.hidden = true;
    state.textContent = hardware.selectable
      ? "Choose a board above to see what installing it would do."
      : "";
    return;
  }
  if (!allowed) {
    row.hidden = true;
    restart.hidden = true;
    state.textContent = "This device does not have the install helper yet, so nothing "
      + "here can change the boot configuration.";
    return;
  }
  const configured = choice.configured === true;
  const installable = choice.installable || {ok: true, reason: null};
  // The device's own observation of whether the written line has taken effect:
  // the boot configuration names the board, but no sound card with the driver's
  // name is listed. That is a restart waiting to happen (or a wrong board), and
  // it survives a reload, which this tab's own flag does not.
  const card = choice.card || {};
  // The helper records the boot it wrote in, so the page can tell "restart to
  // apply it" from "it has been restarted and the card is still not there". The
  // second means the board is wrong, and inviting another restart would send a
  // person round a loop that cannot end.
  const change = hardware.change || {};
  const restartedSince = change.same_boot === false &&
        change.overlay === choice.overlay;
  const pendingByObservation = configured && Boolean(choice.overlay) && card.present === false;
  const pointlessRestart = restartedSince && card.present === false;
  row.hidden = false;
  // Three states, one control each: install the chosen board, remove it again,
  // or -- for "No HAT" -- take the managed overlay out. Nothing is offered that
  // would not change the file.
  const removing = choice.overlay === null;
  const showRemove = Boolean(choice.overlay) && configured;
  button.hidden = showRemove || (removing && !configured);
  button.textContent = removing ? "Remove the audio-HAT overlay" : "Install driver";
  button.disabled = hatBusy || hatRestarting || !installable.ok;
  remove.hidden = !showRemove;
  remove.disabled = hatBusy || hatRestarting;
  restart.hidden = !(hatNeedsRestart || pendingByObservation) || pointlessRestart ||
    hatRestarting;
  restart.disabled = hatBusy || hatRestarting;
  if (hatRestarting) {
    state.textContent = "The device is restarting. This page will reconnect when it is back.";
    return;
  }
  if (!installable.ok) {
    state.textContent = `${installable.reason} Installing would write a line the next boot cannot use, so the button is off.`;
    return;
  }
  if (configured) {
    if (!choice.overlay) {
      state.textContent = "An audio-HAT overlay this page manages is in the boot configuration. Choosing No HAT and removing it takes it out.";
      return;
    }
    // Three separate facts, said separately: the line is in the file, the
    // sound card the driver creates is (or is not) listed now, and neither is a
    // test of the microphone or the speaker. Saying "a restart applies it" to a
    // device that has already restarted told a person to do what was done.
    if (card.present === true) {
      state.textContent = `The boot configuration names ${choice.overlay}, and this device lists ` +
        `the sound card it creates (${card.name}). Whether the microphone and speaker work is ` +
        `what the audio checks show.`;
    } else if (card.present === false && pointlessRestart) {
      // The device has already restarted since the line was written and the
      // card is still absent, so the overlay is not describing this board. There
      // is no button here on purpose: the next step is a different board, not
      // another reboot.
      state.textContent = `The boot configuration names ${choice.overlay}. It was written ` +
        `before the last restart and this boot has come up without a sound card named ` +
        `${card.name}, so the board is not the one this overlay describes. Restarting again ` +
        `will not change that: check which board is fitted, or use a different choice.`;
    } else if (card.present === false) {
      // The restart button is shown in this state, so the sentence can point at
      // it instead of leaving a person to guess how the line takes effect.
      state.textContent = `The boot configuration names ${choice.overlay}, but no sound card ` +
        `named ${card.name} is listed. Restart the device to apply it; if it is still ` +
        `missing after that, the board is not the one this overlay describes.`;
    } else {
      state.textContent = `The boot configuration names ${choice.overlay}. This page cannot ` +
        `read the sound-card list, so it cannot say whether the driver is loaded now.`;
    }
    return;
  }
  state.textContent = hatNeedsRestart
    ? "Written. Restart the device to apply it."
    : "";
}
// One round trip for both actions. The device answers with the helper's own
// words, which are the only account of what happened to the file.
async function hatAction(path, body, busyText) {
  const state = el("hat-install-state");
  hatBusy = true;
  state.textContent = busyText;
  try {
    const result = await api(path, body);
    return result;
  } catch (error) {
    state.textContent = error.status === 401
      ? "The device refused this tab's access. Enter its key again."
      : `That did not happen: ${error.message}`;
    return null;
  } finally {
    hatBusy = false;
  }
}
el("hat-install-button").addEventListener("click", async () => {
  if (hatBusy || hatRestarting) return;
  const result = await hatAction("/api/setup/hat/install", {},
    "Writing the boot configuration…");
  if (!result) return;
  hatNeedsRestart = Boolean(result.changed);
  if (!result.changed) {
    el("hat-install-state").textContent = result.note || "Nothing needed changing.";
  }
  await loadSetup();
});
el("hat-remove-button").addEventListener("click", async () => {
  if (hatBusy || hatRestarting) return;
  const result = await hatAction("/api/setup/hat/remove", {},
    "Removing the overlay from the boot configuration…");
  if (!result) return;
  hatNeedsRestart = Boolean(result.changed);
  await loadSetup();
});
el("hat-restart-button").addEventListener("click", async () => {
  if (hatBusy || hatRestarting) return;
  // A restart is the one action here a person cannot undo by waiting, so it
  // asks first, in the browser, before anything is sent.
  if (!window.confirm("Restart this device now? The page will disconnect for about a minute.")) return;
  hatRestarting = true;
  const result = await hatAction("/api/setup/restart", {confirm: "restart"},
    "Restarting the device…");
  if (!result) {
    hatRestarting = false;
    await loadSetup();
    return;
  }
  el("hat-install-state").textContent = result.note ||
    "The device is restarting. This page will reconnect when it is back.";
});
el("hat-select").addEventListener("change", async () => {
  const select = el("hat-select");
  if (hatBusy) return;
  hatBusy = true;
  select.disabled = true;
  try {
    await api("/api/setup/hat", {choice: select.value});
    await loadSetup();
  } catch (error) {
    el("hat-state").textContent = error.status === 401
      ? "The device refused this tab's access. Enter its key again."
      : `That choice was not recorded: ${error.message}.`;
  } finally {
    hatBusy = false;
    select.disabled = false;
  }
});
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
  // The "service state is not proof it is configured" caveat used to be glued
  // to every one of these rows. Said six times it stopped being read, so it is
  // said once on the Components card, where the service list lives.
  return `${option.label} on this device now — ${parts.join("; ")}.`;
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
  renderHatChoice(hardware);
  for (const setting of Object.values(settings)) {
    for (const option of setting.options || []) {
      const observed = observedLine(option);
      if (observed) observations.push(observationRow(setting.label, observed));
    }
  }
  // The updates reason is not repeated here: the Setup card's own Updates line
  // says it in the same words, and a second copy in a different card's list is
  // exactly the repetition this pass is removing.
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
    // Written only when it changes. A poll that keeps failing with the same
    // sentence would otherwise reassign the same text every three seconds, and
    // an alert region that re-announces "the device did not answer" forever is
    // worse than silence.
    if (el("error").textContent !== error.message) el("error").textContent = error.message;
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
    for (const id of ["volume", "mute", "test-output", "test-input"]) el(id).disabled = true;
    return false;
  } finally {
    refreshing = false;
    // A pre-write/pre-pair response is stale even if the write already finished.
    if (started !== revision && token && !busy) await refresh();
  }
}
async function change(path, body) {
  // Returns whether the write was actually sent. A caller that queued a value
  // has to know the difference between "sent" and "declined because another
  // write is in flight", or the newest level is silently dropped.
  if (busy || !currentAudio?.available || (!token && !bypass)) return false;
  const started = session;
  const isVolume = path === "/api/audio/volume";
  const target = isVolume ? body.percent : body.muted;
  revision++;
  busy = true;
  setOp(isVolume, {status: "pending", target, message: ""});
  audio(currentAudio);
  try {
    const result = await api(path, body);
    if (started !== session) return false;
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
    if (started !== session) return false;
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
      for (const id of ["volume", "mute", "test-output", "test-input"]) el(id).disabled = true;
    }
    showNotices();
    await refresh();
  }
  return true;
}
// The slider's own writer. Moving it queues the newest level and restarts a
// short timer; when the timer runs out, one change is sent. A write already in
// flight defers rather than queues behind itself, so a fast drag produces a
// handful of commands instead of one per pixel, and the last value is always
// the one the device ends up with.
function scheduleVolume(delay = VOLUME_SETTLE_MS) {
  if (volumeTimer) clearTimeout(volumeTimer);
  volumeTimer = setTimeout(() => { volumeTimer = 0; flushVolume(); }, delay);
}
async function flushVolume() {
  if (queuedVolume === null) return;
  if (busy) {
    // Another write is running. Try again shortly rather than dropping the level
    // the person chose, and rather than queueing a command behind it.
    scheduleVolume(80);
    return;
  }
  if (el("volume").disabled) {
    // Nothing can be sent: no usable output, the device is not answering, or
    // this tab is not connected. Drop the queued level and leave the slider
    // where the person put it, marked as not applied. A control that looks
    // dead but still writes is the one thing this page must not be.
    queuedVolume = null;
    draft = true;
    if (currentAudio) {
      el("volume-value").textContent = volumeLabel(currentAudio);
      el("audio-controls").setAttribute("aria-busy", "false");
    }
    return;
  }
  const percent = queuedVolume;
  queuedVolume = null;
  if (currentAudio) {
    el("volume-value").textContent = volumeLabel(currentAudio);
    el("audio-controls").setAttribute("aria-busy", "true");
  }
  const sent = await change("/api/audio/volume", {percent});
  if (!sent && queuedVolume === null && !el("volume").disabled) {
    // The page declined to send it (another write started in the meantime).
    // Keep the intent rather than pretending it went.
    queuedVolume = percent;
    scheduleVolume(400);
    return;
  }
  // A newer level arrived while that write was in flight.
  if (queuedVolume !== null) scheduleVolume(VOLUME_SETTLE_MS);
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
  forgetQueuedVolume();
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
  el("page-footer").hidden = true;
  // A write that settles after this never repaints (currentAudio is cleared), so
  // the busy flag would otherwise stay set for the next time the card is shown.
  el("audio-controls").setAttribute("aria-busy", "false");
  el("pair").hidden = false;
  el("connection").textContent = "Disconnected";
  // What the card offers next: the key field when the device wants a key, the
  // continue button when it does not. Focusing a hidden field left focus on the
  // device name, because focusing something that is not rendered does nothing.
  focusCard();
});
el("retry").addEventListener("click", async () => {
  // A read, and only a read: a write whose outcome was uncertain is never
  // repeated automatically, and this button must not become that retry.
  el("retry").disabled = true;
  try { await refresh(); } finally { el("retry").disabled = false; }
});
el("volume").addEventListener("input", () => {
  // Marked as a draft so a status poll cannot drag the slider back under the
  // person's finger, then queued: the write happens when they stop moving it.
  draft = true;
  queuedVolume = Number(el("volume").value);
  el("volume-value").textContent = volumeLabel(currentAudio || {available: false});
  scheduleVolume();
});
el("retry-volume").addEventListener("click", () => {
  // Deliberate, and only ever this one value: a write whose outcome was unknown
  // is never repeated by the page itself.
  if (volumeOp?.target == null) return;
  queuedVolume = volumeOp.target;
  scheduleVolume(0);
});
el("mute").addEventListener("click", () => change("/api/audio/mute", {muted: !currentAudio.muted}));
el("test-output").addEventListener("click", () => runTest("test-output"));
el("test-input").addEventListener("click", () => runTest("test-input"));
// "Did the speaker work?" and "did the microphone hear me?" are the two questions
// a beginner actually asks, and no reading answers either. Each is one deliberate
// press, bounded by the device, and it reports in the same place every other
// audio outcome is reported.
async function runTest(route) {
  if (testing || busy || (!token && !bypass)) return;
  const isOutput = route === "test-output";
  testing = true;
  el("test-result").textContent = isOutput ? "Playing a short tone…"
                                           : "Listening for about a second…";
  if (currentAudio) audio(currentAudio);
  try {
    const result = await api(`/api/audio/${route}`, {});
    if (isOutput) {
      el("test-result").textContent = result.played
        ? `Played a ${result.hertz} Hz tone for ${result.seconds} seconds. If you did not hear it, check the volume and that the speaker is connected.`
        : String(result.reason || "The tone could not be played.");
    } else if (!result.available) {
      el("test-result").textContent = String(result.reason || "The microphone could not be read.");
    } else {
      // The level is what the source produced. Saying "the microphone works"
      // would claim more: a source returns silence with the microphone unplugged
      // and noise with a fan nearby, and neither is a working microphone.
      el("test-result").textContent =
        `${result.level} input: peak ${result.peak_percent}% of full scale over ${result.seconds} seconds.`
        + (result.level === "Silence"
           ? " Speak while pressing the button, and check the microphone is connected."
           : " Nothing was kept: no recording was saved or sent.");
    }
  } catch (error) {
    el("test-result").textContent = error.status === 401
      ? "The device refused this tab's access. Enter its key again."
      : `The test could not run: ${error.message}.`;
  } finally {
    testing = false;
    if (currentAudio) audio(currentAudio);
  }
}

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
    // The other half of the same question. A device that finds nobody is asked
    // why, and "nobody else advertises" and "this device does not advertise
    // either" are different answers to the same silence.
    summary += ` ${announcementSummary(data.announcement)}`;
    el("devices-status").textContent = summary;
    // Keep the status visible even with no links: a hidden section with no
    // explanation is the silent failure this replaces. An advertisement that
    // failed is also worth showing before there is anything to switch to.
    el("devices").hidden = list.children.length === 0 && !discovery.enabled
      && !discovery.error && !data.announcement?.error;
  } catch {
    // Keep the last visible list on a temporary HTTP failure.
  } finally {
    loadingDevices = false;
  }
}
function announcementSummary(announcement) {
  // Whether *this* device can be found by the others, in the device's own words
  // where it gave a reason. Silence here would leave a person comparing two
  // devices that each see only themselves with nothing to act on.
  const period = text => {
    const trimmed = String(text || "").trim();
    return trimmed && !/[.!?]$/.test(trimmed) ? `${trimmed}.` : trimmed;
  };
  if (!announcement) return "";
  if (announcement.error) {
    return period(`This device is not announcing itself: ${String(announcement.error)}`);
  }
  if (announcement.running) return period(`This device announces itself as “${announcement.instance}”`);
  if (announcement.reason) return period(`This device is not announcing itself: ${String(announcement.reason)}`);
  return "This device is not announcing itself, and did not say why.";
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
  // An address that names a section is the same request as a tap.
  revealSection(location.hash);
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
