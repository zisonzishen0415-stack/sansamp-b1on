#!/usr/bin/env python3
"""Measure the x86 core's magnitude response via steady-state sine bursts.

Writes out/sweep_test.wav, runs the native renderer (needs /tmp/bddi_render
built in WSL), reads the result and prints dB per frequency.  Also prints
the digitized target (V1L end-to-end, PRESENCE 0 / DRIVE 0 / BLEND 100)
for a side-by-side.

usage: measure_core_response.py [p d b ba t m l mode]   (defaults match the
"presence 0 drive 0 blend 100" plot: 0 0 1 0.5 0.5 0.5 0.6 0)
"""
import struct
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
SR = 44100
FREQS = [20, 30, 40, 50, 60, 80, 100, 150, 200, 300, 400, 500, 700, 1000,
         1500, 2000, 3000, 4000, 5000, 7000, 10000, 15000]

# digitized from 09_284_06_bdv1lFt.png (V1 late), presence 0 / drive 0
TARGET = {20: -7.9, 30: -3.1, 40: -0.8, 50: 0.5, 60: 0.8, 80: 0.5,
          100: -0.4, 150: -3.8, 200: -7.3, 300: -13.5, 400: -17.8,
          500: -22.5, 700: -27.5, 1000: -12.5, 1500: -5.0, 2000: -2.0,
          3000: -0.4, 4000: -2.7, 5000: -9.3, 7000: -23.4, 10000: -38.8,
          15000: -42.0}

params = [float(v) for v in sys.argv[1:]] or [0.0, 0.0, 1.0, 0.5, 0.5, 0.5, 0.6, 0.0]

amp = 0.25
burst = int(0.45 * SR)
meas = int(0.15 * SR)
sig = []
for f in FREQS:
    t = np.arange(burst) / SR
    tone = amp * np.sin(2 * np.pi * f * t)
    sig.append(tone)
    sig.append(np.zeros(int(0.15 * SR)))
x = np.concatenate(sig)
w16 = (np.clip(x, -1, 1) * 32767).astype("<i2")
with wave.open(str(OUT / "sweep_test.wav"), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(w16.tobytes())

wav_in = "/mnt/d/" + str(OUT / "sweep_test.wav").replace("\\", "/")[3:]
wav_out = "/mnt/d/" + str(OUT / "sweep_meas.wav").replace("\\", "/")[3:]
tools = "/mnt/d/" + str(ROOT / "tools").replace("\\", "/")[3:]
core = "/mnt/d/" + str(ROOT / "core").replace("\\", "/")[3:]
bash = (f"cd {tools} && "
        f"gcc -O2 -I{core} -o /tmp/bddi_render bddi_render.c {core}/bddi.c -lm && "
        f"/tmp/bddi_render {wav_in} {wav_out} " + " ".join(str(p) for p in params))
print("running:", bash)
r = subprocess.run(["wsl.exe", "-e", "bash", "-lc", bash],
                   capture_output=True)
print(r.stdout.decode("utf-8", "replace").strip()[-200:],
      r.stderr.decode("utf-8", "replace").strip()[-200:])

with wave.open(str(OUT / "sweep_meas.wav")) as w:
    n = w.getnframes()
    ch = w.getnchannels()
    y = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float64) / 32768.0
    if ch == 2:
        y = y[0::2]                      # renderer writes stereo (duplicated)

pos = 0
print(f"{'freq':>7} {'ours':>7} {'target':>7} {'diff':>7}")
for f in FREQS:
    seg = y[pos + burst - meas: pos + burst]
    rms = np.sqrt((seg ** 2).mean())
    rel = 20 * np.log10(rms / (amp / np.sqrt(2)) + 1e-12)
    tg = TARGET.get(f, float("nan"))
    print(f"{f:7d} {rel:7.1f} {tg:7.1f} {rel - tg:7.1f}")
    pos += burst + int(0.15 * SR)
