"""live_multi: sketch lines become browser events; the hub replays per-channel status."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "bench"))

from live_multi import MultiHub, layout, render_page, to_event  # noqa: E402
from multi_cell import DEFAULT_CHANNELS, parse_channels, parse_line  # noqa: E402


def test_window_event():
    e = json.loads(to_event(parse_line("S,1250,94,94,L1:94:160000:600:158000:162000:9")))
    assert e["type"] == "window" and e["drdy"] == 94
    assert e["chans"]["L1"] == {"n": 94, "mean": 160000, "std": 600, "vmin": 158000, "vmax": 162000, "rep": 9}


def test_readback_and_voltage_events():
    rb = json.loads(to_event(parse_line("R,R2,1,81,C4,40,00")))
    assert rb == {"type": "readback", "ch": "R2", "ok": True, "regs": "81 C4 40 00"}
    v = json.loads(to_event(parse_line("V,L2,AIN0,1659.0")))
    assert v == {"type": "voltage", "ch": "L2", "name": "AIN0", "value": "1659.0"}


def test_hub_replays_latest_status_per_channel():
    hub = MultiHub()
    for line in ("R,L1,1,81,C4,40,00", "R,L2,0,00,00,00,00", "R,L1,0,FF,FF,FF,FF", "S,1,1,1"):
        hub.publish(to_event(parse_line(line)))
    q = hub.add()
    replay = [json.loads(q.get_nowait()) for _ in range(q.qsize())]
    assert [(e["ch"], e["ok"]) for e in replay] == [("L1", False), ("L2", False)]


def test_layout_defaults_to_plate_l_corners_from_the_config():
    lay = layout(parse_channels(DEFAULT_CHANNELS))
    assert lay["title"] == "Plate L" and lay["total_of"] == "plate L" and lay["plates"] == ["L"]
    cells = {c["ch"]: c for c in lay["cells"]}
    assert list(cells) == ["L1", "L2", "L3", "L4"] and all(c["on"] for c in cells.values())
    assert (cells["L1"]["x"], cells["L1"]["y"], cells["L1"]["desc"]) == (-307.2, 122.4, "toe, outer")
    assert (cells["L3"]["x"], cells["L3"]["y"], cells["L3"]["desc"]) == (-62.4, -122.4, "heel, inner")
    assert lay["centre"] == {"L": -184.8}


def test_layout_for_both_plates_and_a_partial_set():
    both = layout(parse_channels("all"))
    assert both["title"] == "Both plates" and both["plates"] == ["L", "R"]
    assert {c["ch"]: c["desc"] for c in both["cells"]}["R2"] == "toe, outer"
    toes = layout(parse_channels("L1,L2,R1,R2"))
    assert toes["title"] == "L1 L2 R1 R2"
    assert [c["ch"] for c in toes["cells"] if not c["on"]] == ["L3", "L4", "R3", "R4"]


def test_page_has_the_layout_filled_in():
    page = render_page(parse_channels("R"))
    assert "__LAYOUT__" not in page and "__TITLE__" not in page
    assert "<title>Plate R live</title>" in page
    start = page.index("const LAYOUT = ") + len("const LAYOUT = ")
    lay = json.loads(page[start : page.index(";\n", start)])
    assert [c["ch"] for c in lay["cells"]] == ["R1", "R2", "R3", "R4"]
