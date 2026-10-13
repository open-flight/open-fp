#!/usr/bin/env python3
"""Place the open-fp ADC board and export a Specctra DSN for Freerouting.

Run with KiCad's bundled Python (it has the pcbnew module), from hardware/pcb/adc-board:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
      scripts/gen_pcb.py

Coordinates: the enclosure frame from hardware/cad (mm): +x toe, +y the LEFT plate's
side, origin at the centre of the base footprint. KiCad: kx = 150 + x, ky = 100 - y.
Every component goes on the board UNDERSIDE (B.Cu); the top side carries only copper
and silkscreen, because the board top is 0.9 mm under the (raised) lid.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design  # noqa: E402

FPLIB = os.environ.get('KICAD_FOOTPRINT_DIR',
                       '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
OUTDIR = os.path.join(HERE, '..')
BOARD = os.path.join(OUTDIR, 'adc-board.kicad_pcb')
OX, OY = 150.0, 100.0

# ---- mechanical ----------------------------------------------------------------
HALF_W = 25.0          # board y extent (lid lip inner edge is at +-25.3)
TAB_W = 27.35          # local tabs under the SMD shield headers (lip notched there)
TAB_X = (-18.0, 32.0)
NOTCH_X, NOTCH_Y = 135.5, 18.5   # corner notches clear the lid posts at (+-140, +-23)
END_X = 142.0
HOLES = [(-129.5, 0.0), (-54.5, 0.0), (54.5, 0.0), (129.5, 0.0)]   # ADC-pad insert grid
MOUTH = {85: 70.0, 125: 110.0}   # JST mouth |x| for each slot |x|


def mm(v):
    return pcbnew.FromMM(v)


def kpt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY - y))


def enc(p):
    return (pcbnew.ToMM(p.x) - OX, OY - pcbnew.ToMM(p.y))


def outline():
    pts = [(-NOTCH_X, HALF_W), (TAB_X[0], HALF_W), (TAB_X[0], TAB_W), (TAB_X[1], TAB_W),
           (TAB_X[1], HALF_W), (NOTCH_X, HALF_W), (NOTCH_X, NOTCH_Y), (END_X, NOTCH_Y),
           (END_X, -NOTCH_Y), (NOTCH_X, -NOTCH_Y), (NOTCH_X, -HALF_W), (TAB_X[1], -HALF_W),
           (TAB_X[1], -TAB_W), (TAB_X[0], -TAB_W), (TAB_X[0], -HALF_W), (-NOTCH_X, -HALF_W),
           (-NOTCH_X, -NOTCH_Y), (-END_X, -NOTCH_Y), (-END_X, NOTCH_Y), (-NOTCH_X, NOTCH_Y)]
    return pts


def read_nc_names(path):
    """(ref, pin) -> 'unconnected-(...)' net names from the schematic's netlist export."""
    from sexp import parse, find, findall
    out = {}
    if not os.path.exists(path):
        print('note: %s missing; unconnected pins get no net' % path)
        return out
    t = parse(open(path).read())
    for n in findall(find(t, 'nets'), 'net'):
        name = find(n, 'name')[1]
        if name.startswith('unconnected-'):
            for x in findall(n, 'node'):
                out[(find(x, 'ref')[1], find(x, 'pin')[1])] = name
    return out


class Builder:
    def __init__(self):
        self.board = pcbnew.NewBoard(BOARD)
        self.nets = {}
        self.fps = {}
        self.nc_names = read_nc_names(os.path.join(OUTDIR, 'adc-board.net'))

    def raw_net(self, kname):
        if kname not in self.nets:
            ni = pcbnew.NETINFO_ITEM(self.board, kname)
            self.board.Add(ni)
            self.nets[kname] = ni
        return self.nets[kname]

    def net(self, name):
        if name is None:
            return None
        kname = name if name in ('GND', '+3V3') else '/' + name
        if kname not in self.nets:
            ni = pcbnew.NETINFO_ITEM(self.board, kname)
            self.board.Add(ni)
            self.nets[kname] = ni
        return self.nets[kname]

    def setup(self):
        b = self.board
        ds = b.GetDesignSettings()
        ds.SetCopperLayerCount(2)
        ds.SetBoardThickness(mm(1.6))
        ds.m_TrackMinWidth = mm(0.15)
        ds.m_MinClearance = mm(0.15)
        ds.m_ViasMinSize = mm(0.6)
        ds.m_MinThroughDrill = mm(0.3)
        ds.m_CopperEdgeClearance = mm(0.3)
        ds.m_HoleClearance = mm(0.25)
        ds.m_HoleToHoleMin = mm(0.25)
        # drill/place origin = lower-left corner of the board's bounding box (fab files)
        ds.SetAuxOrigin(kpt(-END_X, -TAB_W))
        ns = ds.m_NetSettings
        dflt = ns.GetDefaultNetclass()
        dflt.SetTrackWidth(mm(0.2))
        dflt.SetClearance(mm(0.2))
        dflt.SetViaDiameter(mm(0.6))
        dflt.SetViaDrill(mm(0.3))
        pwr = pcbnew.NETCLASS('Power')
        pwr.SetTrackWidth(mm(0.4))
        pwr.SetClearance(mm(0.2))
        pwr.SetViaDiameter(mm(0.7))
        pwr.SetViaDrill(mm(0.35))
        ns.SetNetclass('Power', pwr)
        ns.SetNetclassPatternAssignment('GND', 'Power')
        ns.SetNetclassPatternAssignment('+3V3', 'Power')
        for i, (a, c) in enumerate(zip(outline(), outline()[1:] + outline()[:1])):
            s = pcbnew.PCB_SHAPE(b)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(kpt(*a))
            s.SetEnd(kpt(*c))
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(mm(0.1))
            b.Add(s)

    def load(self, fpid):
        lib, name = fpid.split(':')
        fp = pcbnew.FootprintLoad(os.path.join(FPLIB, lib + '.pretty'), name)
        fp.SetFPIDAsString(fpid)
        return fp

    def add(self, p, x, y, want, side='bottom'):
        """Place part p centred at enclosure (x, y) on the given side.

        want(fp) -> score; the orientation (0/90/180/270) with the highest score wins.
        """
        fp = self.load(p['fp'])
        fp.SetReference(p['ref'])
        fp.SetValue(p['value'])
        for k, v in (('Manufacturer', p['mfr']), ('MPN', p['mpn']), ('Description', p['desc'])):
            fp.SetField(k, v)
            fp.GetField(k).SetVisible(False)
        if p['ref'][0] in 'RC':
            fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
        fp.Reference().SetTextThickness(mm(0.12))
        fp.SetPath(pcbnew.KIID_PATH('/' + p['uuid']))
        fp.SetSheetfile('adc-board.kicad_sch')
        fp.SetSheetname('/')
        self.board.Add(fp)
        fp.SetPosition(kpt(x, y))
        if side == 'bottom':
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        best = None
        for a in (0, 90, 180, 270):
            fp.SetOrientationDegrees(a)
            sc = want(fp)
            if best is None or sc > best[0] + 1e-9:
                best = (sc, a)
        fp.SetOrientationDegrees(best[1])
        if p['ref'][0] in 'UJ':
            fp.Reference().SetPosition(fp.GetPosition())   # inside the body outline
        for pad in fp.Pads():
            n = p['pins'].get(pad.GetNumber())
            if n:
                pad.SetNet(self.net(n))
            elif (p['ref'], pad.GetNumber()) in self.nc_names:
                # KiCad's own name for an unconnected pin, so schematic parity is exact
                pad.SetNet(self.raw_net(self.nc_names[(p['ref'], pad.GetNumber())]))
        self.fps[p['ref']] = fp
        return fp


def pad_xy(fp, num):
    pts = [enc(pd.GetPosition()) for pd in fp.Pads() if pd.GetNumber() == num]
    return (sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts))


def dir_score(a, b, d):
    """Dot product of unit(a->b) with d."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1
    return (dx * d[0] + dy * d[1]) / n


def two_pin(d):
    return lambda fp: dir_score(pad_xy(fp, '1'), pad_xy(fp, '2'), d)


def main():
    parts, headers = design.build()
    by = {p['ref']: p for p in parts}
    B = Builder()
    B.setup()

    # --- shield headers: pin k exactly on the Uno R3 grid ---------------------------------
    ux0, uy0 = design.UNO_ORIGIN
    for ref, (uy, uxs) in headers.items():
        p = by[ref]
        first = (uxs[0] + ux0, uy + uy0)
        last = (uxs[-1] + ux0, uy + uy0)
        cx, cy = (first[0] + last[0]) / 2, (first[1] + last[1]) / 2
        d = (1 if last[0] > first[0] else -1, 0)
        fp = B.add(p, cx, cy, lambda f, d=d: dir_score(pad_xy(f, '1'), pad_xy(f, str(len(uxs))), d))
        # check: the pin line (mid-point between alternating pads) is on the target
        for k, ux in enumerate(uxs):
            px, py = pad_xy(fp, str(k + 1))
            assert abs(px - (ux + ux0)) < 0.01, (ref, k, px, ux + ux0)
            assert abs(abs(py - (uy + uy0)) - 1.655) < 0.01, (ref, k, py)

    # --- channel blocks --------------------------------------------------------------------
    for k, (name, cs, slot, side) in enumerate(design.CHANNELS, start=1):
        s = 1 if slot > 0 else -1
        t = side
        xm = s * MOUTH[abs(slot)]

        def E(u, v):
            return (xm + s * u, t * v)

        U = B.add(by['U%d' % k], *E(-22.0, 16.0),
                  want=lambda f: dir_score(enc(f.GetPosition()),
                                           ((pad_xy(f, '8')[0] + pad_xy(f, '9')[0]) / 2,
                                            (pad_xy(f, '8')[1] + pad_xy(f, '9')[1]) / 2), (s, 0)))
        J = B.add(by['J%d' % k], *E(-5.3, 17.8),
                  want=lambda f: dir_score(pad_xy(f, '2'), pad_xy(f, 'MP'), (s, 0)))
        # REF cap across REFP0 (pin 9, +3V3) and REFN0 (pin 8, GND), at the analog end
        p9, p8 = pad_xy(U, '9'), pad_xy(U, '8')
        d98 = (0, 1 if p9[1] > p8[1] else -1)
        B.add(by['C%d03' % k], *E(-17.9, 16.0), want=two_pin(d98))
        vdir = (0, t)
        grid = {
            'C%d05' % k: (-15.6, 12.4), 'C%d04' % k: (-15.6, 15.5), 'C%d06' % k: (-15.6, 18.6),
            'R%d02' % k: (-15.6, 21.7), 'R%d03' % k: (-12.9, 12.4), 'R%d04' % k: (-12.9, 18.6),
            'R%d01' % k: (-12.9, 21.7),
        }
        # keep the S resistor (R?03) on the same side as the JST's S pin (pin 3), so the
        # S -> R -> AIN0 path is short: mirror the RC rows when pin 3 is the outer pin
        outer3 = abs(pad_xy(J, '3')[1]) > abs(enc(J.GetPosition())[1])
        for ref, (u, v) in grid.items():
            if outer3:
                v = 34.1 - v
            B.add(by[ref], *E(u, v), want=two_pin(vdir))
        # top-layer keepout over the analog end (AIN pair, divider, RC, JST): no tracks
        # or vias, so SPI cannot run over AIN0/AIN1 and the top GND pour stays solid there
        keepout(B.board, [E(-17.0, 10.6), E(0.5, 10.6), E(0.5, 24.7), E(-17.0, 24.7)],
                pcbnew.F_Cu, 'analog_%s' % name)
        # bottom-layer strip between the RC network and the board edge: stops the router
        # running other channels' SPI/CS along the edge past this channel's AIN nets
        keepout(B.board, [E(-30.5, 23.3), E(0.5, 23.3), E(0.5, 25.5), E(-30.5, 25.5)],
                pcbnew.B_Cu, 'edge_%s' % name)
        # decoupling at the digital end, pads along u (+3V3 pad toward the chip)
        udir = (-s, 0)
        B.add(by['C%d01' % k], *E(-27.2, 16.95), want=two_pin(udir))
        B.add(by['C%d02' % k], *E(-27.2, 15.05), want=two_pin(udir))
        B.add(by['C%d07' % k], *E(-27.2, 10.9), want=two_pin(udir))

    # --- Q-side parts ---------------------------------------------------------------------
    d13 = (28.96 + ux0, 50.8 + uy0)
    v33 = (35.56 + ux0, 2.54 + uy0)
    B.add(by['R1'], d13[0], 18.3, want=two_pin((0, 1)))
    B.add(by['C1'], v33[0] + 1.3, -18.3, want=two_pin((0, -1)))
    B.add(by['C2'], v33[0] + 4.3, -18.3, want=two_pin((0, -1)))

    # --- mounting holes -------------------------------------------------------------------
    for i, (x, y) in enumerate(HOLES):
        fp = B.load(design.FP_HOLE)
        fp.SetReference('H%d' % (i + 1))
        fp.SetValue('M2.5')
        B.board.Add(fp)
        fp.SetPosition(kpt(x, y))
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)

    silkscreen(B, parts)
    B.board.BuildConnectivity()
    pcbnew.SaveBoard(BOARD, B.board)
    print('saved', os.path.abspath(BOARD), 'nets', len(B.nets))


def keepout(board, pts, layer, name):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    z.SetLayer(layer)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in pts:
        p = kpt(x, y)
        ol.Append(p.x, p.y)
    board.Add(z)


def text(board, s, x, y, size=1.5, layer=pcbnew.F_SilkS, angle=0, thick=0.2, just=None):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(kpt(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(thick))
    t.SetTextAngleDegrees(angle)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    if just == 'left':
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    board.Add(t)
    return t


def silkscreen(B, parts):
    b = B.board
    F, Bk = pcbnew.F_SilkS, pcbnew.B_SilkS
    text(b, 'open-fp ADC board rev A  -  8x ADS1220  -  UNO Q shield', -95, -3.5, 1.5)
    text(b, 'all parts on the underside', -95, -6.0, 1.2)
    text(b, 'TOE  +x  >>>', 95, -3.5, 1.8)
    text(b, '<<<  HEEL  -x', -95, 3.0, 1.8)
    text(b, 'UNO Q below', 8, 0, 1.5)
    text(b, '+y : LEFT plate side', 8, 14, 1.2)
    text(b, '-y : RIGHT plate side', 8, -14, 1.2)
    for k, (name, cs, slot, side) in enumerate(design.CHANNELS, start=1):
        J = B.fps['J%d' % k]
        s = 1 if slot > 0 else -1
        jx, jy = enc(J.GetPosition())
        # top side: big channel name, slot, and W/B/R next to each pin (pads are below)
        text(b, name, jx - s * 12, jy - side * 0.2 + side * 0.0, 2.5, F, thick=0.35)
        text(b, 'slot x=%+d' % slot, jx + s * 9.0, side * 11.5, 1.0, F)
        for pin, col in (('1', 'W'), ('2', 'B'), ('3', 'R')):
            px, py = pad_xy(J, pin)
            text(b, col, px - s * 4.0, py, 1.2, F, thick=0.2)
        p1 = pad_xy(J, '1')
        text(b, '1', p1[0] + s * 3.2, p1[1], 1.0, F)
        text(b, 'pin1=E+ W  2=E- B  3=S R', jx - s * 8, side * 9.0, 0.9, F, thick=0.15)
        # bottom side: channel name in the (part-free) plug corridor, readable from below
        text(b, name, jx + s * 11.5, jy, 2.5, Bk, thick=0.35)
        for pin, col in (('1', 'W'), ('2', 'B'), ('3', 'R')):
            text(b, col, jx + s * 7.2, pad_xy(J, pin)[1], 1.0, Bk, thick=0.15)


if __name__ == '__main__':
    main()
