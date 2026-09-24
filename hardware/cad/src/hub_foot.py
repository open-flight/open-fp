"""TPU hub foot (10_hub_foot_tpu) that locates on the load cell's centre strap.

The 50 kg half-bridge cell's load point is a riveted steel strap across the centre
tongue with a dome in the middle. This foot has a channel the strap drops into (stops
it sliding or rotating) and a dimple that catches the dome (centres it along the strap).
The bottom face is the only part of the plate that touches the floor.

Dimensions marked EST were estimated from photos (34 mm frame for scale). Measure with
calipers and edit, then run:  python hardware/cad/src/hub_foot.py
Print flat, channel up, TPU 95A, 100 % infill.
"""
from pathlib import Path

import cadquery as cq

# -- cell strap (measure these) --------------------------------------------------------
STRAP_W = 11.0        # EST width of the raised strap
DOME_D = 5.5          # EST diameter of the centre dome
# -- foot ----------------------------------------------------------------------------------
CLEAR = 0.4           # total side clearance so the strap drops in easily
FOOT_D = 18.0         # was 16; wider so there is material beside the channel
BASE_T = 3.5          # foot material below the load point (sets the floor clearance)
CHANNEL_D = 1.2       # how deep the strap sits in the foot; keep below the strap's height above the tongue
DIMPLE_D = DOME_D + 0.5
DIMPLE_DEPTH = 0.6
EDGE_CHAMFER = 0.4

T = BASE_T + CHANNEL_D
foot = cq.Workplane("XY").circle(FOOT_D / 2).extrude(T).faces("<Z").edges().chamfer(EDGE_CHAMFER)
foot = foot.cut(cq.Workplane("XY").workplane(offset=T - CHANNEL_D)
                .rect(FOOT_D + 2, STRAP_W + CLEAR).extrude(CHANNEL_D + 0.1))
foot = foot.cut(cq.Workplane("XY").workplane(offset=T - CHANNEL_D - DIMPLE_DEPTH)
                .circle(DIMPLE_D / 2).extrude(DIMPLE_DEPTH + 0.1))

root = Path(__file__).resolve().parents[1]
cq.exporters.export(foot, str(root / "stl" / "10_hub_foot_tpu.stl"), tolerance=0.01, angularTolerance=0.1)
cq.exporters.export(foot, str(root / "step" / "10_hub_foot_tpu.step"))
bb = foot.val().BoundingBox()
print(f"10_hub_foot_tpu: Ø{FOOT_D} x {T:.1f} mm, channel {STRAP_W + CLEAR:.1f} wide x {CHANNEL_D} deep, "
      f"dimple Ø{DIMPLE_D:.1f} x {DIMPLE_DEPTH}; bbox {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f}")
