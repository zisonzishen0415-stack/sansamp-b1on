#!/usr/bin/env python3
"""Coarse ASCII map of the reference image to understand its layout."""
import sys

from PIL import Image

img = Image.open(sys.argv[1]).convert("RGB")
W, H = img.size
px = img.load()
STEP = 16


def cls(c):
    r, g, b = c
    mx, mn = max(c), min(c)
    if mx < 60:
        return "#"          # black
    if mx < 120 and mx - mn < 30:
        return "+"          # dark grey
    if r > 200 and g < 90:
        return "R"          # red
    if r > 110 and g < 70:
        return "d"          # dark red
    if r > 200 and 110 <= g <= 208 and b > 140:
        return "p"          # pink
    if r > 200 and g > 208:
        return "s"          # skin / near white
    if mn > 205:
        return "."          # pale blue canvas
    return "?"              # grid line / AA grey


print(f"{W}x{H} step {STEP}")
for y in range(0, H, STEP):
    row = []
    for x in range(0, W, STEP):
        from collections import Counter
        cnt = Counter(cls(px[min(W - 1, x + dx), min(H - 1, y + dy)])
                      for dy in range(0, STEP, 4) for dx in range(0, STEP, 4))
        row.append(cnt.most_common(1)[0][0])
    print(f"{y:4d} " + "".join(row))
