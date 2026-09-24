"""Counts -> forces -> CoP -> lead/trail (§9.3), plus zeroing and drift (§9.4)."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .calibration import Calibration
from .clock import ClockMapper
from .config import CHANNEL_IDS, N_CH, Config
from .protocol import FLAG_DRDY_MISSED, FLAG_SATURATION, Batch, SequenceTracker

FULL_SCALE_COUNTS = 2**23
TARE_DRIFT_WARN = 0.02 * FULL_SCALE_COUNTS
FLAG_HOLD_S = 2.0          # how long a saturation / missed-DRDY flag stays up in status


@dataclass
class Samples:
    t: np.ndarray            # (n,) host monotonic seconds
    counts: np.ndarray       # (n, 8) int32
    forces: np.ndarray       # (n, 8) N
    fz: dict                 # "L", "R" -> (n,) N
    fz_total: np.ndarray     # (n,) N
    cop: dict                # "L", "R", "C" -> (n, 2) mm, NaN when unloaded
    lead_pct: np.ndarray     # (n,) %, NaN when unloaded
    flags: int = 0

    def __len__(self):
        return len(self.t)

    @classmethod
    def concat(cls, parts: list["Samples"]) -> "Samples":
        return cls(
            t=np.concatenate([p.t for p in parts]),
            counts=np.concatenate([p.counts for p in parts]),
            forces=np.concatenate([p.forces for p in parts]),
            fz={k: np.concatenate([p.fz[k] for p in parts]) for k in ("L", "R")},
            fz_total=np.concatenate([p.fz_total for p in parts]),
            cop={k: np.concatenate([p.cop[k] for p in parts]) for k in ("L", "R", "C")},
            lead_pct=np.concatenate([p.lead_pct for p in parts]),
            flags=int(np.bitwise_or.reduce([p.flags for p in parts])) if parts else 0,
        )


class Stats:
    def __init__(self):
        self.batches = 0
        self.frames = 0
        self.dropped = 0              # batches dropped on the Linux side (inbox full)
        self.decode_errors = 0


class _RawHistory:
    """Ring buffer of recent raw counts for zeroing and calibration captures."""

    def __init__(self, capacity: int):
        self.buf = np.zeros((capacity, N_CH))
        self.n = 0
        self.i = 0

    def extend(self, counts: np.ndarray):
        for row in counts:
            self.buf[self.i] = row
            self.i = (self.i + 1) % len(self.buf)
            self.n = min(self.n + 1, len(self.buf))

    def last(self, k: int) -> np.ndarray:
        k = min(k, self.n)
        idx = (self.i - k + np.arange(k)) % len(self.buf)
        return self.buf[idx]


class Pipeline:
    RATE_HZ = 200.0

    def __init__(self, cfg: Config, cal: Calibration | None = None, clock_latency_s: float = 0.0,
                 auto_zero_n: float = 20.0, auto_zero_after_s: float = 3.0, auto_zero_tau_s: float = 5.0):
        self.cfg = cfg
        self.stats = Stats()
        self.seq = SequenceTracker()
        self.clock = ClockMapper(fixed_latency_s=clock_latency_s)
        self.ui_buffer = UiBuffer()
        self._history = _RawHistory(int(self.RATE_HZ * 10))
        self.auto_zero_n = auto_zero_n
        self.auto_zero_after_s = auto_zero_after_s
        self.auto_zero_tau_s = auto_zero_tau_s
        self._quiet_s = 0.0
        self._last_arrival = 0.0
        self._last_flag_t = {FLAG_SATURATION: -math.inf, FLAG_DRDY_MISSED: -math.inf}
        self.set_calibration(cal or Calibration.default())
        self.set_config(cfg)

    def set_config(self, cfg: Config):
        self.cfg = cfg
        self._signs = np.asarray(cfg.signs, dtype=float)
        self._pos = np.asarray(cfg.positions())
        self._idx = {p: cfg.plate_channels(p) for p in ("L", "R")}

    def set_calibration(self, cal: Calibration):
        self.cal = cal
        self.tares = np.asarray(cal.tares, dtype=float).copy()
        self._gains = np.asarray(cal.gains, dtype=float)

    # -- processing --------------------------------------------------------

    def process(self, batch: Batch, arrival_s: float) -> Samples:
        self.stats.batches += 1
        self.stats.frames += batch.n
        before = self.seq.restarts
        self.seq.update(batch.seq)
        if self.seq.restarts != before:
            self.clock.reset()
        mcu_us = batch.sample_times_us()
        self.clock.update(int(mcu_us[-1]) % 2**32, arrival_s)
        t = self.clock.to_host_array(mcu_us)
        self._last_arrival = arrival_s
        for flag in self._last_flag_t:
            if batch.flags & flag:
                self._last_flag_t[flag] = arrival_s

        counts = batch.counts
        self._history.extend(counts)
        forces = self._forces(counts)
        self._auto_zero(counts, forces)
        return self._derive(t, counts, forces, batch.flags)

    def _forces(self, counts: np.ndarray) -> np.ndarray:
        return self._signs * self._gains * (counts - self.tares)

    def _auto_zero(self, counts: np.ndarray, forces: np.ndarray):
        dt = 1 / self.RATE_HZ
        alpha = dt / self.auto_zero_tau_s
        for row, f in zip(counts, forces):
            if abs(f.sum()) < self.auto_zero_n:
                self._quiet_s += dt
                if self._quiet_s >= self.auto_zero_after_s:
                    self.tares += alpha * (row - self.tares)
            else:
                self._quiet_s = 0.0

    def _derive(self, t, counts, forces, flags) -> Samples:
        fz, cop = {}, {}
        for p, idx in self._idx.items():
            fp = forces[:, idx]
            fz[p] = fp.sum(axis=1)
            with np.errstate(invalid="ignore", divide="ignore"):
                c = fp @ self._pos[idx] / fz[p][:, None]
            c[fz[p] < self.cfg.cop_min_force_n] = np.nan
            cop[p] = c
        total = fz["L"] + fz["R"]
        loaded = {p: np.where(np.isnan(cop[p][:, :1]), 0.0, fz[p][:, None]) for p in ("L", "R")}
        w = loaded["L"] + loaded["R"]
        with np.errstate(invalid="ignore", divide="ignore"):
            cop["C"] = (loaded["L"] * np.nan_to_num(cop["L"]) + loaded["R"] * np.nan_to_num(cop["R"])) / w
            lead = 100.0 * fz[self.cfg.lead_plate] / total
        cop["C"][w[:, 0] <= 0] = np.nan
        lead[total < self.cfg.cop_min_force_n] = np.nan
        return Samples(t, counts, forces, fz, total, cop, lead, flags)

    # -- control -----------------------------------------------------------

    def recent_counts(self, seconds: float) -> np.ndarray:
        """Raw counts (k, 8) from the last `seconds`; empty before any data."""
        return self._history.last(int(seconds * self.RATE_HZ))

    def mean_counts(self, seconds: float = 2.0) -> np.ndarray:
        rows = self.recent_counts(seconds)
        if len(rows) == 0:
            raise RuntimeError("no samples yet")
        return rows.mean(axis=0)

    def zero_now(self, seconds: float = 2.0) -> dict:
        self.tares = self.mean_counts(seconds)
        self._quiet_s = 0.0
        return {"ok": True, "tares": self.tares.tolist()}

    def status(self) -> dict:
        now = self._last_arrival
        drift = []
        if self.cal.is_calibrated:
            moved = np.abs(self.tares - np.asarray(self.cal.tares)) > TARE_DRIFT_WARN
            drift = [CHANNEL_IDS[i] for i in np.flatnonzero(moved)]
        return {
            "batches": self.stats.batches,
            "frames": self.stats.frames,
            "dropped": self.stats.dropped,
            "decode_errors": self.stats.decode_errors,
            "seq_gaps": self.seq.gaps,
            "seq_missing": self.seq.missing,
            "mcu_restarts": self.seq.restarts,
            "saturation": now - self._last_flag_t[FLAG_SATURATION] < FLAG_HOLD_S,
            "drdy_missed": now - self._last_flag_t[FLAG_DRDY_MISSED] < FLAG_HOLD_S,
            "calibrated": self.cal.is_calibrated,
            "calibration_date": self.cal.created,
            "tare_drift_channels": drift,
        }


def json_list(a: np.ndarray, digits: int) -> list:
    """Round and turn NaN into None so the result is strict JSON. Rows with NaN -> None."""
    a = np.round(np.asarray(a, dtype=float), digits)
    if a.ndim == 1:
        return [None if math.isnan(v) else v for v in a.tolist()]
    return [None if any(math.isnan(v) for v in row) else row for row in a.tolist()]


class UiBuffer:
    """Accumulates samples between 30 Hz UI pushes (§9.3 'live' message)."""

    def __init__(self):
        self._parts: list[Samples] = []

    def extend(self, samples: Samples):
        if len(samples):
            self._parts.append(samples)

    def drain(self, **extra) -> dict:
        parts, self._parts = self._parts, []
        if not parts:
            return {"t": [], "fz": {"L": [], "R": []}, "cop": {"L": [], "R": [], "C": []},
                    "lead_pct": [], "forces": [], "flags": 0, **extra}
        s = Samples.concat(parts)
        return {
            "t": np.round(s.t, 4).tolist(),
            "fz": {k: json_list(s.fz[k], 1) for k in ("L", "R")},
            "cop": {k: json_list(s.cop[k], 1) for k in ("L", "R", "C")},
            "lead_pct": json_list(s.lead_pct, 2),
            "forces": np.round(s.forces, 0).tolist(),
            "flags": s.flags,
            **extra,
        }
