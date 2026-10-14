#!/usr/bin/env python3
"""Compare ZDL (Ziddle) wet f32 vs native x86 wet wav: gain + correlation."""
import sys
import wave

import numpy as np

zdl_f32, x86_wav = sys.argv[1], sys.argv[2]

b = open(zdl_f32, "rb").read()
z = np.frombuffer(b, dtype="<f4")
z = z[0::2]                      # left channel of the interleaved wet

with wave.open(x86_wav) as f:
    n = f.getnframes()
    x = np.frombuffer(f.readframes(n), dtype="<i2").astype(np.float64) / 32768.0
    if f.getnchannels() == 2:
        x = x[0::2]

m = min(len(z), len(x))
z, x = z[:m].astype(np.float64), x[:m]

# best gain (least squares) and correlation
g = float((z * x).sum() / max((z * z).sum(), 1e-12))
c = float(np.corrcoef(z, x)[0, 1])
print(f"samples {m}")
print(f"zdl rms {np.sqrt((z**2).mean()):.4f}   x86 rms {np.sqrt((x**2).mean()):.4f}")
print(f"best x86->zdl gain {g:.4f} ({20*np.log10(abs(g)+1e-12):.2f} dB)  corr {c:.5f}")
# after gain alignment, residual
r = z - g * x
print(f"residual rms {np.sqrt((r**2).mean()):.5f} "
      f"({20*np.log10(np.sqrt((r**2).mean())/np.sqrt((z**2).mean())+1e-12):.1f} dB rel)")
