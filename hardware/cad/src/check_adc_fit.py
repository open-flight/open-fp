"""Check the ADC board (hardware/pcb/adc-board) against the centre enclosure STEPs.

Reads the board outline and mounting holes from the .kicad_pcb, places the lid on
the base, and checks:
  - each board hole sits on a pad insert hole, and every pad hole has a board hole
  - the board, its underside parts, the plugs, the cable runs to the slots, the
    standoffs and the UNO Q stack do not touch the base or the lid
and writes a top-view overlay PNG.

    python check_adc_fit.py [out.png]
"""
import os
import re
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
PCB = os.path.join(ROOT, "pcb", "adc-board", "adc-board.kicad_pcb")
STEP = os.path.join(HERE, "..", "step")
OX, OY = 150.0, 100.0                       # KiCad: kx = 150 + x, ky = 100 - y

BOARD_Z0, BOARD_Z1 = 20.0, 21.6
UNDER_Z0 = 13.9                             # lowest underside part (JST)
LID_Z = 22.3                                # lid underside / wall top
LID_T = 2.0
JST_Y, PLUG_W, PLUG_L = 17.8, 10.0, 10.0    # plug envelope past the JST mouth (VERIFY)
CABLE_D = 4.0
# channel slot x (enclosure frame); the JST mouth is 15 mm board-side of it
SLOTS = [-108.5, -67.5, 83.0, 124.0]
MOUTH_TO_SLOT = 15.0
STANDOFF_R = 2.9                            # 5 mm A/F hex, corner radius
PAD_TOP = 5.4
UNO = dict(x=(-34.29, 34.29), y=(-26.67, 26.67), z=(7.4, 20.0))


def board_from_pcb():
    txt = open(PCB).read()
    segs = []
    for m in re.finditer(r"\(gr_line\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)(.*?)\(layer \"([^\"]+)\"\)", txt, re.S):
        if m.group(6) == "Edge.Cuts":
            a = (float(m.group(1)) - OX, OY - float(m.group(2)))
            b = (float(m.group(3)) - OX, OY - float(m.group(4)))
            segs.append((a, b))
    # chain the segments into one closed loop
    loop = [segs[0][0], segs[0][1]]
    rest = segs[1:]
    while rest:
        for i, (a, b) in enumerate(rest):
            if _close(a, loop[-1]):
                loop.append(b)
            elif _close(b, loop[-1]):
                loop.append(a)
            else:
                continue
            rest.pop(i)
            break
        else:
            raise SystemExit("board outline does not close")
    holes = [(float(x) - OX, OY - float(y)) for x, y in
             re.findall(r'\(footprint "MountingHole:[^"]+"\s*\(layer "[^"]+"\)\s*\(uuid "[^"]+"\)\s*\(at ([-\d.]+) ([-\d.]+)', txt)]
    return loop[:-1], holes


def _close(a, b):
    return abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6


def prism(poly, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).polyline(poly).close().extrude(z1 - z0)


def box(x0, x1, y0, y1, z0, z1):
    x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def pad_holes(base):
    out = []
    for f in base.Faces():
        if f.geomType() != "CYLINDER":
            continue
        c = f._geomAdaptor().Cylinder()
        bb = f.BoundingBox()
        if abs(c.Radius() - 1.75) < 1e-3 and abs(bb.zmax - PAD_TOP) < 1e-3:
            out.append((round(c.Location().X(), 3), round(c.Location().Y(), 3)))
    return sorted(set(out))


def main():
    png = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "renders", "centre-enclosure-adc-fit.png")
    outline, holes = board_from_pcb()
    base = cq.importers.importStep(os.path.join(STEP, "03_centre_enclosure_base.step")).val()
    lid = cq.importers.importStep(os.path.join(STEP, "04_centre_enclosure_lid.step")).val()
    # installed: flipped about x (the lid is symmetric in y), plate underside at the wall top
    lid = lid.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, LID_Z + LID_T))
    bb = base.BoundingBox()
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    print(f"board  x {min(xs):.2f} .. {max(xs):.2f}  y {min(ys):.2f} .. {max(ys):.2f}  "
          f"({max(xs) - min(xs):.2f} x {max(ys) - min(ys):.2f})")
    print(f"base   x {bb.xmin:.2f} .. {bb.xmax:.2f}  y {bb.ymin:.2f} .. {bb.ymax:.2f}  "
          f"z {bb.zmin:.2f} .. {bb.zmax:.2f}  ({bb.xlen:.1f} x {bb.ylen:.1f})")
    ok = True

    ph = pad_holes(base)
    print(f"board holes {holes}")
    print(f"pad holes   {ph}")
    for h in holes:
        hit = [p for p in ph if abs(p[0] - h[0]) < 0.01 and abs(p[1] - h[1]) < 0.01]
        ok &= bool(hit)
        print(f"  hole ({h[0]:.2f}, {h[1]:.2f}): {'on a pad insert' if hit else 'NO PAD'}")
    if len(ph) != len(holes):
        ok = False
        print(f"  {len(ph)} pad holes for {len(holes)} board holes")

    keep = {
        "board": prism(outline, BOARD_Z0, BOARD_Z1),
        "underside parts": prism(outline, UNDER_Z0, BOARD_Z0),
        "UNO Q + headers": box(*UNO["x"], *UNO["y"], *UNO["z"]),
    }
    for x, y in holes:
        keep[f"standoff ({x:g}, {y:g})"] = cq.Workplane("XY").workplane(offset=PAD_TOP).center(x, y).circle(STANDOFF_R).extrude(BOARD_Z0 - PAD_TOP)
    for slot in SLOTS:
        d = 1 if slot > 0 else -1
        mouth = slot - d * MOUTH_TO_SLOT
        for s in (-1, 1):
            yc = s * JST_Y
            keep[f"plug {slot:g} {'+' if s > 0 else '-'}y"] = box(mouth, mouth + d * PLUG_L, yc - PLUG_W / 2, yc + PLUG_W / 2, UNDER_Z0, BOARD_Z0)
            # cable: along x from the plug to the slot, then out through the wall
            r = CABLE_D / 2
            keep[f"cable {slot:g} {'+' if s > 0 else '-'}y"] = (
                box(mouth + d * PLUG_L, slot + d * r, yc - r, yc + r, 14.0, 18.0),
                box(slot - r, slot + r, yc, s * (bb.ymax + 1), 14.0, 18.0))
    print("interference (mm3, must be 0):")
    for name, k in keep.items():
        v = k[0].union(k[1]).val() if isinstance(k, tuple) else k.val()
        vb, vl = v.intersect(base).Volume(), v.intersect(lid).Volume()
        good = vb < 1e-6 and vl < 1e-6
        ok &= good
        print(f"  {name:22s} base {vb:7.3f}  lid {vl:7.3f}  {'ok' if good else 'CLASH'}")
    board = keep["board"].val()
    print(f"gaps: board to lid {board.distance(lid):.2f}, board to base {board.distance(base):.2f}")

    render(base, outline, holes, keep, png)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


def section_edges(shape, z):
    """Edges of the solid's cross-section at height z, as point lists."""
    sec = shape.intersect(cq.Solid.makeBox(1000, 200, 0.01, pnt=cq.Vector(-500, -100, z)))
    out = []
    for f in sec.Faces():
        if f.normalAt().z > -0.9:
            continue
        for e in f.Edges():
            n = 1 if e.geomType() == "LINE" else 24
            out.append([(p.x, p.y) for p in (e.positionAt(t / n) for t in range(n + 1))])
    return out


def render(base, outline, holes, keep, png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon, Rectangle

    fig, ax = plt.subplots(figsize=(16, 4.6), dpi=130)
    for pts in section_edges(base, 15.0):
        ax.plot(*zip(*pts), color="#4e483c", lw=0.9)
    for pts in section_edges(base, 4.0):
        if max(abs(p[1]) for p in pts) < 27.9:          # pads, bosses, posts (not the walls)
            ax.plot(*zip(*pts), color="#4e483c", lw=0.6, ls="--")
    ax.add_patch(Polygon(outline, closed=True, fc="#2e7d32", alpha=0.25, ec="#1b5e20", lw=1.2))
    for x, y in holes:
        ax.add_patch(Circle((x, y), 1.35, fc="white", ec="#1b5e20", lw=1))
    for name, k in keep.items():
        if name.startswith(("plug", "cable")):
            for part in (k if isinstance(k, tuple) else (k,)):
                b = part.val().BoundingBox()
                ax.add_patch(Rectangle((b.xmin, b.ymin), b.xlen, b.ylen, ec="none", alpha=0.45,
                                       fc="#e65100" if name.startswith("plug") else "#1565c0"))
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.set_xlabel("x (mm, +toe)")
    ax.set_ylabel("y (mm)")
    ax.set_title("Centre enclosure base (section at z 15; pads, bosses and posts dashed at z 4) with the ADC board (green), "
                 "plugs (orange) and cable runs (blue)", fontsize=9)
    ax.grid(True, lw=0.3, alpha=0.5)
    os.makedirs(os.path.dirname(os.path.abspath(png)), exist_ok=True)
    fig.savefig(png, bbox_inches="tight")
    print(f"wrote {png}")


if __name__ == "__main__":
    main()
