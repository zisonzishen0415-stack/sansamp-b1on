#!/usr/bin/env python3
"""Digitize the top/bottom envelope of the blue curve family in a panel of
the kanengomibako plots (presence / drive / bass / treble families).

usage: digitize_envelope.py plot.png x1 f1 x2 f2 ymin ymax
"""
import math
import sys

import numpy as np
from PIL import Image

path = sys.argv[1]
x1, f1, x2, f2 = (float(sys.argv[2]), float(sys.argv[3]),
                  float(sys.argv[4]), float(sys.argv[5]))
ymin, ymax = float(sys.argv[6]), float(sys.argv[7])

a = np.asarray(Image.open(path).convert("RGB")).astype(int)
H, W = a.shape[:2]
r, g, b = a[..., 0], a[..., 1], a[..., 2]
blue = (b > 220) & (r < 90) & (g < 90)
green = (g > 220) & (r < 90) & (b < 90)

frame = a.sum(axis=2) < 200
rows = np.where(frame.sum(axis=1) > W * 0.4)[0]
y_top, y_bot = int(rows.min()), int(rows.max())
PPD = (x2 - x1) / (math.log10(f2 / f1))


def db(y):
    return ymax - (y - y_top) * (ymax - ymin) / (y_bot - y_top)


def xf(f):
    return int(round(x1 + math.log10(f / f1) * PPD))


freqs = [30, 50, 80, 100, 150, 200, 300, 500, 700, 1000, 1500, 2000, 3000,
         4000, 5000, 7000, 10000]
print(f"frame y {y_top}..{y_bot} -> {ymax}..{ymin} dB")
print(f"{'freq':>7} {'blue_top':>9} {'blue_bot':>9} {'grn_top':>9} {'grn_bot':>9}")
for f in freqs:
    x = xf(f)
    if not (0 <= x < W):
        continue
    col_b = np.where(blue[y_top + 1:y_bot, x])[0]
    col_g = np.where(green[y_top + 1:y_bot, x])[0]
    bt = db(col_b.min() + y_top + 1) if len(col_b) else float("nan")
    bb = db(col_b.max() + y_top + 1) if len(col_b) else float("nan")
    gt = db(col_g.min() + y_top + 1) if len(col_g) else float("nan")
    gb = db(col_g.max() + y_top + 1) if len(col_g) else float("nan")
    print(f"{f:7d} {bt:9.1f} {bb:9.1f} {gt:9.1f} {gb:9.1f}")
