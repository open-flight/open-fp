#!/usr/bin/env python3
"""Write adc-board.kicad_sch from design.py.

Every pin end gets a net label, a power symbol, or a no-connect flag, so the
schematic is flat and readable without wires. Symbols are copied from the stock
KiCad libraries (ADS1220xPW is flattened from its parent ADS1120-PW).
Run: python3 scripts/gen_sch.py   (from hardware/pcb/adc-board)
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from sexp import Sym, parse, dump, find, findall  # noqa: E402
import design  # noqa: E402

KICAD_SYM = os.environ.get('KICAD_SYMBOL_DIR',
                           '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols')
OUT = os.path.join(os.path.dirname(__file__), '..', 'adc-board.kicad_sch')
Y, N = Sym('yes'), Sym('no')


def load_symbol(lib, name, as_name=None):
    t = parse(open(os.path.join(KICAD_SYM, lib + '.kicad_sym')).read())
    syms = {s[1]: s for s in findall(t, 'symbol')}
    s = copy.deepcopy(syms[name])
    ext = find(s, 'extends')
    if ext:
        parent = copy.deepcopy(syms[ext[1]])
        # keep the child's properties, take the parent's graphics and pins
        props = {p[1]: p for p in findall(s, 'property')}
        body = []
        for x in parent[2:]:
            if isinstance(x, list) and x[0] == 'property' and x[1] in props:
                body.append(props[x[1]])
            else:
                body.append(x)
        s = [Sym('symbol'), name] + body
    full = '%s:%s' % (lib, as_name or name)
    s[1] = full
    base = (as_name or name)
    for sub in findall(s, 'symbol'):
        suffix = sub[1].rsplit('_', 2)
        sub[1] = '%s_%s_%s' % (base, suffix[-2], suffix[-1])
    return s


def pins_of(sym):
    out = {}
    for sub in findall(sym, 'symbol'):
        for p in findall(sub, 'pin'):
            at = find(p, 'at')
            out[find(p, 'number')[1]] = (float(at[1]), float(at[2]), int(float(at[3])))
    return out


def eff(hide=False, justify=None):
    e = [Sym('effects'), [Sym('font'), [Sym('size'), 1.27, 1.27]]]
    if justify:
        e.append([Sym('justify')] + [Sym(j) for j in justify])
    if hide:
        e.append([Sym('hide'), Y])
    return e


class Sheet:
    def __init__(self):
        self.items = []
        self.libs = {}
        self.pwr = 0
        self.n = 0

    def lib(self, lib_id):
        if lib_id not in self.libs:
            lib, name = lib_id.split(':')
            src = {'ADS1220xPW': 'ADS1220xPW'}.get(name, name)
            sym = load_symbol(lib, src)
            if name == 'ADS1220xPW':
                # DOUT/DRDY goes high-Z when CS is high (datasheet 8.5.1), so all
                # eight share MISO. Mark it tri-state so ERC accepts the bus.
                for sub in findall(sym, 'symbol'):
                    for p in findall(sub, 'pin'):
                        if find(p, 'number')[1] == '15':
                            p[1] = Sym('tri_state')
            self.libs[lib_id] = sym
        return self.libs[lib_id]

    def uid(self, *k):
        self.n += 1
        return design.uid('sch', self.n, *k)

    def symbol(self, lib_id, x, y, ref, value, fp='', rot=0, fields=None, power=False, uuid_=None):
        sym = self.lib(lib_id)
        u = uuid_ or self.uid(ref)
        hide_ref = power
        node = [Sym('symbol'), [Sym('lib_id'), lib_id], [Sym('at'), x, y, rot], [Sym('unit'), 1],
                [Sym('exclude_from_sim'), N], [Sym('in_bom'), N if power else Y],
                [Sym('on_board'), N if power else Y], [Sym('dnp'), N], [Sym('uuid'), u],
                [Sym('property'), 'Reference', ref, [Sym('at'), x + 2.54, y - 1.27, 0],
                 eff(hide=hide_ref, justify=['left'])],
                [Sym('property'), 'Value', value, [Sym('at'), x + 2.54, y + 1.27, 0],
                 eff(justify=['left'])],
                [Sym('property'), 'Footprint', fp, [Sym('at'), x, y, 0], eff(hide=True)],
                [Sym('property'), 'Datasheet', '~', [Sym('at'), x, y, 0], eff(hide=True)],
                [Sym('property'), 'Description', '', [Sym('at'), x, y, 0], eff(hide=True)]]
        for k, v in (fields or {}).items():
            node.append([Sym('property'), k, v, [Sym('at'), x, y, 0], eff(hide=True)])
        for num in pins_of(sym):
            node.append([Sym('pin'), num, [Sym('uuid'), design.uid('pin', u, num)]])
        node.append([Sym('instances'), [Sym('project'), design.PROJECT,
                     [Sym('path'), '/' + design.ROOT_UUID, [Sym('reference'), ref], [Sym('unit'), 1]]]])
        self.items.append(node)
        return sym

    def pin_end(self, sym, num, x, y, rot=0):
        px, py, a = pins_of(sym)[num]
        # rotate (symbol coords, y up) then flip y for the sheet
        import math
        r = math.radians(rot)
        rx = px * math.cos(r) - py * math.sin(r)
        ry = px * math.sin(r) + py * math.cos(r)
        return round(x + rx, 2), round(y - ry, 2), (a + rot + 180) % 360

    def label(self, net, x, y, out):
        just = {0: ['left', 'bottom'], 90: ['left', 'bottom'], 180: ['right', 'bottom'],
                270: ['right', 'bottom']}[out]
        self.items.append([Sym('label'), net, [Sym('at'), x, y, out], eff(justify=just),
                           [Sym('uuid'), self.uid('lbl', net)]])

    def power(self, net, x, y, out):
        self.pwr += 1
        ref = '#PWR%03d' % self.pwr
        lib_id = 'power:GND' if net == 'GND' else 'power:+3V3'
        rot = (out - (270 if net == 'GND' else 90)) % 360
        self.symbol(lib_id, x, y, ref, net, rot=rot, power=True)

    def nc(self, x, y):
        self.items.append([Sym('no_connect'), [Sym('at'), x, y], [Sym('uuid'), self.uid('nc')]])

    def text(self, s, x, y, size=1.27):
        self.items.append([Sym('text'), s, [Sym('exclude_from_sim'), N], [Sym('at'), x, y, 0],
                           [Sym('effects'), [Sym('font'), [Sym('size'), size, size]],
                            [Sym('justify'), Sym('left'), Sym('bottom')]],
                           [Sym('uuid'), self.uid('txt')]])

    def place(self, p, x, y, rot=0):
        fields = {'Manufacturer': p['mfr'], 'MPN': p['mpn'], 'Description': p['desc']}
        sym = self.symbol(p['sym'], x, y, p['ref'], p['value'], p['fp'], rot, fields, uuid_=p['uuid'])
        for num, net in p['pins'].items():
            ex, ey, out = self.pin_end(sym, num, x, y, rot)
            if net is None:
                self.nc(ex, ey)
            elif net in ('GND', '+3V3'):
                self.power(net, ex, ey, out)
            else:
                self.label(net, ex, ey, out)
        return sym

    def write(self, path):
        g = 2.54
        root = [Sym('kicad_sch'), [Sym('version'), 20250114], [Sym('generator'), 'eeschema'],
                [Sym('generator_version'), '9.0'], [Sym('uuid'), design.ROOT_UUID],
                [Sym('paper'), 'A2'],
                [Sym('title_block'), [Sym('title'), 'open-fp ADC board (8x ADS1220, UNO Q shield)'],
                 [Sym('rev'), 'A'], [Sym('company'), 'open-fp'],
                 [Sym('comment'), 1, 'Generated by scripts/gen_sch.py from scripts/design.py'],
                 [Sym('comment'), 2, 'Ratiometric: REFP0=3V3=E+, REFN0=GND; AIN0=S, AIN1=1.5k/1.5k divider']],
                [Sym('lib_symbols')] + list(self.libs.values())]
        root += self.items
        root.append([Sym('sheet_instances'), [Sym('path'), '/', [Sym('page'), '1']]])
        root.append([Sym('embedded_fonts'), N])
        with open(path, 'w') as f:
            f.write(dump(root) + '\n')


def main():
    parts, _ = design.build()
    by = {p['ref']: p for p in parts}
    sh = Sheet()
    g = 2.54
    for k, (name, cs, slot, side) in enumerate(design.CHANNELS, start=1):
        col, row = (k - 1) % 4, (k - 1) // 4
        bx, by_ = 14 * g + col * 54 * g, 20 * g + row * 40 * g
        wall = '+y' if side > 0 else '-y'
        sh.text('Channel %s  (CS %s, slot x=%+d on the %s wall)' % (name, cs, slot, wall),
                bx, by_ - 2 * g, 2.0)
        sh.place(by['J%d' % k], bx + 6 * g, by_ + 8 * g)
        sh.text('J%d: 1=E+ white, 2=E- black, 3=S red' % k, bx, by_ + 14 * g)
        sh.place(by['U%d' % k], bx + 28 * g, by_ + 12 * g)
        row_y = by_ + 30 * g
        for i, n in enumerate(['R%d01' % k, 'R%d02' % k, 'R%d03' % k, 'R%d04' % k,
                               'C%d01' % k, 'C%d02' % k, 'C%d03' % k, 'C%d04' % k,
                               'C%d05' % k, 'C%d06' % k, 'C%d07' % k]):
            sh.place(by[n], bx + (2 + 4 * i) * g, row_y)
    hx, hy = 20 * g, 20 * g + 80 * g + 6 * g
    sh.text('UNO Q shield headers (SMD male, board underside). Never connect D0, D1, D10.',
            hx, hy - 2 * g, 2.0)
    for i, ref in enumerate(['J9', 'J10', 'J11', 'J12']):
        p = by[ref]
        x0, y0 = hx + (12 + 30 * i) * g, hy + 8 * g
        sym = sh.place(p, x0, y0)
        for j, qn in enumerate(p['qpins']):
            ex, ey, _ = sh.pin_end(sym, str(j + 1), x0, y0)
            sh.text("Q " + qn, x0 + 6 * g, ey + 0.6)
    sh.place(by['R1'], hx + 135 * g, hy + 8 * g)
    sh.text('R1: SCLK series, near the Q', hx + 133 * g, hy + 14 * g)
    sh.place(by['C1'], hx + 145 * g, hy + 8 * g)
    sh.place(by['C2'], hx + 150 * g, hy + 8 * g)
    sh.text('3V3 entry bulk + HF', hx + 143 * g, hy + 14 * g)
    # PWR_FLAGs
    for i, net in enumerate(['+3V3', 'GND']):
        x, y = hx + (160 + 6 * i) * g, hy + 8 * g
        sym = sh.symbol('power:PWR_FLAG', x, y, '#FLG%02d' % (i + 1), 'PWR_FLAG', power=True)
        ex, ey, out = sh.pin_end(sym, '1', x, y)
        sh.power(net, ex, ey, out)
    sh.write(OUT)
    print('wrote', os.path.abspath(OUT))


if __name__ == '__main__':
    main()
