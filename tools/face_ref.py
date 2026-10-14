#!/usr/bin/env python3
"""Fine class map of the reference sprite (8 px steps) to see sub-cell art."""
import sys

from PIL import Image

img = Image.open(sys.argv[1]).convert("RGB")
W, H = img.size
px = img.load()


def cls(c):
    r, g, b = c
    mx, mn = max(c), min(c)
    if c[2] > 235 and c[0] > 200:
        return "."                     # canvas
    if 90 < c[0] < 215 and abs(c[0] - c[2]) < 40:
        return ":"                     # grid line
    if mx < 60:
        return "#"                     # black
    if mx < 135 and mx - mn < 35:
        return "+"                     # dark grey
    if r > 220 and g < 90:
        return "R"                     # bright red
    if r > 110 and g < 70:
        return "d"                     # dark red
    if r > 200 and 110 <= g <= 208 and b > 140:
        return "p"                     # pink
    if r > 240 and g > 200:
        return "s"                     # skin
    return "?"


X0, X1 = int(sys.argv[2]), int(sys.argv[3])
Y0, Y1 = int(sys.argv[4]), int(sys.argv[5])
STEP = 8
print(f"x {X0}..{X1}  y {Y0}..{Y1}  step {STEP}")
hdr = "     " + "".join(str((x // 100) % 10) if x % 80 == 0 else " "
                        for x in range(X0, X1, STEP))
print(hdr)
for y in range(Y0, Y1, STEP):
    print(f"{y:4d} " + "".join(cls(px[x, y]) for x in range(X0, X1, STEP)))
