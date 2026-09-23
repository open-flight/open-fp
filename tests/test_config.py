import json

import numpy as np
import pytest

from open_fp.config import CHANNEL_IDS, Config, load_config, save_config


def test_channel_order_matches_cs_pin_order():
    assert CHANNEL_IDS == ("L1", "L2", "L3", "L4", "R1", "R2", "R3", "R4")


def test_default_positions_match_spec_table():
    expected = [
        (-307.2, 122.4), (-62.4, 122.4), (-62.4, -122.4), (-307.2, -122.4),
        (62.4, 122.4), (307.2, 122.4), (307.2, -122.4), (62.4, -122.4),
    ]
    np.testing.assert_allclose(Config().positions(), expected)


def test_plate_spacing_moves_plates_symmetrically():
    pos = Config(plate_spacing_mm=400.0).positions()
    assert pos[0][0] == pytest.approx(-200.0 - 122.4)
    assert pos[4][0] == pytest.approx(200.0 - 122.4)


def test_explicit_positions_override_geometry():
    custom = [[float(i), float(-i)] for i in range(8)]
    np.testing.assert_allclose(Config(positions_mm=custom).positions(), custom)


def test_plate_indices():
    cfg = Config()
    assert cfg.plate_channels("L") == [0, 1, 2, 3]
    assert cfg.plate_channels("R") == [4, 5, 6, 7]


@pytest.mark.parametrize("golfer, lead, trail", [("RH", "L", "R"), ("LH", "R", "L")])
def test_handedness_maps_plates(golfer, lead, trail):
    cfg = Config(golfer=golfer)
    assert (cfg.lead_plate, cfg.trail_plate) == (lead, trail)


def test_lead_direction_points_toward_lead_plate():
    assert Config(golfer="RH").lead_dir_x == -1
    assert Config(golfer="LH").lead_dir_x == 1


def test_rejects_bad_golfer():
    with pytest.raises(ValueError):
        Config(golfer="XX")


def test_rejects_bad_sign_count():
    with pytest.raises(ValueError):
        Config(signs=[1, 1, 1])


def test_load_missing_file_gives_defaults(tmp_path):
    assert load_config(tmp_path / "nope.json") == Config()


def test_save_load_round_trip(tmp_path):
    cfg = Config(golfer="LH", plate_spacing_mm=380.0, signs=[1, -1, 1, 1, 1, 1, 1, 1], bw_override_n=800.0)
    cfg.swing.trigger_speed_mm_s = 250.0
    path = tmp_path / "config.json"
    save_config(cfg, path)
    assert load_config(path) == cfg


def test_load_partial_file_keeps_other_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"golfer": "LH", "swing": {"address_hold_s": 1.2}}))
    cfg = load_config(path)
    assert cfg.golfer == "LH"
    assert cfg.swing.address_hold_s == 1.2
    assert cfg.swing.trigger_speed_mm_s == Config().swing.trigger_speed_mm_s
    assert cfg.plate_spacing_mm == Config().plate_spacing_mm


def test_load_rejects_unknown_keys(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"golfr": "LH"}))
    with pytest.raises(ValueError):
        load_config(path)


def test_update_from_dict_validates():
    cfg = Config()
    with pytest.raises(ValueError):
        cfg.updated({"golfer": "nope"})
    assert cfg.updated({"golfer": "LH"}).golfer == "LH"
    assert cfg.golfer == "RH"  # original untouched
