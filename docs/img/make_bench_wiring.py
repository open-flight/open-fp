#!/usr/bin/env python3
"""Generate docs/img/bench-single-cell.svg: wiring for the M1 one-cell bench test.

UNO Q header -> one ADS1220 module (L1) -> two 1 kΩ resistors + one load cell.
Pin assignments match docs/wiring.md (verified against arduino:zephyr 1.0.0).
"""
from pathlib import Path

INK, MUTED, ACCENT = "#1F2933", "#5F6B78", "#C2410C"
BOARD, BOARD_S = "#E8F1F2", "#2F6F73"
MODULE, MODULE_S = "#EEF0F8", "#4B5694"
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


def path(d, color, width=2.6, dash=""):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
        f'stroke-linejoin="round" stroke-linecap="round"{extra}/>')


def dot(x, y, color):
    add(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/>')


def pin(x, y, label, side, color=INK):
    """A labelled pin stub. side='r' puts the stub on the right edge, 'l' on the left."""
    add(f'<circle cx="{x}" cy="{y}" r="5" fill="#FFFFFF" stroke="{color}" stroke-width="2"/>')
    if side == "r":
        text(x - 12, y + 4, label, 13, color, 600, "end")
    else:
        text(x + 12, y + 4, label, 13, color, 600)


def resistor(x, y, label):
    """Vertical resistor body centred at (x, y)."""
    rect(x - 9, y - 26, 18, 52, "#FFF6E5", "#B7791F", 4, 1.5)
    for i, c in enumerate(["#8B4513", "#222222", "#D64545", "#C9A227"]):
        add(f'<rect x="{x - 9}" y="{y - 18 + i * 10}" width="18" height="4" fill="{c}"/>')
    text(x + 16, y + 4, label, 13, INK, 600)


W, H = 1280, 900
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
    'font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif">')
add(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')
text(40, 46, "Bench test: one load cell (L1)", 24, INK, 700)
text(40, 72, "UNO Q → one ADS1220 → load cell completed into a full bridge by R1 and R2. "
     "Wire with the UNO Q unplugged.", 14, MUTED)

# ---- UNO Q header -------------------------------------------------------------------------
BX, BY = 60, 120
rect(BX, BY, 190, 470, BOARD, BOARD_S, 10, 2)
text(BX + 95, BY + 30, "Arduino UNO Q", 16, BOARD_S, 700, "middle")
text(BX + 95, BY + 50, "MCU header pins", 12, MUTED, 400, "middle")
uno = {"3V3": 120, "GND": 170, "D13": 240, "D11": 290, "D12": 340, "D3": 400, "D2": 450}
UX = BX + 190
for name, dy in uno.items():
    pin(UX, BY + dy, name, "r", BOARD_S)
text(BX + 95, BY + 520, "Leave D10, D0, D1 unconnected", 12, ACCENT, 600, "middle")

# ---- power flags -------------------------------------------------------------------------
def flag_3v3(x, y):
    """3V3 net flag: the wire at (x, y) goes up to it."""
    path(f"M{x},{y} L{x},{y - 22}", WIRE["3v3"])
    add(f'<path d="M{x - 11},{y - 22} L{x + 11},{y - 22} L{x},{y - 36} Z" fill="{WIRE["3v3"]}"/>')
    text(x, y - 42, "3V3", 12, WIRE["3v3"], 700, "middle")


def ground(x, y):
    """GND symbol: the wire at (x, y) goes down to it."""
    path(f"M{x},{y} L{x},{y + 18}", WIRE["gnd"])
    for i, w in enumerate((14, 9, 4)):
        path(f"M{x - w},{y + 18 + i * 5} L{x + w},{y + 18 + i * 5}", WIRE["gnd"], 2.2)


# ---- ADS1220 module ------------------------------------------------------------------------
MX, MY = 520, 120
rect(MX, MY, 250, 560, MODULE, MODULE_S, 10, 2)
text(MX + 125, MY + 30, "ADS1220 module (L1)", 16, MODULE_S, 700, "middle")
text(MX + 125, MY + 50, "match these names to your silkscreen", 12, MUTED, 400, "middle")
left = {"AVDD / VCC": 120, "DVDD": 145, "GND (AVSS/DGND)": 170, "SCLK": 240, "DIN": 290,
        "DOUT": 340, "CS": 400, "DRDY": 450, "CLK*": 510}
right = {"REFP0": 120, "REFN0": 170, "AIN0": 260, "AIN1": 400}
for name, dy in left.items():
    pin(MX, MY + dy, name, "l", MODULE_S)
for name, dy in right.items():
    pin(MX + 250, MY + dy, name, "r", MODULE_S)
text(MX + 238, MY + 540, "AIN2, AIN3: leave open", 12, MUTED, 400, "end")


# ---- UNO Q -> module wires ---------------------------------------------------------------
def run(y_from, y_to, color, x_turn):
    path(f"M{UX},{y_from} L{x_turn},{y_from} L{x_turn},{y_to} L{MX},{y_to}", color)


run(BY + 120, MY + 120, WIRE["3v3"], 330)
dot(330, MY + 120, WIRE["3v3"])
path(f"M330,{MY + 120} L330,{MY + 145} L{MX},{MY + 145}", WIRE["3v3"])
run(BY + 170, MY + 170, WIRE["gnd"], 360)
run(BY + 240, MY + 240, WIRE["sck"], 390)
run(BY + 290, MY + 290, WIRE["mosi"], 410)
run(BY + 340, MY + 340, WIRE["miso"], 430)
run(BY + 400, MY + 400, WIRE["cs"], 450)
run(BY + 450, MY + 450, WIRE["drdy"], 470)
path(f"M{MX},{MY + 510} L{MX - 40},{MY + 510}", WIRE["gnd"])      # CLK strap
ground(MX - 40, MY + 510)

# ---- right side: reference, divider, load cell --------------------------------------------
RX = MX + 250
path(f"M{RX},{MY + 120} L{RX + 50},{MY + 120}", WIRE["3v3"])      # REFP0 -> 3V3
flag_3v3(RX + 50, MY + 120)
path(f"M{RX},{MY + 170} L{RX + 90},{MY + 170}", WIRE["gnd"])      # REFN0 -> GND
ground(RX + 90, MY + 170)

# load cell: S straight across to AIN0
CX, CY = 1080, MY + 190
rect(CX - 70, CY, 140, 160, CELL, CELL_S, 12, 2)
text(CX, CY + 60, "Load cell", 14, CELL_S, 700, "middle")
text(CX, CY + 78, "3-wire half bridge", 11, MUTED, 400, "middle")
add(f'<rect x="{CX - 22}" y="{CY + 92}" width="44" height="52" rx="6" fill="#FFFFFF" stroke="{CELL_S}"/>')
text(CX, CY + 123, "strap", 11, MUTED, 400, "middle")
path(f"M{CX},{CY} L{CX},{CY - 30}", WIRE["3v3"])                  # E+ (top)
flag_3v3(CX, CY - 30)
text(CX + 10, CY - 8, "E+", 13, WIRE["3v3"], 700)
path(f"M{CX},{CY + 160} L{CX},{CY + 180}", WIRE["gnd"])           # E- (bottom)
ground(CX, CY + 180)
text(CX + 10, CY + 176, "E−", 13, WIRE["gnd"], 700)
path(f"M{RX},{MY + 260} L{CX - 70},{MY + 260}", WIRE["sig"])      # S -> AIN0
text(CX - 80, MY + 252, "S (centre tap)", 13, WIRE["sig"], 700, "end")

# R1 / R2 divider -> AIN1
RDX = 900
flag_3v3(RDX, MY + 330)
path(f"M{RDX},{MY + 330} L{RDX},{MY + 344}", WIRE["3v3"])
resistor(RDX, MY + 370, "R1  1 kΩ 0.1 %")
path(f"M{RDX},{MY + 396} L{RDX},{MY + 434}", WIRE["ref"])
dot(RDX, MY + 400, WIRE["ref"])
path(f"M{RX},{MY + 400} L{RDX},{MY + 400}", WIRE["ref"])
text(RDX - 12, MY + 392, "≈1.65 V", 12, MUTED, 400, "end")
resistor(RDX, MY + 460, "R2  1 kΩ 0.1 %")
path(f"M{RDX},{MY + 486} L{RDX},{MY + 496}", WIRE["gnd"])
ground(RDX, MY + 496)
text(RDX + 40, MY + 530, "Solder R1 and R2 at the ADC board", 12, MUTED)

# ---- legend and notes ----------------------------------------------------------------------
LX, LY = 60, 740
text(LX, LY, "Wire colours in this drawing", 13, INK, 700)
items = [("3V3", "3v3"), ("GND", "gnd"), ("SCLK", "sck"), ("MOSI → DIN", "mosi"),
         ("MISO ← DOUT", "miso"), ("CS", "cs"), ("DRDY", "drdy"), ("Signal", "sig"), ("Divider", "ref")]
for i, (label, key) in enumerate(items):
    x = LX + (i % 3) * 140
    y = LY + 24 + (i // 3) * 22
    path(f"M{x},{y - 4} L{x + 26},{y - 4}", WIRE[key], 3)
    text(x + 34, y, label, 12)
NX = 560
text(NX, LY, "Power flags", 13, INK, 700)
flag_3v3(NX + 12, LY + 58)
text(NX + 34, LY + 42, "every 3V3 flag connects to the UNO Q's 3V3 pin", 12)
ground(NX + 12, LY + 76)
text(NX + 34, LY + 96, "every ground symbol connects to the UNO Q's GND", 12)
text(NX, LY + 128, "* CLK: only if your module breaks it out and doesn't already ground it "
     "(selects the internal oscillator).", 12, MUTED)
text(NX, LY + 146, "Identify E+, E− and S with a meter first (docs/wiring.md §2): the ~2 kΩ pair "
     "are E+/E−, the other wire is S.", 12, MUTED)

add("</svg>")
dest = Path(__file__).with_name("bench-single-cell.svg")
dest.write_text("\n".join(out), encoding="utf-8")
print(f"wrote {dest}")
