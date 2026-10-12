"""live_multi: sketch lines become browser events; the hub replays per-channel status."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "bench"))

from live_multi import MultiHub, to_event  # noqa: E402
from multi_cell import parse_line  # noqa: E402


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
