// Vertical force trace (uPlot). One instance; live mode appends to a ring buffer and
// calls setData, replay mode shows a whole swing with event lines and a cursor.

const WINDOW_S = 5;
const RATE = 200;
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export const EVENT_LABELS = {
  motion_start: "Motion start",
  max_trail: "Max trail",
  transition: "Transition",
  impact: "Impact",
  max_lead: "Max lead",
  finish: "Finish",
};

export class TraceChart {
  constructor(el) {
    this.el = el;
    this.n = WINDOW_S * RATE;
    this.buf = { t: [], lead: [], trail: [], total: [] };
    this.mode = "live";
    this.events = null;
    this.cursorT = null;
    this.bw = null;
    this.golfer = "RH";

    const axis = {
      stroke: css("--muted"),
      grid: { stroke: css("--line"), width: 1 },
      ticks: { stroke: css("--line"), width: 1 },
      font: `11px ${css("--font")}`,
    };
    const opts = {
      width: el.clientWidth || 600,
      height: el.clientHeight || 220,
      pxAlign: 0,
      legend: { show: false },
      cursor: { show: false },
      scales: { x: { time: false }, y: { range: (u, lo, hi) => [0, Math.max(160, Math.ceil(hi / 20) * 20)] } },
      axes: [
        { ...axis, values: (u, vals) => vals.map((v) => `${+v.toFixed(2)} s`) },
        { ...axis, size: 44, values: (u, vals) => vals.map((v) => `${v}`) },
      ],
      series: [
        {},
        { stroke: css("--lead"), width: 2 },
        { stroke: css("--trail"), width: 2 },
        { stroke: css("--comb"), width: 1, dash: [4, 3] },
      ],
      hooks: { draw: [(u) => this.drawOverlay(u)] },
    };
    this.u = new uPlot(opts, [[], [], [], []], el);
    new ResizeObserver(() => this.u.setSize({ width: el.clientWidth, height: el.clientHeight })).observe(el);
  }

  pctBW(v, bw) {
    return v == null ? null : (100 * v) / (bw || 800);
  }

  pushLive(msg) {
    this.bw = msg.bw_n;
    this.golfer = msg.golfer;
    const lead = msg.lead_plate;
    const trail = lead === "L" ? "R" : "L";
    // Until bodyweight is captured, scale by the current total so the trace is still readable.
    const n = msg.t.length;
    for (let k = 0; k < n; k++) {
      const total = (msg.fz.L[k] ?? 0) + (msg.fz.R[k] ?? 0);
      const bw = msg.bw_n || (total > 200 ? total : 800);
      this.buf.t.push(msg.t[k]);
      this.buf.lead.push(this.pctBW(msg.fz[lead][k], bw));
      this.buf.trail.push(this.pctBW(msg.fz[trail][k], bw));
      this.buf.total.push(this.pctBW(total, bw));
    }
    for (const key in this.buf) if (this.buf[key].length > this.n) this.buf[key].splice(0, this.buf[key].length - this.n);
    if (this.mode === "live" && !this._pending) {
      this._pending = true;
      requestAnimationFrame(() => {
        this._pending = false;
        if (this.mode !== "live") return;
        const t = this.buf.t;
        const tEnd = t[t.length - 1];
        const x = t.map((v) => v - tEnd);
        this.u.batch(() => {
          this.u.setScale("x", { min: -WINDOW_S, max: 0 });
          this.u.setData([x, this.buf.lead, this.buf.trail, this.buf.total], false);
        });
      });
    }
  }

  showReplay(swing, leadPlate) {
    this.mode = "replay";
    const a = swing.arrays;
    const trail = leadPlate === "L" ? "R" : "L";
    const bw = swing.bw_n;
    const lead = a[`fz_${leadPlate}`].map((v) => this.pctBW(v, bw));
    const tr = a[`fz_${trail}`].map((v) => this.pctBW(v, bw));
    const total = a.fz_L.map((v, i) => this.pctBW((v ?? 0) + (a.fz_R[i] ?? 0), bw));
    this.events = swing.events;
    this.cursorT = 0;
    this.u.setData([a.t, lead, tr, total], false);
    this.u.setScale("x", { min: a.t[0], max: a.t[a.t.length - 1] });
  }

  setCursor(t) {
    this.cursorT = t;
    this.u.redraw(false, false);
  }

  showLive() {
    this.mode = "live";
    this.events = null;
    this.cursorT = null;
  }

  drawOverlay(u) {
    if (this.mode !== "replay" || !this.events) return;
    const { ctx } = u;
    const dpr = devicePixelRatio || 1;
    const top = u.bbox.top, bottom = u.bbox.top + u.bbox.height;
    ctx.save();
    ctx.font = `600 ${10 * dpr}px ${css("--font")}`;
    ctx.textBaseline = "top";
    const rowsEnd = [];                       // right edge of the last label in each row
    const marks = Object.entries(EVENT_LABELS)
      .filter(([name]) => this.events[name] != null)
      .map(([name, label]) => [Math.round(u.valToPos(this.events[name], "x", true)), label.toUpperCase()])
      .sort((a, b) => a[0] - b[0]);
    for (const [x, text] of marks) {
      ctx.strokeStyle = css("--event");
      ctx.globalAlpha = 0.8;
      ctx.setLineDash([3 * dpr, 3 * dpr]);
      ctx.lineWidth = dpr;
      ctx.beginPath();
      ctx.moveTo(x, top);
      ctx.lineTo(x, bottom);
      ctx.stroke();
      ctx.setLineDash([]);
      const w = ctx.measureText(text).width;
      let row = rowsEnd.findIndex((end) => x + 4 * dpr > end + 6 * dpr);
      if (row === -1) row = rowsEnd.length;
      rowsEnd[row] = x + 4 * dpr + w;
      ctx.fillStyle = css("--event");
      ctx.fillText(text, x + 4 * dpr, top + 2 * dpr + row * 12 * dpr);
    }
    if (this.cursorT != null) {
      const x = Math.round(u.valToPos(this.cursorT, "x", true));
      ctx.globalAlpha = 1;
      ctx.strokeStyle = css("--comb");
      ctx.lineWidth = 1.5 * dpr;
      ctx.beginPath();
      ctx.moveTo(x, top);
      ctx.lineTo(x, bottom);
      ctx.stroke();
    }
    ctx.restore();
  }
}
