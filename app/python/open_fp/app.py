"""Application core shared by the board (main.py) and the simulator (tools/sim).

Framework-free: the web layer calls these methods for REST routes (§9.8) and emits
whatever `tick()` returns as Socket.IO messages. All state is guarded by one lock,
because Bridge callbacks, the main loop and HTTP handlers run on different threads.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from pathlib import Path

import numpy as np

from .calibration import CalibrationSession, load_calibration, placement_spots, save_calibration
from .config import CHANNEL_IDS, load_config, save_config
from .pipeline import Pipeline
from .protocol import ProtocolError, decode_batch
from .store import SwingStore
from .swing import SwingDetector

LIVE_PERIOD_S = 1 / 30
STATUS_PERIOD_S = 1.0
RATE_WINDOW_S = 2.0


class Core:
    def __init__(self, data_dir: str | Path, now_fn=time.time, monotonic_fn=time.monotonic,
                 clock_latency_s: float = 0.0):
        self.data = Path(data_dir)
        self.data.mkdir(parents=True, exist_ok=True)
        self.now_fn, self.monotonic_fn = now_fn, monotonic_fn
        self.cfg = load_config(self.data / "config.json")
        self.pipe = Pipeline(self.cfg, load_calibration(self.data / "calibration.json"),
                             clock_latency_s=clock_latency_s)
        self.detector = SwingDetector(self.cfg, now_fn=now_fn)
        self.store = SwingStore(self.data / "swings")
        self.mcu_status: dict | None = None      # last fp_status reply, set by main.py
        self._lock = threading.RLock()
        self._outbox: list[tuple[str, dict]] = []
        self._last_live = -np.inf
        self._last_status = -np.inf
        self._arrivals: deque[tuple[float, int]] = deque()
        self._calib: CalibrationSession | None = None
        self._calib_result = None

    # -- data path -------------------------------------------------------------

    def on_payload(self, payload, arrival_s: float) -> None:
        with self._lock:
            try:
                batch = decode_batch(payload)
            except (ProtocolError, ValueError, TypeError):
                self.pipe.stats.decode_errors += 1
                return
            samples = self.pipe.process(batch, arrival_s)
            self._arrivals.append((arrival_s, batch.n))
            while self._arrivals and arrival_s - self._arrivals[0][0] > RATE_WINDOW_S:
                self._arrivals.popleft()
            for ev in self.detector.update(samples):
                self._handle_event(ev)
            self.pipe.ui_buffer.extend(samples)

    def _handle_event(self, ev) -> None:
        if ev.kind in ("swing_complete", "swing_updated"):
            self.store.save(ev.swing)
            self._outbox.append(("swing" if ev.kind == "swing_complete" else "swing_updated", ev.swing.summary()))

    def tick(self, now_s: float) -> list[tuple[str, dict]]:
        """Messages to push to browsers now: queued events, `live` (30 Hz), `status` (1 Hz)."""
        with self._lock:
            out, self._outbox = self._outbox, []
            if now_s - self._last_live >= LIVE_PERIOD_S:
                self._last_live = now_s
                out.append(("live", self.pipe.ui_buffer.drain(
                    state=self.detector.state, bw_n=self.detector.bw_n,
                    lead_plate=self.cfg.lead_plate, golfer=self.cfg.golfer)))
            if now_s - self._last_status >= STATUS_PERIOD_S:
                self._last_status = now_s
                out.append(("status", self.status()))
            return out

    # -- REST ------------------------------------------------------------------

    def status(self) -> dict:
        with self._lock:
            st = self.pipe.status()
            rows = self.pipe.recent_counts(1.0)
            chans = []
            for i, ch in enumerate(CHANNEL_IDS):
                if len(rows):
                    mean, std = float(rows[:, i].mean()), float(rows[:, i].std())
                    force = self.cfg.signs[i] * self.pipe.cal.gains[i] * (mean - self.pipe.tares[i])
                else:
                    mean = std = force = None
                chans.append({"id": ch, "counts": _r(mean, 0), "noise_counts": _r(std, 1),
                              "tare": _r(self.pipe.tares[i], 0), "force_n": _r(force, 1)})
            rate = None
            if len(self._arrivals) > 1:
                span = self._arrivals[-1][0] - self._arrivals[0][0]
                rate = sum(n for _, n in list(self._arrivals)[1:]) / span if span > 0 else None
            return {**st, "state": self.detector.state, "bw_n": _r(self.detector.bw_n, 1),
                    "golfer": self.cfg.golfer, "rate_hz": _r(rate, 1), "channels": chans,
                    "mcu": self.mcu_status}

    def zero(self) -> dict:
        with self._lock:
            return {"ok": self.pipe.zero_now()["ok"]}

    def get_config(self) -> dict:
        with self._lock:
            return self.cfg.to_dict()

    def put_config(self, changes: dict) -> dict:
        with self._lock:
            new = self.cfg.updated(changes)
            save_config(new, self.data / "config.json")
            self.cfg = new
            self.pipe.set_config(new)
            self.detector.set_config(new)
            return new.to_dict()

    def record_arm(self) -> dict:
        with self._lock:
            return {"ok": self.detector.arm(), "state": self.detector.state}

    def record_trigger(self) -> dict:
        with self._lock:
            return {"ok": self.detector.trigger(), "state": self.detector.state}

    def shot_event(self, t_unix_ms: float) -> dict:
        """External impact (e.g. OpenFlight launch monitor), Unix ms on an NTP-synced clock."""
        with self._lock:
            t_mono = t_unix_ms / 1000 - (self.now_fn() - self.monotonic_fn())
            events = self.detector.mark_impact(t_mono, source="shot")
            for ev in events:
                self._handle_event(ev)
            labelled = events[0].swing.id if events else None
            return {"ok": True, "labelled": labelled, "pending": self.detector.state == "swinging"}

    # swings

    def swings(self) -> list[dict]:
        return self.store.list()

    def swing(self, swing_id: str) -> dict:
        return self.store.get(swing_id)

    def swing_csv(self, swing_id: str) -> str:
        return self.store.csv(swing_id)

    def delete_swing(self, swing_id: str) -> dict:
        return {"ok": self.store.delete(swing_id)}

    # calibration wizard (§9.5)

    def calib_start(self, mass_kg: float) -> dict:
        with self._lock:
            self._calib = CalibrationSession(self.cfg, float(mass_kg))
            self._calib_result = None
            steps = [{"kind": "zero"}]
            for plate in ("L", "R"):
                for name, xy in placement_spots(self.cfg, plate):
                    steps.append({"kind": "place", "plate": plate, "spot": name, "xy": [xy[0], xy[1]]})
            return {"mass_kg": float(mass_kg), "steps": steps}

    def calib_capture(self, step: dict, seconds: float = 2.0) -> dict:
        with self._lock:
            if self._calib is None:
                raise RuntimeError("start calibration first")
            mean = self.pipe.mean_counts(seconds)
            if step.get("kind") == "zero":
                self._calib.set_zero(mean)
            else:
                self._calib.add_placement(step["plate"], step["spot"], mean)
            return {"ok": True, "captured": {p: self._calib.captured(p) for p in ("L", "R")}}

    def calib_solve(self) -> dict:
        with self._lock:
            if self._calib is None:
                raise RuntimeError("start calibration first")
            self._calib_result = self._calib.solve()
            c = self._calib_result
            return {"gains": c.gains, "tares": c.tares, "residuals_n": c.residuals_n}

    def calib_save(self) -> dict:
        with self._lock:
            if self._calib_result is None:
                raise RuntimeError("solve calibration first")
            save_calibration(self._calib_result, self.data / "calibration.json")
            self.pipe.set_calibration(self._calib_result)
            self._calib = self._calib_result = None
            return {"ok": True}


def _r(v, digits):
    return None if v is None else round(float(v), digits)
