#!/usr/bin/env python3
"""Guided test for one load cell on one ADS1220 (milestone M1).

Flash bench/ads1220_single first (tools/bench/flash.sh), then run on the dev machine:

    python tools/bench/single_cell.py                 # readback, noise, press test
    python tools/bench/single_cell.py --mass-kg 2.0   # also measure counts per kg

It streams the sketch's output with `arduino-app-cli monitor` over SSH, walks you through
the steps, and prints PASS/FAIL with numbers to record in docs/VERIFIED.md. A JSON copy of
the results is written to bench/results/ (git-ignored).

Offline: `python tools/bench/single_cell.py --stdin < saved.log` checks a saved log.
"""

from __future__ import annotations

import argparse
import json
import queue
import statistics
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

FULL_SCALE = 8_388_607  # 24-bit ADC, counts
EXPECTED_RATE_HZ = 1000.0
MAX_NOISE_COUNTS = 5_000  # per-sample std at 1000 SPS; a few hundred is typical
MAX_DRIFT_COUNTS = 20_000  # over the baseline window
MIN_HEADROOM = 0.10  # keep the unloaded reading within 90 % of full scale
PRESS_DELTA_COUNTS = 20_000  # a firm thumb press is far more than this
COUNTS_PER_KG_RANGE = (3_000, 60_000)


@dataclass(frozen=True)
class Mode:
    """How the sketch is measuring, and the thresholds that go with it."""

    name: str
    command: str  # keystroke that switches the sketch into this mode (and re-checks the ADC)
    regs: tuple[int, ...]  # config registers the readback should match
    press_delta: float  # counts a firm thumb press should exceed
    cpk_range: tuple[float, float]  # plausible counts per kg


# AIN0 - AIN1, gain 128: the real configuration, needs R1/R2 on AIN1.
DIFFERENTIAL = Mode(
    "differential", "d", (0x0E, 0xC4, 0x40, 0x00), PRESS_DELTA_COUNTS, COUNTS_PER_KG_RANGE
)
# AIN0 - AVSS, gain 1, PGA bypassed: tests wiring and response before R1/R2 are fitted.
# The signal sits at ~half scale and moves ~85-170 counts/kg, so thresholds are ~128x smaller.
SINGLE_ENDED = Mode("single-ended", "s", (0x81, 0xC4, 0x40, 0x00), 150, (20, 600))


# -- sketch output ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Readback:
    ok: bool
    regs: tuple[int, ...]


@dataclass(frozen=True)
class Stats:
    ms: int
    n: int  # samples the loop captured
    mean: int
    std: int
    vmin: int
    vmax: int
    drdy: int | None = None  # conversions the ADC signalled (interrupt count), if reported


@dataclass(frozen=True)
class SketchError:
    message: str


def parse_line(line: str):
    """One line of ads1220_single output -> Readback | Stats | SketchError | None."""
    line = line.strip()
    parts = line.split(",")
    try:
        if parts[0] == "R" and len(parts) == 6:
            return Readback(parts[1] == "1", tuple(int(p, 16) for p in parts[2:]))
        if parts[0] == "S" and len(parts) in (7, 8):
            return Stats(*(int(p) for p in parts[1:]))
        if parts[0] == "E" and len(parts) >= 2:
            return SketchError(",".join(parts[1:]))
    except ValueError:
        return None
    return None


# -- analysis --------------------------------------------------------------------------------


@dataclass
class Baseline:
    ok: bool
    mean: float = 0.0
    noise: float = 0.0
    drift: float = 0.0
    rate_hz: float = 0.0
    headroom: float = 0.0
    problems: list[str] = field(default_factory=list)


def check_baseline(windows: list[Stats]) -> Baseline:
    """Unloaded cell: sample rate, noise, drift and distance from full scale."""
    if not windows:
        return Baseline(False, problems=["no data from the sketch"])
    total_n = sum(w.n for w in windows)
    duration_s = (windows[-1].ms - windows[0].ms) / 1000 + 0.1
    b = Baseline(True)
    # The ADC's own rate: DRDY pulses if the sketch counts them, else samples captured.
    conversions = sum(w.drdy if w.drdy is not None else w.n for w in windows)
    b.rate_hz = conversions / duration_s
    b.mean = sum(w.mean * w.n for w in windows) / total_n
    b.noise = statistics.median(w.std for w in windows)
    b.drift = windows[-1].mean - windows[0].mean
    b.headroom = FULL_SCALE - abs(b.mean)
    if abs(b.rate_hz - EXPECTED_RATE_HZ) > 0.1 * EXPECTED_RATE_HZ:
        b.problems.append(
            f"sample rate {b.rate_hz:.0f} Hz, expected ~{EXPECTED_RATE_HZ:.0f} Hz "
            "(DRDY or register config)"
        )
    saturated = any(w.vmax >= FULL_SCALE - 1 or w.vmin <= -FULL_SCALE for w in windows)
    if saturated or b.headroom < MIN_HEADROOM * FULL_SCALE:
        b.problems.append(
            f"reading {b.mean:,.0f} is at or near full scale: the bridge is badly "
            "unbalanced (check S -> AIN0, R1/R2 -> AIN1, E+/E-)"
        )
    if b.noise > MAX_NOISE_COUNTS:
        b.problems.append(
            f"noisy: {b.noise:,.0f} counts per sample (expect a few hundred); "
            "look for a loose or long unshielded wire"
        )
    if abs(b.drift) > MAX_DRIFT_COUNTS:
        b.problems.append(
            f"drift of {b.drift:,.0f} counts while unloaded (let it warm up, "
            "and don't touch the cell or wires)"
        )
    b.ok = not b.problems
    return b


@dataclass
class Press:
    pressed: bool
    delta: float = 0.0
    sign: int = 0


def detect_press(
    baseline_mean: float, windows: list[Stats], min_delta: float = PRESS_DELTA_COUNTS
) -> Press:
    """Did the reading move clearly away from the baseline? Reports the biggest move."""
    if not windows:
        return Press(False)
    peak = max(windows, key=lambda w: abs(w.mean - baseline_mean))
    delta = peak.mean - baseline_mean
    return Press(abs(delta) >= min_delta, delta, 1 if delta > 0 else -1)


def returned_to_baseline(
    baseline_mean: float, windows: list[Stats], press_delta: float, floor: float = 5_000
) -> bool:
    """After letting go, the reading should settle back to within 5 % of the press (or `floor`)."""
    if not windows:
        return False
    tail = windows[-5:]
    settled = statistics.median(w.mean for w in tail)
    return abs(settled - baseline_mean) <= max(floor, 0.05 * abs(press_delta))


@dataclass
class Scale:
    ok: bool
    counts_per_kg: float
    delta: float


def scale_from_mass(
    baseline_mean: float,
    windows: list[Stats],
    mass_kg: float,
    cpk_range: tuple[float, float] = COUNTS_PER_KG_RANGE,
) -> Scale:
    """Counts per kg from a known mass, using the steadier second half of the window."""
    steady = windows[len(windows) // 2 :] or windows
    delta = statistics.median(w.mean for w in steady) - baseline_mean
    cpk = abs(delta) / mass_kg
    lo, hi = cpk_range
    return Scale(lo <= cpk <= hi, cpk, delta)


def summarize(
    readback: Readback | None,
    base: Baseline | None,
    press: Press | None,
    scale: Scale | None,
    mode: Mode = DIFFERENTIAL,
) -> str:
    def line(ok, label, detail=""):
        return f"  {'PASS' if ok else 'FAIL'}  {label}{': ' + detail if detail else ''}"

    out = ["", "Result"]
    if readback is None:
        out.append(line(False, "register readback", "no R line from the sketch"))
    else:
        regs = _hex(readback.regs)
        out.append(
            line(
                readback.ok,
                "register readback",
                regs + ("" if readback.ok else f" (expected {_hex(mode.regs)})"),
            )
        )
    if base is not None and base.rate_hz == 0:
        out.append(line(False, "unloaded baseline", "no data from the sketch"))
    elif base is not None:
        out.append(
            line(
                base.ok,
                "unloaded baseline",
                f"mean {base.mean:,.0f}, noise {base.noise:,.0f} counts, drift {base.drift:,.0f}, "
                f"{base.rate_hz:.0f} Hz, headroom {100 * base.headroom / FULL_SCALE:.0f} %",
            )
        )
        out += [f"        - {p}" for p in base.problems]
    if press is not None:
        out.append(
            line(
                press.pressed,
                "press test",
                f"moved {press.delta:+,.0f} counts "
                f"({'rises' if press.sign > 0 else 'falls'} under load)"
                if press.pressed
                else "no clear change: check the S wire and that you pressed the strap",
            )
        )
    if scale is not None:
        lo, hi = mode.cpk_range
        out.append(
            line(
                scale.ok,
                "known mass",
                f"{scale.counts_per_kg:,.0f} counts/kg (plausible range {lo:,}-{hi:,})",
            )
        )
    return "\n".join(out)


def _hex(regs) -> str:
    return " ".join(f"{r:02X}" for r in regs)


# -- live session ------------------------------------------------------------------------------


class Monitor:
    """Streams and parses `arduino-app-cli monitor` output from the board over SSH."""

    def __init__(self, host: str, source=None):
        self.q: queue.Queue = queue.Queue()
        self.proc = None
        if source is None:
            # Long-lived: the stream is read by a thread until close() terminates it.
            self.proc = subprocess.Popen(  # pylint: disable=consider-using-with
                ["ssh", "-o", "BatchMode=yes", f"arduino@{host}", "arduino-app-cli", "monitor"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            source = self.proc.stdout
        threading.Thread(target=self._pump, args=(source,), daemon=True).start()

    def _pump(self, stream):
        seen: set[str] = set()
        for raw in stream:
            item = parse_line(raw)
            if isinstance(item, SketchError) and item.message not in seen:
                seen.add(item.message)  # the sketch repeats errors; show each one once
                print(f"  sketch: {item.message}")
            if item is not None:
                self.q.put(item)
        self.q.put(None)

    def send(self, text: str):
        if self.proc and self.proc.stdin:
            self.proc.stdin.write(text)
            self.proc.stdin.flush()

    def collect(self, seconds: float) -> list:
        items, end = [], time.monotonic() + seconds
        while (left := end - time.monotonic()) > 0:
            try:
                item = self.q.get(timeout=left)
            except queue.Empty:
                break
            if item is None:
                break
            items.append(item)
        return items

    def close(self):
        if self.proc:
            self.proc.terminate()


def stats_only(items):
    return [i for i in items if isinstance(i, Stats)]


def countdown(prompt: str):
    input(f"\n{prompt}\n  Press Enter when ready...")


def run_live(args) -> int:
    mon = Monitor(args.host)
    results: dict = {"cell": args.cell, "date": datetime.now().isoformat(timespec="seconds")}
    try:
        print(f"Connecting to arduino@{args.host} (arduino-app-cli monitor)...")
        mode = SINGLE_ENDED if args.single_ended else DIFFERENTIAL
        print(f"Measuring {mode.name}.")
        mon.send(mode.command)  # switch mode, reset the ADC, print its readback
        items = mon.collect(6.0)
        readbacks = [i for i in items if isinstance(i, Readback)]
        readback = readbacks[-1] if readbacks else None
        if not stats_only(items) and not readbacks:
            print(
                "No output from the sketch. Is bench/ads1220_single flashed, "
                "and is the board on the network?"
            )
            return 2
        if readback is None or not readback.ok:
            print(summarize(readback, None, None, None, mode))
            print(
                "\nStopping: the ADC must read back its registers before the other steps mean "
                "anything.\nCheck the wiring against docs/bench-single-cell.md (step 4 and "
                "Troubleshooting), then rerun."
            )
            return 1

        countdown(
            "Step 1/3 - baseline. Take everything off the cell and don't touch it or its wires."
        )
        print(f"  Recording {args.baseline_s:.0f} s...")
        base = check_baseline(stats_only(mon.collect(args.baseline_s)))
        print(f"  mean {base.mean:,.0f}, noise {base.noise:,.0f} counts, {base.rate_hz:.0f} Hz")

        countdown(
            "Step 2/3 - press test. When you press Enter, push firmly on the strap\n"
            "  with your thumb for ~2 s, then let go.\n"
            "  (Support the cell by its outer frame, e.g. in the cradle.)"
        )
        print("  Press now...")
        press = detect_press(base.mean, stats_only(mon.collect(6.0)), mode.press_delta)
        released = returned_to_baseline(
            base.mean, stats_only(mon.collect(2.0)), press.delta, floor=mode.press_delta / 4
        )
        if press.pressed and not released:
            base.problems.append(
                "didn't return to baseline after letting go (cell rubbing or loose)"
            )
            base.ok = False

        scale = None
        if args.mass_kg:
            countdown(
                f"Step 3/3 - known mass. Place the {args.mass_kg} kg mass on the strap\n"
                "  (frame supported), hands off, then press Enter."
            )
            print("  Recording 5 s...")
            scale = scale_from_mass(
                base.mean, stats_only(mon.collect(5.0)), args.mass_kg, mode.cpk_range
            )

        print(summarize(readback, base, press, scale, mode))
        results.update(
            readback=asdict(readback) if readback else None,
            baseline=asdict(base),
            press=asdict(press),
            scale=asdict(scale) if scale else None,
        )
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{args.cell}-{datetime.now():%Y%m%d-%H%M%S}.json"
        path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(
            f"\nSaved {path}.\nRecord the baseline and noise in docs/VERIFIED.md "
            "(Bench measurements)."
        )
        ok = bool(
            readback and readback.ok and base.ok and press.pressed and (scale is None or scale.ok)
        )
        return 0 if ok else 1
    finally:
        mon.close()


def run_stdin() -> int:
    items = [i for i in (parse_line(line) for line in sys.stdin) if i is not None]
    readbacks = [i for i in items if isinstance(i, Readback)]
    print(
        summarize(
            readbacks[-1] if readbacks else None, check_baseline(stats_only(items)), None, None
        )
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--host", default="open-fp.local")
    ap.add_argument("--cell", default="L1", help="label for the results file")
    ap.add_argument(
        "--mass-kg", type=float, default=None, help="known test mass for a counts/kg check"
    )
    ap.add_argument(
        "--single-ended",
        action="store_true",
        help="measure AIN0 against ground (gain 1): tests wiring before R1/R2 are fitted",
    )
    ap.add_argument("--baseline-s", type=float, default=10.0)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "bench" / "results"))
    ap.add_argument("--stdin", action="store_true", help="analyse a saved log from stdin instead")
    args = ap.parse_args()
    try:
        return run_stdin() if args.stdin else run_live(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
