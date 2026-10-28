// Swing library cards.

const fmt = (v, d = 0) => (v == null ? null : Number(v).toFixed(d));

function timeOf(created) {
  const d = new Date(created);
  return isNaN(d) ? created : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function pathSvg(points, golfer) {
  const pts = points.filter(Boolean);
  if (pts.length < 2) return `<svg viewBox="0 0 64 64" aria-hidden="true"></svg>`;
  const mirror = golfer === "LH" ? -1 : 1;
  const xs = pts.map((p) => mirror * p[0]), ys = pts.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const span = Math.max(x1 - x0, y1 - y0, 40);
  const sx = (x) => 32 + ((x - (x0 + x1) / 2) / span) * 54;
  const sy = (y) => 32 - ((y - (y0 + y1) / 2) / span) * 54;
  const d = pts.map((p, i) => `${i ? "L" : "M"}${sx(mirror * p[0]).toFixed(1)} ${sy(p[1]).toFixed(1)}`).join("");
  const first = pts[0], last = pts[pts.length - 1];
  return `<svg viewBox="0 0 64 64" aria-hidden="true">
    <rect x="0.5" y="0.5" width="63" height="63" rx="4" fill="none" stroke="var(--line)"/>
    <path d="${d}" fill="none" stroke="var(--comb)" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" opacity="0.85"/>
    <circle cx="${sx(mirror * first[0])}" cy="${sy(first[1])}" r="2.5" fill="var(--muted)"/>
    <circle cx="${sx(mirror * last[0])}" cy="${sy(last[1])}" r="2.5" fill="var(--lead)"/>
  </svg>`;
}

export function cardHtml(s) {
  const m = s.metrics;
  const trailPct = m.lead_pct_max_trail == null ? null : 100 - m.lead_pct_max_trail;
  return `<button type="button" class="card" data-id="${s.id}" aria-label="Replay swing from ${timeOf(s.created)}">
    ${pathSvg(s.path, s.golfer)}
    <span class="when num">${timeOf(s.created)}${s.impact_source ? ' <span class="imp">impact</span>' : ""}</span>
    <span class="nums num"><span class="t">trail <b>${fmt(trailPct) ?? "—"}%</b></span><span class="l">lead <b>${fmt(m.lead_pct_max_lead) ?? "—"}%</b></span></span>
    <span class="nums num"><span>transition <b>${fmt(m.time_max_trail_to_transition_ms) ?? "—"}</b> ms</span></span>
  </button>`;
}

export function renderCards(ol, list, currentId) {
  if (!list.length) {
    ol.innerHTML = `<li class="empty">No swings yet. Step on, settle at address, and swing — captures show up here.</li>`;
    return;
  }
  ol.innerHTML = list.map((s) => `<li>${cardHtml(s)}</li>`).join("");
  if (currentId) ol.querySelector(`[data-id="${currentId}"]`)?.setAttribute("aria-current", "true");
}
