"""Synthetic 8-channel force plate data for the simulator and tests (§11.5)."""
from __future__ import annotations

import numpy as np

from open_fp.config import N_CH, Config


def corner_forces(cfg: Config, plate: str, xy, total_n: float) -> np.ndarray:
    """Split a point load on one plate over its 4 cells so CoP lands exactly at xy.

    Bilinear weights over the rectangle spanned by the cells. Returns (8,) forces in N.
    """
    idx = cfg.plate_channels(plate)
    pos = np.asarray(cfg.positions())[idx]
    x0, x1 = pos[:, 0].min(), pos[:, 0].max()
    y0, y1 = pos[:, 1].min(), pos[:, 1].max()
    u = (xy[0] - x0) / (x1 - x0)
    v = (xy[1] - y0) / (y1 - y0)
    wx = np.where(np.isclose(pos[:, 0], x1), u, 1 - u)
    wy = np.where(np.isclose(pos[:, 1], y1), v, 1 - v)
    out = np.zeros(N_CH)
    out[idx] = total_n * wx * wy
    return out
