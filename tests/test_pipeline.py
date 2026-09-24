import json

import numpy as np
import pytest

from open_fp.calibration import Calibration
from open_fp.config import Config
from open_fp.pipeline import Pipeline, Samples
from open_fp.protocol import FLAG_SATURATION, Batch
from synth import corner_forces

GAINS = [4.1e-4, 4.6e-4, 5.0e-4, 4.4e-4, 4.8e-4, 4.2e-4, 4.5e-4, 4.9e-4]
TARES = [1200.0, -3400.0, 560.0, 88000.0, -12000.0, 4000.0, 0.0, 250.0]
CAL = Calibration(tares=TARES, gains=GAINS, created="2026-09-23T12:00:00", mass_kg=20.0)


def counts_for(cfg, forces_n, tares=TARES):
    """Counts (n, 8) that produce the given forces (n, 8) under CAL and cfg.signs."""
    f = np.atleast_2d(forces_n)
    return np.round(np.asarray(tares) + np.asarray(cfg.signs) * f / np.asarray(GAINS)).astype(np.int32)


class Feeder:
    """Feeds batches of 10 frames at 200 Hz with a steady clock."""

    def __init__(self, pipe):
        self.pipe, self.seq, self.t_us, self.host = pipe, 0, 0, 100.0

    def feed(self, counts, flags=0, seq=None):
        counts = np.atleast_2d(counts)
        out = []
        for i in range(0, len(counts), 10):
            chunk = counts[i:i + 10]
            b = Batch(seq if seq is not None else self.seq, self.t_us % 2**32, 5000, flags, chunk)
            self.host += len(chunk) * 0.005
            out.append(self.pipe.process(b, self.host))
            self.seq += 1
            self.t_us += len(chunk) * 5000
        return Samples.concat(out)


def load(cfg, plate_loads):
    """Forces (8,) for a dict plate -> (xy, N)."""
    return sum(corner_forces(cfg, p, xy, n) for p, (xy, n) in plate_loads.items())


@pytest.mark.parametrize("ch", range(8))
def test_point_load_on_each_cell_gives_its_position(ch):
    cfg = Config()
    pipe = Pipeline(cfg, CAL)
    f = np.zeros(8)
    f[ch] = 500.0
    s = Feeder(pipe).feed(counts_for(cfg, np.tile(f, (10, 1))))
    plate = "L" if ch < 4 else "R"
    np.testing.assert_allclose(s.fz[plate], 500.0, rtol=1e-4)
    np.testing.assert_allclose(s.cop[plate][-1], cfg.positions()[ch], atol=0.5)


@pytest.mark.parametrize("plate", ["L", "R"])
def test_centre_load(plate):
    cfg = Config()
    pipe = Pipeline(cfg, CAL)
    centre = np.asarray(cfg.positions())[cfg.plate_channels(plate)].mean(axis=0)
    s = Feeder(pipe).feed(counts_for(cfg, np.tile(load(cfg, {plate: (centre, 400.0)}), (10, 1))))
    np.testing.assert_allclose(s.cop[plate][-1], centre, atol=0.5)
    np.testing.assert_allclose(s.cop["C"][-1], centre, atol=0.5)


def test_cop_is_nan_below_min_force():
    cfg = Config()
    pipe = Pipeline(cfg, CAL)
    f = load(cfg, {"L": ((-184.8, 0), 10.0), "R": ((184.8, 0), 600.0)})
    s = Feeder(pipe).feed(counts_for(cfg, np.tile(f, (10, 1))))
    assert np.all(np.isnan(s.cop["L"]))
    assert not np.any(np.isnan(s.cop["R"]))


@pytest.mark.parametrize("golfer, expected_lead", [("RH", 60.0), ("LH", 40.0)])
def test_lead_pct_follows_handedness(golfer, expected_lead):
    cfg = Config(golfer=golfer)
    pipe = Pipeline(cfg, CAL)
    f = load(cfg, {"L": ((-184.8, 0), 480.0), "R": ((184.8, 0), 320.0)})
    s = Feeder(pipe).feed(counts_for(cfg, np.tile(f, (10, 1))))
    np.testing.assert_allclose(s.lead_pct, expected_lead, atol=0.05)


def test_combined_cop_is_force_weighted():
    cfg = Config()
    pipe = Pipeline(cfg, CAL)
    f = load(cfg, {"L": ((-200, 10), 600.0), "R": ((150, 50), 200.0)})
    s = Feeder(pipe).feed(counts_for(cfg, np.tile(f, (10, 1))))
    expected = (600 * np.array([-200, 10]) + 200 * np.array([150, 50])) / 800
    np.testing.assert_allclose(s.cop["C"][-1], expected, atol=0.5)
    np.testing.assert_allclose(s.fz_total, 800.0, rtol=1e-4)


def test_channel_signs_are_applied():
    cfg = Config(signs=[1, -1, 1, 1, 1, 1, 1, -1])
    pipe = Pipeline(cfg, CAL)
    f = load(cfg, {"L": ((-184.8, 0), 400.0), "R": ((184.8, 0), 400.0)})
    s = Feeder(pipe).feed(counts_for(cfg, np.tile(f, (10, 1))))
    np.testing.assert_allclose(s.forces[-1], f, atol=0.1)


def test_sample_times_are_5ms_apart_and_increasing():
    cfg = Config()
    pipe = Pipeline(cfg, CAL)
    s = Feeder(pipe).feed(counts_for(cfg, np.zeros((50, 8))))
    np.testing.assert_allclose(np.diff(s.t), 0.005, atol=1e-6)


def test_zero_now_uses_recent_average():
    cfg = Config()
    pipe = Pipeline(cfg, CAL)
    offset = np.array([50, -80, 30, 0, 10, 20, -30, 40], dtype=float)
    Feeder(pipe).feed(counts_for(cfg, np.zeros((400, 8)), tares=np.asarray(TARES) + offset))
    pipe.zero_now()
    np.testing.assert_allclose(pipe.tares, np.asarray(TARES) + offset, atol=1)


def test_auto_zero_tracks_drift_when_empty():
    cfg = Config()
    pipe = Pipeline(cfg, CAL)
    drift = np.array([2000, 0, 0, 0, 0, 0, 0, 0], dtype=float)  # ~8 N on L1
    Feeder(pipe).feed(counts_for(cfg, np.zeros((200 * 25, 8)), tares=np.asarray(TARES) + drift))
    assert pipe.tares[0] == pytest.approx(TARES[0] + 2000, abs=50)


def test_auto_zero_does_not_run_while_loaded():
    cfg = Config()
    pipe = Pipeline(cfg, CAL)
    f = load(cfg, {"L": ((-184.8, 0), 400.0), "R": ((184.8, 0), 400.0)})
    Feeder(pipe).feed(counts_for(cfg, np.tile(f, (200 * 10, 1))))
    np.testing.assert_allclose(pipe.tares, TARES)


def test_status_reports_gaps_flags_and_calibration():
    cfg = Config()
    pipe = Pipeline(cfg, Calibration.default())
    fd = Feeder(pipe)
    fd.feed(counts_for(cfg, np.zeros((10, 8))))
    fd.seq += 3
    fd.feed(counts_for(cfg, np.zeros((10, 8))), flags=FLAG_SATURATION)
    st = pipe.status()
    assert st["seq_gaps"] == 1 and st["seq_missing"] == 3
    assert st["saturation"] is True
    assert st["calibrated"] is False
    assert st["batches"] == 2
    json.dumps(st)


def test_status_warns_on_tare_drift():
    cfg = Config()
    pipe = Pipeline(cfg, CAL)
    pipe.tares[2] += 0.03 * 2**23
    assert pipe.status()["tare_drift_channels"] == ["L3"]


def test_ui_buffer_drain_is_json_safe_and_empties():
    cfg = Config()
    pipe = Pipeline(cfg, CAL)
    f = load(cfg, {"L": ((-184.8, 0), 10.0), "R": ((184.8, 0), 600.0)})
    s = Feeder(pipe).feed(counts_for(cfg, np.tile(f, (20, 1))))
    pipe.ui_buffer.extend(s)
    msg = pipe.ui_buffer.drain(state="idle", bw_n=None)
    text = json.dumps(msg, allow_nan=False)
    assert len(msg["t"]) == 20
    assert msg["cop"]["L"][0] is None
    assert set(msg["fz"]) == {"L", "R"} and msg["state"] == "idle"
    assert len(msg["forces"]) == 20 and len(msg["forces"][0]) == 8
    assert "NaN" not in text
    assert pipe.ui_buffer.drain()["t"] == []
