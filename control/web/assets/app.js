"use strict";
const el = id => document.getElementById(id);
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
// Only these mean "the device refused and changed nothing". Anything else,
// including 503, may have run the native command before failing.
const DEFINITE = new Set([400, 401, 403, 404, 405, 413]);
const fragment = new URLSearchParams(location.hash.slice(1));
if (fragment.has("key")) {
  token = fragment.get("key");
  sessionStorage.setItem("debra-key", token);
  history.replaceState(null, "", location.pathname);
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
    signal: AbortSignal.timeout(20000)
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
function setBypassAvailable(available) {
  bypassAvailable = available;
  el("bypass").hidden = !available;
  el("bypass-note").hidden = !available;
}
function revokeBypass() {
  setBypassAvailable(false);
  bypass = false;
  el("pair").hidden = false;
  el("dashboard").hidden = true;
}
function setOp(isVolume, value) {
  if (isVolume) volumeOp = value; else muteOp = value;
}
function notices() {
  return [volumeOp?.message, muteOp?.message].filter(Boolean).join(" ");
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
  if (!data.available) return `${selected}% · not confirmed`;
  return draft ? `${selected}% · not applied` : `${data.percent}%`;
}
function audio(data) {
  currentAudio = data;
  for (const id of ["volume", "apply", "mute"]) el(id).disabled = !data.available || busy;
  el("output").textContent = data.description ? `${data.description} (${data.sink})` : data.sink;
  el("audio-status").textContent = data.available ? (data.muted ? "Muted" : "Output unmuted") : data.error;
  el("mute").textContent = data.muted ? "Unmute" : "Mute";
  reconcile(data);
  if (data.available && !draft) el("volume").value = Math.min(100, data.percent);
  el("volume-value").textContent = volumeLabel(data);
}
function render(data) {
  el("pair").hidden = true;
  el("dashboard").hidden = false;
  el("hostname").textContent = data.hostname;
  el("model").textContent = data.model || "Board model unavailable";
  el("connection").textContent = "Connected · updates every 3 seconds";
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
    ["RAM used / total", `${bytes(m.MemTotal == null || m.MemAvailable == null ? null : m.MemTotal - m.MemAvailable)} / ${bytes(m.MemTotal)}`],
    ["CPU temperature", fmt(data.temperature_c, " °C")],
    ["Storage free", bytes(data.storage?.free_bytes)],
    ["Wi-Fi signal", data.wifi.length ? data.wifi.map(w => `${w.interface}: ${fmt(w.signal_dbm, " dBm")}`).join(", ") : "Unavailable / not wireless"],
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
async function refresh() {
  if ((!token && !bypass) || busy || refreshing) return;
  const started = revision;
  refreshing = true;
  try {
    const result = await api("/api/status");
    if (started !== revision || busy) return;
    if (bypass && result.auth !== "none") {
      revokeBypass();
      throw new Error("Device no longer reports keyless access");
    }
    if (bypass) setBypassAvailable(true);
    render(result);
    el("error").textContent = notices();
  } catch (error) {
    if (started !== revision || busy) return;
    setBypassAvailable(false);
    if (error.status === 401) {
      revokeBypass();
    }
    // A read failure is not a write outcome: keep any rejection or uncertainty
    // visible next to it rather than replacing it.
    el("error").textContent = [notices(), error.message].filter(Boolean).join(" ");
    el("connection").textContent = "Not connected · readings may be stale";
    for (const id of ["volume", "apply", "mute"]) el(id).disabled = true;
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
    setOp(isVolume, null);
    if (isVolume && el("volume").value === String(target)) draft = false;
    audio(result);
  } catch (error) {
    if (started !== session) return;
    if (error.status === 401) revokeBypass();
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
    el("error").textContent = notices();
  } finally {
    busy = false;
    // The POST has settled: repaint the controls from the state we now know,
    // before the follow-up read. A failed read must not leave "applying…"
    // standing on a write that has already finished.
    audio(currentAudio);
    if (!token && !bypass) {
      for (const id of ["volume", "apply", "mute"]) el(id).disabled = true;
    }
    el("error").textContent = notices();
    await refresh();
  }
}
el("pair-form").addEventListener("submit", async event => {
  event.preventDefault();
  token = el("key").value.trim();
  bypass = false;
  session++;
  revision++;
  draft = false;
  volumeOp = null;
  muteOp = null;
  sessionStorage.setItem("debra-key", token);
  el("key").value = "";
  await refresh();
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
  await refresh();
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
  el("dashboard").hidden = true;
  el("pair").hidden = false;
  el("connection").textContent = "Disconnected";
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
// Is this row the server the page came from? Matching the origin is exact; the
// name comparisons cover the usual case where the page was opened by IP but the
// device advertises a .local name (or the other way round).
function isSelfDevice(url, self) {
  const authority = url.slice("http://".length).replace(/\/$/, "");
  if (authority.toLowerCase() === location.host.toLowerCase()) return true;
  const hostname = String(self?.hostname || "").toLowerCase();
  if (!hostname || self?.port == null) return false;
  const port = authority.slice(authority.lastIndexOf(":") + 1);
  if (port !== String(self.port)) return false;
  const host = authority.slice(0, authority.lastIndexOf(":")).toLowerCase();
  return host === hostname || host === `${hostname}.local` || host.split(".")[0] === hostname;
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
    const response = await fetch("/api/devices", {cache: "no-store", signal: AbortSignal.timeout(20000)});
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
      summary += ` Refused ${discovery.refused.length} advertisement`
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

async function start() {
  loadDevices();
  if (token) {
    await refresh();
    return;
  }
  el("pair").hidden = false;
  // A transient failure should not require a reload, but an old probe must not
  // overwrite a newer pairing or disconnect decision.
  const started = revision;
  for (let attempt = 0; attempt < 3; attempt++) {
    let available = false, unauthorized = false;
    try {
      const probe = await fetch("/api/status", {cache: "no-store", signal: AbortSignal.timeout(20000)});
      unauthorized = probe.status === 401;
      if (probe.status === 200) available = (await probe.json())?.auth === "none";
    } catch {
      // A non-JSON response or failed request is not proof of keyless access.
    }
    if (started !== revision) return;
    setBypassAvailable(available);
    if (available || unauthorized) return;
    if (attempt < 2) await new Promise(resolve => setTimeout(resolve, 200 * (attempt + 1)));
  }
}

start();
setInterval(refresh, 3000);
setInterval(loadDevices, 5000);
