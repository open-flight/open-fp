import json

import numpy as np
import pytest

from open_fp.calibration import Calibration
from open_fp.config import Config
from open_fp.pipeline import Pipeline
from open_fp.swing import SwingDetector, lateral_speed
from synth import RATE_HZ, Scenario, generate, to_batches

CAL = Calibration(tares=[500.0 * i for i in range(8)], gains=[4.5e-4] * 8, created="x")
HOST0 = 1000.0


def run(cfg, scenarios, seed=0, detector=None, on_batch=None):
    """Generate a session, run it through Pipeline + SwingDetector. Returns (data, det, events, states)."""
    data = generate(scenarios, cfg, cal=CAL, seed=seed)
    pipe = Pipeline(cfg, CAL)
    det = detector or SwingDetector(cfg, now_fn=lambda: 1_790_000_000.0)
    events, states, host = [], [], HOST0
    for b in to_batches(data.counts):
        host += b.n / RATE_HZ
        s = pipe.process(b, host)
        for e in det.update(s):
            events.append(e)
        states.append(det.state)
        if on_batch:
            events += on_batch(det, host) or []
    return data, det, events, states


def completed(events):
    return [e.swing for e in events if e.kind == "swing_complete"]


def swing_session(n=1, seed=0):
    rng = np.random.default_rng(seed)
    out = [Scenario("empty", 1.0), Scenario("step_on", 1.0)]
    for _ in range(n):
        out += [Scenario("swing"), Scenario("stance", float(rng.uniform(2.0, 3.0)))]
    return out


def host_time(data_t):
    """Host time of a session time (first sample arrives with the first batch)."""
    return HOST0 + 10 / RATE_HZ + data_t - 9 / RATE_HZ


# -- helpers ---------------------------------------------------------------

def test_lateral_speed_of_constant_velocity():
    t = np.arange(100) / RATE_HZ
    v = lateral_speed(t, 120.0 * t)
    np.testing.assert_allclose(v[20:], 120.0, rtol=1e-6)


# -- end to end on synthetic swings ---------------------------------------

def test_single_swing_is_captured_with_correct_events():
    cfg = Config()
    data, det, events, states = run(cfg, swing_session(1), seed=1)
    swings = completed(events)
    assert len(swings) == 1
    sw, truth = swings[0], data.truth["swings"][0]
    ev = {k: sw.t0_host + v for k, v in sw.events.items() if v is not None}
    for name, tol in [("motion_start", 0.15), ("max_trail", 0.05), ("transition", 0.02), ("max_lead", 0.06)]:
        assert ev[name] == pytest.approx(host_time(truth[name]), abs=tol), name
    assert sw.events["impact"] is None
    for s in ("address", "armed", "swinging", "review"):
        assert s in states


def test_metrics_match_synthetic_truth():
    cfg = Config()
    data, det, events, _ = run(cfg, swing_session(1), seed=1)
    m = completed(events)[0].metrics
    assert m["lead_pct_address"] == pytest.approx(55, abs=1)
    assert m["lead_pct_max_trail"] == pytest.approx(30, abs=1.5)
    assert m["lead_pct_max_lead"] == pytest.approx(88, abs=1.5)
    assert m["lead_pct_impact"] is None
    assert m["peak_fz_pct_bw"]["lead"] == pytest.approx(140, abs=10)
    assert m["time_max_trail_to_transition_ms"] > 0
    assert m["time_transition_to_max_lead_ms"] > 0
    assert m["peak_shift_rate_pct_s"] > 100
    assert m["lateral_cop_range_mm"] == pytest.approx(0.58 * cfg.plate_spacing_mm, rel=0.1)
    assert m["peak_lateral_speed_mm_s"] > 300
    assert m["lead_cop_y_max_lead_mm"] == pytest.approx(-30, abs=5)   # lead foot rolls to heel
    assert m["trail_cop_y_max_lead_mm"] == pytest.approx(30, abs=5)


def test_bw_captured_at_address():
    cfg = Config()
    data, det, events, _ = run(cfg, swing_session(1), seed=1)
    assert completed(events)[0].bw_n == pytest.approx(data.truth["bw_n"], rel=0.01)


def test_bw_override_is_used():
    cfg = Config(bw_override_n=900.0)
    _, _, events, _ = run(cfg, swing_session(1), seed=1)
    assert completed(events)[0].bw_n == 900.0


def test_twenty_swings_none_missed():
    cfg = Config()
    data, _, events, _ = run(cfg, swing_session(20, seed=5), seed=5)
    swings = completed(events)
    assert len(swings) == 20
    for sw, truth in zip(swings, data.truth["swings"]):
        assert sw.t0_host + sw.events["transition"] == pytest.approx(host_time(truth["transition"]), abs=0.02)


def test_left_handed_swing_is_captured():
    cfg = Config(golfer="LH")
    _, _, events, _ = run(cfg, swing_session(1), seed=2)
    swings = completed(events)
    assert len(swings) == 1
    assert swings[0].metrics["lead_pct_max_lead"] == pytest.approx(88, abs=1.5)


# -- false trigger rejection ----------------------------------------------

def test_no_trigger_standing_still_two_minutes():
    cfg = Config()
    _, det, events, _ = run(cfg, [Scenario("step_on"), Scenario("stance", 120.0)], seed=3)
    assert completed(events) == []
    assert det.state == "armed"


@pytest.mark.parametrize("kind", ["sway", "shuffle", "press"])
def test_no_trigger_on_sway_shuffle_or_press(kind):
    cfg = Config()
    _, _, events, _ = run(cfg, [Scenario("step_on"), Scenario("stance", 2.0), Scenario(kind),
                                Scenario("stance", 2.0)], seed=4)
    assert completed(events) == []


def test_empty_plates_stay_idle():
    cfg = Config()
    _, det, events, states = run(cfg, [Scenario("empty", 5.0)])
    assert set(states) == {"idle"} and events == []


# -- manual control and external impact -----------------------------------

def test_manual_trigger_when_armed_captures_swing():
    cfg = Config()
    fired = []

    def on_batch(det, host):
        if det.state == "armed" and not fired and host > HOST0 + 3.5:
            fired.append(host)
            assert det.trigger() is True

    _, _, events, _ = run(cfg, [Scenario("step_on"), Scenario("stance", 6.0)], on_batch=on_batch)
    assert len(completed(events)) == 1


def test_manual_trigger_ignored_when_idle():
    det = SwingDetector(Config())
    assert det.trigger() is False


def test_shot_event_during_swing_labels_impact():
    cfg = Config()
    data = generate(swing_session(1), cfg, cal=CAL, seed=1)
    t_imp = host_time(data.truth["swings"][0]["impact"])
    sent = []

    def on_batch(det, host):
        if not sent and host >= t_imp + 0.02:     # shot message arrives ~20 ms late
            sent.append(True)
            return det.mark_impact(t_imp)

    _, _, events, _ = run(cfg, swing_session(1), seed=1, on_batch=on_batch)
    sw = completed(events)[0]
    assert sw.t0_host + sw.events["impact"] == pytest.approx(t_imp, abs=0.006)
    assert sw.impact_source == "shot"
    assert sw.metrics["lead_pct_impact"] is not None
    assert sw.metrics["peak_lead_fz_rel_impact_ms"] is not None


def test_late_shot_event_updates_last_swing():
    cfg = Config()
    data, det, events, _ = run(cfg, swing_session(1), seed=1)
    t_imp = host_time(data.truth["swings"][0]["impact"])
    upd = det.mark_impact(t_imp)
    assert [e.kind for e in upd] == ["swing_updated"]
    assert upd[0].swing.events["impact"] is not None
    assert upd[0].swing.id == completed(events)[0].id


def test_shot_event_outside_any_swing_is_ignored():
    det = SwingDetector(Config())
    assert det.mark_impact(5.0) == []


# -- output ---------------------------------------------------------------

def test_summary_and_arrays_are_json_safe():
    cfg = Config()
    _, _, events, _ = run(cfg, swing_session(1), seed=1)
    sw = completed(events)[0]
    summary = sw.summary()
    json.dumps(summary, allow_nan=False)
    assert summary["id"] == sw.id and "metrics" in summary and len(summary["path"]) <= 60
    full = sw.to_dict()
    json.dumps(full, allow_nan=False)
    n = len(full["arrays"]["t"])
    assert n == len(full["arrays"]["lead_pct"]) == len(full["arrays"]["forces"])
    assert full["arrays"]["t"][0] == 0.0


def test_capture_window_spans_pre_roll_to_post_trigger():
    cfg = Config()
    _, _, events, _ = run(cfg, swing_session(1), seed=1)
    sw = completed(events)[0]
    t = sw.arrays["t"]
    assert sw.events["motion_start"] >= cfg.swing.pre_roll_s - 0.2
    assert t[-1] <= cfg.swing.max_capture_s
    assert t[-1] - sw.events["trigger"] == pytest.approx(cfg.swing.post_trigger_s, abs=0.01)
