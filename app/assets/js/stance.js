// Top-down stance view on a 2D canvas. World units are mm in the stance frame
// (+x from Plate L to Plate R, +y toward the ball). Lead foot is always drawn on the
// left: the view mirrors x for left-handed golfers.

const PLATE_MM = 304.8;
const CELL_CAPACITY_N = 50 * 9.80665;
const ENCLOSURE = { w: 61, h: 295 };
const TRAIL_S = 3;

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export const PHASES = [
  // [from event, to event, label, color token]
  [null, "motion_start", "Address", "--muted"],
  ["motion_start", "max_trail", "Backswing", "--trail"],
  ["max_trail", "transition", "Transition", "--event"],
  ["transition", "max_lead", "Downswing", "--lead"],
  ["max_lead", null, "Finish", "--comb"],
];

export class StanceView {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.cfg = null;
    this.live = null;          // latest live frame
    this.trail = [];           // [t, x, y] combined CoP history
    this.replay = null;        // { swing, cursor }
    this.colors = {};
    this.dirty = true;
    new ResizeObserver(() => this.resize()).observe(canvas);
    this.resize();
    const loop = () => {
      if (this.dirty) this.draw();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  setConfig(cfg) {
    this.cfg = cfg;
    this.positions = cfg.positions_mm ?? defaultPositions(cfg);
    this.dirty = true;
  }

  resize() {
    const dpr = window.devicePixelRatio || 1;
    const r = this.canvas.getBoundingClientRect();
    this.canvas.width = Math.max(1, Math.round(r.width * dpr));
    this.canvas.height = Math.max(1, Math.round(r.height * dpr));
    this.dpr = dpr;
    this.dirty = true;
  }

  pushLive(msg) {
    const n = msg.t.length;
    if (!n) return;
    const i = n - 1;
    this.live = {
      fz: { L: msg.fz.L[i], R: msg.fz.R[i] },
      cop: { L: msg.cop.L[i], R: msg.cop.R[i], C: msg.cop.C[i] },
      bw: msg.bw_n,
      forces: msg.forces ? msg.forces[i] : null,
    };
    for (let k = 0; k < n; k++) {
      const c = msg.cop.C[k];
      if (c) this.trail.push([msg.t[k], c[0], c[1]]);
    }
    const tEnd = msg.t[i];
    while (this.trail.length && tEnd - this.trail[0][0] > TRAIL_S) this.trail.shift();
    if (!this.replay) this.dirty = true;
  }

  showReplay(swing) { this.replay = { swing, cursor: 0 }; this.dirty = true; }
  setCursor(i) { if (this.replay) { this.replay.cursor = i; this.dirty = true; } }
  showLive() { this.replay = null; this.dirty = true; }

  // -- geometry -------------------------------------------------------------

  layout() {
    const half = (this.cfg?.plate_spacing_mm ?? 369.6) / 2 + PLATE_MM / 2;
    const worldW = 2 * half + 60;
    const worldH = PLATE_MM + 90;
    const W = this.canvas.width, H = this.canvas.height;
    const s = Math.min(W / worldW, H / worldH);
    const mirror = this.cfg?.golfer === "LH" ? -1 : 1;
    this.tx = (x, y) => [W / 2 + mirror * x * s, H / 2 - y * s + 12 * this.dpr];
    this.s = s;
  }

  plateCentre(p) {
    const idx = p === "L" ? [0, 1, 2, 3] : [4, 5, 6, 7];
    const xs = idx.map((i) => this.positions[i][0]);
    const ys = idx.map((i) => this.positions[i][1]);
    return [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2];
  }

  // -- drawing ----------------------------------------------------------------

  draw() {
    this.dirty = false;
    const { ctx } = this;
    const c = (this.colors = {
      panel: css("--panel"), line: css("--line"), lineStrong: css("--line-strong"),
      lead: css("--lead"), trail: css("--trail"), comb: css("--comb"), event: css("--event"),
      muted: css("--muted"), dim: css("--dim"),
    });
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    if (!this.cfg) return;
    this.layout();
    const lead = this.cfg.golfer === "LH" ? "R" : "L";
    const frame = this.replay ? this.replayFrame() : this.live;

    this.drawTarget();
    this.drawEnclosure();
    for (const p of ["L", "R"]) this.drawPlate(p, p === lead ? c.lead : c.trail, p === lead ? "LEAD" : "TRAIL", frame);
    if (this.replay) this.drawReplayPath();
    else this.drawTrail();
    if (frame) this.drawCop(frame, lead);
  }

  drawTarget() {
    const { ctx, dpr } = this;
    const [x, y] = [18 * dpr, 16 * dpr];
    ctx.fillStyle = this.colors.muted;
    ctx.font = `600 ${11 * dpr}px ${css("--font")}`;
    ctx.textBaseline = "middle";
    ctx.fillText("← TARGET", x, y);
  }

  drawEnclosure() {
    const { ctx } = this;
    const [x0, y0] = this.tx(-ENCLOSURE.w / 2, ENCLOSURE.h / 2);
    const [x1, y1] = this.tx(ENCLOSURE.w / 2, -ENCLOSURE.h / 2);
    ctx.strokeStyle = this.colors.line;
    ctx.lineWidth = this.dpr;
    ctx.setLineDash([3 * this.dpr, 3 * this.dpr]);
    ctx.strokeRect(Math.min(x0, x1), y0, Math.abs(x1 - x0), y1 - y0);
    ctx.setLineDash([]);
  }

  drawPlate(p, color, label, frame) {
    const { ctx, dpr } = this;
    const [cx, cy] = this.plateCentre(p);
    const [x0, y0] = this.tx(cx - PLATE_MM / 2, cy + PLATE_MM / 2);
    const [x1, y1] = this.tx(cx + PLATE_MM / 2, cy - PLATE_MM / 2);
    const left = Math.min(x0, x1), w = Math.abs(x1 - x0), h = y1 - y0;

    ctx.fillStyle = "#161E29";
    ctx.strokeStyle = this.colors.lineStrong;
    ctx.lineWidth = dpr;
    roundRect(ctx, left, y0, w, h, 4 * dpr);
    ctx.fill();
    ctx.stroke();

    // shoe outline, toe toward the ball (+y)
    this.drawShoe(cx, cy, p);

    // load cells as rings filling toward capacity
    const idx = p === "L" ? [0, 1, 2, 3] : [4, 5, 6, 7];
    for (const i of idx) {
      const [px, py] = this.tx(...this.positions[i]);
      const r = Math.max(7 * dpr, 17 * this.s);
      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.strokeStyle = this.colors.line;
      ctx.lineWidth = 3 * dpr;
      ctx.stroke();
      const f = frame?.forces?.[i];
      if (f != null && f > 0) {
        ctx.beginPath();
        ctx.arc(px, py, r, -Math.PI / 2, -Math.PI / 2 + Math.min(1, f / CELL_CAPACITY_N) * Math.PI * 2);
        ctx.strokeStyle = color;
        ctx.stroke();
      }
    }

    ctx.fillStyle = color;
    ctx.font = `600 ${11 * dpr}px ${css("--font")}`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const kg = frame?.fz?.[p] == null ? null : Math.max(0, frame.fz[p]) / 9.80665;
    ctx.fillText(kg == null ? label : `${label} · ${kg.toFixed(1)} kg`, left + w / 2, y1 + 8 * dpr);
    ctx.textAlign = "start";
  }

  drawShoe(cx, cy, p) {
    const { ctx } = this;
    const inner = p === "L" ? 1 : -1;      // world +x is the inner side of the left foot
    const len = 290, wid = 108;
    // outline with +x as the inner (arch) side, toe at +y
    const pts = [
      [0, 0.5], [0.34, 0.40], [0.40, 0.16], [0.27, -0.06], [0.33, -0.30], [0.28, -0.46],
      [0, -0.5], [-0.32, -0.45], [-0.44, -0.20], [-0.48, 0.14], [-0.36, 0.40],
    ].map(([x, y]) => this.tx(cx + inner * x * wid, cy + y * len));
    ctx.beginPath();
    smoothClosed(ctx, pts);
    ctx.fillStyle = "rgba(255,255,255,0.025)";
    ctx.strokeStyle = "rgba(255,255,255,0.10)";
    ctx.lineWidth = this.dpr;
    ctx.fill();
    ctx.stroke();
  }

  drawTrail() {
    const { ctx, trail } = this;
    if (trail.length < 2) return;
    const tEnd = trail[trail.length - 1][0];
    ctx.lineWidth = 2 * this.dpr;
    ctx.lineCap = "round";
    for (let k = 1; k < trail.length; k++) {
      const a = 1 - (tEnd - trail[k][0]) / TRAIL_S;
      ctx.strokeStyle = `rgba(242,245,248,${(a * a * 0.7).toFixed(3)})`;
      ctx.beginPath();
      ctx.moveTo(...this.tx(trail[k - 1][1], trail[k - 1][2]));
      ctx.lineTo(...this.tx(trail[k][1], trail[k][2]));
      ctx.stroke();
    }
  }

  drawCop(frame, lead) {
    const { ctx, dpr } = this;
    const bw = frame.bw || (frame.fz.L + frame.fz.R) || 800;
    for (const p of ["L", "R"]) {
      const c = frame.cop[p];
      if (!c) continue;
      const [x, y] = this.tx(c[0], c[1]);
      const r = (5 + 15 * Math.sqrt(Math.max(0, frame.fz[p]) / bw)) * dpr;
      const col = p === lead ? this.colors.lead : this.colors.trail;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = hexAlpha(col, 0.28);
      ctx.fill();
      ctx.lineWidth = 2 * dpr;
      ctx.strokeStyle = col;
      ctx.stroke();
    }
    const cc = frame.cop.C;
    if (cc) {
      const [x, y] = this.tx(cc[0], cc[1]);
      ctx.beginPath();
      ctx.arc(x, y, 6 * dpr, 0, Math.PI * 2);
      ctx.fillStyle = this.colors.comb;
      ctx.fill();
      ctx.lineWidth = 2 * dpr;
      ctx.strokeStyle = this.colors.panel;
      ctx.stroke();
    }
  }

  // -- replay -------------------------------------------------------------------

  replayFrame() {
    const { swing, cursor } = this.replay;
    const a = swing.arrays;
    const i = Math.min(cursor, a.t.length - 1);
    return {
      fz: { L: a.fz_L[i], R: a.fz_R[i] },
      cop: { L: a.cop_L[i], R: a.cop_R[i], C: a.cop_C[i] },
      bw: swing.bw_n,
      forces: a.forces[i],
    };
  }

  drawReplayPath() {
    const { ctx, dpr } = this;
    const { swing } = this.replay;
    const a = swing.arrays;
    const ev = swing.events;
    const idx = (name) => (ev[name] == null ? null : nearest(a.t, ev[name]));
    ctx.lineWidth = 2.5 * dpr;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    for (const [from, to, , token] of PHASES) {
      const i0 = from ? idx(from) : 0;
      const i1 = to ? idx(to) : a.t.length - 1;
      if (i0 == null || i1 == null || i1 <= i0) continue;
      ctx.strokeStyle = css(token);
      ctx.beginPath();
      let pen = false;
      for (let k = i0; k <= i1; k++) {
        const c = a.cop_C[k];
        if (!c) { pen = false; continue; }
        const [x, y] = this.tx(c[0], c[1]);
        if (pen) ctx.lineTo(x, y); else ctx.moveTo(x, y);
        pen = true;
      }
      ctx.stroke();
    }
    // event markers
    for (const name of ["max_trail", "transition", "impact", "max_lead"]) {
      const i = idx(name);
      const c = i == null ? null : a.cop_C[i];
      if (!c) continue;
      const [x, y] = this.tx(c[0], c[1]);
      const r = 5 * dpr;
      ctx.beginPath();
      ctx.moveTo(x, y - r); ctx.lineTo(x + r, y); ctx.lineTo(x, y + r); ctx.lineTo(x - r, y); ctx.closePath();
      ctx.fillStyle = this.colors.panel;
      ctx.fill();
      ctx.lineWidth = 1.5 * dpr;
      ctx.strokeStyle = this.colors.event;
      ctx.stroke();
    }
  }
}

export function defaultPositions(cfg) {
  const half = cfg.plate_spacing_mm / 2, o = cfg.cell_offset_mm;
  const corners = { L1: [1, 1], L2: [-1, 1], L3: [-1, -1], L4: [1, -1], R1: [-1, 1], R2: [1, 1], R3: [1, -1], R4: [-1, -1] };
  return Object.entries(corners).map(([ch, [out, toe]]) => {
    const side = ch[0] === "L" ? -1 : 1;
    return [side * (half + out * o), toe * o];
  });
}

export function nearest(ts, t) {
  let lo = 0, hi = ts.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (ts[mid] < t) lo = mid + 1; else hi = mid;
  }
  return lo;
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function smoothClosed(ctx, pts) {
  const n = pts.length;
  const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  ctx.moveTo(...mid(pts[n - 1], pts[0]));
  for (let i = 0; i < n; i++) {
    const m = mid(pts[i], pts[(i + 1) % n]);
    ctx.quadraticCurveTo(pts[i][0], pts[i][1], m[0], m[1]);
  }
  ctx.closePath();
}

function hexAlpha(hex, a) {
  const v = parseInt(hex.slice(1), 16);
  return `rgba(${v >> 16},${(v >> 8) & 255},${v & 255},${a})`;
}
