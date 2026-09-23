import json

import numpy as np
import pytest

from open_fp.calibration import (
    G,
    NOMINAL_GAIN_N_PER_COUNT,
    Calibration,
    CalibrationError,
    CalibrationSession,
    load_calibration,
    placement_spots,
    save_calibration,
    solve_plate_gains,
)
from open_fp.config import Config

TRUE_GAINS = np.array([4.1e-4, 4.6e-4, 5.0e-4, 4.4e-4, 4.8e-4, 4.2e-4, 4.5e-4, 4.9e-4])
TARES = np.array([1200, -3400, 560, 88000, -12000, 4000, 0, 250], dtype=float)


def _corner_forces(cfg, plate, xy, total_n):
    """Bilinear split of a point load over a plate's 4 cells (exact CoP)."""
    idx = cfg.plate_channels(plate)
    pos = np.asarray(cfg.positions())[idx]
    x0, x1 = pos[:, 0].min(), pos[:, 0].max()
    y0, y1 = pos[:, 1].min(), pos[:, 1].max()
    u = (xy[0] - x0) / (x1 - x0)
    v = (xy[1] - y0) / (y1 - y0)
    wx = np.where(np.isclose(pos[:, 0], x1), u, 1 - u)
    wy = np.where(np.isclose(pos[:, 1], y1), v, 1 - v)
    return idx, total_n * wx * wy


def _counts_for_load(cfg, plate, xy, mass_kg, signs, rng=None, noise=0.0):
    f = np.zeros(8)
    idx, fc = _corner_forces(cfg, plate, xy, mass_kg * G)
    f[idx] = fc
    counts = TARES + np.asarray(signs) * f / TRUE_GAINS
    if rng is not None:
        counts += rng.normal(0, noise, 8)
    return counts


def test_default_is_uncalibrated_nominal():
    cal = Calibration.default()
    assert not cal.is_calibrated
    assert cal.gains == [NOMINAL_GAIN_N_PER_COUNT] * 8
    assert cal.tares == [0.0] * 8


def test_solve_recovers_exact_gains():
    g = TRUE_GAINS[:4]
    rng = np.random.default_rng(0)
    delta = rng.uniform(0, 30000, size=(5, 4))
    delta *= (20 * G) / (delta @ g)[:, None]  # each row sums to 20 kg of force
    gains, resid = solve_plate_gains(delta, 20.0)
    np.testing.assert_allclose(gains, g, rtol=1e-9)
    assert np.all(np.abs(resid) < 1e-6)


def test_solve_rejects_underdetermined():
    with pytest.raises(CalibrationError):
        solve_plate_gains(np.ones((3, 4)), 20.0)


def test_placement_spots_centre_and_inboard_of_each_cell():
    cfg = Config()
    spots = placement_spots(cfg, "L")
    assert [s[0] for s in spots] == ["centre", "L1", "L2", "L3", "L4"]
    assert spots[0][1] == pytest.approx((-184.8, 0.0))
    assert spots[1][1] == pytest.approx((-307.2 + 40, 122.4 - 40))  # L1 toe-outer, moved in


def _run_session(cfg, signs, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    s = CalibrationSession(cfg, mass_kg=20.0)
    s.set_zero(TARES + rng.normal(0, noise, 8))
    for plate in "LR":
        for name, xy in placement_spots(cfg, plate):
            s.add_placement(plate, name, _counts_for_load(cfg, plate, xy, 20.0, signs, rng, noise))
    return s.solve(now="2026-09-23T12:00:00")


def test_session_recovers_gains_from_noisy_data():
    cfg = Config()
    cal = _run_session(cfg, cfg.signs, noise=20.0)
    np.testing.assert_allclose(cal.gains, TRUE_GAINS, rtol=0.01)
    np.testing.assert_allclose(cal.tares, TARES, atol=100)
    assert cal.is_calibrated and cal.mass_kg == 20.0
    assert set(cal.residuals_n) == {"L", "R"} and len(cal.residuals_n["L"]) == 5


def test_session_respects_channel_signs():
    signs = [1, -1, 1, 1, 1, 1, -1, 1]
    cfg = Config(signs=signs)
    cal = _run_session(cfg, signs)
    np.testing.assert_allclose(cal.gains, TRUE_GAINS, rtol=1e-6)


def test_session_requires_zero_and_four_placements():
    cfg = Config()
    s = CalibrationSession(cfg, mass_kg=20.0)
    with pytest.raises(CalibrationError, match="zero"):
        s.solve()
    s.set_zero(TARES)
    for name, xy in placement_spots(cfg, "L")[:3]:
        s.add_placement("L", name, _counts_for_load(cfg, "L", xy, 20.0, cfg.signs))
    with pytest.raises(CalibrationError, match="plate L"):
        s.solve()


def test_session_recapture_replaces_placement():
    cfg = Config()
    s = CalibrationSession(cfg, mass_kg=20.0)
    s.add_placement("L", "centre", np.zeros(8))
    s.add_placement("L", "centre", np.ones(8))
    assert s.captured("L") == ["centre"]


def test_save_and_load_round_trip_with_history(tmp_path):
    path = tmp_path / "calibration.json"
    cal = _run_session(Config(), Config().signs)
    save_calibration(cal, path)
    loaded = load_calibration(path)
    assert loaded == cal
    assert (tmp_path / "calibration-20260923-1200.json").exists()
    data = json.loads(path.read_text())
    assert data["created"] == "2026-09-23T12:00:00"


def test_load_missing_gives_default(tmp_path):
    assert load_calibration(tmp_path / "none.json") == Calibration.default()
