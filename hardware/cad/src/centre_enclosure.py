"""Centre enclosure base (03) and lid (04), as source.

Replaces the enclosure section of forceplate_parts.py, which is an older
revision (150 x 70 mm). Rev A was edited in the STEP/STL directly (see
docs/VERIFIED.md); REV_A below reproduces those files exactly (0.00 mm3
difference both ways against commit 064a41c). REV_B fits the 204.5 mm ADC
board (hardware/pcb/adc-board, rev B) and is what step/ and stl/ now hold.

Frame: mm, +x = toe, z = 0 at the base underside, origin at the centre of the
rev A footprint (the ADC board docs use the same frame). Rev B is shorter and
not centred on x = 0: outside x -124.9 ... +140.4.

    python centre_enclosure.py                  # rev B -> ../step, ../stl
    python centre_enclosure.py --rev a --out D  # rev A (stripboard carriers) -> D/step, D/stl
    python centre_enclosure.py --rev a --check D  # compare with D/03_*.step, D/04_*.step
Then run check_adc_fit.py.
"""
import argparse
import math
import os

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- shared ----------
WALL = 2.4            # base wall and floor
IW = 56.0             # cavity width (y +-28)
WALL_TOP = 22.3       # rev A raise (2026-10-12)
R_OUT, R_IN = 4.0, 3.0
LID_T = 2.0           # lid plate
LIP_H, LIP_CLR = 1.5, 0.3
LIP_CUT_X = 34.0      # lip removed on both long sides for |x| < 34 (board header tabs)
POST_R, INS_R = 3.6, 1.75     # bosses / M2.5 heat-set insert holes (3.5 mm)
POST_INSET = 5.0      # lid post centre from the cavity walls
POST_INS_D = 7.4      # lid-post insert hole depth from the wall top
CSK_HOLE, CSK_D = 2.8, 5.5    # lid screw holes, 90 deg countersink
VENT_W, VENT_L, VENT_PITCH = 2.0, 30.0, 12.0
SLOT_W, SLOT_Z0, SLOT_Z1 = 6.0, 2.4, 19.0
PAD_TOP, PAD_INS_D = 5.4, 2.5
USB_W, USB_H, USB_Z0 = 14.0, 8.0, 6.4   # USB-C slot in the heel end wall, centred y 0
VENT_END = 25.0       # vents stop this far from the cavity ends

# UNO Q bosses (UNO hole pattern), 5 mm tall, insert holes to the floor
UNO = [(-20.3, -24.15), (-19.0, 24.05), (31.8, -19.05), (31.8, 8.85)]
UNO_BOSS_TOP = 7.4

REV_A = dict(
    x0=-145.0, x1=145.0,                      # cavity
    slots=[-125.0, -85.0, 85.0, 125.0],
    slot_in_neg=-22.6,   # the -y slots were cut 2.4 mm into the pads' edge
    pads=[dict(box=(-137.0, -47.0, -25.0, 25.0)), dict(box=(47.0, 137.0, -25.0, 25.0))],
    pad_holes=[(s * (54.5 + 7.5 * i), 7.5 * j) for s in (-1, 1) for i in range(11) for j in range(-3, 4)],
)

# Rev B: ADC board x -94.5 ... +110, holes on y = 0. Outer plugs reach ~11 mm
# past each board end and their cables turn to the slots at x -108.5 / +124.
# Lid posts sit just past the outer slots (2 mm from the slot edge).
SLOTS_B = [-108.5, -67.5, 83.0, 124.0]
POST_GAP = 2.0        # min. gap from an outer slot's edge to a lid post
_px_toe = math.ceil((SLOTS_B[-1] + SLOT_W / 2 + POST_GAP + POST_R) * 2) / 2     # 133.0
_px_heel = -math.ceil(-(SLOTS_B[0] - SLOT_W / 2 - POST_GAP - POST_R) * 2) / 2   # -117.5
REV_B = dict(
    x0=_px_heel - POST_INSET, x1=_px_toe + POST_INSET,   # cavity -122.5 ... +138
    slots=SLOTS_B,
    pads=[dict(round=(x, 0.0), r=4.5) for x in (-90.0, -58.5, 74.0, 105.5)],
    pad_holes=[(x, 0.0) for x in (-90.0, -58.5, 74.0, 105.5)],
)


def rrect(x0, x1, y0, y1, z0, z1, r):
    w = cq.Workplane("XY").workplane(offset=z0).center((x0 + x1) / 2, (y0 + y1) / 2)
    return w.rect(x1 - x0, y1 - y0).extrude(z1 - z0).edges("|Z").fillet(r)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl(x, y, r, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1 - z0)


def posts(p):
    x0, x1 = p["x0"], p["x1"]
    yy = IW / 2 - POST_INSET
    return [(x, y) for x in (x0 + POST_INSET, x1 - POST_INSET) for y in (-yy, yy)]


def base(p):
    x0, x1, yi = p["x0"], p["x1"], IW / 2
    b = rrect(x0 - WALL, x1 + WALL, -yi - WALL, yi + WALL, 0, WALL_TOP, R_OUT)
    b = b.cut(rrect(x0, x1, -yi, yi, WALL, WALL_TOP + 1, R_IN))
    # lid posts with insert holes from the top
    for x, y in posts(p):
        b = b.union(cyl(x, y, POST_R, WALL, WALL_TOP))
        b = b.cut(cyl(x, y, INS_R, WALL_TOP - POST_INS_D, WALL_TOP + 1))
    # UNO Q bosses
    for x, y in UNO:
        b = b.union(cyl(x, y, POST_R, WALL, UNO_BOSS_TOP))
        b = b.cut(cyl(x, y, INS_R, WALL, UNO_BOSS_TOP + 1))
    # ADC standoff pads with insert holes
    for pad in p["pads"]:
        if "box" in pad:
            b = b.union(box(*pad["box"], WALL, PAD_TOP))
        else:
            b = b.union(cyl(*pad["round"], pad["r"], WALL, PAD_TOP))
    for x, y in p["pad_holes"]:
        b = b.cut(cyl(x, y, INS_R, PAD_TOP - PAD_INS_D, PAD_TOP + 1))
    # cable slots, both long walls
    for x in p["slots"]:
        for s in (-1, 1):
            if s > 0:
                y0, y1 = yi - 0.5, yi + WALL + 1
            else:
                y0, y1 = -yi - WALL - 1, p.get("slot_in_neg", -yi + 0.5)
            b = b.cut(box(x - SLOT_W / 2, x + SLOT_W / 2, y0, y1, SLOT_Z0, SLOT_Z1))
    # USB-C slot in the heel end wall
    b = b.cut(box(x0 - WALL - 1, x0 + 1, -USB_W / 2, USB_W / 2, USB_Z0, USB_Z0 + USB_H))
    return b


def lid(p):
    x0, x1, yi = p["x0"], p["x1"], IW / 2
    lo = rrect(x0 - WALL, x1 + WALL, -yi - WALL, yi + WALL, 0, LID_T, R_OUT)
    c = LIP_CLR
    lip = rrect(x0 + c, x1 - c, -yi + c, yi - c, LID_T, LID_T + LIP_H, R_IN)
    lip = lip.cut(box(x0 + c + WALL, x1 - c - WALL, -yi + c + WALL, yi - c - WALL, LID_T - 1, LID_T + LIP_H + 1))
    lo = lo.union(lip)
    pts = posts(p)
    lo = lo.faces("<Z").workplane(centerOption="CenterOfBoundBox").pushPoints(
        [(x - (x0 + x1) / 2, -y) for x, y in pts]).cskHole(CSK_HOLE, CSK_D, 90)
    # vents: on the rev A 12 mm grid (x = -120 + 12k), clear of the ends and posts
    k = 0
    while True:
        vx = -120.0 + VENT_PITCH * k
        k += 1
        if vx > x1 - VENT_END:
            break
        if vx < x0 + VENT_END:
            continue
        lo = lo.cut(box(vx - VENT_W / 2, vx + VENT_W / 2, -VENT_L / 2, VENT_L / 2, -1, LID_T + 1))
    for x, y in pts:
        lo = lo.cut(cyl(x, y, POST_R, LID_T, LID_T + LIP_H + 1))
    # lip cut for the board's header tabs
    for s in (-1, 1):
        lo = lo.cut(box(-LIP_CUT_X, LIP_CUT_X, min(s * 24.5, s * 29.0), max(s * 24.5, s * 29.0),
                        LID_T, LID_T + LIP_H + 1))
    return lo


def compare(mine, path):
    ref = cq.importers.importStep(path).val()
    m = mine.val()
    extra, missing = m.cut(ref), ref.cut(m)
    print(f"{os.path.basename(path)}: mine {m.Volume():.1f}  ref {ref.Volume():.1f}  "
          f"extra {extra.Volume():.2f}  missing {missing.Volume():.2f}")
    for name, d in (("extra", extra), ("missing", missing)):
        for s in d.Solids():
            if s.Volume() > 0.05:
                bb = s.BoundingBox()
                print(f"  {name} {s.Volume():8.2f}  x {bb.xmin:.2f}..{bb.xmax:.2f}  "
                      f"y {bb.ymin:.2f}..{bb.ymax:.2f}  z {bb.zmin:.2f}..{bb.zmax:.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", choices=("a", "b"), default="b")
    ap.add_argument("--out", default=os.path.join(HERE, ".."), help="dir holding step/ and stl/")
    ap.add_argument("--check", metavar="DIR", help="compare with DIR/03_*.step, DIR/04_*.step instead of writing")
    a = ap.parse_args()
    p = REV_A if a.rev == "a" else REV_B
    if a.check:
        compare(base(p), os.path.join(a.check, "03_centre_enclosure_base.step"))
        compare(lid(p), os.path.join(a.check, "04_centre_enclosure_lid.step"))
        return
    for name, part in (("03_centre_enclosure_base", base(p)), ("04_centre_enclosure_lid", lid(p))):
        s = part.val()
        bb = s.BoundingBox()
        assert len(part.solids().vals()) == 1 and s.isValid(), name
        print(f"{name}: valid, {s.Volume():.0f} mm3, x {bb.xmin:.1f}..{bb.xmax:.1f} "
              f"y {bb.ymin:.1f}..{bb.ymax:.1f} z {bb.zmin:.1f}..{bb.zmax:.1f}")
        cq.exporters.export(part, os.path.join(a.out, "step", f"{name}.step"))
        cq.exporters.export(part, os.path.join(a.out, "stl", f"{name}.stl"), tolerance=0.02, angularTolerance=0.1)


if __name__ == "__main__":
    main()
