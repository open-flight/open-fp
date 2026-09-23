import numpy as np
import pytest

from open_fp.calibration import Calibration
from open_fp.config import Config
from open_fp.pipeline import Pipeline, Samples
from synth import RATE_HZ, Scenario, corner_forces, generate, to_batches


@pytest.mark.parametrize("plate", ["L", "R"])
def test_corner_forces_reproduce_total_and_cop(plate):
    cfg = Config()
    idx = cfg.plate_channels(plate)
    pos = np.asarray(cfg.positions())[idx]
    for xy in [pos.mean(axis=0), pos[0], pos.mean(axis=0) + [30, -50]]:
        f = corner_forces(cfg, plate, xy, 700.0)
        assert f.shape == (8,)
        assert f.sum() == pytest.approx(700.0)
        assert f[idx] @ pos / f.sum() == pytest.approx(xy)
        other = [i for i in range(8) if i not in idx]
        assert np.all(f[other] == 0)


# --- scenario generator ---------------------------------------------------

CAL = Calibration(tares=[1000.0 * i for i in range(8)], gains=[4.5e-4] * 8, created="x")


def _run(cfg, data):
    pipe = Pipeline(cfg, CAL)
    host = 50.0
    parts = []
    for b in to_batches(data.counts):
        host += b.n / RATE_HZ
        parts.append(pipe.process(b, host))
    return Samples.concat(parts)


def test_swing_truth_shape():
    d = generate([Scenario("swing")], Config(), seed=1, noise_counts=0, drift_counts_per_s=0)
    tr = d.truth["swings"][0]
    lead = d.truth["lead_pct"]
    assert np.nanmean(lead[: int(1.0 * RATE_HZ)]) == pytest.approx(55, abs=1)
    assert np.nanmin(lead) == pytest.approx(30, abs=2)
    assert np.nanmax(lead) == pytest.approx(88, abs=3)
    assert tr["motion_start"] < tr["max_trail"] < tr["transition"] < tr["impact"] < tr["max_lead"]
    lead_fz = d.forces[:, :4].sum(axis=1)  # RH: plate L is lead
    assert lead_fz.max() / d.truth["bw_n"] == pytest.approx(1.4, abs=0.1)


def test_generator_is_deterministic_per_seed():
    a = generate([Scenario("swing")], Config(), seed=3)
    b = generate([Scenario("swing")], Config(), seed=3)
    c = generate([Scenario("swing")], Config(), seed=4)
    np.testing.assert_array_equal(a.counts, b.counts)
    assert not np.array_equal(a.counts, c.counts)


def test_pipeline_recovers_truth_from_generated_counts():
    cfg = Config()
    d = generate([Scenario("stance", 1.0), Scenario("swing")], cfg, cal=CAL, seed=2,
                 noise_counts=0, drift_counts_per_s=0)
    s = _run(cfg, d)
    ok = ~np.isnan(d.truth["lead_pct"])
    np.testing.assert_allclose(s.lead_pct[ok], d.truth["lead_pct"][ok], atol=0.2)
    np.testing.assert_allclose(s.fz_total, d.forces.sum(axis=1), rtol=1e-3, atol=1.0)


def test_lh_golfer_puts_lead_on_plate_r():
    cfg = Config(golfer="LH")
    d = generate([Scenario("swing")], cfg, seed=1, noise_counts=0, drift_counts_per_s=0)
    t_ml = d.truth["swings"][0]["max_lead"]
    i = int(t_ml * RATE_HZ)
    assert d.forces[i, 4:].sum() > 0.8 * d.forces[i].sum()


def test_empty_scenario_has_no_load():
    d = generate([Scenario("empty", 2.0)], Config(), seed=0)
    assert np.all(d.forces == 0)
    assert len(d.counts) == int(2.0 * RATE_HZ)


def test_to_batches_groups_frames_with_sequence_and_time():
    counts = np.zeros((25, 8), dtype=np.int32)
    bs = to_batches(counts, seq0=7, t0_us=2**32 - 10_000)
    assert [b.n for b in bs] == [10, 10, 5]
    assert [b.seq for b in bs] == [7, 8, 9]
    assert bs[1].t_first_us == (2**32 - 10_000 + 50_000) % 2**32
