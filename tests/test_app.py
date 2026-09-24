import json

import numpy as np
import pytest

from open_fp.app import Core
from open_fp.calibration import Calibration, G, placement_spots, save_calibration
from open_fp.config import Config
from open_fp.protocol import encode_batch
from synth import RATE_HZ, Scenario, corner_forces, generate, to_batches

CAL = Calibration(tares=[100.0 * i for i in range(8)], gains=[4.5e-4] * 8, created="2026-09-23T10:00:00")
UNIX0 = 1_790_000_000.0


class Clock:
    def __init__(self):
        self.mono = 500.0

    def monotonic(self):
        return self.mono

    def unix(self):
        return UNIX0 + self.mono


class Stream:
    """One continuous MCU stream: sequence numbers and MCU time carry across calls."""

    def __init__(self, core, clock):
        self.core, self.clock, self.seq, self.t_us = core, clock, 0, 0

    def feed(self, counts, on_batch=None):
        """Stream counts in real time; return all messages emitted by tick()."""
        msgs = []
        for b in to_batches(counts, seq0=self.seq, t0_us=self.t_us):
            self.clock.mono += b.n / RATE_HZ
            self.core.on_payload(encode_batch(b), self.clock.mono)
            if on_batch:
                on_batch(self.clock.mono)
            msgs += self.core.tick(self.clock.mono)
            self.seq += 1
            self.t_us += b.n * 5000
        return msgs


@pytest.fixture
def env(tmp_path):
    save_calibration(CAL, tmp_path / "calibration.json")
    clock = Clock()
    core = Core(tmp_path, now_fn=clock.unix, monotonic_fn=clock.monotonic)
    return core, clock, tmp_path, Stream(core, clock)


def of(msgs, kind):
    return [d for k, d in msgs if k == kind]


def test_live_messages_at_about_30hz_and_json_safe(env):
    core, clock, _, st = env
    d = generate([Scenario("step_on"), Scenario("stance", 2.0)], core.cfg, cal=CAL)
    msgs = st.feed(d.counts)
    live = of(msgs, "live")
    assert 3.0 * 20 * 0.9 <= len(live) <= 3.0 * 30 * 1.05     # 50 ms batches cap it at 20 Hz here
    assert sum(len(m["t"]) for m in live) == len(d.counts)
    json.dumps(live, allow_nan=False)
    assert live[-1]["state"] == "armed" and live[-1]["bw_n"] == pytest.approx(d.truth["bw_n"], rel=0.01)
    assert live[-1]["lead_plate"] == "L"


def test_status_once_per_second_with_channels(env):
    core, clock, _, st = env
    d = generate([Scenario("stance", 3.0)], core.cfg, cal=CAL)
    status = of(st.feed(d.counts), "status")
    assert len(status) == 3
    st = status[-1]
    assert st["calibrated"] is True and st["state"] in ("address", "armed")
    assert [c["id"] for c in st["channels"]] == ["L1", "L2", "L3", "L4", "R1", "R2", "R3", "R4"]
    assert st["rate_hz"] == pytest.approx(200, rel=0.05)
    json.dumps(st, allow_nan=False)


def test_bad_payload_is_counted_not_raised(env):
    core, clock, _, st = env
    core.on_payload(b"garbage", clock.mono)
    assert core.status()["decode_errors"] == 1


def test_swing_is_saved_and_announced(env):
    core, clock, _, st = env
    d = generate([Scenario("step_on"), Scenario("swing"), Scenario("stance", 2.0)], core.cfg, cal=CAL, seed=1)
    msgs = st.feed(d.counts)
    swings = of(msgs, "swing")
    assert len(swings) == 1
    assert [s["id"] for s in core.swings()] == [swings[0]["id"]]
    full = core.swing(swings[0]["id"])
    assert len(full["arrays"]["t"]) > 100
    assert core.swing_csv(swings[0]["id"]).startswith("t_s,")
    assert core.delete_swing(swings[0]["id"]) == {"ok": True}
    assert core.swings() == []


def test_shot_event_labels_impact(env):
    core, clock, _, st = env
    d = generate([Scenario("step_on"), Scenario("swing"), Scenario("stance", 2.0)], core.cfg, cal=CAL, seed=1)
    t_imp = d.truth["swings"][0]["impact"]
    host0 = clock.mono
    impact_host = host0 + 0.005 + t_imp
    def on_batch(now):
        if abs(now - (impact_host + 0.03)) < 0.025:
            core.shot_event(t_unix_ms=(UNIX0 + impact_host) * 1000)

    msgs = st.feed(d.counts, on_batch)
    sw = of(msgs, "swing")[0]
    assert sw["impact_source"] == "shot"
    assert sw["events"]["impact"] is not None


def test_late_shot_event_sends_swing_updated(env):
    core, clock, _, st = env
    d = generate([Scenario("step_on"), Scenario("swing"), Scenario("stance", 1.0)], core.cfg, cal=CAL, seed=1)
    host0 = clock.mono
    st.feed(d.counts)
    impact_host = host0 + 0.005 + d.truth["swings"][0]["impact"]
    res = core.shot_event(t_unix_ms=(UNIX0 + impact_host) * 1000)
    assert res["labelled"] is not None
    upd = of(core.tick(clock.mono + 1), "swing_updated")
    assert upd and upd[0]["events"]["impact"] is not None
    assert core.swings()[0]["events"]["impact"] is not None


def test_put_config_applies_and_persists(env):
    core, clock, path, st = env
    out = core.put_config({"golfer": "LH", "plate_spacing_mm": 380.0})
    assert out["golfer"] == "LH"
    assert core.pipe.cfg.golfer == "LH" and core.detector.cfg.golfer == "LH"
    assert json.loads((path / "config.json").read_text())["plate_spacing_mm"] == 380.0
    with pytest.raises(ValueError):
        core.put_config({"golfer": "nope"})


def test_zero_requires_samples(env):
    core, clock, _, st = env
    with pytest.raises(RuntimeError):
        core.zero()
    st.feed(np.tile(np.asarray(CAL.tares, dtype=np.int32) + 50, (400, 1)))
    assert core.zero()["ok"] is True
    np.testing.assert_allclose(core.pipe.tares, np.asarray(CAL.tares) + 50, atol=1)


def test_manual_arm_and_trigger(env):
    core, clock, _, st = env
    assert core.record_trigger()["ok"] is False
    d = generate([Scenario("step_on"), Scenario("stance", 2.0)], core.cfg, cal=CAL)
    st.feed(d.counts)
    assert core.record_arm()["state"] == "armed"
    assert core.record_trigger()["ok"] is True
    d2 = generate([Scenario("stance", 2.0)], core.cfg, cal=CAL, seed=2)
    msgs = st.feed(d2.counts)
    assert len(of(msgs, "swing")) == 1


def test_calibration_wizard_end_to_end(env):
    core, clock, path, st = env
    cfg = core.cfg
    true_gains = np.array([4.1e-4, 4.6e-4, 5.0e-4, 4.4e-4, 4.8e-4, 4.2e-4, 4.5e-4, 4.9e-4])
    tares = np.array([900.0, -300, 40, 700, -1200, 60, 0, 5000])

    def hold(forces, seconds=2.2):
        n = int(seconds * RATE_HZ)
        counts = np.round(tares + np.asarray(cfg.signs) * forces / true_gains).astype(np.int32)
        st.feed(np.tile(counts, (n, 1)))

    plan = core.calib_start(mass_kg=20.0)
    assert plan["steps"][0]["kind"] == "zero" and len(plan["steps"]) == 11
    hold(np.zeros(8))
    assert core.calib_capture({"kind": "zero"})["ok"]
    for step in plan["steps"][1:]:
        hold(corner_forces(cfg, step["plate"], step["xy"], 20.0 * G))
        core.calib_capture(step)
    solved = core.calib_solve()
    np.testing.assert_allclose(solved["gains"], true_gains, rtol=1e-3)
    assert max(abs(r) for rs in solved["residuals_n"].values() for r in rs) < 1.0
    core.calib_save()
    assert core.pipe.cal.gains == pytest.approx(true_gains.tolist(), rel=1e-3)
    assert json.loads((path / "calibration.json").read_text())["mass_kg"] == 20.0


def test_calib_capture_without_start_errors(env):
    core, _, _, st = env
    with pytest.raises(RuntimeError):
        core.calib_capture({"kind": "zero"})


def test_placement_step_positions_come_from_config(env):
    core, _, _, st = env
    steps = core.calib_start(mass_kg=20.0)["steps"]
    assert steps[1]["xy"] == list(placement_spots(Config(), "L")[0][1])
