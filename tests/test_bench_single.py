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
