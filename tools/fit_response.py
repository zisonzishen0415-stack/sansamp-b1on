#!/usr/bin/env python3
"""Staged fit of the V1L end-to-end target with RBJ biquads mirroring the
C core's bq_* helpers.  Stage A: 2nd-order HP (low end).  Stage B: 4th-order
Butterworth-style LP (the speaker roll-off).  Stage C: two peaking cuts
(the fixed mid scoop).  Prints everything for transcription into bddi.c.
"""
import numpy as np
from scipy.optimize import minimize

FREQS = np.array([20, 30, 40, 50, 60, 80, 100, 150, 200, 300, 400, 500,
                  700, 1000, 1500, 2000, 3000, 4000, 5000, 7000, 10000,
                  15000], float)
TARGET = np.array([-7.9, -3.1, -0.8, 0.5, 0.8, 0.5, -0.4, -3.8, -7.3,
                   -13.5, -17.8, -22.5, -27.5, -12.5, -5.0, -2.0, -0.4,
                   -2.7, -9.3, -23.4, -38.8, -42.0])
SR = 44100.0


def rbq(kind, f0, Q, gain_db=0.0):
    w0 = 2 * np.pi * f0 / SR
    cw, sw = np.cos(w0), np.sin(w0)
    A = 10 ** (gain_db / 40.0)
    if kind == "peaking":
        al = sw / (2 * Q)
        b = [1 + al * A, -2 * cw, 1 - al * A]
        a = [1 + al / A, -2 * cw, 1 - al / A]
    elif kind == "highshelf":
        al = sw / 2 * np.sqrt((A + 1 / A) * (1 / Q - 1) + 2)
        sq = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * cw + sq), -2 * A * ((A - 1) + (A + 1) * cw),
             A * ((A + 1) + (A - 1) * cw - sq)]
        a = [(A + 1) - (A - 1) * cw + sq, 2 * ((A - 1) - (A + 1) * cw),
             (A + 1) - (A - 1) * cw - sq]
    elif kind == "highpass":
        al = sw / (2 * Q)
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
        a = [1 + al, -2 * cw, 1 - al]
    elif kind == "lowpass":
        al = sw / (2 * Q)
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
        a = [1 + al, -2 * cw, 1 - al]
    elif kind == "lowshelf":
        al = sw / 2 * np.sqrt((A + 1 / A) * (1 / Q - 1) + 2)
        sq = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) - (A - 1) * cw + sq), 2 * A * ((A - 1) - (A + 1) * cw),
             A * ((A + 1) - (A - 1) * cw - sq)]
        a = [(A + 1) + (A - 1) * cw + sq, -2 * ((A - 1) + (A + 1) * cw),
             (A + 1) + (A - 1) * cw - sq]
    return np.array(b) / a[0], np.array(a) / a[0]


def resp(bq, f=FREQS):
    b, a = bq
    z = np.exp(-2j * np.pi * f / SR)
    return 20 * np.log10(np.abs((b[0] + b[1] * z + b[2] * z ** 2) /
                                (a[0] + a[1] * z + a[2] * z ** 2)) + 1e-12)


# PRESENCE stage floor (from plot 07: min setting ~+2 dB shelf, hinge ~1.5k)
PRES_MIN = rbq("highshelf", 1500.0, 0.7, 2.0)
res_target = TARGET - resp(PRES_MIN)

# ---- A: high-pass ---------------------------------------------------------
def cost_hp(p):
    r = resp(rbq("highpass", abs(p[0]), abs(p[1]))) - res_target
    return float((r[FREQS <= 100] ** 2).sum())


ra = minimize(cost_hp, [30, 0.7], method="Nelder-Mead")
f_hp, q_hp = abs(ra.x[0]), abs(ra.x[1])
print(f"A: HP2 f={f_hp:.1f} Hz Q={q_hp:.3f}")
hp = resp(rbq("highpass", f_hp, q_hp))

# ---- B: 4th-order Butterworth LP at 3.5 kHz (hand-placed from the
#          required slope: -4/-10.5/-25/-40.7 dB at 4/5/7/10 kHz) ----------
lp_f, lp_q1, lp_q2 = 3500.0, 0.5412, 1.3066
lp = (resp(rbq("lowpass", lp_f, lp_q1)) + resp(rbq("lowpass", lp_f, lp_q2)))
print(f"B: LP4 Butterworth f={lp_f:.0f} Hz, Q = {lp_q1} / {lp_q2} (cascade)")

# ---- C: two peaking cuts (scoop) + a small low shelf ----------------------
base = hp + lp


def cost_sc(p):
    f1, q1, g1, f2, q2, g2, fl, gl = p
    r = (resp(rbq("peaking", abs(f1), abs(q1), -abs(g1))) +
         resp(rbq("peaking", abs(f2), abs(q2), -abs(g2))) +
         resp(rbq("lowshelf", 60 + abs(fl), 0.7, abs(gl))))
    m = (FREQS >= 40) & (FREQS <= 3000)
    w = np.where((FREQS >= 250) & (FREQS <= 1500), 2.0, 1.0)
    return float((w * (base + r - res_target) ** 2)[m].sum())


rc = minimize(cost_sc, [650, 1.7, 24, 420, 0.7, 10, 60, 1.8],
              method="Nelder-Mead", options=dict(maxiter=40000))
f1, q1, g1 = abs(rc.x[0]), abs(rc.x[1]), abs(rc.x[2])
f2, q2, g2 = abs(rc.x[3]), abs(rc.x[4]), abs(rc.x[5])
f_ls, g_ls = 60 + abs(rc.x[6]), abs(rc.x[7])
print(f"C: scoop1 f={f1:.0f} Q={q1:.2f} g=-{g1:.1f}dB   "
      f"scoop2 f={f2:.0f} Q={q2:.2f} g=-{g2:.1f}dB   "
      f"low-shelf f={f_ls:.0f} g=+{g_ls:.2f}dB")
sc = (resp(rbq("peaking", f1, q1, -g1)) + resp(rbq("peaking", f2, q2, -g2))
      + resp(rbq("lowshelf", f_ls, 0.7, g_ls)))

total = resp(PRES_MIN) + hp + lp + sc
err = total - TARGET
print(f"total rms err {np.sqrt((err ** 2).mean()):.2f} dB")
print(f"{'freq':>7} {'fit':>7} {'target':>7} {'err':>6}")
for f, t, m in zip(FREQS, TARGET, total):
    print(f"{f:7.0f} {m:7.1f} {t:7.1f} {m - t:6.1f}")
