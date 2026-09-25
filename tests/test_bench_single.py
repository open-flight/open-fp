import pytest
from single_cell import (
    FULL_SCALE,
    Readback,
    SketchError,
    Stats,
    check_baseline,
    detect_press,
    parse_line,
    returned_to_baseline,
    scale_from_mass,
    summarize,
)


def S(ms, mean, std=400, n=100, spread=2000):
    return Stats(ms=ms, n=n, mean=mean, std=std, vmin=mean - spread, vmax=mean + spread)


# -- parsing -------------------------------------------------------------------------------------


def test_parse_readback_ok_and_fail():
    assert parse_line("R,1,0E,C4,40,00") == Readback(True, (0x0E, 0xC4, 0x40, 0x00))
    assert parse_line("R,0,FF,FF,FF,FF") == Readback(False, (0xFF, 0xFF, 0xFF, 0xFF))


def test_parse_stats_with_negative_values():
    assert parse_line("S,12345,100,-250000,512,-253000,-247000") == Stats(
        12345, 100, -250000, 512, -253000, -247000
    )


def test_parse_error_and_noise_lines():
    assert parse_line("E,no DRDY for 500 ms") == SketchError("no DRDY for 500 ms")
    assert parse_line("# banner") is None
    assert parse_line("") is None
    assert parse_line("garbage,line") is None
    assert parse_line("S,1,2") is None  # truncated line from a partial read


def test_parse_tolerates_monitor_prefix_and_crlf():
    assert parse_line("  S,1,100,5,6,0,10\r\n") == Stats(1, 100, 5, 6, 0, 10)


# -- baseline ----------------------------------------------------------------------------------


def test_good_baseline_passes():
    windows = [S(100 * i, 1_200_000 + i) for i in range(100)]
    r = check_baseline(windows)
    assert r.ok, r.problems
    assert r.rate_hz == pytest.approx(1000, rel=0.01)
    assert r.mean == pytest.approx(1_200_050, abs=1)
    assert r.noise == 400
    assert r.headroom == FULL_SCALE - r.mean


def test_baseline_flags_low_sample_rate():
    windows = [S(100 * i, 0, n=40) for i in range(50)]
    r = check_baseline(windows)
    assert not r.ok and any("sample rate" in p for p in r.problems)


def test_baseline_flags_saturation():
    windows = [S(100 * i, 8_388_607, std=0, spread=0) for i in range(50)]
    r = check_baseline(windows)
    assert not r.ok and any("full scale" in p for p in r.problems)


def test_baseline_flags_high_noise():
    windows = [S(100 * i, 0, std=40_000) for i in range(50)]
    r = check_baseline(windows)
    assert not r.ok and any("noisy" in p for p in r.problems)


def test_baseline_flags_drift():
    windows = [S(100 * i, 1000 * i) for i in range(100)]  # 99k counts over 10 s
    r = check_baseline(windows)
    assert not r.ok and any("drift" in p for p in r.problems)


def test_baseline_needs_data():
    r = check_baseline([])
    assert not r.ok and r.problems


# -- press ---------------------------------------------------------------------------------------


def test_detect_press_and_sign():
    base = 1_000_000
    press = [S(i, base) for i in range(5)] + [S(i, base - 150_000) for i in range(5, 25)]
    r = detect_press(base, press, min_delta=20_000)
    assert r.pressed and r.delta == pytest.approx(-150_000, abs=1) and r.sign == -1


def test_detect_press_none():
    r = detect_press(0, [S(i, 3_000) for i in range(30)], min_delta=20_000)
    assert not r.pressed


# -- mass scale --------------------------------------------------------------------------------


def test_scale_from_mass():
    base = 500_000
    loaded = [S(i, base + 43_000) for i in range(30)]
    s = scale_from_mass(base, loaded, mass_kg=2.0)
    assert s.counts_per_kg == pytest.approx(21_500)
    assert s.ok


def test_scale_flags_implausible_sensitivity():
    s = scale_from_mass(0, [S(i, 300) for i in range(30)], mass_kg=2.0)
    assert not s.ok


def test_summary_lists_failures():
    windows = [S(100 * i, 0) for i in range(100)]
    text = summarize(Readback(False, (0xFF,) * 4), check_baseline(windows), None, None)
    assert "FAIL" in text and "readback" in text.lower()


def test_returned_to_baseline():
    assert returned_to_baseline(1_000, [S(i, 1_800) for i in range(10)], press_delta=-150_000)
    assert not returned_to_baseline(1_000, [S(i, 60_000) for i in range(10)], press_delta=-150_000)


def test_summary_without_data_says_so_plainly():
    text = summarize(Readback(True, (0x0E, 0xC4, 0x40, 0x00)), check_baseline([]), None, None)
    assert "no data from the sketch" in text
    assert "headroom" not in text and "mean 0" not in text


# -- single-ended mode (AIN0 vs ground; for testing before R1/R2 are fitted) -----------------------


def test_modes_have_expected_registers():
    from single_cell import DIFFERENTIAL, SINGLE_ENDED

    assert DIFFERENTIAL.regs == (0x0E, 0xC4, 0x40, 0x00)
    assert SINGLE_ENDED.regs == (0x81, 0xC4, 0x40, 0x00)
    assert SINGLE_ENDED.command == "s" and DIFFERENTIAL.command == "d"


def test_single_ended_press_threshold_sees_a_small_gain_1_press():
    from single_cell import SINGLE_ENDED

    base = 4_190_000
    windows = [S(i, base) for i in range(5)] + [S(i, base - 600, std=40) for i in range(5, 20)]
    assert detect_press(base, windows, min_delta=SINGLE_ENDED.press_delta).pressed
    assert not detect_press(base, windows, min_delta=20_000).pressed


def test_single_ended_mass_range():
    from single_cell import SINGLE_ENDED

    s = scale_from_mass(
        0, [S(i, 240) for i in range(30)], mass_kg=2.0, cpk_range=SINGLE_ENDED.cpk_range
    )
    assert s.ok and s.counts_per_kg == pytest.approx(120)


def test_summary_uses_mode_expected_registers():
    from single_cell import SINGLE_ENDED

    text = summarize(Readback(False, (0x0E, 0xC4, 0x40, 0x00)), None, None, None, mode=SINGLE_ENDED)
    assert "expected 81 C4 40 00" in text


def test_release_tolerance_scales_with_mode():
    from single_cell import SINGLE_ENDED

    windows = [S(i, 1_000 + 300) for i in range(10)]  # 300 counts off after a 600-count press
    assert returned_to_baseline(1_000, windows, press_delta=-600)  # default floor: 5,000
    assert not returned_to_baseline(
        1_000, windows, press_delta=-600, floor=SINGLE_ENDED.press_delta / 4
    )


def test_parse_stats_with_drdy_count():
    st = parse_line("S,1000,74,4190000,40,4189900,4190100,100")
    assert st == Stats(1000, 74, 4190000, 40, 4189900, 4190100, 100)


def test_rate_uses_drdy_count_when_reported():
    # loop captured only 74 of every 100 conversions, but the ADC ran at 1000 SPS
    windows = [Stats(100 * i, 74, 0, 400, -2000, 2000, 100) for i in range(50)]
    r = check_baseline(windows)
    assert r.rate_hz == pytest.approx(1000, rel=0.01) and r.ok, r.problems


def test_release_tolerance_allows_for_baseline_drift():
    # the owner's first single-ended run: -343 press, 176 counts of baseline drift in 10 s
    windows = [S(i, 1_000 - 150) for i in range(10)]
    assert not returned_to_baseline(1_000, windows, press_delta=-343, floor=37.5)
    assert returned_to_baseline(1_000, windows, press_delta=-343, floor=37.5, drift=-176)


def test_release_offset_reports_where_it_settled():
    from single_cell import release_offset

    assert release_offset(1_000, [S(i, 1_120) for i in range(10)]) == 120
