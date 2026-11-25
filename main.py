#!/usr/bin/env python3
"""world-at-a-glance: draw a newspaper front page summing up the world news
of Wednesday 25 November 2026 as one 1024x1024 PNG.

Fourteen stories: the Strait of Hormuz tanker mines lead the page, then
Nvidia, Poland, Shanghai and the SpaceX/Tesla merger, then nine short
stories from Ukraine, the markets, Microsoft, Bangladesh, Nepal and the
United States. Everything is drawn with code: a hand-made 5x7 bitmap font,
flat ink shapes and fourteen small spot illustrations, one per story. No
network, no files are read, no randomness, no clock: every run writes the
same bytes.

Run:  mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
Writes entry.png into the output directory (default /output).
"""

import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (246, 241, 227)
INK = (26, 26, 26)
RED = (179, 38, 30)
SEA = (22, 50, 74)
SEA2 = (38, 84, 112)
GOLD = (200, 155, 60)
GREEN = (46, 125, 50)
GREY = (120, 116, 108)
LIGHT = (226, 219, 200)
ORANGE = (232, 110, 30)
YELLOW = (245, 190, 60)
WHITE = (255, 255, 255)
SKY = (168, 196, 214)
DARK = (30, 34, 40)


def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, pixels):
    """pixels: bytes of W*H*3 RGB rows, top to bottom."""
    raw = b"".join(b"\x00" + pixels[y * W * 3:(y + 1) * W * 3] for y in range(H))
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    try:
        os.chmod(path, 0o644)
    except OSError:
        pass


class Canvas:
    def __init__(self):
        self.px = bytearray(PAPER) * (W * H)

    def set(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.px[i:i + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + w), min(H, y + h)
        for yy in range(y0, y1):
            i = (yy * W + x0) * 3
            self.px[i:i + (x1 - x0) * 3] = bytes(c) * (x1 - x0)

    def frame(self, x, y, w, h, c, t=1):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.rect(x0 - t // 2, y0 - t // 2, t, t, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill:
                    if d <= r * r:
                        self.set(xx, yy, c)
                elif abs(d - r * r) <= r:
                    self.set(xx, yy, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for yy in range(cy - ry, cy + ry + 1):
            for xx in range(cx - rx, cx + rx + 1):
                if ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0:
                    self.set(xx, yy, c)

    def poly(self, pts, c):
        """Scanline fill of a polygon given as [(x, y), ...]."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(H, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.rect(int(xs[i]), y, max(1, int(xs[i + 1]) - int(xs[i])), 1, c)

    def text(self, s, x, y, scale=1, c=INK):
        s = s.upper()
        cx = x
        for ch in s:
            g = FONT.get(ch)
            if g is None:
                cx += 6 * scale
                continue
            for row in range(7):
                bits = g[row]
                for col in range(5):
                    if bits >> (4 - col) & 1:
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, c)
            cx += 6 * scale
        return cx - x

    def text_w(self, s, scale=1):
        return len(s) * 6 * scale - scale

    def center(self, s, cx, y, scale=1, c=INK):
        self.text(s, cx - self.text_w(s, scale) // 2, y, scale, c)


# 5x7 bitmap font. Each glyph is 7 rows of 5 bits, top to bottom.
FONT = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    " ": (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    ",": (0x00, 0x00, 0x00, 0x00, 0x0C, 0x04, 0x08),
    ":": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    ";": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x04, 0x08),
    "'": (0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00),
    "-": (0x00, 0x00, 0x00, 0x0E, 0x00, 0x00, 0x00),
    "+": (0x00, 0x04, 0x04, 0x0E, 0x04, 0x04, 0x00),
    "$": (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    "%": (0x19, 0x1A, 0x02, 0x04, 0x08, 0x0B, 0x13),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "/": (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x06, 0x04, 0x00, 0x04),
    "=": (0x00, 0x00, 0x0E, 0x00, 0x0E, 0x00, 0x00),
    "|": (0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
}


# ---------------------------------------------------------------------------
# Spot illustrations. Each draws inside (x, y, w, h).
# ---------------------------------------------------------------------------

def _tanker(c, x, y, w, flame=True):
    """A small oil tanker: dark hull, red waterline, deckhouse, flames."""
    h = w // 4
    c.rect(x, y + h // 2, w, h // 2, (40, 40, 44))
    c.rect(x, y + h * 3 // 4, w, h // 4, (150, 40, 30))
    c.rect(x + w * 3 // 5, y, w // 5, h // 2, (230, 225, 210))
    c.rect(x + w // 8, y + h // 2 - 4, 4, 4, GOLD)
    if flame:
        c.poly([(x + w // 4, y), (x + w // 4 + 12, y - 26),
                (x + w // 4 + 24, y)], ORANGE)
        c.poly([(x + w // 2, y - 6), (x + w // 2 + 10, y - 30),
                (x + w // 2 + 20, y - 6)], YELLOW)
        c.poly([(x + w * 3 // 4, y), (x + w * 3 // 4 + 9, y - 20),
                (x + w * 3 // 4 + 18, y)], ORANGE)


def _mine(c, cx, cy, r=7):
    c.circle(cx, cy, r, INK)
    for dx, dy in ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0),
                   (-1, 1), (0, 1), (1, 1)):
        c.line(cx + dx * r, cy + dy * r, cx + dx * (r + 5),
               cy + dy * (r + 5), INK, 2)


def draw_hormuz(c, x, y, w, h):
    """Lead picture: the Strait of Hormuz, burning tankers, mines."""
    c.rect(x, y, w, h, SEA)
    # Land on both sides of the strait channel.
    c.poly([(x, y), (x + w * 3 // 5, y), (x + w // 2, y + h // 3),
            (x, y + h // 2)], (214, 196, 150))
    c.poly([(x + w, y + h), (x + w * 2 // 5, y + h),
            (x + w // 2, y + h * 2 // 3), (x + w, y + h // 2)],
           (198, 178, 132))
    # Dashed shipping lane through the channel.
    for i in range(0, w, 26):
        c.line(x + i, y + h * 2 // 3 - i // 3, x + i + 14,
               y + h * 2 // 3 - (i + 14) // 3, (150, 190, 210), 2)
    _mine(c, x + w // 4, y + h * 3 // 5)
    _mine(c, x + w * 3 // 5, y + h // 2)
    _tanker(c, x + w // 8, y + h // 2, w // 3)
    _tanker(c, x + w // 2, y + h // 2, w // 4)
    _tanker(c, x + w * 3 // 4 - 20, y + h // 3, w // 5, flame=False)
    # Smoke columns over the burning ships.
    c.circle(x + w // 4, y + h // 2 - 34, 12, (90, 90, 92))
    c.circle(x + w // 4 + 16, y + h // 2 - 48, 9, (110, 110, 112))
    c.circle(x + w * 5 // 8, y + h // 2 - 36, 10, (90, 90, 92))


def med_nvidia(c, x, y, w, h):
    """Nvidia: a share chart that leaps up, then slides back down."""
    c.rect(x, y, w, h, WHITE)
    c.frame(x, y, w, h, INK)
    ox, oy = x + 10, y + h - 12
    top = y + 22
    c.line(ox, top - 6, ox, oy, INK, 2)
    c.line(ox, oy, x + w - 8, oy, INK, 2)
    frac = [(0.00, 0.90), (0.20, 0.70), (0.40, 0.66), (0.58, 0.30),
            (0.70, 0.06), (0.84, 0.36), (0.97, 0.58)]
    pts = [(ox + int(fx * (w - 26)), top + int(fy * (oy - top)))
           for fx, fy in frac]
    for a, b in zip(pts, pts[1:]):
        col = GREEN if b[1] <= a[1] else RED
        c.line(a[0], a[1], b[0], b[1], col, 3)
    c.circle(pts[4][0], pts[4][1], 4, GREEN)
    c.text("+31%", x + 12, y + 4, 2, GREEN)
    c.text("-5%", x + w - 46, y + 4, 2, RED)
    # A small chip at bottom left.
    cx, cy = x + 12, oy - 22
    c.rect(cx, cy, 22, 22, DARK)
    c.rect(cx + 7, cy + 7, 8, 8, GOLD)


def med_poland(c, x, y, w, h):
    """Poland: radar screen, a red border line, a drone crossing it."""
    c.rect(x, y, w, h, SKY)
    cx, cy = x + w // 4, y + h // 2 + 4
    r0 = h // 2 - 8
    for r in (r0, r0 * 2 // 3, r0 // 3):
        c.circle(cx, cy, r, SEA2, fill=False)
    c.line(cx, cy, cx + r0 - 3, cy - r0 // 2, SEA2, 2)
    # Border line and the drone crossing it.
    bx = x + w * 3 // 5
    c.vline(bx, y + 6, h - 12, RED, 2)
    dx, dy = bx + 34, y + h // 3
    c.poly([(dx, dy - 6), (dx + 12, dy), (dx, dy + 6), (dx - 12, dy)], INK)
    c.line(dx - 18, dy, dx + 18, dy, INK, 2)
    for i in range(0, 34, 11):
        c.line(bx - 30 + i, dy + 12 + i // 2,
               bx - 22 + i, dy + 12 + (i + 8) // 2, INK, 2)
    # AWACS silhouette at bottom right.
    ax, ay = x + w - 62, y + h - 14
    c.ellipse(ax, ay, 34, 6, WHITE)
    c.line(ax - 6, ay - 5, ax - 6, ay - 11, INK, 2)
    c.ellipse(ax - 6, ay - 13, 11, 3, INK)
    # Polish flag, top left.
    c.rect(x + 8, y + 6, 22, 6, WHITE)
    c.rect(x + 8, y + 12, 22, 6, RED)


def med_chen(c, x, y, w, h):
    """Shanghai: towers at night, the Pearl tower, a red PROBE stamp."""
    c.rect(x, y, w, h, (44, 52, 66))
    base = y + h
    fracs = [0.55, 0.85, 0.68, 0.95, 0.74, 0.88, 0.60]
    bw = w // 7
    for i, fr in enumerate(fracs):
        hh = int(fr * (h - 6))
        bx = x + i * bw + 2
        c.rect(bx, base - hh, bw - 4, hh, (18, 20, 26))
        for wy in range(base - hh + 7, base - 7, 14):
            c.rect(bx + 4, wy, 4, 5, GOLD)
    # Oriental Pearl tower: mast with two spheres.
    tx = x + w // 2
    c.line(tx, y + 4, tx, base - 22, (200, 90, 110), 3)
    c.circle(tx, y + h // 4, 9, (220, 110, 130))
    c.circle(tx, y + h // 2, 6, (220, 110, 130))
    # Red investigation stamp.
    sx, sy = x + w - 78, y + 6
    c.frame(sx, sy, 72, 26, RED, 3)
    c.text("PROBE", sx + 6, sy + 9, 2, RED)


def med_merger(c, x, y, w, h):
    """SpaceX and Tesla: a rocket and an electric car, side by side."""
    c.rect(x, y, w, h, WHITE)
    c.frame(x, y, w, h, INK)
    # Rocket, nose up, left.
    rx = x + 26
    c.rect(rx, y + 16, 20, 38, (230, 230, 228))
    c.poly([(rx, y + 16), (rx + 10, y + 2), (rx + 20, y + 16)], RED)
    c.poly([(rx - 8, y + 54), (rx, y + 38), (rx, y + 54)], RED)
    c.poly([(rx + 20, y + 54), (rx + 20, y + 38), (rx + 28, y + 54)], RED)
    c.poly([(rx + 6, y + 54), (rx + 10, y + h - 4), (rx + 14, y + 54)],
           ORANGE)
    c.circle(rx + 10, y + 30, 4, SEA2)
    # Plus sign between the two.
    c.text("+", x + w // 2 - 5, y + h // 2 - 6, 2, INK)
    # Electric car, right.
    cx = x + w - 82
    cy = y + h - 24
    c.poly([(cx, cy), (cx + 10, cy - 12), (cx + 42, cy - 12),
            (cx + 54, cy), (cx + 54, cy + 8), (cx, cy + 8)], (30, 90, 140))
    c.poly([(cx + 13, cy - 11), (cx + 21, cy - 20), (cx + 36, cy - 20),
            (cx + 41, cy - 11)], (168, 196, 214))
    c.circle(cx + 11, cy + 8, 6, INK)
    c.circle(cx + 43, cy + 8, 6, INK)


# ---------------------------------------------------------------------------
# Short-strip illustrations for the nine small stories (wide, ~40 px tall).
# ---------------------------------------------------------------------------

def strip_gaza(c, x, y, w, h):
    """Gaza: rain over a dark city, tents in front."""
    c.rect(x, y, w, h, (58, 66, 78))
    c.ellipse(x + 34, y + 6, 26, 8, (140, 146, 152))
    c.ellipse(x + w - 40, y + 8, 22, 7, (140, 146, 152))
    for i in range(8):
        c.line(x + 16 + i * 16, y + 16, x + 13 + i * 16, y + 24, SKY, 2)
    base = y + h
    for i, fr in enumerate([0.45, 0.70, 0.55, 0.85, 0.60, 0.42]):
        hh = int(fr * (h - 12))
        bw = w // 6
        c.rect(x + i * bw + 2, base - hh - 12, bw - 4, hh, (20, 22, 28))
    for i, tx in enumerate((x + 20, x + w // 2 - 12, x + w - 66)):
        c.poly([(tx, base - 2), (tx + 20, base - 16), (tx + 40, base - 2)],
               (228, 226, 216) if i != 1 else (150, 180, 210))


def strip_sanofi(c, x, y, w, h):
    """Sanofi: a big capsule and the $41B price tag."""
    c.rect(x, y, w, h, WHITE)
    c.frame(x, y, w, h, INK)
    cx, cy = x + w // 3, y + h // 2
    r = 11
    c.circle(cx - 26, cy, r, RED)
    c.rect(cx - 26, cy - r, 26, 2 * r, RED)
    c.circle(cx + 26, cy, r, WHITE)
    c.rect(cx, cy - r, 26, 2 * r, WHITE)
    c.circle(cx - 26, cy, r, INK, fill=False)
    c.circle(cx + 26, cy, r, INK, fill=False)
    c.hline(cx - 26, cy - r, 52, INK, 2)
    c.hline(cx - 26, cy + r - 2, 52, INK, 2)
    c.vline(cx, cy - r, 2 * r, INK, 2)
    c.text("$41B", x + w - 62, y + h // 2 - 7, 2, INK)


def strip_hanoi(c, x, y, w, h):
    """Hanoi: a street, smoke, and a fire truck with its ladder."""
    c.rect(x, y, w, h, (232, 224, 204))
    base = y + h
    for i, fr in enumerate([0.40, 0.55, 0.45]):
        hh = int(fr * (h - 14))
        bw = w // 3
        c.rect(x + i * bw + 2, base - hh - 16, bw - 4, hh, (120, 100, 80))
        c.rect(x + i * bw + 8, base - hh - 10, 8, 8, GOLD)
    c.circle(x + w // 2, y + 10, 10, (120, 118, 114))
    c.circle(x + w // 2 + 14, y + 6, 7, (140, 138, 134))
    tx, ty = x + 12, base - 16
    c.rect(tx, ty, 84, 14, RED)
    c.rect(tx + 60, ty - 10, 22, 10, RED)
    c.line(tx + 6, ty - 2, tx + 78, ty - 26, INK, 3)
    c.line(tx + 12, ty - 2, tx + 84, ty - 26, INK, 2)
    c.circle(tx + 16, ty + 14, 5, INK)
    c.circle(tx + 68, ty + 14, 5, INK)


def strip_refinery(c, x, y, w, h):
    """Ukraine's refinery strikes: towers burning under a night sky."""
    c.rect(x, y, w, h, DARK)
    base = y + h
    for i, tx in enumerate((x + 16, x + 92, x + 168, x + 244)):
        tw = 34
        th = 20 + (i % 2) * 6
        c.rect(tx, base - th, tw, th, (90, 96, 104))
        c.rect(tx + 6, base - th - 8, 6, 8, (90, 96, 104))
        c.rect(tx + 22, base - th - 8, 6, 8, (90, 96, 104))
        if i in (0, 2):
            c.poly([(tx + 8, base - th - 8), (tx + 14, base - th - 22),
                    (tx + 20, base - th - 8)], ORANGE)
            c.poly([(tx + 20, base - th - 8), (tx + 25, base - th - 18),
                    (tx + 30, base - th - 8)], YELLOW)
    # Drone silhouette, top right.
    dx, dy = x + w - 40, y + 10
    c.poly([(dx, dy - 4), (dx + 10, dy), (dx, dy + 4), (dx - 10, dy)], WHITE)
    c.line(dx - 14, dy, dx + 14, dy, WHITE, 2)


def strip_tariffs(c, x, y, w, h):
    """Tariff threats: falling bars and a red down arrow."""
    c.rect(x, y, w, h, WHITE)
    c.frame(x, y, w, h, INK)
    base = y + h - 8
    heights = [26, 22, 17, 12, 8]
    for i, hh in enumerate(heights):
        bx = x + 18 + i * 26
        c.rect(bx, base - hh, 16, hh, RED)
    c.line(x + 16, base - 30, x + w - 60, base - 4, INK, 3)
    c.poly([(x + w - 60, base - 4), (x + w - 74, base - 8),
            (x + w - 68, base + 2)], INK)
    c.text("%", x + w - 46, y + h // 2 - 7, 2, RED)


def strip_microsoft(c, x, y, w, h):
    """Microsoft: four window panes cracked by the outage."""
    c.rect(x, y, w, h, WHITE)
    c.frame(x, y, w, h, INK)
    px, py, s = x + 14, y + 6, 13
    cols = [(226, 60, 48), (120, 180, 60), (40, 120, 200), (240, 180, 40)]
    for i, col in enumerate(cols):
        c.rect(px + (i % 2) * (s + 2), py + (i // 2) * (s + 2), s, s, col)
    # Crack zigzag across the panes.
    c.line(px - 2, py + 4, px + 14, py + 12, INK, 2)
    c.line(px + 14, py + 12, px + 10, py + 22, INK, 2)
    c.line(px + 10, py + 22, px + 30, py + 28, INK, 2)
    c.text("CODE RED", x + 62, y + h // 2 - 7, 2, RED)


def strip_hasina(c, x, y, w, h):
    """Hasina: a plane heading home, and a calendar marked 16 DEC."""
    c.rect(x, y, w, h, SKY)
    # Airplane silhouette.
    ax, ay = x + 30, y + h // 2
    c.ellipse(ax, ay, 34, 7, WHITE)
    c.poly([(ax - 4, ay), (ax + 10, ay - 14), (ax + 16, ay)], WHITE)
    c.poly([(ax + 28, ay), (ax + 40, ay - 8), (ax + 40, ay + 2)], WHITE)
    c.line(ax - 38, ay, ax - 26, ay - 8, WHITE, 3)
    # Calendar page.
    cx, cy = x + w - 96, y + 4
    c.rect(cx, cy, 84, h - 8, WHITE)
    c.frame(cx, cy, 84, h - 8, INK, 2)
    c.rect(cx, cy, 84, 10, RED)
    c.text("DEC 16", cx + 8, cy + 16, 2, INK)


def strip_nepal(c, x, y, w, h):
    """Nepal quake: mountains and a seismograph zigzag."""
    c.rect(x, y, w, h, SKY)
    base = y + h
    c.poly([(x, base), (x + 70, y + 6), (x + 140, base)], (120, 140, 160))
    c.poly([(x + 90, base), (x + 180, y + 2), (x + 260, base)],
           (96, 118, 140))
    c.poly([(x + 210, base), (x + 260, y + 12), (x + w, base)],
           (120, 140, 160))
    # Snow caps.
    c.poly([(x + 62, y + 12), (x + 70, y + 6), (x + 78, y + 12)],
           WHITE)
    c.poly([(x + 172, y + 8), (x + 180, y + 2), (x + 188, y + 8)],
           WHITE)
    # Seismograph trace.
    pts = [(x + 8, y + h - 8), (x + 60, y + h - 8), (x + 72, y + 8),
           (x + 84, y + h - 12), (x + 96, y + h - 8), (x + 150, y + h - 8),
           (x + 162, y + 12), (x + 174, y + h - 10), (x + 186, y + h - 8),
           (x + w - 8, y + h - 8)]
    for a, b in zip(pts, pts[1:]):
        c.line(a[0], a[1], b[0], b[1], RED, 2)


def strip_ice(c, x, y, w, h):
    """ICE lawsuits: a courthouse front and the scales of justice."""
    c.rect(x, y, w, h, (226, 219, 200))
    base = y + h
    # Courthouse: pediment, columns, steps.
    c.poly([(x + 10, y + 12), (x + 90, y + 2), (x + 170, y + 12)],
           (180, 172, 150))
    for i in range(4):
        cx = x + 24 + i * 40
        c.rect(cx, y + 14, 10, h - 20, (240, 236, 224))
    c.rect(x + 8, base - 6, 164, 6, (180, 172, 150))
    # Scales of justice, right.
    sx, sy = x + w - 56, y + 8
    c.vline(sx, sy, 24, INK, 2)
    c.hline(sx - 16, sy + 2, 32, INK, 2)
    c.line(sx - 16, sy + 2, sx - 22, sy + 14, INK, 2)
    c.line(sx - 16, sy + 2, sx - 10, sy + 14, INK, 2)
    c.line(sx + 16, sy + 2, sx + 10, sy + 14, INK, 2)
    c.line(sx + 16, sy + 2, sx + 22, sy + 14, INK, 2)
    c.poly([(sx - 24, sy + 14), (sx - 8, sy + 14), (sx - 16, sy + 20)],
           INK)
    c.poly([(sx + 8, sy + 14), (sx + 24, sy + 14), (sx + 16, sy + 20)],
           INK)


# ---------------------------------------------------------------------------
# Page layout.
# ---------------------------------------------------------------------------

M = 24                      # outer margin
CW = W - 2 * M              # content width


def story(c, x, y, w, h, kicker, heads, body, draw, pic_h):
    """Medium story: kicker, illustration, headline, body, rule below."""
    c.text(kicker, x, y, 1, RED)
    draw(c, x, y + 16, w, pic_h)
    hy = y + 16 + pic_h + 10
    for hd in heads:
        c.text(hd, x, hy, 2, INK)
        hy += 24
    by = hy + 4
    for line in body:
        c.text(line, x, by, 2, INK)
        by += 17
    c.hline(x, y + h - 1, w, INK, 1)


def small_story(c, x, y, w, h, kicker, heads, body, draw, pic_h):
    """Small story: kicker, strip illustration, headline, one body line."""
    c.text(kicker, x, y, 1, RED)
    draw(c, x, y + 16, w, pic_h)
    hy = y + 16 + pic_h + 8
    for hd in heads:
        c.text(hd, x, hy, 2, INK)
        hy += 22
    by = hy + 4
    for line in body:
        c.text(line, x, by, 2, INK)
        by += 15
    c.hline(x, y + h - 1, w, INK, 1)


def build():
    c = Canvas()
    # Masthead.
    c.hline(M, 14, CW, INK, 3)
    c.center("THE WORLD IN ONE PICTURE", W // 2, 30, 4, INK)
    c.center("WEDNESDAY  -  25 NOVEMBER 2026", W // 2, 66, 2, RED)
    c.hline(M, 90, CW, INK, 1)
    c.text("THE DAY IN FOURTEEN STORIES", M, 98, 1, INK)
    c.text("WORLD NEWS  -  ONE IMAGE", W - M - c.text_w(
        "WORLD NEWS  -  ONE IMAGE", 1), 98, 1, INK)
    c.hline(M, 114, CW, INK, 3)

    # Lead story: Hormuz. Illustration left, text right.
    ly, lh = 126, 254
    lx, lw = M, 540
    tx = lx + lw + 16
    tw = M + CW - tx
    draw_hormuz(c, lx, ly + 20, lw, lh - 28)
    c.text("THE STRAIT OF HORMUZ  -  MIDDLE EAST", tx, ly + 4, 1, RED)
    hy = ly + 26
    for hd in ("TANKERS HIT MINES", "IN THE STRAIT"):
        c.text(hd, tx, hy, 3, INK)
        hy += 30
    by = hy + 8
    for line in ("THREE OIL TANKERS CAUGHT FIRE",
                 "AFTER STRIKING MINES IN THE",
                 "STRAIT OF HORMUZ, IRAN SAID.",
                 "THE SHIPS WERE UNDER U.S.",
                 "ESCORT. ALL CREWS ARE SAFE.",
                 "OIL TRANSIT DOWN ABOUT 40%."):
        c.text(line, tx, by, 2, INK)
        by += 19
    c.frame(tx, by + 6, tw, 40, RED, 2)
    c.center("BRENT CRUDE BELOW $90", tx + tw // 2, by + 17, 2, RED)
    c.hline(M, ly + lh, CW, INK, 2)

    # Row two: four medium stories.
    ry, rh = 388, 190
    rw = (CW - 48) // 4
    story(c, M, ry, rw, rh, "MARKETS  -  NEW YORK",
          ("HUANG APOLOGIZES", "TO NVIDIA STAFF"),
          ("IN DAILY THERAPY,",
           "SHARES SLID AGAIN."),
          med_nvidia, 72)
    story(c, M + rw + 16, ry, rw, rh, "EUROPE  -  NATO",
          ("RUSSIAN DRONE IN", "POLAND, 2ND TIME"),
          ("POLAND HELD FIRE",
           "NATO SENDS AWACS"),
          med_poland, 72)
    story(c, M + 2 * (rw + 16), ry, rw, rh, "CHINA  -  BEIJING",
          ("CHEN JINING UNDER", "CORRUPTION PROBE"),
          ("POLITBURO MEMBER",
           "PROBED FOR BREACHES"),
          med_chen, 72)
    story(c, M + 3 * (rw + 16), ry, rw, rh, "BUSINESS",
          ("SPACEX AND TESLA", "TOWARD A MERGER"),
          ("FIVE DIRECTORS TO",
           "GUIDE $3.5T TALKS"),
          med_merger, 72)
    c.hline(M, ry + rh, CW, INK, 2)

    # Rows three to five: nine small stories, three per row.
    sw = (CW - 32) // 3
    rows = [
        (586, [
            ("MIDDLE EAST", ("GAZA STRIKE KILLS", "HAMAS SECURITY CHIEF"),
             ("SIX KILLED IN GAZA CITY.",), strip_gaza),
            ("BUSINESS  -  PARIS", ("SANOFI BUYS INSMED", "FOR $41 BILLION"),
             ("$175 A SHARE IN CASH.",), strip_sanofi),
            ("ASIA  -  VIETNAM", ("HANOI BLAST", "KILLS SIX"),
             ("TEN INJURED. CAUSE PROBED.",), strip_hanoi),
        ]),
        (723, [
            ("UKRAINE  -  WAR", ("UKRAINE HITS TWO", "RUSSIAN REFINERIES"),
             ("PUTIN VOWS RETALIATION.",), strip_refinery),
            ("MARKETS  -  WORLD", ("TARIFF THREATS HIT", "WORLD STOCKS"),
             ("TECH SHARES LED THE FALL.",), strip_tariffs),
            ("TECHNOLOGY", ("MICROSOFT DECLARES", "CODE RED"),
             ("AFTER A 24-HOUR OUTAGE.",), strip_microsoft),
        ]),
        (860, [
            ("ASIA  -  BANGLADESH", ("HASINA PLANS RETURN", "TO BANGLADESH"),
             ("DHAKA VOWS TO ARREST HER.",), strip_hasina),
            ("ASIA  -  NEPAL", ("QUAKE SHAKES NEPAL", "AND EASTERN INDIA"),
             ("MAGNITUDE 5.3 IN KOSHI.",), strip_nepal),
            ("UNITED STATES", ("TRUMP FACES WAVE OF", "ICE LAWSUITS"),
             ("FEDERAL CASES PILE UP.",), strip_ice),
        ]),
    ]
    for ry, cells in rows:
        for i, (kicker, heads, body, draw) in enumerate(cells):
            small_story(c, M + i * (sw + 16), ry, sw, 137,
                        kicker, heads, body, draw, 40)

    # Footer.
    c.hline(M, 1004, CW, INK, 2)
    c.text("SOURCES: IRNA, CNBC, REUTERS, AP, BLOOMBERG, SANOFI, "
           "AL JAZEERA, KYIV INDEPENDENT",
           M, 1010, 1, GREY)
    return c


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    c = build()
    write_png(os.path.join(out, "entry.png"), bytes(c.px))


if __name__ == "__main__":
    main()
