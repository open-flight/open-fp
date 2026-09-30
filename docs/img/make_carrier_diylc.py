#!/usr/bin/env python3
"""Generate hardware/carrier-stripboard.diy: the ADC carrier as a DIY Layout Creator project.

Same layout as docs/img/carrier-stripboard.svg (the cuts, links and breakout positions are
imported from make_carrier_layout.py), for editing in DIYLC (https://github.com/bancika/diy-layout-creator).
Open it with File > Open. Coordinates are in inches; the board's top-left corner is at (1, 1)
and hole (column c, row r) sits at (1 + 0.1 c, 1 + 0.1 (r + 1)), which is how DIYLC places
stripboard holes. Strips run left-right (HORIZONTAL).
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from _svg import WIRE
from make_carrier_layout import COLS, HEEL_CS, MODULES, RAILS, ROW_NAMES, ROWS, cuts, links

OUT = Path(__file__).resolve().parents[2] / "hardware" / "carrier-stripboard.diy"
X0, Y0 = 1.0, 1.0  # board corner, inches
CABLE = {"E+": "f4f4f4", "E−": "222222", "S": "d64545", "shield": "9aa5b1"}


def at(col: int, row: str) -> tuple[float, float]:
    return round(X0 + 0.1 * col, 3), round(Y0 + 0.1 * (ROW_NAMES.index(row) + 1), 3)


def hexc(color: str) -> str:
    return color.lstrip("#").lower()


def pt(p) -> str:
    return f'<point x="{p[0]}" y="{p[1]}"/>'


class Project:
    def __init__(self):
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

    def label(self, p, text: str, size: int = 10, color: str = "000000", bold: bool = False):
        self.parts.append(f"""    <diylc.misc.Label>
      <name>{self.name("L")}</name>
      {pt(p)}
      <text>{escape(text)}</text>
      <font name="Dialog" size="{size}" style="{1 if bold else 0}"/>
      <color hex="{color}"/>
      <center>false</center>
      <horizontalAlignment>CENTER</horizontalAlignment>
      <verticalAlignment>CENTER</verticalAlignment>
      <orientation>DEFAULT</orientation>
    </diylc.misc.Label>""")

    def xml(self) -> str:
        body = "\n".join(self.parts)
        return f"""<?xml version="1.0" encoding="UTF-8" ?>
<project>
  <fileVersion>
    <major>4</major>
    <minor>34</minor>
    <build>0</build>
  </fileVersion>
  <title>open-fp ADC carrier (toe)</title>
  <author>open-fp</author>
  <width value="29.0" unit="cm"/>
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


def build() -> str:
    p = Project()
    p.board()
    # links first: they run under the breakouts
    for (c1, r1), (c2, r2), key, lab in links():
        unit = next((n for n, x0, _ in MODULES if x0 <= c1 < x0 + 9 and lab != "tie"), "")
        name = f"{unit} {lab}" if unit else f"tie {r1}-{r2} col {c1}"
        p.jumper(at(c1, r1), at(c2, r2), hexc(WIRE[key]), name)
    for c, r in cuts():
        p.cut(at(c, r))
    for name, x0, cs in MODULES:
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
            (round(ax + 0.2, 3), round(Y0 + 0.1 * (ROWS + 1) + 0.5, 3)),
            f"cell {name}",
            9,
        )
    # L1's DRDY off the top of its DRDY pin
    name, x0, _ = MODULES[0]
    drdy = at(x0 + 7, "H")
    p.wire(drdy, (round(drdy[0] - 0.15, 3), round(Y0 - 0.25, 3)), hexc(WIRE["drdy"]))
    p.label((round(drdy[0] - 0.15, 3), round(Y0 - 0.35, 3)), "L1 DRDY -> D2", 8, hexc(WIRE["drdy"]))
    # bus in/out and rail names
    for col, dx, text in ((1, -0.4, "BUS IN (from UNO Q)"), (COLS, 0.4, "BUS OUT (to heel)")):
        for row in "ABJKL":
            a = at(col, row)
            p.wire(a, (round(a[0] + dx, 3), a[1]), hexc(WIRE[RAILS[row][1]]))
        x, y = at(col, "M")
        p.label((round(x + dx, 3), y), text, 8, bold=True)
    for row, (rail, key) in RAILS.items():
        x, y = at(COLS, row)
        p.label((round(x + 0.75, 3), y), rail, 9, hexc(WIRE[key]), True)
    bottom = Y0 + 0.1 * (ROWS + 1)
    notes = [
        "open-fp ADC carrier, toe (L1 L2 R1 R2). Heel: same board with L3 L4 R3 R4, CS <- "
        + ", ".join(HEEL_CS)
        + "; BUS OUT unused.",
        "Cell cable (JST at the cradle): E+ white on N, E- black on O, S red on P, shield grey to O.",
        "Fit all links before the breakouts (they run underneath). Red = cut the strip at that hole.",
        "Breakouts: pins down, header spacer under. R1 (AVDD-AIN1) and R2 (AIN1-AGND) solder on top.",
        "Mount with ~3 mm nylon standoffs in strips I or M. Steps: docs/harness.md.",
    ]
    for i, n in enumerate(notes):
        p.label((round(X0 + 1.9, 3), round(bottom + 0.8 + 0.15 * i, 3)), n, 9)
    return p.xml()


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT}")
