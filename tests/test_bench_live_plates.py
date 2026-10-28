"""live_plates: ads1220_stream lines become protocol batches that drive the app core."""

import json
import time

import numpy as np
from live_plates import parse_stream_line, seed_config
from multi_cell import ChanReadback

from open_fp.app import Core
from open_fp.calibration import NOMINAL_GAIN_N_PER_COUNT
from open_fp.config import load_config
from open_fp.protocol import encode_batch


def line(seq: int, t_first: int, counts, flags: int = 0) -> str:
    """What the sketch prints: 6 hex digits of 24-bit two's complement per value."""
    hexes = "".join(f"{int(v) & 0xFFFFFF:06X}" for v in np.asarray(counts).ravel())
    return f"B,{seq},{t_first},5000,{flags},{hexes}"


def test_batch_line_round_trip_with_negative_counts():
    counts = np.arange(80, dtype=np.int32).reshape(10, 8) * 1000 - 40000
    counts[0, 0], counts[0, 1] = -8388608, 8388607
    b = parse_stream_line(line(7, 123456, counts, flags=2))
    assert (b.seq, b.t_first_us, b.period_us, b.flags) == (7, 123456, 5000, 2)
    assert b.counts.dtype == np.int32 and np.array_equal(b.counts, counts)


def test_malformed_batch_lines_are_dropped():
    assert parse_stream_line("B,1,2,5000,0,ABC") is None          # not whole values
    assert parse_stream_line("B,1,2,5000,0,ZZZZZZ" * 8) is None   # not hex
    assert parse_stream_line("B,1,2,5000") is None


def test_other_lines_parse_like_the_bench_sketches():
    assert parse_stream_line("R,R4,1,0E,C4,40,00") == ChanReadback("R4", True, (0x0E, 0xC4, 0x40, 0x00))
    assert parse_stream_line("# ads1220_stream: hello") is None


def test_fresh_data_dir_gets_negative_signs(tmp_path):
    seed_config(tmp_path)
    assert load_config(tmp_path / "config.json").signs == [-1] * 8
    (tmp_path / "config.json").write_text(json.dumps({"signs": [1] * 8}), encoding="utf-8")
    seed_config(tmp_path)  # never overwrites
    assert load_config(tmp_path / "config.json").signs == [1] * 8


def test_stream_drives_the_core_lead_trail_split(tmp_path):
    """Plates zeroed empty, then a golfer with 70 % on the left (lead, RH) plate."""
    seed_config(tmp_path)
    core = Core(tmp_path)
    offsets = np.array([150_000, -2_500_000, 400_000, 130_000, 110_000, -900_000, 405_000, -1_187_000])
    per_cell_n = np.array([0.7, 0.7, 0.7, 0.7, 0.3, 0.3, 0.3, 0.3]) * 800 / 4
    loaded = offsets - per_cell_n / NOMINAL_GAIN_N_PER_COUNT   # cells read lower under load
    seq, t = 0, 0
    for counts_row in [offsets] * 60 + [loaded] * 60:          # 3 s empty, 3 s standing
        if seq == 30:
            core.zero()
        b = parse_stream_line(line(seq, t, np.tile(counts_row, (10, 1))))
        core.on_payload(encode_batch(b), time.monotonic())
        seq, t = seq + 1, t + 50_000
    live = [p for e, p in core.tick(time.monotonic()) if e == "live"][-1]
    lead = [v for v in live["lead_pct"] if v is not None][-1]
    assert abs(lead - 70.0) < 0.5
    assert abs(live["fz"]["L"][-1] - 560) < 5 and abs(live["fz"]["R"][-1] - 240) < 5
