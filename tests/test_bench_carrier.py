import pytest
from carrier_check import OPEN, Check, checks_for, judge, parse_reading, run, summarize
from multi_cell import DEFAULT_CHANNELS, parse_channels


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("498", 498.0),
        ("1.02k", 1020.0),
        ("2M", 2e6),
        ("OL", OPEN),
        ("1", OPEN),
        ("y", True),
        ("n", False),
        ("498 Ω", 498.0),
        ("s", None),
        ("abc", None),
    ],
)
def test_parse_reading(text, value):
    assert parse_reading(text) == value


def test_judge_kinds():
    assert judge(Check("x", "", "beep"), True) and judge(Check("x", "", "beep"), 0.4)
    assert not judge(Check("x", "", "beep"), 480.0)
    assert judge(Check("x", "", "open"), OPEN) and judge(Check("x", "", "open"), False)
    assert not judge(Check("x", "", "open"), 2_000.0)
    assert judge(Check("x", "", "ohms", 400, 600), 500.0)
    assert not judge(Check("x", "", "ohms", 400, 600), True)
    assert judge(Check("x", "", "yes"), True) and not judge(Check("x", "", "yes"), False)


def _find(checks, text):
    return next(c for c in checks if text in c.what)


def test_supply_resistance_scales_with_units():
    four = _find(checks_for(["L1", "L2", "R1", "R2"], "units"), "no cells plugged in")
    one = _find(checks_for(["L1"], "units"), "no cells plugged in")
    assert four.lo < 500 < four.hi and one.lo < 2000 < one.hi
    cells = _find(checks_for(["L1", "L2", "R1", "R2"], "cables"), "all 4 cells plugged in")
    assert cells.lo < 250 < cells.hi


def test_stages_are_cumulative_and_ordered():
    bare = checks_for(["L1"], "bare")
    full = checks_for(["L1"], "uno")
    assert {c.stage for c in bare} == {"bare"}
    assert [c.stage for c in full][: len(bare)] == ["bare"] * len(bare)
    assert {c.stage for c in full} == {"bare", "units", "cables", "uno"}


def test_cs_checks_follow_the_pin_map():
    checks = checks_for(["L1", "R2"], "uno")
    assert _find(checks, "D8 to R2's CS pin").expect == "beep"
    assert _find(checks, "D3 to the other units' CS pins").expect == "open"
    assert _find(checks, "D2 to L1's DRDY").expect == "beep"
    assert not any("DRDY" in c.what for c in checks_for(["R1"], "uno"))


def test_run_and_summary():
    checks = [Check("bare", "A to B", "open", hint="bridge"), Check("bare", "B to N", "beep")]
    answers = iter(["junk", "12", "y"])
    results = run(checks, ask=lambda _: next(answers))
    assert [r["ok"] for r in results] == [False, True]
    text = summarize(results)
    assert "1 failed" in text and "bridge" in text and "Fix the failures" in text
    assert "Safe to power" in summarize(run(checks[1:], ask=lambda _: "y"))


def test_resistor_value_scales_the_expected_readings():
    r680 = _find(checks_for(["L1"], "units", r_each=680), "no cells plugged in")
    r1k5 = _find(checks_for(["L1"], "units", r_each=1500), "no cells plugged in")
    assert r680.lo < 1360 < r680.hi and r1k5.lo < 3000 < r1k5.hi
    ain1 = _find(checks_for(["L1"], "units", r_each=1500), "AIN1 pin")
    assert ain1.lo < 1500 < ain1.hi


def test_plate_r_carrier_checks_its_own_cs_pins():
    checks = checks_for(parse_channels("R"), "uno")
    assert _find(checks, "D7 to R1's CS pin").expect == "beep"
    assert _find(checks, "A2 to R4's CS pin").expect == "beep"
    assert not any("DRDY" in c.what for c in checks)


def test_chain_check_only_when_both_plates_are_wired():
    assert not any("BUS OUT" in c.what for c in checks_for(parse_channels(DEFAULT_CHANNELS), "uno"))
    both = checks_for(parse_channels("all"), "uno")
    assert _find(both, "plate L BUS OUT to plate R BUS IN").expect == "beep"
    assert not any("BUS OUT" in c.what for c in checks_for(parse_channels("all"), "cables"))
    supply = _find(checks_for(parse_channels("all"), "units"), "no cells plugged in")
    assert supply.lo < 250 < supply.hi  # 8 x 2 kΩ in parallel
