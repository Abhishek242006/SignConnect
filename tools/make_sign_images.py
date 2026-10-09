"""Generate an illustration (SVG) of every sign in the vocabulary -> static/signs/<slug>.svg

Run:  python tools/make_sign_images.py
The drawings are stylised illustrations of the project-defined gestures
(right hand, palm facing the viewer). Replace any file with a real photo of the same name
(e.g. static/signs/hello.svg -> keep the .svg name, or edit templates to use .jpg).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signconnect.vocabulary import SIGNS  # noqa: E402

SKIN, EDGE, BG = "#f3c9a5", "#7a4b2a", "#eef2fb"
BASES = {"index": (78, 135), "middle": (101, 129), "ring": (124, 134), "pinky": (145, 147)}
LENGTH = {"index": 80, "middle": 88, "ring": 80, "pinky": 64}
THUMB_BASE, THUMB_LEN = (64, 182), 68
SPREAD = {"index": -12, "middle": 0, "ring": 12, "pinky": 22}
TOGETHER = {"index": -2, "middle": 0, "ring": 2, "pinky": 4}


def tip(base, angle, length):
    a = math.radians(angle)
    return (base[0] + length * math.sin(a), base[1] - length * math.cos(a))


def limb(points, parts, width=21, detail=False):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    for w, c, o in ((width + 6, EDGE, 1), (width, SKIN, 1), (width * 0.38, "#fcebdc", 0.85)):
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-opacity="{o}" stroke-width="{w}" '
                     f'stroke-linecap="round" stroke-linejoin="round"/>')
    if detail:  # fingernail at the tip + two knuckle creases on straight fingers
        (x0, y0), (x1, y1) = points[-2], points[-1]
        d = math.hypot(x1 - x0, y1 - y0) or 1
        ux, uy = (x1 - x0) / d, (y1 - y0) / d
        ang = math.degrees(math.atan2(ux, -uy))
        cx, cy = x1 - ux * 9, y1 - uy * 9
        parts.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="6" ry="8" transform="rotate({ang:.1f} {cx:.1f} {cy:.1f})" '
                     f'fill="#fff1e8" stroke="#c99a7a" stroke-width="1.2"/>')
        if len(points) == 2:
            for t in (0.4, 0.68):
                px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                parts.append(f'<line x1="{px - uy * 7:.1f}" y1="{py + ux * 7:.1f}" x2="{px + uy * 7:.1f}" y2="{py - ux * 7:.1f}" '
                             f'stroke="#c99a7a" stroke-width="1.6" stroke-linecap="round"/>')


def hand(fingers, thumb, spread=True, rotate=0):
    """fingers: dict finger -> 'ext' | 'curl' | ('pinch', (x, y)); thumb: ('ext', angle) | 'across' | 'tuck' | ('pinch', (x, y))"""
    ang = SPREAD if spread else TOGETHER
    p = []
    p.append(f'<rect x="60" y="128" width="96" height="84" rx="30" fill="{EDGE}"/>')
    p.append(f'<rect x="84" y="196" width="48" height="50" rx="8" fill="{EDGE}"/>')
    p.append(f'<rect x="66" y="134" width="84" height="72" rx="26" fill="{SKIN}"/>')
    p.append(f'<rect x="90" y="200" width="36" height="46" rx="6" fill="{SKIN}"/>')
    for f in ("index", "middle", "ring", "pinky"):          # curled first, so extended ones overlap
        s, b = fingers[f], BASES[f]
        if s == "curl":
            limb([b, (b[0], b[1] + 24)], p, 20)
    for f in ("index", "middle", "ring", "pinky"):
        s, b = fingers[f], BASES[f]
        if s == "ext":
            limb([b, tip(b, ang[f], LENGTH[f])], p, detail=True)
        elif isinstance(s, tuple):
            limb([b, (b[0] - 10, b[1] - 38), s[1]], p)
    tb = THUMB_BASE
    if isinstance(thumb, tuple) and thumb[0] == "ext":
        limb([tb, tip(tb, thumb[1], THUMB_LEN)], p, 22, detail=True)
    elif isinstance(thumb, tuple):
        limb([tb, (56, 150), thumb[1]], p, 22)
    elif thumb == "across":
        limb([tb, (92, 176), (130, 170)], p, 22)
    else:  # tuck
        limb([tb, (84, 178)], p, 22)
    body = "".join(p)
    return f'<g transform="translate(110 150) scale(0.72) rotate({rotate} 108 170) translate(-108 -170)">{body}</g>'


E, C = "ext", "curl"
ALL_EXT = {"index": E, "middle": E, "ring": E, "pinky": E}
FIST = {"index": C, "middle": C, "ring": C, "pinky": C}
PINCH = (70, 122)

SPECS = {
    "hello": hand(ALL_EXT, ("ext", -58)),
    "thank-you": hand(ALL_EXT, ("ext", -35), spread=False, rotate=32),
    "yes": hand(FIST, "across"),
    "no": hand({"index": E, "middle": E, "ring": C, "pinky": C}, ("pinch", (82, 112)), spread=False),
    "help": hand(FIST, ("ext", -3)),
    "please": hand(ALL_EXT, "tuck", spread=False),
    "stop": hand(ALL_EXT, "tuck", spread=False, rotate=90),
    "good": hand({"index": ("pinch", PINCH), "middle": E, "ring": E, "pinky": E}, ("pinch", PINCH)),
    "bad": hand(FIST, ("ext", -3), rotate=180),
    "water": hand({"index": E, "middle": E, "ring": E, "pinky": C}, "across"),
    "food": hand({f: ("pinch", (100, 92)) for f in ("index", "middle", "ring", "pinky")}, ("pinch", (96, 96))),
    "emergency": hand({"index": E, "middle": C, "ring": C, "pinky": E}, "across"),
    "doctor": hand({"index": E, "middle": E, "ring": C, "pinky": C}, ("ext", -58)),
    "call": hand({"index": C, "middle": C, "ring": C, "pinky": E}, ("ext", -75)),
    "sorry": hand({"index": C, "middle": C, "ring": C, "pinky": E}, "across"),
    "i": hand({"index": E, "middle": C, "ring": C, "pinky": C}, "across"),
    "you": hand({"index": E, "middle": C, "ring": C, "pinky": C}, "across", rotate=90),
}


def main():
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "signs")
    os.makedirs(out, exist_ok=True)
    for s in SIGNS:
        art = SPECS[s["slug"]]
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 260" role="img" '
               f'aria-label="Hand shape for the sign {s["word"]}"><rect width="220" height="260" rx="18" fill="{BG}"/>{art}</svg>')
        with open(os.path.join(out, s["slug"] + ".svg"), "w") as f:
            f.write(svg)
    print("Wrote", len(SIGNS), "images to", out)


if __name__ == "__main__":
    main()
