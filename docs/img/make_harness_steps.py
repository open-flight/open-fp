#!/usr/bin/env python3
"""Generate the step-by-step system wiring diagrams used by docs/harness.md.

  harness-1-unit.svg     one unit: ADS1220 breakout + R1/R2 + cell connector, 6 wires out
  harness-2-carrier.svg  four units on a carrier: 5 bus rails, BUS IN / BUS OUT, CS and cells
  harness-3-system.svg   the whole system: UNO Q -> toe carrier -> heel carrier, 8 cells

Breakout pin names/order are the purple ADS1220 board used in this build; UNO Q pins follow
docs/wiring.md (R4's CS is A2, not D10).
"""

from pathlib import Path

from _svg import ACCENT, BUS, INK, MUTED, WIRE, Svg

HERE = Path(__file__).parent
MODULE, MODULE_S = "#EFEAF7", "#5B3B8C"
CAR, CAR_S = "#F6F4EF", "#7A7063"
Q_FILL, Q_S = "#E8F1F2", "#2F6F73"
CELL, CELL_S = "#E9ECEF", "#56626F"


# ---------------------------------------------------------------------------------------------
# Step 1: one unit
# ---------------------------------------------------------------------------------------------
def unit() -> Svg:
    s = Svg(1280, 760)
    s.step_title(1, "Build a unit (×8)", "A unit is one ADS1220 breakout, its two bridge resistors, "
                 "and its load-cell cable, soldered on. The plug-in JST is at the cradle. Every unit is identical.")
    MX, MY, MW = 540, 150, 250
    left = [("DRDY", 120), ("MISO", 170), ("MOSI", 220), ("SCLK", 270), ("CS", 320),
            ("CLK", 370), ("DVDD", 430), ("DGND", 480)]
    right = [("AIN0", 120), ("AIN1", 170), ("AIN2", 220), ("AIN3", 270), ("REFN0", 330),
             ("REFP0", 380), ("AVDD", 430), ("AGND", 480)]
    s.rect(MX, MY + 40, MW, 480, MODULE, MODULE_S, 10, 2)
    s.text(MX + MW / 2, MY + 72, "ADS1220 breakout", 16, MODULE_S, 700, "middle")
    s.text(MX + MW / 2, MY + 90, "pins as printed on the board", 11, MUTED, 400, "middle")
    y = {}
    for name, dy in left:
        s.pin(MX, MY + dy, name, "l", MODULE_S)
        y[name] = MY + dy
    for name, dy in right:
        s.pin(MX + MW, MY + dy, name, "r", MODULE_S)
        y[name] = MY + dy

    # the unit's connector to the carrier: 6 wires (+ DRDY on L1)
    HX = 250
    s.rect(60, MY + 40, 190, 480, "#FFFFFF", INK, 10, 2)
    s.text(155, MY + 70, "Unit → carrier", 15, INK, 700, "middle")
    s.text(155, MY + 88, "the only wires that leave a unit", 11, MUTED, 400, "middle")
    links = [("DRDY*", "DRDY", "drdy"), ("MISO", "MISO", "miso"), ("MOSI", "MOSI", "mosi"),
             ("SCLK", "SCLK", "sck"), ("CS", "CS", "cs"), ("3V3", "DVDD", "3v3"), ("GND", "DGND", "gnd")]
    for label, pin, key in links:
        s.pin(HX, y[pin], label, "r", INK)
        s.line([(HX, y[pin]), (MX, y[pin])], WIRE[key], dash="7 5" if pin == "DRDY" else "")
    s.text(155, MY + 505, "* DRDY: L1 only", 12, ACCENT, 600, "middle")
    s.line([(MX, y["CLK"]), (MX - 50, y["CLK"])], WIRE["gnd"])
    s.ground(MX - 50, y["CLK"])

    RX = MX + MW
    s.line([(RX, y["REFN0"]), (RX + 50, y["REFN0"])], WIRE["gnd"])
    s.ground(RX + 50, y["REFN0"])
    s.line([(RX, y["REFP0"]), (RX + 100, y["REFP0"])], WIRE["3v3"])
    s.flag_3v3(RX + 100, y["REFP0"])
    s.line([(RX, y["AVDD"]), (RX + 150, y["AVDD"])], WIRE["3v3"])
    s.flag_3v3(RX + 150, y["AVDD"])
    s.line([(RX, y["AGND"]), (RX + 50, y["AGND"])], WIRE["gnd"])
    s.ground(RX + 50, y["AGND"])
    s.text(RX - 14, y["AIN3"] + 26, "AIN2, AIN3: leave open", 11, MUTED, 400, "end")

    NX, NY = RX + 90, y["AIN1"]  # bridge-completion divider on AIN1
    s.line([(RX, NY), (NX + 34, NY)], WIRE["ref"])
    s.dot(NX, NY, WIRE["ref"])
    s.resistor_h(NX + 60, NY, "R1  1 kΩ")
    s.line([(NX + 86, NY), (NX + 140, NY)], WIRE["3v3"])
    s.flag_3v3(NX + 140, NY)
    s.line([(NX, NY), (NX, NY + 24)], WIRE["ref"])
    s.resistor_v(NX, NY + 50, "R2  1 kΩ")
    s.line([(NX, NY + 76), (NX, NY + 84)], WIRE["gnd"])
    s.ground(NX, NY + 84)
    s.text(RX + 14, NY - 10, "≈1.65 V", 12, MUTED)

    # cable solder pads on the unit, then the cable to the cell (JST at the cradle end)
    JX, JY = 1010, MY - 30
    s.rect(JX, JY, 44, 130, "#FFFFFF", INK, 4, 1.8)
    s.text(JX + 22, JY - 10, "solder", 12, INK, 700, "middle")
    pe, pn, ps = JY + 22, JY + 52, JY + 108
    s.line([(RX, y["AIN0"]), (RX + 40, y["AIN0"]), (RX + 40, ps), (JX, ps)], WIRE["sig"])
    s.text(JX - 8, ps - 8, "S → AIN0", 12, WIRE["sig"], 700, "end")
    s.line([(JX, pe), (JX - 40, pe)], WIRE["3v3"])
    s.flag_3v3(JX - 40, pe)
    s.line([(JX, pn), (JX - 70, pn)], WIRE["gnd"])
    s.ground(JX - 70, pn)
    for yy, lab in ((pe, "1 E+"), (pn, "2 E−"), (ps, "3 S")):
        s.text(JX + 22, yy + 4, lab, 10, INK, 700, "middle")
    CX = 1150
    s.rect(CX, JY - 10, 100, 150, CELL, CELL_S, 12, 2)
    s.text(CX + 50, JY + 58, "Load cell", 13, CELL_S, 700, "middle")
    for yy, col, lab in ((pe, "#F4F4F4", "white"), (pn, "#222222", "black"), (ps, "#D64545", "red")):
        s.line([(JX + 44, yy), (CX, yy)], "#9AA5B1", 4.5)
        s.line([(JX + 44, yy), (CX, yy)], col, 2.6)
        s.text(JX + 123, yy - 6, lab, 10, MUTED, 400, "middle")
    s.rect(JX + 66, JY + 6, 18, 118, "#FFFFFF", INK, 3, 1.6)
    s.text(JX + 75, JY + 146, "JST", 11, INK, 700, "middle")
    s.text(JX + 75, JY + 160, "at cradle", 10, MUTED, 400, "middle")
    s.text(CX + 50, JY + 160, "cable shield → GND,", 11, MUTED, 400, "middle")
    s.text(CX + 50, JY + 175, "this end only", 11, MUTED, 400, "middle")

    LY = 700
    s.text(60, LY, "3V3 flag and ground symbol = the carrier's 3V3 and GND rails (step 2). Red is "
           "the centre tap S on this build's cells; which of white/black is E+ only sets the sign.",
           12, MUTED)
    s.text(60, LY + 20, "Both supplies (DVDD, AVDD) and both grounds (DGND, AGND) must be connected. "
           "CLK to GND selects the internal oscillator.", 12, ACCENT, 600)
    return s


# ---------------------------------------------------------------------------------------------
# Step 2: four units on a carrier
# ---------------------------------------------------------------------------------------------
def carrier() -> Svg:
    s = Svg(1280, 800)
    s.step_title(2, "Put four units on a carrier (×2)", "A carrier is a perfboard with 5 bus rails. "
                 "Every unit taps all five rails; its CS wire and cell cable leave from the bottom edge.")
    X0, X1, Y0, Y1 = 70, 1210, 130, 640
    s.rect(X0, Y0, X1 - X0, Y1 - Y0, CAR, CAR_S, 12, 2)
    s.text((X0 + X1) / 2, Y0 + 28, "Toe carrier (perfboard). The heel carrier is identical, with L3, L4, R3, R4.",
           13, CAR_S, 700, "middle")
    rails = [Y0 + 70 + 22 * i for i in range(5)]
    # BUS IN / BUS OUT headers
    for hx, title, anchor, tx in ((X0 + 16, "BUS IN ← UNO Q", "start", X0 + 16),
                                  (X1 - 76, "BUS OUT → heel carrier", "end", X1 - 16)):
        s.rect(hx, rails[0] - 16, 60, rails[-1] - rails[0] + 32, "#FFFFFF", INK, 4, 1.8)
        s.text(tx, rails[0] - 26, title, 12, INK, 700, anchor)
    for (label, key), ry in zip(BUS, rails):
        s.line([(X0 + 76, ry), (X1 - 76, ry)], WIRE[key], 3)
        s.dot(X0 + 76, ry, WIRE[key], 4.5)
        s.dot(X1 - 76, ry, WIRE[key], 4.5)
        s.text(X0 + 84, ry - 5, label, 11, WIRE[key], 700)
    units = [("L1", "toe outer", "D3", "450 mm"), ("L2", "toe inner", "D4", "250 mm"),
             ("R1", "toe inner", "D7", "250 mm"), ("R2", "toe outer", "D8", "450 mm")]
    UW, UY, UH = 200, 330, 150
    for k, (name, where, cs_pin, cable) in enumerate(units):
        ux = 230 + k * 240
        s.rect(ux, UY, UW, UH, MODULE, MODULE_S, 8, 1.8)
        s.text(ux + UW / 2, UY + 44, name, 22, MODULE_S, 700, "middle")
        s.text(ux + UW / 2, UY + 64, "unit (step 1)", 11, MUTED, 400, "middle")
        s.text(ux + UW / 2, UY + 82, where, 11, INK, 400, "middle")
        for i, ((_, key), ry) in enumerate(zip(BUS, rails)):
            tx = ux + 40 + 30 * i
            s.line([(tx, UY), (tx, ry)], WIRE[key], 1.8)
            s.dot(tx, ry, WIRE[key])
        # bottom edge: CS (and DRDY on L1) to the UNO Q, cell cable to its cradle JST
        cx = ux + 40
        s.line([(cx, UY + UH), (cx, Y1)], WIRE["cs"])
        s.pin(cx, Y1, "", "l", WIRE["cs"])
        s.text(cx, Y1 + 24, f"CS ← {cs_pin}", 12, WIRE["cs"], 700, "middle")
        if name == "L1":
            dx = ux + 90
            s.line([(dx, UY + UH), (dx, Y1)], WIRE["drdy"])
            s.pin(dx, Y1, "", "l", WIRE["drdy"])
            s.text(dx + 4, Y1 + 42, "DRDY → D2", 12, WIRE["drdy"], 700, "middle")
        jx = ux + 150
        s.line([(jx, UY + UH - 6), (jx, Y1 + 60)], WIRE["cell"], 4)
        s.dot(jx, UY + UH - 6, INK, 5)
        s.text(jx, Y1 + 78, f"cell {name}", 12, INK, 700, "middle")
        s.text(jx, Y1 + 94, cable, 11, MUTED, 400, "middle")
    s.text(640, Y1 + 118, "Dot = soldered joint. The 5 rails run the full width, so BUS IN and "
           "BUS OUT are the same 5 signals: that is what lets carriers chain.", 12, MUTED, 400, "middle")
    return s


# ---------------------------------------------------------------------------------------------
# Step 3: the whole system
# ---------------------------------------------------------------------------------------------
def system() -> Svg:
    s = Svg(1400, 1040)
    s.step_title(3, "Chain the carriers to the UNO Q", "Top-down, roughly as it sits on the floor: "
                 "plates left and right, the centre enclosure between them, toe (ball side) at the top.")

    def cell(x, yy, name):
        s.rect(x, yy, 70, 50, CELL, CELL_S, 8, 1.6)
        s.text(x + 35, yy + 31, name, 15, CELL_S, 700, "middle")

    # plates and cells
    for px, label in ((50, "Plate L"), (1070, "Plate R")):
        s.rect(px, 170, 280, 720, "#EEF1F4", "#9AA5B1", 6, 1.6)
        s.text(px + 140, 912, label, 14, INK, 700, "middle")
    cells = {"L1": (80, 200), "L2": (230, 200), "L3": (230, 810), "L4": (80, 810),
             "R1": (1100, 200), "R2": (1250, 200), "R3": (1250, 810), "R4": (1100, 810)}
    for n, (x, yy) in cells.items():
        cell(x, yy, n)
    s.text(190, 160, "toe ↑", 12, MUTED, 600, "middle")

    # enclosure, carriers, UNO Q
    s.rect(400, 150, 610, 760, "none", "#9AA5B1", 10, 1.6, "8 6")
    s.text(705, 935, "Centre enclosure", 13, MUTED, 700, "middle")
    TY, HY = 190, 690
    for yy, name, units in ((TY, "Toe carrier", "L1 L2 R1 R2"), (HY, "Heel carrier", "L3 L4 R3 R4")):
        s.rect(450, yy, 500, 170, CAR, CAR_S, 10, 2)
        s.text(700, yy + 30, name, 15, CAR_S, 700, "middle")
        for k, u in enumerate(units.split()):
            s.rect(478 + k * 115, yy + 50, 100, 60, MODULE, MODULE_S, 6, 1.4)
            s.text(528 + k * 115, yy + 86, u, 15, MODULE_S, 700, "middle")
    s.rect(560, 450, 280, 150, Q_FILL, Q_S, 10, 2)
    s.text(700, 518, "Arduino UNO Q", 16, Q_S, 700, "middle")
    s.text(700, 538, "14 header pins used", 11, MUTED, 400, "middle")

    def bundle_v(x, y0, y1, keys, gap=5):
        for i, key in enumerate(keys):
            xx = x + (i - (len(keys) - 1) / 2) * gap
            s.line([(xx, y0), (xx, y1)], WIRE[key], 2.4)

    bus_keys = [k for _, k in BUS]
    # ① Q -> toe BUS IN, ③ Q -> toe CS + DRDY, ④ Q -> heel CS
    bundle_v(610, 450, TY + 170, bus_keys)
    bundle_v(760, 450, TY + 170, ["cs", "cs", "cs", "cs", "drdy"])
    bundle_v(760, 600, HY, ["cs", "cs", "cs", "cs"])
    # ② toe BUS OUT -> heel BUS IN, around the right of the UNO Q (nested, no crossings)
    for i, key in enumerate(bus_keys):
        y_top = TY + 128 + 5 * i
        x_v = 990 - 5 * i
        y_bot = HY + 62 - 5 * i
        s.line([(950, y_top), (x_v, y_top), (x_v, y_bot), (950, y_bot)], WIRE[key], 2.4)

    def tag(x, yy, n, title, sub, anchor="start"):
        s.add(f'<circle cx="{x}" cy="{yy - 5}" r="11" fill="{INK}"/>')
        s.text(x, yy, n, 12, "#FFFFFF", 700, "middle")
        tx = x + 18 if anchor == "start" else x - 18
        s.text(tx, yy - 2, title, 13, INK, 700, anchor)
        s.text(tx, yy + 14, sub, 11, MUTED, 400, anchor)

    tag(588, 405, "1", "BUS → toe BUS IN", "3V3 GND SCLK MOSI MISO", "end")
    tag(790, 405, "3", "CS + DRDY → toe", "D3 D4 D7 D8 + D2")
    s.add(f'<circle cx="{955}" cy="{495}" r="11" fill="{INK}"/>')
    s.text(955, 500, "2", 12, "#FFFFFF", 700, "middle")
    for i, (txt, size, col, wt) in enumerate((("toe BUS OUT", 12, INK, 700), ("→ heel BUS IN", 12, INK, 700),
                                              ("same 5 wires,", 11, MUTED, 400), ("chained", 11, MUTED, 400))):
        s.text(960, 530 + 16 * i, txt, size, col, wt, "end")
    tag(790, 650, "4", "CS → heel", "D5 D6 D9 A2")

    # cell cables: each cell to its carrier; outer cells route around the inner ones
    def cable(pts):
        s.line(pts, "#9AA5B1", 5)
        s.line(pts, "#E9ECEF", 2)

    cable([(115, 200), (115, 182), (425, 182), (425, 225), (450, 225)])          # L1
    cable([(300, 245), (450, 245)])                                              # L2
    cable([(1285, 200), (1285, 182), (975, 182), (975, 225), (950, 225)])        # R2
    cable([(1100, 245), (950, 245)])                                             # R1
    cable([(300, 825), (450, 825)])                                              # L3
    cable([(115, 860), (115, 878), (425, 878), (425, 845), (450, 845)])          # L4
    cable([(1100, 825), (950, 825)])                                             # R4
    cable([(1285, 860), (1285, 878), (975, 878), (975, 845), (950, 845)])        # R3
    s.text(705, 975, "Grey: cell cables (outer corners ~450 mm, inner ~250 mm), each to its "
           "unit on the carrier. Each has its JST at the cradle end.", 12, MUTED, 400, "middle")
    s.legend(300, 1005, [(lab, k) for lab, k in BUS] + [("CS", "cs"), ("DRDY", "drdy")], cols=7, col_w=118)
    return s


if __name__ == "__main__":
    unit().save(HERE / "harness-1-unit.svg")
    carrier().save(HERE / "harness-2-carrier.svg")
    system().save(HERE / "harness-3-system.svg")
