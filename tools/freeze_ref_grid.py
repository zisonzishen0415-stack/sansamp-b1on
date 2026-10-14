#!/usr/bin/env python3
"""Freeze out/ref_grid.json into tools/ref_sprite_grid.py (committed data)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
g = json.loads((ROOT / "out" / "ref_grid.json").read_text())

head = '''"""User-provided reference chibi, extracted to its native pixel grid.

Source: references/user_cover_ref.png (grid-editor screenshot, ~23.7 px per
cell), extracted by tools/extract_ref.py with a sub-cell alignment search
(700/700 cells classified cleanly).  Letters:

  K black   k dark grey   R bright red   D dark red   P pink   S skin   . empty

A literal pixel copy of the user-supplied art (personal, non-commercial use).
"""

GRID = [
'''
lines = [head]
for r in g:
    lines.append('    "' + "".join(r) + '",\n')
lines.append("]\n")
(ROOT / "tools" / "ref_sprite_grid.py").write_text("".join(lines))
print(f"wrote tools/ref_sprite_grid.py  {len(g)} rows x {len(g[0])} cols")
