"""Generates the original still-life illustrations used by the demo catalogues.

Run:  python scripts/make_demo_art.py
Writes SVGs into frontend/public/demo/. Flat shapes, a soft table line and a
paper-grain filter; each object is drawn from simple geometry, no traced images.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "demo"

PALETTES = {
    "stationery": dict(bg="#E7E3D3", table="#D6D0BC", ink="#1F2A1C", a="#3F6212", b="#F3EFE2",
                       c="#B9A27A", d="#7C8F5A"),
    "ceramics": dict(bg="#E4E1DA", table="#CFC9BD", ink="#22201C", a="#1F5F5B", b="#EFE8DA",
                     c="#8C6A4F", d="#B9B2A3"),
    "apothecary": dict(bg="#E9E1DD", table="#D5C9C3", ink="#231C22", a="#6B2C5C", b="#F4EEE8",
                       c="#B2722E", d="#9BA383"),
    "neutral": dict(bg="#E6E2DA", table="#D2CCC0", ink="#22201C", a="#5B5A55", b="#F2EEE6",
                    c="#A88B62", d="#B8B2A6"),
}


def frame(body: str, p: dict, title: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" role="img" aria-label="{title}">
<title>{title}</title>
<defs>
<filter id="grain" x="0" y="0" width="100%" height="100%">
<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="4"/>
<feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.09 0"/>
</filter>
</defs>
<rect width="800" height="800" fill="{p['bg']}"/>
<rect y="560" width="800" height="240" fill="{p['table']}"/>
{body}
<rect width="800" height="800" filter="url(#grain)"/>
</svg>"""


def shadow(cx, cy, rx, ry=None):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry or rx * 0.12}" fill="#000" opacity="0.12"/>'


def speckles(rng, x0, y0, w, h, color, n=60, r=(1.5, 3.5)):
    out = []
    for _ in range(n):
        out.append(f'<circle cx="{x0 + rng.random() * w:.1f}" cy="{y0 + rng.random() * h:.1f}" '
                   f'r="{rng.uniform(*r):.1f}" fill="{color}" opacity="0.55"/>')
    return "".join(out)


def frond(x, y, length, angle, color, width=3):
    """A simple fern frond: a curved stem with paired leaflets shrinking to the tip."""
    parts = []
    a = math.radians(angle)
    pts = []
    for i in range(14):
        t = i / 13
        bend = math.sin(t * math.pi) * 18
        px = x + math.cos(a) * length * t - math.sin(a) * bend
        py = y + math.sin(a) * length * t + math.cos(a) * bend
        pts.append((px, py))
    d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts)
    parts.append(f'<path d="{d}" stroke="{color}" stroke-width="{width}" fill="none" stroke-linecap="round"/>')
    for i, (px, py) in enumerate(pts[1:-1], start=1):
        size = 34 * (1 - i / 14) + 6
        for side in (-1, 1):
            la = a + side * math.radians(62)
            ex, ey = px + math.cos(la) * size, py + math.sin(la) * size
            parts.append(f'<path d="M {px:.1f} {py:.1f} Q {(px + ex) / 2 + side * 4:.1f} '
                         f'{(py + ey) / 2 - 6:.1f} {ex:.1f} {ey:.1f}" stroke="{color}" '
                         f'stroke-width="{width + 5}" stroke-linecap="round" fill="none"/>')
    return "".join(parts)


# --- objects ----------------------------------------------------------------------
def cards(p, rng):
    out = [shadow(400, 600, 250)]
    for i, (dx, rot) in enumerate([(-60, -8), (30, 5), (-10, -1)]):
        out.append(f'<g transform="rotate({rot} 400 420)"><rect x="{230 + dx}" y="250" width="340" '
                   f'height="330" fill="{p["b"]}" stroke="{p["table"]}" stroke-width="2"/></g>')
    out.append(f'<rect x="250" y="268" width="300" height="290" fill="#FFFFFF" opacity="0.35"/>')
    out.append(frond(330, 520, 230, -70, p["a"]))
    return "".join(out)


def tags(p, rng):
    out = [shadow(400, 600, 260)]
    for i, (x, y, rot) in enumerate([(220, 260, -12), (370, 230, 6), (300, 330, -2)]):
        g = (f'<path d="M {x} {y + 40} L {x + 40} {y} L {x + 200} {y} L {x + 200} {y + 260} '
             f'L {x + 40} {y + 260} L {x} {y + 220} Z" fill="{p["b"]}" stroke="{p["c"]}" stroke-width="2"/>'
             f'<circle cx="{x + 40}" cy="{y + 130}" r="12" fill="{p["bg"]}" stroke="{p["c"]}" stroke-width="3"/>'
             + speckles(rng, x + 60, y + 20, 130, 220, p["d"], 45, (2, 4.5))
             + f'<path d="M {x + 40} {y + 130} C {x - 60} {y + 120}, {x - 40} {y + 300}, {x - 120} {y + 330}" '
               f'stroke="{p["c"]}" stroke-width="4" fill="none"/>')
        out.append(f'<g transform="rotate({rot} {x + 100} {y + 130})">{g}</g>')
    return "".join(out)


def envelopes(p, rng):
    out = [shadow(400, 600, 280)]
    for i, rot in enumerate([-16, -6, 4, 14]):
        out.append(f'<g transform="rotate({rot} 400 600)"><rect x="200" y="290" width="400" height="270" '
                   f'fill="{p["b"]}" stroke="{p["c"]}" stroke-width="2"/>'
                   f'<path d="M 200 290 L 400 420 L 600 290" fill="none" stroke="{p["c"]}" stroke-width="2"/></g>')
    return "".join(out)


def notebook(p, rng):
    out = [shadow(400, 595, 200)]
    out.append(f'<rect x="240" y="200" width="320" height="390" fill="{p["a"]}"/>')
    for i in range(3):
        out.append(frond(300 + i * 90, 560, 300, -84 + i * 4, p["b"], 2))
    out.append(f'<rect x="240" y="200" width="24" height="390" fill="{p["ink"]}" opacity="0.25"/>')
    for y in range(225, 575, 28):
        out.append(f'<line x1="252" y1="{y}" x2="252" y2="{y + 14}" stroke="{p["b"]}" stroke-width="3"/>')
    return "".join(out)


def label_pad(p, rng):
    out = [shadow(380, 598, 220)]
    out.append(f'<rect x="200" y="250" width="360" height="330" fill="{p["b"]}" stroke="{p["c"]}" stroke-width="2"/>')
    out.append(f'<rect x="200" y="250" width="360" height="22" fill="{p["c"]}" opacity="0.6"/>')
    out.append(f'<rect x="236" y="300" width="288" height="240" fill="none" stroke="{p["ink"]}" stroke-width="2"/>')
    for i, y in enumerate((360, 410, 460, 510)):
        out.append(f'<line x1="256" y1="{y}" x2="504" y2="{y}" stroke="{p["ink"]}" stroke-width="1.5" opacity="0.6"/>')
    out.append(f'<g transform="rotate(-28 560 470)"><rect x="440" y="455" width="300" height="22" fill="{p["c"]}"/>'
               f'<path d="M 740 455 L 780 466 L 740 477 Z" fill="{p["ink"]}"/></g>')
    return "".join(out)


def wrap(p, rng):
    out = [shadow(400, 600, 270)]
    out.append(f'<path d="M 160 330 L 600 270 L 650 560 L 190 580 Z" fill="{p["b"]}" stroke="{p["c"]}" stroke-width="2"/>')
    out.append(f'<path d="M 600 270 L 520 380 L 650 560" fill="{p["bg"]}" opacity="0.5"/>')
    for i, (x, y, a) in enumerate([(240, 540, -75), (350, 520, -95), (450, 545, -70)]):
        out.append(frond(x, y, 180, a, p["a"], 2))
    return "".join(out)


def mug(p, rng):
    out = [shadow(400, 590, 170)]
    out.append(f'<path d="M 520 360 C 640 360, 640 500, 520 500" stroke="{p["b"]}" stroke-width="34" fill="none"/>')
    out.append(f'<path d="M 270 300 L 270 560 Q 400 600 530 560 L 530 300 Z" fill="{p["b"]}"/>')
    out.append(speckles(rng, 280, 320, 240, 240, p["c"], 90, (1.5, 3)))
    out.append(f'<ellipse cx="400" cy="300" rx="130" ry="26" fill="{p["c"]}"/>')
    out.append(f'<ellipse cx="400" cy="304" rx="116" ry="18" fill="{p["ink"]}" opacity="0.55"/>')
    return "".join(out)


def bowls(p, rng):
    out = [shadow(400, 588, 250)]
    for w, top, col in [(250, 360, p["d"]), (190, 400, p["b"]), (130, 440, p["a"])]:
        out.append(f'<path d="M {400 - w} {top} Q {400 - w} 580 400 580 Q {400 + w} 580 {400 + w} {top} Z" fill="{col}"/>')
        out.append(f'<ellipse cx="400" cy="{top}" rx="{w}" ry="{w * 0.16}" fill="{p["ink"]}" opacity="0.18"/>')
    return "".join(out)


def cone(p, rng):
    out = [shadow(400, 592, 160)]
    out.append(f'<path d="M 300 460 L 300 570 Q 400 600 500 570 L 500 460 Z" fill="{p["b"]}"/>')
    out.append(f'<path d="M 250 230 L 550 230 L 450 450 L 350 450 Z" fill="{p["a"]}"/>')
    for x in range(290, 520, 40):
        out.append(f'<line x1="{x}" y1="245" x2="{400 + (x - 400) * 0.45:.0f}" y2="440" stroke="{p["b"]}" stroke-width="3" opacity="0.4"/>')
    out.append(f'<rect x="300" y="450" width="200" height="16" fill="{p["ink"]}" opacity="0.7"/>')
    out.append(f'<ellipse cx="400" cy="230" rx="150" ry="20" fill="{p["ink"]}" opacity="0.45"/>')
    return "".join(out)


def vase(p, rng):
    out = [shadow(400, 588, 130)]
    out.append(f'<path d="M 400 330 C 380 230, 360 160, 300 110" stroke="{p["c"]}" stroke-width="5" fill="none"/>')
    for i in range(6):
        out.append(f'<ellipse cx="{300 + i * 9}" cy="{112 + i * 18}" rx="14" ry="6" fill="{p["c"]}" transform="rotate(-30 {300 + i * 9} {112 + i * 18})"/>')
    out.append(f'<path d="M 375 330 L 375 380 C 260 400, 260 580, 400 585 C 540 580, 540 400, 425 380 L 425 330 Z" fill="{p["d"]}"/>')
    out.append(f'<path d="M 300 430 C 340 470, 330 520, 380 560" stroke="{p["b"]}" stroke-width="10" opacity="0.5" fill="none"/>')
    return "".join(out)


def plate(p, rng):
    out = [shadow(400, 560, 300, 50)]
    out.append(f'<ellipse cx="400" cy="480" rx="300" ry="90" fill="{p["b"]}"/>')
    out.append(f'<ellipse cx="400" cy="480" rx="190" ry="54" fill="{p["bg"]}" opacity="0.6"/>')
    out.append(f'<ellipse cx="400" cy="490" rx="300" ry="90" fill="none" stroke="{p["d"]}" stroke-width="3"/>')
    return "".join(out)


def spoon_rest(p, rng):
    out = [shadow(400, 560, 220, 40)]
    out.append(f'<ellipse cx="400" cy="500" rx="220" ry="70" fill="{p["a"]}"/>')
    out.append(f'<ellipse cx="400" cy="492" rx="180" ry="48" fill="{p["ink"]}" opacity="0.25"/>')
    out.append(f'<g transform="rotate(-14 400 470)"><ellipse cx="300" cy="470" rx="70" ry="34" fill="{p["c"]}"/>'
               f'<rect x="360" y="460" width="340" height="20" rx="10" fill="{p["c"]}"/></g>')
    return "".join(out)


def candle(p, rng):
    out = [shadow(400, 592, 150)]
    out.append(f'<path d="M 400 248 C 386 225, 392 205, 400 190 C 408 205, 414 225, 400 248 Z" fill="{p["c"]}"/>')
    out.append(f'<line x1="400" y1="250" x2="400" y2="290" stroke="{p["ink"]}" stroke-width="4"/>')
    out.append(f'<rect x="280" y="280" width="240" height="300" fill="{p["c"]}" opacity="0.85"/>')
    out.append(f'<rect x="280" y="280" width="240" height="40" fill="{p["b"]}"/>')
    out.append(f'<rect x="320" y="390" width="160" height="110" fill="{p["b"]}"/>')
    out.append(f'<line x1="345" y1="430" x2="455" y2="430" stroke="{p["a"]}" stroke-width="5"/>')
    out.append(f'<line x1="360" y1="455" x2="440" y2="455" stroke="{p["ink"]}" stroke-width="2"/>')
    return "".join(out)


def balm(p, rng):
    out = [shadow(380, 590, 190)]
    out.append(f'<g transform="rotate(-12 560 420)"><ellipse cx="560" cy="440" rx="130" ry="130" fill="{p["d"]}"/>'
               f'<ellipse cx="560" cy="440" rx="96" ry="96" fill="none" stroke="{p["b"]}" stroke-width="4"/></g>')
    out.append(f'<path d="M 220 470 L 220 550 Q 340 600 460 550 L 460 470 Z" fill="{p["d"]}"/>')
    out.append(f'<ellipse cx="340" cy="470" rx="120" ry="34" fill="{p["b"]}"/>')
    out.append(f'<path d="M 270 470 Q 330 450 400 470" stroke="{p["c"]}" stroke-width="6" fill="none" opacity="0.5"/>')
    return "".join(out)


def bottle(p, rng):
    out = [shadow(400, 592, 110)]
    out.append(f'<rect x="378" y="150" width="44" height="60" fill="{p["c"]}"/>')
    out.append(f'<path d="M 382 210 L 382 260 C 330 280, 320 300, 320 340 L 320 580 L 480 580 L 480 340 C 480 300, 470 280, 418 260 L 418 210 Z" fill="{p["d"]}" opacity="0.9"/>')
    out.append(f'<rect x="340" y="400" width="120" height="120" fill="{p["b"]}"/>')
    out.append(f'<line x1="360" y1="440" x2="440" y2="440" stroke="{p["a"]}" stroke-width="5"/>')
    return "".join(out)


def matches(p, rng):
    out = [shadow(400, 592, 260)]
    out.append(f'<rect x="170" y="420" width="300" height="160" fill="{p["a"]}"/>')
    out.append(f'<rect x="170" y="420" width="300" height="20" fill="{p["c"]}"/>')
    out.append(f'<circle cx="320" cy="505" r="40" fill="none" stroke="{p["b"]}" stroke-width="4"/>')
    for i in range(5):
        a = -60 + i * 9
        out.append(f'<g transform="rotate({a} 560 560)"><rect x="556" y="250" width="8" height="310" fill="{p["c"]}"/>'
                   f'<ellipse cx="560" cy="250" rx="9" ry="14" fill="{p["ink"]}"/></g>')
    return "".join(out)


def mist(p, rng):
    out = [shadow(400, 592, 120)]
    out.append(f'<rect x="372" y="170" width="56" height="60" fill="{p["ink"]}"/>')
    out.append(f'<rect x="428" y="186" width="34" height="14" fill="{p["ink"]}"/>')
    out.append(f'<path d="M 330 230 L 470 230 L 480 580 L 320 580 Z" fill="{p["b"]}" opacity="0.92"/>')
    out.append(f'<rect x="345" y="380" width="110" height="130" fill="{p["d"]}"/>')
    for i, (x, y) in enumerate([(500, 180), (530, 170), (520, 205), (560, 190)]):
        out.append(f'<circle cx="{x}" cy="{y}" r="{4 - i * 0.6:.1f}" fill="{p["ink"]}" opacity="0.4"/>')
    return "".join(out)


def tin(p, rng):
    out = [shadow(400, 588, 200)]
    out.append(f'<path d="M 230 470 L 230 550 Q 400 600 570 550 L 570 470 Z" fill="{p["d"]}"/>')
    out.append(f'<ellipse cx="400" cy="470" rx="170" ry="44" fill="{p["b"]}"/>')
    out.append(f'<ellipse cx="400" cy="470" rx="140" ry="32" fill="{p["c"]}" opacity="0.7"/>')
    out.append(f'<line x1="400" y1="470" x2="400" y2="440" stroke="{p["ink"]}" stroke-width="4"/>')
    out.append(f'<g transform="rotate(14 600 360)"><ellipse cx="560" cy="360" rx="170" ry="44" fill="{p["a"]}"/></g>')
    return "".join(out)


def parcel(p, rng):
    out = [shadow(400, 592, 240)]
    out.append(f'<path d="M 190 330 L 400 260 L 610 330 L 610 560 L 400 600 L 190 560 Z" fill="{p["c"]}"/>')
    out.append(f'<path d="M 190 330 L 400 390 L 610 330" fill="none" stroke="{p["ink"]}" stroke-width="2" opacity="0.4"/>')
    out.append(f'<path d="M 400 390 L 400 600" stroke="{p["ink"]}" stroke-width="2" opacity="0.4"/>')
    out.append(f'<path d="M 295 295 L 505 360 L 505 580 M 505 295 L 295 360 L 295 580" stroke="{p["b"]}" stroke-width="7" fill="none"/>')
    return "".join(out)


ART = {
    "pressed-fern-cards": ("stationery", cards), "seed-paper-tags": ("stationery", tags),
    "linen-envelopes": ("stationery", envelopes), "field-notebook": ("stationery", notebook),
    "herbarium-labels": ("stationery", label_pad), "botanical-wrap": ("stationery", wrap),
    "speckled-mug": ("ceramics", mug), "nesting-bowls": ("ceramics", bowls),
    "pour-over-cone": ("ceramics", cone), "bud-vase": ("ceramics", vase),
    "serving-plate": ("ceramics", plate), "spoon-rest": ("ceramics", spoon_rest),
    "night-candle": ("apothecary", candle), "hand-balm": ("apothecary", balm),
    "bath-oil": ("apothecary", bottle), "cedar-matches": ("apothecary", matches),
    "room-mist": ("apothecary", mist), "travel-candle": ("apothecary", tin),
    "parcel": ("neutral", parcel),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, (palette, fn) in ART.items():
        rng = random.Random(slug)
        title = slug.replace("-", " ").capitalize()
        (OUT / f"{slug}.svg").write_text(frame(fn(PALETTES[palette], rng), PALETTES[palette], title))
    print(f"wrote {len(ART)} files to {OUT}")


if __name__ == "__main__":
    main()
