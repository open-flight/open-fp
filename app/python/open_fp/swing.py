"""Swing state machine, force event detection and metrics (§9.6).

States: idle -> address -> armed -> swinging -> review. Only vertical-force-derived
events and metrics; impact is known only from an external shot event or manual mark.
Times in a Swing's `events` are seconds from the first captured sample.
"""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

import numpy as np

from .config import Config
from .pipeline import Samples, json_list

HISTORY_S = 10.0
SMOOTH_TAU_S = 0.02
LAG_S = 0.05
TOTAL_EMA_TAU_S = 0.5
ADDRESS_ENTER_S = 0.1
MANUAL_LOOKBACK_S = 1.5


def lateral_speed(t: np.ndarray, x: np.ndarray, lag_s: float = LAG_S) -> np.ndarray:
    """Signed rate of change of x over a `lag_s` window (NaN for the first lag)."""
    t, x = np.asarray(t, float), np.asarray(x, float)
    out = np.full(len(x), np.nan)
    if len(t) < 2:
        return out
    k = max(1, int(round(lag_s / np.median(np.diff(t)))))
    if len(x) > k:
        out[k:] = (x[k:] - x[:-k]) / (t[k:] - t[:-k])
    return out


def _smooth(x: np.ndarray, n: int = 5) -> np.ndarray:
    """Centred moving average that ignores NaN."""
    x = np.asarray(x, float)
    ok = ~np.isnan(x)
    kern = np.ones(n)
    num = np.convolve(np.where(ok, x, 0.0), kern, "same")
    den = np.convolve(ok.astype(float), kern, "same")
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    out[~ok] = np.nan
    return out


def _f(v, digits=1):
    """Plain rounded float, or None for missing/NaN."""
    if v is None:
        return None
    v = float(v)
    return None if math.isnan(v) else round(v, digits)


@dataclass
class Swing:
    id: str
    created: str
    golfer: str
    bw_n: float
    t0_host: float                 # host monotonic time of arrays["t"][0]
    arrays: dict                   # t, forces (n,8), fz_L, fz_R, cop_L, cop_R, cop_C, lead_pct
    events: dict                   # name -> seconds from t0, or None
    metrics: dict
    impact_source: str | None = None   # "shot" | "manual" | None

    def summary(self) -> dict:
        cop = self.arrays["cop_C"]
        idx = np.unique(np.linspace(0, len(cop) - 1, min(60, len(cop))).astype(int))
        return {
            "id": self.id, "created": self.created, "golfer": self.golfer, "bw_n": _f(self.bw_n),
            "events": {k: _f(v, 3) for k, v in self.events.items()},
            "metrics": self.metrics, "impact_source": self.impact_source,
            "path": json_list(cop[idx], 1),
        }

    def to_dict(self) -> dict:
        a = self.arrays
        return {
            **self.summary(),
            "t0_host": self.t0_host,
            "arrays": {
                "t": np.round(a["t"], 4).tolist(),
                "forces": json_list(a["forces"], 1),
                "fz_L": json_list(a["fz_L"], 1), "fz_R": json_list(a["fz_R"], 1),
                "cop_L": json_list(a["cop_L"], 1), "cop_R": json_list(a["cop_R"], 1),
                "cop_C": json_list(a["cop_C"], 1), "lead_pct": json_list(a["lead_pct"], 2),
            },
        }


class _Tick(NamedTuple):
    """One 200 Hz sample as the state machine sees it."""
    t: float
    total: float          # N, both plates
    f_lead: float
    f_trail: float
    lead: float           # lead % of total
    vx: float             # lateral CoP speed, mm/s (signed)
    v2: float             # CoP speed, mm/s


@dataclass
class Event:
    kind: str                      # "state" | "swing_complete" | "swing_updated"
    swing: Swing | None = None
    state: str | None = None


def analyze(a: dict, cfg: Config, bw_n: float, *, ms_i: int, trig_i: int,
            impact_i: int | None = None) -> tuple[dict, dict]:
    """Detect force events and compute metrics on a captured swing's arrays."""
    th = cfg.swing
    t, lead = a["t"], a["lead_pct"]
    cop_c = a["cop_C"]
    x = _smooth(cop_c[:, 0])
    rate = 1 / np.median(np.diff(t))
    n = len(t)

    def argext(fn, arr, lo, hi):
        seg = arr[lo:hi]
        return None if hi <= lo or np.all(np.isnan(seg)) else lo + int(fn(seg))

    mt = argext(np.nanargmin, lead, ms_i, trig_i + 1)
    tr = None
    if mt is not None and lead[mt] < 50:
        up = np.flatnonzero(lead[mt:] >= 50)
        tr = mt + int(up[0]) if len(up) else None
    ml = argext(np.nanargmax, lead, tr if tr is not None else (mt or ms_i), n)

    speed2d = np.hypot(lateral_speed(t, x), lateral_speed(t, _smooth(cop_c[:, 1])))
    fin = None
    if ml is not None:
        hold = int(th.finish_hold_s * rate)
        slow = np.nan_to_num(speed2d[ml:], nan=np.inf) < th.finish_speed_mm_s
        run = 0
        for j, s in enumerate(slow):
            run = run + 1 if s else 0
            if run >= hold:
                fin = ml + j - hold + 1
                break

    def at(i):
        return None if i is None else float(t[i])

    events = {"motion_start": at(ms_i), "max_trail": at(mt), "transition": at(tr),
              "max_lead": at(ml), "finish": at(fin), "impact": at(impact_i), "trigger": at(trig_i)}

    lp, tp = cfg.lead_plate, cfg.trail_plate
    lead_cop, trail_cop = a[f"cop_{lp}"], a[f"cop_{tp}"]
    fz_lead, fz_trail = a[f"fz_{lp}"], a[f"fz_{tp}"]
    total = fz_lead + fz_trail
    pre = slice(0, max(ms_i, 1))
    end = fin if fin is not None else n
    vx = lateral_speed(t, x)
    move = slice(ms_i, end)
    pk = ms_i + int(np.nanargmax(np.abs(vx[move]))) if np.any(~np.isnan(vx[move])) else None

    def ms(i, j):
        return None if i is None or j is None else round((t[i] - t[j]) * 1000, 0)

    def val(arr, i, d=1):
        return None if i is None else _f(arr[i], d)

    # Vertical force peaks are taken over the downswing only (max trail to finish), so a
    # step off the plates after the finish can't win. The unweighting minimum is the low
    # point between motion start and that peak.
    ds = mt if mt is not None else ms_i
    total_s, lead_s = _smooth(total), _smooth(fz_lead)
    pk_fz = argext(np.nanargmax, total_s, ds, end)
    pk_lead = argext(np.nanargmax, lead_s, ds, end)
    mn_fz = argext(np.nanargmin, total_s, ms_i, pk_fz if pk_fz is not None else end)

    metrics = {
        "lead_pct_address": _f(np.nanmean(lead[pre])),
        "lead_pct_max_trail": val(lead, mt),
        "lead_pct_max_lead": val(lead, ml),
        "lead_pct_impact": val(lead, impact_i),
        "lead_cop_y_address_mm": _f(np.nanmean(lead_cop[pre, 1])),
        "trail_cop_y_address_mm": _f(np.nanmean(trail_cop[pre, 1])),
        "lead_cop_y_max_lead_mm": None if ml is None else _f(lead_cop[ml, 1]),
        "trail_cop_y_max_lead_mm": None if ml is None else _f(trail_cop[ml, 1]),
        "time_max_trail_to_transition_ms": ms(tr, mt),
        "time_transition_to_max_lead_ms": ms(ml, tr),
        "peak_shift_rate_pct_s": _f(np.nanmax(lateral_speed(t, lead)[ms_i:])),
        "lateral_cop_range_mm": _f(np.nanmax(x[move]) - np.nanmin(x[move])),
        "lateral_cop_path_mm": _f(np.nansum(np.abs(np.diff(x[move])))),
        "peak_lateral_speed_mm_s": None if pk is None else _f(abs(vx[pk])),
        "peak_lateral_speed_rel_transition_ms": ms(pk, tr),
        "peak_fz_pct_bw": {
            "lead": _f(100 * np.nanmax(fz_lead) / bw_n),
            "trail": _f(100 * np.nanmax(fz_trail) / bw_n),
            "total": _f(100 * np.nanmax(total) / bw_n),
        },
        "peak_lead_fz_rel_impact_ms": ms(pk_lead, impact_i),
        "peak_lead_fz_rel_transition_ms": ms(pk_lead, tr),
        "peak_fz_downswing_pct_bw": None if pk_fz is None else _f(100 * total_s[pk_fz] / bw_n),
        "peak_fz_rel_transition_ms": ms(pk_fz, tr),
        "peak_fz_rel_impact_ms": ms(pk_fz, impact_i),
        "min_fz_pct_bw": None if mn_fz is None else _f(100 * total_s[mn_fz] / bw_n),
        "min_fz_rel_transition_ms": ms(mn_fz, tr),
        "min_fz_rel_impact_ms": ms(mn_fz, impact_i),
    }
    return events, metrics


class SwingDetector:
    def __init__(self, cfg: Config, now_fn=time.time):
        self.cfg = cfg
        self.now_fn = now_fn
        self.state = "idle"
        self.bw_n: float | None = cfg.bw_override_n
        self.last_swing: Swing | None = None
        self._hist: deque[Samples] = deque()
        self._ids: set[str] = set()
        self._last_t: float | None = None
        self._sxy: np.ndarray | None = None
        self._lag: deque[tuple[float, np.ndarray]] = deque()
        self._total_ema: float | None = None
        self._quiet_since: float | None = None
        self._quiet: deque[tuple[float, float, float]] = deque()   # (t, total, lead)
        self._quiet_for = 0.0
        self._address_lead: float | None = None
        # per-swing state, cleared by _reset_swing()
        self._motion_start: float | None = None
        self._trigger: float | None = None
        self._impact: float | None = None
        self._impact_source: str | None = None
        self._run_start: float | None = None
        self._last_slow_t: float | None = None
        self._min_lead = math.inf

    def set_config(self, cfg: Config):
        self.cfg = cfg
        if cfg.bw_override_n:
            self.bw_n = cfg.bw_override_n

    # -- public control ----------------------------------------------------

    def update(self, s: Samples) -> list[Event]:
        events: list[Event] = []
        if len(s) == 0:
            return events
        self._hist.append(s)
        while self._hist and s.t[-1] - self._hist[0].t[-1] > HISTORY_S:
            self._hist.popleft()
        lead_plate, trail_plate = self.cfg.lead_plate, self.cfg.trail_plate
        for i in range(len(s)):
            t = float(s.t[i])
            vx, v2 = self._speeds(t, s.cop["C"][i])
            tick = _Tick(t, float(s.fz_total[i]), float(s.fz[lead_plate][i]),
                         float(s.fz[trail_plate][i]), float(s.lead_pct[i]), vx, v2)
            self._step(tick, events)
        return events

    def arm(self) -> bool:
        if self._last_t is None or not self._quiet:
            return False
        self._arm()
        return True

    def trigger(self) -> bool:
        """Manual trigger: capture now (or the swing in progress)."""
        if self.state == "swinging" and self._trigger is None:
            self._trigger = self._last_t
            return True
        if self.state == "armed":
            self._motion_start = self._last_t - MANUAL_LOOKBACK_S
            self._trigger = self._last_t
            self._set_state("swinging", [])
            return True
        return False

    def mark_impact(self, t_host: float, source: str = "shot") -> list[Event]:
        """Label impact at host time `t_host` in the current or most recent swing."""
        swinging = self.state == "swinging" and self._motion_start is not None
        if swinging and t_host >= self._motion_start:
            if self._trigger is None:
                self._trigger = t_host
            self._impact, self._impact_source = t_host, source
            return []
        sw = self.last_swing
        if sw is not None and sw.t0_host <= t_host <= sw.t0_host + sw.arrays["t"][-1]:
            t = sw.arrays["t"]
            ms_i = self._index(t, sw.events["motion_start"])
            trig_i = self._index(t, sw.events["trigger"])
            sw.events, sw.metrics = analyze(sw.arrays, self.cfg, sw.bw_n, ms_i=ms_i, trig_i=trig_i,
                                            impact_i=self._index(t, t_host - sw.t0_host))
            sw.impact_source = source
            return [Event("swing_updated", swing=sw)]
        return []

    # -- per-sample machinery ------------------------------------------------

    def _speeds(self, t: float, xy: np.ndarray) -> tuple[float, float]:
        if np.any(np.isnan(xy)):
            self._sxy, self._lag = None, deque()
            return math.nan, math.nan
        if self._sxy is None:
            self._sxy = xy.astype(float).copy()
        else:
            dt = t - self._last_t if self._last_t is not None else 0.0
            self._sxy += (dt / (SMOOTH_TAU_S + dt)) * (xy - self._sxy)
        self._lag.append((t, self._sxy.copy()))
        while len(self._lag) > 1 and t - self._lag[0][0] > LAG_S + 1e-9:
            self._lag.popleft()
        t0, p0 = self._lag[0]
        if t - t0 < LAG_S * 0.9:
            return math.nan, math.nan
        v = (self._sxy - p0) / (t - t0)
        return float(v[0]), float(np.hypot(*v))

    def _step(self, k: _Tick, events: list[Event]) -> None:
        th = self.cfg.swing
        prev_t, self._last_t = self._last_t, k.t
        dt = k.t - prev_t if prev_t is not None else 0.0
        idle_thr = th.idle_total_pct_bw / 100 * self.bw_n if self.bw_n else th.idle_total_n
        if k.total < idle_thr:
            self._quiet_since, self._total_ema = None, None
            self._quiet.clear()
            if self.state != "idle":
                self._reset_swing()
                self._set_state("idle", events)
            return
        quiet = self._update_quiet(k, dt)
        if self.state in ("idle", "review", "address"):
            self._step_waiting(quiet, events)
        elif self.state == "armed":
            self._step_armed(k, quiet, events)
        elif self.state == "swinging":
            self._step_swinging(k, events)

    def _update_quiet(self, k: _Tick, dt: float) -> bool:
        """Track whether the golfer is standing still at address; returns this sample's verdict."""
        th = self.cfg.swing
        if self._total_ema is None:
            self._total_ema = k.total
        else:
            self._total_ema += dt / (TOTAL_EMA_TAU_S + dt) * (k.total - self._total_ema)
        steady = abs(k.total - self._total_ema) <= th.address_total_tol_pct / 100 * self._total_ema
        quiet = (min(k.f_lead, k.f_trail) > th.address_foot_pct / 100 * k.total
                 and steady and k.v2 < th.address_cop_speed_mm_s)
        if quiet:
            if self._quiet_since is None:
                self._quiet_since = k.t
            self._quiet.append((k.t, k.total, k.lead))
            while self._quiet and k.t - self._quiet[0][0] > th.address_hold_s:
                self._quiet.popleft()
        else:
            self._quiet_since = None
            self._quiet.clear()
        self._quiet_for = k.t - self._quiet_since if self._quiet_since is not None else 0.0
        return quiet

    def _step_waiting(self, quiet: bool, events: list[Event]) -> None:
        """idle / review / address: arm once the golfer holds still long enough."""
        if self._quiet_for >= self.cfg.swing.address_hold_s:
            self._arm(events)
        elif self._quiet_for >= ADDRESS_ENTER_S and self.state != "address":
            self._set_state("address", events)
        elif not quiet and self.state == "address":
            self._set_state("idle", events)

    def _step_armed(self, k: _Tick, quiet: bool, events: list[Event]) -> None:
        """armed: start a swing on sustained lateral CoP motion."""
        th = self.cfg.swing
        if quiet:
            self._address_lead = float(np.mean([q[2] for q in self._quiet]))
        if not math.isnan(k.v2) and k.v2 < th.address_cop_speed_mm_s:
            self._last_slow_t = k.t
        if math.isnan(k.vx) or abs(k.vx) <= th.motion_speed_mm_s:
            self._run_start = None
            return
        if self._run_start is None:
            self._run_start = k.t
        if k.t - self._run_start >= th.motion_sustain_s:
            slow = self._last_slow_t
            self._motion_start = slow if slow is not None else self._run_start
            self._min_lead = k.lead
            self._set_state("swinging", events)

    def _step_swinging(self, k: _Tick, events: list[Event]) -> None:
        """swinging: wait for the downswing trigger, then capture until post-trigger time."""
        th = self.cfg.swing
        if not math.isnan(k.lead):
            self._min_lead = min(self._min_lead, k.lead)
        if self._trigger is not None:
            start = self._motion_start - th.pre_roll_s
            if k.t >= self._trigger + th.post_trigger_s or k.t - start >= th.max_capture_s:
                self._finalize(k.t, events)
            return
        if min(k.f_lead, k.f_trail) < th.min_foot_pct_bw / 100 * (self.bw_n or k.total):
            # a foot came off the plate: stepping, not swinging
            self._reset_swing()
            self._set_state("idle", events)
        elif self._quiet_for >= th.address_hold_s:  # settled back without swinging
            self._reset_swing()
            self._arm(events)
        elif k.t - self._motion_start > th.max_capture_s - th.pre_roll_s - th.post_trigger_s:
            self._reset_swing()
            self._set_state("idle", events)
        elif (self._address_lead is not None
              and self._min_lead <= self._address_lead - th.min_backswing_shift_pct
              and not math.isnan(k.vx) and k.vx * self.cfg.lead_dir_x > th.trigger_speed_mm_s):
            self._trigger = k.t

    # -- helpers -------------------------------------------------------------

    def _arm(self, events=None):
        if self._quiet:
            if not self.cfg.bw_override_n:
                self.bw_n = float(np.mean([q[1] for q in self._quiet]))
            self._address_lead = float(np.mean([q[2] for q in self._quiet]))
        self._set_state("armed", events if events is not None else [])

    def _set_state(self, state: str, events: list):
        if state != self.state:
            self.state = state
            events.append(Event("state", state=state))

    def _reset_swing(self):
        self._motion_start = self._trigger = self._impact = None
        self._impact_source = None
        self._run_start = self._last_slow_t = None
        self._min_lead = math.inf

    @staticmethod
    def _index(t: np.ndarray, rel: float | None) -> int | None:
        if rel is None:
            return None
        return int(np.clip(np.searchsorted(t, rel - 1e-9), 0, len(t) - 1))

    def _finalize(self, t_end: float, events: list):
        th = self.cfg.swing
        s = Samples.concat(list(self._hist))
        start = self._motion_start - th.pre_roll_s
        m = (s.t >= start - 1e-9) & (s.t <= t_end + 1e-9)
        t0 = float(s.t[m][0])
        arrays = {
            "t": s.t[m] - t0, "forces": s.forces[m],
            "fz_L": s.fz["L"][m], "fz_R": s.fz["R"][m],
            "cop_L": s.cop["L"][m], "cop_R": s.cop["R"][m], "cop_C": s.cop["C"][m],
            "lead_pct": s.lead_pct[m],
        }
        t = arrays["t"]
        ms_i = self._index(t, self._motion_start - t0)
        trig_i = self._index(t, self._trigger - t0)
        imp_i = self._index(t, self._impact - t0) if self._impact is not None else None
        bw = self.bw_n or float(np.nanmedian(s.fz_total[m]))
        ev, metrics = analyze(arrays, self.cfg, bw, ms_i=ms_i, trig_i=trig_i, impact_i=imp_i)
        created = self.now_fn()
        swing = Swing(id=self._new_id(created),
                      created=datetime.fromtimestamp(created).isoformat(timespec="seconds"),
                      golfer=self.cfg.golfer, bw_n=bw, t0_host=t0, arrays=arrays, events=ev,
                      metrics=metrics,
                      impact_source=self._impact_source if self._impact is not None else None)
        self.last_swing = swing
        self._reset_swing()
        self._quiet_since = None        # re-address needs a fresh quiet period after review
        self._quiet.clear()
        self._set_state("review", events)
        events.append(Event("swing_complete", swing=swing))

    def _new_id(self, created: float) -> str:
        millis = int(created * 1000) % 1000
        base = datetime.fromtimestamp(created).strftime("%Y%m%d-%H%M%S-") + f"{millis:03d}"
        sid, k = base, 1
        while sid in self._ids:
            k += 1
            sid = f"{base}-{k}"
        self._ids.add(sid)
        return sid
