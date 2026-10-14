#!/usr/bin/env python3
"""Look at fine structure of the two best candidates to choose an excerpt."""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

d = Path(sys.argv[1])

for name in ("emg_sd.ogg", "pick.ogg"):
    x, sr = sf.read(str(d / name), always_2d=True)
    mono = x.mean(axis=1)
    # stereo correlation (a duplicated mono DI reads 1.0)
    if x.shape[1] == 2:
        c = float(np.corrcoef(x[:, 0], x[:, 1])[0, 1])
    else:
        c = 1.0
    print(f"== {name}  {len(mono)/sr:.1f}s  stereo_corr={c:.3f}")
    w = int(0.25 * sr)
    env = np.array([np.sqrt((mono[i:i + w] ** 2).mean())
                    for i in range(0, len(mono) - w, w)])
    # print a coarse envelope map: 1 char = 0.25 s, level buckets
    chars = " .:-=+*#%@"
    line = ""
    for i in range(0, min(len(env), 240)):
        v = env[i]
        b = 0 if v < 1e-4 else min(9, int(np.log10(v / 1e-4) / np.log10(1e4) * 10))
        line += chars[max(0, min(9, b))]
    print("  0..60s:", line)
    # silences (candidate take boundaries) in the first 30 s
    sil = []
    for i, v in enumerate(env[:120]):
        if v < 5e-3:
            sil.append(round(i * 0.25, 2))
    print("  quiet 0.25s slots (first 30 s):", sil)
