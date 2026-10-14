#!/usr/bin/env python3
"""Locate axis label clusters in the plot margins to fix the axis mapping."""
import sys

import numpy as np
from PIL import Image

a = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(int)
H, W = a.shape[:2]
dark = a.sum(axis=2) < 300

# x labels: bottom strip below the frame
strip = dark[H - 20:, :]
colsum = strip.sum(axis=0)
clusters, cur = [], None
for x in range(W):
    if colsum[x] > 0:
        if cur is None:
            cur = [x, x]
        else:
            cur[1] = x
    else:
        if cur is not None and cur[1] - cur[0] > 4:
            clusters.append(cur)
        cur = None
if cur:
    clusters.append(cur)
print("bottom text x-clusters:", [(c[0], c[1], (c[0] + c[1]) // 2) for c in clusters])

# y labels: left strip
strip2 = dark[:, :40]
rowsum = strip2.sum(axis=1)
clusters2, cur = [], None
for y in range(H):
    if rowsum[y] > 0:
        if cur is None:
            cur = [y, y]
        else:
            cur[1] = y
    else:
        if cur is not None and cur[1] - cur[0] > 2:
            clusters2.append(cur)
        cur = None
if cur:
    clusters2.append(cur)
print("left text y-clusters:", [(c[0], c[1], (c[0] + c[1]) // 2) for c in clusters2])
