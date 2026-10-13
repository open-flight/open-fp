#!/usr/bin/env python3
"""Autoroute with Freerouting, then add GND stitching vias and both-layer GND pours.

  KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
  $KPY scripts/route.py /path/to/freerouting.jar [passes]   # route + finish
  $KPY scripts/route.py finish                               # redo vias/zones only

Steps: export DSN -> java -jar freerouting.jar -> import SES -> stitching vias -> zones -> fill.
Needs Java 21+ (brew install openjdk) and freerouting.jar (github.com/freerouting/freerouting).
"""
import math
import os
import shutil
import subprocess
import sys

import pcbnew

sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, '..', 'adc-board.kicad_pcb')
WORK = os.path.join(HERE, '..', '.scratch')
JAVA = os.environ.get('JAVA', '/opt/homebrew/opt/openjdk/bin/java')
KICAD_CLI = os.environ.get('KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
OX, OY = 150.0, 100.0


def mm(v):
    return pcbnew.FromMM(v)


def route(jar, passes):
    os.makedirs(WORK, exist_ok=True)
    b = pcbnew.LoadBoard(BOARD)
    dsn, ses = os.path.join(WORK, 'adc-board.dsn'), os.path.join(WORK, 'adc-board.ses')
    assert pcbnew.ExportSpecctraDSN(b, dsn), 'DSN export failed'
    shrink_boundary(dsn, 150)   # keep routing >= 0.3 mm from the edge (DRC rule)
    subprocess.check_call([JAVA, '-jar', jar, '-de', dsn, '-do', ses, '-mp', str(passes),
                           '--gui.enabled=false'])
    assert pcbnew.ImportSpecctraSES(b, ses), 'SES import failed'
    return b


def shrink_boundary(dsn, d_um):
    """Offset the DSN's rectilinear board boundary inward by d_um (DSN units are um)."""
    import re
    txt = open(dsn).read()
    m = re.search(r'\(boundary\s*\(path pcb 0\s+([-\d.\s]+)\)', txt)
    nums = [float(x) for x in m.group(1).split()]
    pts = list(zip(nums[0::2], nums[1::2]))
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts)))
    sgn = 1 if area > 0 else -1     # CCW (y up): inward normal of edge (dx,dy) is (-dy,dx)
    out = []
    for i in range(len(pts)):
        a, c, e = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
        n1 = norm((-(c[1] - a[1]) * sgn, (c[0] - a[0]) * sgn))
        n2 = norm((-(e[1] - c[1]) * sgn, (e[0] - c[0]) * sgn))
        out.append((c[0] + d_um * (n1[0] + n2[0]), c[1] + d_um * (n1[1] + n2[1])))
    out.append(out[0])
    new = '(boundary\n      (path pcb 0  ' + '  '.join('%.1f %.1f' % p for p in out) + ')'
    txt = txt[:m.start()] + new + txt[m.end():]
    open(dsn, 'w').write(txt)


def norm(v):
    n = math.hypot(*v) or 1
    return (v[0] / n, v[1] / n)


def stitch(b, pitch=6.0):
    """GND vias on a grid wherever nothing else is within 0.9 mm (both layers)."""
    gnd = b.FindNet('GND')
    obstacles = []
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            obstacles.append(('circ', t.GetPosition(), mm(0.3 + 0.9 + 0.3)))
        else:
            obstacles.append(('seg', t.GetStart(), t.GetEnd(), t.GetWidth() / 2))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            obstacles.append(('box', bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
        if fp.GetReference().startswith('H'):
            obstacles.append(('circ', fp.GetPosition(), mm(3.5)))
        cy = fp.GetCourtyard(pcbnew.B_CrtYd)
        bb = fp.GetBoundingBox(False)
        if fp.GetFPIDAsString().startswith('Connector_JST'):
            obstacles.append(('box', bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
    edge = b.GetBoardEdgesBoundingBox()
    poly = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(poly, True)
    clr = mm(0.9)
    n = 0
    y = edge.GetTop() + mm(2)
    while y < edge.GetBottom() - mm(2):
        x = edge.GetLeft() + mm(2)
        while x < edge.GetRight() - mm(2):
            pt = pcbnew.VECTOR2I(int(x), int(y))
            ok = poly.Contains(pt) and all(
                poly.Contains(pcbnew.VECTOR2I(int(x + dx), int(y + dy)))
                for dx, dy in ((mm(1.5), 0), (-mm(1.5), 0), (0, mm(1.5)), (0, -mm(1.5))))
            if ok:
                ring = [pcbnew.VECTOR2I(int(x + dx), int(y + dy)) for dx, dy in
                        ((0, 0), (mm(0.5), 0), (-mm(0.5), 0), (0, mm(0.5)), (0, -mm(0.5)))]
                if any(z.GetIsRuleArea() and z.Outline().Contains(q) for z in b.Zones() for q in ring):
                    ok = False
            if ok:
                for o in obstacles:
                    if o[0] == 'seg':
                        if seg_dist(pt, o[1], o[2]) < o[3] + clr:
                            ok = False
                            break
                    elif o[0] == 'box':
                        if o[1] - clr < x < o[3] + clr and o[2] - clr < y < o[4] + clr:
                            ok = False
                            break
                    else:
                        if math.hypot(x - o[1].x, y - o[1].y) < o[2]:
                            ok = False
                            break
            if ok:
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(pt)
                v.SetWidth(mm(0.6))
                v.SetDrill(mm(0.3))
                v.SetNet(gnd)
                b.Add(v)
                n += 1
            x += mm(pitch)
        y += mm(pitch)
    return n


def seg_dist(p, a, c):
    ax, ay, cx, cy, px, py = a.x, a.y, c.x, c.y, p.x, p.y
    dx, dy = cx - ax, cy - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def zones(b):
    gnd = b.FindNet('GND')
    for z in list(b.Zones()):
        if not z.GetIsRuleArea():
            b.Remove(z)
    bb = b.GetBoardEdgesBoundingBox()
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(b)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetLocalClearance(mm(0.25))
        z.SetMinThickness(mm(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetThermalReliefGap(mm(0.25))
        z.SetThermalReliefSpokeWidth(mm(0.3))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline()
        ol.NewOutline()
        m = mm(0.5)
        for x, y in ((bb.GetLeft() - m, bb.GetTop() - m), (bb.GetRight() + m, bb.GetTop() - m),
                     (bb.GetRight() + m, bb.GetBottom() + m), (bb.GetLeft() - m, bb.GetBottom() + m)):
            ol.Append(int(x), int(y))
        z.SetAssignedPriority(0)
        b.Add(z)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())


def widen(b, w=0.15, clearance=0.2, fine=0.15):
    """Freerouting necks tracks down at some pads; bring them up to the 0.15 mm minimum
    wherever that keeps the clearance (0.2 mm; 0.15 mm to the ADS1220's 0.65 mm-pitch
    pads, as allowed by the 'tssop_fine_pitch' rule in adc-board.kicad_dru)."""
    pads = [p for fp in b.GetFootprints() for p in fp.Pads()]
    fine_pads = set(p.m_Uuid.AsString() for fp in b.GetFootprints()
                    if fp.GetReference().startswith('U') for p in fp.Pads())
    tracks = list(b.GetTracks())
    n = kept = 0
    for t in tracks:
        if t.GetClass() != 'PCB_TRACK' or t.GetWidth() >= mm(w):
            continue
        old = t.GetWidth()
        t.SetWidth(mm(w))
        lay = t.GetLayer()
        shp = t.GetEffectiveShape(lay)
        bad = False
        for o in pads + tracks:
            if o is t or o.GetNetCode() == t.GetNetCode() or not o.IsOnLayer(lay):
                continue
            c = clearance
            if o.GetClass() == 'PAD' and o.m_Uuid.AsString() in fine_pads:
                c = fine
            if o.GetEffectiveShape(lay).Collide(shp, mm(c) - 1):
                bad = True
                print('  neck at (%.2f, %.2f) blocked by %s %s' % (
                    pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y), o.GetClass(),
                    o.GetNetname()))
                break
        if bad:
            t.SetWidth(old)
            kept += 1
        else:
            n += 1
    if kept:
        print('WARNING: %d necked segments could not be widened' % kept)
    return n


def drop_dangling_vias(b):
    """Remove signal vias that Freerouting left connected on one layer only."""
    dead = []
    fps = list(b.GetFootprints())
    for v in [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']:
        if v.GetNetname() == 'GND':
            continue
        pos, r = v.GetPosition(), v.GetWidth(pcbnew.F_Cu) / 2
        layers = set()
        for t in b.GetTracks():
            if t.GetClass() == 'PCB_TRACK' and t.GetNetCode() == v.GetNetCode():
                if seg_dist(pos, t.GetStart(), t.GetEnd()) <= r + t.GetWidth() / 2:
                    layers.add(t.GetLayer())
        for fp in fps:
            for p in fp.Pads():
                if p.GetNetCode() == v.GetNetCode() and p.HitTest(pos):
                    layers |= {pcbnew.F_Cu, pcbnew.B_Cu} & set(p.GetLayerSet().Seq())
        if len(layers) < 2:
            dead.append(v)
    for v in dead:
        b.Delete(v)
    return len(dead)


def drc_errors():
    out = os.path.join(WORK, 'drc_try.json')
    subprocess.call([KICAD_CLI, 'pcb', 'drc', '--schematic-parity', '--severity-error',
                     '--format', 'json', '-o', out, BOARD],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import json
    d = json.load(open(out))
    return (len(d.get('violations', [])) + len(d.get('unconnected_items', []))
            + len(d.get('schematic_parity', [])))


def finish(routed):
    b = pcbnew.LoadBoard(routed)
    print('widened %d necked-down segments' % widen(b))
    n = stitch(b)
    zones(b)
    b.BuildConnectivity()
    pcbnew.SaveBoard(BOARD, b)
    print('%d stitching vias; saved %s' % (n, os.path.abspath(BOARD)))


def main():
    routed = os.path.join(WORK, 'routed.kicad_pcb')
    if sys.argv[1] == 'finish':
        finish(routed)
        return
    passes = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    tries = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    placed = os.path.join(WORK, 'placed.kicad_pcb')
    shutil.copy(BOARD, placed)
    for i in range(tries):
        # Freerouting is not deterministic; retry until DRC has zero errors
        shutil.copy(placed, BOARD)
        b = route(sys.argv[1], passes)
        pcbnew.SaveBoard(routed, b)
        finish(routed)
        e = drc_errors()
        print('attempt %d: %d DRC errors' % (i + 1, e))
        if e == 0:
            return
    sys.exit('no clean route after %d attempts' % tries)


if __name__ == '__main__':
    main()
