// Swing metric cards: what each number means, a reference range where one is published,
// and the golfer's own spread across the swings in the library.
// Sources: docs/research/swing-catalyst.md.

const STORE_KEY = "open-fp.metrics";
const NEEDS_IMPACT = "Needs a shot event from the launch monitor.";

const REF_DIST = "Driver, 86 swings by 23 golfers (McGhie, unpublished; from Lynn, Carolinas PGA slides). A pressure-mat split, so close to but not the same as our force split.";
const REF_FZ = "Tour average for vertical force (Lynn, Carolinas PGA slides, PING study). How it was measured isn't published.";

const fmt = (v, d = 0) => Number(v).toFixed(d);

// Narrowest scale a range bar may use, so near-identical swings don't look far apart.
const MIN_SPAN = { "% lead": 20, "% trail": 20, "%/s": 150, mm: 60, "mm/s": 400, "%BW": 40, ms: 100 };

// kind "bw": stored as %BW, can be shown in newtons.
export const METRICS = {
  address: {
    label: "Address", unit: "% lead", get: (m) => m.lead_pct_address,
    what: "Share of your vertical force on the lead foot while you stand still at address.",
    read: "Most players start close to even, slightly toward the lead foot. Driver and irons look much the same here.",
    ref: { mean: 53.7, sd: 8.3, src: REF_DIST },
  },
  maxTrail: {
    label: "Max trail", unit: "% trail", get: (m) => (m.lead_pct_max_trail == null ? null : 100 - m.lead_pct_max_trail),
    what: "The most force on your trail foot in the backswing. It's a force event: near the top of the backswing, not exactly at it.",
    read: "The reference is the trail-foot share at the top. It's lower with shorter clubs (75% mid irons, 72% short irons). The spread is wide, so treat it as a style, not a target.",
    ref: { mean: 78.3, sd: 14.0, src: REF_DIST },
  },
  maxLead: {
    label: "Max lead", unit: "% lead", get: (m) => m.lead_pct_max_lead,
    what: "The most force on your lead foot after the shift, usually just after impact.",
    read: "How fully you get onto the lead side. Compare it with Lead at impact to see whether you get there in time.",
  },
  leadImpact: {
    label: "Lead at impact", unit: "% lead", get: (m) => m.lead_pct_impact, needsImpact: true,
    what: "Share of your vertical force on the lead foot at the moment of impact.",
    read: "The driver reference is about 76%, and irons sit further forward (82–84%). Individual players range from almost none to all of it, so work on your own repeatability rather than the average.",
    ref: { mean: 75.9, sd: 17.7, src: REF_DIST },
  },
  shiftRate: {
    label: "Peak shift rate", unit: "%/s", get: (m) => m.peak_shift_rate_pct_s,
    what: "How fast force moves from your trail foot to your lead foot, at its quickest.",
    read: "Good players tend to make a rapid, continuous shift in the downswing. On the stance view that shows as a smooth, near-straight line from trail to lead.",
  },
  copRange: {
    label: "Lateral CoP range", unit: "mm", get: (m) => m.lateral_cop_range_mm,
    what: "How far your combined pressure point travels toward and away from the target, from the start of the swing to the finish.",
    read: "It grows with stance width, so compare it across your own swings with the same stance, not with other players.",
  },
  copSpeed: {
    label: "Peak CoP speed", unit: "mm/s", get: (m) => m.peak_lateral_speed_mm_s,
    what: "The fastest your combined pressure point moves sideways during the swing.",
    read: "Usually comes in the downswing shift. A smooth trace with one clear peak is more repeatable than one with several surges.",
  },
  peakFz: {
    label: "Peak force", kind: "bw", get: (m) => m.peak_fz_downswing_pct_bw,
    what: "The highest total vertical force from both feet in the downswing, as a share of your body weight.",
    read: "Pushing into the ground is one way the body adds speed, but more isn't automatically better. Swing Catalyst reports a player who gained about 6 mph after bringing this from 234% down to 175% with better timing. Pressure toward the toes tends to go with higher peaks.",
    ref: { mean: 179, sd: 20, src: REF_FZ },
  },
  peakLead: {
    label: "Peak lead force", kind: "bw", get: (m) => m.peak_fz_pct_bw?.lead,
    what: "The highest vertical force under your lead foot alone.",
    read: "Most of the downswing push comes through the lead leg. Compare it with Peak force to see how much the trail foot still adds.",
  },
  minFz: {
    label: "Unweighting", kind: "bw", get: (m) => m.min_fz_pct_bw,
    what: "The lowest total vertical force between the start of the swing and the downswing peak.",
    read: "Below 100% means you briefly take weight off the ground, usually around the transition, before pushing down. How deep it goes shows how forcefully you drop before the push.",
  },
  peakAfter5050: {
    label: "50/50 → peak force", unit: "ms", get: (m) => m.peak_fz_rel_transition_ms,
    what: "Time from the moment your force crosses 50/50 to the downswing force peak.",
    read: "A later pressure shift goes with a later vertical peak. The peak usually comes late in the downswing, around club parallel. Look for this to be consistent across your swings.",
  },
  peakVsImpact: {
    label: "Peak force vs impact", unit: "ms", get: (m) => m.peak_fz_rel_impact_ms, needsImpact: true,
    what: "When the downswing force peak happens relative to impact. Negative means before impact.",
    read: "Good players usually peak shortly before impact, around club parallel in the downswing.",
  },
  minVs5050: {
    label: "Unweighting vs 50/50", unit: "ms", get: (m) => m.min_fz_rel_transition_ms,
    what: "When the unweighting low point happens relative to the 50/50 crossing. Negative means before it.",
    read: "The low point typically falls around the transition. Read it together with 50/50 → peak force to see the whole drop-then-push.",
  },
  trailTo5050: {
    label: "Max trail → 50/50", unit: "ms", get: (m) => m.time_max_trail_to_transition_ms,
    what: "Time from the most force on your trail foot to the moment force is split evenly again.",
    read: "How quickly you start moving force back toward the target. Around transition, pressure can stay on the trail foot while your body is already moving forward, so this is a force timing, not body timing.",
  },
  fiftyToLead: {
    label: "50/50 → max lead", unit: "ms", get: (m) => m.time_transition_to_max_lead_ms,
    what: "Time from the even split to the most force on your lead foot.",
    read: "Shorter means a quicker finish to the shift. Compare it with your own swings rather than an absolute number.",
  },
  copSpeedTiming: {
    label: "Peak CoP speed vs 50/50", unit: "ms", get: (m) => m.peak_lateral_speed_rel_transition_ms,
    what: "When the pressure point moves fastest relative to the 50/50 crossing. Negative means before it.",
    read: "In a clean shift the fastest movement comes close to the 50/50 crossing.",
  },
};

export const SETS = {
  shift: { label: "Weight shift", keys: ["address", "maxTrail", "maxLead", "leadImpact", "shiftRate", "copRange", "copSpeed"] },
  force: { label: "Vertical force", keys: ["peakFz", "peakLead", "minFz", "peakAfter5050", "peakVsImpact", "minVs5050"] },
  timing: { label: "Timing", keys: ["trailTo5050", "fiftyToLead", "peakAfter5050", "peakVsImpact", "minVs5050", "copSpeedTiming"] },
};

function loadPrefs() {
  try { return { set: "shift", units: "pct", ...JSON.parse(localStorage.getItem(STORE_KEY) ?? "{}") }; }
  catch { return { set: "shift", units: "pct" }; }
}

function savePrefs(p) {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(p)); } catch { /* private window: keep in memory */ }
}

function stats(vals) {
  if (vals.length < 3) return null;
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  const sd = Math.sqrt(vals.reduce((a, b) => a + (b - mean) ** 2, 0) / (vals.length - 1));
  return { mean, sd, n: vals.length };
}

function rangeSvg(value, ref, own, minSpan) {
  const pts = [value];
  if (ref) pts.push(ref.mean - ref.sd, ref.mean + ref.sd);
  if (own) pts.push(own.mean - own.sd, own.mean + own.sd);
  let lo = Math.min(...pts), hi = Math.max(...pts);
  const pad = Math.max((hi - lo) * 0.12, (minSpan - (hi - lo)) / 2, 1);
  lo -= pad; hi += pad;
  const x = (v) => (((v - lo) / (hi - lo)) * 100).toFixed(2);
  const band = (b, cls) => `<rect class="${cls}" x="${x(b.mean - b.sd)}%" width="${(x(b.mean + b.sd) - x(b.mean - b.sd)).toFixed(2)}%" y="${cls === "ref" ? 2 : 5}" height="${cls === "ref" ? 10 : 4}" rx="2"/>`;
  return `<svg class="range" aria-hidden="true" height="14" width="100%">
    <line x1="0" x2="100%" y1="7" y2="7"/>
    ${ref ? band(ref, "ref") : ""}${own ? band(own, "own") : ""}
    <circle cx="${x(value)}%" cy="7" r="4"/>
  </svg>`;
}

export class MetricsPanel {
  constructor({ list, help, sets, units }) {
    this.el = { list, help, sets, units };
    this.prefs = loadPrefs();
    if (!SETS[this.prefs.set]) this.prefs.set = "shift";
    this.swing = null;
    this.library = [];
    this.open = null;
    sets.innerHTML = Object.entries(SETS).map(([k, s]) => `<button type="button" data-set="${k}">${s.label}</button>`).join("");
    sets.addEventListener("click", (e) => {
      const b = e.target.closest("[data-set]");
      if (b) this.update({ set: b.dataset.set });
    });
    units.addEventListener("click", (e) => {
      const b = e.target.closest("[data-units]");
      if (b) this.update({ units: b.dataset.units });
    });
    list.addEventListener("click", (e) => {
      const b = e.target.closest("[data-why]");
      if (!b) return;
      this.open = this.open === b.dataset.why ? null : b.dataset.why;
      this.render();
    });
    this.render();
  }

  update(prefs) {
    this.prefs = { ...this.prefs, ...prefs };
    savePrefs(this.prefs);
    this.render();
  }

  show(swing, library) {
    this.swing = swing;
    this.library = library ?? this.library;
    this.render();
  }

  // value in display units for one swing summary, or null
  value(def, s) {
    const v = def.get(s.metrics ?? {});
    if (v == null) return null;
    return def.kind === "bw" && this.prefs.units === "n" ? (v / 100) * s.bw_n : v;
  }

  unit(def) {
    if (def.kind !== "bw") return def.unit;
    return this.prefs.units === "n" ? "N" : "%BW";
  }

  render() {
    const { list, help, sets, units } = this.el;
    const keys = SETS[this.prefs.set].keys;
    for (const b of sets.querySelectorAll("[data-set]")) b.setAttribute("aria-pressed", String(b.dataset.set === this.prefs.set));
    units.hidden = !keys.some((k) => METRICS[k].kind === "bw");
    for (const b of units.querySelectorAll("[data-units]")) b.setAttribute("aria-pressed", String(b.dataset.units === this.prefs.units));
    if (this.open && !keys.includes(this.open)) this.open = null;

    if (!this.swing) {
      list.innerHTML = `<li class="empty">Take a swing. Metrics appear here once it's captured.</li>`;
      help.hidden = true;
      return;
    }
    list.innerHTML = keys.map((k) => this.cardHtml(k)).join("");
    const def = METRICS[this.open];
    help.hidden = !def;
    if (def) {
      help.innerHTML = `<h3>${def.label}</h3><p>${def.what}</p><p>${def.read}</p>`
        + (def.ref ? `<p class="src">Reference ${fmt(def.ref.mean, 1)} ± ${fmt(def.ref.sd, 1)} ${def.kind === "bw" ? "%BW" : def.unit}: ${def.ref.src}</p>` : "")
        + (def.needsImpact ? `<p class="src">${NEEDS_IMPACT}</p>` : "");
    }
  }

  cardHtml(key) {
    const def = METRICS[key];
    const unit = this.unit(def);
    const n = def.kind === "bw" && this.prefs.units === "n";
    const v = this.value(def, this.swing);
    const why = `<button type="button" class="why" data-why="${key}" aria-expanded="${this.open === key}" aria-controls="metric-help" aria-label="What is ${def.label}?">?</button>`;
    if (v == null) {
      const reason = def.needsImpact ? "No shot event" : "No data";
      return `<li class="metric"><div class="name">${def.label}${why}</div><div class="val na" title="${def.needsImpact ? NEEDS_IMPACT : "Not detected in this swing"}">${reason}</div></li>`;
    }
    const own = stats(this.library.map((s) => this.value(def, s)).filter((x) => x != null));
    let ref = def.ref;
    if (ref && n) {
      const k = this.swing.bw_n / 100;
      ref = { ...ref, mean: ref.mean * k, sd: ref.sd * k };
    }
    const ctx = [
      own ? `<span class="you">You ${fmt(own.mean)} ± ${fmt(own.sd)} <span class="n">(${own.n})</span></span>` : "",
      ref ? `<span class="ref">Ref ${fmt(ref.mean)} ± ${fmt(ref.sd)}</span>` : "",
    ].join("");
    return `<li class="metric${this.open === key ? " open" : ""}">
      <div class="name">${def.label}${why}</div>
      <div class="val">${fmt(v)}<small>${unit}</small></div>
      ${own || ref ? rangeSvg(v, ref, own, n ? 0.4 * this.swing.bw_n : MIN_SPAN[unit] ?? 0) : ""}
      ${ctx ? `<div class="ctx">${ctx}</div>` : ""}
    </li>`;
  }
}
