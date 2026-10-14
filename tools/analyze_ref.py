#!/usr/bin/env python3
"""Find the grid: pitch + origin, from the user's reference sprite image."""
import sys
from collections import Counter

from PIL import Image

img = Image.open(sys.argv[1]).convert("RGB")
W, H = img.size
px = img.load()
print(f"size {W}x{H}")

BG = (222, 240, 243)


def is_bg(c):
    return abs(c[0] - BG[0]) < 30 and abs(c[1] - BG[1]) < 30 and abs(c[2] - BG[2]) < 30


# columns that are "grid-ish" (darker than bg, gray-blue) over a tall run
def col_profile(x, y0, y1):
    dark = 0
    for y in range(y0, y1):
        c = px[x, y]
        if not is_bg(c) and abs(c[0] - c[2]) < 40 and c[0] > 90:
            dark += 1
    return dark


n = 0
xs = []
for x in range(W):
    if col_profile(x, 20, 120) > 80:      # mostly gray down the column
        xs.append(x)

# group consecutive columns into line positions
lines = []
for x in xs:
    if lines and x - lines[-1][-1] <= 1:
        lines[-1].append(x)
    else:
        lines.append([x])
centers = [sum(g) / len(g) for g in lines]
print(f"vertical grid lines: {len(centers)}")
print("first 12:", [round(c, 1) for c in centers[:12]])
if len(centers) > 2:
    gaps = [round(centers[i + 1] - centers[i], 1) for i in range(len(centers) - 1)]
    print("gaps:", gaps[:15], "median", sorted(gaps)[len(gaps) // 2])

# sprite bbox: strongly non-bg pixels
minx, maxx, miny, maxy = W, 0, H, 0
for y in range(H):
    for x in range(W):
        c = px[x, y]
        if not is_bg(c) and not (abs(c[0] - c[2]) < 40 and c[0] > 90):
            if x < minx: minx = x
            if x > maxx: maxx = x
            if y < miny: miny = y
            if y > maxy: maxy = y
print(f"sprite bbox px: x {minx}..{maxx}  y {miny}..{maxy}  "
      f"({maxx - minx + 1} x {maxy - miny + 1})")
