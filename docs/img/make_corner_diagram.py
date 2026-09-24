#!/usr/bin/env python3
"""Generate docs/img/corner-assembly.svg: how one load-cell corner goes together.

Dimensions (mm) are measured from the STL files in hardware/cad/stl (see VERIFIED.md).
The load cell's centre boss height isn't in the CAD, so it is drawn at ~1 mm.
"""
from pathlib import Path

# -- geometry (mm) ----------------------------------------------------------------
CR_W, CR_H = 54.0, 11.2          # cradle
POCKET_HALF, POCKET_D = 17.3, 8.2
RELIEF_R, RELIEF_TOP = 12.0, 9.7
M4_X, M4_R, M4_D = 22.5, 2.8, 6.5
M2_X, M2_R, M2_D = 22.5, 1.6, 4.0
NOTCH_HALF, NOTCH_D = 3.5, 7.2
CELL_HALF, CELL_T = 17.0, 7.8
BOSS_R, BOSS_H = 5.0, 1.0
FOOT_R, FOOT_T = 8.0, 3.5
RET_T, WIN_HALF = 1.6, 14.0
AL_T, NEO_T = 6.35, 1.6

# -- palette (light, prints well) --------------------------------------------------
INK, MUTED, ACCENT = "#1F2933", "#5F6B78", "#C2410C"
PETG, PETG_S = "#F1ECE3", "#7A7063"
ALU, ALU_S = "#C9D1D9", "#6E7B88"
NEO = "#3B4148"
STEEL, STEEL_S = "#AEB8C2", "#56626F"
TPU, TPU_S = "#2EC4B6", "#17857B"
BRASS = "#C9A227"
SCREW = "#4A5563"
FLOOR, FLOOR_S = "#DDD7CE", "#8E8475"
WIRES = ["#D64545", "#222222", "#F4F4F4"]

out: list[str] = []


def add(s):
    out.append(s)


def rect(x, y, w, h, fill, stroke="none", sw=1.2, extra=""):
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')


def poly(pts, fill, stroke, sw=1.2, extra=""):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    add(f'<polygon points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" {extra}/>')


def line(x1, y1, x2, y2, stroke=MUTED, sw=1, extra=""):
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')


def text(x, y, s, size=13, fill=INK, weight=400, anchor="start", extra=""):
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{s}</text>')


def label(x, y, lines, tx, ty, color=INK):
    """Leader from part point (x, y) to a text block at (tx, ty)."""
    line(x, y, tx - 6, ty - 4, stroke=MUTED, sw=0.8)
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="{MUTED}"/>')
    for i, (s, kw) in enumerate(lines):
        text(tx, ty + i * 16, s, **({"fill": color} | kw))


class Section:
    """Side section through the M4 screw line, as installed (floor at the bottom).

    z is mm above the cradle's open (retainer) face; x is mm across the cradle.
    """

    def __init__(self, cx, y0, s):
        self.cx, self.y0, self.s = cx, y0, s

    def P(self, x, z, dz=0.0):
        return (self.cx + x * self.s, self.y0 - (z + dz) * self.s)

    def cradle(self, dz=0.0):
        P = lambda x, z: self.P(x, z, dz)
        pts = [P(-27, CR_H), P(-M4_X - M4_R, CR_H), P(-M4_X - M4_R, CR_H - M4_D), P(-M4_X + M4_R, CR_H - M4_D),
               P(-M4_X + M4_R, CR_H), P(M4_X - M4_R, CR_H), P(M4_X - M4_R, CR_H - M4_D), P(M4_X + M4_R, CR_H - M4_D),
               P(M4_X + M4_R, CR_H), P(27, CR_H), P(27, 0), P(POCKET_HALF, 0), P(POCKET_HALF, POCKET_D),
               P(RELIEF_R, POCKET_D), P(RELIEF_R, RELIEF_TOP), P(-RELIEF_R, RELIEF_TOP), P(-RELIEF_R, POCKET_D),
               P(-POCKET_HALF, POCKET_D), P(-POCKET_HALF, 0), P(-27, 0)]
        # back wall of the pocket with the cable notch cut into it (seen through the open pocket)
        bx0, by0 = P(-POCKET_HALF, POCKET_D)
        bx1, by1 = P(POCKET_HALF, 0)
        rect(bx0, by0, bx1 - bx0, by1 - by0, "#E4DDD1", "none")
        nx0, ny0 = P(-NOTCH_HALF, NOTCH_D)
        nx1, ny1 = P(NOTCH_HALF, 0)
        rect(nx0, ny0, nx1 - nx0, ny1 - ny0, "#FFFFFF", ACCENT, 1.2, 'stroke-dasharray="4 3"')
        poly(pts, "url(#hatch)", PETG_S, 1.4)
        # M4 heat-set inserts
        for sx in (-1, 1):
            x0, y0 = P(sx * M4_X - M4_R + 0.4, CR_H)
            x1, y1 = P(sx * M4_X + M4_R - 0.4, CR_H - M4_D + 0.3)
            rect(x0, y0, x1 - x0, y1 - y0, BRASS, "#8A6D12", 0.8)
        # M2 inserts at the corners (behind the section)
        for sx in (-1, 1):
            x0, y0 = P(sx * M2_X - M2_R, M2_D)
            x1, y1 = P(sx * M2_X + M2_R, 0)
            rect(x0, y0, x1 - x0, y1 - y0, "none", PETG_S, 0.9, 'stroke-dasharray="3 2"')
        return P

    def plate(self, dz=0.0, half=34.0):
        P = lambda x, z: self.P(x, z, dz)
        x0, ya = P(-half, CR_H + AL_T)
        x1, yb = P(half, CR_H)
        rect(x0, ya, x1 - x0, yb - ya, ALU, ALU_S, 1.2)
        _, yn = P(0, CR_H + AL_T + NEO_T)
        rect(x0, yn, x1 - x0, ya - yn, NEO, NEO, 1)
        # countersunk holes for the M4 flat heads (plate top face)
        for sx in (-1, 1):
            cx = sx * M4_X
            poly([P(cx - 4.1, CR_H + AL_T), P(cx + 4.1, CR_H + AL_T), P(cx + 2.25, CR_H + AL_T - 1.85),
                  P(cx + 2.25, CR_H), P(cx - 2.25, CR_H), P(cx - 2.25, CR_H + AL_T - 1.85)], "#FFFFFF", ALU_S, 1)
        return P

    def m4(self, dz=0.0):
        P = lambda x, z: self.P(x, z, dz)
        top = CR_H + AL_T
        for sx in (-1, 1):
            cx = sx * M4_X
            poly([P(cx - 4.0, top), P(cx + 4.0, top), P(cx + 2.0, top - 2.0), P(cx + 2.0, top - 12),
                  P(cx - 2.0, top - 12), P(cx - 2.0, top - 2.0)], SCREW, SCREW, 1)

    def cell(self, dz=0.0):
        P = lambda x, z: self.P(x, z, dz)
        z0 = POCKET_D - CELL_T                       # cell pressed up against the pocket ceiling
        x0, y0 = P(-CELL_HALF, POCKET_D)
        x1, y1 = P(CELL_HALF, z0)
        rect(x0, y0, x1 - x0, y1 - y0, STEEL, STEEL_S, 1.3, 'rx="2"')
        for sx in (-1, 1):                           # slots between frame and centre beam
            a, b = P(sx * 9.5, POCKET_D - 1.0)
            c, d = P(sx * 9.5, z0 + 1.0)
            line(a, b, c, d, STEEL_S, 1.2)
        bx0, by0 = P(-BOSS_R, z0)
        bx1, by1 = P(BOSS_R, z0 - BOSS_H)
        rect(bx0, by0, bx1 - bx0, by1 - by0, STEEL, STEEL_S, 1.2)
        return P

    def foot(self, dz=0.0):
        P = lambda x, z: self.P(x, z, dz)
        zt = POCKET_D - CELL_T - BOSS_H
        x0, y0 = P(-FOOT_R, zt)
        x1, y1 = P(FOOT_R, zt - FOOT_T)
        rect(x0, y0, x1 - x0, y1 - y0, TPU, TPU_S, 1.3, 'rx="2"')
        return P

    def retainer(self, dz=0.0):
        P = lambda x, z: self.P(x, z, dz)
        for a, b in ((-27, -WIN_HALF), (WIN_HALF, 27)):
            x0, y0 = P(a, 0)
            x1, y1 = P(b, -RET_T)
            rect(x0, y0, x1 - x0, y1 - y0, "url(#hatch)", PETG_S, 1.3)
        return P

    def m2(self, dz=0.0):
        P = lambda x, z: self.P(x, z, dz)
        for sx in (-1, 1):
            cx = sx * M2_X
            poly([P(cx - 2.2, -RET_T), P(cx + 2.2, -RET_T), P(cx + 1.0, -RET_T + 1.2), P(cx + 1.0, -RET_T + 5),
                  P(cx - 1.0, -RET_T + 5), P(cx - 1.0, -RET_T + 1.2)], SCREW, SCREW, 1)

    def floor(self, z, half=40.0, depth=4.0):
        x0, y0 = self.P(-half, z)
        x1, y1 = self.P(half, z - depth)
        rect(x0, y0, x1 - x0, y1 - y0, "url(#floor)", FLOOR_S, 1)


def arrow(x, y1, y2, color=MUTED):
    line(x, y1, x, y2, color, 1.2, 'marker-end="url(#arrow)"')


W, H = 1280, 1250
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
    'font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif">')
add(f"""<defs>
  <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <rect width="6" height="6" fill="{PETG}"/><line x1="0" y1="0" x2="0" y2="6" stroke="#CFC5B5" stroke-width="1.4"/>
  </pattern>
  <pattern id="floor" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
    <rect width="8" height="8" fill="{FLOOR}"/><line x1="0" y1="0" x2="0" y2="8" stroke="#B9AF9F" stroke-width="1.5"/>
  </pattern>
  <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/>
  </marker>
  <marker id="arrowA" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{ACCENT}"/>
  </marker>
</defs>""")
rect(0, 0, W, H, "#FFFFFF")

text(40, 46, "Corner assembly", 24, weight=700)
text(40, 70, "One of eight. Load path: plate → cradle → cell frame → cell centre → TPU foot → floor.", 14, MUTED)

# ---------------- Panel A: exploded ----------------
text(40, 116, "1 · Exploded, as installed", 16, weight=700)
text(40, 136, "Cutaway through the two plate screws. Plate on top, floor at the bottom. Parts move along the dashed line.", 13, MUTED)
A = Section(cx=300, y0=0, s=6)
# vertical placement of each part (y of the cradle's open face for that part)
ys = {"m4": 280, "plate": 395, "cradle": 435, "cell": 525, "foot": 560, "retainer": 630, "m2": 690, "floor": 745}
line(300, 165, 300, 790, "#B8C0C8", 1, 'stroke-dasharray="6 5"')

A.y0 = ys["m4"]; A.m4()
A.y0 = ys["plate"]; A.plate(half=34)
A.y0 = ys["cradle"]; A.cradle()
A.y0 = ys["cell"]; A.cell()
A.y0 = ys["foot"]; A.foot()
A.y0 = ys["retainer"]; A.retainer()
A.y0 = ys["m2"]; A.m2()
A.y0 = ys["floor"]; A.floor(0, half=34, depth=4)

# assembly arrows
arrow(206, 236, 262)                     # screws down into plate
arrow(394, 236, 262)
arrow(300, 474, 440)                     # cell up into pocket
arrow(252, 578, 545)                     # foot up onto boss
arrow(470, 622, 594)                     # retainer up onto cradle
arrow(206, 676, 646)                     # M2 screws up
arrow(394, 676, 646)

LX = 530
label(419, 205, [("M4 × 12 flat-head ×2", {"weight": 600}), ("down through the plate, blue threadlocker", {"fill": MUTED})], LX, 196)
label(504, 300, [("Neoprene on 1/4\" aluminum plate", {"weight": 600}), ("countersunk so the screw heads sit flush", {"fill": MUTED})], LX, 288)
label(435, 380, [("Cradle, pocket facing DOWN", {"weight": 600}), ("M4 heat-set inserts in the top face;", {"fill": MUTED}), ("Ø24 relief above the cell lets its centre flex", {"fill": MUTED})], LX, 360)
label(321, 425, [("Cable notch (in the pocket's back wall)", {"weight": 600, "fill": ACCENT}), ("must break through into the pocket", {"fill": ACCENT})], LX, 424)
label(402, 500, [("Load cell, centre boss facing DOWN", {"weight": 600}), ("frame presses up against the pocket ceiling;", {"fill": MUTED}), ("wires lie on the bottom face", {"fill": MUTED})], LX, 490)
label(348, 572, [("TPU hub foot", {"weight": 600}), ("CA-glue centred on the boss", {"fill": MUTED})], LX, 564)
label(420, 634, [("Retainer, countersinks facing the floor", {"weight": 600}), ("notch lines up with the cradle notch", {"fill": MUTED})], LX, 628)
label(394, 684, [("M2 × 5 countersunk ×4", {"weight": 600}), ("one per corner (two shown)", {"fill": MUTED})], LX, 686)
label(470, 755, [("3/8\" rubber flooring", {"weight": 600})], LX, 760)

# ---------------- Panel B: assembled ----------------
text(840, 116, "2 · Assembled", 16, weight=700)
text(840, 136, "Only the TPU foot touches the floor.", 13, MUTED)
B = Section(cx=1040, y0=300, s=6.5)
z_floor = POCKET_D - CELL_T - BOSS_H - FOOT_T
B.plate(half=34)
B.m4()
B.cradle()
B.cell()
B.foot()
B.retainer()
B.m2()
B.floor(z_floor, half=34, depth=4)
# clearance callout
gx, gy_top = B.P(-22.5 - 6, -RET_T)
_, gy_bot = B.P(0, z_floor)
line(gx, gy_top, gx, gy_bot, ACCENT, 1.2, 'marker-start="url(#arrowA)" marker-end="url(#arrowA)"')
text(gx - 8, (gy_top + gy_bot) / 2 + 4, "gap", 12, ACCENT, 600, "end")
text(840, 384, "The retainer must clear the floor. If it touches, it carries", 13, INK)
text(840, 401, "load around the cell and the reading drops.", 13, INK)

# ---------------- Panel C: bottom view ----------------
text(840, 456, "3 · From below (looking up at the retainer)", 16, weight=700)
text(840, 476, "Line up the cradle notch, the retainer notch, and the cell's wires.", 13, MUTED)
cx3, cy3, s3 = 985, 640, 4.4
def Q(x, y):
    return (cx3 + x * s3, cy3 - y * s3)
# cradle behind (same outline), hidden pocket edge
x0, y0 = Q(-27, 27); x1, y1 = Q(27, -27)
rect(x0, y0, x1 - x0, y1 - y0, "#E4DDD1", PETG_S, 1, 'rx="18"')
# retainer: outline minus window and notch (fixed geometry: notch runs into the window)
rp = [Q(-27, 27), Q(27, 27), Q(27, -27), Q(NOTCH_HALF, -27), Q(NOTCH_HALF, -WIN_HALF), Q(WIN_HALF, -WIN_HALF),
      Q(WIN_HALF, WIN_HALF), Q(-WIN_HALF, WIN_HALF), Q(-WIN_HALF, -WIN_HALF), Q(-NOTCH_HALF, -WIN_HALF),
      Q(-NOTCH_HALF, -27), Q(-27, -27)]
poly(rp, PETG, PETG_S, 1.4)
# cell face in the window
wx0, wy0 = Q(-WIN_HALF, WIN_HALF); wx1, wy1 = Q(WIN_HALF, -WIN_HALF)
rect(wx0, wy0, wx1 - wx0, wy1 - wy0, STEEL, STEEL_S, 1)
nx0, ny0 = Q(-NOTCH_HALF, -WIN_HALF); nx1, ny1 = Q(NOTCH_HALF, -27)
rect(nx0, ny0, nx1 - nx0, ny1 - ny0, "#E4DDD1", "none")
# hidden pocket edge
px0, py0 = Q(-POCKET_HALF, POCKET_HALF); px1, py1 = Q(POCKET_HALF, -POCKET_HALF)
rect(px0, py0, px1 - px0, py1 - py0, "none", PETG_S, 1, 'stroke-dasharray="4 3"')
# foot
fx, fy = Q(0, 0)
add(f'<circle cx="{fx}" cy="{fy}" r="{FOOT_R * s3}" fill="{TPU}" stroke="{TPU_S}" stroke-width="1.3"/>')
# wires: leave the side of the centre beam and run out through the notch
for i, c in enumerate(WIRES):
    ox = (i - 1) * 1.6
    pts = [Q(ox + 9.0, -2.0), Q(ox * 0.6, -9.5), Q(ox * 0.6, -34)]
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f} Q{pts[1][0]:.1f},{pts[1][1]:.1f} {Q(ox * 0.6, -16)[0]:.1f},{Q(ox * 0.6, -16)[1]:.1f} L{pts[2][0]:.1f},{pts[2][1]:.1f}"
    add(f'<path d="{d}" fill="none" stroke="#777" stroke-width="3.6" stroke-linecap="round"/>')
    add(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round"/>')
# M2 screw heads
for sx in (-1, 1):
    for sy in (-1, 1):
        hx, hy = Q(sx * M2_X, sy * M2_X)
        add(f'<circle cx="{hx}" cy="{hy}" r="{2.2 * s3}" fill="{SCREW}"/>')
        line(hx - 5, hy, hx + 5, hy, "#FFFFFF", 1.2)
tx, ty = Q(0, -36)
arrow_y = ty + 30
line(tx, ty + 4, tx, arrow_y, ACCENT, 1.4, 'marker-end="url(#arrowA)"')
text(tx, arrow_y + 18, "notch points toward the enclosure", 13, ACCENT, 600, "middle")
label(*Q(WIN_HALF, 8), [("28 mm window", {"weight": 600}), ("foot pokes through", {"fill": MUTED})], 1130, 560)
text(1130, 640, "dashed: pocket", 12, MUTED)
text(1130, 656, "edge (hidden)", 12, MUTED)

# ---------------- Panel D: plate plan ----------------
text(40, 870, "4 · Which way the notches point (plate L and R from above)", 16, weight=700)
text(40, 890, "Cradles are under the plates. Every notch faces the centre enclosure, so the cables run inward.", 13, MUTED)
sd = 0.72
spacing = 369.6
ox, oy = 640, 1060        # stance origin on the page
def S(x, y):
    return (ox + x * sd, oy - y * sd)
positions = {"L1": (-307.2, 122.4), "L2": (-62.4, 122.4), "L3": (-62.4, -122.4), "L4": (-307.2, -122.4),
             "R1": (62.4, 122.4), "R2": (307.2, 122.4), "R3": (307.2, -122.4), "R4": (62.4, -122.4)}
for side in (-1, 1):
    c = side * spacing / 2
    x0, y0 = S(c - 152.4, 152.4); x1, y1 = S(c + 152.4, -152.4)
    rect(x0, y0, x1 - x0, y1 - y0, ALU, ALU_S, 1.2, 'rx="3"')
    text((x0 + x1) / 2, y1 + 20, "Plate L" if side < 0 else "Plate R", 13, INK, 600, "middle")
ex0, ey0 = S(-30.5, 147.5); ex1, ey1 = S(30.5, -147.5)
rect(ex0, ey0, ex1 - ex0, ey1 - ey0, "#E4DDD1", PETG_S, 1.2, 'rx="4"')
text((ex0 + ex1) / 2, (ey0 + ey1) / 2, "enclosure", 12, PETG_S, 600, "middle",
     f'transform="rotate(-90 {(ex0 + ex1) / 2:.1f} {(ey0 + ey1) / 2:.1f})"')
for ch, (x, y) in positions.items():
    inward = 1 if ch[0] == "L" else -1          # direction toward the enclosure
    x0, y0 = S(x - 27, y + 27); x1, y1 = S(x + 27, y - 27)
    rect(x0, y0, x1 - x0, y1 - y0, PETG, PETG_S, 1.1, 'rx="3"')
    # notch on the enclosure-facing side
    nx = x + inward * 27
    a = S(nx - inward * 10, y + 3.5); b = S(nx, y - 3.5)
    rect(min(a[0], b[0]), a[1], abs(b[0] - a[0]), b[1] - a[1], "#FFFFFF", ACCENT, 1.1)
    # cable to the enclosure wall; outer corners detour around the inner cradle
    wall = -inward * 30.5
    if abs(x) > 200:
        yd = y - 45 * (1 if y > 0 else -1)
        pts = [(nx, y), (nx + inward * 12, y), (nx + inward * 12, yd), (wall, yd)]
    else:
        pts = [(nx, y), (wall, y)]
    d = " L".join(f"{S(px, py)[0]:.1f},{S(px, py)[1]:.1f}" for px, py in pts)
    add(f'<path d="M{d}" fill="none" stroke="{ACCENT}" stroke-width="1.4" stroke-dasharray="5 3"/>')
    cx_, cy_ = S(x, y)
    text(cx_, cy_ + 5, ch, 13, INK, 700, "middle")
tx0, _ = S(-spacing / 2 - 152.4, 0)
text(tx0 - 14, S(0, 152.4)[1] + 4, "toe / ball ↑", 12, MUTED, 600, "end")
text(tx0 - 14, S(0, -152.4)[1] + 4, "heel", 12, MUTED, 600, "end")

add("</svg>")
dest = Path(__file__).with_name("corner-assembly.svg")
dest.write_text("\n".join(out))
print(f"wrote {dest}")
