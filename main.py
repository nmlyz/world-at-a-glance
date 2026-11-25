#!/usr/bin/env python3
"""world-at-a-glance: draw a newspaper front page summing up the world news
of Wednesday 25 November 2026 as one 1024x1024 PNG.

Everything is drawn with code: a hand-made 5x7 bitmap font, flat ink shapes
and eight small spot illustrations, one per story. No network, no files are
read, no randomness, no clock: every run writes the same bytes.

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

    def wrap(self, s, max_chars):
        lines, cur = [], ""
        for word in s.split(" "):
            if cur and len(cur) + 1 + len(word) > max_chars:
                lines.append(cur)
                cur = word
            else:
                cur = (cur + " " + word).strip()
        if cur:
            lines.append(cur)
        return lines


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
# Spot illustrations, one per story. Each draws inside (x, y, w, h).
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


def draw_nvidia(c, x, y, w, h):
    c.rect(x, y, w, h, WHITE)
    c.frame(x, y, w, h, INK)
    ox, oy = x + 16, y + h - 16
    top = y + 26
    c.line(ox, top - 8, ox, oy, INK, 2)
    c.line(ox, oy, x + w - 10, oy, INK, 2)
    frac = [(0.00, 0.92), (0.18, 0.72), (0.36, 0.68), (0.55, 0.38),
            (0.68, 0.08), (0.80, 0.34), (0.95, 0.55)]
    pts = [(ox + int(fx * (w - 40)), top + int(fy * (oy - top)))
           for fx, fy in frac]
    for a, b in zip(pts, pts[1:]):
        col = GREEN if b[1] <= a[1] else RED
        c.line(a[0], a[1], b[0], b[1], col, 3)
    c.circle(pts[4][0], pts[4][1], 4, GREEN)
    c.text("+31%", x + w // 2 - 10, y + 6, 2, GREEN)
    c.text("-5%", x + w - 52, y + h - 40, 2, RED)
    # A chip in the corner.
    cx, cy = x + w - 58, y + h - 52
    c.rect(cx, cy, 40, 40, (30, 34, 40))
    c.rect(cx + 11, cy + 11, 18, 18, GOLD)
    for i in range(4):
        c.rect(cx - 6, cy + 5 + i * 9, 6, 4, GOLD)
        c.rect(cx + 40, cy + 5 + i * 9, 6, 4, GOLD)


def draw_poland(c, x, y, w, h):
    c.rect(x, y, w, h, SKY)
    cx, cy = x + w // 3, y + h // 2
    r0 = h // 2 - 6
    for r in (r0, r0 * 2 // 3, r0 // 3):
        c.circle(cx, cy, r, SEA2, fill=False)
    c.line(cx, cy, cx + r0 - 4, cy - r0 // 2, SEA2, 2)
    # Dashed drone track crossing the border line.
    bx = x + w * 2 // 3
    c.vline(bx, y + 8, h - 16, RED, 2)
    for i in range(0, 70, 14):
        c.line(x + w // 2 + i, y + h // 4 + i // 2,
               x + w // 2 + i + 8, y + h // 4 + (i + 8) // 2, INK, 2)
    dx, dy = x + w - 52, y + h // 4 + 38
    c.poly([(dx, dy - 7), (dx + 14, dy), (dx, dy + 7), (dx - 14, dy)], INK)
    c.line(dx - 20, dy, dx + 20, dy, INK, 2)
    # AWACS: fuselage, dish, tail.
    ax, ay = x + w - 96, y + h - 22
    c.ellipse(ax, ay, 48, 9, WHITE)
    c.line(ax - 8, ay - 7, ax - 8, ay - 16, INK, 3)
    c.ellipse(ax - 8, ay - 19, 16, 4, INK)
    c.poly([(ax + 44, ay), (ax + 56, ay - 10), (ax + 56, ay + 2)], WHITE)
    # Polish flag.
    c.rect(x + 10, y + 10, 30, 8, WHITE)
    c.rect(x + 10, y + 18, 30, 8, RED)


def draw_chen(c, x, y, w, h):
    c.rect(x, y, w, h, (44, 52, 66))
    base = y + h
    fracs = [0.55, 0.85, 0.68, 0.95, 0.74, 0.88, 0.60]
    bw = w // 7
    for i, fr in enumerate(fracs):
        hh = int(fr * (h - 8))
        bx = x + i * bw + 2
        c.rect(bx, base - hh, bw - 4, hh, (18, 20, 26))
        for wy in range(base - hh + 8, base - 8, 16):
            c.rect(bx + 4, wy, 4, 6, GOLD)
    # Oriental Pearl tower: mast with two spheres.
    tx = x + w // 2
    c.line(tx, y + 6, tx, base - 30, (200, 90, 110), 3)
    c.circle(tx, y + h // 4, 11, (220, 110, 130))
    c.circle(tx, y + h // 2, 7, (220, 110, 130))
    # Red investigation stamp.
    sx, sy = x + w - 96, y + 10
    c.frame(sx, sy, 88, 34, RED, 3)
    c.text("PROBE", sx + 8, sy + 11, 2, RED)


def draw_merger(c, x, y, w, h):
    c.rect(x, y, w, h, WHITE)
    c.frame(x, y, w, h, INK)
    # Rocket, nose up.
    rx = x + 34
    c.rect(rx, y + 22, 26, 62, (230, 230, 228))
    c.poly([(rx, y + 22), (rx + 13, y + 2), (rx + 26, y + 22)], RED)
    c.poly([(rx - 10, y + 84), (rx, y + 62), (rx, y + 84)], RED)
    c.poly([(rx + 26, y + 84), (rx + 26, y + 62), (rx + 36, y + 84)], RED)
    c.poly([(rx + 8, y + 84), (rx + 13, y + h - 8), (rx + 18, y + 84)],
           ORANGE)
    c.circle(rx + 13, y + 40, 5, SEA2)
    # Plus sign between the two.
    c.text("+", x + w // 2 - 6, y + h // 2 - 8, 2, INK)
    # Electric car.
    cx = x + w - 96
    cy = y + h - 34
    c.poly([(cx, cy), (cx + 12, cy - 16), (cx + 52, cy - 16),
            (cx + 66, cy), (cx + 66, cy + 10), (cx, cy + 10)], (30, 90, 140))
    c.poly([(cx + 16, cy - 14), (cx + 26, cy - 26), (cx + 44, cy - 26),
            (cx + 50, cy - 14)], (168, 196, 214))
    c.circle(cx + 14, cy + 10, 7, INK)
    c.circle(cx + 52, cy + 10, 7, INK)


def draw_gaza(c, x, y, w, h):
    c.rect(x, y, w, h, (58, 66, 78))
    # Rain clouds.
    c.ellipse(x + 40, y + 18, 34, 12, (140, 146, 152))
    c.ellipse(x + w - 46, y + 26, 30, 11, (140, 146, 152))
    for i in range(6):
        c.line(x + 20 + i * 14, y + 34, x + 16 + i * 14, y + 48, SKY, 2)
    # City silhouette.
    base = y + h
    for i, fr in enumerate([0.55, 0.80, 0.62, 0.92, 0.68, 0.50]):
        hh = int(fr * (h - 30))
        bw = w // 6
        c.rect(x + i * bw + 2, base - hh, bw - 4, hh, (20, 22, 28))
    # Tents in the foreground.
    for i, tx in enumerate((x + 18, x + w // 2 - 10, x + w - 62)):
        c.poly([(tx, base - 4), (tx + 22, base - 34), (tx + 44, base - 4)],
               (228, 226, 216) if i != 1 else (150, 180, 210))
        c.line(tx + 22, base - 34, tx + 22, base - 4, INK, 2)


def draw_sanofi(c, x, y, w, h):
    c.rect(x, y, w, h, WHITE)
    c.frame(x, y, w, h, INK)
    # Big capsule: red left half, white right half.
    cx, cy = x + w // 2, y + 34
    c.circle(cx - 36, cy, 16, RED)
    c.rect(cx - 36, cy - 16, 36, 32, RED)
    c.circle(cx + 36, cy, 16, WHITE)
    c.rect(cx, cy - 16, 36, 32, WHITE)
    c.circle(cx - 36, cy, 16, INK, fill=False)
    c.circle(cx + 36, cy, 16, INK, fill=False)
    c.hline(cx - 36, cy - 16, 72, INK, 2)
    c.hline(cx - 36, cy + 14, 72, INK, 2)
    c.vline(cx, cy - 16, 32, INK, 2)
    # Flask.
    fx, fy = x + 16, y + h - 52
    c.poly([(fx, fy), (fx + 26, fy), (fx + 34, fy + 34), (fx - 8, fy + 34)],
           (168, 196, 214))
    c.rect(fx + 8, fy - 10, 10, 12, (168, 196, 214))
    c.text("$41B", x + w - 78, y + h - 40, 2, INK)


def draw_hanoi(c, x, y, w, h):
    c.rect(x, y, w, h, (232, 224, 204))
    base = y + h
    # Street buildings.
    for i, fr in enumerate([0.45, 0.62, 0.50]):
        hh = int(fr * (h - 30))
        bw = w // 3
        c.rect(x + i * bw + 2, base - hh - 30, bw - 4, hh, (120, 100, 80))
        c.rect(x + i * bw + 8, base - hh - 22, 10, 10, GOLD)
    # Smoke.
    c.circle(x + w // 2, y + 22, 14, (120, 118, 114))
    c.circle(x + w // 2 + 18, y + 12, 10, (140, 138, 134))
    # Fire truck with ladder.
    tx, ty = x + 12, base - 30
    c.rect(tx, ty, 96, 22, RED)
    c.rect(tx + 70, ty - 14, 26, 14, RED)
    c.line(tx + 8, ty - 4, tx + 90, ty - 44, INK, 3)
    c.line(tx + 14, ty - 4, tx + 96, ty - 44, INK, 2)
    for i in range(5):
        c.line(tx + 16 + i * 16, ty - 8 - i * 8,
               tx + 16 + i * 16, ty - 16 - i * 8, INK, 2)
    c.circle(tx + 18, ty + 22, 7, INK)
    c.circle(tx + 78, ty + 22, 7, INK)


# ---------------------------------------------------------------------------
# Page layout.
# ---------------------------------------------------------------------------

M = 24                      # outer margin
CW = W - 2 * M              # content width


def story(c, x, y, w, h, kicker, heads, body, draw, pic_h):
    """One story block: kicker, illustration, headline lines, body lines."""
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


def build():
    c = Canvas()
    # Masthead.
    c.hline(M, 14, CW, INK, 3)
    c.center("THE WORLD IN ONE PICTURE", W // 2, 30, 4, INK)
    c.center("WEDNESDAY  -  25 NOVEMBER 2026", W // 2, 66, 2, RED)
    c.hline(M, 90, CW, INK, 1)
    c.text("THE DAY IN EIGHT STORIES", M, 98, 1, INK)
    c.text("WORLD NEWS  -  ONE IMAGE", W - M - c.text_w(
        "WORLD NEWS  -  ONE IMAGE", 1), 98, 1, INK)
    c.hline(M, 114, CW, INK, 3)

    # Lead story: Hormuz. Illustration left, text right.
    ly, lh = 126, 344
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
                 "OIL TRANSIT THROUGH THE",
                 "STRAIT IS DOWN ABOUT 40%."):
        c.text(line, tx, by, 2, INK)
        by += 19
    c.frame(tx, by + 6, tw, 40, RED, 2)
    c.center("BRENT CRUDE BELOW $90", tx + tw // 2, by + 17, 2, RED)
    c.hline(M, ly + lh, CW, INK, 2)

    # Row two: three stories.
    ry, rh = 478, 222
    rw = (CW - 32) // 3
    story(c, M, ry, rw, rh, "MARKETS  -  NEW YORK",
          ("NVIDIA COOLS AFTER", "HUANG'S BIG DAY"),
          ("SHARES FELL MORE THAN 5%",
           "ON TUESDAY, A DAY AFTER",
           "A 31% JUMP ON HIS RETURN."),
          draw_nvidia, 92)
    story(c, M + rw + 16, ry, rw, rh, "EUROPE  -  NATO",
          ("RUSSIAN DRONE ENTERS", "POLISH AIRSPACE"),
          ("SECOND INCURSION IN FOUR",
           "DAYS. POLAND HELD FIRE.",
           "NATO SENDS AN AWACS JET."),
          draw_poland, 92)
    story(c, M + 2 * (rw + 16), ry, rw, rh, "CHINA  -  BEIJING",
          ("SHANGHAI CHIEF UNDER", "CORRUPTION PROBE"),
          ("CHEN JINING, A POLITBURO",
           "MEMBER, IS INVESTIGATED",
           "FOR DISCIPLINE BREACHES."),
          draw_chen, 92)
    c.hline(M, ry + rh, CW, INK, 2)

    # Row three: four stories.
    ry, rh = 712, 288
    rw = (CW - 48) // 4
    story(c, M, ry, rw, rh, "BUSINESS",
          ("SPACEX AND TESLA", "TOWARD A MERGER"),
          ("FIVE DIRECTORS NAMED",
           "TO GUIDE TALKS ON A",
           "DEAL PUT AT $3.5T."),
          draw_merger, 120)
    story(c, M + rw + 16, ry, rw, rh, "MIDDLE EAST",
          ("GAZA STRIKE KILLS", "HAMAS SECURITY CHIEF"),
          ("NAEEM ABU NAHAL DIED",
           "IN GAZA CITY. SIX",
           "PEOPLE WERE KILLED."),
          draw_gaza, 120)
    story(c, M + 2 * (rw + 16), ry, rw, rh, "BUSINESS  -  PARIS",
          ("SANOFI BUYS INSMED", "FOR $41 BILLION"),
          ("$175 A SHARE IN CASH,",
           "THE BIGGEST PHARMA",
           "DEAL IN THREE YEARS."),
          draw_sanofi, 120)
    story(c, M + 3 * (rw + 16), ry, rw, rh, "ASIA  -  VIETNAM",
          ("HANOI BLAST KILLS SIX",),
          ("A RESTAURANT BLAST",
           "KILLED SIX, INJURED",
           "TEN. CAUSE PROBED."),
          draw_hanoi, 120)

    # Footer.
    c.hline(M, 1010, CW, INK, 2)
    c.text("SOURCES: IRNA, CNBC, REUTERS, AP, SANOFI, AL JAZEERA, AEROTIME",
           M, 1016, 1, GREY)
    return c


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    c = build()
    write_png(os.path.join(out, "entry.png"), bytes(c.px))


if __name__ == "__main__":
    main()
