"use strict";
// The setup page is deliberately small and dependency-free: it is served from a
// device that has no internet, over a network that is about to disappear.
const el = id => document.getElementById(id);
const SECTIONS = ["loading", "form-card", "handover", "uncertain", "failed", "online"];
let status = null;
let busy = false;
// A status request that started before a submission is no longer news: the
// answer it carries describes the device as it was before the person pressed
// the button. Rendering it replaced the form - and the advice just shown - with
// an older screen.
let generation = 0;
// The state revision the person submitted from. A status answer that began
// before the submission is stale only if it is not newer than this. Comparing
// request start time with answer age discarded a genuinely new answer - a GET
// started before the POST can receive the state the POST produced, and on a
// single-radio handover there may be no later poll to repair that.
let submittedRevision = null;
// The revision of the answer currently on screen. It only moves forward, so an
// answer that is older than what the page already shows can never replace it.
// Ordering against the submission alone let two answers resolve out of order:
// the newer failure appeared, then an older "still waiting" answer redrew the
// form over it, because it had started after the submission.
let lastRevision = null;
// True only while the person has asked the uncertain card to check again. In
// that case even an answer with the same revision is useful: it says the device
// never received the request, which is exactly what the card cannot tell.
let reconciling = false;
// True while the person is filling the form after a failure. Without it the
// 15-second poll re-rendered the failure screen and wiped the form mid-typing.
let editing = false;

function newerThanSubmit(answer) {
  return typeof answer.revision === "number"
    && typeof submittedRevision === "number"
    && answer.revision > submittedRevision;
}

function acceptable(answer, started) {
  // "Ask the device again" deliberately wants the same-revision answer: it is
  // the proof that the device never received the request.
  if (reconciling) return true;
  const fresh = typeof answer.revision === "number";
  if (fresh && typeof lastRevision === "number" && answer.revision <= lastRevision) {
    // Not newer than the screen already showing. This is what stops two
    // overlapping answers from resolving out of order, and it is why a request
    // that started after the submission cannot restore a pre-submission form
    // over the handover card: its revision is the one already drawn from.
    return false;
  }
  // A request that began after the submission is news, unless it is older by
  // revision, which is refused above.
  return started === generation || (fresh && newerThanSubmit(answer));
}

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
  el("device-name").textContent = status.hostname || "your Debra";
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
  el("step-label").textContent = needsCountry ? "STEP 1 OF 2" : "ONE STEP";
  el("form-card").classList.toggle("hidden", false);
  show("form-card");
}

async function load() {
  const started = generation;
  try {
    const response = await fetch("/api/status", {cache: "no-store", signal: AbortSignal.timeout(8000)});
    if (!response.ok) throw new Error("The device did not answer");
    const answer = await response.json();
    if (!acceptable(answer, started)) return;
    if (typeof answer.revision === "number") {
      // Forward only. A regression here would let the next older answer be
      // accepted as if it were new.
      lastRevision = typeof lastRevision === "number"
        ? Math.max(lastRevision, answer.revision) : answer.revision;
    }
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
  submittedRevision = lastRevision;
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

// The uncertain card used to have no way out except the next poll or a manual
// reload. It now asks the device directly. The answer with the same revision is
// the useful one here: it proves the device never received the request.
el("check-again").addEventListener("click", async () => {
  el("check-again").disabled = true;
  reconciling = true;
  try {
    await load();
  } finally {
    reconciling = false;
    el("check-again").disabled = false;
  }
});

el("start-over").addEventListener("click", () => location.reload());

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
