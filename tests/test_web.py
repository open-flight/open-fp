import pytest
from fastapi.testclient import TestClient

from open_fp.app import Core
from open_fp.web import register
from sim_server import SimWebUI


@pytest.fixture
def client(tmp_path):
    ui = SimWebUI(assets_dir="app/assets")
    core = Core(tmp_path)
    register(ui, core)
    ui.mount_assets()
    return TestClient(ui.app), core


def test_status(client):
    c, _ = client
    r = c.get("/api/status")
    assert r.status_code == 200 and r.json()["state"] == "idle"


def test_config_round_trip_and_validation(client):
    c, core = client
    assert c.put("/api/config", json={"golfer": "LH"}).json()["golfer"] == "LH"
    assert c.get("/api/config").json()["golfer"] == "LH"
    r = c.put("/api/config", json={"golfer": "??"})
    assert r.status_code == 400 and "golfer" in r.json()["detail"]


def test_zero_without_data_is_conflict(client):
    c, _ = client
    assert c.post("/api/zero").status_code == 409


def test_swings_empty_and_unknown(client):
    c, _ = client
    assert c.get("/api/swings").json() == []
    assert c.get("/api/swings/20260101-000000-000").status_code == 404
    assert c.get("/api/swings/..%2F..%2Fetc").status_code == 404
    assert c.delete("/api/swings/20260101-000000-000").json() == {"ok": False}


def test_csv_route_is_matched_before_id_route(client, tmp_path):
    c, core = client
    from test_store import make_swing
    core.store.save(make_swing())
    r = c.get("/api/swings/20260923-120000-000.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]


def test_calibration_routes(client):
    c, _ = client
    assert c.post("/api/calib/capture", json={"kind": "zero"}).status_code == 409
    steps = c.post("/api/calib/start", json={"mass_kg": 20}).json()["steps"]
    assert len(steps) == 11


def test_shot_and_record_routes(client):
    c, _ = client
    assert c.post("/api/events/shot", json={"t_unix_ms": 1.0}).json()["ok"] is True
    assert c.post("/api/record/trigger").json()["ok"] is False
    assert c.post("/api/record/arm").json()["ok"] is False


def test_static_index_served(client):
    c, _ = client
    r = c.get("/")
    assert r.status_code == 200 and "<html" in r.text.lower()
