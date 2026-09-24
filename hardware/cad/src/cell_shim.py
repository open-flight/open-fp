"""TPU shim ring (11_cell_shim_tpu) that stops the load cell rattling in the cradle.

The cell's raised centre strap faces out of the pocket, so its outer frame sits a few mm
below the cradle rim and the flat retainer doesn't touch it. This ring sits between the
retainer and the frame, pressing ONLY on the frame's outer edge (never the tongue or
strap), so it holds the frame against the pocket ceiling without changing the load path.
A gap lines up with the cable notch so the wires aren't clamped.

The gap depends on the cell, so this makes a tuning set. Print one of each, try them
with the retainer screwed down, and use the thinnest one that stops the rattle. Each ring
has 1-5 small nicks on the edge opposite the wire gap (1 = thinnest).
Print flat, TPU 95A, 100 % infill.   python hardware/cad/src/cell_shim.py
"""
from pathlib import Path

import cadquery as cq

OUTER = 34.0          # pocket is 34.6; cell is 34
INNER = 28.6          # stays on the frame (frame opening is ~27.3), outside the retainer window (28)
OUTER_R, INNER_R = 4.0, 2.0
WIRE_GAP = 9.0        # centred on the cable notch side (-y), wider than the 7 mm notch
THICKNESSES = [1.5, 2.0, 2.5, 3.0, 3.5]
NICK_W, NICK_D, NICK_PITCH = 1.0, 0.6, 2.5


def shim(t: float, nicks: int) -> cq.Workplane:
    ring = (cq.Workplane("XY").rect(OUTER, OUTER).extrude(t).edges("|Z").fillet(OUTER_R)
            .cut(cq.Workplane("XY").rect(INNER, INNER).extrude(t).edges("|Z").fillet(INNER_R)))
    ring = ring.cut(cq.Workplane("XY").center(0, -OUTER / 2).rect(WIRE_GAP, 8).extrude(t))
    xs = [(i - (nicks - 1) / 2) * NICK_PITCH for i in range(nicks)]
    for x in xs:
        ring = ring.cut(cq.Workplane("XY").center(x, OUTER / 2).rect(NICK_W, 2 * NICK_D).extrude(t))
    return ring


root = Path(__file__).resolve().parents[1]
for i, t in enumerate(THICKNESSES, start=1):
    name = f"11_cell_shim_tpu_{t:.1f}mm"
    part = shim(t, i)
    cq.exporters.export(part, str(root / "stl" / f"{name}.stl"), tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(part, str(root / "step" / f"{name}.step"))
    v = part.val()
    print(f"{name}: {i} nick(s), valid={v.isValid()}, volume={v.Volume():.0f} mm3")
