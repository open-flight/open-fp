#!/usr/bin/env python3
"""Compare a KiCad netlist export (kicad-cli sch export netlist) against design.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from sexp import parse, find, findall  # noqa: E402
import design  # noqa: E402

t = parse(open(sys.argv[1]).read())
got = {}
for n in findall(find(t, 'nets'), 'net'):
    got[find(n, 'name')[1].lstrip('/')] = sorted((find(x, 'ref')[1], find(x, 'pin')[1])
                                     for x in findall(n, 'node'))
parts, _ = design.build()
exp = {}
for p in parts:
    for pin, net in p['pins'].items():
        if net:
            exp.setdefault(net, []).append((p['ref'], pin))
bad = [k for k, v in exp.items() if sorted(v) != got.get(k)]
extra = [k for k, v in got.items() if k not in exp and len(v) > 1]
print('nets expected %d, mismatched %s, unexpected multi-pin nets %s' % (len(exp), bad, extra))
sys.exit(1 if bad or extra else 0)
