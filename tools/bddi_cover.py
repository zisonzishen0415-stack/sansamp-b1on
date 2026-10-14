#!/usr/bin/env python3
"""128x64 1-bpp cover for the BassDriver ZDL screen -- the user's chibi,
pixel-for-pixel.

The user supplied a reference chibi (references/user_cover_ref.png).
tools/extract_ref.py pulled it back to its native 25x28 pixel grid
(tools/ref_sprite_grid.py); this module draws that grid at 2x, 50x56
bitmap pixels, mapping each cell class to a 1-bpp tone with a 2x2
ordered dither:

    K black      -> solid ink        R bright red -> 50% dither
    k dark grey  -> 75% dither       D dark red   -> 75% dither
    P pink       -> 25% dither       S skin       -> paper

The effect name sits to the right of the sprite.  Cover convention (see
ZoomMultistompZDL-2026-10 src/airwindows/common/custom_covers.py): the
firmware paints three 20x15 knob-value boxes on top at y=46 (x 14/55/96);
only ~3 px slivers of the dress edge fall under the outer boxes.

usage:  python bddi_cover.py  -> out/bddi_cover_{preview,preview_8x,device}.png
"""
from __future__ import annotations

import os
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent           # sansamp-b1on
G1ON = ROOT.parent                                      # g1oncontrol
ZDL_ROOT = Path(os.environ.get(
    "BDDI_ZDL_ROOT",
    str(G1ON / "zoomreverse" / "ZoomMultistompZDL-2026-10")))
sys.path.insert(0, str(ZDL_ROOT / "build"))
sys.path.insert(0, str(ZDL_ROOT / "src" / "airwindows" / "common"))
sys.path.insert(0, str(ROOT / "tools"))

from screen_image import Canvas, encode_zoom_rle            # noqa: E402
from ref_sprite_grid import GRID                            # noqa: E402

INK, PAPER = 1, 0

SPRITE_X, SPRITE_Y = 19, 6      # top-left of the 2x sprite (50 x 56 px)
SCALE = 2

# per-class tone, 0..16; whole 2x2 cell blocks are either solid or empty,
# chosen by a 4x4 Bayer matrix -> chunky, crisp pixel-art halftone
TONES = {"K": 16, "k": 12, "D": 12, "R": 8, "P": 4, "S": 0, ".": 0}
BAYER4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def _fill(c, x0, y0, x1, y1, v=INK):
    for y in range(y0, y1 + 1):
        c.hline(x0, x1, y, v)


def _note(c, x, y):
    """Eighth note: head + stem + flag (9 px wide, 9 px tall)."""
    c.filled_circle(x, y + 6, 2)
    c.vline(x + 2, y, y + 6)
    c.px(x + 3, y)
    c.px(x + 3, y + 1)
    c.px(x + 4, y + 2)


def _sparkle(c, x, y):
    """Four-point star, 7 px across."""
    c.hline(x - 3, x + 3, y)
    c.vline(x, y - 3, y + 3)
    for dx, dy in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
        c.px(x + dx, y + dy)


def _draw_sprite(c, x0, y0):
    for j, row in enumerate(GRID):
        for i, ch in enumerate(row):
            tone = TONES.get(ch, 0)
            if tone <= BAYER4[j % 4][i % 4]:
                continue                      # this cell stays paper
            _fill(c, x0 + i * SCALE, y0 + j * SCALE,
                  x0 + i * SCALE + SCALE - 1, y0 + j * SCALE + SCALE - 1)


def make_bddi_canvas(param_names=None) -> Canvas:
    c = Canvas()
    c.rect(1, 1, 126, 62)
    _draw_sprite(c, SPRITE_X, SPRITE_Y)
    c.draw_text("BASS", 86, 13, scale=2, spacing=1)
    c.draw_text("DRIVER", 79, 27, scale=2, spacing=1)
    _note(c, 7, 17)                 # left gutter
    _note(c, 77, 47)                # between the sprite and the right box
    _sparkle(c, 120, 52)            # right gutter
    c.px(9, 15)
    c.px(15, 14)
    c.px(83, 44)
    c.px(121, 44)
    return c


def make_bddi_screen(param_names=None) -> bytes:
    return encode_zoom_rle(make_bddi_canvas(param_names))


# ---------------------------------------------------------------- preview
KNOB_BOXES = [(bx, 46, bx + 19, 60) for bx in (14, 55, 96)]


def _png_gray(path, w, h, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    Path(path).write_bytes(png)


def preview_png(c, path, scale=4, vstretch=1.0, boxes=False):
    oh = int(64 * scale * vstretch)
    rows = []
    for oy in range(oh):
        y = min(63, int(oy / (scale * vstretch)))
        row = bytearray(128 * scale)
        for x in range(128):
            v = 0 if c.pixels[y][x] else 255
            for k in range(scale):
                row[x * scale + k] = v
        if boxes:
            for bx0, by0, bx1, by1 in KNOB_BOXES:
                if by0 <= y <= by1:
                    for x in (bx0, bx1):
                        for k in range(scale):
                            row[x * scale + k] = 96
                if y in (by0, by1):
                    for x in range(bx0, bx1 + 1):
                        for k in range(scale):
                            row[x * scale + k] = 96
        rows.append(row)
    _png_gray(path, 128 * scale, oh, rows)


def main() -> int:
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    c = make_bddi_canvas()
    preview_png(c, out / "bddi_cover_preview.png", scale=4)
    preview_png(c, out / "bddi_cover_preview_8x.png", scale=8)
    preview_png(c, out / "bddi_cover_device.png", scale=4, vstretch=1.4,
                boxes=True)
    blob = encode_zoom_rle(c)
    (out / "bddi_cover.bin").write_bytes(blob)
    print(f"cover RLE: {len(blob)} bytes -> out/bddi_cover_{{preview,device}}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
