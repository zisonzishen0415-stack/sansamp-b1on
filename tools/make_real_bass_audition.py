#!/usr/bin/env python3
"""Prepare the real bass DI excerpt used for the A/B auditions.

Source: "EMG - Seymour Duncan -bass guitar sound sample.ogg" from Wikimedia
Commons (uploader User:ZngZng, CC BY-SA 4.0) -- a pickup-comparison
recording; the two channels are near-identical (corr 0.989), i.e. a straight
DI capture.  Take 1 (the EMG P-X pass, 0..11.5 s) is trimmed, faded and
peak-normalised.  Outputs (both gitignored):
  out/bass_real.f32      mono f32 44.1k, for the Ziddle ZDL runner
  out/bass_real_dry.wav  16-bit WAV dry reference for listening
"""
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "references" / "bass_src" / "emg_sd.ogg"
OUT = ROOT / "out"
SR = 44100

x, sr = sf.read(str(SRC), always_2d=True)
mono = x.mean(axis=1)
if sr != SR:
    from scipy.signal import resample_poly
    from math import gcd
    g = gcd(int(sr), SR)
    mono = resample_poly(mono, SR // g, int(sr) // g)
    sr = SR

# take 1: 0 .. 11.4 s (the file goes silent at 11.5 s)
seg = mono[: int(11.4 * sr)]

# 20 ms fade-in, 150 ms fade-out
fi = int(0.02 * sr)
fo = int(0.15 * sr)
seg[:fi] *= np.linspace(0, 1, fi)
seg[-fo:] *= np.linspace(1, 0, fo)

peak = float(np.abs(seg).max())
seg = seg / peak * 0.70
rms = float(np.sqrt((seg ** 2).mean()))

OUT.mkdir(exist_ok=True)
(OUT / "bass_real.f32").write_bytes(seg.astype("<f4").tobytes())
w16 = (np.clip(seg, -1, 1) * 32767).astype("<i2")
sf.write(str(OUT / "bass_real_dry.wav"), w16, sr, subtype="PCM_16")
print(f"bass_real: {len(seg)/sr:.2f}s  src peak {peak:.3f} -> 0.70  "
      f"rms {20*np.log10(rms+1e-12):.1f} dBFS")
