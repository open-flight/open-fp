"""Minimal S-expression reader/writer for KiCad files (no dependencies)."""
import re

_TOK = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')


class Sym(str):
    """Bare (unquoted) atom."""


def parse(text):
    stack, cur = [], []
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOK.match(text, pos)
        if not m:
            if text[pos:].strip() == '':
                break
            raise ValueError('bad token at %d' % pos)
        pos = m.end()
        if m.group(1):
            stack.append(cur)
            cur = []
        elif m.group(2):
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif m.group(3) is not None:
            s = m.group(3)[1:-1]
            cur.append(s.replace('\\"', '"').replace('\\\\', '\\'))
        else:
            cur.append(Sym(m.group(4)))
    return cur[0] if len(cur) == 1 else cur


def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def dump(node, indent=0):
    if isinstance(node, list):
        if not node:
            return '()'
        simple = all(not isinstance(x, list) for x in node)
        if simple:
            return '(' + ' '.join(dump(x) for x in node) + ')'
        out = '(' + dump(node[0])
        for x in node[1:]:
            if isinstance(x, list):
                out += '\n' + '\t' * (indent + 1) + dump(x, indent + 1)
            else:
                out += ' ' + dump(x)
        return out + '\n' + '\t' * indent + ')'
    if isinstance(node, Sym):
        return str(node)
    if isinstance(node, bool):
        return 'yes' if node else 'no'
    if isinstance(node, (int, float)):
        return fmt(node)
    return q(node)


def fmt(v):
    if isinstance(v, int):
        return str(v)
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def find(node, key):
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def findall(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]
