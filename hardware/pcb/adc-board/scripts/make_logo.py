#!/usr/bin/env python3
"""Turn art/openflight-logo.png into a one-colour silkscreen bitmap for gen_pcb.py.

Run with any Python that has Pillow (not KiCad's), from anywhere:
  python3 hardware/pcb/adc-board/scripts/make_logo.py

Silkscreen is one colour, so the logo prints white wherever it is opaque, except its
grey parts (the shadows behind OPEN and the ball's dimples), which stay as gaps. The
output, art/openflight-logo.runs, is plain text so KiCad's Python can read it without
Pillow: a header line `pitch_mm width height`, then one line per pixel row (top first)
of `start:end` runs of set pixels.
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, '..', 'art')
WIDTH_MM = 40.0
PITCH_MM = 0.16   # one pixel is already wider than PCBWay's 0.15 mm minimum silk line


def main():
    im = Image.open(os.path.join(ART, 'openflight-logo.png')).convert('RGBA')
    mono = Image.new('L', im.size, 0)
    src, dst = im.load(), mono.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = src[x, y]
            grey = abs(r - g) < 20 and abs(g - b) < 20 and r < 170
            if a >= 128 and not grey:
                dst[x, y] = 255
    mono = mono.crop(mono.getbbox())
    w = round(WIDTH_MM / PITCH_MM)
    h = round(mono.height * w / mono.width)
    mono = mono.resize((w, h), Image.LANCZOS).point(lambda v: 255 if v >= 128 else 0)
    px = mono.load()
    lines = ['%g %d %d' % (PITCH_MM, w, h)]
    for y in range(h):
        runs, x = [], 0
        while x < w:
            if px[x, y]:
                x0 = x
                while x < w and px[x, y]:
                    x += 1
                runs.append('%d:%d' % (x0, x))
            else:
                x += 1
        lines.append(' '.join(runs))
    out = os.path.join(ART, 'openflight-logo.runs')
    with open(out, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    mono.save(os.path.join(ART, 'openflight-logo-silk.png'))
    print('wrote', out, '%d x %d px = %.1f x %.1f mm' % (w, h, w * PITCH_MM, h * PITCH_MM))


if __name__ == '__main__':
    main()
