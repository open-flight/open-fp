#!/usr/bin/env python3
"""Generate the two ADC carriers as DIY Layout Creator projects, one per plate.

hardware/carrier-stripboard.diy is plate L's carrier (L1-L4, BUS IN from the UNO Q) and
hardware/carrier-stripboard-right.diy is plate R's (R1-R4, BUS IN from plate L's BUS OUT,
BUS OUT empty). Same board as docs/img/carrier-stripboard.svg (the cuts, links and breakout positions are
imported from make_carrier_layout.py), for editing in DIYLC (https://github.com/bancika/diy-layout-creator).
Open it with File > Open. Coordinates are in inches; the board's top-left corner is at (1, 1)
and hole (column c, row r) sits at (1 + 0.1 c, 1 + 0.1 (r + 1)), which is how DIYLC places
stripboard holes. Strips run left-right (HORIZONTAL).
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from _svg import WIRE
from make_carrier_layout import COLS, MODULES, RAILS, RIGHT, RIGHT_CS, ROW_NAMES, ROWS, cuts, links

HARDWARE = Path(__file__).resolve().parents[2] / "hardware"
OUT = {"L": HARDWARE / "carrier-stripboard.diy", "R": HARDWARE / "carrier-stripboard-right.diy"}
PLATE_NAME = {"L": "left", "R": "right"}
X0, Y0 = 1.0, 1.0  # board corner, inches
CABLE = {"E+": "f4f4f4", "E−": "222222", "S": "d64545", "shield": "9aa5b1"}


def modules(plate: str) -> list[tuple[str, int, str]]:
    """(unit, x0, CS pin on the UNO Q) for each breakout: the same board positions on both."""
    if plate == "L":
        return list(MODULES)
    return [(name, x0, cs) for name, (_, x0, _), cs in zip(RIGHT, MODULES, RIGHT_CS)]


def at(col: int, row: str) -> tuple[float, float]:
    return round(X0 + 0.1 * col, 3), round(Y0 + 0.1 * (ROW_NAMES.index(row) + 1), 3)


def hexc(color: str) -> str:
    return color.lstrip("#").lower()


def pt(p) -> str:
    return f'<point x="{p[0]}" y="{p[1]}"/>'


class Project:
    def __init__(self, title: str):
        self.title = title
        self.parts: list[str] = []
        self.count: dict[str, int] = {}

    def name(self, prefix: str) -> str:
        self.count[prefix] = self.count.get(prefix, 0) + 1
        return f"{prefix}{self.count[prefix]}"

    def board(self):
        a, b = (X0, Y0), (round(X0 + 0.1 * (COLS + 1), 3), round(Y0 + 0.1 * (ROWS + 1), 3))
        self.parts.append(f"""    <diylc.boards.VeroBoard>
      <name>Carrier</name>
      <alpha>127</alpha>
      <value></value>
      <controlPoints>
        {pt(a)}
        {pt(b)}
      </controlPoints>
      <firstPoint x="{a[0]}" y="{a[1]}"/>
      <secondPoint x="{b[0]}" y="{b[1]}"/>
      <boardColor hex="f8ebb3"/>
      <borderColor hex="ada47d"/>
      <coordinateColor hex="000000"/>
      <xType>Numbers</xType>
      <coordinateOrigin>Top_Left</coordinateOrigin>
      <coordinateDisplay>Both_Sides</coordinateDisplay>
      <yType>Letters</yType>
      <mode>TwoPoints</mode>
      <spacing value="0.1" unit="in"/>
      <stripColor hex="da8a67"/>
      <orientation>HORIZONTAL</orientation>
    </diylc.boards.VeroBoard>""")

    def cut(self, p):
        self.parts.append(f"""    <diylc.connectivity.TraceCut>
      <name>{self.name("Cut")}</name>
      <size value="0.08" unit="in"/>
      <fillColor hex="ffffff"/>
      <borderColor hex="ff0000"/>
      <boardColor hex="f8ebb3"/>
      <cutBetweenHoles>false</cutBetweenHoles>
      <orientation>HORIZONTAL</orientation>
      <holeSpacing value="0.1" unit="in"/>
      {pt(p)}
    </diylc.connectivity.TraceCut>""")

    def jumper(self, a, b, color: str, label: str):
        mid = (round((a[0] + b[0]) / 2, 3), round((a[1] + b[1]) / 2, 3))
        self.parts.append(f"""    <diylc.connectivity.Jumper>
      <name>{escape(label)}</name>
      <alpha>127</alpha>
      <points>
        {pt(a)}
        {pt(b)}
        {pt(mid)}
      </points>
      <bodyColor hex="ffffff"/>
      <borderColor hex="000000"/>
      <labelColor hex="000000"/>
      <leadColor hex="{color}"/>
      <display>NONE</display>
      <flipStanding>false</flipStanding>
      <moveLabel>false</moveLabel>
      <style>SOLID</style>
    </diylc.connectivity.Jumper>""")

    def wire(self, a, b, color: str):
        self.parts.append(f"""    <diylc.connectivity.HookupWire>
      <name>{self.name("W")}</name>
      <alpha>127</alpha>
      <controlPoints2>
        {pt(a)}
        {pt(b)}
      </controlPoints2>
      <color hex="{color}"/>
      <pointCount>TWO</pointCount>
      <style>SOLID</style>
      <smooth>true</smooth>
      <lastUpdatePointIndex>-1</lastUpdatePointIndex>
      <gauge>_24</gauge>
      <striped>false</striped>
      <stripeColor hex="ffff00"/>
    </diylc.connectivity.HookupWire>""")

    def header(self, top, pins: int, label: str):
        points = "\n        ".join(pt((top[0], round(top[1] + 0.1 * i, 3))) for i in range(pins))
        self.parts.append(f"""    <diylc.electromechanical.PinHeader>
      <name>{escape(label)}</name>
      <alpha>127</alpha>
      <orientation>DEFAULT</orientation>
      <controlPoints>
        {points}
      </controlPoints>
      <rowCount>1</rowCount>
      <columnCount>{pins}</columnCount>
      <spacing value="0.1" unit="in"/>
      <shrouded>false</shrouded>
      <bodyColor hex="808080"/>
      <shroudColor hex="595959"/>
    </diylc.electromechanical.PinHeader>""")

    def rect(self, a, b, color: str, alpha: int = 50):
        self.parts.append(f"""    <diylc.shapes.Rectangle>
      <name>{self.name("RECT")}</name>
      <alpha>{alpha}</alpha>
      <value></value>
      <controlPoints>
        {pt(a)}
        {pt(b)}
      </controlPoints>
      <firstPoint x="{a[0]}" y="{a[1]}"/>
      <secondPoint x="{b[0]}" y="{b[1]}"/>
      <color hex="{color}"/>
      <borderColor hex="5b3b8c"/>
      <borderThickness value="0.3" unit="mm"/>
      <edgeRadius value="1.0" unit="mm"/>
    </diylc.shapes.Rectangle>""")

    def label(
        self,
        p,
        text: str,
        size: int = 10,
        color: str = "000000",
        bold: bool = False,
        align="CENTER",
    ):
        self.parts.append(f"""    <diylc.misc.Label>
      <name>{self.name("L")}</name>
      {pt(p)}
      <text>{escape(text)}</text>
      <font name="Dialog" size="{size}" style="{1 if bold else 0}"/>
      <color hex="{color}"/>
      <center>false</center>
      <horizontalAlignment>{align}</horizontalAlignment>
      <verticalAlignment>CENTER</verticalAlignment>
      <orientation>DEFAULT</orientation>
    </diylc.misc.Label>""")

    def resistor(self, a, b, name: str):
        mid = (round((a[0] + b[0]) / 2, 3), round((a[1] + b[1]) / 2, 3))
        self.parts.append(f"""    <diylc.passive.Resistor>
      <name>{name}</name>
      <alpha>127</alpha>
      <length value="6.3" unit="mm"/>
      <width value="2.3" unit="mm"/>
      <points>
        {pt(a)}
        {pt(b)}
        {pt(mid)}
      </points>
      <bodyColor hex="82cffd"/>
      <borderColor hex="5b90b1"/>
      <labelColor hex="000000"/>
      <leadColor hex="cccccc"/>
      <display>BOTH</display>
      <flipStanding>false</flipStanding>
      <labelOriantation>Directional</labelOriantation>
      <moveLabel>false</moveLabel>
      <hideShortLeads>false</hideShortLeads>
      <value value="1.0" unit="K"/>
      <power>HALF</power>
      <colorCode>NONE</colorCode>
      <shape>Standard</shape>
    </diylc.passive.Resistor>""")

    def pad(self, p, color: str = "c9a227"):
        self.parts.append(f"""    <diylc.connectivity.SolderPad>
      <name>{self.name("Pad")}</name>
      <size value="0.09" unit="in"/>
      <color hex="{color}"/>
      {pt(p)}
      <type>SQUARE</type>
      <holeSize value="0.8" unit="mm"/>
      <layer>_1</layer>
    </diylc.connectivity.SolderPad>""")

    def xml(self) -> str:
        body = "\n".join(self.parts)
        return f"""<?xml version="1.0" encoding="UTF-8" ?>
<project>
  <fileVersion>
    <major>4</major>
    <minor>34</minor>
    <build>0</build>
  </fileVersion>
  <title>{escape(self.title)}</title>
  <author>open-fp</author>
  <width value="36.0" unit="cm"/>
  <height value="21.0" unit="cm"/>
  <gridSpacing value="0.1" unit="in"/>
  <dotSpacing>1</dotSpacing>
  <components>
{body}
  </components>
  <groups/>
  <lockedLayers/>
  <lockedComponents/>
  <hiddenLayers/>
  <font name="Dialog" size="12" style="0"/>
</project>
"""


def inset(p: Project, plate: str):
    """Zoomed top view of one breakout: pin names, R1/R2 and the wires soldered on top."""
    left = ["AGND", "AVDD", "REFP0", "REFN0", "AIN3", "AIN2", "AIN1", "AIN0"]
    right = ["DGND", "DVDD", "CLK", "CS", "SCLK", "MOSI", "MISO", "DRDY"]
    lx, rx, y0, dy = 9.3, 10.7, 1.2, 0.2
    ys = [round(y0 + dy * i, 3) for i in range(8)]
    p.label((10.0, 0.62), "Top of each breakout (all four alike)", 11, bold=True)
    p.label((10.0, 0.8), "the same pins as rows A-H on the board; R1/R2 solder on top", 8, "444444")
    p.rect(
        (round(lx - 0.15, 3), round(y0 - 0.15, 3)),
        (round(rx + 0.15, 3), round(ys[-1] + 0.15, 3)),
        "7b4fb8",
        40,
    )
    for y, a, b in zip(ys, left, right):
        p.pad((lx, y))
        p.pad((rx, y))
        p.label((round(lx + 0.1, 3), y), a, 8, align="LEFT")
        p.label((round(rx - 0.1, 3), y), b, 8, align="RIGHT")
    for y, row in zip(ys, "ABCDEFGH"):
        p.label((round(lx - 0.9, 3), y), row, 8, "888888")
    # R1: AVDD -> AIN1, R2: AIN1 -> AGND, side by side left of the pin column
    r1x, r2x = round(lx - 0.35, 3), round(lx - 0.7, 3)
    avdd, ain1, agnd = ys[1], ys[6], ys[0]
    p.resistor((r1x, avdd), (r1x, ain1), "R1")
    p.wire((r1x, avdd), (lx, avdd), hexc(WIRE["3v3"]))
    p.wire((r1x, ain1), (lx, ain1), hexc(WIRE["ref"]))
    p.resistor((r2x, agnd), (r2x, ain1), "R2")
    p.wire((r2x, agnd), (lx, agnd), hexc(WIRE["gnd"]))
    p.wire((r2x, ain1), (r1x, ain1), hexc(WIRE["ref"]))
    # wires soldered to the top of pins
    on_top = [(ys[3], "CS wire from the UNO Q", "cs")]
    if plate == "L":
        on_top.append((ys[7], "L1 only: DRDY -> D2", "drdy"))
    for y, text, key in on_top:
        p.wire((rx, y), (round(rx + 0.45, 3), y), hexc(WIRE[key]))
        p.label((round(rx + 0.5, 3), y), text, 8, hexc(WIRE[key]), True, "LEFT")
    notes = [
        "R1 AVDD-AIN1 and R2 AIN1-AGND: 1 k 0.1 %, a matched pair",
        "(any equal pair 680 R - 2 k; never mixed values). AIN1 then sits",
        "at ~1.65 V, the other half of the bridge.",
        "Every pin also goes through to its strip below (rows A-H).",
    ]
    for i, n in enumerate(notes):
        p.label((round(lx - 0.75, 3), round(ys[-1] + 0.45 + 0.14 * i, 3)), n, 8, align="LEFT")


def build(plate: str = "L") -> str:
    mods = modules(plate)
    units = " ".join(name for name, _, _ in mods)
    p = Project(f"open-fp ADC carrier ({PLATE_NAME[plate]} plate)")
    p.board()
    # links first: they run under the breakouts
    for (c1, r1), (c2, r2), key, lab in links():
        unit = next((n for n, x0, _ in mods if x0 <= c1 < x0 + 9 and lab != "tie"), "")
        name = f"{unit} {lab}" if unit else f"tie {r1}-{r2} col {c1}"
        p.jumper(at(c1, r1), at(c2, r2), hexc(WIRE[key]), name)
    for c, r in cuts():
        p.cut(at(c, r))
    for name, x0, cs in mods:
        (ax, ay), (dx, hy) = at(x0, "A"), at(x0 + 7, "H")
        p.rect(
            (round(ax - 0.06, 3), round(ay - 0.06, 3)),
            (round(dx + 0.06, 3), round(hy + 0.06, 3)),
            "7b4fb8",
        )
        p.header((ax, ay), 8, f"{name} AGND..AIN0")
        p.header((dx, ay), 8, f"{name} DGND..DRDY")
        p.label((round((ax + dx) / 2, 3), round(ay - 0.32, 3)), name, 12, "5b3b8c", True)
        p.label((round((ax + dx) / 2, 3), round(ay - 0.2, 3)), f"CS <- {cs}", 8, hexc(WIRE["cs"]))
        # CS wire off the top of the CS pin (right column, row D)
        cs_pin = at(x0 + 7, "D")
        p.wire(cs_pin, (round(cs_pin[0] + 0.25, 3), round(Y0 - 0.25, 3)), hexc(WIRE["cs"]))
        # cell cable: E+ on N (3V3), E- on O (GND), S on P; shield to strip O
        below = round(Y0 + 0.1 * (ROWS + 1) + 0.35, 3)
        for row, key, dx in (("N", "E+", -0.3), ("O", "E−", -0.15), ("P", "S", 0.0)):
            a = at(x0 + 2, row)
            p.wire(a, (round(a[0] + dx, 3), below), CABLE[key])
        sh = at(x0 + 3, "O")
        p.wire(sh, (round(sh[0] + 0.1, 3), below), CABLE["shield"])
        p.label(
            (round(ax + 0.15, 3), round(Y0 + 0.1 * (ROWS + 1) + 0.5, 3)),
            f"{name} cable",
            9,
            bold=True,
        )
    if plate == "L":
        # L1's DRDY off the top of its DRDY pin
        name, x0, _ = mods[0]
        drdy = at(x0 + 7, "H")
        p.wire(drdy, (round(drdy[0] - 0.15, 3), round(Y0 - 0.25, 3)), hexc(WIRE["drdy"]))
        p.label(
            (round(drdy[0] - 0.15, 3), round(Y0 - 0.35, 3)), "L1 DRDY -> D2", 8, hexc(WIRE["drdy"])
        )
    # bus in/out: plate L's BUS IN comes from the UNO Q (pin on each wire) and its BUS OUT
    # goes on to plate R's BUS IN; plate R's BUS OUT stays empty
    if plate == "L":
        bus_in = {"A": "GND", "B": "3V3", "J": "SCLK <- D13", "K": "MOSI <- D11", "L": "MISO <- D12"}
        in_from, out_to = "BUS IN from UNO Q", "-> plate R BUS IN"
    else:
        bus_in = {"A": "GND", "B": "3V3", "J": "SCLK", "K": "MOSI", "L": "MISO"}
        in_from, out_to = "BUS IN from plate L BUS OUT", "empty"
    for row in "ABJKL":
        key = hexc(WIRE[RAILS[row][1]])
        a = at(1, row)
        p.wire(a, (round(a[0] - 0.4, 3), a[1]), key)
        p.label((round(a[0] - 0.45, 3), a[1]), bus_in[row], 8, key, True, "RIGHT")
        if plate == "L":
            b = at(COLS, row)
            p.wire(b, (round(b[0] + 0.4, 3), b[1]), key)
    x, y = at(1, "M")
    p.label((round(x - 0.45, 3), y), in_from, 8, bold=True, align="RIGHT")
    # what every strip is for, left-aligned beside the board
    bus_out = f"BUS OUT {out_to}"
    strips = {
        "A": (f"AGND | DGND pins; GND rail, never cut. {bus_out}", "gnd"),
        "B": (f"AVDD | DVDD pins; 3V3 rail, never cut. {bus_out}", "3v3"),
        "C": ("REFP0 | CLK   (link C->B, CLK link C->A)", None),
        "D": ("REFN0 | CS    (link D->A; CS wire on top of the pin)", None),
        "E": ("AIN3 | SCLK   (SCLK link E->J, diagonal, insulated)", None),
        "F": ("AIN2 | MOSI   (MOSI link F->K)", None),
        "G": ("AIN1 | MISO   (MISO link G->L; R1/R2 meet at AIN1)", None),
        "H": (
            "AIN0 | DRDY   (link H->P to the cable's S)"
            + ("" if plate == "L" else "; DRDY not wired on plate R"),
            None,
        ),
        "I": ("spare: mounting holes", None),
        "J": (f"SCLK rail. {bus_out}", "sck"),
        "K": (f"MOSI rail. {bus_out}", "mosi"),
        "L": (f"MISO rail. {bus_out}", "miso"),
        "M": ("spare: mounting holes", None),
        "N": ("3V3 (tie link col 19 to B): cable E+", "3v3"),
        "O": ("GND (tie link col 10 to A): cable E- and shield", "gnd"),
        "P": ("cable S -> AIN0; cut so each unit has its own", "sig"),
        "Q": ("spare", None),
    }
    for row, (text, key) in strips.items():
        x, y = at(COLS, row)
        color = hexc(WIRE[key]) if key else "444444"
        p.label((round(x + 0.5, 3), y), f"{row}  {text}", 8, color, key is not None, "LEFT")
    p.label(
        (round(at(1, "A")[0] + 1.8, 3), round(Y0 - 0.62, 3)),
        f"open-fp ADC carrier: {PLATE_NAME[plate]} plate ({units}), component side",
        13,
        bold=True,
    )
    inset(p, plate)
    bottom = Y0 + 0.1 * (ROWS + 1)
    cs_wires = ", ".join(f"{name} <- {cs}" for name, _, cs in mods)
    if plate == "L":
        first = [
            f"To the UNO Q: the 5 bus wires into BUS IN and the CS wires ({cs_wires}), plus L1 DRDY -> D2.",
            "BUS OUT chains to the plate R carrier's BUS IN, strip to strip (hardware/carrier-stripboard-right.diy).",
        ]
    else:
        first = [
            f"To the UNO Q: only the 4 CS wires ({cs_wires}). A2, not D10. No DRDY on this carrier.",
            "BUS IN: 5 wires from the plate L carrier's BUS OUT, strip to strip (A GND, B 3V3, J SCLK, K MOSI, L MISO).",
            "BUS OUT stays empty. The plate L carrier is hardware/carrier-stripboard.diy.",
        ]
    notes = first + [
        "Each cell has 3 wires; its JST at the cradle joins them to a shielded cable. White E+ -> N, black E- -> O,",
        "red S -> P. Grey is the cable's shield (drain wire), not a cell wire: GND on strip O here, nothing at the cradle.",
        "Pale circles = cut the strip at that hole (from the copper side; check with a meter).",
        "Fit all links before the breakouts: they run underneath. Breakouts pins down, header spacer under.",
        "Mount with ~3 mm nylon standoffs in strip I or M. Full steps: docs/harness.md.",
    ]
    for i, n in enumerate(notes):
        p.label((round(X0, 3), round(bottom + 0.8 + 0.15 * i, 3)), n, 9, align="LEFT")
    return p.xml()


if __name__ == "__main__":
    for plate, path in OUT.items():
        path.write_text(build(plate), encoding="utf-8")
        print(f"wrote {path}")
