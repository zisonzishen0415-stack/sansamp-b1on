#!/usr/bin/env python3
"""Digitize a kanengomibako frequency-response plot -> (freq, dB) samples.

Auto-detects the plot frame, the 5 dB horizontal gridlines and the log-x
gridlines; extracts the pure-blue curve (V1 late) and the pure-green curve
(V1 early), and prints values at standard 1/3-octave-ish frequencies.

usage: digitize_plot.py plot.png [xminHz xmaxHz yminDB ymaxDB]
"""
import sys

import numpy as np
from PIL import Image

path = sys.argv[1]
# default: axis anchors measured from the label centres of the Ft plot
x1, f1 = float(sys.argv[2]) if len(sys.argv) > 2 else 175.0, 100.0
x2, f2 = float(sys.argv[3]) if len(sys.argv) > 3 else 522.0, 10000.0
ymin = -40.0
ymax = 10.0

im = Image.open(path).convert("RGB")
a = np.asarray(im).astype(int)
H, W = a.shape[:2]
r, g, b = a[..., 0], a[..., 1], a[..., 2]

frame = a.sum(axis=2) < 200
rows = np.where(frame.sum(axis=1) > W * 0.4)[0]
cols = np.where(frame.sum(axis=0) > H * 0.4)[0]
y_top, y_bot = int(rows.min()), int(rows.max())
x_l, x_r = int(cols.min()), int(cols.max())
print(f"frame x {x_l}..{x_r}  y {y_top}..{y_bot}  ({W}x{H})")

lvl = (abs(r - 200) < 12) & (abs(g - 200) < 12) & (abs(b - 200) < 12)
gl = np.where(lvl[:, x_l + 3:x_r - 3].sum(axis=1) > (x_r - x_l) * 0.6)[0]
gl = [int(v) for v in gl if y_top < v < y_bot]
# group
g2, groups = gl[0] if gl else 0, []
for v in gl:
    if groups and v - groups[-1][-1] <= 2:
        groups[-1].append(v)
    else:
        groups.append([v])
gy = [sum(t) / len(t) for t in groups]
print(f"h-gridlines {len(gy)}: {[round(v,1) for v in gy]}")

vgl = np.where(lvl[y_top + 3:y_bot - 3, :].sum(axis=0) > (y_bot - y_top) * 0.6)[0]
vgl = [int(v) for v in vgl if x_l < v < x_r]
g3, vg = vgl[0] if vgl else 0, []
for v in vgl:
    if vg and v - vg[-1][-1] <= 2:
        vg[-1].append(v)
    else:
        vg.append([v])
gx = [sum(t) / len(t) for t in vg]
print(f"v-gridlines {len(gx)}: {[round(v,1) for v in gx]}")


def db_of_y(y):
    return ymax - (y - y_top) * (ymax - ymin) / (y_bot - y_top)


import math
PPD = (x2 - x1) / (math.log10(f2) - math.log10(f1))   # px per decade


def x_of_f(f):
    return x1 + (math.log10(f) - math.log10(f1)) * PPD


def curve(mask):
    out = {}
    for x in range(x_l + 1, x_r):
        ys = np.where(mask[y_top + 1:y_bot, x])[0]
        if len(ys):
            out[x] = db_of_y(ys.mean() + y_top + 1)
    return out


blue = curve((b > 220) & (r < 90) & (g < 90))
green = curve((g > 220) & (r < 90) & (b < 90))
print(f"blue samples {len(blue)}  green {len(green)}")

freqs = [20, 30, 40, 50, 60, 80, 100, 150, 200, 300, 400, 500, 700, 1000,
         1500, 2000, 3000, 4000, 5000, 7000, 10000, 15000, 20000]
print(f"({x_l}px -> {10**(2+(x_l-x1)/PPD):.1f} Hz, "
      f"{x_r}px -> {10**(2+(x_r-x1)/PPD):.0f} Hz)")
print(f"{'freq':>7} {'V1late':>8} {'V1early':>8}")
for f in freqs:
    x = int(round(x_of_f(f)))
    bl = blue.get(x, float("nan"))
    gr = green.get(x, float("nan"))
    print(f"{f:7d} {bl:8.1f} {gr:8.1f}")
