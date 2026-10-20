#!/usr/bin/env python3
"""Live browser view of the cells on bench/ads1220_all (one carrier per plate, or both).

    .venv/bin/python tools/bench/live_multi.py                  # plate L: http://localhost:7072
    .venv/bin/python tools/bench/live_multi.py --channels R     # plate R: R1-R4
    .venv/bin/python tools/bench/live_multi.py --channels all   # both plates

Streams `arduino-app-cli monitor` over SSH and pushes each 100 ms window to the page with
server-sent events. The page shows each cell's load since tare on a plan of its plate, the
total, the centre of pressure on each plate (toe/heel and inner/outer), the left/right split
when both plates are shown, and a 30 s chart. Corner positions come from open_fp.config's
defaults. Counts become kg with one shared counts-per-kg factor: put a known weight on (or
stand on the plates) and press Calibrate. Standard library only (plus open_fp.config); the
chart uses app/assets/vendor/uPlot.
"""

from __future__ import annotations

import argparse
import json
import queue
import signal
import sys
import threading
import webbrowser
from dataclasses import asdict
from http.server import ThreadingHTTPServer
from pathlib import Path

from live_view import Hub, make_handler
from multi_cell import (
    CHANNELS,
    DEFAULT_CHANNELS,
    ChanReadback,
    ChanVoltage,
    Window,
    parse_channels,
    parse_line,
)
from single_cell import ModeLine, Monitor, SketchError

KEYS = ("d", "s", "v", "r")  # keystrokes ads1220_all understands (minus the raw dump)
APP_PYTHON = Path(__file__).resolve().parents[2] / "app" / "python"


def title(channels: list[str]) -> str:
    """'Plate L', 'Both plates', or the channel names for any other set."""
    for plate in ("L", "R"):
        if channels == [ch for ch in CHANNELS if ch[0] == plate]:
            return f"Plate {plate}"
    if sorted(channels) == sorted(CHANNELS):
        return "Both plates"
    return " ".join(channels)


def layout(channels: list[str]) -> dict:
    """What the page draws: every corner of each plate in use, from open_fp.config's geometry.

    Stance frame (mm): +x from plate L toward plate R, +y toward the toe. `on` marks the
    corners in `channels`; the others are drawn as empty sockets.
    """
    if str(APP_PYTHON) not in sys.path:
        sys.path.insert(0, str(APP_PYTHON))
    from open_fp.config import CHANNEL_IDS, Config

    cfg = Config()
    half = cfg.plate_spacing_mm / 2
    centre = {"L": -half, "R": half}
    plates = [p for p in ("L", "R") if any(ch[0] == p for ch in channels)]
    cells = []
    for ch, (x, y) in zip(CHANNEL_IDS, cfg.positions()):
        if ch[0] not in plates:
            continue
        outward = (x - centre[ch[0]]) * (-1 if ch[0] == "L" else 1)
        cells.append(
            {
                "ch": ch,
                "plate": ch[0],
                "x": round(x, 1),
                "y": round(y, 1),
                "desc": f"{'toe' if y > 0 else 'heel'}, {'outer' if outward > 0 else 'inner'}",
                "on": ch in channels,
            }
        )
    name = title(channels)
    return {
        "title": name,
        "total_of": name[0].lower() + name[1:] if name.startswith(("Plate", "Both")) else name,
        "plates": plates,
        "centre": {p: round(centre[p], 1) for p in plates},
        "offset": cfg.cell_offset_mm,
        "cells": cells,
    }


def render_page(channels: list[str]) -> str:
    """PAGE with the layout for `channels` filled in."""
    lay = layout(channels)
    return PAGE.replace("__TITLE__", lay["title"]).replace("__LAYOUT__", json.dumps(lay))


def to_event(item) -> str:
    """A parsed ads1220_all line as a JSON event for the browser."""
    if isinstance(item, Window):
        chans = {ch: asdict(s) for ch, s in item.chans.items()}
        return json.dumps(
            {"type": "window", "ms": item.ms, "ticks": item.ticks, "drdy": item.drdy, "chans": chans}
        )
    if isinstance(item, ChanReadback):
        regs = " ".join(f"{r:02X}" for r in item.regs)
        return json.dumps({"type": "readback", "ch": item.ch, "ok": item.ok, "regs": regs})
    if isinstance(item, ChanVoltage):
        return json.dumps({"type": "voltage", "ch": item.ch, "name": item.name, "value": item.value})
    if isinstance(item, ModeLine):
        return json.dumps({"type": "mode", "name": item.name})
    if isinstance(item, SketchError):
        return json.dumps({"type": "error", "message": item.message})
    return json.dumps({"type": "unknown"})


class MultiHub(Hub):
    """Hub that replays the latest readback and voltage per channel to a newly opened page."""

    def publish(self, event: str):
        e = json.loads(event)
        key = e["type"]
        if key == "readback":
            key = "readback:" + e["ch"]
        elif key == "voltage":
            key = f"voltage:{e['ch']}:{e['name']}"
        with self._lock:
            if key == "mode" or key.startswith(("readback:", "voltage:")):
                self._latest[key] = event
            for q in self._clients:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    pass  # a stalled page just misses some windows


def pump(mon: Monitor, hub: Hub):
    while True:
        item = mon.q.get()
        if item is None:
            hub.publish(json.dumps({"type": "closed"}))
            return
        hub.publish(to_event(item))


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>__TITLE__ live</title>
<link rel="stylesheet" href="/uPlot.min.css" />
<style>
  :root { --bg:#0B0F14; --panel:#121821; --line:#1E2733; --edge:#2A3544; --text:#D7DEE7; --muted:#7A8796;
          --bad:#E5676B; --L1:#2EC4B6; --L2:#4EA8DE; --L3:#A78BFA; --L4:#8AC926;
          --R1:#FF9F1C; --R2:#F15BB5; --R3:#FFD166; --R4:#F4845F; --tot:#EDEFF2; color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text);
         font:14px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  header { display:flex; gap:16px; align-items:center; padding:12px 20px; border-bottom:1px solid var(--line); flex-wrap:wrap; }
  h1 { font-size:16px; margin:0 8px 0 0; }
  .pill { color:var(--muted); font-variant-numeric:tabular-nums; }
  .pill b { color:var(--text); font-weight:600; }
  .dot { display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--muted); margin-right:6px; }
  .ok .dot { background:var(--L1); } .bad .dot { background:var(--bad); }
  main { display:grid; grid-template-columns: minmax(0,1.15fr) minmax(0,1fr); gap:12px; padding:12px 20px; }
  section { background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:14px; min-width:0; }
  .wide { grid-column: 1 / -1; }
  .label { font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); font-weight:600; }
  .num { font-variant-numeric:tabular-nums; }
  .big { font-size:72px; font-weight:250; letter-spacing:-.03em; line-height:1; margin:6px 0 2px; }
  .big small { font-size:24px; color:var(--muted); margin-left:6px; }
  .sub { color:var(--muted); }
  [hidden] { display:none !important; }
  /* plates */
  .plates { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:12px; }
  .plates.one { grid-template-columns:minmax(0, 320px); justify-content:center; }
  .plate { position:relative; aspect-ratio: 0.82; border:1px solid var(--edge); border-radius:8px;
           background:repeating-linear-gradient(135deg, #10161E 0 10px, #0E141B 10px 20px); }
  .plate .name { position:absolute; left:0; right:0; top:46%; text-align:center; color:#3A4656;
                 font-size:13px; letter-spacing:.2em; font-weight:700; }
  .cell { position:absolute; width:31%; aspect-ratio:1; border-radius:50%; border:2px solid var(--c);
          display:flex; flex-direction:column; align-items:center; justify-content:center; overflow:hidden;
          background:var(--bg); transform:translate(-50%,-50%); }
  .cell .fill { position:absolute; left:0; right:0; bottom:0; height:0; background:var(--c); opacity:.28; transition:height .1s linear; }
  .cell .id { position:relative; font-size:11px; font-weight:700; letter-spacing:.08em; color:var(--c); }
  .cell .v { position:relative; font-size:20px; font-weight:500; }
  .cell .n { position:relative; font-size:10px; color:var(--muted); }
  .cell.off { border-style:dashed; opacity:.45; }
  .socket { position:absolute; width:18%; aspect-ratio:1; border-radius:50%; border:1px dashed #2A3544;
            transform:translate(-50%,-50%); }
  .edge-tag { position:absolute; left:0; right:0; text-align:center; font-size:10px; color:var(--muted); letter-spacing:.1em; }
  .edge-tag.toe { top:4px; } .edge-tag.heel { bottom:4px; }
  .cop { position:absolute; width:16px; height:16px; border-radius:50%; background:var(--tot);
         transform:translate(-50%,-50%); transition:left .1s linear, top .1s linear; box-shadow:0 0 0 3px #0B0F14; z-index:2; }
  .cop.idle { opacity:.15; }
  /* split */
  .split { display:flex; height:30px; border-radius:6px; overflow:hidden; margin-top:8px; border:1px solid var(--edge); }
  .split div { display:flex; align-items:center; padding:0 10px; font-weight:600; font-variant-numeric:tabular-nums;
               transition:flex-grow .1s linear; color:var(--bg); white-space:nowrap; min-width:0; }
  .split .l { background:var(--L2); flex:1 1 0; } .split .r { background:var(--R1); flex:1 1 0; justify-content:flex-end; }
  .coplines div { margin-top:4px; }
  /* controls */
  button { font:inherit; color:var(--text); background:transparent; border:1px solid var(--edge); border-radius:6px;
           min-height:40px; padding:0 12px; cursor:pointer; margin:0 6px 6px 0; }
  button:hover { border-color:var(--muted); }
  button:focus-visible, input:focus-visible { outline:2px solid var(--L1); outline-offset:2px; }
  button.primary { background:var(--L1); color:var(--bg); border-color:var(--L1); font-weight:600; }
  input { width:84px; font:inherit; color:var(--text); background:var(--bg); border:1px solid var(--edge); border-radius:4px; padding:6px; }
  .row { display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin-top:10px; }
  .row button { margin:0; }
  table { width:100%; border-collapse:collapse; margin-top:10px; font-variant-numeric:tabular-nums; font-size:13px; }
  th, td { padding:4px 6px; text-align:right; border-bottom:1px solid var(--line); }
  th:first-child, td:first-child { text-align:left; }
  th { color:var(--muted); font-weight:600; font-size:11px; letter-spacing:.06em; }
  .legend { display:flex; gap:14px; flex-wrap:wrap; margin-top:6px; font-size:12px; color:var(--muted); }
  .legend i { display:inline-block; width:12px; height:3px; background:var(--c); margin-right:6px; vertical-align:middle; }
  #chart { min-height:300px; }
  #log { color:var(--bad); font-size:12px; margin-top:8px; min-height:1em; }
  .u-legend { display:none; }
  @media (max-width: 900px) { main { grid-template-columns: 1fr; padding:12px 16px; } .big { font-size:56px; } }
</style>
</head>
<body>
<header>
  <h1>__TITLE__ live</h1>
  <span id="link" class="pill"><span class="dot"></span><span id="linktext">connecting…</span></span>
  <span class="pill">mode <b id="mode">?</b></span>
  <span class="pill">rate <b id="rate">–</b> Hz</span>
  <span class="pill">answering <b id="answering">–</b></span>
</header>
<main>
  <section>
    <div class="label">Total on <span id="totalof"></span></div>
    <div class="big num"><span id="total">–</span><small id="unit">kg</small></div>
    <div class="sub num" id="totalsub">waiting for data…</div>
    <div class="plates" id="plates"></div>
  </section>
  <section>
    <div id="splitbox" hidden>
      <div class="label">Left / right</div>
      <div class="split"><div class="l" id="splitL">–</div><div class="r" id="splitR">–</div></div>
    </div>
    <div class="label" style="margin-top:18px">Centre of pressure</div>
    <div class="sub num coplines" id="coplines">–</div>

    <div class="label" style="margin-top:18px">Zero and scale</div>
    <div class="row">
      <button class="primary" id="tare" title="Zero every cell with nothing on the plates">Tare</button>
      <label class="sub" for="known">Known load</label>
      <input id="known" type="number" min="0.5" step="0.1" placeholder="kg" />
      <button id="cal" title="With the known weight on the cells, set counts per kg from the current total">Calibrate</button>
    </div>
    <div class="row sub num">
      <label for="cpk">counts per kg</label><input id="cpk" type="number" min="1" step="1" />
      <span id="calnote">rough default until calibrated</span>
    </div>
    <div class="row">
      <button data-key="v" title="Each ADC measures its own supply, reference and inputs">Voltage check</button>
      <button data-key="r" title="Re-read every ADC's registers">Re-check ADCs</button>
    </div>
    <table>
      <thead><tr><th>Cell</th><th>Readback</th><th>Noise</th><th>AIN0</th><th>AIN1</th><th>REF</th></tr></thead>
      <tbody id="units"></tbody>
    </table>
    <div id="log" role="status"></div>
  </section>
  <section class="wide">
    <div class="label">Last 30 s (100 ms averages)</div>
    <div class="legend" id="legend"></div>
    <div id="chart"></div>
  </section>
</main>
<script src="/uPlot.iife.min.js"></script>
<script>
const $ = (id) => document.getElementById(id);
// Filled in by live_multi.py from open_fp.config: stance frame in mm, +x toward plate R, +y toward the toe.
const LAYOUT = __LAYOUT__;
const CELLS = LAYOUT.cells.filter((c) => c.on);
const PLATES = LAYOUT.plates, BOTH = PLATES.length === 2;
const PLATE_NAME = { L: "LEFT", R: "RIGHT" };
const COLOR = (ch) => getComputedStyle(document.documentElement).getPropertyValue("--" + ch).trim();
const N = 300, SETTLE = 5, AVG = 5;
const DEFAULT_CPK = { differential: 20000, "single-ended": 120 };
const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } },
                set(k, v) { try { localStorage.setItem(k, v); } catch {} } };

let mode = null, settle = SETTLE, t0 = null, tare = null;
const recent = Object.fromEntries(CELLS.map((c) => [c.ch, []]));
const noise = {};
const xs = [], series = Object.fromEntries([...CELLS.map((c) => c.ch), "tot"].map((k) => [k, []]));

// plan view: corners sit at ±offset from the plate centre, drawn at 22/78 % across and 18/82 % down
function planLeft(p, x) { return 50 + ((x - LAYOUT.centre[p]) / LAYOUT.offset) * 28; }
function planTop(y) { return 50 - (y / LAYOUT.offset) * 32; }
function clamp(v) { return Math.max(3, Math.min(97, v)); }
$("plates").classList.toggle("one", !BOTH);
$("totalof").textContent = LAYOUT.total_of;
for (const p of PLATES) {
  $("plates").insertAdjacentHTML("beforeend",
    `<div class="plate" id="plate${p}"><div class="edge-tag toe">TOE ▲</div><div class="name">${PLATE_NAME[p]}</div>` +
    `<div class="edge-tag heel">HEEL</div><div class="cop idle" id="cop${p}"></div></div>`);
}
for (const c of LAYOUT.cells) {
  const where = `left:${planLeft(c.plate, c.x)}%;top:${planTop(c.y)}%`;
  if (!c.on) {
    $("plate" + c.plate).insertAdjacentHTML("beforeend", `<div class="socket" style="${where}" title="${c.ch} (${c.desc}): not in --channels"></div>`);
    continue;
  }
  $("plate" + c.plate).insertAdjacentHTML("beforeend",
    `<div class="cell off" id="cell-${c.ch}" style="--c:var(--${c.ch});${where}" title="${c.ch}: ${c.desc}">
       <div class="fill"></div><div class="id">${c.ch}</div><div class="v num">–</div><div class="n num"></div></div>`);
  $("units").insertAdjacentHTML("beforeend",
    `<tr id="u-${c.ch}"><td style="color:var(--${c.ch});font-weight:700">${c.ch}</td><td class="rb">–</td><td class="nz">–</td>
       <td data-v="AIN0">–</td><td data-v="AIN1">–</td><td data-v="REF">–</td></tr>`);
}
$("splitbox").hidden = !BOTH;

$("legend").innerHTML = [...CELLS.map((c) => c.ch), "total"].map((k) =>
  `<span><i style="--c:var(--${k === "total" ? "tot" : k})"></i>${k}</span>`).join("");

const chart = new uPlot({
  width: $("chart").clientWidth, height: 300, legend: { show: false }, cursor: { show: false },
  scales: { x: { time: false } },
  axes: [
    { stroke: "#7A8796", grid: { stroke: "#1E2733" }, values: (u, v) => v.map((s) => s.toFixed(0) + " s") },
    { stroke: "#7A8796", grid: { stroke: "#1E2733" }, size: 70, values: (u, v) => v.map((c) => fmtUnit(c)) },
  ],
  series: [{}, ...CELLS.map((c) => ({ stroke: COLOR(c.ch), width: 1.5 })), { stroke: COLOR("tot"), width: 2.5 }],
}, [[], ...CELLS.map(() => []), []], $("chart"));
new ResizeObserver(() => chart.setSize({ width: $("chart").clientWidth, height: 300 })).observe($("chart"));

// scale
function cpk() { return Number($("cpk").value) || 0; }
function toUnit(counts) { const k = cpk(); return k ? counts / k : counts; }
function fmtUnit(v) { return cpk() ? v.toFixed(Math.abs(v) < 10 ? 1 : 0) : Math.round(v).toLocaleString(); }
$("cpk").oninput = () => { store.set("openfp.cpk." + mode, $("cpk").value); $("calnote").textContent = "set by hand"; resetChart(); };

function loads() {  // counts since tare, positive under load (these cells read lower when pressed)
  const out = {};
  for (const c of CELLS) {
    const r = recent[c.ch];
    if (!r.length || !tare || tare[c.ch] === undefined) continue;
    out[c.ch] = tare[c.ch] - r[r.length - 1];
  }
  return out;
}
function avg(a) { return a.reduce((s, v) => s + v, 0) / a.length; }
function doTare() {
  if (CELLS.some((c) => recent[c.ch].length === 0)) return;
  tare = Object.fromEntries(CELLS.map((c) => [c.ch, avg(recent[c.ch].slice(-AVG))]));
  resetChart();
}
function resetChart() { xs.length = 0; for (const k in series) series[k].length = 0; t0 = null; }
$("tare").onclick = doTare;
$("cal").onclick = () => {
  const kg = Number($("known").value);
  const l = loads(), total = Object.values(l).reduce((s, v) => s + v, 0);
  if (!kg || !tare) return say("Tare with the plates empty first, then put the known load on and enter its kg.");
  if (total <= 0) return say("The total hasn't gone up since tare: is the load on the cells?");
  $("cpk").value = Math.round(total / kg);
  store.set("openfp.cpk." + mode, $("cpk").value);
  $("calnote").textContent = `calibrated with ${kg} kg`;
  resetChart();
};
document.querySelectorAll("[data-key]").forEach((b) => (b.onclick = () => fetch("/key/" + b.dataset.key, { method: "POST" })));
function say(msg) { $("log").textContent = msg; setTimeout(() => ($("log").textContent = ""), 5000); }

// Centre of pressure of the cells in `cells`, from positive loads only: { w, x, y } in mm, or null.
function cop(cells, l) {
  let w = 0, x = 0, y = 0;
  for (const c of cells) { const v = Math.max(0, l[c.ch] ?? 0); w += v; x += v * c.x; y += v * c.y; }
  return w > 0 ? { w, x: x / w, y: y / w } : null;
}
function mm(v, pos, neg) { return `${Math.abs(v).toFixed(0)} mm ${v >= 0 ? pos : neg}`; }

function onWindow(e) {
  if (settle > 0) { settle--; return; }
  for (const c of CELLS) {
    const s = e.chans[c.ch];
    $("cell-" + c.ch).classList.toggle("off", !s);
    if (!s) continue;
    recent[c.ch].push(s.mean); if (recent[c.ch].length > 20) recent[c.ch].shift();
    noise[c.ch] = s.std;
  }
  $("rate").textContent = ((e.drdy || e.ticks) * 10).toLocaleString();
  if (!tare && CELLS.every((c) => recent[c.ch].length >= AVG)) doTare();
  if (!tare) return;

  const l = loads();
  const total = Object.values(l).reduce((s, v) => s + v, 0);
  const totalNoise = Math.sqrt(CELLS.reduce((s, c) => s + (noise[c.ch] || 0) ** 2, 0));
  const loaded = total > Math.max(10 * totalNoise, cpk() ? 0.5 * cpk() : 0);
  $("total").textContent = fmtUnit(toUnit(total));
  $("unit").textContent = cpk() ? "kg" : "counts";
  $("totalsub").textContent = loaded ? "since tare" : "unloaded (since tare)";
  const peak = Math.max(...CELLS.map((c) => Math.abs(l[c.ch] ?? 0)), cpk() ? 20 * cpk() : 1);
  for (const c of CELLS) {
    const el = $("cell-" + c.ch), v = l[c.ch];
    if (v === undefined) continue;
    el.querySelector(".v").textContent = fmtUnit(toUnit(v));
    el.querySelector(".n").textContent = "± " + fmtUnit(toUnit(noise[c.ch] || 0));
    el.querySelector(".fill").style.height = Math.max(0, Math.min(100, (100 * v) / peak)) + "%";
    const row = $("u-" + c.ch);
    row.querySelector(".nz").textContent = (noise[c.ch] ?? 0).toLocaleString();
  }

  // per plate: where the load sits relative to the plate centre (toe/heel, inner/outer)
  const lines = [], w = {};
  for (const p of PLATES) {
    const k = cop(CELLS.filter((c) => c.plate === p), l), dot = $("cop" + p);
    w[p] = k ? k.w : 0;
    if (!loaded || !k) { dot.classList.add("idle"); continue; }
    dot.classList.remove("idle");
    dot.style.left = clamp(planLeft(p, k.x)) + "%"; dot.style.top = clamp(planTop(k.y)) + "%";
    const out = (k.x - LAYOUT.centre[p]) * (p === "L" ? -1 : 1);  // + toward the plate's outer edge
    lines.push(`Plate ${p}: ${mm(k.y, "toe", "heel")}, ${mm(out, "outer", "inner")} of centre`);
  }
  if (loaded && BOTH) {
    const k = cop(CELLS, l);
    if (k) lines.push(`Both: ${mm(k.x, "toward R", "toward L")} of the centre line, ${mm(k.y, "toe", "heel")}`);
  }
  $("coplines").innerHTML = lines.length ? lines.map((s) => `<div>${s}</div>`).join("") : "put some load on";
  if (!$("splitbox").hidden) {
    const left = w.L || 0, right = w.R || 0;
    if (loaded && left + right > 0) {
      const lp = (100 * left) / (left + right);
      $("splitL").style.flexGrow = lp; $("splitR").style.flexGrow = 100 - lp;
      $("splitL").textContent = `L ${lp.toFixed(0)} %`; $("splitR").textContent = `${(100 - lp).toFixed(0)} % R`;
    } else {
      $("splitL").style.flexGrow = 1; $("splitR").style.flexGrow = 1;
      $("splitL").textContent = "L –"; $("splitR").textContent = "– R";
    }
  }

  if (t0 === null) t0 = e.ms;
  xs.push((e.ms - t0) / 1000);
  for (const c of CELLS) series[c.ch].push(l[c.ch] === undefined ? null : toUnit(l[c.ch]));
  series.tot.push(toUnit(total));
  if (xs.length > N) { xs.shift(); for (const k in series) series[k].shift(); }
  chart.setData([xs, ...CELLS.map((c) => series[c.ch]), series.tot]);
}

const answering = {};
const es = new EventSource("/events");
es.onopen = () => { $("link").className = "pill ok"; $("linktext").textContent = "connected"; };
es.onerror = () => { $("link").className = "pill bad"; $("linktext").textContent = "reconnecting…"; };
es.onmessage = (m) => {
  const e = JSON.parse(m.data);
  if (e.type === "window") onWindow(e);
  else if (e.type === "mode") {
    if (e.name !== mode) {
      mode = e.name; tare = null; settle = SETTLE; resetChart();
      for (const c of CELLS) recent[c.ch].length = 0;
      const saved = store.get("openfp.cpk." + mode);
      $("cpk").value = saved ?? DEFAULT_CPK[mode] ?? "";
      $("calnote").textContent = saved ? "saved calibration" : "rough default until calibrated";
    }
    $("mode").textContent = e.name;
  } else if (e.type === "readback") {
    answering[e.ch] = e.ok;
    $("answering").textContent = CELLS.map((c) => c.ch).filter((ch) => answering[ch]).join(" ") || "none";
    const row = $("u-" + e.ch);
    if (row) { const td = row.querySelector(".rb"); td.textContent = e.ok ? "OK" : "FAIL"; td.style.color = e.ok ? "" : "var(--bad)"; }
  } else if (e.type === "voltage") {
    const td = $("u-" + e.ch)?.querySelector(`[data-v="${e.name}"]`);
    if (td) td.textContent = e.value;
  } else if (e.type === "error") say(e.message);
  else if (e.type === "closed") { $("link").className = "pill bad"; $("linktext").textContent = "monitor closed"; }
};
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--host", default="open-fp.local", help="the UNO Q")
    ap.add_argument("--port", type=int, default=7072)
    ap.add_argument("--no-open", action="store_true", help="don't open a browser")
    ap.add_argument(
        "--channels",
        default=DEFAULT_CHANNELS,
        help="cells to show: L or R (a plate's four), all, or names like L1,L2,R1,R2 "
        "(default: L, the plate L carrier)",
    )
    args = ap.parse_args()
    try:
        channels = parse_channels(args.channels)
    except ValueError as e:
        print(f"--channels: {e}")
        return 2
    page = render_page(channels)

    mon = Monitor(args.host, parse=parse_line)
    # On SIGTERM (e.g. pkill), exit through the normal path so the ssh monitor is closed too.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    hub = MultiHub()
    threading.Thread(target=pump, args=(mon, hub), daemon=True).start()
    # Report the mode and every readback for the page, once ssh has attached to the monitor
    # (a key sent before that is lost).
    threading.Timer(3.0, mon.send, args=("r",)).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(mon, hub, page, KEYS))
    url = f"http://localhost:{args.port}"
    print(f"{title(channels)} live view ({' '.join(channels)}): {url}  (Ctrl-C to stop)")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        mon.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
