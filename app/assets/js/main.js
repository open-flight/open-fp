import { api, connect } from "./socket.js";
import { StanceView, nearest } from "./stance.js";
import { EVENT_LABELS, TraceChart } from "./chart.js";
import { renderCards } from "./swings.js";
import { MetricsPanel } from "./metrics.js";

const $ = (id) => document.getElementById(id);
const G = 9.80665;
const STATE_TEXT = { idle: "Idle", address: "Address", armed: "Armed", swinging: "Swinging", review: "Captured" };

const stance = new StanceView($("stance"));
const chart = new TraceChart($("trace"));
const metrics = new MetricsPanel({ list: $("metrics"), help: $("metric-help"), sets: $("metric-sets"), units: $("metric-units") });
const app = {
  cfg: null,
  swings: [],
  replay: null,       // { swing, i, playing, speed }
  lastSwing: null,
  displayLead: null,
};

// -- header controls ---------------------------------------------------------

function setPressed(group, attr, value) {
  for (const b of document.querySelectorAll(`${group} [${attr}]`)) b.setAttribute("aria-pressed", String(b.getAttribute(attr) === String(value)));
}

async function loadConfig() {
  app.cfg = await api.config();
  stance.setConfig(app.cfg);
  setPressed(".bar .seg", "data-golfer", app.cfg.golfer);
}

document.querySelectorAll("[data-golfer]").forEach((b) =>
  b.addEventListener("click", async () => {
    try {
      app.cfg = await api.putConfig({ golfer: b.dataset.golfer });
      stance.setConfig(app.cfg);
      setPressed(".bar .seg", "data-golfer", app.cfg.golfer);
      if (app.replay) openReplay(app.replay.swing.id);
    } catch (e) { toast(`Couldn't change handedness: ${e.message}`); }
  }),
);

$("zero").addEventListener("click", async () => {
  try { await api.zero(); toast("Zeroed. Plates should read 0 with nobody on them."); }
  catch (e) { toast(`Couldn't zero: ${e.message}`); }
});

$("capture").addEventListener("click", async () => {
  const r = await api.trigger().catch(() => ({ ok: false }));
  toast(r.ok ? "Capturing…" : "Nothing to capture. Settle at address until the badge says Armed.");
});

document.querySelectorAll("[data-view]").forEach((b) =>
  b.addEventListener("click", () => {
    const view = b.dataset.view;
    setPressed(".tabs", "data-view", view);
    $("view-live").hidden = view !== "live";
    $("view-diag").hidden = view !== "diag";
    if (view === "live") stance.resize();
  }),
);

// -- live --------------------------------------------------------------------

function onLive(msg) {
  stance.pushLive(msg);
  chart.pushLive(msg);
  setState(msg.state);
  $("bw").textContent = msg.bw_n ? `${(msg.bw_n / G).toFixed(1)} kg` : "—";
  const lead = msg.lead_pct.filter((v) => v != null).at(-1);
  const panel = document.querySelector(".balance-panel");
  if (lead == null) {
    app.displayLead = null;
    panel.classList.add("empty");
    $("lead-pct").textContent = "—";
    $("trail-pct").textContent = "—";
    return;
  }
  panel.classList.remove("empty");
  app.displayLead = app.displayLead == null ? lead : app.displayLead + 0.5 * (lead - app.displayLead);
  if (app.replay) return;
  showBalance(app.displayLead);
}

function showBalance(lead) {
  $("lead-pct").textContent = `${Math.round(lead)}%`;
  $("trail-pct").textContent = `${100 - Math.round(lead)}%`;
  $("bar-lead").style.width = `${lead}%`;
}

function setState(state) {
  const el = $("state");
  if (el.dataset.state === state) return;
  el.dataset.state = state;
  $("state-text").textContent = STATE_TEXT[state] ?? state;
}

function onStatus(st) {
  const ok = st.rate_hz != null && st.rate_hz > 150;
  const link = $("link");
  link.classList.toggle("ok", ok);
  link.classList.toggle("bad", !ok);
  $("link-text").textContent = ok ? `Connected · ${Math.round(st.rate_hz)} Hz` : st.rate_hz ? `Weak link · ${Math.round(st.rate_hz)} Hz` : "No data from plates";
  renderDiagnostics(st);
}

// -- swings -------------------------------------------------------------------

async function refreshSwings() {
  app.swings = await api.swings();
  renderCards($("cards"), app.swings, app.replay?.swing.id);
  $("swing-count").textContent = app.swings.length ? `${app.swings.length}` : "";
  if (!app.lastSwing && app.swings.length) {
    app.lastSwing = app.swings[0];
    if (!app.replay) metrics.show(app.lastSwing, app.swings);
  }
}

function onSwing(summary) {
  app.lastSwing = summary;
  app.swings = [summary, ...app.swings.filter((s) => s.id !== summary.id)];
  renderCards($("cards"), app.swings, app.replay?.swing.id);
  $("cards").querySelector(`[data-id="${summary.id}"]`)?.classList.add("fresh");
  $("swing-count").textContent = `${app.swings.length}`;
  if (!app.replay) {
    metrics.show(summary, app.swings);
    $("metrics-title").textContent = "Last swing";
  }
  const m = summary.metrics;
  toast(`Swing captured · max lead ${Math.round(m.lead_pct_max_lead ?? 0)}% · 50/50 in ${m.time_max_trail_to_transition_ms ?? "—"} ms`, () => openReplay(summary.id));
}

function onSwingUpdated(summary) {
  app.swings = app.swings.map((s) => (s.id === summary.id ? summary : s));
  renderCards($("cards"), app.swings, app.replay?.swing.id);
  if (app.lastSwing?.id === summary.id && !app.replay) metrics.show(summary, app.swings);
  if (app.replay?.swing.id === summary.id) openReplay(summary.id);
}

$("cards").addEventListener("click", (e) => {
  const card = e.target.closest(".card");
  if (card) openReplay(card.dataset.id);
});

// -- replay -------------------------------------------------------------------

async function openReplay(id) {
  let swing;
  try { swing = await api.swing(id); } catch (e) { toast(`Couldn't load swing: ${e.message}`); return; }
  const speed = app.replay?.speed ?? 0.5;
  app.replay = { swing, i: 0, playing: false, speed };
  const lead = app.cfg.golfer === "LH" ? "R" : "L";
  stance.showReplay(swing);
  chart.showReplay(swing, lead);
  $("replay").hidden = false;
  $("stance-title").textContent = `Replay · ${new Date(swing.created).toLocaleTimeString()}`;
  $("trace-title").textContent = "Vertical force · swing";
  $("metrics-title").textContent = "This swing";
  $("csv").href = api.csvUrl(id);
  metrics.show(swing, app.swings);
  renderCards($("cards"), app.swings, id);
  renderChips(swing);
  const start = swing.events.motion_start ?? 0;
  seek(nearest(swing.arrays.t, Math.max(0, start - 0.3)));
  play(true);
}

function renderChips(swing) {
  $("event-chips").innerHTML = Object.entries(EVENT_LABELS).map(([name, label]) => {
    const t = swing.events[name];
    const dis = t == null ? ` disabled title="${name === "impact" ? "No shot event for this swing" : "Not detected"}"` : "";
    return `<button type="button" data-event="${name}"${dis}>${label}${t == null ? "" : `<span class="t">${t.toFixed(2)} s</span>`}</button>`;
  }).join("");
}

$("event-chips").addEventListener("click", (e) => {
  const b = e.target.closest("[data-event]");
  if (!b || !app.replay) return;
  play(false);
  seek(nearest(app.replay.swing.arrays.t, app.replay.swing.events[b.dataset.event]));
});

function seek(i) {
  const r = app.replay;
  const a = r.swing.arrays;
  r.i = Math.max(0, Math.min(a.t.length - 1, i));
  stance.setCursor(r.i);
  chart.setCursor(a.t[r.i]);
  $("scrub").value = String(Math.round((1000 * r.i) / (a.t.length - 1)));
  $("scrub-time").textContent = `${a.t[r.i].toFixed(2)} s`;
  const lead = a.lead_pct[r.i];
  if (lead != null) showBalance(lead);
}

function play(on) {
  const r = app.replay;
  if (!r) return;
  r.playing = on;
  $("play").textContent = on ? "❚❚" : "▶";
  $("play").setAttribute("aria-label", on ? "Pause" : "Play");
  if (!on) return;
  const a = r.swing.arrays;
  if (r.i >= a.t.length - 1) seek(0);
  let last = performance.now();
  let t = a.t[r.i];
  const step = (now) => {
    if (!app.replay || !r.playing || app.replay !== r) return;
    t += ((now - last) / 1000) * r.speed;
    last = now;
    const i = nearest(a.t, t);
    seek(i);
    if (i >= a.t.length - 1) return play(false);
    requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

$("play").addEventListener("click", () => play(!app.replay?.playing));
$("scrub").addEventListener("input", (e) => {
  if (!app.replay) return;
  play(false);
  seek(Math.round((Number(e.target.value) / 1000) * (app.replay.swing.arrays.t.length - 1)));
});
document.querySelectorAll("[data-speed]").forEach((b) =>
  b.addEventListener("click", () => {
    if (app.replay) app.replay.speed = Number(b.dataset.speed);
    setPressed("#replay .seg", "data-speed", b.dataset.speed);
  }),
);

function closeReplay() {
  if (app.replay) app.replay.playing = false;
  app.replay = null;
  stance.showLive();
  chart.showLive();
  $("replay").hidden = true;
  $("stance-title").textContent = "Stance";
  $("trace-title").textContent = "Vertical force · last 5 s";
  $("metrics-title").textContent = "Last swing";
  if (app.lastSwing) metrics.show(app.lastSwing, app.swings);
  renderCards($("cards"), app.swings, null);
}

$("back-live").addEventListener("click", closeReplay);
$("delete").addEventListener("click", async () => {
  const id = app.replay?.swing.id;
  if (!id || !confirm("Delete this swing? This can't be undone.")) return;
  await api.deleteSwing(id);
  if (app.lastSwing?.id === id) app.lastSwing = null;
  closeReplay();
  await refreshSwings();
  toast("Swing deleted.");
});

document.addEventListener("keydown", (e) => {
  if (!app.replay || e.target.closest("input, button")) return;
  if (e.key === " ") { e.preventDefault(); play(!app.replay.playing); }
  if (e.key === "ArrowRight") { play(false); seek(app.replay.i + 1); }
  if (e.key === "ArrowLeft") { play(false); seek(app.replay.i - 1); }
  if (e.key === "Escape") closeReplay();
});

// -- diagnostics ----------------------------------------------------------------

function renderDiagnostics(st) {
  const flag = (v, cls = "warn") => (v ? ` class="${cls}"` : "");
  const rows = [
    ["Frame rate", `${st.rate_hz ?? "—"} Hz`],
    ["Batches", st.batches],
    ["Sequence gaps", st.seq_gaps, st.seq_gaps > 0],
    ["Batches lost", st.seq_missing, st.seq_missing > 0],
    ["Dropped on Linux", st.dropped, st.dropped > 0],
    ["Decode errors", st.decode_errors, st.decode_errors > 0],
    ["MCU restarts", st.mcu_restarts, st.mcu_restarts > 0],
    ["Saturation", st.saturation ? "yes" : "no", st.saturation, "bad"],
    ["Missed DRDY", st.drdy_missed ? "yes" : "no", st.drdy_missed, "bad"],
    ["Calibration", st.calibrated ? (st.calibration_date ?? "yes").replace("T", " ") : "not calibrated", !st.calibrated],
    ["Tare drift", st.tare_drift_channels.length ? st.tare_drift_channels.join(", ") : "none", st.tare_drift_channels.length > 0],
  ];
  $("link-stats").innerHTML = rows.map(([k, v, bad, cls]) => `<dt>${k}</dt><dd${flag(bad, cls)}>${v}</dd>`).join("");
  $("channel-rows").innerHTML = st.channels.map((c) => {
    const frac = c.force_n == null ? 0 : Math.max(0, Math.min(1, c.force_n / (50 * G)));
    const f = (v, d = 0) => (v == null ? "—" : Number(v).toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: d }));
    return `<tr class="${c.id[0]}"><td>${c.id}</td><td>${f(c.counts)}</td><td>${f(c.tare)}</td><td>${f(c.noise_counts, 1)}</td><td>${f(c.force_n, 1)} N</td>
      <td><div class="cellbar"><i style="width:${(frac * 100).toFixed(1)}%"></i></div></td></tr>`;
  }).join("");
}

// -- toast --------------------------------------------------------------------------

let toastTimer;
function toast(text, onClick) {
  const el = $("toast");
  el.textContent = text;
  el.hidden = false;
  el.onclick = () => { el.hidden = true; onClick?.(); };
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 5000);
}

// -- boot -----------------------------------------------------------------------------

await loadConfig();
await refreshSwings();
connect({
  onConnect: () => { refreshSwings(); },
  onDisconnect: () => onStatus({ rate_hz: null, channels: [], tare_drift_channels: [] }),
  handlers: { live: onLive, status: onStatus, swing: onSwing, swing_updated: onSwingUpdated },
});
