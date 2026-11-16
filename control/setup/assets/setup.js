"use strict";
// The setup page is deliberately small and dependency-free: it is served from a
// device that has no internet, over a network that is about to disappear.
const el = id => document.getElementById(id);
const SECTIONS = ["loading", "form-card", "security-handover", "handover", "uncertain", "failed", "online"];
let status = null;
let busy = false;
// A status request that started before a submission is no longer news: the
// answer it carries describes the device as it was before the person pressed
// the button. Rendering it replaced the form - and the advice just shown - with
// an older screen.
let generation = 0;
// True while the person is filling the form after a failure. Without it the
// 15-second poll re-rendered the failure screen and wiped the form mid-typing.
let editing = false;
// True from the moment the device accepted a change of the setup network's
// protection. The phase stays "hotspot" for that - nothing is being joined - so
// without this flag a poll would put the form back over the handover that says
// which network and password to reconnect with.
let switching = false;

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

// Rebuild the country list, keeping a chosen code selected. `other` also
// recreates the free-text field, so a poll does not make it vanish.
function buildCountries(selected, typed) {
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
  if (selected === "other") other.selected = true;
  select.append(other);
  if (selected === "other") ensureCountryCode(typed || "");
}

function ensureCountryCode(value) {
  let input = el("country-code");
  if (!input) {
    input = document.createElement("input");
    input.id = "country-code";
    input.maxLength = 2;
    input.placeholder = "GB";
    input.autocomplete = "off";
    input.style.marginTop = "8px";
    input.addEventListener("input", () => { input.value = input.value.toUpperCase(); });
    el("country").after(input);
  }
  if (value) input.value = value;
  return input;
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

// The <select> is a sibling of its <label>, not a child of it. closest() walks
// ancestors only, so it returned null here, the throw was swallowed by load()'s
// catch, and the page told the user it could not reach a device that had
// answered correctly. Both the first render and the retry path use this, so
// they cannot drift apart.
function showCountryField(needsCountry) {
  const label = document.querySelector('label[for="country"]');
  if (label) label.classList.toggle("hidden", !needsCountry);
  el("country").classList.toggle("hidden", !needsCountry);
  el("country-note").classList.toggle("hidden", !needsCountry);
}

function render() {
  if (switching) {
    // The radio is being changed underneath this page. Every status field that
    // is about to arrive describes the device as it was, so none of them is a
    // reason to take the handover away.
    show("security-handover");
    return;
  }
  el("device-name").textContent = status.hostname || "your Debra";
  // A development build raises the setup network with no password. Say so,
  // rather than leaving a person looking for a password that does not exist.
  const openSetup = status.security === "none";
  el("open-setup").classList.toggle("hidden", !openSetup);
  if (openSetup) {
    el("open-setup").textContent =
      "This is a development build: the setup network has no password.";
  }
  const host = status.hostname || "debra";
  el("device-url").textContent = `http://${host}.local:8787/`;
  el("device-name-again").textContent = host;
  el("footer-note").textContent = status.phase === "online"
    ? "This page only configures Wi-Fi. Everything else is on the device's own page."
    : "Only Wi-Fi details are accepted on this page. Nothing here changes your home router.";

  if (status.phase === "online") {
    editing = false;
    el("online-ssid").textContent = status.ssid || "your network";
    const list = el("online-values");
    list.replaceChildren();
    const rows = [
      ["Device name", host],
      ["Address", status.address || "not reported"],
      // Not "Setup page": this is the device's own control page, and it is a
      // different program that may not be installed yet. Calling it setup would
      // send a person looking for the page they are already on.
      ["Device page", `http://${host}.local:8787/`],
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
    // "not captured yet" with no reason reads as progress that is not
    // happening. The device says why, and says that a later boot retries.
    const note = el("baseline-note");
    note.textContent = status.baseline_error
      ? `The first baseline was not captured: ${status.baseline_error}. ` +
        "The device tries again on its next boot."
      : "";
    note.classList.toggle("hidden", !status.baseline_error);
    show("online");
    return;
  }
  if (status.phase === "connecting") {
    editing = false;
    el("hotspot-name").textContent = status.hotspot?.ssid || "the setup network";
    el("join-name").textContent = status.ssid || "your network";
    show("handover");
    return;
  }
  if (status.phase === "failed" && !editing) {
    el("failed-reason").textContent = status.last_error || "The device could not join that network.";
    show("failed");
    return;
  }
  // Keep what the person already chose, so a poll does not reset the form.
  // That includes "Other" plus the code typed beside it: the previous version
  // only preserved a two-letter dropdown value, so choosing Other and typing
  // "IS" was silently replaced by a blank select while the code stayed visible.
  const chosen = el("country").value;
  const typed = (el("country-code")?.value || "").toUpperCase();
  const keep = chosen === "other" ? "other"
    : (/^[A-Z]{2}$/.test(chosen) ? chosen : "");
  buildCountries(status.country || keep, keep === "other" ? typed : "");
  if (keep === "other") ensureCountryCode(typed);
  const needsCountry = !status.country;
  showCountryField(needsCountry);
  buildNetworkPicker(status.networks);
  renderSecurity();
  el("step-label").textContent = needsCountry ? "STEP 1 OF 2" : "ONE STEP";
  el("form-card").classList.toggle("hidden", false);
  show("form-card");
}

// How the setup network is protected, said in one line, with the one button
// that changes it. The button names the mode it leads to rather than the mode
// it is in, because "Bypass security" is only an answer to "password required".
function renderSecurity() {
  const open = status.security === "none";
  el("security-mode").textContent = open
    ? "Setup network: open (development build)"
    : "Setup network: password required";
  el("security-toggle").textContent = open ? "Require a password" : "Bypass security";
}

async function load() {
  const started = generation;
  try {
    const response = await fetch("/api/status", {cache: "no-store", signal: AbortSignal.timeout(8000)});
    if (!response.ok) throw new Error("The device did not answer");
    const answer = await response.json();
    if (started !== generation) return;
    status = answer;
    render();
  } catch {
    el("loading").querySelector("p").textContent =
      "This page could not reach the device. Reconnect to its setup network and reload.";
  }
}

// A beginner should not have to spell a network name from memory. The list is
// only what the radio saw before the access point went up; choosing an entry
// fills the text field, so typing still works and a hidden network still joins.
let pickerKey = null;
function buildNetworkPicker(networks) {
  const pick = el("ssid-pick");
  const label = el("ssid-pick-label");
  const note = el("ssid-pick-note");
  const offered = Array.isArray(networks) ? networks : [];
  // Rebuild only when the list actually changed. A 15-second poll otherwise
  // reset the selection a person had just made.
  const key = JSON.stringify(offered.map(item => [item?.ssid, item?.security]));
  if (key === pickerKey) return;
  pickerKey = key;
  pick.replaceChildren();
  const first = document.createElement("option");
  first.value = "";
  first.textContent = "Choose a network";
  pick.append(first);
  for (const network of offered) {
    if (!network || typeof network.ssid !== "string" || !network.ssid) continue;
    const option = document.createElement("option");
    option.value = network.ssid;
    const open = (network.security || "open").toLowerCase() === "open";
    option.textContent = network.ssid + (open ? " (no password)" : "");
    pick.append(option);
  }
  const usable = pick.options.length > 1;
  pick.classList.toggle("hidden", !usable);
  label.classList.toggle("hidden", !usable);
  note.classList.toggle("hidden", !usable);
}

el("ssid-pick").addEventListener("change", () => {
  const chosen = el("ssid-pick").value;
  if (!chosen) return;
  el("ssid").value = chosen;
  // A name that needs a password should lead straight to the password field.
  el("psk").focus();
});

el("country").addEventListener("change", () => {
  if (el("country").value === "other") {
    ensureCountryCode("").focus();
  } else {
    el("country-code")?.remove();
  }
});

el("join").addEventListener("click", async () => {
  if (busy) return;
  // The name is sent exactly as typed. Trimming it here silently joined a
  // different network: a name with a leading space is a different SSID on the
  // air, and the device was asked for the trimmed one.
  const ssid = el("ssid").value || "";
  const psk = el("psk").value || "";
  const country = countryValue();
  // Refused only when nothing was really typed. Spaces inside or around a name
  // are part of the name on the air, so they are sent exactly as typed; a field
  // of nothing but spaces means the person has not named a network.
  if (!ssid.trim()) { error("Enter the name of your Wi-Fi network."); return; }
  if (psk && psk.length < 8) { error("A Wi-Fi password is at least 8 characters."); return; }
  if (country === "") { error("Enter a two-letter country code, or choose one from the list."); return; }
  error("");
  busy = true;
  editing = false;
  generation += 1;
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
    // A 429 or a 400 means the form is still the right screen. Clearing the
    // editing flag here let the next poll replace the form - and the advice
    // just shown - with the previous failure card.
    editing = true;
    // The advice is useless on a hidden form: a poll may have swapped the card
    // for the failure screen while this request was in flight.
    show("form-card");
    error(data.error || "The device refused that request.");
  } catch {
    // A lost reply is ambiguous, not proof that the radio changed. The previous
    // version showed the handover card unconditionally, telling the person to
    // leave a setup network the device may never have touched.
    el("uncertain-ssid").textContent = ssid;
    el("uncertain-network").textContent = status?.hotspot?.ssid || "the setup network";
    show("uncertain");
  } finally {
    busy = false;
    el("join").disabled = false;
    el("join").textContent = "Join network";
  }
});

// Bypassing the password and putting one back are one button, because they are
// one decision. The device answers before it touches the radio, exactly like a
// join, so this page has to be able to say what to reconnect to on its own.
el("security-toggle").addEventListener("click", async () => {
  if (busy) return;
  const mode = status?.security === "wpa" ? "none" : "wpa";
  busy = true;
  el("security-toggle").disabled = true;
  el("security-error").textContent = "";
  try {
    const response = await fetch("/api/security", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({mode}),
      signal: AbortSignal.timeout(15000),
    });
    const data = await response.json().catch(() => ({}));
    if (response.status !== 202) {
      // A refusal changes nothing, so the form is still the right screen and
      // the advice belongs on it.
      el("security-error").textContent = data.error || "The device refused that request.";
      return;
    }
    showSecurityHandover(mode, data.ssid, data.password || null);
  } catch {
    // The reply is the last thing the setup network can carry. Losing it here
    // means the device is already changing, so say so rather than claim the
    // form is still current.
    showSecurityHandover(mode, status?.hotspot?.ssid || null, null);
  } finally {
    busy = false;
    el("security-toggle").disabled = false;
  }
});

function showSecurityHandover(mode, ssid, password) {
  switching = true;
  el("security-ssid").textContent = ssid || "the setup network";
  const protectedMode = mode === "wpa";
  el("security-password").textContent = password || "";
  el("security-password-line").classList.toggle("hidden", !(protectedMode && password));
  el("security-open-line").classList.toggle("hidden", protectedMode);
  // A password that was generated but did not arrive is not a password the
  // person can type. Saying where the copy is beats an empty field.
  el("security-missing").classList.toggle("hidden", !(protectedMode && !password));
  show("security-handover");
}

el("retry").addEventListener("click", () => {
  // The access point is back, so the page is reachable again: show the form
  // without a reload, and keep the last failure out of the way.
  editing = true;
  buildCountries(status?.country || "");
  showCountryField(!status?.country);
  // Keep the network name, which is probably right, and clear the password,
  // which is probably what was wrong.
  el("psk").value = "";
  error("");
  show("form-card");
  el("psk").focus();
});

load();
// Keep polling while connecting too: the access point is down then, the fetch
// simply fails, and when it comes back the page has to discover whether the
// join worked. Stopping at `connecting` left a reload as the only way to know.
// A recursive timeout rather than setInterval: a poll that takes longer than
// the interval cannot overlap the next one, and the delay is read each time so
// a browser test can shorten it. Fifteen seconds is a guess nothing here has
// measured against a real phone on a real access point.
const POLL_MS = () => Number(window.DEBRA_POLL_MS) || 15000;
function poll(delay) {
  setTimeout(async () => {
    if (!busy) await load();
    poll(POLL_MS());
  }, delay === undefined ? POLL_MS() : delay);
}
// Look again a second after the page opens: a join started on another device,
// or a reload while the device was still associating, is then picked up quickly
// instead of after a full interval.
poll(1000);
