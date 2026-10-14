#!/usr/bin/env python3
"""Extract the sprite cell grid from the user's reference image.

The reference is a ~23.5 px/cell grid-editor screenshot.  We fit the grid
from line positions found in the empty margins, classify each cell centre
(with a 5x5 vote) and print the sprite as a letter grid:

  K = black          k = dark grey    R = bright red
  D = dark red       P = pink         S = pale skin      . = empty
"""
import json
import sys
from pathlib import Path

from PIL import Image

img = Image.open(sys.argv[1]).convert("RGB")
W, H = img.size
px = img.load()


def is_canvas(c):
    return c[2] > 235 and c[0] > 200          # pale blue (222,240,243)


def is_gridline(c):
    return 90 < c[0] < 215 and abs(c[0] - c[2]) < 40


def is_sprite(c):
    r, g, b = c
    if max(c) < 60:                            # black
        return True
    if r > 110 and g < 90:                     # red / dark red
        return True
    if r > 200 and 110 <= g <= 208 and b > 140:  # pink
        return True
    if r > 240 and 200 < g < 238 and b < 235:    # skin
        return True
    if max(c) < 130 and max(c) - min(c) < 30:    # dark grey
        return True
    return False


def cls(c):
    r, g, b = c
    mx, mn = max(c), min(c)
    if is_canvas(c) or is_gridline(c):
        return "."
    if mx < 60:
        return "K"
    if mx < 135 and mx - mn < 35:
        return "k"
    if r > 220 and g < 90:
        return "R"
    if r > 110 and g < 70:
        return "D"
    if r > 200 and 110 <= g <= 208 and b > 140:
        return "P"
    if r > 240 and g > 200:
        return "S"
    return "?"


# --- fit the grid to the sprite bbox -------------------------------------
# sprite bbox in px (AA halo included; ~half a pixel each side)
minx, maxx, miny, maxy = W, 0, H, 0
for y in range(0, H):
    for x in range(0, W):
        if is_sprite(px[x, y]):
            minx, maxx = min(minx, x), max(maxx, x)
            miny, maxy = min(miny, y), max(maxy, y)
bw, bh = maxx - minx + 1, maxy - miny + 1
print(f"sprite bbox px: x {minx}..{maxx}  y {miny}..{maxy}  ({bw}x{bh})")

# the sprite is an integer number of cells: try the neighbour counts and
# pick the pitch that best matches the margin-line pitch (~23.5)
best = None
for nc in range(18, 30):
    p = bw / nc
    if best is None or abs(p - 23.5) < abs(best[1] - 23.5):
        best = (nc, p)
ncx, pitch = best
ncy = int(round(bh / pitch))
print(f"fit: {ncx} x {ncy} cells, pitch {pitch:.2f}")
ox, oy = minx, miny

def extract(ox, oy):
    grid = []
    clean = 0
    for j in range(ncy):
        row = []
        for i in range(ncx):
            cx = int(ox + (i + 0.5) * pitch)
            cy = int(oy + (j + 0.5) * pitch)
            votes = {}
            for dy in range(-6, 7, 6):
                for dx in range(-6, 7, 6):
                    c = px[min(W - 1, max(0, cx + dx)),
                           min(H - 1, max(0, cy + dy))]
                    k = cls(c)
                    votes[k] = votes.get(k, 0) + 1
            best_k = max(votes, key=lambda k: (votes[k], k != "."))
            if votes[best_k] >= 8:
                clean += 1
            row.append(best_k)
        grid.append(row)
    return grid, clean


# sub-cell alignment search: the screenshot grid can be off by half a cell
best_grid, best_clean, best_off = None, -1, (0, 0)
for ddx in range(-12, 13, 3):
    for ddy in range(-12, 13, 3):
        g, cl = extract(ox + ddx, oy + ddy)
        if cl > best_clean:
            best_grid, best_clean, best_off = g, cl, (ddx, ddy)
print(f"alignment offset {best_off}  clean cells {best_clean}/{ncx * ncy}")
grid = best_grid

print(f"grid {len(grid[0])} x {len(grid)}")
for r in grid:
    print("".join(r))
Path(sys.argv[2]).write_text(json.dumps(grid))
print(f"-> {sys.argv[2]}")
