#!/usr/bin/env python3
"""Generate docs/img/bench-single-cell.svg: wiring for the M1 one-cell bench test.

UNO Q header -> one ADS1220 breakout (L1) -> two 1 kΩ resistors + one load cell.
Module pins use the silkscreen names and physical order of the purple ADS1220 breakout
used in this build (left: DRDY MISO MOSI SCLK CS CLK DVDD DGND; right: AIN0 AIN1 AIN2
AIN3 REFN0 REFP0 AVDD AGND). UNO Q pins match docs/wiring.md.
"""
from pathlib import Path

INK, MUTED, ACCENT = "#1F2933", "#5F6B78", "#C2410C"
BOARD, BOARD_S = "#E8F1F2", "#2F6F73"
MODULE, MODULE_S = "#EFEAF7", "#5B3B8C"
CELL, CELL_S = "#E9ECEF", "#56626F"
WIRE = {
    "3v3": "#D64545", "gnd": "#222222", "sck": "#2F80ED", "mosi": "#27AE60",
    "miso": "#9B51E0", "cs": "#E2A400", "drdy": "#EB5757", "sig": "#00897B", "ref": "#8D6E63",
}
out: list[str] = []


def add(s):
    out.append(s)


def text(x, y, s, size=13, fill=INK, weight=400, anchor="start"):
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{s}</text>')


def rect(x, y, w, h, fill, stroke, rx=6, sw=1.5):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}"/>')


def path(d, color, width=2.6):
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
        f'stroke-linejoin="round" stroke-linecap="round"/>')


def dot(x, y, color):
    add(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/>')


def pin(x, y, label, side, color=INK):
    """A labelled pin. side='r': label to the left of a pin on a right edge; 'l': the reverse."""
    add(f'<circle cx="{x}" cy="{y}" r="5" fill="#FFFFFF" stroke="{color}" stroke-width="2"/>')
    if side == "r":
        text(x - 12, y + 4, label, 13, color, 700, "end")
    else:
        text(x + 12, y + 4, label, 13, color, 700)


def resistor_v(x, y, label):
    """Vertical resistor body centred at (x, y), 52 px long."""
    rect(x - 9, y - 26, 18, 52, "#FFF6E5", "#B7791F", 4, 1.5)
    for i, c in enumerate(["#8B4513", "#222222", "#D64545", "#C9A227"]):
        add(f'<rect x="{x - 9}" y="{y - 18 + i * 10}" width="18" height="4" fill="{c}"/>')
    text(x + 16, y + 4, label, 13, INK, 600)


def resistor_h(x, y, label):
    """Horizontal resistor body centred at (x, y), 52 px long."""
    rect(x - 26, y - 9, 52, 18, "#FFF6E5", "#B7791F", 4, 1.5)
    for i, c in enumerate(["#8B4513", "#222222", "#D64545", "#C9A227"]):
        add(f'<rect x="{x - 18 + i * 10}" y="{y - 9}" width="4" height="18" fill="{c}"/>')
    text(x, y + 26, label, 13, INK, 600, "middle")


def flag_3v3(x, y):
    """3V3 net flag above (x, y)."""
    path(f"M{x},{y} L{x},{y - 22}", WIRE["3v3"])
    add(f'<path d="M{x - 11},{y - 22} L{x + 11},{y - 22} L{x},{y - 36} Z" fill="{WIRE["3v3"]}"/>')
    text(x, y - 42, "3V3", 12, WIRE["3v3"], 700, "middle")


def ground(x, y):
    """GND symbol below (x, y)."""
    path(f"M{x},{y} L{x},{y + 18}", WIRE["gnd"])
    for i, w in enumerate((14, 9, 4)):
        path(f"M{x - w},{y + 18 + i * 5} L{x + w},{y + 18 + i * 5}", WIRE["gnd"], 2.2)


W, H = 1280, 900
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
    'font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif">')
add(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')
text(40, 46, "Bench test: one load cell (L1)", 24, INK, 700)
text(40, 72, "UNO Q → one ADS1220 breakout → load cell, completed into a full bridge by R1 and R2. "
     "Wire with the UNO Q unplugged.", 14, MUTED)

# ---- ADS1220 breakout: silkscreen names, physical order ----------------------------------
MX, MY = 540, 130
MW = 250
LEFT = [("DRDY", 120), ("MISO", 170), ("MOSI", 220), ("SCLK", 270), ("CS", 320),
        ("CLK", 370), ("DVDD", 430), ("DGND", 480)]
RIGHT = [("AIN0", 120), ("AIN1", 170), ("AIN2", 220), ("AIN3", 270), ("REFN0", 330),
         ("REFP0", 380), ("AVDD", 430), ("AGND", 480)]
rect(MX, MY + 40, MW, 480, MODULE, MODULE_S, 10, 2)
text(MX + MW / 2, MY + 72, "ADS1220 breakout (L1)", 16, MODULE_S, 700, "middle")
text(MX + MW / 2, MY + 90, "pin names and order as printed on the board", 11, MUTED, 400, "middle")
for name, dy in LEFT:
    pin(MX, MY + dy, name, "l", MODULE_S)
for name, dy in RIGHT:
    pin(MX + MW, MY + dy, name, "r", MODULE_S)
y_of = {n: MY + dy for n, dy in LEFT + RIGHT}

# ---- UNO Q: pins lined up with the breakout so every wire is straight -------------------------
BX, BY = 60, MY + 40
UX = BX + 190
rect(BX, BY, 190, 480, BOARD, BOARD_S, 10, 2)
text(BX + 95, BY + 32, "Arduino UNO Q", 16, BOARD_S, 700, "middle")
text(BX + 95, BY + 50, "MCU header pins", 12, MUTED, 400, "middle")
links = [("D2", "DRDY", "drdy"), ("D12", "MISO", "miso"), ("D11", "MOSI", "mosi"),
         ("D13", "SCLK", "sck"), ("D3", "CS", "cs"), ("3V3", "DVDD", "3v3"), ("GND", "DGND", "gnd")]
for q, m, key in links:
    y = y_of[m]
    pin(UX, y, q, "r", BOARD_S)
    path(f"M{UX},{y} L{MX},{y}", WIRE[key])
text(BX + 95, BY + 500, "Leave D10, D0, D1 unconnected", 12, ACCENT, 600, "middle")
# CLK: grounded (internal oscillator)
path(f"M{MX},{y_of['CLK']} L{MX - 50},{y_of['CLK']}", WIRE["gnd"])
ground(MX - 50, y_of["CLK"])
text(MX - 64, y_of["CLK"] - 8, "CLK → GND", 12, MUTED, 600, "end")

# ---- right side: reference, analog supply, divider, load cell --------------------------------
RX = MX + MW
# REFN0 -> GND, REFP0 -> 3V3, AVDD -> 3V3, AGND -> GND (short stubs to flags)
path(f"M{RX},{y_of['REFN0']} L{RX + 50},{y_of['REFN0']}", WIRE["gnd"])
ground(RX + 50, y_of["REFN0"])
path(f"M{RX},{y_of['REFP0']} L{RX + 100},{y_of['REFP0']}", WIRE["3v3"])
flag_3v3(RX + 100, y_of["REFP0"])
path(f"M{RX},{y_of['AVDD']} L{RX + 150},{y_of['AVDD']}", WIRE["3v3"])
flag_3v3(RX + 150, y_of["AVDD"])
path(f"M{RX},{y_of['AGND']} L{RX + 50},{y_of['AGND']}", WIRE["gnd"])
ground(RX + 50, y_of["AGND"])
text(RX - 14, y_of["AIN3"] + 26, "AIN2, AIN3: leave open", 11, MUTED, 400, "end")

# divider on AIN1: R1 to 3V3 (horizontal), R2 to GND (vertical)
NX, NY = RX + 90, y_of["AIN1"]
path(f"M{RX},{NY} L{NX},{NY}", WIRE["ref"])
dot(NX, NY, WIRE["ref"])
path(f"M{NX},{NY} L{NX + 34},{NY}", WIRE["ref"])
resistor_h(NX + 60, NY, "R1  1 kΩ")
path(f"M{NX + 86},{NY} L{NX + 140},{NY}", WIRE["3v3"])
flag_3v3(NX + 140, NY)
path(f"M{NX},{NY} L{NX},{NY + 24}", WIRE["ref"])
resistor_v(NX, NY + 50, "R2  1 kΩ")
path(f"M{NX},{NY + 76} L{NX},{NY + 84}", WIRE["gnd"])
ground(NX, NY + 84)
text(RX + 14, NY - 10, "≈1.65 V", 12, MUTED)
text(NX + 20, NY + 124, "0.1 % resistors, soldered at the breakout", 12, MUTED)

# load cell: S -> AIN0 routed over the top of the divider
CX, CY = 1110, MY - 10
rect(CX - 70, CY, 140, 170, CELL, CELL_S, 12, 2)
text(CX, CY + 76, "Load cell", 14, CELL_S, 700, "middle")
text(CX, CY + 94, "3-wire half bridge", 11, MUTED, 400, "middle")
add(f'<rect x="{CX - 22}" y="{CY + 106}" width="44" height="52" rx="6" fill="#FFFFFF" stroke="{CELL_S}"/>')
text(CX, CY + 137, "strap", 11, MUTED, 400, "middle")
sy = CY + 40
path(f"M{RX},{y_of['AIN0']} L{RX + 40},{y_of['AIN0']} L{RX + 40},{sy} L{CX - 70},{sy}", WIRE["sig"])
text(CX - 80, sy - 8, "S (centre tap)", 13, WIRE["sig"], 700, "end")
path(f"M{CX + 70},{CY + 40} L{CX + 110},{CY + 40}", WIRE["3v3"])
flag_3v3(CX + 110, CY + 40)
text(CX + 78, CY + 60, "E+", 13, WIRE["3v3"], 700)
path(f"M{CX + 70},{CY + 120} L{CX + 110},{CY + 120}", WIRE["gnd"])
ground(CX + 110, CY + 120)
text(CX + 78, CY + 112, "E−", 13, WIRE["gnd"], 700)

# ---- legend and notes ------------------------------------------------------------------------
LX, LY = 60, 720
text(LX, LY, "Wire colours in this drawing", 13, INK, 700)
items = [("3V3", "3v3"), ("GND", "gnd"), ("SCLK", "sck"), ("MOSI", "mosi"),
         ("MISO", "miso"), ("CS", "cs"), ("DRDY", "drdy"), ("Signal", "sig"), ("Divider", "ref")]
for i, (label, key) in enumerate(items):
    x = LX + (i % 3) * 130
    y = LY + 24 + (i // 3) * 22
    path(f"M{x},{y - 4} L{x + 26},{y - 4}", WIRE[key], 3)
    text(x + 34, y, label, 12)
NX2 = 560
text(NX2, LY, "Power flags", 13, INK, 700)
flag_3v3(NX2 + 12, LY + 58)
text(NX2 + 34, LY + 42, "every 3V3 flag connects to the UNO Q's 3V3 pin", 12)
ground(NX2 + 12, LY + 76)
text(NX2 + 34, LY + 96, "every ground symbol connects to the UNO Q's GND", 12)
text(NX2, LY + 128, "Both grounds (DGND and AGND) and both supplies (DVDD and AVDD) must be "
     "connected.", 12, ACCENT, 600)
text(NX2, LY + 146, "Identify E+, E− and S with a meter first (docs/wiring.md §2): the ~2 kΩ pair "
     "are E+/E−, the other wire is S.", 12, MUTED)

add("</svg>")
dest = Path(__file__).with_name("bench-single-cell.svg")
dest.write_text("\n".join(out), encoding="utf-8")
print(f"wrote {dest}")
