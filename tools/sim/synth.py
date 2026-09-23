"""Synthetic 8-channel force plate data for the simulator and tests (§11.5).

A session is a list of Scenario segments (empty, step_on, stance, swing, sway, shuffle).
Each segment is described as lead % of total load, total load in bodyweights, and a CoP
offset from each foot's plate centre; that is turned into per-cell forces (bilinear split,
so CoP is exact), then into ADC counts with a calibration, noise, and slow tare drift.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from open_fp.calibration import G, Calibration
from open_fp.config import N_CH, Config
from open_fp.protocol import Batch

RATE_HZ = 200.0
PERIOD_US = 5000


def corner_forces(cfg: Config, plate: str, xy, total_n) -> np.ndarray:
    """Split a point load on one plate over its 4 cells so CoP lands exactly at xy.

    Bilinear weights over the rectangle spanned by the cells. xy (..., 2), total_n (...)
    -> forces (..., 8) in N, zero on the other plate's channels.
    """
    idx = cfg.plate_channels(plate)
    pos = np.asarray(cfg.positions())[idx]
    x0, x1 = pos[:, 0].min(), pos[:, 0].max()
    y0, y1 = pos[:, 1].min(), pos[:, 1].max()
    xy = np.asarray(xy, dtype=float)
    u = ((xy[..., 0] - x0) / (x1 - x0))[..., None]
    v = ((xy[..., 1] - y0) / (y1 - y0))[..., None]
    wx = np.where(np.isclose(pos[:, 0], x1), u, 1 - u)
    wy = np.where(np.isclose(pos[:, 1], y1), v, 1 - v)
    out = np.zeros(xy.shape[:-1] + (N_CH,))
    out[..., idx] = np.asarray(total_n, dtype=float)[..., None] * wx * wy
    return out


@dataclass
class Scenario:
    kind: str                     # empty | step_on | stance | swing | sway | shuffle
    duration: float | None = None
    params: dict = field(default_factory=dict)


@dataclass
class SynthData:
    t: np.ndarray                 # (n,) seconds from session start
    forces: np.ndarray            # (n, 8) N, true per-cell forces
    counts: np.ndarray            # (n, 8) int32
    truth: dict


@dataclass
class _Seg:
    lead: np.ndarray              # lead % of total (NaN = plates empty)
    total: np.ndarray             # total load, bodyweights
    lead_off: np.ndarray          # (n, 2) CoP offset from lead plate centre, mm
    trail_off: np.ndarray
    swings: list = field(default_factory=list)   # event times relative to segment start


def _keyframes(t: np.ndarray, keys: list[tuple[float, float]]) -> np.ndarray:
    """Piecewise smoothstep through (time, value) keys; flat outside."""
    kt = np.array([k[0] for k in keys])
    kv = np.array([k[1] for k in keys])
    out = np.full_like(t, kv[0], dtype=float)
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        m = (t >= t0) & (t <= t1)
        p = (t[m] - t0) / (t1 - t0) if t1 > t0 else np.ones(m.sum())
        out[m] = v0 + (v1 - v0) * (3 * p**2 - 2 * p**3)
    out[t > kt[-1]] = kv[-1]
    return out


def _times(duration: float) -> np.ndarray:
    return np.arange(int(round(duration * RATE_HZ))) / RATE_HZ


def _zeros2(n):
    return np.zeros((n, 2))


def _seg_empty(duration, rng, **_):
    t = _times(duration)
    return _Seg(np.full(len(t), np.nan), np.zeros(len(t)), _zeros2(len(t)), _zeros2(len(t)))


def _seg_stance(duration, rng, lead=55.0, **_):
    t = _times(duration)
    ph = rng.uniform(0, 2 * np.pi)
    sway = 1.5 * np.sin(2 * np.pi * 0.3 * t + ph)          # tiny postural sway, % lead
    off = np.stack([np.zeros_like(t), 2.0 * np.sin(2 * np.pi * 0.2 * t + ph)], axis=1)
    return _Seg(lead + sway, np.ones(len(t)), off, off.copy())


def _seg_step_on(duration, rng, lead=55.0, **_):
    t = _times(duration)
    total = _keyframes(t, [(0, 0.0), (duration * 0.6, 1.0)])
    return _Seg(np.full(len(t), lead), total, _zeros2(len(t)), _zeros2(len(t)))


def _seg_swing(duration, rng, address_s=2.0, tempo=None, **_):
    tempo = tempo if tempo is not None else rng.uniform(0.85, 1.15)
    a = address_s
    t_ms = a                                  # motion start
    t_mt = t_ms + 0.85 * tempo                # max trail (lead 30 %)
    t_ml = t_mt + 0.35 * tempo                # max lead (lead 88 %)
    t_imp = t_mt + 0.30 * tempo
    t_fin = t_ml + 1.0
    duration = duration or t_fin + 1.5
    t = _times(duration)
    lead = _keyframes(t, [(0, 55), (t_ms, 55), (t_mt, 30), (t_ml, 88), (t_fin, 90)])
    peak_t = t_mt + 0.32 * tempo
    total = 1.0 + 0.62 * np.exp(-0.5 * ((t - peak_t) / 0.07) ** 2)
    lead_y = _keyframes(t, [(0, 0), (t_mt, 10), (t_ml, -30), (t_fin, -25)])
    trail_y = _keyframes(t, [(0, 0), (t_mt, -20), (t_ml, 30), (t_fin, 60)])
    zeros = np.zeros_like(t)
    after = t > t_mt
    t_tr = float(t[after][np.argmax(lead[after] >= 50)])
    swing = {"motion_start": t_ms, "max_trail": t_mt, "transition": t_tr, "impact": t_imp,
             "max_lead": t_ml, "finish": t_fin, "tempo": tempo}
    return _Seg(lead, total, np.stack([zeros, lead_y], 1), np.stack([zeros, trail_y], 1), [swing])


def _seg_sway(duration, rng, amp=15.0, freq=0.4, **_):
    t = _times(duration)
    lead = 50 + amp * np.sin(2 * np.pi * freq * t)
    return _Seg(lead, np.ones(len(t)), _zeros2(len(t)), _zeros2(len(t)))


def _seg_shuffle(duration, rng, **_):
    t = _times(duration)
    lead = _keyframes(t, [(0, 55), (0.5, 55), (0.65, 0), (0.95, 0), (1.1, 55), (1.8, 55),
                          (1.95, 100), (2.25, 100), (2.4, 55)])
    return _Seg(lead, np.ones(len(t)), _zeros2(len(t)), _zeros2(len(t)))


_SEGMENTS = {
    "empty": (_seg_empty, 2.0), "step_on": (_seg_step_on, 1.0), "stance": (_seg_stance, 3.0),
    "swing": (_seg_swing, None), "sway": (_seg_sway, 8.0), "shuffle": (_seg_shuffle, 4.0),
}


def generate(scenarios: list[Scenario], cfg: Config, *, cal: Calibration | None = None,
             bw_kg: float = 82.0, seed: int = 0, noise_counts: float = 30.0,
             drift_counts_per_s: float = 5.0) -> SynthData:
    rng = np.random.default_rng(seed)
    segs, swings, t0 = [], [], 0.0
    for sc in scenarios:
        fn, default_dur = _SEGMENTS[sc.kind]
        seg = fn(sc.duration or default_dur, rng, **sc.params)
        swings += [{k: (v + t0 if k != "tempo" else v) for k, v in s.items()} for s in seg.swings]
        t0 += len(seg.lead) / RATE_HZ
        segs.append(seg)

    lead = np.concatenate([s.lead for s in segs])
    total_n = np.concatenate([s.total for s in segs]) * bw_kg * G
    lead_off = np.concatenate([s.lead_off for s in segs])
    trail_off = np.concatenate([s.trail_off for s in segs])
    n = len(lead)
    frac = np.nan_to_num(lead) / 100.0

    pos = np.asarray(cfg.positions())
    centre = {p: pos[cfg.plate_channels(p)].mean(axis=0) for p in ("L", "R")}
    forces = (corner_forces(cfg, cfg.lead_plate, centre[cfg.lead_plate] + lead_off, total_n * frac)
              + corner_forces(cfg, cfg.trail_plate, centre[cfg.trail_plate] + trail_off, total_n * (1 - frac)))

    cal = cal or Calibration(tares=rng.uniform(-50_000, 50_000, N_CH).tolist(),
                             gains=Calibration.default().gains)
    t = np.arange(n) / RATE_HZ
    drift = rng.uniform(-1, 1, N_CH) * drift_counts_per_s
    noise = rng.normal(0, noise_counts, (n, N_CH)) if noise_counts else 0.0
    counts = (np.asarray(cal.tares) + np.asarray(cfg.signs) * forces / np.asarray(cal.gains)
              + drift * t[:, None] + noise)
    counts = np.clip(np.round(counts), -(2**23), 2**23 - 1).astype(np.int32)

    truth = {"lead_pct": np.where(total_n > 0, lead, np.nan), "bw_n": bw_kg * G, "swings": swings}
    return SynthData(t, forces, counts, truth)


def to_batches(counts: np.ndarray, seq0: int = 0, t0_us: int = 0, frames: int = 10) -> list[Batch]:
    out = []
    for k, i in enumerate(range(0, len(counts), frames)):
        chunk = np.asarray(counts[i:i + frames], dtype=np.int32)
        out.append(Batch(seq=(seq0 + k) % 2**32, t_first_us=(t0_us + i * PERIOD_US) % 2**32,
                         period_us=PERIOD_US, flags=0, counts=chunk))
    return out
