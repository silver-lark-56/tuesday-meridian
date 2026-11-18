"""THE TUESDAY MERIDIAN — one-page front page of world news, Tuesday 17 Nov 2026.

Draws a 1024x1024 newspaper front page from stories.json with PIL. Every
illustration is an original vector-style drawing made of basic shapes; no
photos, no third-party images, no AI-generated pictures. Fully deterministic:
one fixed seed, no timestamps, no network, no wall-clock input — the same
input files always produce the same PNG bytes.

Run:  python3 generate.py          (writes entry.png next to this file)
"""

import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SEED = 20261117
RNG = random.Random(SEED)

W, H = 1024, 1024
MARGIN = 16
CONTENT_W = W - 2 * MARGIN  # 992

# ---- palette ----
PAPER = (247, 241, 221)
PAPER_DARK = (238, 230, 203)
INK = (17, 17, 17)
INK_SOFT = (60, 58, 52)
RED = (178, 34, 28)
RED_DARK = (140, 24, 20)
BLUE_DARK = (24, 44, 84)
SKY = (186, 214, 235)
SKY_LIGHT = (214, 231, 244)
SEA = (64, 116, 168)
SEA_DEEP = (38, 84, 134)
SAND = (232, 220, 192)
LAND = (232, 214, 166)
LAND_EDGE = (180, 162, 118)
MAP_SEA = (196, 220, 238)
WHITE = (255, 255, 255)
GREY_LINE = (150, 142, 120)
BLACK = (0, 0, 0)

REGION_COLORS = {
    "EUROPE": (31, 78, 121),
    "MIDDLE EAST": (180, 83, 9),
    "ASIA": (107, 33, 168),
    "AFRICA": (22, 101, 52),
    "AMERICAS": (15, 118, 110),
    "US": (15, 118, 110),
    "PACIFIC": (8, 145, 178),
    "OCEANIA": (8, 145, 178),
    "GLOBAL": (101, 163, 13),
    "WORLD": (101, 163, 13),
}

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def font(name, size):
    return ImageFont.truetype(str(FONT_DIR / name), size)


F_SERIF_B = lambda s: font("DejaVuSerif-Bold.ttf", s)
F_SERIF = lambda s: font("DejaVuSerif.ttf", s)
F_SANS_B = lambda s: font("DejaVuSans-Bold.ttf", s)
F_SANS = lambda s: font("DejaVuSans.ttf", s)


def wrap_text(draw, text, fnt, max_w):
    """Greedy word wrap by pixel width. Returns a list of lines."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_lines(draw, x, y, lines, fnt, fill, leading):
    for i, line in enumerate(lines):
        draw.text((x, y + i * leading), line, font=fnt, fill=fill)
    return y + len(lines) * leading


def fit_font(draw, text, start_size, max_w, bold=True):
    """Largest font size (down to 9) at which text fits max_w. Sans family."""
    size = start_size
    while size > 9:
        fnt = F_SANS_B(size) if bold else F_SANS(size)
        if draw.textlength(text, font=fnt) <= max_w:
            return fnt
        size -= 1
    return F_SANS_B(9) if bold else F_SANS(9)


def banner(draw, x, y, text, fnt, fg, bg, pad_x=5, pad_y=2):
    """Small filled label; returns (width, height)."""
    w = int(draw.textlength(text, font=fnt)) + 2 * pad_x
    h = fnt.size + 2 * pad_y + 2
    draw.rectangle([x, y, x + w, y + h], fill=bg)
    draw.text((x + pad_x, y + pad_y), text, font=fnt, fill=fg)
    return w, h


def jet_shape(draw, cx, cy, s, color, flip=False):
    """Simple jet silhouette from triangles. s = overall length."""
    d = -1 if flip else 1
    body = [(cx - d * s * 0.5, cy), (cx + d * s * 0.5, cy - s * 0.08),
            (cx + d * s * 0.5, cy + s * 0.08)]
    wing = [(cx - d * s * 0.1, cy), (cx + d * s * 0.2, cy - s * 0.28),
            (cx + d * s * 0.3, cy - s * 0.28), (cx + d * s * 0.15, cy)]
    tail = [(cx - d * s * 0.5, cy), (cx - d * s * 0.38, cy - s * 0.22),
            (cx - d * s * 0.28, cy - s * 0.2), (cx - d * s * 0.3, cy)]
    for poly in (body, wing, tail):
        draw.polygon(poly, fill=color)


def burst(draw, cx, cy, r, color=RED, core=(255, 200, 40)):
    """Explosion star: 8 spikes + core circle."""
    pts = []
    for i in range(16):
        ang = math.pi * i / 8
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    draw.polygon(pts, fill=color)
    draw.ellipse([cx - r * 0.35, cy - r * 0.35, cx + r * 0.35, cy + r * 0.35],
                 fill=core)


def smoke(draw, cx, cy, base_r, color=(120, 120, 120), puffs=5):
    """Cluster of overlapping grey circles rising up-left."""
    for i in range(puffs):
        r = base_r * (0.55 + 0.18 * i)
        ox = -i * base_r * 0.55 + RNG.uniform(-2, 2)
        oy = -i * base_r * 0.6 + RNG.uniform(-2, 2)
        draw.ellipse([cx + ox - r, cy + oy - r, cx + ox + r, cy + oy + r],
                     fill=color)


def dashed_line(draw, points, color, width=2, dash=6, gap=4):
    """Dashed polyline through points."""
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0:
            continue
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        d = 0.0
        while d < length:
            e = min(d + dash, length)
            draw.line([x1 + ux * d, y1 + uy * d, x1 + ux * e, y1 + uy * e],
                      fill=color, width=width)
            d = e + gap


def flag_us(draw, x, y, w, h):
    stripe = h / 13
    for i in range(13):
        draw.rectangle([x, y + i * stripe, x + w, y + (i + 1) * stripe],
                       fill=(178, 34, 52) if i % 2 == 0 else WHITE)
    draw.rectangle([x, y, x + w * 0.4, y + stripe * 7], fill=(60, 59, 110))
    for r in range(3):
        for c in range(4):
            px = x + 3 + c * (w * 0.4 - 6) / 3
            py = y + 3 + r * (stripe * 7 - 6) / 2
            draw.ellipse([px - 1, py - 1, px + 1, py + 1], fill=WHITE)
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=1)


def flag_china(draw, x, y, w, h):
    draw.rectangle([x, y, x + w, y + h], fill=(222, 41, 16))
    draw.ellipse([x + w * 0.14, y + h * 0.18, x + w * 0.34, y + h * 0.52],
                 fill=(255, 222, 0))
    for dx, dy in ((0.55, 0.15), (0.68, 0.3), (0.68, 0.55), (0.55, 0.68)):
        cx, cy = x + w * dx, y + h * dy
        draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(255, 222, 0))
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=1)


def flag_russia(draw, x, y, w, h):
    for i, col in enumerate((WHITE, (0, 57, 166), (213, 0, 50))):
        draw.rectangle([x, y + i * h / 3, x + w, y + (i + 1) * h / 3], fill=col)
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=1)


def flag_india(draw, x, y, w, h):
    for i, col in enumerate(((255, 153, 51), WHITE, (19, 136, 8))):
        draw.rectangle([x, y + i * h / 3, x + w, y + (i + 1) * h / 3], fill=col)
    cx, cy, r = x + w / 2, y + h / 2, h / 6
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(6, 3, 141), width=2)
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=1)


def flag_japan(draw, x, y, w, h):
    draw.rectangle([x, y, x + w, y + h], fill=WHITE)
    cx, cy, r = x + w / 2, y + h / 2, h * 0.3
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(188, 0, 45))
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=1)


def flag_australia(draw, x, y, w, h):
    draw.rectangle([x, y, x + w, y + h], fill=(0, 0, 139))
    draw.rectangle([x, y, x + w * 0.45, y + h * 0.5], fill=(0, 0, 100))
    draw.line([x, y, x + w * 0.45, y + h * 0.5], fill=WHITE, width=2)
    draw.line([x + w * 0.45, y, x, y + h * 0.5], fill=WHITE, width=2)
    draw.line([x + w * 0.22, y, x + w * 0.22, y + h * 0.5], fill=(200, 0, 0), width=2)
    draw.line([x, y + h * 0.25, x + w * 0.45, y + h * 0.25], fill=(200, 0, 0), width=2)
    for dx, dy in ((0.65, 0.25), (0.8, 0.45), (0.65, 0.7), (0.85, 0.75), (0.75, 0.6)):
        cx, cy = x + w * dx, y + h * dy
        draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=WHITE)
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=1)


def flag_ukraine(draw, x, y, w, h):
    draw.rectangle([x, y, x + w, y + h / 2], fill=(0, 91, 187))
    draw.rectangle([x, y + h / 2, x + w, y + h], fill=(255, 213, 0))
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=1)


def flag_mongolia(draw, x, y, w, h):
    for i, col in enumerate(((201, 42, 42), (0, 80, 160), (201, 42, 42))):
        draw.rectangle([x + i * w / 3, y, x + (i + 1) * w / 3, y + h], fill=col)
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=1)


# ---- simplified world map polygons (lon, lat), hand-drawn, original ----
CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-125, 72), (-110, 73), (-95, 72), (-85, 70),
     (-80, 73), (-65, 60), (-55, 52), (-65, 45), (-75, 35), (-80, 25),
     (-90, 21), (-97, 16), (-94, 17), (-83, 9), (-79, 9), (-85, 12),
     (-92, 15), (-97, 16), (-105, 20), (-110, 23), (-114, 28), (-120, 34),
     (-124, 40), (-124, 48), (-130, 55), (-145, 60), (-158, 58), (-165, 60)],
    # South America
    [(-79, 9), (-77, 4), (-80, -3), (-81, -6), (-77, -12), (-70, -18),
     (-70, -23), (-65, -28), (-58, -34), (-62, -39), (-65, -45), (-68, -52),
     (-66, -55), (-70, -54), (-73, -45), (-73, -37), (-72, -30), (-70, -20),
     (-75, -15), (-79, -8)],
    # Europe
    [(-10, 36), (-9, 43), (-2, 48), (-4, 50), (0, 53), (3, 58), (5, 60),
     (10, 59), (10, 62), (18, 69), (25, 71), (30, 70), (32, 66), (28, 61),
     (24, 58), (21, 55), (24, 52), (30, 55), (28, 50), (24, 46), (28, 44),
     (23, 40), (22, 37), (19, 40), (16, 42), (12, 44), (8, 44), (7, 44),
     (3, 43), (-2, 37), (-6, 36), (-9, 37)],
    # Africa
    [(-17, 15), (-16, 21), (-10, 31), (-5, 35), (0, 36), (10, 37), (11, 34),
     (20, 32), (25, 32), (32, 31), (34, 28), (35, 23), (37, 18), (39, 15),
     (43, 11), (48, 11), (51, 10), (46, 5), (41, 0), (40, -5), (39, -10),
     (35, -18), (33, -22), (30, -26), (26, -34), (20, -35), (17, -32),
     (15, -27), (12, -18), (13, -10), (9, -1), (9, 4), (4, 6), (-8, 4),
     (-13, 8)],
    # Asia
    [(30, 70), (40, 73), (55, 73), (70, 73), (85, 75), (100, 77), (115, 73),
     (130, 72), (145, 72), (160, 70), (170, 67), (178, 65), (178, 62),
     (170, 60), (162, 56), (158, 52), (150, 50), (142, 45), (140, 40),
     (135, 35), (130, 33), (127, 35), (122, 38), (120, 32), (122, 28),
     (118, 25), (110, 21), (108, 18), (105, 10), (103, 8), (100, 7),
     (98, 10), (95, 16), (92, 22), (88, 22), (86, 20), (80, 16), (77, 8),
     (73, 20), (68, 23), (66, 25), (61, 25), (57, 26), (53, 27), (50, 29),
     (48, 30), (44, 29), (40, 31), (36, 36), (30, 36), (32, 42), (30, 46),
     (28, 50), (30, 55), (30, 60), (30, 66), (32, 70)],
    # Australia
    [(114, -22), (114, -28), (118, -35), (124, -33), (129, -32), (132, -32),
     (135, -35), (138, -35), (140, -38), (145, -38), (150, -37), (153, -30),
     (153, -27), (151, -24), (146, -19), (142, -15), (142, -11), (140, -17),
     (136, -15), (132, -12), (130, -13), (126, -14), (122, -17), (118, -20)],
    # Greenland
    [(-45, 60), (-40, 64), (-32, 68), (-22, 70), (-20, 76), (-30, 82),
     (-45, 80), (-55, 76), (-58, 70), (-52, 64)],
    # Britain
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (1, 51),
     (-3, 50)],
    # Japan
    [(130, 31), (132, 33), (135, 34), (137, 35), (139, 35), (140, 38),
     (141, 40), (142, 44), (145, 44), (144, 42), (140, 39), (139, 36),
     (136, 34), (133, 34)],
    # Sumatra
    [(95, 5), (100, 0), (104, -5), (106, -6), (102, -2), (98, 3)],
    # Borneo
    [(109, 1), (113, 4), (117, 6), (119, 1), (117, -3), (112, -3), (109, -1)],
    # New Guinea
    [(131, -1), (136, -2), (141, -3), (146, -6), (150, -10), (147, -9),
     (142, -8), (136, -4)],
]


# ---- lead illustrations (boxes ~325 x 130) ----

def art_bridge(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=SKY_LIGHT)
    d.rectangle([x0, y0, x1, y0 + (y1 - y0) * 0.42], fill=SKY)
    sea_y = y0 + (y1 - y0) * 0.66
    d.rectangle([x0, sea_y, x1, y1], fill=SEA)
    d.rectangle([x0, sea_y, x1, sea_y + 3], fill=SEA_DEEP)
    # waves
    for i in range(14):
        wx = x0 + 8 + i * 23
        d.arc([wx, sea_y + 12, wx + 16, sea_y + 20], start=200, end=340,
              fill=(180, 210, 235), width=2)
    # bridge deck with a gap in the middle
    deck_y = y0 + (y1 - y0) * 0.52
    mid = (x0 + x1) // 2
    gap = 46
    d.rectangle([x0 + 6, deck_y, mid - gap // 2, deck_y + 7], fill=(90, 90, 90))
    d.rectangle([mid + gap // 2, deck_y, x1 - 6, deck_y + 7], fill=(90, 90, 90))
    # broken ends angled down into the sea
    d.polygon([(mid - gap // 2, deck_y), (mid - gap // 2 + 12, deck_y + 7),
               (mid - 8, sea_y + 2), (mid - 20, sea_y + 2)], fill=(110, 110, 110))
    d.polygon([(mid + gap // 2, deck_y), (mid + gap // 2 - 12, deck_y + 7),
               (mid + 8, sea_y + 2), (mid + 20, sea_y + 2)], fill=(110, 110, 110))
    # piers
    for px in (x0 + 40, x0 + 120, x1 - 120, x1 - 40):
        d.rectangle([px - 5, deck_y + 7, px + 5, sea_y + 2], fill=(120, 120, 120))
    # arch hint
    d.arc([x0 + 60, deck_y - 26, x1 - 60, deck_y + 10], start=180, end=360,
          fill=(70, 70, 70), width=3)
    # explosion + smoke at the gap
    burst(d, mid, deck_y - 6, 13)
    smoke(d, mid - 6, deck_y - 22, 7, puffs=4)
    # jets
    jet_shape(d, x0 + 52, y0 + 22, 26, INK)
    jet_shape(d, x1 - 56, y0 + 16, 22, INK, flip=True)
    d.line([x0 + 66, y0 + 26, x0 + 96, y0 + 32], fill=INK_SOFT, width=1)
    # labels
    f = F_SANS_B(10)
    d.text((x0 + 6, y0 + 4), "CRIMEA", font=f, fill=INK_SOFT)
    d.text((x1 - 48, y0 + 4), "RUSSIA", font=f, fill=INK_SOFT)
    banner(d, x1 - 118, y0 + 34, "ROAD ARCH DOWN", F_SANS_B(10), WHITE, RED)
    # bottom strip
    d.rectangle([x0, y1 - 16, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 6, y1 - 14), "KERCH STRAIT", font=F_SANS_B(10), fill=WHITE)


def art_hormuz(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=SAND)
    w, h = x1 - x0, y1 - y0
    # gulf water: polygon along the lower right
    gulf = [(x0 + w * 0.30, y1), (x0 + w * 0.42, y0 + h * 0.55),
            (x0 + w * 0.62, y0 + h * 0.42), (x0 + w * 0.86, y0 + h * 0.52),
            (x1, y0 + h * 0.60), (x1, y1)]
    d.polygon(gulf, fill=SEA)
    # coast shading
    d.line(gulf[:-1], fill=(140, 120, 80), width=2)
    # dashed drone route Iran -> Bahrain
    dashed_line(d, [(x0 + w * 0.52, y0 + h * 0.22), (x0 + w * 0.34, y0 + h * 0.34),
                    (x0 + w * 0.26, y0 + h * 0.52)], RED, width=2)
    # dashed US strike route
    dashed_line(d, [(x0 + w * 0.40, y0 + h * 0.78), (x0 + w * 0.62, y0 + h * 0.55),
                    (x0 + w * 0.74, y0 + h * 0.42)], BLUE_DARK, width=2)
    # Bahrain radar mark
    bx, by = x0 + w * 0.26, y0 + h * 0.52
    d.ellipse([bx - 9, by - 9, bx + 9, by + 9], outline=RED, width=2)
    d.line([bx - 12, by + 12, bx + 12, by - 12], fill=RED, width=3)
    d.line([bx - 12, by - 12, bx + 12, by + 12], fill=RED, width=3)
    # Qeshm strike burst
    burst(d, x0 + w * 0.76, y0 + h * 0.40, 12)
    # tanker on fire
    tx, ty = x0 + w * 0.88, y0 + h * 0.72
    d.polygon([(tx - 26, ty), (tx + 26, ty), (tx + 20, ty + 10), (tx - 20, ty + 10)],
              fill=(30, 30, 30))
    d.rectangle([tx + 8, ty - 10, tx + 22, ty], fill=WHITE)
    smoke(d, tx - 6, ty - 6, 5, color=(90, 90, 90), puffs=3)
    burst(d, tx - 14, ty - 2, 7)
    # labels
    f = F_SANS_B(10)
    d.text((x0 + w * 0.48, y0 + 5), "IRAN", font=f, fill=INK_SOFT)
    d.text((x0 + 6, y0 + h * 0.58), "BAHRAIN", font=f, fill=INK_SOFT)
    d.text((x0 + w * 0.74, y0 + h * 0.16), "QESHM", font=f, fill=INK_SOFT)
    d.text((x0 + w * 0.60, y1 - 30), "HORMUZ", font=F_SANS_B(10), fill=WHITE)
    banner(d, x0 + w * 0.30, y0 + h * 0.30, "DRONES DOWNED", F_SANS_B(9),
           WHITE, RED)
    banner(d, x0 + w * 0.55, y0 + h * 0.62, "US STRIKES", F_SANS_B(9),
           WHITE, BLUE_DARK)
    d.rectangle([x0, y1 - 16, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 6, y1 - 14), "STRAIT OF HORMUZ", font=F_SANS_B(10), fill=WHITE)


def art_summit(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(226, 232, 240))
    w, h = x1 - x0, y1 - y0
    # skyline silhouette (kept low so it never touches the flags)
    base = y0 + h * 0.86
    towers = [(0.02, 0.16), (0.10, 0.24), (0.20, 0.14), (0.30, 0.28),
              (0.42, 0.18), (0.54, 0.32), (0.64, 0.22), (0.74, 0.26),
              (0.84, 0.16), (0.93, 0.22)]
    for fx, fh in towers:
        tx = x0 + w * fx
        tw = w * 0.075
        d.rectangle([tx, base - h * fh, tx + tw, base], fill=(90, 104, 128))
    d.rectangle([x0, base, x1, y1 - 16], fill=(70, 84, 106))
    # three flags on a stage
    fw, fh = w * 0.24, h * 0.34
    fy = y0 + 10
    flag_china(d, x0 + w * 0.08, fy, fw, fh)
    flag_us(d, x0 + w * 0.38, fy, fw, fh)
    flag_russia(d, x0 + w * 0.68, fy, fw, fh)
    f = F_SANS_B(10)
    for fx, name in ((0.08, "XI"), (0.38, "TRUMP"), (0.68, "PUTIN")):
        cx = x0 + w * fx + fw / 2
        tw = d.textlength(name, font=f)
        d.text((cx - tw / 2, fy + fh + 3), name, font=f, fill=INK)
    banner(d, x0 + w * 0.30, y0 + h * 0.68, "SHENZHEN  ·  THU 19 NOV",
           F_SANS_B(10), WHITE, RED_DARK)
    d.rectangle([x0, y1 - 16, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 6, y1 - 14), "FIRST THREE-WAY SUMMIT", font=F_SANS_B(10),
           fill=WHITE)


# ---- secondary illustrations (boxes ~190 x 62) ----

def art_drones(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=SKY_LIGHT)
    # radar dish
    cx, cy = x0 + 34, y1 - 22
    d.pieslice([cx - 26, cy - 26, cx + 26, cy + 26], start=300, end=60,
               fill=(120, 130, 140))
    d.line([cx, cy, cx + 4, y1 - 14], fill=INK_SOFT, width=3)
    d.arc([cx - 18, cy - 18, cx + 18, cy + 18], start=300, end=60,
          fill=RED, width=2)
    # drones with red X
    for dx, dy in ((110, 14), (140, 30), (168, 12)):
        d.line([x0 + dx - 7, y0 + dy - 5, x0 + dx + 7, y0 + dy + 5],
               fill=INK, width=2)
        d.line([x0 + dx - 7, y0 + dy + 5, x0 + dx + 7, y0 + dy - 5],
               fill=INK, width=2)
        d.ellipse([x0 + dx - 3, y0 + dy - 3, x0 + dx + 3, y0 + dy + 3],
                  fill=RED)
    banner(d, x0 + 78, y0 + 32, "DOWNED", F_SANS_B(9), WHITE, RED)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "BAHRAIN · US RADAR", font=F_SANS_B(9), fill=WHITE)


def art_measles(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(255, 240, 240))
    # virus: spiky circles
    for cx, cy, r in ((x0 + 30, y0 + 22, 11), (x0 + 58, y0 + 36, 8),
                      (x0 + 82, y0 + 18, 6)):
        for k in range(8):
            ang = math.pi * k / 4
            d.line([cx + r * math.cos(ang), cy + r * math.sin(ang),
                    cx + (r + 5) * math.cos(ang), cy + (r + 5) * math.sin(ang)],
                   fill=RED, width=2)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(220, 80, 80))
        d.ellipse([cx - r * 0.4, cy - r * 0.4, cx + r * 0.4, cy + r * 0.4],
                  fill=(150, 30, 30))
    # syringe (shortened so it never reaches the flag corner)
    d.line([x0 + 108, y0 + 40, x0 + 132, y0 + 26], fill=(100, 100, 100), width=5)
    d.line([x0 + 132, y0 + 26, x0 + 142, y0 + 20], fill=INK_SOFT, width=2)
    d.rectangle([x0 + 100, y0 + 36, x0 + 112, y0 + 46], fill=RED)
    flag_us(d, x1 - 44, y0 + 4, 40, 17)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "PAHO · MEASLES", font=F_SANS_B(9), fill=WHITE)


def art_cop31(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(232, 244, 232))
    # globe
    cx, cy, r = x0 + 36, y0 + 26, 20
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=SEA)
    d.ellipse([cx - r + 4, cy - r + 6, cx - 2, cy - 2], fill=(80, 170, 90))
    d.ellipse([cx + 2, cy + 2, cx + r - 2, cy + r - 6], fill=(80, 170, 90))
    # thermometer
    tx = x0 + 82
    d.rectangle([tx, y0 + 8, tx + 8, y0 + 38], fill=WHITE, outline=INK)
    d.rectangle([tx + 1, y0 + 24, tx + 7, y0 + 38], fill=RED)
    d.ellipse([tx - 4, y0 + 34, tx + 12, y0 + 50], fill=RED)
    # draft paper
    px = x0 + 118
    d.rectangle([px, y0 + 8, px + 56, y0 + 44], fill=WHITE, outline=INK_SOFT)
    for i in range(4):
        d.line([px + 6, y0 + 14 + i * 7, px + 50, y0 + 14 + i * 7],
               fill=GREY_LINE, width=2)
    banner(d, px + 6, y0 + 30, "DRAFT", F_SANS_B(8), WHITE, (22, 101, 52))
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "ANTALYA · COP31", font=F_SANS_B(9), fill=WHITE)


def art_chip(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(240, 240, 248))
    # chip
    cx, cy, s = x0 + 40, y0 + 26, 34
    d.rectangle([cx - s // 2, cy - s // 2, cx + s // 2, cy + s // 2],
                fill=(30, 30, 40))
    d.rectangle([cx - 8, cy - 8, cx + 8, cy + 8], fill=(80, 200, 120))
    for dx in (-1, 0, 1):
        d.line([cx + dx * 10, cy - s // 2, cx + dx * 10, cy - s // 2 - 6],
               fill=INK_SOFT, width=2)
        d.line([cx + dx * 10, cy + s // 2, cx + dx * 10, cy + s // 2 + 6],
               fill=INK_SOFT, width=2)
    # rising chart
    pts = [(x0 + 84, y0 + 42), (x0 + 104, y0 + 34), (x0 + 124, y0 + 38),
           (x0 + 144, y0 + 24), (x0 + 166, y0 + 12)]
    d.line(pts, fill=(22, 140, 60), width=3)
    for px, py in pts:
        d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(22, 140, 60))
    banner(d, x0 + 96, y0 + 30, "RECORD QTR", F_SANS_B(9), WHITE,
           (22, 101, 52))
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "AI CHIPS · WALL ST", font=F_SANS_B(9), fill=WHITE)


def art_gaza(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(238, 230, 210))
    # tents
    for tx in (18, 62, 106):
        d.polygon([(x0 + tx, y0 + 44), (x0 + tx + 18, y0 + 20),
                   (x0 + tx + 36, y0 + 44)], fill=WHITE, outline=INK_SOFT)
        d.line([x0 + tx + 18, y0 + 20, x0 + tx + 18, y0 + 44],
               fill=GREY_LINE, width=1)
    # aid truck
    d.rectangle([x0 + 142, y0 + 26, x0 + 182, y0 + 44], fill=WHITE,
                outline=INK_SOFT)
    d.text((x0 + 152, y0 + 30), "AID", font=F_SANS_B(10), fill=RED)
    d.ellipse([x0 + 148, y0 + 42, x0 + 156, y0 + 50], fill=INK)
    d.ellipse([x0 + 170, y0 + 42, x0 + 178, y0 + 50], fill=INK)
    # rain
    for rx in range(10, 190, 16):
        d.line([x0 + rx, y0 + 4, x0 + rx - 3, y0 + 12], fill=SEA, width=1)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "GAZA · CROSSINGS", font=F_SANS_B(9), fill=WHITE)


def art_ebola(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(255, 245, 240))
    # clinic
    d.rectangle([x0 + 14, y0 + 18, x0 + 78, y0 + 48], fill=WHITE,
                outline=INK_SOFT)
    d.polygon([(x0 + 10, y0 + 18), (x0 + 46, y0 + 6), (x0 + 82, y0 + 18)],
              fill=RED)
    d.rectangle([x0 + 40, y0 + 24, x0 + 52, y0 + 36], fill=RED)
    d.rectangle([x0 + 44, y0 + 20, x0 + 48, y0 + 40], fill=RED)
    # virus
    for cx, cy, r in ((x0 + 116, y0 + 20, 9), (x0 + 146, y0 + 34, 7),
                      (x0 + 168, y0 + 16, 6)):
        for k in range(8):
            ang = math.pi * k / 4
            d.line([cx + r * math.cos(ang), cy + r * math.sin(ang),
                    cx + (r + 4) * math.cos(ang), cy + (r + 4) * math.sin(ang)],
                   fill=RED, width=2)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(220, 80, 80))
    banner(d, x0 + 108, y0 + 32, "WHO TALKS", F_SANS_B(9), WHITE, RED_DARK)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "DR CONGO · EBOLA", font=F_SANS_B(9), fill=WHITE)


def art_jets(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=SKY_LIGHT)
    # rising sun
    d.ellipse([x1 - 46, y0 + 6, x1 - 10, y0 + 42], fill=(188, 0, 45))
    jet_shape(d, x0 + 52, y0 + 22, 34, INK)
    jet_shape(d, x0 + 118, y0 + 38, 28, (90, 90, 90), flip=True)
    d.line([x0 + 70, y0 + 26, x0 + 100, y0 + 32], fill=INK_SOFT, width=1)
    banner(d, x0 + 10, y0 + 32, "SCRAMBLED", F_SANS_B(9), WHITE, RED)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "JAPAN · AIRSPACE", font=F_SANS_B(9), fill=WHITE)


def art_bank(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(240, 242, 245))
    # bank building
    d.polygon([(x0 + 16, y0 + 20), (x0 + 52, y0 + 8), (x0 + 88, y0 + 20)],
              fill=(60, 70, 90))
    for cx in (26, 42, 58, 74):
        d.rectangle([x0 + cx, y0 + 22, x0 + cx + 5, y0 + 42], fill=(90, 100, 120))
    d.rectangle([x0 + 16, y0 + 42, x0 + 88, y0 + 48], fill=(60, 70, 90))
    # down arrow + files
    d.line([x0 + 130, y0 + 10, x0 + 130, y0 + 38], fill=RED, width=4)
    d.polygon([(x0 + 130, y0 + 46), (x0 + 121, y0 + 34), (x0 + 139, y0 + 34)],
              fill=RED)
    d.rectangle([x0 + 148, y0 + 14, x0 + 180, y0 + 46], fill=WHITE,
                outline=INK_SOFT)
    for i in range(3):
        d.line([x0 + 153, y0 + 20 + i * 8, x0 + 175, y0 + 20 + i * 8],
               fill=GREY_LINE, width=2)
    banner(d, x0 + 100, y0 + 30, "-6%", F_SANS_B(10), WHITE, RED)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "FRANKFURT · LEAK", font=F_SANS_B(9), fill=WHITE)


def art_resignation(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(242, 238, 224))
    # letter
    d.rectangle([x0 + 24, y0 + 6, x0 + 108, y0 + 46], fill=WHITE,
                outline=INK_SOFT)
    for i in range(4):
        d.line([x0 + 32, y0 + 13 + i * 7, x0 + 100, y0 + 13 + i * 7],
               fill=GREY_LINE, width=2)
    d.ellipse([x0 + 88, y0 + 34, x0 + 102, y0 + 48], fill=RED)
    flag_mongolia(d, x0 + 128, y0 + 12, 48, 28)
    banner(d, x0 + 120, y0 + 32, "TO RESIGN", F_SANS_B(9), WHITE, BLUE_DARK)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "ULAANBAATAR", font=F_SANS_B(9), fill=WHITE)


def art_cyclone(d, x0, y0, x1, y1):
    d.rectangle([x0, y0, x1, y1], fill=(210, 232, 245))
    # spiral
    cx, cy = x0 + 52, y0 + 26
    for r in (8, 14, 20, 26):
        d.arc([cx - r, cy - r, cx + r, cy + r], start=20 + r * 6,
              end=290 + r * 6, fill=(30, 90, 150), width=3)
    d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=WHITE)
    # island
    d.ellipse([x0 + 130, y0 + 30, x0 + 178, y0 + 46], fill=(120, 180, 120))
    d.line([x0 + 154, y0 + 30, x0 + 154, y0 + 18], fill=(100, 80, 50), width=2)
    d.polygon([(x0 + 154, y0 + 18), (x0 + 144, y0 + 26), (x0 + 164, y0 + 26)],
              fill=(40, 120, 60))
    banner(d, x0 + 96, y0 + 8, "CAT 3", F_SANS_B(10), WHITE, RED)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "COOK ISLANDS", font=F_SANS_B(9), fill=WHITE)


ART_FUNCS = {
    "bridge": art_bridge, "hormuz": art_hormuz, "summit": art_summit,
    "drones": art_drones, "measles": art_measles, "cop31": art_cop31,
    "chip": art_chip, "gaza": art_gaza, "ebola": art_ebola,
    "jets": art_jets, "bank": art_bank, "resignation": art_resignation,
    "cyclone": art_cyclone,
}


# ---- layout ----

def region_key(region):
    return {"US": "AMERICAS", "PACIFIC": "OCEANIA", "GLOBAL": "WORLD"}.get(
        region, region)


def draw_region_strip(d, y0, y1, counts):
    order = ["EUROPE", "MIDDLE EAST", "ASIA", "AFRICA", "AMERICAS",
             "OCEANIA", "WORLD"]
    seg_w = CONTENT_W / len(order)
    fnt = F_SANS_B(12)
    for i, name in enumerate(order):
        x = MARGIN + i * seg_w
        d.rectangle([x, y0, x + seg_w - 1, y1],
                    fill=REGION_COLORS[name])
        label = "%s %d" % (name, counts.get(name, 0))
        tw = d.textlength(label, font=fnt)
        d.text((x + (seg_w - tw) / 2, y0 + 4), label, font=fnt, fill=WHITE)


def fit_lines(draw, text, sizes, max_w, max_lines, serif=True, bold=True):
    """Pick the largest font size whose wrap fits in max_lines lines.
    Never silently drops words: the smallest size is used as a last resort
    and the caller still draws every wrapped line."""
    for size in sizes:
        fnt = (F_SERIF_B if serif else F_SANS_B)(size) if bold else \
            (F_SERIF if serif else F_SANS)(size)
        lines = wrap_text(draw, text, fnt, max_w)
        if len(lines) <= max_lines:
            return fnt, lines
    fnt = (F_SERIF_B if serif else F_SANS_B)(sizes[-1]) if bold else \
        (F_SERIF if serif else F_SANS)(sizes[-1])
    return fnt, wrap_text(draw, text, fnt, max_w)


def draw_lead(d, story, x0, y0, col_w):
    art_h = 130
    ART_FUNCS[story["art"]](d, x0, y0, x0 + col_w, y0 + art_h)
    d.rectangle([x0, y0, x0 + col_w, y0 + art_h], outline=INK, width=1)
    color = REGION_COLORS[story["region"]]
    y = y0 + art_h + 4
    tag = "%d  %s · %s" % (story["n"], story["region"], story["field"])
    d.text((x0, y), tag, font=F_SANS_B(12), fill=color)
    y += 17
    f_head, lines = fit_lines(d, story["headline"], [24, 22, 20], col_w, 2)
    y = draw_lines(d, x0, y, lines, f_head, INK, f_head.size + 3)
    y += 3
    f_deck, dlines = fit_lines(d, story["deck"], [12, 11], col_w, 3,
                               serif=False, bold=False)
    draw_lines(d, x0, y, dlines, f_deck, INK_SOFT, f_deck.size + 3)


def draw_second(d, story, x0, y0, col_w):
    art_h = 62
    ART_FUNCS[story["art"]](d, x0, y0, x0 + col_w, y0 + art_h)
    d.rectangle([x0, y0, x0 + col_w, y0 + art_h], outline=INK, width=1)
    color = REGION_COLORS[story["region"]]
    y = y0 + art_h + 3
    tag = "%d  %s · %s" % (story["n"], story["region"], story["field"])
    d.text((x0, y), tag, font=F_SANS_B(10), fill=color)
    y += 14
    f_head, lines = fit_lines(d, story["headline"], [15, 14, 13], col_w, 2)
    y = draw_lines(d, x0, y, lines, f_head, INK, f_head.size + 2)
    y += 2
    f_deck, dlines = fit_lines(d, story["deck"], [11, 10, 9], col_w, 2,
                               serif=False, bold=False)
    draw_lines(d, x0, y, dlines, f_deck, INK_SOFT, f_deck.size + 2)


def draw_map(d, x0, y0, x1, y1, stories, briefs):
    d.rectangle([x0, y0, x1, y1], fill=MAP_SEA)
    d.rectangle([x0, y0, x1, y1], outline=INK, width=1)

    def proj(lon, lat):
        px = x0 + (lon + 180) / 360 * (x1 - x0)
        py = y0 + (80 - lat) / 135 * (y1 - y0)
        return px, py

    for poly in CONTINENTS:
        pts = [proj(lon, lat) for lon, lat in poly]
        d.polygon(pts, fill=LAND, outline=LAND_EDGE)
    # brief dots first (under the numbered pins)
    for b in briefs:
        px, py = proj(*b["loc"])
        col = REGION_COLORS[region_key(b["region"])]
        d.ellipse([px - 2.5, py - 2.5, px + 2.5, py + 2.5], fill=col,
                  outline=WHITE, width=1)
    # numbered pins for stories 1-13
    f_pin = F_SANS_B(8)
    for s in stories:
        px, py = proj(*s["loc"])
        col = REGION_COLORS[region_key(s["region"])]
        d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=WHITE,
                  outline=col, width=2)
        num = str(s["n"])
        tw = d.textlength(num, font=f_pin)
        d.text((px - tw / 2, py - 5), num, font=f_pin, fill=col)


def draw_also_list(d, x0, y0, x1, y1, briefs):
    col_gap = 12
    col_w = (x1 - x0 - col_gap) / 2
    half = (len(briefs) + 1) // 2
    cols = [briefs[:half], briefs[half:]]
    rows = max(len(c) for c in cols)
    leading = (y1 - y0) / rows
    f_num = F_SANS_B(11)
    f_txt = F_SANS(11)
    for ci, col in enumerate(cols):
        cx = x0 + ci * (col_w + col_gap)
        for ri, b in enumerate(col):
            yy = y0 + ri * leading
            num = "%d" % b["n"]
            d.text((cx, yy), num, font=f_num,
                   fill=REGION_COLORS[region_key(b["region"])])
            nx = cx + d.textlength(num + " ", font=f_num)
            fnt = f_txt
            if d.textlength(b["text"], font=fnt) > col_w - (nx - cx):
                fnt = fit_font(d, b["text"], 11, col_w - (nx - cx),
                               bold=False)
            d.text((nx, yy), b["text"], font=fnt, fill=INK)
            # hairline separator
            d.line([cx, yy + leading - 1, cx + col_w, yy + leading - 1],
                   fill=(215, 205, 175), width=1)


def build_page(data):
    stories = data["stories"]
    briefs = data["briefs"]
    total = len(stories) + len(briefs)
    counts = {}
    for item in stories + briefs:
        key = region_key(item["region"])
        counts[key] = counts.get(key, 0) + 1

    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=INK, width=2)

    # ---- top strip ----
    f_kick = F_SANS_B(12)
    d.text((MARGIN, 7), "THE TUESDAY MERIDIAN", font=F_SERIF_B(13), fill=INK)
    strip = "%d STORIES · 6 CONTINENTS · ALL FROM THIS ONE DAY" % total
    tw = d.textlength(strip, font=f_kick)
    d.text((W - MARGIN - tw, 7), strip, font=f_kick, fill=RED)

    # ---- masthead: the date, biggest element on the page ----
    date_text = data["date"].title()  # "Tuesday 17 November 2026"
    f_date = fit_font(d, date_text, 66, CONTENT_W, bold=True)
    # fit_font uses sans; redo with serif for the masthead look
    size = 66
    while size > 40:
        cand = F_SERIF_B(size)
        if d.textlength(date_text, font=cand) <= CONTENT_W:
            f_date = cand
            break
        size -= 1
    else:
        f_date = F_SERIF_B(40)
    tw = d.textlength(date_text, font=f_date)
    d.text(((W - tw) / 2, 24), date_text, font=f_date, fill=INK)
    d.line([MARGIN, 100, W - MARGIN, 100], fill=INK, width=3)
    d.line([MARGIN, 104, W - MARGIN, 104], fill=INK, width=1)

    # ---- region strip ----
    draw_region_strip(d, 108, 130, counts)

    # ---- leads ----
    gap = 8
    col_w = (CONTENT_W - 2 * gap) / 3
    for i, s in enumerate([s for s in stories if s["tier"] == "lead"]):
        draw_lead(d, s, MARGIN + i * (col_w + gap), 134, col_w)

    # ---- secondary rows ----
    seconds = [s for s in stories if s["tier"] == "second"]
    scol_w = (CONTENT_W - 4 * gap) / 5
    for row in range(2):
        y = 388 + row * 146
        for i in range(5):
            s = seconds[row * 5 + i]
            draw_second(d, s, MARGIN + i * (scol_w + gap), y, scol_w)

    # ---- bottom: map + also list ----
    d.line([MARGIN, 682, W - MARGIN, 682], fill=INK, width=2)
    f_sec = F_SANS_B(13)
    d.text((MARGIN, 686), "WHERE IT HAPPENED", font=f_sec, fill=RED)
    d.text((340, 686), "ALSO ON TUESDAY 17 NOVEMBER", font=f_sec, fill=RED)
    draw_map(d, MARGIN, 706, 332, 884, stories, briefs)
    d.text((MARGIN, 888), "Pins: stories 1–13  ·  dots: briefs 14–%d" % total,
           font=F_SANS(10), fill=INK_SOFT)
    d.text((MARGIN, 902), "Every inhabited continent: not one country's day.",
           font=F_SANS_B(10), fill=INK)
    draw_also_list(d, 340, 706, W - MARGIN, 918, briefs)

    # ---- date check strip ----
    y_dc = 924
    d.rectangle([MARGIN, y_dc, W - MARGIN, y_dc + 30], fill=PAPER_DARK,
                outline=RED, width=1)
    bw, _ = banner(d, MARGIN + 5, y_dc + 6, "DATE CHECK", F_SANS_B(11),
                   WHITE, RED)
    f_dc = F_SANS(11)
    dc_lines = wrap_text(d, data["date_check"], f_dc,
                         CONTENT_W - bw - 16)
    draw_lines(d, MARGIN + 5 + bw + 6, y_dc + 3, dc_lines[:2], f_dc, INK, 13)

    # ---- footer ----
    d.line([MARGIN, 962, W - MARGIN, 962], fill=INK, width=2)
    foot1 = ("Every story here happened or was first reported on Tuesday "
             "17 November 2026. Contested claims are marked as claims.")
    d.text((MARGIN, 966), foot1, font=F_SANS_B(11), fill=INK)
    foot2 = ("Sources: Reuters, AP, AFP, BBC, Al Jazeera, WHO, UN. "
             "Original drawings.")
    d.text((MARGIN, 982), foot2, font=F_SANS(10), fill=INK_SOFT)
    return img


def save_entry(img, out_path):
    """Save at most 1 MiB, deterministically. Flat art quantizes cleanly."""
    limit = 1048576
    img.save(out_path, format="PNG", optimize=True)
    size = out_path.stat().st_size
    if size > limit:
        pal = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
        pal.save(out_path, format="PNG", optimize=True)
        size = out_path.stat().st_size
    if size > limit:
        pal = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
        pal.save(out_path, format="PNG", optimize=True)
        size = out_path.stat().st_size
    return size


def main():
    here = Path(__file__).resolve().parent
    with open(here / "stories.json", encoding="utf-8") as fh:
        data = json.load(fh)
    img = build_page(data)
    out = here / "entry.png"
    size = save_entry(img, out)
    print("wrote %s (%d bytes, %dx%d)" % (out, size, img.width, img.height))
    assert img.width == 1024 and img.height == 1024
    assert size <= 1048576, "entry.png exceeds the 1 MiB cap"


if __name__ == "__main__":
    main()
