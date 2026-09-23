import numpy as np
import pytest

from open_fp.clock import ClockMapper, Unwrapper


def test_unwrapper_passes_through_monotonic_values():
    u = Unwrapper()
    assert [u.unwrap(v) for v in [0, 10, 2**31]] == [0, 10, 2**31]


def test_unwrapper_handles_wrap():
    u = Unwrapper()
    assert u.unwrap(2**32 - 100) == 2**32 - 100
    assert u.unwrap(50) == 2**32 + 50
    assert u.unwrap(2**31 + 50) == 2**32 + 2**31 + 50
    assert u.unwrap(10) == 2 * 2**32 + 10


def test_unmapped_before_first_update():
    with pytest.raises(RuntimeError):
        ClockMapper().to_host(0)


def _simulate(mapper, *, offset_s=1000.0, drift_ppm=50.0, start_us=0, duration_s=60.0,
              period_s=0.05, max_delay_s=0.03, seed=0):
    """Feed batches whose arrival = true host time + random positive delay."""
    rng = np.random.default_rng(seed)
    n = int(duration_s / period_s)
    for i in range(n):
        mcu_s = i * period_s
        mcu_us = (start_us + int(mcu_s * 1e6)) % 2**32
        true_host = offset_s + mcu_s * (1 + drift_ppm * 1e-6)
        mapper.update(mcu_us, true_host + rng.uniform(0, max_delay_s))
    def truth(mcu_s):
        return offset_s + mcu_s * (1 + drift_ppm * 1e-6)
    return truth, (start_us + int(duration_s * 1e6)) % 2**32, duration_s


def test_mapping_tracks_lower_envelope_not_mean_delay():
    m = ClockMapper()
    truth, last_us, dur = _simulate(m, max_delay_s=0.03)
    # Mean delay is 15 ms; lower-envelope fit should be within ~2 ms of truth.
    t_mcu = dur - 0.05
    assert abs(m.to_host(last_us - 50_000) - truth(t_mcu)) < 0.002


def test_mapping_follows_drift():
    m = ClockMapper()
    truth, last_us, dur = _simulate(m, drift_ppm=200.0, duration_s=120.0, max_delay_s=0.005)
    assert abs(m.to_host(last_us - 50_000) - truth(dur - 0.05)) < 0.002


def test_mapping_survives_micros_wraparound():
    m = ClockMapper()
    start = 2**32 - 10_000_000  # wraps 10 s in
    truth, last_us, dur = _simulate(m, start_us=start, duration_s=30.0, max_delay_s=0.005)
    assert abs(m.to_host(last_us - 50_000) - truth(dur - 0.05)) < 0.002


def test_fixed_latency_is_subtracted():
    m0, m1 = ClockMapper(), ClockMapper(fixed_latency_s=0.010)
    for m in (m0, m1):
        _simulate(m, max_delay_s=0.001, duration_s=5.0)
    assert m0.to_host(1_000_000) - m1.to_host(1_000_000) == pytest.approx(0.010, abs=1e-6)


def test_reset_on_mcu_restart():
    m = ClockMapper()
    _simulate(m, duration_s=5.0)
    m.reset()
    m.update(0, 5000.0)
    assert m.to_host(0) == pytest.approx(5000.0)


def test_to_host_array():
    m = ClockMapper()
    _simulate(m, duration_s=5.0, max_delay_s=0.0, drift_ppm=0.0)
    out = m.to_host_array(np.array([1_000_000, 1_005_000], dtype=np.int64))
    np.testing.assert_allclose(out, [1001.0, 1001.005], atol=1e-6)
