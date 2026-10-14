#!/usr/bin/env python3
"""Inspect downloaded candidate bass recordings: format/level/spectrum."""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

for p in sorted(Path(sys.argv[1]).glob("*.ogg")):
    x, sr = sf.read(str(p), always_2d=True)
    mono = x.mean(axis=1)
    peak = float(np.abs(mono).max())
    rms = float(np.sqrt((mono ** 2).mean()))
    # crude spectral tilt in dB per octave-ish: energy below/above 1 kHz
    sp = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
    fr = np.fft.rfftfreq(len(mono), 1 / sr)
    lo = sp[fr < 1000].sum()
    hi = sp[fr >= 1000].sum()
    print(f"{p.name:14s} sr={sr} ch={x.shape[1]} {len(mono)/sr:6.2f}s "
          f"peak={peak:5.3f} rms={rms:5.3f} dBFS={20*np.log10(rms+1e-12):6.1f} "
          f"lo/hi={lo/max(hi,1e-9):6.2f}")
    # level over time in 1 s windows (see structure / silence)
    w = sr
    env = [round(float(np.sqrt((mono[i:i+w] ** 2).mean())), 3)
           for i in range(0, len(mono) - w, w)]
    print("  1s rms:", env[:40])
