"""Map MCU micros() timestamps to host monotonic time (§9.9).

Each batch gives a pair (MCU time, host arrival). Arrivals are delayed by a variable
transport latency but never early, so we fit a line to the *lower envelope* of
(host - mcu) offsets over a sliding window: split the window into bins, take the
earliest-arriving point in each bin, least-squares fit, then re-pick each bin's point
against the fitted trend (so clock drift doesn't bias the pick) and fit again.

`fixed_latency_s` is the part of the delay that is always present (e.g. serial time of
the batch itself) and is subtracted, since the envelope can't see it.
"""
from __future__ import annotations

from collections import deque

import numpy as np

WRAP = 2**32


class Unwrapper:
    """Extend a wrapping u32 counter to a monotonic int."""

    def __init__(self):
        self._last_raw: int | None = None
        self._last: int = 0

    def unwrap(self, raw: int, commit: bool = True) -> int:
        raw = int(raw)
        if self._last_raw is None:
            value = raw
        else:
            diff = (raw - self._last_raw) % WRAP
            value = self._last + diff if diff <= WRAP // 2 else self._last - (WRAP - diff)
        if commit:
            self._last_raw, self._last = raw, value
        return value


class ClockMapper:
    def __init__(self, window_s: float = 60.0, n_bins: int = 12, fixed_latency_s: float = 0.0):
        self.window_s = window_s
        self.n_bins = n_bins
        self.fixed_latency_s = fixed_latency_s
        self.reset()

    def reset(self):
        """Forget everything, e.g. after an MCU restart."""
        self._unwrap = Unwrapper()
        self._pts: deque[tuple[float, float]] = deque()   # (mcu_s, host - mcu_s)
        self._fit: tuple[float, float] | None = None       # offset = a + b * mcu_s

    def update(self, mcu_us: int, host_arrival_s: float) -> None:
        mcu_s = self._unwrap.unwrap(mcu_us) / 1e6
        self._pts.append((mcu_s, host_arrival_s - self.fixed_latency_s - mcu_s))
        while self._pts and mcu_s - self._pts[0][0] > self.window_s:
            self._pts.popleft()
        self._fit = None

    def _solve(self) -> tuple[float, float]:
        if self._fit is not None:
            return self._fit
        if not self._pts:
            raise RuntimeError("clock not synchronised yet")
        pts = np.asarray(self._pts)
        t, off = pts[:, 0], pts[:, 1]
        span = t[-1] - t[0]
        if span <= 0 or len(pts) < 2 * self.n_bins:
            self._fit = (float(off.min()), 0.0)
            return self._fit
        bins = np.minimum(((t - t[0]) / span * self.n_bins).astype(int), self.n_bins - 1)
        a, b = float(off.min()), 0.0
        for _ in range(2):
            resid = off - (a + b * t)
            idx = [np.flatnonzero(bins == k)[np.argmin(resid[bins == k])]
                   for k in range(self.n_bins) if np.any(bins == k)]
            if len(idx) < 2:
                break
            b, a = np.polyfit(t[idx], off[idx], 1)
            # Guard against the fit drifting above any point (envelope must be a lower bound).
            a += min(0.0, float(np.min(off - (a + b * t))))
        self._fit = (float(a), float(b))
        return self._fit

    def to_host(self, mcu_us: int) -> float:
        a, b = self._solve()
        mcu_s = self._unwrap.unwrap(mcu_us, commit=False) / 1e6
        return mcu_s + a + b * mcu_s

    def to_host_array(self, mcu_us: np.ndarray) -> np.ndarray:
        """Map an array of times; values are relative to the first element's unwrap."""
        mcu_us = np.asarray(mcu_us, dtype=np.int64)
        if len(mcu_us) == 0:
            return np.empty(0)
        base_raw = int(mcu_us[0])
        base = self._unwrap.unwrap(base_raw % WRAP, commit=False)
        a, b = self._solve()
        mcu_s = (base + (mcu_us - base_raw)) / 1e6
        return mcu_s + a + b * mcu_s
