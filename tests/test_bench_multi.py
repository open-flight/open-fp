from multi_cell import (
    ChanReadback,
    ChanStats,
    ChanVoltage,
    Report,
    Window,
    attribute_press,
    check_bus,
    check_channel,
    check_rate,
    check_voltages,
    choose_mode,
    parse_line,
    summarize,
)
from single_cell import DIFFERENTIAL, SINGLE_ENDED, ModeLine, SketchError

OK_REGS = (0x0E, 0xC4, 0x40, 0x00)


def cs(mean, std=120, n=240, rep=5, spread=400):
    return ChanStats(n=n, mean=mean, std=std, vmin=mean - spread, vmax=mean + spread, rep=rep)


def win(ms, **chans):
    return Window(ms=ms, ticks=240, drdy=250, chans=chans)


# -- parsing -------------------------------------------------------------------------------------


def test_parse_readback_per_channel():
    assert parse_line("R,L2,1,0E,C4,40,00") == ChanReadback("L2", True, OK_REGS)
    assert parse_line("R,R4,0,FF,FF,FF,FF") == ChanReadback("R4", False, (0xFF,) * 4)
    assert parse_line("R,X9,1,0E,C4,40,00") is None


def test_parse_window_with_several_channels():
    w = parse_line("S,1250,241,250,L1:241:4195000:110:4194700:4195300:3,R2:241:-12:0:-12:-12:240")
    assert w == Window(
        1250,
        241,
        250,
        {
            "L1": ChanStats(241, 4195000, 110, 4194700, 4195300, 3),
            "R2": ChanStats(241, -12, 0, -12, -12, 240),
        },
    )
    assert parse_line("S,1250,241,250") == Window(1250, 241, 250, {})


def test_parse_rejects_truncated_window():
    assert parse_line("S,1250,241,250,L1:241:4195000") is None


def test_parse_voltage_mode_and_error_lines():
    assert parse_line("V,L1,AIN0,1654") == ChanVoltage("L1", "AIN0", "1654")
    assert parse_line("V,L1,REF,<AVDD/4: REFP0/REFN0 not connected?") == ChanVoltage(
        "L1", "REF", "<AVDD/4: REFP0/REFN0 not connected?"
    )
    assert parse_line("M,single-ended") == ModeLine("single-ended")
    assert parse_line("E,raw dump: fewer than 16 ticks (DRDY?)") == SketchError(
        "raw dump: fewer than 16 ticks (DRDY?)"
    )
    assert parse_line("# banner") is None
    assert parse_line("X,L1,0,400290,4194960") is None


# -- bus -----------------------------------------------------------------------------------------


def test_bus_flags_missing_and_unexpected_units():
    rbs = {
        "L1": ChanReadback("L1", True, OK_REGS),
        "L2": ChanReadback("L2", False, (0, 0, 0, 0)),
        "L3": ChanReadback("L3", True, OK_REGS),
    }
    problems = check_bus(rbs, ["L1", "L2"])
    assert any("L2 doesn't answer on CS D4" in p for p in problems)
    assert any("L3's CS (D5)" in p for p in problems)
    assert check_bus({"L1": ChanReadback("L1", True, OK_REGS)}, ["L1"]) == []


# -- voltages ------------------------------------------------------------------------------------


GOOD = {"AVDD": "3308", "AIN0": "1654", "AIN1": "589", "REF": "3305"}


def test_voltages_ok_without_r1r2():
    v = check_voltages("L1", GOOD)
    assert v.ok and not v.r1r2


def test_voltages_detect_r1r2_and_bridge_offset():
    assert check_voltages("L1", {**GOOD, "AIN1": "1650"}).r1r2
    v = check_voltages("L1", {**GOOD, "AIN0": "1690", "AIN1": "1650"})
    assert v.r1r2 and not v.ok and "bridge offset +40 mV" in v.problems[0]


def test_voltages_catch_s_wire_at_the_rail_and_missing_reference():
    v = check_voltages("L2", {**GOOD, "AIN0": ">2048"})
    assert not v.ok and "centre tap (AIN0) >2048" in v.problems[0]
    v = check_voltages("L2", {**GOOD, "REF": "<AVDD/4: REFP0/REFN0 not connected?"})
    assert not v.ok and "REFP0 -> 3V3" in v.problems[0]


def test_mode_is_differential_only_if_every_unit_has_r1r2():
    fitted = check_voltages("L1", {**GOOD, "AIN1": "1652"})
    bare = check_voltages("L2", GOOD)
    assert choose_mode({"L1": fitted}, None)[0] is DIFFERENTIAL
    mode, reason = choose_mode({"L1": fitted, "L2": bare}, None)
    assert mode is SINGLE_ENDED and "L2" in reason
    assert choose_mode({"L1": bare}, "differential")[0] is DIFFERENTIAL


# -- baseline ------------------------------------------------------------------------------------


def test_healthy_channel_passes():
    b = check_channel("L1", [win(i * 250, L1=cs(4195000)) for i in range(20)], SINGLE_ENDED)
    assert b.ok, b.problems


def test_stuck_channel_is_caught():
    stuck = [win(i * 250, R1=cs(4194960, std=0, rep=239, spread=0)) for i in range(20)]
    b = check_channel("R1", stuck, SINGLE_ENDED)
    assert not b.ok and "stuck" in b.problems[0]
    # the 257-count jumps seen on the second breakout still count as stuck
    jumpy = [win(i * 250, R1=cs(4194960, std=40, rep=230, spread=257)) for i in range(20)]
    assert not check_channel("R1", jumpy, SINGLE_ENDED).ok


def test_saturated_differential_channel_is_caught():
    sat = [win(i * 250, L2=cs(8388607, std=0, rep=239, spread=0)) for i in range(8)]
    b = check_channel("L2", sat, DIFFERENTIAL)
    assert not b.ok and any("full scale" in p and "R1/R2" in p for p in b.problems)
    assert not any("stuck" in p for p in b.problems)  # saturation, not the stuck-breakout fault


def test_missing_channel():
    assert not check_channel("R2", [win(0, L1=cs(1))], SINGLE_ENDED).ok


def test_rate_from_l1_drdy_and_timer_fallback():
    r = check_rate([win(i * 250, L1=cs(1)) for i in range(20)])
    assert r.ok and 990 < r.rate_hz < 1010 and 0.9 < r.captured < 1.0
    timer = [Window(i * 250, 250, 0, {"L2": cs(1)}) for i in range(8)]
    assert check_rate(timer).ok
    slow = [Window(i * 250, 100, 125, {"L1": cs(1)}) for i in range(8)]
    assert not check_rate(slow).ok


# -- press attribution ---------------------------------------------------------------------------

BASE = {"L1": 4_195_000.0, "L2": 4_100_000.0, "R1": 4_300_000.0}


def pressed(**moves):
    return [
        win(0, **{ch: cs(int(m)) for ch, m in BASE.items()}),
        win(250, **{ch: cs(int(m + moves.get(ch, 0))) for ch, m in BASE.items()}),
    ]


def test_press_on_the_right_unit_passes():
    r = attribute_press("L2", BASE, pressed(L2=-600, L1=20), SINGLE_ENDED.press_delta)
    assert r.ok and r.deltas["L2"] == -600


def test_press_moving_another_unit_means_swapped():
    r = attribute_press("L2", BASE, pressed(R1=-600), SINGLE_ENDED.press_delta)
    assert not r.ok and "L2 and R1 are swapped" in r.problem


def test_press_moving_two_units_is_crosstalk():
    r = attribute_press("L1", BASE, pressed(L1=-600, R1=-400), SINGLE_ENDED.press_delta)
    assert not r.ok and "so did R1" in r.problem


def test_no_response():
    r = attribute_press("R1", BASE, pressed(R1=-30), SINGLE_ENDED.press_delta)
    assert not r.ok and "didn't respond" in r.problem


# -- summary -------------------------------------------------------------------------------------


def test_summary_pass_and_fail():
    rep = Report(["L1", "R1"], readbacks={"L1": ChanReadback("L1", True, OK_REGS)})
    rep.bus_problems = check_bus(rep.readbacks, rep.expected)
    text = summarize(rep)
    assert "FAIL: R1 (1 of 2 units)" in text and "R1 doesn't answer on CS D7" in text
    ok = Report(["L1"], readbacks={"L1": ChanReadback("L1", True, OK_REGS)})
    ok.baselines["L1"] = check_channel(
        "L1", [win(i * 250, L1=cs(4195000)) for i in range(8)], SINGLE_ENDED
    )
    assert "PASS: 1 unit(s)" in summarize(ok)
