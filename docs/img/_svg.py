"""Tiny SVG helpers shared by the docs/img/make_*.py diagram generators."""

from __future__ import annotations

from pathlib import Path

INK, MUTED, ACCENT = "#1F2933", "#5F6B78", "#C2410C"
WIRE = {
    "3v3": "#D64545", "gnd": "#222222", "sck": "#2F80ED", "mosi": "#27AE60",
    "miso": "#9B51E0", "cs": "#E2A400", "drdy": "#EB5757", "sig": "#00897B",
    "ref": "#8D6E63", "cell": "#7A8796",
}
BUS = [("3V3", "3v3"), ("GND", "gnd"), ("SCLK", "sck"), ("MOSI", "mosi"), ("MISO", "miso")]
FONT = "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif"


class Svg:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
                    f'height="{h}" font-family="{FONT}">', f'<rect width="{w}" height="{h}" fill="#FFFFFF"/>']

    def add(self, s: str):
        self.out.append(s)

    def text(self, x, y, s, size=13, fill=INK, weight=400, anchor="start"):
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
                 f'text-anchor="{anchor}">{s}</text>')

    def rect(self, x, y, w, h, fill, stroke, rx=6, sw=1.5, dash=""):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{extra}/>')

    def line(self, pts, color, width=2.4, dash=""):
        d = " L".join(f"{x},{y}" for x, y in pts)
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="M{d}" fill="none" stroke="{color}" stroke-width="{width}" '
                 f'stroke-linejoin="round" stroke-linecap="round"{extra}/>')

    def dot(self, x, y, color, r=3.6):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')

    def pin(self, x, y, label, side, color=INK, size=13):
        """side 'r': label left of the pin (pin on a right edge); 'l': label right of it."""
        self.add(f'<circle cx="{x}" cy="{y}" r="5" fill="#FFFFFF" stroke="{color}" stroke-width="2"/>')
        if side == "r":
            self.text(x - 12, y + 4, label, size, color, 700, "end")
        else:
            self.text(x + 12, y + 4, label, size, color, 700)

    def flag_3v3(self, x, y, label="3V3"):
        self.line([(x, y), (x, y - 22)], WIRE["3v3"])
        self.add(f'<path d="M{x - 11},{y - 22} L{x + 11},{y - 22} L{x},{y - 36} Z" fill="{WIRE["3v3"]}"/>')
        self.text(x, y - 42, label, 12, WIRE["3v3"], 700, "middle")

    def ground(self, x, y):
        self.line([(x, y), (x, y + 18)], WIRE["gnd"])
        for i, w in enumerate((14, 9, 4)):
            self.line([(x - w, y + 18 + i * 5), (x + w, y + 18 + i * 5)], WIRE["gnd"], 2.2)

    def resistor_v(self, x, y, label):
        self.rect(x - 9, y - 26, 18, 52, "#FFF6E5", "#B7791F", 4)
        for i, c in enumerate(["#8B4513", "#222222", "#D64545", "#C9A227"]):
            self.add(f'<rect x="{x - 9}" y="{y - 18 + i * 10}" width="18" height="4" fill="{c}"/>')
        self.text(x + 16, y + 4, label, 13, INK, 600)

    def resistor_h(self, x, y, label):
        self.rect(x - 26, y - 9, 52, 18, "#FFF6E5", "#B7791F", 4)
        for i, c in enumerate(["#8B4513", "#222222", "#D64545", "#C9A227"]):
            self.add(f'<rect x="{x - 18 + i * 10}" y="{y - 9}" width="4" height="18" fill="{c}"/>')
        self.text(x, y + 26, label, 13, INK, 600, "middle")

    def step_title(self, n: int, title: str, subtitle: str):
        self.add(f'<circle cx="58" cy="44" r="18" fill="{INK}"/>')
        self.text(58, 50, str(n), 18, "#FFFFFF", 700, "middle")
        self.text(88, 52, title, 24, INK, 700)
        self.text(40, 88, subtitle, 14, MUTED)

    def legend(self, x, y, items, cols=5, col_w=150):
        for i, (label, key) in enumerate(items):
            cx = x + (i % cols) * col_w
            cy = y + (i // cols) * 22
            self.line([(cx, cy - 4), (cx + 26, cy - 4)], WIRE[key], 3)
            self.text(cx + 34, cy, label, 12)

    def save(self, path: Path):
        path.write_text("\n".join(self.out + ["</svg>"]), encoding="utf-8")
        print(f"wrote {path}")
