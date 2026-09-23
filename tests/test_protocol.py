import numpy as np
import pytest

from open_fp.protocol import (
    FLAG_DRDY_MISSED,
    FLAG_SATURATION,
    HEADER_SIZE,
    Batch,
    ProtocolError,
    SequenceTracker,
    decode_batch,
    encode_batch,
    encode_batch_ints,
)


def _batch(n=10, seq=7, flags=0):
    rng = np.random.default_rng(1)
    counts = rng.integers(-(2**23), 2**23, size=(n, 8), dtype=np.int32)
    return Batch(seq=seq, t_first_us=123_456_789, period_us=5000, flags=flags, counts=counts)


def _assert_same(a: Batch, b: Batch):
    assert (a.seq, a.t_first_us, a.period_us, a.flags) == (b.seq, b.t_first_us, b.period_us, b.flags)
    np.testing.assert_array_equal(a.counts, b.counts)
    assert b.counts.dtype == np.int32


def test_header_is_16_bytes():
    assert HEADER_SIZE == 16


def test_binary_round_trip():
    b = _batch(flags=FLAG_DRDY_MISSED | FLAG_SATURATION)
    payload = encode_batch(b)
    assert len(payload) == 16 + 10 * 8 * 4
    _assert_same(b, decode_batch(payload))


def test_binary_layout_is_little_endian_header():
    payload = encode_batch(_batch(n=1, seq=0x01020304))
    assert payload[0:2] == b"\x1a\xf0"          # magic 0xF01A LE
    assert payload[2] == 1 and payload[3] == 1  # version, n
    assert payload[4:8] == b"\x04\x03\x02\x01"


@pytest.mark.parametrize("kind", [bytes, bytearray, memoryview])
def test_accepts_bytes_like(kind):
    b = _batch()
    _assert_same(b, decode_batch(kind(encode_batch(b))))


def test_int_array_fallback_round_trip():
    b = _batch(n=3, seq=2**32 - 1)
    ints = encode_batch_ints(b)
    assert isinstance(ints, list) and len(ints) == 7 + 3 * 8
    _assert_same(b, decode_batch(ints))


def test_rejects_wrong_magic():
    payload = bytearray(encode_batch(_batch()))
    payload[0] ^= 0xFF
    with pytest.raises(ProtocolError, match="magic"):
        decode_batch(payload)


def test_rejects_wrong_version():
    payload = bytearray(encode_batch(_batch()))
    payload[2] = 99
    with pytest.raises(ProtocolError, match="version"):
        decode_batch(payload)


def test_rejects_length_mismatch():
    payload = encode_batch(_batch())[:-4]
    with pytest.raises(ProtocolError, match="length"):
        decode_batch(payload)


def test_rejects_short_payload():
    with pytest.raises(ProtocolError):
        decode_batch(b"\x1a\xf0")


def test_rejects_int_fallback_wrong_length():
    ints = encode_batch_ints(_batch(n=2))[:-1]
    with pytest.raises(ProtocolError, match="length"):
        decode_batch(ints)


def test_sample_times_us():
    b = _batch(n=3)
    np.testing.assert_array_equal(b.sample_times_us(), [123_456_789, 123_461_789, 123_466_789])


def test_sequence_tracker_counts_gaps():
    tr = SequenceTracker()
    for s in [5, 6, 7, 10, 11]:
        tr.update(s)
    assert tr.gaps == 1 and tr.missing == 2


def test_sequence_tracker_handles_u32_wrap():
    tr = SequenceTracker()
    for s in [2**32 - 2, 2**32 - 1, 0, 1]:
        tr.update(s)
    assert tr.gaps == 0 and tr.missing == 0


def test_sequence_tracker_treats_backwards_jump_as_restart():
    tr = SequenceTracker()
    for s in [100, 101, 0, 1]:
        tr.update(s)
    assert tr.restarts == 1 and tr.missing == 0


def test_sequence_tracker_ignores_duplicate():
    tr = SequenceTracker()
    for s in [1, 2, 2, 3]:
        assert tr.update(s) in (0,)
    assert tr.duplicates == 1 and tr.missing == 0
