#!/usr/bin/env python3
"""Generate docs/img/carrier-stripboard.svg: the ADC carrier on 2.54 mm stripboard.

Seen from the component side. Strips run left-right; rows are lettered A-Q, columns
numbered 1-37. Four breakouts sit in a row with their header columns across the strips,
so every pin lands on its own strip. The breakout's pin rows pair up (AGND|DGND,
AVDD|DVDD, ...), which lets strip A be the GND rail and strip B the 3V3 rail under all four.

Layout per breakout (x0 = its analog column; digital column is x0 + 7):
  rows A,B        GND and 3V3 rails (never cut)
  rows C-H        cut at x0+3 (between the header columns) and x0+8 (before the next breakout)
  links           REFP0 C->B, REFN0 D->A, CLK C->A, SCLK E->J, MOSI F->K, MISO G->L, AIN0 H->P
  cell cable      column x0+2: E+ into N (3V3b), E- into O (GNDb), S into P; row Q spare.
                  The plug-in JST is at the cradle, so the cable solders straight in here.
  row P           cut at x0 and x0+3 so each unit's S strip is separate
Strips J,K,L are the SCLK/MOSI/MISO rails; N/O repeat 3V3/GND next to the cable pads and are
tied to A/B by links at columns 10 and 19. Bus wires solder in at column 1 (BUS IN) and
37 (BUS OUT).
"""

from pathlib import Path

from _svg import ACCENT, INK, MUTED, WIRE, Svg

HERE = Path(__file__).parent
COLS, ROWS = 37, 17
ROW_NAMES = "ABCDEFGHIJKLMNOPQ"
P = 24                      # px per 2.54 mm hole pitch
GX, GY = 110, 190           # grid origin (column 1, row A)
MODULES = [("L1", 2, "D3"), ("L2", 11, "D4"), ("R1", 20, "D7"), ("R2", 29, "D8")]
HEEL = ["L3", "L4", "R3", "R4"]
HEEL_CS = ["D5", "D6", "D9", "A2"]
ANALOG = ["AGND", "AVDD", "REFP0", "REFN0", "AIN3", "AIN2", "AIN1", "AIN0"]
DIGITAL = ["DGND", "DVDD", "CLK", "CS", "SCLK", "MOSI", "MISO", "DRDY"]
RAILS = {"A": ("GND", "gnd"), "B": ("3V3", "3v3"), "J": ("SCLK", "sck"), "K": ("MOSI", "mosi"),
         "L": ("MISO", "miso"), "N": ("3V3", "3v3"), "O": ("GND", "gnd")}


def xy(col, row):
    """Centre of hole (column 1..37, row letter)."""
    return GX + (col - 1) * P, GY + ROW_NAMES.index(row) * P


def cuts():
    out = []
    for _, x0, _ in MODULES:
        out += [(x0 + 3, r) for r in "CDEFGH"]
        out += [(x0, "P"), (x0 + 3, "P")]
    for _, x0, _ in MODULES[:-1]:
        out += [(x0 + 8, r) for r in "CDEFGH"]
    return out


def links():
    """(from, to, colour key, label) for every wire link on the component side."""
    out = []
    for _, x0, _ in MODULES:
        out += [
            ((x0 + 1, "C"), (x0 + 1, "B"), "3v3", "REFP0"),
            ((x0 + 2, "D"), (x0 + 2, "A"), "gnd", "REFN0"),
            ((x0 + 6, "C"), (x0 + 6, "A"), "gnd", "CLK"),
            ((x0 + 4, "E"), (x0 + 4, "J"), "sck", "SCLK"),
            ((x0 + 5, "F"), (x0 + 5, "K"), "mosi", "MOSI"),
            ((x0 + 6, "G"), (x0 + 6, "L"), "miso", "MISO"),
            ((x0 + 1, "H"), (x0 + 1, "P"), "sig", "S"),
        ]
    out += [((10, "A"), (10, "O"), "gnd", "tie"), ((19, "B"), (19, "N"), "3v3", "tie")]
    return out


def draw() -> Svg:
    s = Svg(1120, 920)
    s.text(40, 46, "ADC carrier on stripboard (toe carrier shown)", 24, INK, 700)
    s.text(40, 72, "Component side. Copper strips run left–right underneath; red ✕ = cut the strip at "
           "that hole. 37 × 17 holes ≈ 94 × 43 mm.", 14, MUTED)
    # board and strips
    s.rect(GX - P, GY - P, (COLS + 1) * P, (ROWS + 1) * P, "#F3EBDD", "#B99C6B", 6, 1.5)
    for i, r in enumerate(ROW_NAMES):
        y = GY + i * P
        fill = "#E4C9A0"
        s.add(f'<rect x="{GX - P * 0.5}" y="{y - P * 0.36}" width="{COLS * P}" height="{P * 0.72}" '
              f'rx="3" fill="{fill}" opacity="0.55"/>')
        s.text(GX - P - 10, y + 5, r, 13, INK, 700, "end")
        if r in RAILS:
            name, key = RAILS[r]
            s.text(GX + COLS * P + 14, y + 5, name, 12, WIRE[key], 700)
    for c in range(1, COLS + 1):
        if c == 1 or c % 5 == 0 or c == COLS:
            s.text(GX + (c - 1) * P, GY - P - 8, str(c), 11, MUTED, 600, "middle")
    for c in range(1, COLS + 1):
        for r in ROW_NAMES:
            x, y = xy(c, r)
            s.add(f'<circle cx="{x}" cy="{y}" r="3.2" fill="#FFFFFF" stroke="#B99C6B" stroke-width="0.8"/>')

    # breakouts: outline + pins
    for name, x0, cs in MODULES:
        (xa, ya), (xd, yd) = xy(x0, "A"), xy(x0 + 7, "H")
        s.rect(xa - 0.62 * P, ya - 0.62 * P, (xd - xa) + 1.24 * P, (yd - ya) + 1.24 * P,
               "#7B4FB8", "#5B3B8C", 4, 1.5)
        s.add(f'<rect x="{xa - 0.62 * P}" y="{ya - 0.62 * P}" width="{(xd - xa) + 1.24 * P}" '
              f'height="{(yd - ya) + 1.24 * P}" rx="4" fill="#FFFFFF" opacity="0.72"/>')
        s.text((xa + xd) / 2, GY - P - 34, name, 18, "#5B3B8C", 700, "middle")
        s.text((xa + xd) / 2, GY - P - 20, f"CS ← {cs}", 11, WIRE["cs"], 700, "middle")
        for i, r in enumerate("ABCDEFGH"):
            for col, labels in ((x0, ANALOG), (x0 + 7, DIGITAL)):
                x, y = xy(col, r)
                s.add(f'<rect x="{x - 5}" y="{y - 5}" width="10" height="10" fill="#C9A227" stroke="#8A6D12"/>')
        # CS flying lead (and DRDY on L1) — marked, not a link
        cx, cy = xy(x0 + 5, "D")
        s.add(f'<circle cx="{cx}" cy="{cy}" r="7" fill="none" stroke="{WIRE["cs"]}" stroke-width="3"/>')
    # cell cable pads: the cable solders straight in (its JST is at the cradle)
    for name, x0, _ in MODULES:
        for r, lab in (("N", "E+"), ("O", "E−"), ("P", "S")):
            xx, yy = xy(x0 + 2, r)
            s.add(f'<circle cx="{xx}" cy="{yy}" r="7" fill="none" stroke="{WIRE["cell"]}" stroke-width="2.8"/>')
            s.text(xx - 11, yy + 4, lab, 10, WIRE["cell"], 700, "end")
        x, y2 = xy(x0 + 2, "Q")
        s.text(x, y2 + 30, f"cable · cell {name}", 11, INK, 700, "middle")
    # links
    for (c1, r1), (c2, r2), key, _ in links():
        (x1, y1), (x2, y2) = xy(c1, r1), xy(c2, r2)
        s.line([(x1, y1), (x2, y2)], WIRE[key], 4)
        s.dot(x1, y1, WIRE[key], 4.5)
        s.dot(x2, y2, WIRE[key], 4.5)
    # cuts
    for c, r in cuts():
        x, y = xy(c, r)
        s.line([(x - 6, y - 6), (x + 6, y + 6)], "#E03131", 2.6)
        s.line([(x - 6, y + 6), (x + 6, y - 6)], "#E03131", 2.6)
    # bus pads
    for col, label in ((1, "BUS IN"), (COLS, "BUS OUT")):
        for r in "ABJKL":
            x, y = xy(col, r)
            s.add(f'<circle cx="{x}" cy="{y}" r="7" fill="none" stroke="{INK}" stroke-width="2.4"/>')
        x, y = xy(col, "M")
        s.text(x, y + 6, label, 11, INK, 700, "middle")

    # key
    ky = GY + ROWS * P + 70
    items = [("wire link (component side; touches copper only at its dotted ends)", None),
             ("✕ cut the strip at this hole (from the copper side)", "#E03131"),
             ("○ solder a bus wire here (5 per end)", INK),
             ("○ solder this unit's CS wire from the UNO Q here", WIRE["cs"]),
             ("○ solder the cell cable's E+ / E− / S here (JST is at the cradle)", WIRE["cell"]),
             ("■ breakout header pin (pins down, plastic spacer under the breakout)", "#C9A227")]
    for i, (txt, col) in enumerate(items):
        s.text(40 + (i % 2) * 540, ky + (i // 2) * 22, txt, 12, col or INK, 600 if col else 400)
    pins = " · ".join(f"{r} {a}|{d}" for r, a, d in zip("ABCDEFGH", ANALOG, DIGITAL))
    s.text(40, ky + 72, "Breakout pins by row (left|right column): " + pins, 11, "#5B3B8C", 700)
    s.text(40, ky + 92, "Fit all links before the breakouts: they run underneath them. The tie links in "
           "columns 10 and 19 pass over cut holes; links only touch copper at their ends.", 12, MUTED)
    s.text(40, ky + 118, "Not shown: R1/R2 solder on top of each breakout (AVDD–AIN1 and AIN1–AGND pins). "
           "L1's DRDY wire solders to L1's DRDY pin on top. Cable shields solder to strip O.",
           12, ACCENT, 600)
    s.text(40, ky + 138, "Heel carrier: identical board with L3, L4, R3, R4 (CS ← " + ", ".join(HEEL_CS) +
           "); its BUS OUT pads stay empty.", 12, MUTED)
    return s


if __name__ == "__main__":
    draw().save(HERE / "carrier-stripboard.svg")
