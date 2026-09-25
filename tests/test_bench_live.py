import json

from live_view import KEYS, to_event
from single_cell import ModeLine, Readback, SketchError, Stats, Voltage, parse_line


def test_parse_mode_and_voltage_lines():
    assert parse_line("M,single-ended") == ModeLine("single-ended")
    assert parse_line("V,AIN0,1663") == Voltage("AIN0", "1663")
    assert parse_line("V,REF,<AVDD/4: REFP0/REFN0 not connected?") == Voltage(
        "REF", "<AVDD/4: REFP0/REFN0 not connected?"
    )


def test_events_are_json_with_a_type():
    items = [
        Stats(1000, 95, 4204513, 116, 4204200, 4204800, 95),
        Readback(True, (0x81, 0xC4, 0x40, 0x00)),
        ModeLine("differential"),
        Voltage("AIN0", "1663"),
        SketchError("no DRDY for 500 ms"),
    ]
    events = [json.loads(to_event(i)) for i in items]
    assert [e["type"] for e in events] == ["stats", "readback", "mode", "voltage", "error"]
    assert events[0]["mean"] == 4204513 and events[0]["drdy"] == 95
    assert events[1]["regs"] == "81 C4 40 00" and events[1]["ok"] is True


def test_only_sketch_keys_are_forwarded():
    assert set(KEYS) == {"s", "d", "v", "r"}


def test_page_uses_the_stats_event_field_names():
    # regression: the page read e.min/e.max, but stats events carry vmin/vmax (NaN broke the chart)
    from live_view import PAGE

    fields = json.loads(to_event(Stats(0, 1, 2, 3, 4, 5, 6))).keys()
    for name in ("vmin", "vmax", "mean", "std", "drdy", "ms", "n"):
        assert name in fields and f"e.{name}" in PAGE, name
