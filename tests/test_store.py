import csv
import io
import json

import numpy as np
import pytest

from open_fp.store import SwingStore
from open_fp.swing import Swing


def make_swing(sid="20260923-120000-000", created="2026-09-23T12:00:00", n=50):
    t = np.arange(n) / 200.0
    cop = np.stack([np.linspace(-100, 100, n), np.zeros(n)], axis=1)
    cop_nan = cop.copy()
    cop_nan[0] = np.nan
    arrays = {
        "t": t, "forces": np.full((n, 8), 100.0),
        "fz_L": np.full(n, 400.0), "fz_R": np.full(n, 400.0),
        "cop_L": cop_nan, "cop_R": cop, "cop_C": cop, "lead_pct": np.full(n, 50.0),
    }
    events = {"motion_start": 0.05, "max_trail": 0.1, "transition": 0.12, "max_lead": 0.2,
              "finish": None, "impact": None, "trigger": 0.15}
    metrics = {"lead_pct_address": 55.0, "peak_fz_pct_bw": {"lead": 140.0}}
    return Swing(id=sid, created=created, golfer="RH", bw_n=800.0, t0_host=123.4,
                 arrays=arrays, events=events, metrics=metrics)


def test_save_then_get_round_trips_arrays(tmp_path):
    store = SwingStore(tmp_path)
    sw = make_swing()
    store.save(sw)
    got = store.get(sw.id)
    json.dumps(got, allow_nan=False)
    assert got["id"] == sw.id and got["metrics"] == sw.metrics
    assert got["arrays"]["cop_L"][0] is None
    np.testing.assert_allclose(got["arrays"]["t"], sw.arrays["t"])
    assert len(got["arrays"]["forces"]) == 50


def test_load_swing_restores_numpy(tmp_path):
    store = SwingStore(tmp_path)
    sw = make_swing()
    store.save(sw)
    back = store.load_swing(sw.id)
    np.testing.assert_array_equal(back.arrays["forces"], sw.arrays["forces"])
    assert np.isnan(back.arrays["cop_L"][0, 0])
    assert back.events == sw.events and back.bw_n == sw.bw_n


def test_list_returns_summaries_newest_first(tmp_path):
    store = SwingStore(tmp_path)
    store.save(make_swing("20260923-120000-000", "2026-09-23T12:00:00"))
    store.save(make_swing("20260923-130000-000", "2026-09-23T13:00:00"))
    items = store.list()
    assert [i["id"] for i in items] == ["20260923-130000-000", "20260923-120000-000"]
    assert "arrays" not in items[0] and "path" in items[0]
    json.dumps(items, allow_nan=False)


def test_update_overwrites(tmp_path):
    store = SwingStore(tmp_path)
    sw = make_swing()
    store.save(sw)
    sw.events["impact"] = 0.18
    store.save(sw)
    assert store.get(sw.id)["events"]["impact"] == 0.18
    assert len(store.list()) == 1


def test_delete(tmp_path):
    store = SwingStore(tmp_path)
    sw = make_swing()
    store.save(sw)
    assert store.delete(sw.id) is True
    assert store.list() == []
    assert store.delete(sw.id) is False
    assert list(tmp_path.iterdir()) == []


def test_get_missing_raises_keyerror(tmp_path):
    with pytest.raises(KeyError):
        SwingStore(tmp_path).get("20260101-000000-000")


@pytest.mark.parametrize("bad", ["../etc/passwd", "a/b", "..", "", "x" * 200, "id.json"])
def test_rejects_unsafe_ids(tmp_path, bad):
    store = SwingStore(tmp_path)
    with pytest.raises(KeyError):
        store.get(bad)
    with pytest.raises(KeyError):
        store.delete(bad)


def test_csv_export(tmp_path):
    store = SwingStore(tmp_path)
    sw = make_swing()
    store.save(sw)
    rows = list(csv.reader(io.StringIO(store.csv(sw.id))))
    header = rows[0]
    assert header[:2] == ["t_s", "lead_pct"]
    assert "L1_n" in header and "R4_n" in header and "cop_C_x_mm" in header
    assert len(rows) == 1 + 50
    assert rows[1][header.index("cop_L_x_mm")] == ""      # NaN -> empty cell


def test_skips_corrupt_files_in_list(tmp_path):
    store = SwingStore(tmp_path)
    store.save(make_swing())
    (tmp_path / "20260101-000000-000.json").write_text("{not json")
    assert len(store.list()) == 1
