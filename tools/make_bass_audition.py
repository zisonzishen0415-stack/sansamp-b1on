#!/usr/bin/env python3
"""Bass audition input for the BassDriver (pure stdlib Karplus-Strong).

Bass groove: root-octave eighths on E1/A1/D2/G2, a walk-up, then a
sustained low E with a fifth. ~10 s. Writes mono f32 (for zdlrun) and a
16-bit WAV (dry reference). ASCII only.
"""
import math
import random
import struct
import wave
from pathlib import Path

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "out"
OUT.mkdir(exist_ok=True)
rng = random.Random(7)

E1, A1, D2, G2, B2 = 41.20, 55.00, 73.42, 98.00, 123.47
D3, E3 = 146.83, 164.81


def ks_note(freq, dur, damp=0.9985, brightness=0.45, amp=1.0, detune=0.0):
    n = int(dur * SR)
    if n <= 0:
        return []
    out = [0.0] * n
    for f, g in ((freq, amp), (freq * (1.0 + detune), amp * 0.7)):
        N = max(2, int(round(SR / f)))
        buf = [rng.gauss(0, 1) for _ in range(N)]
        buf = [0.25 * buf[i - 1] + 0.5 * buf[i] + 0.25 * buf[(i + 1) % N] for i in range(N)]
        if brightness < 1.0:
            buf = [(buf[i - 1] + buf[i] + buf[(i + 1) % N]) / 3.0 for i in range(N)]
        m = max(abs(v) for v in buf) + 1e-9
        buf = [v / m * 0.9 for v in buf]
        for i in range(n):
            out[i] += g * buf[0]
            nxt = damp * (buf[0] + buf[1]) * 0.5
            buf.append(nxt)
            buf.pop(0)
    return out


def add_pick_noise(x, at):
    nn = int(0.012 * SR)
    if at + nn >= len(x):
        return
    prev = 0.0
    for i in range(nn):
        v = rng.gauss(0, 1)
        hp = v - prev
        prev = v
        env = math.exp(-i / (0.003 * SR))
        x[at + i] += 0.03 * hp * env


total_s = 10.0
perf = [0.0] * int(total_s * SR)


def place(seg, start):
    i0 = int(start * SR)
    end = min(len(perf), i0 + len(seg))
    for i in range(end - i0):
        perf[i0 + i] += seg[i]


t = 0.5
B = 0.42  # eighth note at ~142 bpm feel

# 1) root-octave groove: E1 E2 x3, A1 A2 x2, D2 D3 x2, G2 (octave down = G1)
groove = [E1, E1 * 2, E1, E1 * 2, E1, E1 * 2, E1, E1 * 2,
          A1, A1 * 2, A1, A1 * 2,
          D2, D2 * 2, D2, D2 * 2,
          G2, 49.00, G2, 49.00]
for f in groove:
    place(ks_note(f, 0.55, damp=0.9975, brightness=0.4, amp=0.62, detune=0.001), t)
    add_pick_noise(perf, int(t * SR))
    t += B

# 2) walk-up fill: E1 G1 A1 B1 D2
for f in (E1, 49.00, A1, 61.74, D2):
    place(ks_note(f, 0.35, damp=0.996, brightness=0.5, amp=0.6, detune=0.001), t)
    add_pick_noise(perf, int(t * SR))
    t += 0.21

# 3) sustained low E + fifth, let it ring
place(ks_note(E1, 2.6, damp=0.999, brightness=0.35, amp=0.70, detune=0.0015), t)
place(ks_note(B2, 2.6, damp=0.9988, brightness=0.4, amp=0.35, detune=0.0015), t)
add_pick_noise(perf, int(t * SR))

peak = max(abs(v) for v in perf) + 1e-9
perf = [v / peak * 0.85 for v in perf]
(OUT / "bass_audition.f32").write_bytes(b"".join(struct.pack("<f", v) for v in perf))
with wave.open(str(OUT / "bass_audition_dry.wav"), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, v)) * 32767)) for v in perf))
print(f"wrote bass_audition.f32/.wav  {len(perf) / SR:.2f}s  {len(perf)} samples")
