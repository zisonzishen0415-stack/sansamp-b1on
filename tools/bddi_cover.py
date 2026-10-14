#!/usr/bin/env python3
"""Anime pixel-art cover (128x64, 1-bpp) for the BassDriver ZDL screen.

Convention (verified from stock covers; see
ZoomMultistompZDL-2026-10/src/airwindows/common/custom_covers.py):
the cover IS the full 128x64 frame, and the firmware paints up to three
20x15 knob-value boxes ON TOP at y=46 (knob_layout(3) -> x 14/55/96).
So: name banner rows 2..15, art rows 16..36, knob labels/dials rows 37..60
in the free gutters (x 0..13, 34..54, 75..95, 116..127).

The face is hand-plotted row by row (the spans below ARE the drawing, the
same way a pixel artist works); the LCD stretches pixels 1.4x vertically
(lcd_geometry.PIXEL_ASPECT), which opens the bitmap face into the taller
oval an anime face wants, so the girl is drawn unsquashed on purpose --
only the banner text goes through _VSquash.

usage:
  python bddi_cover.py     -> out/bddi_cover_preview.png (4x, as drawn)
                              out/bddi_cover_device.png  (4x + 1.4 vertical)
                              out/bddi_cover.bin         (RLE blob)
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

from screen_image import Canvas, encode_zoom_rle            # noqa: E402
from custom_covers import _VSquash, _draw_knob_row          # noqa: E402

INK, PAPER = 1, 0

NAME = "BASS DRIVER"


# ---------------------------------------------------------------- primitives
def _fill(c, x0, y0, x1, y1, v=INK):
    for y in range(y0, y1 + 1):
        c.hline(x0, x1, y, v)


def _spans(c, rows, v=INK):
    """rows: {y: (x0, x1)} -- the hand-plotted outline itself."""
    for y, (x0, x1) in rows.items():
        c.hline(x0, x1, y, v)


def _spike(c, xc, y0, y1, hw, v=INK):
    """Downward triangle: half-width hw at y0, apex at y1."""
    n = max(1, y1 - y0)
    for i, y in enumerate(range(y0, y1 + 1)):
        h = int(hw * (1.0 - i / float(n)) + 0.5)
        c.hline(xc - h, xc + h, y, v)


def _mir_span(c, x0, x1, y, v=INK):
    c.hline(x0, x1, y, v)
    c.hline(127 - x1, 127 - x0, y, v)


def _line(c, x0, y0, x1, y1, v=INK):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        c.px(x0, y0, v)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


# ---------------------------------------------------------------- the girl
# Full-body chibi in the reference style: twin tufts on top, a wide hair
# mass with side wings (pointed tips, white highlight dashes for the light
# shade the coloured original gets from its red), small pale face with dot
# eyes + dithered blush, black dress with a white centre stripe and dotted
# hem, two short legs.  22 rows tall (15..36) -> ~31 px on the LCD.
TUFTS = {15: [(56, 59), (68, 71)], 16: [(55, 60), (67, 72)]}

HAIR = {
    17: [(53, 74)], 18: [(49, 78)], 19: [(47, 80)], 20: [(45, 82)],
    21: [(44, 83)], 22: [(43, 84)], 23: [(43, 84)], 24: [(43, 84)],
    25: [(43, 84)], 26: [(43, 84)], 27: [(44, 83)], 28: [(45, 82)],
    29: [(46, 81)], 30: [(46, 51), (76, 81)],
}

FACE = {
    21: (58, 69), 22: (55, 72), 23: (53, 74), 24: (51, 76),
    25: (50, 77), 26: (50, 77), 27: (51, 76), 28: (53, 74),
    29: (55, 72), 30: (58, 69),
}

DRESS = {
    33: [(57, 70)], 34: [(55, 72)], 35: [(54, 73)], 36: [(54, 73)],
    37: [(53, 74)], 38: [(53, 74)], 39: [(52, 75)], 40: [(52, 75)],
}

ARMS = {
    34: [(51, 53), (74, 76)], 35: [(51, 53), (74, 76)],
    36: [(51, 53), (74, 76)], 37: [(51, 53), (74, 76)],
    38: [(52, 54), (73, 75)],
}

LEGS = {
    41: [(58, 61), (66, 69)], 42: [(58, 61), (66, 69)],
    43: [(58, 61), (66, 69)], 44: [(57, 62), (65, 70)],
}

# white dashes breaking up the solid hair mass (the coloured original's
# lighter red highlights)
HILITE = {
    19: [(55, 58), (69, 72)],
    23: [(45, 47), (80, 82)],
    26: [(45, 47), (80, 82)],
}

DX = -16                       # chibi group offset: bass leans at her right

# the bass leaning beside her (absolute coords): headstock + pegs, neck,
# rounded body with pickup and knobs
BASS_HEAD = {16: [(82, 92)], 17: [(81, 93)], 18: [(83, 91)]}
PEGS = (83, 87, 91)

BASS_BODY = {
    30: [(83, 93)], 31: [(80, 96)], 32: [(78, 98)], 33: [(77, 99)],
    34: [(77, 99)], 35: [(78, 98)], 36: [(78, 98)], 37: [(77, 99)],
    38: [(76, 100)], 39: [(76, 100)], 40: [(77, 99)], 41: [(78, 98)],
    42: [(80, 96)], 43: [(82, 94)], 44: [(84, 92)],
}


def _eye_dot(c, x0, y0):
    """Reference-style dot eye: 6 wide x 5 tall black oval, white glint."""
    c.hline(x0 + 1, x0 + 4, y0)
    for y in (y0 + 1, y0 + 2, y0 + 3):
        c.hline(x0, x0 + 5, y)
    c.hline(x0 + 1, x0 + 4, y0 + 4)
    c.px(x0 + 2, y0 + 3, PAPER)                      # glint, bottom-centre
    c.px(x0 + 3, y0 + 3, PAPER)


def _tail(c, pts):
    """Tapered solid hair tail along a polyline (3 px wide -> point)."""
    segs = len(pts) - 1
    for i in range(segs):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        n = max(abs(x1 - x0), abs(y1 - y0)) + 1
        for s in range(n + 1):
            t = (i + s / float(n)) / segs
            x = int(round(x0 + (x1 - x0) * s / float(n)))
            y = int(round(y0 + (y1 - y0) * s / float(n)))
            r = 3 if t < 0.22 else (2 if t < 0.6 else 1)
            _fill(c, x - r, y - r, x + r, y + r)


def _bow(c, x0, y0):
    """4x4 ribbon knot."""
    _fill(c, x0, y0, x0 + 4, y0 + 3)
    _fill(c, x0 + 1, y0 + 1, x0 + 3, y0 + 2, PAPER)
    c.px(x0 + 2, y0 + 1)


def _note(c, x, y):
    c.filled_circle(x, y + 6, 2)
    c.vline(x + 2, y, y + 6)
    c.px(x + 3, y)
    c.px(x + 3, y + 1)
    c.px(x + 4, y + 2)


def _sparkle(c, x, y):
    c.hline(x - 3, x + 3, y)
    c.vline(x, y - 3, y + 3)
    for dx, dy in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
        c.px(x + dx, y + dy)


def _bass(c):
    """The bass leaning beside her: headstock, pegs, neck, body."""
    for y, runs in BASS_HEAD.items():
        for x0, x1 in runs:
            c.hline(x0, x1, y)
    for x in PEGS:                                    # tuning pegs
        c.px(x, 15)
    c.vline(86, 19, 29)                               # neck
    c.vline(90, 19, 29)
    c.hline(87, 89, 19)                               # nut
    for y in (21, 22, 26, 27):                        # white string dashes
        c.px(88, y, PAPER)
    for y, runs in BASS_BODY.items():                 # body
        for x0, x1 in runs:
            c.hline(x0, x1, y)
    _fill(c, 81, 37, 82, 41, PAPER)                   # pickup
    for x, y in ((93, 35), (95, 38), (90, 43)):       # knobs
        c.px(x, y, PAPER)


def _draw_girl(c):
    dx = DX
    for d in (TUFTS, HAIR, DRESS, ARMS, LEGS):
        for y, runs in d.items():
            for x0, x1 in runs:
                c.hline(x0 + dx, x1 + dx, y)
    for y, (x0, x1) in FACE.items():                  # carve the pale face
        c.hline(x0 + dx, x1 + dx, y, PAPER)
    _eye_dot(c, 56 + dx, 24)                          # dot eyes
    _eye_dot(c, 66 + dx, 24)
    c.hline(62 + dx, 65 + dx, 29)                     # tiny mouth
    for y in (26, 27):                                # dithered blush
        for x in (53, 54, 55, 72, 73, 74):
            if (x + y) % 2 == 0:
                c.px(x + dx, y)
    _fill(c, 63 + dx, 34, 64 + dx, 40, PAPER)         # dress centre stripe
    c.px(63 + dx, 33, PAPER)
    c.px(64 + dx, 33, PAPER)                          # collar
    for x in (54, 57, 60, 67, 70, 73):                # dotted hem
        c.px(x + dx, 40, PAPER)
    for y, runs in HILITE.items():                    # hair highlights
        for x0, x1 in runs:
            c.hline(x0 + dx, x1 + dx, y, PAPER)
    _bass(c)
    _note(c, 7, 17)
    _sparkle(c, 117, 20)
    c.px(112, 26)
    c.px(123, 15)


# ---------------------------------------------------------------- assembly
def make_bddi_canvas(param_names=None) -> Canvas:
    """No knob labels by default: the chibi needs the full frame; the
    firmware still paints its three value boxes on top while editing."""
    c = Canvas()
    c.rect(1, 1, 126, 62)
    for y in range(2, 15):                            # inverse banner
        c.hline(2, 125, y)
    adv = 3 * 2 + 1
    w = len(NAME) * adv - 1
    _VSquash(c, 9).draw_text(NAME, max(3, (128 - w) // 2), 4,
                             scale=2, spacing=1, v=PAPER)
    _draw_girl(c)
    if param_names:
        _draw_knob_row(c, list(param_names))
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
