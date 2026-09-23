"""MCU -> Linux frame batches (§8.3, §9.2).

Binary form (MessagePack bin): 16-byte little-endian header then n * 8 * int32 LE:
    magic u16, version u8, n u8, seq u32, t_first_us u32, period_us u16, flags u8, reserved u8

Int-array fallback (if Bridge.notify can't send bin): a flat list
    [magic, version, n, seq, t_first_us, period_us, flags, c[0][0], ..., c[n-1][7]]
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

import numpy as np

MAGIC = 0xF01A
VERSION = 1
N_CH = 8
HEADER = struct.Struct("<HBBIIHBB")
HEADER_SIZE = HEADER.size
INT_HEADER_LEN = 7

FLAG_DRDY_MISSED = 0x01
FLAG_SATURATION = 0x02


class ProtocolError(ValueError):
    pass


@dataclass
class Batch:
    seq: int
    t_first_us: int      # MCU micros() at the first frame (wraps at 2**32)
    period_us: int       # frame period, 5000 at 200 Hz
    flags: int
    counts: np.ndarray   # (n, 8) int32, decimated ADC counts

    @property
    def n(self) -> int:
        return len(self.counts)

    def sample_times_us(self) -> np.ndarray:
        """MCU time of each frame (not wrapped; may exceed 2**32)."""
        return self.t_first_us + self.period_us * np.arange(self.n, dtype=np.int64)


def decode_batch(payload) -> Batch:
    if isinstance(payload, (list, tuple)):
        return _decode_ints(payload)
    return _decode_bytes(bytes(payload))


def _check(magic: int, version: int):
    if magic != MAGIC:
        raise ProtocolError(f"bad magic 0x{magic:04X}")
    if version != VERSION:
        raise ProtocolError(f"unsupported version {version}")


def _decode_bytes(buf: bytes) -> Batch:
    if len(buf) < HEADER_SIZE:
        raise ProtocolError(f"payload too short ({len(buf)} B)")
    magic, version, n, seq, t_first, period, flags, _ = HEADER.unpack_from(buf)
    _check(magic, version)
    expected = HEADER_SIZE + n * N_CH * 4
    if len(buf) != expected:
        raise ProtocolError(f"length {len(buf)} != expected {expected} for n={n}")
    counts = np.frombuffer(buf, dtype="<i4", offset=HEADER_SIZE).reshape(n, N_CH).astype(np.int32)
    return Batch(seq, t_first, period, flags, counts)


def _decode_ints(vals) -> Batch:
    if len(vals) < INT_HEADER_LEN:
        raise ProtocolError(f"payload too short ({len(vals)} ints)")
    magic, version, n, seq, t_first, period, flags = (int(v) for v in vals[:INT_HEADER_LEN])
    _check(magic, version)
    expected = INT_HEADER_LEN + n * N_CH
    if len(vals) != expected:
        raise ProtocolError(f"length {len(vals)} != expected {expected} for n={n}")
    counts = np.asarray(vals[INT_HEADER_LEN:], dtype=np.int32).reshape(n, N_CH)
    return Batch(seq, t_first, period, flags, counts)


def encode_batch(b: Batch) -> bytes:
    """Binary form, as the MCU sends it. Used by the simulator and tests."""
    header = HEADER.pack(MAGIC, VERSION, b.n, b.seq, b.t_first_us, b.period_us, b.flags, 0)
    return header + np.ascontiguousarray(b.counts, dtype="<i4").tobytes()


def encode_batch_ints(b: Batch) -> list[int]:
    head = [MAGIC, VERSION, b.n, b.seq, b.t_first_us, b.period_us, b.flags]
    return head + np.asarray(b.counts, dtype=np.int64).ravel().tolist()


class SequenceTracker:
    """Counts dropped batches from the u32 sequence number."""

    def __init__(self):
        self.last: int | None = None
        self.gaps = 0         # number of discontinuities
        self.missing = 0      # total batches lost
        self.restarts = 0     # sequence went backwards (MCU reset)
        self.duplicates = 0

    def update(self, seq: int) -> int:
        """Record `seq`; return how many batches were missed just before it."""
        missed = 0
        if self.last is not None:
            diff = (seq - self.last) % 2**32
            if diff == 0:
                self.duplicates += 1
                return 0
            if diff >= 2**31:
                self.restarts += 1
            elif diff > 1:
                missed = diff - 1
                self.gaps += 1
                self.missing += missed
        self.last = seq
        return missed
