#!/usr/bin/env python3
"""Live browser view of the one-cell bench sketch (bench/ads1220_single).

    .venv/bin/python tools/bench/live_view.py        # opens http://localhost:7071

Streams `arduino-app-cli monitor` over SSH (like single_cell.py) and pushes each 100 ms
window to the page with server-sent events. The page shows the change since tare, a 30 s
chart, noise and sample rate, and has buttons for the sketch's keys (mode, voltage check).
Standard library only; the chart uses the uPlot copy in app/assets/vendor.
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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from single_cell import ModeLine, Monitor, Readback, SketchError, Stats, Voltage

ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "app" / "assets" / "vendor"
KEYS = ("s", "d", "v", "r")  # keystrokes the sketch understands


def to_event(item) -> str:
    """A parsed sketch line as a JSON event for the browser."""
    if isinstance(item, Stats):
        return json.dumps({"type": "stats", **asdict(item)})
    if isinstance(item, Readback):
        regs = " ".join(f"{r:02X}" for r in item.regs)
        return json.dumps({"type": "readback", "ok": item.ok, "regs": regs})
    if isinstance(item, ModeLine):
        return json.dumps({"type": "mode", "name": item.name})
    if isinstance(item, Voltage):
        return json.dumps({"type": "voltage", "name": item.name, "value": item.value})
    if isinstance(item, SketchError):
        return json.dumps({"type": "error", "message": item.message})
    return json.dumps({"type": "unknown"})


class Hub:
    """Fans events out to every connected page; replays the latest status to new ones."""

    def __init__(self):
        self._lock = threading.Lock()
        self._clients: list[queue.Queue] = []
        self._latest: dict[str, str] = {}  # event type (or voltage name) -> last event

    def add(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=600)
        with self._lock:
            self._clients.append(q)
            for event in self._latest.values():
                q.put_nowait(event)
        return q

    def remove(self, q: queue.Queue):
        with self._lock:
            if q in self._clients:
                self._clients.remove(q)

    def publish(self, event: str):
        kind = json.loads(event)
        key = kind["type"] if kind["type"] != "voltage" else "voltage:" + kind["name"]
        with self._lock:
            if key in ("readback", "mode") or key.startswith("voltage:"):
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


def make_handler(mon: Monitor, hub: Hub):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):  # keep the terminal quiet
            pass

        def _send(self, body: bytes, ctype: str, status: int = 200):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802 (http.server API)
            if self.path == "/":
                self._send(PAGE.encode(), "text/html; charset=utf-8")
            elif self.path in ("/uPlot.iife.min.js", "/uPlot.min.css"):
                ctype = "text/javascript" if self.path.endswith(".js") else "text/css"
                self._send((VENDOR / self.path.lstrip("/")).read_bytes(), ctype)
            elif self.path == "/events":
                self._events()
            else:
                self._send(b"not found", "text/plain", 404)

        def do_POST(self):  # noqa: N802 (http.server API)
            key = self.path.rsplit("/", 1)[-1]
            if self.path.startswith("/key/") and key in KEYS:
                mon.send(key)
                self._send(b"", "text/plain", 204)
            else:
                self._send(b"unknown key", "text/plain", 400)

        def _events(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            q = hub.add()
            try:
                while True:
                    try:
                        event = q.get(timeout=15)
                        self.wfile.write(f"data: {event}\n\n".encode())
                    except queue.Empty:
                        self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                hub.remove(q)

    return Handler


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>L1 live</title>
<link rel="stylesheet" href="/uPlot.min.css" />
<style>
  :root { --bg:#0B0F14; --panel:#121821; --line:#1E2733; --lead:#2EC4B6; --trail:#FF9F1C;
          --text:#D7DEE7; --muted:#7A8796; --bad:#E5676B; color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text);
         font:14px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  header { display:flex; gap:16px; align-items:center; padding:12px 20px; border-bottom:1px solid var(--line); flex-wrap:wrap; }
  h1 { font-size:16px; margin:0 8px 0 0; }
  .pill { color:var(--muted); font-variant-numeric:tabular-nums; }
  .pill b { color:var(--text); font-weight:600; }
  .dot { display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--muted); margin-right:6px; }
  .ok .dot { background:var(--lead); } .bad .dot { background:var(--bad); }
  main { display:grid; grid-template-columns: 320px 1fr; gap:12px; padding:12px 20px; }
  section { background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:14px; }
  .label { font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); font-weight:600; }
  .big { font-size:64px; font-weight:250; letter-spacing:-.03em; font-variant-numeric:tabular-nums; line-height:1.05; color:var(--lead); }
  .big.neg { color:var(--trail); }
  .sub { color:var(--muted); font-variant-numeric:tabular-nums; margin-top:4px; }
  button { font:inherit; color:var(--text); background:transparent; border:1px solid #2A3544; border-radius:6px;
           min-height:40px; padding:0 12px; cursor:pointer; margin:0 6px 6px 0; }
  button:hover { border-color:var(--muted); }
  button:focus-visible, input:focus-visible { outline:2px solid var(--lead); outline-offset:2px; }
  button.primary { background:var(--lead); color:var(--bg); border-color:var(--lead); font-weight:600; }
  .buttons { margin-top:14px; }
  dl { display:grid; grid-template-columns:auto 1fr; gap:4px 12px; margin:10px 0 0; font-variant-numeric:tabular-nums; }
  dt { color:var(--muted); } dd { margin:0; text-align:right; }
  input { width:90px; font:inherit; color:var(--text); background:var(--bg); border:1px solid #2A3544; border-radius:4px; padding:4px 6px; }
  #chart { min-height:360px; }
  #log { color:var(--bad); font-size:12px; margin-top:8px; min-height:1em; }
  .u-legend { display:none; }
  @media (max-width: 800px) { main { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<header>
  <h1>L1 live</h1>
  <span id="link" class="pill"><span class="dot"></span><span id="linktext">connecting…</span></span>
  <span class="pill">mode <b id="mode">?</b></span>
  <span class="pill">readback <b id="readback">?</b></span>
  <span class="pill">rate <b id="rate">–</b> Hz</span>
  <span class="pill">noise <b id="noise">–</b> counts</span>
</header>
<main>
  <section>
    <div class="label">Change since tare</div>
    <div class="big" id="delta">–</div>
    <div class="sub"><span id="kg">–</span> kg at <input id="cpk" type="number" min="1" step="1" aria-label="Counts per kg" /> counts/kg (rough until calibrated)</div>
    <div class="sub">raw <span id="raw">–</span></div>
    <div class="buttons">
      <button class="primary" id="tare">Tare</button>
      <button data-key="s" title="AIN0 vs ground, gain 1: works before R1/R2 are fitted">Single-ended</button>
      <button data-key="d" title="AIN0 - AIN1, gain 128: needs R1/R2">Differential</button>
      <button data-key="v" title="ADC measures its own supply, reference and inputs">Voltage check</button>
      <button data-key="r">Re-check ADC</button>
    </div>
    <div class="label" style="margin-top:12px">Voltage check (mV)</div>
    <dl id="volts"><dt>—</dt><dd>press Voltage check</dd></dl>
    <div id="log" role="status"></div>
  </section>
  <section>
    <div class="label">Change since tare, last 30 s (100 ms averages, with min–max)</div>
    <div id="chart"></div>
  </section>
</main>
<script src="/uPlot.iife.min.js"></script>
<script>
const $ = (id) => document.getElementById(id);
const N = 300;                               // 30 s of 100 ms windows
const DEFAULT_CPK = { "single-ended": 120, "differential": 15000 };
let t0 = null, tare = null, mode = null, recent = [];
const xs = [], ys = [], lo = [], hi = [];
const fmt = (v) => (v >= 0 ? "+" : "−") + Math.abs(Math.round(v)).toLocaleString();

const chart = new uPlot({
  width: $("chart").clientWidth, height: 360, legend: { show: false }, cursor: { show: false },
  scales: { x: { time: false } },
  axes: [
    { stroke: "#7A8796", grid: { stroke: "#1E2733" }, values: (u, v) => v.map((s) => s.toFixed(0) + " s") },
    { stroke: "#7A8796", grid: { stroke: "#1E2733" }, size: 70, values: (u, v) => v.map((c) => c.toLocaleString()) },
  ],
  series: [{}, { stroke: "rgba(46,196,182,.25)", width: 1 }, { stroke: "rgba(46,196,182,.25)", width: 1 },
           { stroke: "#2EC4B6", width: 2 }],
}, [[], [], [], []], $("chart"));
new ResizeObserver(() => chart.setSize({ width: $("chart").clientWidth, height: 360 })).observe($("chart"));

function doTare() {
  if (!recent.length) return;
  tare = recent.reduce((a, b) => a + b, 0) / recent.length;
  xs.length = ys.length = lo.length = hi.length = 0;
}
$("tare").onclick = doTare;
document.querySelectorAll("[data-key]").forEach((b) => (b.onclick = () => fetch("/key/" + b.dataset.key, { method: "POST" })));

function onStats(e) {
  if (t0 === null) t0 = e.ms;
  recent.push(e.mean); if (recent.length > 5) recent.shift();
  if (tare === null && recent.length === 5) doTare();
  const base = tare ?? e.mean;
  const d = e.mean - base;
  xs.push((e.ms - t0) / 1000); ys.push(d); lo.push(e.vmin - base); hi.push(e.vmax - base);
  if (xs.length > N) { xs.shift(); ys.shift(); lo.shift(); hi.shift(); }
  chart.setData([xs, lo, hi, ys]);
  $("delta").textContent = fmt(d);
  $("delta").classList.toggle("neg", d < 0);
  $("raw").textContent = e.mean.toLocaleString();
  $("noise").textContent = e.std.toLocaleString();
  $("rate").textContent = ((e.drdy ?? e.n) * 10).toLocaleString();
  const cpk = Number($("cpk").value) || 0;
  $("kg").textContent = cpk ? (Math.abs(d) / cpk).toFixed(2) : "–";
}

const es = new EventSource("/events");
es.onopen = () => { $("link").className = "pill ok"; $("linktext").textContent = "connected"; };
es.onerror = () => { $("link").className = "pill bad"; $("linktext").textContent = "reconnecting…"; };
es.onmessage = (m) => {
  const e = JSON.parse(m.data);
  if (e.type === "stats") onStats(e);
  else if (e.type === "mode") {
    if (e.name !== mode) { mode = e.name; tare = null; recent = []; t0 = null; xs.length = ys.length = lo.length = hi.length = 0;
      $("cpk").value = DEFAULT_CPK[mode] ?? ""; }
    $("mode").textContent = e.name;
  } else if (e.type === "readback") {
    $("readback").textContent = (e.ok ? "OK " : "FAIL ") + e.regs;
    $("readback").style.color = e.ok ? "" : "#E5676B";
  } else if (e.type === "voltage") {
    const dl = $("volts");
    if (dl.firstElementChild?.textContent === "—") dl.innerHTML = "";
    let dd = dl.querySelector(`[data-v="${e.name}"]`);
    if (!dd) { dl.insertAdjacentHTML("beforeend", `<dt>${e.name}</dt><dd data-v="${e.name}"></dd>`); dd = dl.querySelector(`[data-v="${e.name}"]`); }
    dd.textContent = e.value;
  } else if (e.type === "error") { $("log").textContent = e.message; setTimeout(() => ($("log").textContent = ""), 4000); }
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
    ap.add_argument("--port", type=int, default=7071)
    ap.add_argument("--no-open", action="store_true", help="don't open a browser")
    args = ap.parse_args()

    mon = Monitor(args.host)
    # On SIGTERM (e.g. pkill), exit through the normal path so the ssh monitor is closed too.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    hub = Hub()
    threading.Thread(target=pump, args=(mon, hub), daemon=True).start()
    mon.send("r")  # report the current mode and readback for the page
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(mon, hub))
    url = f"http://localhost:{args.port}"
    print(f"L1 live view: {url}  (Ctrl-C to stop)")
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
