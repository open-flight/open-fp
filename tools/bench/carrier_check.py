#!/usr/bin/env python3
"""Guided multimeter check of an ADC carrier before it's powered (docs/harness.md §4).

    python tools/bench/carrier_check.py                          # toe carrier: L1, L2, R1, R2
    python tools/bench/carrier_check.py --units L1               # one unit fitted so far
    python tools/bench/carrier_check.py --stage bare             # just the cut board and links

Nothing is powered: the UNO Q is unplugged (or not wired yet). The script asks for one reading
at a time. Type what the meter shows: a resistance like `498`, `1.02k` or `OL` (open), or
`y`/`n` for a continuity beep, or `s` to skip. It says PASS/FAIL with what to look at, then
prints a summary and saves it to bench/results/.

Stages, in build order (each includes the ones before it):
  bare     cuts and links done, no breakouts: rails isolated from each other
  units    breakouts and R1/R2 fitted: supply resistance, bus continuity to each breakout
  cables   cell cables soldered and JSTs plugged in at the cradles: the cells show up
  uno      carrier wired to the UNO Q (Q unplugged from USB): the Q's pins reach the right places

Then power up and run tools/bench/multi_cell.py.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

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
TOE = ("L1", "L2", "R1", "R2")
STAGES = ("bare", "units", "cables", "uno")
R_EACH = 1_000.0  # R1 = R2, ohms (any matched pair 680 Ω-2 kΩ; set with --resistor)
R_CELL = 2_000.0  # the cell's E+ to E- (docs/wiring.md: 2 kΩ, 1 kΩ per corner with R1+R2)
OPEN = float("inf")


@dataclass(frozen=True)
class Check:
    stage: str
    what: str  # where to put the probes
    expect: str  # "open", "beep", "ohms", or "yes" (look and confirm)
    lo: float = 0.0  # for "ohms"
    hi: float = 0.0
    hint: str = ""  # what to look at if it fails


def parse_reading(text: str) -> float | bool | None:
    """'498' / '1.02k' / '2M' -> ohms; 'OL' -> inf; 'y'/'n' -> bool; 's' or junk -> None."""
    t = text.strip().lower().replace("ω", "").replace("ohm", "").replace(" ", "")
    if t in ("y", "yes", "beep"):
        return True
    if t in ("n", "no"):
        return False
    if t in ("ol", "open", "o.l", "o.l.", "1"):  # many meters show "1" or "OL" when open
        return OPEN
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([km]?)", t)
    if not m:
        return None
    return float(m[1]) * {"": 1, "k": 1e3, "m": 1e6}[m[2]]


def judge(check: Check, reading: float | bool) -> bool:
    if check.expect == "yes":
        return reading is True
    if check.expect == "beep":
        return reading is True or (isinstance(reading, float) and reading < 5)
    if check.expect == "open":
        return reading is False or (isinstance(reading, float) and reading > 100_000)
    if isinstance(reading, bool):
        return False
    return check.lo <= reading <= check.hi


def parallel(r: float, n: int) -> float:
    return r / n


def checks_for(
    units: list[str], stage: str, heel_chained: bool = False, r_each: float = R_EACH
) -> list[Check]:
    """Every check up to and including `stage`, in build order."""
    upto = STAGES[: STAGES.index(stage) + 1]
    n = len(units)
    out: list[Check] = []
    if "bare" in upto:
        out += [
            Check(
                "bare",
                "BUS IN strip A (GND) to strip B (3V3)",
                "open",
                hint="a solder bridge between strips A and B, or a link landing on the wrong strip",
            ),
            Check(
                "bare",
                "strip B (3V3) to strip N (3V3 for the cables)",
                "beep",
                hint="the tie link in column 19 (B to N)",
            ),
            Check(
                "bare",
                "strip A (GND) to strip O (GND for the cables)",
                "beep",
                hint="the tie link in column 10 (A to O)",
            ),
        ]
        for rail, strip in (("SCLK", "J"), ("MOSI", "K"), ("MISO", "L")):
            out.append(
                Check(
                    "bare",
                    f"strip {strip} ({rail}) to strip A (GND)",
                    "open",
                    hint=f"a solder bridge on strip {strip}",
                )
            )
            out.append(
                Check(
                    "bare",
                    f"strip {strip} ({rail}) to strip B (3V3)",
                    "open",
                    hint=f"a solder bridge on strip {strip}",
                )
            )
        out += [
            Check(
                "bare",
                "strip J (SCLK) to strip K (MOSI), and K to L (MISO)",
                "open",
                hint="neighbouring rails bridged",
            ),
            Check(
                "bare",
                "strip P between two neighbouring units (e.g. column 3 to column 12)",
                "open",
                hint="a missed row P cut: each unit's S must be separate",
            ),
            Check(
                "bare",
                "strip P (any unit) to strip O (GND) and to strip N (3V3)",
                "open",
                hint="a solder bridge next to row P",
            ),
        ]
    if "units" in upto:
        r_pair = 2 * r_each
        r = parallel(r_pair, n)
        # AIN1 to AGND: R2 in parallel with R1 plus the rest of the 3V3-GND network
        rest = r_pair / (n - 1) if n > 1 else float("inf")
        ain1 = 1 / (1 / r_each + 1 / (r_each + rest))
        out.append(
            Check(
                "units",
                f"strip B (3V3) to strip A (GND), no cells plugged in: {n} x (R1 + R2) in parallel",
                "ohms",
                0.6 * r,
                1.15 * r,
                hint=f"expect ~{r:.0f} Ω once the reading settles (the capacitors charge; a power "
                "LED on the breakouts reads lower). Near 0: a short. Higher: an R1/R2 missing or unsoldered "
                f"(measure each unit's AVDD to AGND pins on top: ~{r_pair:.0f} Ω)",
            )
        )
        for u in units:
            out += [
                Check(
                    "units",
                    f"{u}: AIN1 pin (on top) to AGND pin: R2, with R1 and the rest in parallel",
                    "ohms",
                    0.7 * ain1,
                    1.1 * ain1,
                    hint=f"expect ~{ain1:.0f} Ω. R2 missing or on the wrong pin "
                    "(R1 AVDD-AIN1, R2 AIN1-AGND), or R1/R2 not the same value",
                ),
                Check(
                    "units",
                    f"{u}: SCLK pin (on top) to BUS IN strip J",
                    "beep",
                    hint=f"{u}'s SCLK link (row E to J) or the cut beside it",
                ),
                Check(
                    "units",
                    f"{u}: MOSI pin to BUS IN strip K",
                    "beep",
                    hint=f"{u}'s MOSI link (F to K)",
                ),
                Check(
                    "units",
                    f"{u}: MISO pin to BUS IN strip L",
                    "beep",
                    hint=f"{u}'s MISO link (G to L)",
                ),
                Check(
                    "units",
                    f"{u}: REFP0 pin to strip B (3V3)",
                    "beep",
                    hint=f"{u}'s REFP0 link (C to B)",
                ),
                Check(
                    "units",
                    f"{u}: REFN0 pin to strip A (GND)",
                    "beep",
                    hint=f"{u}'s REFN0 link (D to A)",
                ),
                Check(
                    "units",
                    f"{u}: CLK pin to strip A (GND)",
                    "beep",
                    hint=f"{u}'s CLK link (C to A)",
                ),
                Check(
                    "units",
                    f"{u}: AIN0 pin to its own strip P (cable S hole)",
                    "beep",
                    hint=f"{u}'s S link (H to P)",
                ),
                Check(
                    "units",
                    f"{u}: CS pin to strip A (GND) and to strip B (3V3)",
                    "open",
                    hint="the CS strip (row D) bridged to a rail, or a missing cut in row D",
                ),
            ]
    if "cables" in upto:
        r = 1 / (n / (2 * r_each) + n / R_CELL)
        out.append(
            Check(
                "cables",
                f"strip B (3V3) to strip A (GND), all {n} cells plugged in at their JSTs",
                "ohms",
                0.8 * r,
                1.2 * r,
                hint=f"expect ~{r:.0f} Ω (each cell ~{R_CELL:.0f} Ω in parallel with each R1+R2). "
                "Same as without cells: a cable's "
                "E+/E- not reaching N/O, or a JST not seated",
            )
        )
        for u in units:
            out += [
                Check(
                    "cables",
                    f"{u}: strip P (S) to strip O (GND): half the cell plus the rest",
                    "ohms",
                    300,
                    1_500,
                    hint="near 0: S shorted to E- (swapped at the JST?); open: S wire (red) broken",
                ),
                Check(
                    "cables",
                    f"{u}: strip P (S) to strip N (3V3)",
                    "ohms",
                    300,
                    1_500,
                    hint="near 0: S shorted to E+ (swapped at the JST?)",
                ),
                Check(
                    "cables",
                    f"{u}: cable shield to strip O (GND) at the carrier",
                    "beep",
                    hint="shield not soldered to strip O",
                ),
            ]
    if "uno" in upto:
        out += [
            Check(
                "uno",
                "UNO Q 3V3 pin to UNO Q GND pin",
                "ohms",
                0,
                1e9,
                hint="just record it; compare with the strip B to A reading (should be similar or lower)",
            ),
            Check("uno", "UNO Q 3V3 pin to carrier strip B", "beep", hint="the 3V3 wire to BUS IN"),
            Check("uno", "UNO Q GND pin to carrier strip A", "beep", hint="the GND wire to BUS IN"),
            Check("uno", "UNO Q D13 to carrier strip J (SCLK)", "beep", hint="SCLK wire"),
            Check("uno", "UNO Q D11 to carrier strip K (MOSI)", "beep", hint="MOSI wire"),
            Check("uno", "UNO Q D12 to carrier strip L (MISO)", "beep", hint="MISO wire"),
            Check(
                "uno",
                "look: the power wire is on the pin marked 3V3, not 5V (y/n)",
                "yes",
                hint="move it to 3V3 before powering: 5V would feed the ADCs' reference and inputs",
            ),
        ]
        for u in units:
            out.append(
                Check(
                    "uno",
                    f"UNO Q {CS_PIN[u]} to {u}'s CS pin (on top)",
                    "beep",
                    hint=f"{u}'s CS wire, or it's on the wrong UNO Q pin",
                )
            )
        others = [u for u in units if u != units[0]]
        if others:
            out.append(
                Check(
                    "uno",
                    f"UNO Q {CS_PIN[units[0]]} to the other units' CS pins ({', '.join(others)})",
                    "open",
                    hint="two CS wires joined, or the CS strips (row D) bridged",
                )
            )
        if "L1" in units:
            out.append(
                Check("uno", "UNO Q D2 to L1's DRDY pin (on top)", "beep", hint="L1's DRDY wire")
            )
        out.append(
            Check(
                "uno",
                "UNO Q D10, D0 and D1 to strips A, B, J, K, L and each CS pin",
                "open",
                hint="nothing may connect to D10 (SPI NSS) or D0/D1 (console)",
            )
        )
    if heel_chained:
        out.append(
            Check(
                "uno",
                "toe BUS OUT to heel BUS IN, strip by strip (A, B, J, K, L)",
                "beep",
                hint="the chain wires between carriers",
            )
        )
    return out


def fmt(reading: float | bool) -> str:
    if reading is True:
        return "beep"
    if reading is False:
        return "no beep"
    if reading == OPEN:
        return "OL"
    return f"{reading:,.0f} Ω" if reading < 1e4 else f"{reading / 1e3:,.1f} kΩ"


def expected(c: Check) -> str:
    if c.expect == "beep":
        return "beep (~0 Ω)"
    if c.expect == "open":
        return "no beep (OL)"
    if c.expect == "yes":
        return "y"
    if c.hi >= 1e9:
        return "any (record it)"
    return f"{c.lo:,.0f}-{c.hi:,.0f} Ω"


def run(checks: list[Check], ask=input) -> list[dict]:
    results = []
    stage = ""
    for i, c in enumerate(checks, 1):
        if c.stage != stage:
            stage = c.stage
            print(f"\n== {stage} ==")
        while True:
            text = ask(f"[{i}/{len(checks)}] {c.what}\n    expect {expected(c)} > ")
            reading = parse_reading(text)
            if text.strip().lower() in ("s", "skip"):
                results.append({"check": asdict(c), "reading": None, "ok": None})
                break
            if reading is None:
                print("    type a number (e.g. 498, 1.2k), OL, y/n, or s to skip")
                continue
            ok = judge(c, reading)
            print(
                f"    {'PASS' if ok else 'FAIL'} ({fmt(reading)})" + ("" if ok else f": {c.hint}")
            )
            results.append({"check": asdict(c), "reading": fmt(reading), "ok": ok})
            break
    return results


def summarize(results: list[dict]) -> str:
    failed = [r for r in results if r["ok"] is False]
    skipped = [r for r in results if r["ok"] is None]
    lines = [
        "",
        f"{len(results) - len(failed) - len(skipped)} passed, {len(failed)} failed, {len(skipped)} skipped",
    ]
    for r in failed:
        lines.append(f"  FAIL  {r['check']['what']}: read {r['reading']}. {r['check']['hint']}")
    if not failed:
        lines.append("Safe to power. Flash bench/ads1220_all and run tools/bench/multi_cell.py.")
    else:
        lines.append("Fix the failures before powering the UNO Q.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--units", default=",".join(TOE), help="units fitted, e.g. L1 or L1,L2,R1,R2")
    ap.add_argument(
        "--stage", choices=STAGES, default="uno", help="how far the build has got (default: uno)"
    )
    ap.add_argument(
        "--resistor",
        default="1k",
        help="value of each R1/R2 (they must match), e.g. 680, 1k, 1.5k (default 1k)",
    )
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "bench" / "results"))
    args = ap.parse_args()
    r_each = parse_reading(args.resistor)
    if not isinstance(r_each, float) or not 100 <= r_each <= 1e5:
        print(f"--resistor {args.resistor!r}: give a value like 680, 1k or 1.5k")
        return 2
    units = args.units.split(",")
    bad = [u for u in units if u not in CHANNELS]
    if bad:
        print(f"Unknown unit(s) {bad}; use names from {', '.join(CHANNELS)}")
        return 2
    print("Power off: the UNO Q unplugged from USB. Meter on resistance / continuity.")
    try:
        results = run(checks_for(units, args.stage, r_each=r_each))
    except (KeyboardInterrupt, EOFError):
        print("\nStopped.")
        return 130
    print(summarize(results))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"carrier-check-{'-'.join(units)}-{datetime.now():%Y%m%d-%H%M%S}.json"
    path.write_text(
        json.dumps({"units": units, "stage": args.stage, "results": results}, indent=2),
        encoding="utf-8",
    )
    print(f"Saved {path}.")
    return 0 if all(r["ok"] is not False for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
