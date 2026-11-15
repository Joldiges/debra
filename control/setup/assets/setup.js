"use strict";
// The setup page is deliberately small and dependency-free: it is served from a
// device that has no internet, over a network that is about to disappear.
const el = id => document.getElementById(id);
const SECTIONS = ["loading", "form-card", "handover", "failed", "online"];
let status = null;
let busy = false;

// A short list covers most homes; "Other" swaps to a two-letter code so no
// country is unreachable rather than silently missing from a long dropdown.
const COUNTRIES = [
  ["GB", "United Kingdom"], ["IE", "Ireland"], ["US", "United States"],
  ["CA", "Canada"], ["AU", "Australia"], ["NZ", "New Zealand"],
  ["DE", "Germany"], ["FR", "France"], ["NL", "Netherlands"], ["BE", "Belgium"],
  ["ES", "Spain"], ["PT", "Portugal"], ["IT", "Italy"], ["CH", "Switzerland"],
  ["AT", "Austria"], ["SE", "Sweden"], ["NO", "Norway"], ["DK", "Denmark"],
  ["FI", "Finland"], ["PL", "Poland"], ["CZ", "Czechia"], ["GR", "Greece"],
  ["TR", "Türkiye"], ["ZA", "South Africa"], ["BR", "Brazil"], ["MX", "Mexico"],
  ["AR", "Argentina"], ["IN", "India"], ["JP", "Japan"], ["KR", "South Korea"],
  ["CN", "China"], ["SG", "Singapore"], ["HK", "Hong Kong"], ["AE", "United Arab Emirates"],
  ["IL", "Israel"], ["SA", "Saudi Arabia"],
];

function show(id) {
  for (const name of SECTIONS) el(name).classList.toggle("hidden", name !== id);
}

function buildCountries(selected) {
  const select = el("country");
  select.replaceChildren();
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "Choose a country";
  select.append(blank);
  for (const [code, name] of COUNTRIES) {
    const option = document.createElement("option");
    option.value = code;
    option.textContent = name;
    if (code === selected) option.selected = true;
    select.append(option);
  }
  const other = document.createElement("option");
  other.value = "other";
  other.textContent = "Other (enter a code)";
  select.append(other);
}

function countryValue() {
  const select = el("country");
  if (select.value !== "other") return select.value || null;
  const typed = (el("country-code").value || "").trim().toUpperCase();
  return /^[A-Z]{2}$/.test(typed) ? typed : "";
}

function error(text) {
  el("form-error").textContent = text || "";
}

function render() {
  el("device-name").textContent = status.hostname || "your Debra";
  const host = status.hostname || "debra";
  el("device-url").textContent = `http://${host}.local:8787/`;
  el("footer-note").textContent = status.phase === "online"
    ? "This page only configures Wi-Fi. Everything else is on the device's own page."
    : "Only Wi-Fi details are accepted on this page. Nothing here changes your home router.";

  if (status.phase === "online") {
    el("online-ssid").textContent = status.ssid || "your network";
    const list = el("online-values");
    list.replaceChildren();
    const rows = [
      ["Device name", host],
      ["Address", status.address || "not reported"],
      ["Setup page", `http://${host}.local:8787/`],
      ["Baseline", status.baseline ? "captured" : "not captured yet"],
    ];
    for (const [label, value] of rows) {
      const row = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = label;
      dd.textContent = value;
      row.append(dt, dd);
      list.append(row);
    }
    show("online");
    return;
  }
  if (status.phase === "connecting") {
    el("hotspot-name").textContent = status.hotspot?.ssid || "the setup network";
    el("join-name").textContent = status.ssid || "your network";
    show("handover");
    return;
  }
  if (status.phase === "failed") {
    el("failed-reason").textContent = status.last_error || "The device could not join that network.";
    show("failed");
    return;
  }
  buildCountries(status.country || "");
  const needsCountry = !status.country;
  el("country").closest("label").classList.toggle("hidden", !needsCountry);
  el("country").classList.toggle("hidden", !needsCountry);
  el("country-note").classList.toggle("hidden", !needsCountry);
  el("step-label").textContent = needsCountry ? "STEP 1 OF 2" : "ONE STEP";
  el("form-card").classList.toggle("hidden", false);
  show("form-card");
}

async function load() {
  try {
    const response = await fetch("/api/status", {cache: "no-store", signal: AbortSignal.timeout(8000)});
    if (!response.ok) throw new Error("The device did not answer");
    status = await response.json();
    render();
  } catch {
    el("loading").querySelector("p").textContent =
      "This page could not reach the device. Reconnect to its setup network and reload.";
  }
}

el("country").addEventListener("change", () => {
  const other = el("country").value === "other";
  if (other && !el("country-code")) {
    const input = document.createElement("input");
    input.id = "country-code";
    input.maxLength = 2;
    input.placeholder = "GB";
    input.autocomplete = "off";
    input.style.marginTop = "8px";
    input.addEventListener("input", () => { input.value = input.value.toUpperCase(); });
    el("country").after(input);
    input.focus();
  } else if (!other) {
    el("country-code")?.remove();
  }
});

el("join").addEventListener("click", async () => {
  if (busy) return;
  const ssid = (el("ssid").value || "").trim();
  const psk = el("psk").value || "";
  const country = countryValue();
  if (!ssid) { error("Enter the name of your Wi-Fi network."); return; }
  if (psk && psk.length < 8) { error("A Wi-Fi password is at least 8 characters."); return; }
  if (country === "") { error("Enter a two-letter country code, or choose one from the list."); return; }
  error("");
  busy = true;
  el("join").disabled = true;
  el("join").textContent = "Sending…";
  try {
    const response = await fetch("/api/join", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ssid, psk: psk || null, country: country || null}),
      signal: AbortSignal.timeout(15000),
    });
    if (response.status === 202) {
      el("hotspot-name").textContent = status.hotspot?.ssid || "the setup network";
      el("join-name").textContent = ssid;
      show("handover");
      return;
    }
    const data = await response.json().catch(() => ({}));
    error(data.error || "The device refused that request.");
  } catch {
    // Losing the reply here is expected once the access point drops; the
    // handover screen already explains what happens next.
    show("handover");
  } finally {
    busy = false;
    el("join").disabled = false;
    el("join").textContent = "Join network";
  }
});

el("retry").addEventListener("click", () => {
  // The access point is back, so the page is reachable again: show the form
  // without a reload, and keep the last failure out of the way.
  buildCountries(status?.country || "");
  const needsCountry = !status?.country;
  el("country").classList.toggle("hidden", !needsCountry);
  el("country-note").classList.toggle("hidden", !needsCountry);
  error("");
  show("form-card");
});

load();
setInterval(() => { if (!busy && status?.phase !== "connecting") load(); }, 15000);
