"""Tare + per-channel gain calibration (§9.5).

Per channel i: F_i = sign_i * g_i * (c_i - z_i), with z_i the tare (counts) and g_i the
gain (N/count). Gains are solved per plate by least squares from a known mass placed at
several spots: for placement k, m * G = sum_i g_i * sign_i * (c_ik - z_i).
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

from .config import CHANNEL_IDS, N_CH, Config

G = 9.80665

# Uncalibrated placeholder: a 50 kg cell at ~1 mV/V full scale, gain 128, ratiometric
# 24-bit ADC -> 1e-3 * 128 * 2**23 counts at 50 kg * G. Only good to ~20 %; calibrate.
NOMINAL_GAIN_N_PER_COUNT = 50 * G / (1e-3 * 128 * 2**23)

MIN_PLACEMENTS = 4


class CalibrationError(ValueError):
    pass


@dataclass
class Calibration:
    tares: list[float]
    gains: list[float]
    created: str | None = None                 # ISO timestamp; None = never calibrated
    mass_kg: float | None = None
    residuals_n: dict[str, list[float]] = field(default_factory=dict)

    @classmethod
    def default(cls) -> "Calibration":
        return cls(tares=[0.0] * N_CH, gains=[NOMINAL_GAIN_N_PER_COUNT] * N_CH)

    @property
    def is_calibrated(self) -> bool:
        return self.created is not None


def solve_plate_gains(delta_counts: np.ndarray, mass_kg: float) -> tuple[np.ndarray, np.ndarray]:
    """Least-squares gains for one plate.

    delta_counts: (k, 4) sign-corrected counts above tare, one row per placement.
    Returns (gains (4,), residuals_n (k,)).
    """
    a = np.asarray(delta_counts, dtype=float)
    if a.ndim != 2 or a.shape[1] != 4 or a.shape[0] < MIN_PLACEMENTS:
        raise CalibrationError(f"need >= {MIN_PLACEMENTS} placements of 4 channels, got {a.shape}")
    b = np.full(len(a), mass_kg * G)
    gains, *_ = np.linalg.lstsq(a, b, rcond=None)
    return gains, a @ gains - b


def placement_spots(cfg: Config, plate: str,
                    inboard_mm: float = 40.0) -> list[tuple[str, tuple[float, float]]]:
    """Centre of the plate, then a spot `inboard_mm` in from each cell (x and y)."""
    idx = cfg.plate_channels(plate)
    pos = np.asarray(cfg.positions())[idx]
    centre = pos.mean(axis=0)
    spots = [("centre", (float(centre[0]), float(centre[1])))]
    for i, p in zip(idx, pos):
        xy = p - np.sign(p - centre) * inboard_mm
        spots.append((CHANNEL_IDS[i], (float(xy[0]), float(xy[1]))))
    return spots


class CalibrationSession:
    """Accumulates wizard captures (mean counts per step) and solves."""

    def __init__(self, cfg: Config, mass_kg: float):
        self.cfg = cfg
        self.mass_kg = mass_kg
        self.zero: np.ndarray | None = None
        self._placements: dict[str, dict[str, np.ndarray]] = {"L": {}, "R": {}}

    def set_zero(self, mean_counts) -> None:
        self.zero = np.asarray(mean_counts, dtype=float)

    def add_placement(self, plate: str, spot: str, mean_counts) -> None:
        self._placements[plate][spot] = np.asarray(mean_counts, dtype=float)

    def captured(self, plate: str) -> list[str]:
        return list(self._placements[plate])

    def solve(self, now: str | None = None) -> Calibration:
        if self.zero is None:
            raise CalibrationError("capture zero (plates empty) first")
        signs = np.asarray(self.cfg.signs, dtype=float)
        gains = np.zeros(N_CH)
        residuals: dict[str, list[float]] = {}
        for plate in ("L", "R"):
            caps = self._placements[plate]
            if len(caps) < MIN_PLACEMENTS:
                raise CalibrationError(
                    f"plate {plate}: need {MIN_PLACEMENTS} placements, have {len(caps)}")
            idx = self.cfg.plate_channels(plate)
            delta = np.array([(c[idx] - self.zero[idx]) * signs[idx] for c in caps.values()])
            g, r = solve_plate_gains(delta, self.mass_kg)
            gains[idx] = g
            residuals[plate] = [float(v) for v in r]
        return Calibration(
            tares=[float(v) for v in self.zero],
            gains=[float(v) for v in gains],
            created=now or datetime.now().isoformat(timespec="seconds"),
            mass_kg=self.mass_kg,
            residuals_n=residuals,
        )


def save_calibration(cal: Calibration, path: str | Path) -> None:
    """Write `path` and a timestamped copy next to it, so history is kept."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dataclasses.asdict(cal), indent=2)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    if cal.created:
        stamp = datetime.fromisoformat(cal.created).strftime("%Y%m%d-%H%M")
        (path.parent / f"{path.stem}-{stamp}.json").write_text(text, encoding="utf-8")


def load_calibration(path: str | Path) -> Calibration:
    path = Path(path)
    if not path.exists():
        return Calibration.default()
    return Calibration(**json.loads(path.read_text(encoding="utf-8")))
