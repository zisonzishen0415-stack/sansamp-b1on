#!/usr/bin/env python3
"""Quick peak/rms/NaN stats for raw f32 files (arg: one or more paths)."""
import struct
import sys
from pathlib import Path

for p in sys.argv[1:]:
    b = Path(p).read_bytes()
    v = [struct.unpack_from("<f", b, i * 4)[0] for i in range(len(b) // 4)]
    fin = [x for x in v if x == x]
    nan = len(v) - len(fin)
    pk = max((abs(x) for x in fin), default=0.0)
    rms = (sum(x * x for x in fin) / max(1, len(fin))) ** 0.5
    print(f"{Path(p).name:34s} n={len(v):7d} nan={nan} peak={pk:.3f} rms={rms:.4f}")
