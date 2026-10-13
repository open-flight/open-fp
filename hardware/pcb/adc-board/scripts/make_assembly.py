#!/usr/bin/env python3
"""Write the PCBWay BOM and centroid files.

  python3 scripts/make_assembly.py .scratch/pos.csv

Input: kicad-cli pcb export pos --format csv --units mm --use-drill-file-origin (all sides).
Output: assembly/adc-board-bom.csv and assembly/adc-board-centroid.csv.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design  # noqa: E402

OUT = os.path.join(HERE, '..', 'assembly')


def main():
    parts, _ = design.build()
    by = {p['ref']: p for p in parts}
    rows = list(csv.DictReader(open(sys.argv[1])))
    os.makedirs(OUT, exist_ok=True)
    placed = {}
    with open(os.path.join(OUT, 'adc-board-centroid.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for r in sorted(rows, key=lambda r: natural(r['Ref'])):
            ref = r['Ref']
            if ref not in by:
                continue
            layer = 'Bottom' if r['Side'].lower().startswith('b') else 'Top'
            placed[ref] = layer
            w.writerow([ref, '%.3fmm' % float(r['PosX']), '%.3fmm' % float(r['PosY']), layer,
                        '%g' % (float(r['Rot']) % 360)])
    missing = sorted(set(by) - set(placed))
    assert not missing, 'not in the position file: %s' % missing
    groups = {}
    for p in parts:
        groups.setdefault(p['mpn'], []).append(p)
    with open(os.path.join(OUT, 'adc-board-bom.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Item', 'Designator', 'Qty', 'Manufacturer', 'MPN', 'Description', 'Value',
                    'Package', 'Type', 'Side', 'Alternative'])
        for i, (mpn, ps) in enumerate(sorted(groups.items(), key=lambda kv: natural(kv[1][0]['ref'])), 1):
            p = ps[0]
            refs = sorted((q['ref'] for q in ps), key=natural)
            sides = sorted(set(placed[r] for r in refs))
            w.writerow([i, ','.join(refs), len(refs), p['mfr'], mpn, p['desc'], p['value'],
                        p['pkg'], 'SMD', '/'.join(sides), p.get('alt', '')])
    print('BOM lines: %d, placements: %d' % (len(groups), len(placed)))


def natural(ref):
    import re
    m = re.match(r'([A-Z]+)(\d+)', ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


if __name__ == '__main__':
    main()
