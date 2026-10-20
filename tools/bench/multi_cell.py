#!/usr/bin/env python3
"""Guided test for several load cells on the shared ADS1220 bus (milestone M2 bring-up).

Flash bench/ads1220_all first (tools/bench/flash.sh bench/ads1220_all), then run:

    python tools/bench/multi_cell.py                       # plate L carrier: L1-L4
    python tools/bench/multi_cell.py --channels R          # plate R carrier: R1-R4
    python tools/bench/multi_cell.py --channels all        # both carriers
    python tools/bench/multi_cell.py --channels L1,R2      # any units, by name

For every unit it checks, in order:
  1. it answers on its own chip-select (register readback), and nothing answers on a CS
     that isn't in --channels
  2. its supply, reference and cell voltages (measured by the ADC itself), and whether
     R1/R2 are fitted; that picks the mode: differential if every unit has them, else
     single-ended
  3. an unloaded baseline: not stuck (a working ADS1220 always shows some noise), not
     noisy, not saturated, not drifting
  4. a press test, one cell at a time: the unit you press must move, and only that one.
     This catches cables on the wrong unit and crossed CS wires.

Prints PASS/FAIL per unit and saves a JSON copy to bench/results/ (git-ignored).
Offline: `python tools/bench/multi_cell.py --stdin < saved.log` checks a saved log.
"""

from __future__ import annotations

import argparse
import json
import signal
import statistics
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from single_cell import (
    DIFFERENTIAL,
    FULL_SCALE,
    MAX_NOISE_COUNTS,
    MIN_HEADROOM,
    SINGLE_ENDED,
    Mode,
    ModeLine,
    Monitor,
    SketchError,
    countdown,
    returned_to_baseline,
)

CHANNELS = ("L1", "L2", "L3", "L4", "R1", "R2", "R3", "R4")
CS_PIN = {
    "L1": "D3",
    "L2": "D4",
    "L3": "D5",
    "L4": "D6",
    "R1": "D7",
    "R2": "D8",
    "R3": "D9",
    "R4": "A2",
}
DEFAULT_CHANNELS = "L"  # one carrier per plate (docs/harness.md): plate L's is built first


def parse_channels(spec: str) -> list[str]:
    """'L' / 'R' -> that plate's four units, 'all' -> all eight, else names like 'L1,R2'.

    Parts combine ('L,R1'); duplicates are dropped. Raises ValueError on an unknown name.
    """
    out: list[str] = []
    for part in spec.replace(" ", "").split(","):
        name = part.upper()
        if name == "ALL":
            names = list(CHANNELS)
        elif name in ("L", "R"):
            names = [ch for ch in CHANNELS if ch[0] == name]
        elif name in CHANNELS:
            names = [name]
        else:
            raise ValueError(
                f"unknown channel {part!r}; use L, R, all or names from {', '.join(CHANNELS)}"
            )
        out += [ch for ch in names if ch not in out]
    return out
EXPECTED_RATE_HZ = 1000.0
STUCK_REPEAT_FRACTION = 0.5  # a working ADC repeats a value only occasionally
MAX_DRIFT = {"differential": 20_000, "single-ended": 1_000}  # counts over the baseline
CROSSTALK_FRACTION = 0.25  # another unit may move at most this much of the pressed one
AVDD_RANGE_MV = (3150, 3450)
MAX_REF_ERROR_MV = 60  # REFP0/REFN0 should sit on AVDD/GND
MAX_AIN0_OFFSET_MV = 250  # the cell's centre tap should be near half supply
R1R2_TOLERANCE_MV = 60  # AIN1 within this of half supply means R1/R2 are fitted
MAX_BRIDGE_OFFSET_MV = 20  # of the +-25.8 mV range at gain 128 (docs/wiring.md step 10)


# -- sketch output ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChanReadback:
    ch: str
    ok: bool
    regs: tuple[int, ...]


@dataclass(frozen=True)
class ChanStats:
    n: int
    mean: int
    std: int
    vmin: int
    vmax: int
    rep: int  # reads equal to the previous read of this channel


@dataclass(frozen=True)
class Window:
    ms: int
    ticks: int  # ticks the loop caught
    drdy: int  # L1 DRDY pulses (0 when L1 is absent and a timer paces)
    chans: dict[str, ChanStats]


@dataclass(frozen=True)
class ChanVoltage:
    ch: str
    name: str  # AVDD, AIN0, AIN1, REF
    value: str  # millivolts, or a message such as ">2048"


def parse_line(line: str):
    """One line of ads1220_all output -> ChanReadback | Window | ChanVoltage | ModeLine |
    SketchError | None."""
    parts = line.strip().split(",")
    try:
        if parts[0] == "R" and len(parts) == 7 and parts[1] in CHANNELS:
            return ChanReadback(parts[1], parts[2] == "1", tuple(int(p, 16) for p in parts[3:]))
        if parts[0] == "S" and len(parts) >= 4:
            chans = {}
            for item in parts[4:]:
                name, *vals = item.split(":")
                if name not in CHANNELS or len(vals) != 6:
                    return None
                chans[name] = ChanStats(*(int(v) for v in vals))
            return Window(int(parts[1]), int(parts[2]), int(parts[3]), chans)
        if parts[0] == "V" and len(parts) >= 4 and parts[1] in CHANNELS:
            return ChanVoltage(parts[1], parts[2], ",".join(parts[3:]))
        if parts[0] == "M" and len(parts) == 2:
            return ModeLine(parts[1])
        if parts[0] == "E" and len(parts) >= 2:
            return SketchError(",".join(parts[1:]))
    except ValueError:
        return None
    return None


def latest_readbacks(items) -> dict[str, ChanReadback]:
    out: dict[str, ChanReadback] = {}
    for i in items:
        if isinstance(i, ChanReadback):
            out[i.ch] = i
    return out


def windows_only(items) -> list[Window]:
    return [i for i in items if isinstance(i, Window)]


# -- analysis --------------------------------------------------------------------------------


def check_bus(readbacks: dict[str, ChanReadback], expected: list[str]) -> list[str]:
    """Problems with who answers on which chip-select."""
    problems = []
    for ch in expected:
        rb = readbacks.get(ch)
        if rb is None or not rb.ok:
            regs = " ".join(f"{r:02X}" for r in rb.regs) if rb else "no reply"
            problems.append(
                f"{ch} doesn't answer on CS {CS_PIN[ch]} (read {regs}): check that CS wire, "
                "and the unit's 3V3/GND/SCLK/MOSI/MISO taps"
            )
    for ch, rb in readbacks.items():
        if rb.ok and ch not in expected:
            problems.append(
                f"something answers on {ch}'s CS ({CS_PIN[ch]}) but {ch} isn't in --channels: "
                "a CS wire on the wrong UNO Q pin?"
            )
    return problems


def _mv(value: str) -> tuple[float | None, bool]:
    """'1654' -> (1654, False); '>2048' -> (2048, True); a message -> (None, False)."""
    if value.startswith(">"):
        return float(value[1:]), True
    try:
        return float(value), False
    except ValueError:
        return None, False


@dataclass
class VoltCheck:
    ok: bool
    avdd: float | None = None
    ain0: float | None = None
    ain1: float | None = None
    ref: float | None = None
    r1r2: bool = False
    problems: list[str] = field(default_factory=list)


def check_voltages(ch: str, volts: dict[str, str]) -> VoltCheck:
    """One unit's voltage check: supply, reference, cell centre tap, and R1/R2."""
    v = VoltCheck(True)
    if not volts:
        v.ok = False
        v.problems.append(f"{ch}: no voltage readings")
        return v
    v.avdd, _ = _mv(volts.get("AVDD", ""))
    v.ain0, ain0_sat = _mv(volts.get("AIN0", ""))
    v.ain1, ain1_sat = _mv(volts.get("AIN1", ""))
    ref_raw = volts.get("REF", "")
    v.ref, _ = _mv(ref_raw)
    lo, hi = AVDD_RANGE_MV
    if v.avdd is None or not lo <= v.avdd <= hi:
        v.problems.append(f"{ch}: supply {v.avdd} mV, expected {lo}-{hi} (3V3 and GND taps)")
    half = (v.avdd or 3300) / 2
    if ref_raw.startswith("<"):
        v.problems.append(f"{ch}: no reference: REFP0 -> 3V3 and REFN0 -> GND links missing")
    elif v.ref is not None and v.avdd is not None and abs(v.ref - v.avdd) > MAX_REF_ERROR_MV:
        v.problems.append(
            f"{ch}: reference {v.ref:.0f} mV vs supply {v.avdd:.0f} mV: check the REFP0/REFN0 links"
        )
    if v.ain0 is None:
        v.problems.append(f"{ch}: no AIN0 reading")
    elif ain0_sat or abs(v.ain0 - half) > MAX_AIN0_OFFSET_MV:
        v.problems.append(
            f"{ch}: cell centre tap (AIN0) {'>' if ain0_sat else ''}{v.ain0:.0f} mV, expected "
            f"~{half:.0f}: check the S wire (red) on (x0+2, P), and that the cable's E+/E- reach "
            "3V3/GND. At the rail usually means S and E+/E- are swapped at the JST"
        )
    v.r1r2 = v.ain1 is not None and not ain1_sat and abs(v.ain1 - half) <= R1R2_TOLERANCE_MV
    if v.r1r2 and v.ain0 is not None and abs(v.ain0 - v.ain1) > MAX_BRIDGE_OFFSET_MV:
        v.problems.append(
            f"{ch}: bridge offset {v.ain0 - v.ain1:+.0f} mV (AIN0 - AIN1) is more than "
            f"{MAX_BRIDGE_OFFSET_MV} mV and uses up the +-25.8 mV range at gain 128"
        )
    v.ok = not v.problems
    return v


def choose_mode(checks: dict[str, VoltCheck], forced: str | None) -> tuple[Mode, str]:
    """Differential only if every unit has R1/R2 (the mode is shared by all boards)."""
    if forced == "differential":
        return DIFFERENTIAL, "--mode differential"
    if forced == "single-ended":
        return SINGLE_ENDED, "--mode single-ended"
    missing = [ch for ch, c in checks.items() if not c.r1r2]
    if checks and not missing:
        return DIFFERENTIAL, "R1/R2 found on every unit"
    return SINGLE_ENDED, (
        f"R1/R2 not found on {', '.join(missing)}" if missing else "no voltage readings"
    )


@dataclass
class ChanBaseline:
    ok: bool
    mean: float = 0.0
    noise: float = 0.0
    drift: float = 0.0
    repeat_fraction: float = 0.0
    problems: list[str] = field(default_factory=list)


def check_channel(ch: str, windows: list[Window], mode: Mode) -> ChanBaseline:
    """One unit, unloaded: not stuck, not noisy, not saturated, not drifting."""
    ws = [w.chans[ch] for w in windows if ch in w.chans]
    if not ws:
        return ChanBaseline(False, problems=[f"{ch}: no readings (dropped off the bus?)"])
    total = sum(s.n for s in ws)
    b = ChanBaseline(True)
    b.mean = sum(s.mean * s.n for s in ws) / total
    b.noise = statistics.median(s.std for s in ws)
    b.drift = ws[-1].mean - ws[0].mean
    b.repeat_fraction = sum(s.rep for s in ws) / total
    # A reading pinned at full scale is constant too; report that as saturation, not as stuck.
    pinned = all(s.vmax >= FULL_SCALE - 1 or s.vmin <= -FULL_SCALE for s in ws)
    if not pinned and (b.repeat_fraction > STUCK_REPEAT_FRACTION or b.noise < 1):
        b.problems.append(
            f"{ch}: readings are stuck ({100 * b.repeat_fraction:.0f} % repeat the previous value, "
            f"noise {b.noise:.0f}). A working ADS1220 always shows some noise; this is the fault "
            "seen on the second breakout (docs/VERIFIED.md). Swap the breakout to confirm"
        )
    elif b.noise > MAX_NOISE_COUNTS:
        b.problems.append(
            f"{ch}: noisy, {b.noise:,.0f} counts per sample: loose or unshielded wire?"
        )
    saturated = any(s.vmax >= FULL_SCALE - 1 or s.vmin <= -FULL_SCALE for s in ws)
    if saturated or FULL_SCALE - abs(b.mean) < MIN_HEADROOM * FULL_SCALE:
        b.problems.append(
            f"{ch}: reading {b.mean:,.0f} is at or near full scale"
            + (": R1/R2 missing or the bridge badly unbalanced" if mode is DIFFERENTIAL else "")
        )
    if abs(b.drift) > MAX_DRIFT[mode.name]:
        b.problems.append(f"{ch}: drifted {b.drift:+,.0f} counts while unloaded (hands off?)")
    b.ok = not b.problems
    return b


@dataclass
class Rate:
    ok: bool
    rate_hz: float = 0.0
    captured: float = 0.0  # fraction of conversions the loop read
    problems: list[str] = field(default_factory=list)


def check_rate(windows: list[Window]) -> Rate:
    """L1's conversion rate (the pacing clock) and how much of it the loop caught."""
    if len(windows) < 2:
        return Rate(False, problems=["no data from the sketch"])
    drdy = sum(w.drdy for w in windows)
    ticks = sum(w.ticks for w in windows)
    seconds = (windows[-1].ms - windows[0].ms) / 1000 * len(windows) / (len(windows) - 1)
    r = Rate(True)
    if drdy == 0:  # L1 absent: a 1 ms timer paces, nothing to check against
        r.rate_hz = ticks / seconds
        r.captured = 1.0
        return r
    r.rate_hz = drdy / seconds
    r.captured = ticks / drdy
    if abs(r.rate_hz - EXPECTED_RATE_HZ) > 0.1 * EXPECTED_RATE_HZ:
        r.problems.append(
            f"L1 converts at {r.rate_hz:.0f} Hz, expected ~{EXPECTED_RATE_HZ:.0f}: "
            "check L1's DRDY -> D2"
        )
    r.ok = not r.problems
    return r


@dataclass
class PressResult:
    target: str
    ok: bool
    deltas: dict[str, float]
    released: bool = True
    problem: str = ""


def attribute_press(
    target: str, base_means: dict[str, float], windows: list[Window], min_delta: float
) -> PressResult:
    """Pressing `target` must move `target`, and nothing else by more than a quarter as much."""
    deltas: dict[str, float] = {}
    for ch, base in base_means.items():
        moves = [w.chans[ch].mean - base for w in windows if ch in w.chans]
        deltas[ch] = max(moves, key=abs) if moves else 0.0
    if not deltas:
        return PressResult(target, False, deltas, problem="no data from the sketch")
    mine = abs(deltas.get(target, 0.0))
    others = {ch: d for ch, d in deltas.items() if ch != target}
    biggest = max(deltas, key=lambda ch: abs(deltas[ch]))
    if mine >= min_delta and all(abs(d) < CROSSTALK_FRACTION * mine for d in others.values()):
        return PressResult(target, True, deltas)
    if biggest != target and abs(deltas[biggest]) >= min_delta:
        problem = (
            f"you pressed {target} but {biggest} moved ({deltas[biggest]:+,.0f} counts): "
            f"{target} and {biggest} are swapped, either the cell cables go to the wrong units "
            "or the CS wires are crossed"
        )
    elif mine >= min_delta:
        moved = ", ".join(
            f"{ch} {d:+,.0f}" for ch, d in others.items() if abs(d) >= CROSSTALK_FRACTION * mine
        )
        problem = (
            f"{target} moved ({deltas[target]:+,.0f}) but so did {moved}: two cells pressed at "
            "once, or cables sharing a strip (check the row P cuts)"
        )
    else:
        problem = (
            f"{target} didn't respond ({deltas.get(target, 0.0):+,.0f} counts, need "
            f"{min_delta:,.0f}): check its cable's S wire (red) and the JST at the cradle"
        )
    return PressResult(target, False, deltas, problem=problem)


@dataclass
class Report:
    expected: list[str]
    bus_problems: list[str] = field(default_factory=list)
    readbacks: dict[str, ChanReadback] = field(default_factory=dict)
    volts: dict[str, VoltCheck] = field(default_factory=dict)
    mode: str = ""
    mode_reason: str = ""
    rate: Rate | None = None
    baselines: dict[str, ChanBaseline] = field(default_factory=dict)
    presses: dict[str, PressResult] = field(default_factory=dict)

    def unit_ok(self, ch: str) -> bool:
        rb = self.readbacks.get(ch)
        parts = [rb is not None and rb.ok]
        if ch in self.volts:
            parts.append(self.volts[ch].ok)
        if ch in self.baselines:
            parts.append(self.baselines[ch].ok)
        if ch in self.presses:
            parts.append(self.presses[ch].ok and self.presses[ch].released)
        return all(parts)

    def ok(self) -> bool:
        return (
            not self.bus_problems
            and all(self.unit_ok(ch) for ch in self.expected)
            and (self.rate is None or self.rate.ok)
        )


def summarize(rep: Report) -> str:
    out = [
        "",
        f"Result ({rep.mode or 'mode unknown'}{': ' + rep.mode_reason if rep.mode_reason else ''})",
    ]
    out.append(f"  {'unit':5}{'readback':10}{'volts':8}{'baseline':28}{'press':8}")
    for ch in rep.expected:
        rb = rep.readbacks.get(ch)
        v = rep.volts.get(ch)
        b = rep.baselines.get(ch)
        p = rep.presses.get(ch)
        base = (
            f"{'ok' if b.ok else 'FAIL'} noise {b.noise:,.0f}, rep {100 * b.repeat_fraction:.0f}%"
            if b
            else "-"
        )
        press = "-" if p is None else ("ok" if p.ok and p.released else "FAIL")
        volts = "-" if v is None else ("ok" if v.ok else "FAIL")
        volts += " R" if v and v.r1r2 else ""
        out.append(
            f"  {ch:5}{'ok' if rb and rb.ok else 'FAIL':10}{volts:8}{base:28}{press:8}"
            f"{'PASS' if rep.unit_ok(ch) else 'FAIL'}"
        )
    problems = list(rep.bus_problems)
    for ch in rep.expected:
        if ch in rep.volts:
            problems += rep.volts[ch].problems
        if ch in rep.baselines:
            problems += rep.baselines[ch].problems
        p = rep.presses.get(ch)
        if p and p.problem:
            problems.append(p.problem)
        if p and p.ok and not p.released:
            problems.append(f"{ch}: didn't return to baseline after letting go (rubbing or loose?)")
    if rep.rate:
        problems += rep.rate.problems
        if rep.rate.rate_hz:
            out.append(
                f"  pacing: {rep.rate.rate_hz:.0f} Hz, loop read "
                f"{100 * rep.rate.captured:.0f} % of "
                "conversions (Monitor output blocks the bench loop; the real firmware batches)"
            )
    out.append("  (R = R1/R2 detected)")
    if problems:
        out.append("")
        out += [f"  - {p}" for p in problems]
    out.append("")
    failed = [ch for ch in rep.expected if not rep.unit_ok(ch)]
    if rep.ok():
        out.append(f"  PASS: {len(rep.expected)} unit(s)")
    elif failed:
        out.append(f"  FAIL: {', '.join(failed)} ({len(failed)} of {len(rep.expected)} units)")
    else:
        out.append("  FAIL: shared bus or pacing (see above)")
    return "\n".join(out)


# -- live session ------------------------------------------------------------------------------


def run_live(args) -> int:
    try:
        expected = parse_channels(args.channels or DEFAULT_CHANNELS)
    except ValueError as e:
        print(f"--channels: {e}")
        return 2
    mon = Monitor(args.host, parse=parse_line)
    rep = Report(expected)
    try:
        print(f"Connecting to arduino@{args.host} (arduino-app-cli monitor)...")
        # Keys sent before the monitor is attached are lost: wait for the sketch's first output.
        for _ in range(20):
            if mon.collect(0.5):
                break
        mon.send("r")
        items = mon.collect(4.0)
        rep.readbacks = latest_readbacks(items)
        if not rep.readbacks:
            print(
                "No readback from the sketch. Is bench/ads1220_all flashed "
                "(tools/bench/flash.sh bench/ads1220_all), and is the board on the network?"
            )
            return 2
        rep.bus_problems = check_bus(rep.readbacks, expected)
        present = [ch for ch in expected if rep.readbacks.get(ch) and rep.readbacks[ch].ok]
        answering = [ch for ch, rb in rep.readbacks.items() if rb.ok]
        print(f"  answering: {', '.join(answering) or 'none'}")
        if not present:
            print(summarize(rep))
            print(
                "\nStopping: no expected unit answers. Check the shared wires first: 3V3, GND, "
                "SCLK (D13), MOSI (D11), MISO (D12) from the UNO Q to BUS IN."
            )
            return 1

        print("Voltage check (each ADC measures its own supply, reference and cell)...")
        mon.send("v")
        volts: dict[str, dict[str, str]] = {}
        for i in mon.collect(3.0 + 0.6 * len(answering)):
            if isinstance(i, ChanVoltage):
                volts.setdefault(i.ch, {})[i.name] = i.value
        for ch in present:
            rep.volts[ch] = check_voltages(ch, volts.get(ch, {}))
            v = rep.volts[ch]
            print(
                f"  {ch}: AVDD {v.avdd}, REF {v.ref}, AIN0 {v.ain0}, AIN1 {v.ain1} mV"
                f"{'  (R1/R2 fitted)' if v.r1r2 else ''}"
            )
        mode, rep.mode_reason = choose_mode(rep.volts, args.mode)
        rep.mode = mode.name
        print(f"Measuring {mode.name} ({rep.mode_reason}).")
        mon.send(mode.command)
        mon.collect(2.0)  # re-configure and settle

        countdown(
            "Baseline: take everything off the cells and don't touch them, the wires or the table."
        )
        print(f"  Recording {args.baseline_s:.0f} s...")
        base_w = windows_only(mon.collect(args.baseline_s))
        rep.rate = check_rate(base_w)
        for ch in present:
            rep.baselines[ch] = check_channel(ch, base_w, mode)
            b = rep.baselines[ch]
            print(
                f"  {ch}: mean {b.mean:,.0f}, noise {b.noise:,.0f}, "
                f"repeats {100 * b.repeat_fraction:.0f} %"
            )

        if not args.no_press:
            means = {ch: b.mean for ch, b in rep.baselines.items()}
            for ch in present:
                countdown(
                    f"Press test {present.index(ch) + 1}/{len(present)}: when you press Enter, "
                    f"push firmly on cell {ch}'s strap\n  for ~2 s, then let go. Only that cell."
                )
                print("  Press now...")
                press_w = windows_only(mon.collect(5.0))
                result = attribute_press(ch, means, press_w, mode.press_delta)
                release_w = windows_only(mon.collect(2.0))
                if result.ok:
                    result.released = returned_to_baseline(
                        means[ch],
                        [w.chans[ch] for w in release_w if ch in w.chans],
                        result.deltas[ch],
                        floor=mode.press_delta / 4,
                        drift=rep.baselines[ch].drift,
                    )
                rep.presses[ch] = result
                print(
                    f"  {'ok' if result.ok else 'FAIL'}: {result.deltas.get(ch, 0):+,.0f} counts"
                    + (f"  ({result.problem})" if result.problem else "")
                )

        print(summarize(rep))
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"multi-{'-'.join(expected)}-{datetime.now():%Y%m%d-%H%M%S}.json"
        path.write_text(
            json.dumps(
                {
                    "date": datetime.now().isoformat(timespec="seconds"),
                    "report": asdict(rep),
                    "baseline_windows": [asdict(w) for w in base_w],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            f"\nSaved {path}.\nRecord each unit's noise in docs/VERIFIED.md (Bench measurements)."
        )
        return 0 if rep.ok() else 1
    finally:
        mon.close()


def run_stdin(channels: str | None) -> int:
    """Check a saved log; with no `channels`, expect the units that answered in it."""
    try:
        expected_set = parse_channels(channels) if channels else None
    except ValueError as e:
        print(f"--channels: {e}")
        return 2
    items = [i for i in (parse_line(line) for line in sys.stdin) if i is not None]
    readbacks = latest_readbacks(items)
    expected = (
        [ch for ch, rb in readbacks.items() if rb.ok] if expected_set is None else expected_set
    )
    modes = [i.name for i in items if isinstance(i, ModeLine)]
    mode = SINGLE_ENDED if modes and modes[-1] == "single-ended" else DIFFERENTIAL
    rep = Report(expected, readbacks=readbacks, mode=mode.name, mode_reason="from the log")
    rep.bus_problems = check_bus(readbacks, expected)
    windows = windows_only(items)
    rep.rate = check_rate(windows)
    for ch in expected:
        rep.baselines[ch] = check_channel(ch, windows, mode)
    print(summarize(rep))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--host", default="open-fp.local")
    ap.add_argument(
        "--channels",
        default=None,
        help="units to test: L or R (a plate's four), all, or names like L1,R2 "
        "(default: L, the plate L carrier; with --stdin, the units that answered in the log)",
    )
    ap.add_argument(
        "--mode",
        choices=("differential", "single-ended"),
        default=None,
        help="force a mode (default: differential if every unit has R1/R2, else single-ended)",
    )
    ap.add_argument("--baseline-s", type=float, default=5.0)
    ap.add_argument("--no-press", action="store_true", help="skip the press tests")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "bench" / "results"))
    ap.add_argument("--stdin", action="store_true", help="analyse a saved log from stdin instead")
    args = ap.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        if args.stdin:
            return run_stdin(args.channels)
        return run_live(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
