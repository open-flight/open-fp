#!/usr/bin/env python3
"""Generate docs/img/harness.svg: UNO Q -> two ADC carriers -> 8 load cells.

Topology, not a physical layout: 14 UNO Q pins, one wire each. The 5 shared bus lines run
Q -> toe carrier -> heel carrier; each ADS1220 gets its own chip select; only L1's DRDY is
wired. Pins follow docs/wiring.md (R4's CS is A2, not D10).
"""
from pathlib import Path

INK, MUTED, ACCENT = "#1F2933", "#5F6B78", "#C2410C"
Q_FILL, Q_S = "#E8F1F2", "#2F6F73"
CAR_FILL, CAR_S = "#F6F4EF", "#7A7063"
MOD_FILL, MOD_S = "#EEF0F8", "#4B5694"
BUS = [("3V3", "#D64545"), ("GND", "#222222"), ("SCLK · D13", "#2F80ED"),
       ("MOSI · D11", "#27AE60"), ("MISO · D12", "#9B51E0")]
CS_COLOR, DRDY_COLOR = "#E2A400", "#EB5757"
out: list[str] = []


def add(s):
    out.append(s)


def text(x, y, s, size=13, fill=INK, weight=400, anchor="start"):
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{s}</text>')


def rect(x, y, w, h, fill, stroke, rx=8, sw=1.5, dash=""):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}"{extra}/>')


def poly(points, color, width=2.2):
    d = " L".join(f"{x},{y}" for x, y in points)
    add(f'<path d="M{d}" fill="none" stroke="{color}" stroke-width="{width}" '
        f'stroke-linejoin="round" stroke-linecap="round"/>')


def dot(x, y, color):
    add(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{color}"/>')


W, H = 1400, 980
Y0 = 40          # everything below the title is offset by this
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
    'font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif">')
add(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')
text(40, 40, "Harness: UNO Q → two ADC carriers → 8 load cells", 24, INK, 700)
text(40, 64, "14 pins on the UNO Q, one wire each. The 5 shared lines chain from the toe carrier to "
     "the heel carrier; every ADC has its own chip select.", 14, MUTED)

# ---- UNO Q ---------------------------------------------------------------------------------
QX, QR = 40, 220                      # box left, pin column
pins_toe = [("D8", "R2 CS"), ("D7", "R1 CS"), ("D4", "L2 CS"), ("D3", "L1 CS"), ("D2", "L1 DRDY")]
pins_bus = ["3V3", "GND", "D13", "D11", "D12"]
pins_heel = [("D5", "L3 CS"), ("D6", "L4 CS"), ("D9", "R3 CS"), ("A2", "R4 CS")]
py_toe = [Y0 + 190 + 40 * i for i in range(5)]
py_bus = [Y0 + 420 + 40 * i for i in range(5)]
py_heel = [Y0 + 660 + 40 * i for i in range(4)]
rect(QX, Y0 + 140, QR - QX, 690, Q_FILL, Q_S, 12, 2)
text((QX + QR) / 2, Y0 + 172, "Arduino UNO Q", 16, Q_S, 700, "middle")
for (p, what), y in zip(pins_toe, py_toe):
    add(f'<circle cx="{QR}" cy="{y}" r="5" fill="#FFF" stroke="{Q_S}" stroke-width="2"/>')
    text(QR - 12, y + 4, p, 13, Q_S, 700, "end")
    text(QX + 12, y + 4, what, 11, MUTED)
for (p, (_, color)), y in zip(zip(pins_bus, BUS), py_bus):
    add(f'<circle cx="{QR}" cy="{y}" r="5" fill="#FFF" stroke="{color}" stroke-width="2"/>')
    text(QR - 12, y + 4, p, 13, color, 700, "end")
for (p, what), y in zip(pins_heel, py_heel):
    add(f'<circle cx="{QR}" cy="{y}" r="5" fill="#FFF" stroke="{Q_S}" stroke-width="2"/>')
    text(QR - 12, y + 4, p, 13, Q_S, 700, "end")
    text(QX + 12, y + 4, what, 11, MUTED)
text((QX + QR) / 2, Y0 + 812, "D10, D0, D1: unused", 11, ACCENT, 600, "middle")

# ---- carriers ----------------------------------------------------------------------------------
CX0, CX1 = 400, 1180
MOD_W, MOD_H = 150, 120
MOD_X = [440, 620, 800, 980]


def module(x, y, name, where, cable):
    rect(x, y, MOD_W, MOD_H, MOD_FILL, MOD_S, 6, 1.5)
    text(x + MOD_W / 2, y + 26, name, 18, MOD_S, 700, "middle")
    text(x + MOD_W / 2, y + 44, "ADS1220", 11, MUTED, 400, "middle")
    text(x + MOD_W / 2, y + 66, where, 11, INK, 400, "middle")
    text(x + MOD_W / 2, y + 84, "R1/R2 at the module", 11, MUTED, 400, "middle")
    rect(x + 12, y + 94, MOD_W - 24, 18, "#FFFFFF", MOD_S, 3, 1)
    text(x + MOD_W / 2, y + 107, f"JST → cell ({cable})", 10, MOD_S, 600, "middle")


# toe carrier: CS from above, bus rails along the bottom
TY = Y0 + 170
rect(CX0, TY, CX1 - CX0, 250, CAR_FILL, CAR_S, 12, 2)
text(CX1 + 84, TY + 60, "Toe carrier", 15, CAR_S, 700)
text(CX1 + 84, TY + 80, "+y end pad", 12, MUTED)
text(CX1 + 84, TY + 98, "L1 L2 R1 R2", 12, MUTED)
toe_mods = [("L1", "toe outer", "450 mm"), ("L2", "toe inner", "250 mm"),
            ("R1", "toe inner", "250 mm"), ("R2", "toe outer", "450 mm")]
MTY = TY + 50
for x, (n, w, c) in zip(MOD_X, toe_mods):
    module(x, MTY, n, w, c)
toe_rail = [TY + 190 + 12 * i for i in range(5)]
for (label, color), y in zip(BUS, toe_rail):
    poly([(CX0 + 10, y), (CX1 + 10, y)], color, 2.4)
for x in MOD_X:
    for i, ((_, color), y) in enumerate(zip(BUS, toe_rail)):
        tx = x + 25 + 22 * i
        poly([(tx, MTY + MOD_H), (tx, y)], color, 1.6)
        dot(tx, y, color)

# heel carrier: bus rails along the top (order reversed by the U-turn), CS from below
HY = Y0 + 490
rect(CX0, HY, CX1 - CX0, 250, CAR_FILL, CAR_S, 12, 2)
text(CX1 + 84, HY + 150, "Heel carrier", 15, CAR_S, 700)
text(CX1 + 84, HY + 170, "−y end pad", 12, MUTED)
text(CX1 + 84, HY + 188, "L3 L4 R3 R4", 12, MUTED)
heel_rail = [HY + 12 + 12 * (4 - i) for i in range(5)]   # 3V3 ends up at the bottom
for (label, color), y in zip(BUS, heel_rail):
    poly([(CX0 + 10, y), (CX1 + 10, y)], color, 2.4)
heel_mods = [("L3", "heel inner", "250 mm"), ("L4", "heel outer", "450 mm"),
             ("R3", "heel outer", "450 mm"), ("R4", "heel inner", "250 mm")]
MHY = HY + 84
for x, (n, w, c) in zip(MOD_X, heel_mods):
    module(x, MHY, n, w, c)
    for i, ((_, color), y) in enumerate(zip(BUS, heel_rail)):
        tx = x + 25 + 22 * i
        poly([(tx, y), (tx, MHY)], color, 1.6)
        dot(tx, y, color)

# chain: toe rails -> heel rails, nested so nothing crosses
for i, ((label, color), yt, yh) in enumerate(zip(BUS, toe_rail, heel_rail)):
    xc = CX1 + 70 - 12 * i
    poly([(CX1 + 10, yt), (xc, yt), (xc, yh), (CX1 + 10, yh)], color, 2.4)
text(CX1 + 84, (TY + HY) / 2 + 170, "5 bus wires", 13, INK, 700)
text(CX1 + 84, (TY + HY) / 2 + 188, "chained toe → heel", 12, MUTED)

# ---- Q -> toe carrier: CS + DRDY over the top ---------------------------------------------------
toe_cols = [250 + 20 * i for i in range(5)]
toe_chan = [TY - 90 + 15 * i for i in range(5)]
toe_drop = [MOD_X[3] + 75, MOD_X[2] + 75, MOD_X[1] + 75, MOD_X[0] + 75, MOD_X[0] + 20]
for i, y in enumerate(py_toe):
    color = DRDY_COLOR if i == 4 else CS_COLOR
    poly([(QR, y), (toe_cols[i], y), (toe_cols[i], toe_chan[i]), (toe_drop[i], toe_chan[i]),
          (toe_drop[i], MTY)], color)
text(toe_drop[4] + 6, MTY - 8, "DRDY", 10, DRDY_COLOR, 700)
for x in MOD_X:
    text(x + 81, MTY - 8, "CS", 10, CS_COLOR, 700)

# ---- Q -> bus rails (toe carrier) --------------------------------------------------------------
for i, (y, yr, (_, color)) in enumerate(zip(py_bus, toe_rail, BUS)):
    col = 350 + 10 * i
    poly([(QR, y), (col, y), (col, yr), (CX0 + 10, yr)], color, 2.4)

# ---- Q -> heel carrier: CS under the bottom ------------------------------------------------------
heel_cols = [330, 310, 290, 270]
heel_chan = [HY + 268 + 15 * i for i in range(4)]
for i, y in enumerate(py_heel):
    xd = MOD_X[i] + 75
    poly([(QR, y), (heel_cols[i], y), (heel_cols[i], heel_chan[i]), (xd, heel_chan[i]),
          (xd, MHY + MOD_H)], CS_COLOR)
    text(xd + 6, MHY + MOD_H + 14, "CS", 10, CS_COLOR, 700)

# ---- legend / notes ------------------------------------------------------------------------------
LY = Y0 + 872
items = BUS + [("Chip select (one per ADC)", CS_COLOR), ("DRDY (L1 only)", DRDY_COLOR)]
for i, (label, color) in enumerate(items):
    x = 40 + (i % 4) * 250
    y = LY + (i // 4) * 22
    poly([(x, y - 4), (x + 26, y - 4)], color, 3)
    text(x + 34, y, label, 12)
text(1060, LY, "Cable shields: to the carrier's GND rail only.", 12, MUTED)
text(1060, LY + 18, "Cable lengths: JST to ADC (wiring.md §4).", 12, MUTED)
text(1060, LY + 36, "Carrier contents: docs/wiring.md §8.", 12, MUTED)

add("</svg>")
dest = Path(__file__).with_name("harness.svg")
dest.write_text("\n".join(out), encoding="utf-8")
print(f"wrote {dest}")
