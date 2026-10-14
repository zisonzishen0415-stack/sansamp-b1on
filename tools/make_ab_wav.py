#!/usr/bin/env python3
"""Splice dry + wet f32 renders into one A/B WAV: [dry][0.6s gap][wet].

usage: python make_ab_wav.py dry.f32 wet.f32 out.wav [wet_layout]
  wet_layout: "stereo" (default; zdlrun --out-wet interleaved L,R -> take L)
              "mono"   (plain single-channel f32)
16-bit stereo, 44100 Hz. ASCII only.
"""
import struct
import sys
import wave
from pathlib import Path


def readf(p, stereo=False):
    b = Path(p).read_bytes()
    xs = [struct.unpack_from("<f", b, i * 4)[0] for i in range(len(b) // 4)]
    if stereo:
        xs = xs[0::2]          # left channel of the interleaved pair
    return xs


dry, wet, out = sys.argv[1], sys.argv[2], sys.argv[3]
layout = sys.argv[4] if len(sys.argv) > 4 else "stereo"
d = readf(dry, stereo=False)
w = readf(wet, stereo=(layout == "stereo"))
gap = [0.0] * int(0.6 * 44100)

# avoid clipping across the whole file
peak = max((abs(v) for v in d + w if v == v), default=1.0)
scale = 0.891 / peak if peak > 0.891 else 1.0

frames = []
for v in d + gap + w:
    if v != v:
        v = 0.0
    s = int(max(-1.0, min(1.0, v * scale)) * 32767.0)
    frames.append(struct.pack("<hh", s, s))

with wave.open(out, "wb") as f:
    f.setnchannels(2)
    f.setsampwidth(2)
    f.setframerate(44100)
    f.writeframes(b"".join(frames))
print(f"A/B written: {out}  dry {len(d)/44100.0:.1f}s + gap + wet {len(w)/44100.0:.1f}s  gain={scale:.3f}")
