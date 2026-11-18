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
     (15, -27), (12, -18), (13, -12), (12, -6), (9, -1), (9, 4), (6, 5),
     (4, 6), (-2, 5), (-8, 4), (-13, 8)],
    # Asia
    [(30, 70), (40, 73), (55, 73), (70, 73), (85, 75), (100, 77), (115, 73),
     (130, 72), (145, 72), (160, 70), (170, 67), (178, 65), (178, 62),
     (170, 60), (162, 56), (158, 52), (150, 50), (142, 45), (140, 40),
     (135, 35), (130, 33), (129, 35), (127, 38), (126, 40), (124, 40),
     (122, 38), (120, 32), (122, 28),
     (118, 25), (110, 21), (108, 18), (105, 10), (103, 8), (100, 7),
     (98, 10), (95, 16), (92, 22), (88, 22), (86, 20), (82, 17), (80, 13),
     (77, 8), (75, 12), (73, 20), (68, 23),
     (66, 25), (62, 25), (58, 24), (55, 25), (52, 26), (50, 28), (48, 29),
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
    # Madagascar
    [(44, -12), (47, -15), (50, -16), (50, -20), (47, -25), (44, -25),
     (43, -20), (44, -16)],
    # New Zealand (North + South)
    [(173, -35), (178, -38), (177, -40), (174, -41), (172, -40),
     (173, -37)],
    [(167, -45), (170, -43), (173, -42), (174, -40), (172, -41),
     (168, -46)],
    # Iceland
    [(-22, 64), (-18, 66), (-14, 64), (-15, 63), (-20, 63)],
    # Ireland
    [(-10, 52), (-8, 55), (-6, 55), (-6, 52), (-8, 51)],
    # Sri Lanka
    [(80, 9), (82, 7), (81, 6), (80, 8)],
    # Taiwan
    [(120, 22), (122, 25), (121, 25), (120, 23)],
    # Luzon + Mindanao
    [(120, 18), (122, 14), (121, 13), (120, 16)],
    [(122, 7), (126, 7), (126, 9), (122, 9)],
    # Cuba + Hispaniola
    [(-84, 22), (-80, 23), (-74, 20), (-77, 21), (-82, 22)],
    [(-74, 20), (-72, 20), (-68, 18), (-71, 18)],
    # Sicily + Tasmania
    [(12, 38), (15, 37), (14, 36), (12, 37)],
    [(145, -41), (148, -41), (148, -43), (145, -43)],
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
    # bridge deck with a gap in the middle (road arch brought down)
    deck_y = y0 + (y1 - y0) * 0.52
    mid = (x0 + x1) // 2
    gap = 46
    d.rectangle([x0 + 6, deck_y, mid - gap // 2, deck_y + 7], fill=(90, 90, 90))
    d.rectangle([mid + gap // 2, deck_y, x1 - 6, deck_y + 7], fill=(90, 90, 90))
    # deck railings + lane dashes
    d.line([x0 + 6, deck_y - 3, mid - gap // 2, deck_y - 3],
           fill=(70, 70, 70), width=1)
    d.line([mid + gap // 2, deck_y - 3, x1 - 6, deck_y - 3],
           fill=(70, 70, 70), width=1)
    for lx in range(int(x0) + 14, int(x1) - 14, 18):
        if abs(lx - mid) > gap // 2 + 4:
            d.line([lx, deck_y + 3, lx + 8, deck_y + 3],
                   fill=(220, 220, 220), width=1)
    # broken ends angled down into the sea
    d.polygon([(mid - gap // 2, deck_y), (mid - gap // 2 + 12, deck_y + 7),
               (mid - 8, sea_y + 2), (mid - 20, sea_y + 2)], fill=(110, 110, 110))
    d.polygon([(mid + gap // 2, deck_y), (mid + gap // 2 - 12, deck_y + 7),
               (mid + 8, sea_y + 2), (mid + 20, sea_y + 2)], fill=(110, 110, 110))
    # piers with caps
    for px in (x0 + 40, x0 + 82, x0 + 124, x1 - 124, x1 - 82, x1 - 40):
        d.rectangle([px - 5, deck_y + 7, px + 5, sea_y + 2], fill=(120, 120, 120))
        d.rectangle([px - 8, deck_y + 7, px + 8, deck_y + 10], fill=(90, 90, 90))
    # arch + suspender cables (skip the destroyed middle span)
    d.arc([x0 + 60, deck_y - 26, x1 - 60, deck_y + 10], start=180, end=360,
          fill=(70, 70, 70), width=4)
    acx = (x0 + x1) / 2
    acy = deck_y - 8
    arx = (x1 - x0 - 120) / 2
    ary = 18
    for sx in range(int(x0) + 70, int(x1) - 70, 22):
        if abs(sx - mid) < gap // 2 + 6:
            continue
        t = (sx - acx) / arx
        if abs(t) >= 1:
            continue
        ay = acy - ary * math.sqrt(1 - t * t)
        d.line([sx, ay, sx, deck_y], fill=(100, 100, 100), width=1)
    # falling debris + splash where the span hit the water
    for dx, dy, s in ((-30, 16, 5), (-12, 24, 4), (18, 18, 5), (34, 26, 4)):
        d.rectangle([mid + dx, deck_y + dy, mid + dx + s, deck_y + dy + s],
                    fill=(80, 80, 80))
    for sx in (mid - 26, mid + 14):
        d.arc([sx, sea_y - 2, sx + 22, sea_y + 10], start=180, end=360,
              fill=WHITE, width=2)
    # small patrol boat
    bx = x0 + 44
    d.polygon([(bx, sea_y + 16), (bx + 34, sea_y + 16), (bx + 28, sea_y + 23),
               (bx + 6, sea_y + 23)], fill=(50, 60, 80))
    d.rectangle([bx + 12, sea_y + 10, bx + 20, sea_y + 16], fill=WHITE)
    # explosion + smoke at the gap
    burst(d, mid, deck_y - 6, 14)
    smoke(d, mid - 6, deck_y - 22, 8, puffs=6)
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
    # Qeshm island (small landmass in the strait)
    qx, qy = x0 + w * 0.76, y0 + h * 0.40
    d.ellipse([qx - 16, qy - 7, qx + 16, qy + 7], fill=(222, 206, 170),
              outline=(140, 120, 80))
    # mine markers in the strait shipping lane
    for mx, my in ((0.66, 0.62), (0.72, 0.68), (0.60, 0.70)):
        px, py = x0 + w * mx, y0 + h * my
        d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=BLACK)
        for ang in (45, 135, 225, 315):
            r = math.radians(ang)
            d.line([px, py, px + 5 * math.cos(r), py + 5 * math.sin(r)],
                   fill=BLACK, width=1)
    # dashed tanker route through the strait
    dashed_line(d, [(x0 + w * 0.36, y1 - 20), (x0 + w * 0.58, y0 + h * 0.72),
                    (x0 + w * 0.80, y0 + h * 0.66), (x1 - 8, y0 + h * 0.60)],
                (90, 60, 20), width=2)
    # dashed drone route Iran -> Bahrain, with drone marks
    dashed_line(d, [(x0 + w * 0.52, y0 + h * 0.22), (x0 + w * 0.34, y0 + h * 0.34),
                    (x0 + w * 0.26, y0 + h * 0.52)], RED, width=2)
    for dx, dy in ((0.40, 0.30), (0.33, 0.40)):
        px, py = x0 + w * dx, y0 + h * dy
        d.line([px - 4, py - 4, px + 4, py + 4], fill=INK, width=2)
        d.line([px - 4, py + 4, px + 4, py - 4], fill=INK, width=2)
    # dashed US strike route, with a jet on it
    dashed_line(d, [(x0 + w * 0.40, y0 + h * 0.78), (x0 + w * 0.62, y0 + h * 0.55),
                    (x0 + w * 0.74, y0 + h * 0.42)], BLUE_DARK, width=2)
    jet_shape(d, x0 + w * 0.46, y0 + h * 0.72, 20, BLUE_DARK)
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
    d.text((x0 + w * 0.06, y0 + h * 0.80), "UAE", font=F_SANS_B(9),
           fill=INK_SOFT)
    d.text((x0 + w * 0.42, y0 + h * 0.65), "MINES", font=F_SANS_B(8),
           fill=WHITE)
    d.text((x0 + w * 0.72, y0 + h * 0.54), "PERSIAN GULF",
           font=F_SANS_B(8), fill=(220, 235, 245))
    banner(d, x0 + w * 0.30, y0 + h * 0.30, "DRONES DOWNED", F_SANS_B(9),
           WHITE, RED)
    banner(d, x0 + w * 0.55, y0 + h * 0.62, "US STRIKES", F_SANS_B(9),
           WHITE, BLUE_DARK)
    d.rectangle([x0, y1 - 16, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 6, y1 - 14), "STRAIT OF HORMUZ", font=F_SANS_B(10), fill=WHITE)


def art_summit(d, x0, y0, x1, y1):
    # v3: a summit room, not flags over a skyline — table, name plates,
    # flags on poles, lit Shenzhen towers, calendar page for THU 19 NOV.
    d.rectangle([x0, y0, x1, y1], fill=(226, 232, 240))
    w, h = x1 - x0, y1 - y0
    # sky band + sun
    d.rectangle([x0, y0, x1, y0 + h * 0.42], fill=(196, 216, 238))
    d.ellipse([x0 + w * 0.86, y0 + 6, x0 + w * 0.86 + 18, y0 + 24],
              fill=(255, 214, 90))
    # Shenzhen skyline with lit windows
    base = y0 + h * 0.52
    towers = [(0.02, 0.16), (0.10, 0.26), (0.20, 0.14), (0.30, 0.30),
              (0.42, 0.18), (0.54, 0.34), (0.64, 0.22), (0.74, 0.28),
              (0.84, 0.16), (0.93, 0.22)]
    for fx, fh in towers:
        tx = x0 + w * fx
        tw = w * 0.075
        top = base - h * fh
        d.rectangle([tx, top, tx + tw, base], fill=(90, 104, 128))
        # lit windows: two columns of tiny yellow dots
        wy = top + 4
        while wy < base - 4:
            d.rectangle([tx + 3, wy, tx + 5, wy + 2], fill=(255, 220, 120))
            d.rectangle([tx + tw - 5, wy, tx + tw - 3, wy + 2],
                        fill=(255, 220, 120))
            wy += 7
    # floor band
    d.rectangle([x0, base, x1, y1 - 16], fill=(112, 98, 82))
    # red carpet
    d.rectangle([x0 + w * 0.30, base, x0 + w * 0.70, y1 - 16],
                fill=(150, 30, 30))
    # three flags on poles above the table
    fw, fh = w * 0.20, h * 0.26
    fy = y0 + 8
    for fx, flag in ((0.10, flag_china), (0.40, flag_us),
                     (0.70, flag_russia)):
        px = x0 + w * fx
        d.line([px - 3, fy - 4, px - 3, y0 + h * 0.50], fill=INK_SOFT,
               width=2)
        flag(d, px, fy, fw, fh)
    # conference table with three name plates
    ty = y0 + h * 0.60
    d.rectangle([x0 + w * 0.06, ty, x0 + w * 0.94, ty + 12],
                fill=(96, 64, 32))
    d.rectangle([x0 + w * 0.06, ty, x0 + w * 0.94, ty + 3],
                fill=(140, 100, 60))
    for lx in (0.14, 0.44, 0.74):
        d.rectangle([x0 + w * lx - 4, ty - 2, x0 + w * lx + 4, ty + 14],
                    fill=(60, 44, 26))
    f = F_SANS_B(9)
    for fx, name in ((0.10, "XI"), (0.40, "TRUMP"), (0.70, "PUTIN")):
        cx = x0 + w * fx + fw / 2
        pw = d.textlength(name, font=f) + 8
        d.rectangle([cx - pw / 2, ty - 13, cx + pw / 2, ty - 3], fill=WHITE,
                    outline=INK_SOFT)
        tw = d.textlength(name, font=f)
        d.text((cx - tw / 2, ty - 12), name, font=f, fill=INK)
    # date banner below the table (a calendar page here collided with
    # the PUTIN name plate, so the date stays in the banner)
    banner(d, x0 + 6, y0 + h * 0.60 + 13, "SHENZHEN  ·  THU 19 NOV",
           F_SANS_B(10), WHITE, RED_DARK)
    d.rectangle([x0, y1 - 16, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 6, y1 - 14), "FIRST THREE-WAY SUMMIT", font=F_SANS_B(10),
           fill=WHITE)


# ---- secondary illustrations (boxes ~190 x 62) ----

def art_drones(d, x0, y0, x1, y1):
    # v3: radar station on a Bahrain islet — dish, sweep rings, drone
    # swarm on a dashed track, one drone falling in smoke.
    d.rectangle([x0, y0, x1, y1], fill=SKY_LIGHT)
    w = x1 - x0
    strip = y1 - 14
    # sea + islet ground
    d.rectangle([x0, strip - 8, x1, strip], fill=SEA)
    d.ellipse([x0 + 6, strip - 12, x0 + 78, strip + 2], fill=SAND,
              outline=LAND_EDGE)
    # clouds
    for cx, cy, r in ((150, 8, 7), (168, 12, 5), (120, 6, 5)):
        d.ellipse([x0 + cx - r, y0 + cy - r, x0 + cx + r, y0 + cy + r],
                  fill=WHITE)
    # dashed drone track from the top right (Iran) to the radar
    dashed_line(d, [(x1 - 8, y0 + 4), (x0 + w * 0.62, y0 + 12),
                    (x0 + w * 0.42, y0 + 16)], RED, width=1)
    # radar dish on a mast, with sweep rings
    cx, cy = x0 + 38, strip - 22
    d.line([cx, cy + 6, cx, strip - 8], fill=INK_SOFT, width=3)
    d.pieslice([cx - 16, cy - 16, cx + 16, cy + 16], start=300, end=60,
               fill=(120, 130, 140))
    for rr in (20, 26):
        d.arc([cx - rr, cy - rr, cx + rr, cy + rr], start=300, end=60,
              fill=RED, width=1)
    d.line([cx, cy, cx + 16, cy - 10], fill=RED, width=2)
    # small control hut
    d.rectangle([x0 + 56, strip - 16, x0 + 74, strip - 8], fill=WHITE,
                outline=INK_SOFT)
    d.rectangle([x0 + 61, strip - 13, x0 + 66, strip - 10], fill=SEA)
    # drone swarm: X-marks with red cores
    for dx, dy in ((0.52, 10), (0.64, 6), (0.76, 14), (0.88, 8)):
        px, py = x0 + w * dx, y0 + dy
        d.line([px - 5, py - 4, px + 5, py + 4], fill=INK, width=2)
        d.line([px - 5, py + 4, px + 5, py - 4], fill=INK, width=2)
        d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=RED)
    # one drone falling, trailing smoke
    fx, fy = x0 + w * 0.60, y0 + 26
    d.line([fx - 5, fy - 4, fx + 5, fy + 4], fill=INK, width=2)
    d.line([fx - 5, fy + 4, fx + 5, fy - 4], fill=INK, width=2)
    dashed_line(d, [(fx + 4, fy - 6), (fx + 12, fy - 14)], (120, 120, 120),
                width=1, dash=3, gap=2)
    burst(d, fx + 2, fy + 2, 5)
    banner(d, x0 + w * 0.68, y0 + 24, "DOWNED", F_SANS_B(9), WHITE, RED)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "BAHRAIN · US RADAR", font=F_SANS_B(9), fill=WHITE)


def art_measles(d, x0, y0, x1, y1):
    # v3: clinic scene — viruses, syringe, vaccine vial, crossed shield.
    d.rectangle([x0, y0, x1, y1], fill=(255, 240, 240))
    w = x1 - x0
    strip = y1 - 14
    # floor band
    d.rectangle([x0, strip - 6, x1, strip], fill=(232, 214, 214))
    # viruses: spiky circles, four of them
    for cx, cy, r in ((0.14, 14, 9), (0.30, 26, 7), (0.44, 12, 5),
                      (0.55, 28, 6)):
        px, py = x0 + w * cx, y0 + cy
        for k in range(8):
            ang = math.pi * k / 4
            d.line([px + r * math.cos(ang), py + r * math.sin(ang),
                    px + (r + 4) * math.cos(ang),
                    py + (r + 4) * math.sin(ang)], fill=RED, width=2)
        d.ellipse([px - r, py - r, px + r, py + r], fill=(220, 80, 80))
        d.ellipse([px - r * 0.4, py - r * 0.4, px + r * 0.4, py + r * 0.4],
                  fill=(150, 30, 30))
    # vaccine vial
    vx = x0 + w * 0.62
    d.rectangle([vx, y0 + 20, vx + 12, y0 + 36], fill=WHITE,
                outline=INK_SOFT)
    d.rectangle([vx + 3, y0 + 16, vx + 9, y0 + 20], fill=RED)
    d.rectangle([vx + 1, y0 + 28, vx + 11, y0 + 36], fill=(180, 220, 240))
    # syringe, diagonal
    d.line([x0 + w * 0.70, y0 + 30, x0 + w * 0.84, y0 + 18],
           fill=(100, 100, 100), width=4)
    d.line([x0 + w * 0.84, y0 + 18, x0 + w * 0.89, y0 + 14],
           fill=INK_SOFT, width=2)
    d.rectangle([x0 + w * 0.68, y0 + 28, x0 + w * 0.72, y0 + 34], fill=RED)
    # crossed shield (protection lost)
    sx = x0 + w * 0.80
    d.polygon([(sx, y0 + 24), (sx + 10, y0 + 28), (sx + 10, y0 + 34),
               (sx, y0 + 40), (sx - 10, y0 + 34), (sx - 10, y0 + 28)],
              fill=(200, 220, 240), outline=INK_SOFT)
    d.line([sx - 8, y0 + 38, sx + 8, y0 + 26], fill=RED, width=2)
    flag_us(d, x1 - 44, y0 + 4, 40, 17)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "PAHO · MEASLES", font=F_SANS_B(9), fill=WHITE)


def art_cop31(d, x0, y0, x1, y1):
    # v3: globe + thermometer + factory smoke + draft paper + $120bn tag
    # ($120bn yearly climate finance by 2035, from the story deck).
    d.rectangle([x0, y0, x1, y1], fill=(232, 244, 232))
    w = x1 - x0
    strip = y1 - 14
    # sun
    d.ellipse([x0 + w * 0.30, y0 + 2, x0 + w * 0.30 + 12, y0 + 14],
              fill=(255, 214, 90))
    # globe
    cx, cy, r = x0 + 26, y0 + 22, 16
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=SEA)
    d.ellipse([cx - r + 3, cy - r + 5, cx - 2, cy - 2], fill=(80, 170, 90))
    d.ellipse([cx + 2, cy + 2, cx + r - 2, cy + r - 5], fill=(80, 170, 90))
    d.ellipse([cx - 12, cy - 10, cx - 4, cy + 4], fill=WHITE)
    # thermometer
    tx = x0 + 52
    d.rectangle([tx, y0 + 6, tx + 7, y0 + 30], fill=WHITE, outline=INK)
    d.rectangle([tx + 1, y0 + 20, tx + 6, y0 + 30], fill=RED)
    d.ellipse([tx - 3, y0 + 27, tx + 10, y0 + 40], fill=RED)
    # factory with smoking stack (fossil fuels)
    fx = x0 + 70
    d.rectangle([fx, y0 + 22, fx + 26, strip - 2], fill=(120, 120, 120))
    d.rectangle([fx + 18, y0 + 10, fx + 24, y0 + 22], fill=(100, 100, 100))
    smoke(d, fx + 21, y0 + 8, 4, color=(150, 150, 150), puffs=3)
    d.rectangle([fx + 4, y0 + 27, fx + 9, y0 + 32], fill=(255, 220, 120))
    # leaf sprig at the factory base
    d.ellipse([fx - 6, strip - 10, fx + 2, strip - 2], fill=(60, 150, 70))
    # draft paper with DRAFT + $120BN tags
    px = x0 + 118
    d.rectangle([px, y0 + 6, px + 56, y0 + 36], fill=WHITE, outline=INK_SOFT)
    for i in range(3):
        d.line([px + 6, y0 + 11 + i * 6, px + 50, y0 + 11 + i * 6],
               fill=GREY_LINE, width=2)
    banner(d, px + 6, y0 + 26, "DRAFT", F_SANS_B(8), WHITE, (22, 101, 52))
    banner(d, x0 + 104, y0 + 2, "$120BN", F_SANS_B(8), WHITE, (22, 101, 52))
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "ANTALYA · COP31", font=F_SANS_B(9), fill=WHITE)


def art_chip(d, x0, y0, x1, y1):
    # v3: AI chip with circuit traces + rising chart + $130BN tag
    # (Q4 forecast about $130bn, from the story deck).
    d.rectangle([x0, y0, x1, y1], fill=(240, 240, 248))
    w = x1 - x0
    strip = y1 - 14
    # circuit traces across the panel floor
    for ty in (strip - 8, strip - 4):
        d.line([x0 + 4, ty, x1 - 4, ty], fill=(200, 200, 220), width=1)
    # chip with AI core
    cx, cy, s = x0 + 36, y0 + 21, 30
    d.rectangle([cx - s // 2, cy - s // 2, cx + s // 2, cy + s // 2],
                fill=(30, 30, 40))
    d.rectangle([cx - 8, cy - 8, cx + 8, cy + 8], fill=(80, 200, 120))
    f_ai = F_SANS_B(8)
    d.text((cx - 5, cy - 6), "AI", font=f_ai, fill=INK)
    for dx in (-1, 0, 1):
        d.line([cx + dx * 9, cy - s // 2, cx + dx * 9, cy - s // 2 - 5],
               fill=INK_SOFT, width=2)
        d.line([cx + dx * 9, cy + s // 2, cx + dx * 9, cy + s // 2 + 5],
               fill=INK_SOFT, width=2)
    for dy in (-1, 0, 1):
        d.line([cx - s // 2, cy + dy * 9, cx - s // 2 - 5, cy + dy * 9],
               fill=INK_SOFT, width=2)
        d.line([cx + s // 2, cy + dy * 9, cx + s // 2 + 5, cy + dy * 9],
               fill=INK_SOFT, width=2)
    # small second chip
    d.rectangle([x0 + 62, y0 + 28, x0 + 78, y0 + 42], fill=(50, 50, 70))
    d.rectangle([x0 + 67, y0 + 33, x0 + 73, y0 + 39], fill=(80, 200, 120))
    # rising chart with grid
    gx0, gy0 = x0 + 86, y0 + 8
    d.rectangle([gx0, gy0, x1 - 8, strip - 4], outline=(200, 200, 220))
    d.line([gx0, gy0 + 12, x1 - 8, gy0 + 12], fill=(220, 220, 235), width=1)
    pts = [(gx0 + 2, strip - 10), (gx0 + 20, strip - 16),
           (gx0 + 38, strip - 13), (gx0 + 56, strip - 24),
           (gx0 + 76, strip - 30)]
    d.line(pts, fill=(22, 140, 60), width=3)
    for px, py in pts:
        d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(22, 140, 60))
    banner(d, x0 + 96, y0 + 26, "RECORD QTR", F_SANS_B(9), WHITE,
           (22, 101, 52))
    banner(d, x1 - 62, y0 + 2, "$130BN", F_SANS_B(8), WHITE, (22, 101, 52))
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "AI CHIPS · WALL ST", font=F_SANS_B(9), fill=WHITE)


def art_gaza(d, x0, y0, x1, y1):
    # v3: camp + crossing gate + aid convoy + waiting figures in the rain.
    d.rectangle([x0, y0, x1, y1], fill=(238, 230, 210))
    w = x1 - x0
    strip = y1 - 14
    ground = strip - 4
    d.rectangle([x0, ground, x1, strip], fill=(214, 202, 170))
    # tents
    for tx in (10, 48, 86):
        d.polygon([(x0 + tx, ground), (x0 + tx + 15, y0 + 16),
                   (x0 + tx + 30, ground)], fill=WHITE, outline=INK_SOFT)
        d.line([x0 + tx + 15, y0 + 16, x0 + tx + 15, ground],
               fill=GREY_LINE, width=1)
    # red-cross flag on the middle tent
    d.line([x0 + 63, y0 + 8, x0 + 63, y0 + 16], fill=INK_SOFT, width=1)
    d.rectangle([x0 + 63, y0 + 8, x0 + 75, y0 + 14], fill=WHITE,
                outline=INK_SOFT)
    d.rectangle([x0 + 67, y0 + 9, x0 + 71, y0 + 13], fill=RED)
    # crossing gate (striped barrier) between camp and trucks
    gx = x0 + 122
    d.line([gx, y0 + 12, gx, ground], fill=INK_SOFT, width=2)
    for i, col in enumerate((RED, WHITE, RED, WHITE)):
        d.rectangle([gx, y0 + 12 + i * 3, gx + 18, y0 + 15 + i * 3],
                    fill=col)
    # waiting figures
    for fx in (130, 140):
        d.ellipse([x0 + fx, y0 + 26, x0 + fx + 5, y0 + 31], fill=INK_SOFT)
        d.rectangle([x0 + fx + 1, y0 + 31, x0 + fx + 4, ground],
                    fill=INK_SOFT)
    # aid truck (one wide truck: a second one overflowed the panel edge)
    tx0, ty0, tw = x0 + 146, y0 + 20, 40
    d.rectangle([tx0, ty0, tx0 + tw, ground - 2], fill=WHITE,
                outline=INK_SOFT)
    d.text((tx0 + 9, ty0 + 2), "AID", font=F_SANS_B(9), fill=RED)
    d.ellipse([tx0 + 4, ground - 4, tx0 + 10, ground + 2], fill=INK)
    d.ellipse([tx0 + tw - 10, ground - 4, tx0 + tw - 4, ground + 2],
              fill=INK)
    # rain
    for rx in range(8, int(w) - 4, 14):
        d.line([x0 + rx, y0 + 3, x0 + rx - 3, y0 + 10], fill=SEA, width=1)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "GAZA · CROSSINGS", font=F_SANS_B(9), fill=WHITE)


def art_ebola(d, x0, y0, x1, y1):
    # v3: clinic + annex tent + ambulance + viruses + "11,000 CITED" tag
    # (Tedros cited 11,000 cases at the emergency talks — the story deck).
    d.rectangle([x0, y0, x1, y1], fill=(255, 245, 240))
    w = x1 - x0
    strip = y1 - 14
    ground = strip - 2
    # clinic
    d.rectangle([x0 + 8, y0 + 16, x0 + 62, y0 + 40], fill=WHITE,
                outline=INK_SOFT)
    d.polygon([(x0 + 4, y0 + 16), (x0 + 35, y0 + 5), (x0 + 66, y0 + 16)],
              fill=RED)
    d.rectangle([x0 + 30, y0 + 21, x0 + 40, y0 + 31], fill=RED)
    d.rectangle([x0 + 33, y0 + 18, x0 + 37, y0 + 34], fill=RED)
    d.rectangle([x0 + 12, y0 + 24, x0 + 20, y0 + 32], fill=(180, 220, 240))
    d.rectangle([x0 + 48, y0 + 24, x0 + 56, y0 + 32], fill=(180, 220, 240))
    # annex tent
    d.polygon([(x0 + 66, ground), (x0 + 78, y0 + 22), (x0 + 90, ground)],
              fill=WHITE, outline=INK_SOFT)
    d.rectangle([x0 + 76, y0 + 30, x0 + 80, y0 + 36], fill=RED)
    # ambulance
    ax = x0 + 96
    d.rectangle([ax, y0 + 26, ax + 30, ground - 2], fill=WHITE,
                outline=INK_SOFT)
    d.rectangle([ax + 10, y0 + 29, ax + 18, y0 + 37], fill=RED)
    d.rectangle([ax + 13, y0 + 26, ax + 15, y0 + 40], fill=RED)
    d.ellipse([ax + 3, ground - 5, ax + 9, ground + 1], fill=INK)
    d.ellipse([ax + 21, ground - 5, ax + 27, ground + 1], fill=INK)
    # viruses (kept high so the WHO TALKS banner sits clear below)
    for cx, cy, r in ((0.72, 12, 7), (0.84, 18, 6), (0.94, 10, 5)):
        px, py = x0 + w * cx, y0 + cy
        for k in range(8):
            ang = math.pi * k / 4
            d.line([px + r * math.cos(ang), py + r * math.sin(ang),
                    px + (r + 3) * math.cos(ang),
                    py + (r + 3) * math.sin(ang)], fill=RED, width=2)
        d.ellipse([px - r, py - r, px + r, py + r], fill=(220, 80, 80))
    banner(d, x0 + 96, y0 + 8, "11,000 CITED", F_SANS_B(8), WHITE,
           RED_DARK)
    banner(d, x0 + 132, y0 + 30, "WHO TALKS", F_SANS_B(8), WHITE, RED_DARK)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "DR CONGO · EBOLA", font=F_SANS_B(9), fill=WHITE)


def art_jets(d, x0, y0, x1, y1):
    # v3: three jets over the Sea of Japan — islands, dashed tracks,
    # rising sun, contrails.
    d.rectangle([x0, y0, x1, y1], fill=SKY_LIGHT)
    w = x1 - x0
    strip = y1 - 14
    # sea band + Japan islands along the bottom
    d.rectangle([x0, strip - 10, x1, strip], fill=SEA)
    d.polygon([(x0 + w * 0.60, strip - 4), (x0 + w * 0.67, strip - 12),
               (x0 + w * 0.74, strip - 6), (x0 + w * 0.81, strip - 12),
               (x0 + w * 0.88, strip - 4)], fill=LAND, outline=LAND_EDGE)
    d.text((x0 + 6, strip - 9), "SEA OF JAPAN", font=F_SANS_B(8),
           fill=WHITE)
    # rising sun with rays
    d.ellipse([x1 - 40, y0 + 4, x1 - 10, y0 + 34], fill=(188, 0, 45))
    for ang in (200, 230, 260):
        r = math.radians(ang)
        sx, sy = x1 - 25, y0 + 19
        d.line([sx + 15 * math.cos(r), sy + 15 * math.sin(r),
                sx + 21 * math.cos(r), sy + 21 * math.sin(r)],
               fill=(188, 0, 45), width=2)
    # dashed intercept tracks
    dashed_line(d, [(x0 + 8, y0 + 30), (x0 + w * 0.42, y0 + 16),
                    (x0 + w * 0.62, y0 + 22)], INK_SOFT, width=1)
    dashed_line(d, [(x0 + w * 0.95, y0 + 26), (x0 + w * 0.70, y0 + 14)],
                (120, 120, 120), width=1, dash=4, gap=3)
    # three jets: two scrambling, one turning away
    jet_shape(d, x0 + 46, y0 + 14, 30, INK)
    jet_shape(d, x0 + 96, y0 + 24, 24, (70, 70, 70))
    jet_shape(d, x0 + 138, y0 + 10, 26, (110, 110, 110), flip=True)
    d.line([x0 + 62, y0 + 17, x0 + 82, y0 + 20], fill=INK_SOFT, width=1)
    banner(d, x0 + 6, y0 + 18, "SCRAMBLED", F_SANS_B(9), WHITE, RED)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "JAPAN · AIRSPACE", font=F_SANS_B(9), fill=WHITE)


def art_bank(d, x0, y0, x1, y1):
    # v3: bank + falling chart + down arrow + file stacks + coins.
    d.rectangle([x0, y0, x1, y1], fill=(240, 242, 245))
    w = x1 - x0
    strip = y1 - 14
    # falling chart line across the top
    pts = [(x0 + 6, y0 + 8), (x0 + 40, y0 + 12), (x0 + 70, y0 + 10),
           (x0 + 100, y0 + 20), (x0 + 130, y0 + 26)]
    d.line(pts, fill=RED, width=2)
    for px, py in pts:
        d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=RED)
    # bank building
    d.polygon([(x0 + 12, y0 + 20), (x0 + 44, y0 + 10), (x0 + 76, y0 + 20)],
              fill=(60, 70, 90))
    for cx in (20, 34, 48, 62):
        d.rectangle([x0 + cx, y0 + 22, x0 + cx + 5, y0 + 36],
                    fill=(90, 100, 120))
    d.rectangle([x0 + 12, y0 + 36, x0 + 76, y0 + 41], fill=(60, 70, 90))
    # down arrow
    d.line([x0 + 108, y0 + 12, x0 + 108, y0 + 30], fill=RED, width=4)
    d.polygon([(x0 + 108, y0 + 37), (x0 + 100, y0 + 27), (x0 + 116, y0 + 27)],
              fill=RED)
    # file stacks (two piles of leaked documents)
    for ox in (128, 156):
        d.rectangle([x0 + ox + 3, y0 + 10, x0 + ox + 27, y0 + 38],
                    fill=(225, 225, 225), outline=INK_SOFT)
        d.rectangle([x0 + ox, y0 + 14, x0 + ox + 24, y0 + 40], fill=WHITE,
                    outline=INK_SOFT)
        for i in range(3):
            d.line([x0 + ox + 4, y0 + 19 + i * 6, x0 + ox + 20,
                    y0 + 19 + i * 6], fill=GREY_LINE, width=2)
    d.text((x0 + 126, y0 + 2), "15M DOCS", font=F_SANS_B(8), fill=INK_SOFT)
    banner(d, x0 + 84, y0 + 28, "-6%", F_SANS_B(10), WHITE, RED)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "FRANKFURT · LEAK", font=F_SANS_B(9), fill=WHITE)


def art_resignation(d, x0, y0, x1, y1):
    # v3: parliament building + resignation letter with seal + flag.
    d.rectangle([x0, y0, x1, y1], fill=(242, 238, 224))
    w = x1 - x0
    strip = y1 - 14
    # parliament building (right side): dome + columns + steps
    bx = x0 + 104
    d.rectangle([bx, y0 + 20, bx + 76, strip - 2], fill=(200, 190, 160))
    d.polygon([(bx - 4, y0 + 20), (bx + 38, y0 + 8), (bx + 80, y0 + 20)],
              fill=(150, 60, 50))
    d.ellipse([bx + 30, y0 + 2, bx + 46, y0 + 14], fill=(150, 60, 50))
    for cx in (112, 128, 144, 160):
        d.rectangle([x0 + cx, y0 + 23, x0 + cx + 5, y0 + 36],
                    fill=(240, 235, 220))
    d.rectangle([bx - 2, strip - 6, bx + 78, strip - 2], fill=(170, 160, 130))
    # Mongolia flag mounted on the facade, right of the columns
    flag_mongolia(d, bx + 58, y0 + 22, 18, 12)
    # resignation letter (left side)
    d.rectangle([x0 + 8, y0 + 6, x0 + 92, y0 + 40], fill=WHITE,
                outline=INK_SOFT)
    for i in range(4):
        d.line([x0 + 15, y0 + 12 + i * 6, x0 + 85, y0 + 12 + i * 6],
               fill=GREY_LINE, width=2)
    # signature squiggle + red seal
    d.line([(x0 + 15, y0 + 35), (x0 + 21, y0 + 31), (x0 + 27, y0 + 36),
            (x0 + 33, y0 + 32), (x0 + 39, y0 + 35)], fill=INK_SOFT, width=1)
    d.ellipse([x0 + 72, y0 + 28, x0 + 86, y0 + 42], fill=RED)
    d.ellipse([x0 + 76, y0 + 32, x0 + 82, y0 + 38], fill=(255, 200, 200))
    banner(d, x0 + 104, y0 + 28, "TO RESIGN", F_SANS_B(9), WHITE, BLUE_DARK)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "ULAANBAATAR", font=F_SANS_B(9), fill=WHITE)


def art_cyclone(d, x0, y0, x1, y1):
    # v3: bigger spiral + wind arrows + two islets + small boat + rain.
    d.rectangle([x0, y0, x1, y1], fill=(210, 232, 245))
    w = x1 - x0
    strip = y1 - 14
    # rain bands
    for rx in range(int(x0) + 8, int(x1) - 8, 16):
        d.line([rx, y0 + 3, rx - 4, y0 + 10], fill=(90, 140, 190), width=1)
    # sea band
    d.rectangle([x0, strip - 8, x1, strip], fill=(120, 180, 220))
    # spiral (cyclone eye + arms)
    cx, cy = x0 + 46, y0 + 22
    for r in (7, 12, 17, 22):
        d.arc([cx - r, cy - r, cx + r, cy + r], start=20 + r * 6,
              end=290 + r * 6, fill=(30, 90, 150), width=3)
    d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=WHITE)
    # wind arrows curling around the spiral
    for ax, ay, flip in ((86, 10, False), (92, 30, True), (10, 30, False)):
        d.arc([x0 + ax - 8, y0 + ay - 5, x0 + ax + 8, y0 + ay + 5],
              start=200 if flip else 20, end=340 if flip else 160,
              fill=(30, 90, 150), width=2)
    # main island with palm
    d.ellipse([x0 + 122, strip - 14, x0 + 168, strip - 2],
              fill=(120, 180, 120))
    d.line([x0 + 145, strip - 14, x0 + 145, strip - 24],
           fill=(100, 80, 50), width=2)
    d.polygon([(x0 + 145, strip - 24), (x0 + 136, strip - 16),
               (x0 + 154, strip - 16)], fill=(40, 120, 60))
    # second islet
    d.ellipse([x0 + 172, strip - 10, x0 + 190, strip - 3],
              fill=(120, 180, 120))
    # small boat riding the swell
    bx = x0 + 92
    d.polygon([(bx, strip - 10), (bx + 20, strip - 10), (bx + 16, strip - 5),
               (bx + 4, strip - 5)], fill=(80, 50, 30))
    d.line([bx + 10, strip - 10, bx + 10, strip - 18], fill=INK_SOFT,
           width=1)
    d.polygon([(bx + 10, strip - 18), (bx + 10, strip - 10),
               (bx + 18, strip - 10)], fill=WHITE)
    banner(d, x0 + 84, y0 + 4, "CAT 3", F_SANS_B(10), WHITE, RED)
    d.rectangle([x0, y1 - 14, x1, y1], fill=BLUE_DARK)
    d.text((x0 + 5, y1 - 12), "COOK ISLANDS", font=F_SANS_B(9), fill=WHITE)


ART_FUNCS = {
    "bridge": art_bridge, "hormuz": art_hormuz, "summit": art_summit,
    "drones": art_drones, "measles": art_measles, "cop31": art_cop31,
    "chip": art_chip, "gaza": art_gaza, "ebola": art_ebola,
    "jets": art_jets, "bank": art_bank, "resignation": art_resignation,
    "cyclone": art_cyclone,
}

SEC_ROW_H = 138  # vertical pitch of the secondary-story rows (v3: tighter
# rows free room for the stat strip + field chart below)

# bottom-strip captions for the secondary art panels (re-drawn in the
# story's region colour by draw_second)
STRIP_LABELS = {
    "drones": "BAHRAIN · US RADAR",
    "measles": "PAHO · MEASLES",
    "cop31": "ANTALYA · COP31",
    "chip": "AI CHIPS · WALL ST",
    "gaza": "GAZA · CROSSINGS",
    "ebola": "DR CONGO · EBOLA",
    "jets": "JAPAN · AIRSPACE",
    "bank": "FRANKFURT · LEAK",
    "resignation": "ULAANBAATAR",
    "cyclone": "COOK ISLANDS",
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
    art_h = 112  # v3: slightly shorter lead art buys room for the stat strip
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
    art_h = 56  # v3: tighter secondary art; the panels are denser, not emptier
    ART_FUNCS[story["art"]](d, x0, y0, x0 + col_w, y0 + art_h)
    # region-coloured bottom strip over the art (replaces uniform blue)
    strip_col = REGION_COLORS[region_key(story["region"])]
    d.rectangle([x0, y0 + art_h - 14, x0 + col_w, y0 + art_h],
                fill=strip_col)
    d.text((x0 + 5, y0 + art_h - 12), STRIP_LABELS[story["art"]],
           font=F_SANS_B(9), fill=WHITE)
    d.rectangle([x0, y0, x0 + col_w, y0 + art_h], outline=INK, width=1)
    color = REGION_COLORS[story["region"]]
    y = y0 + art_h + 3
    tag = "%d  %s · %s" % (story["n"], story["region"], story["field"])
    d.text((x0, y), tag, font=F_SANS_B(10), fill=color)
    y += 14
    f_head, lines = fit_lines(d, story["headline"], [16, 15, 14], col_w, 2)
    y = draw_lines(d, x0, y, lines, f_head, INK, f_head.size + 2)
    y += 2
    # deck fills the space the headline left: 3 lines when the headline
    # took one line, else 2 — largest font that fits the row budget,
    # never dropping words
    row_bottom = y0 + SEC_ROW_H
    max_deck = 3 if len(lines) == 1 else 2
    f_deck = dlines = None
    for size in (12, 11, 10):
        cand = F_SANS(size)
        wrapped = wrap_text(d, story["deck"], cand, col_w)
        if (len(wrapped) <= max_deck
                and len(wrapped) * (size + 2) <= row_bottom - y):
            f_deck, dlines = cand, wrapped
            break
    if f_deck is None:
        f_deck = F_SANS(10)
        dlines = wrap_text(d, story["deck"], f_deck, col_w)
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
    f_num = F_SANS_B(8)
    f_txt = F_SANS(11)
    for ci, col in enumerate(cols):
        cx = x0 + ci * (col_w + col_gap)
        for ri, b in enumerate(col):
            yy = y0 + ri * leading
            num = "%d" % b["n"]
            col = REGION_COLORS[region_key(b["region"])]
            # pill badge: region colour, white number (8 px tall so the
            # tight 9.6 px leading keeps a gap between neighbours)
            bw = d.textlength(num, font=f_num) + 6
            by = yy + (leading - 8) / 2
            d.rounded_rectangle([cx, by, cx + bw, by + 8], radius=4,
                                fill=col)
            d.text((cx + 3, yy + 0.5), num, font=f_num, fill=WHITE)
            nx = cx + bw + 4
            fnt = f_txt
            if d.textlength(b["text"], font=fnt) > col_w - (nx - cx):
                fnt = fit_font(d, b["text"], 11, col_w - (nx - cx),
                               bold=False)
            d.text((nx, yy), b["text"], font=fnt, fill=INK)
            # hairline separator
            d.line([cx, yy + leading - 1, cx + col_w, yy + leading - 1],
                   fill=(215, 205, 175), width=1)


# Six big numbers for the stat strip. Every number comes from one of the
# 56 verified stories (story number in the comment) — no new figures.
# 11,000 is framed as "cited", never as "passed on 17 Nov" (the figure
# already existed in 9-12 Nov data; the 17 Nov hook is the WHO statement).
STATS = [
    ("11,000+", "EBOLA CASES CITED BY WHO"),        # story 9 deck
    ("$130bn", "NVIDIA Q4 FORECAST"),               # story 7 deck
    ("-1.6%", "DOW ON TUESDAY"),                    # brief 29
    ("1,441", "DRONES RUSSIA SAYS DOWNED"),         # brief 15 (a claim)
    ("146,000", "MARCH IN FRENCH STRIKE"),          # brief 39
    ("Tk 30,000", "GARMENT WAGE DEMAND"),           # story 43 (Gazipur)
]


def draw_stat_strip(d, y0, y1):
    d.rectangle([MARGIN, y0, W - MARGIN, y1], fill=PAPER_DARK,
                outline=GREY_LINE, width=1)
    cell_w = CONTENT_W / len(STATS)
    f_num = F_SANS_B(19)
    f_lab = F_SANS_B(8)
    for i, (num, lab) in enumerate(STATS):
        x = MARGIN + i * cell_w
        if i:
            d.line([x, y0 + 4, x, y1 - 4], fill=GREY_LINE, width=1)
        tw = d.textlength(num, font=f_num)
        d.text((x + (cell_w - tw) / 2, y0 + 2), num, font=f_num, fill=RED)
        tw = d.textlength(lab, font=f_lab)
        d.text((x + (cell_w - tw) / 2, y0 + 22), lab, font=f_lab,
               fill=INK_SOFT)


CHART_MAP = {"GAZA": "WAR", "WEATHER": "DISASTER"}


def field_counts(stories, briefs):
    """Count all 56 stories by chart field; order by count desc, ties by
    first appearance in the story order."""
    counts, first = {}, {}
    for idx, item in enumerate(stories + briefs):
        f = CHART_MAP.get(item["field"], item["field"])
        counts[f] = counts.get(f, 0) + 1
        first.setdefault(f, idx)
    return sorted(counts.items(), key=lambda kv: (-kv[1], first[kv[0]]))


def draw_field_chart(d, x0, y0, x1, y1, ranked):
    total = sum(n for _, n in ranked)
    f_title = F_SANS_B(11)
    title = "THE DAY BY FIELD"
    d.text((x0, y0), title, font=f_title, fill=RED)
    sub = "%d STORIES · %d FIELDS" % (total, len(ranked))
    f_sub = F_SANS_B(8)
    tw = d.textlength(sub, font=f_sub)
    d.text((x1 - tw, y0 + 2), sub, font=f_sub, fill=INK_SOFT)
    top = y0 + 15
    pitch = (y1 - top) / len(ranked)
    f_lab = F_SANS_B(8)
    f_num = F_SANS_B(8)
    lab_w = 92
    bar_max = (x1 - x0) - lab_w - 22
    max_n = ranked[0][1]
    bar_col = (31, 78, 121)
    for i, (name, n) in enumerate(ranked):
        by = top + i * pitch
        bh = max(4, pitch - 3)
        d.text((x0, by - 1), name, font=f_lab, fill=INK)
        bw = bar_max * n / max_n
        d.rectangle([x0 + lab_w, by, x0 + lab_w + bw, by + bh], fill=bar_col)
        num = str(n)
        tw = d.textlength(num, font=f_num)
        d.text((x1 - tw, by - 1), num, font=f_num, fill=INK)


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
    fields_n = len(field_counts(stories, briefs))
    strip = "%d STORIES · 6 CONTINENTS · %d FIELDS · ONE DAY" % (
        total, fields_n)
    tw = d.textlength(strip, font=f_kick)
    d.text((W - MARGIN - tw, 7), strip, font=f_kick, fill=RED)

    # ---- masthead: the date, biggest element on the page ----
    date_text = data["date"].title()  # "Tuesday 17 November 2026"
    size = 60  # v3: slightly smaller masthead buys room for the stat strip
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
    d.line([MARGIN, 92, W - MARGIN, 92], fill=INK, width=3)
    d.line([MARGIN, 96, W - MARGIN, 96], fill=INK, width=1)

    # ---- region strip ----
    draw_region_strip(d, 100, 122, counts)

    # ---- stat strip (v3): six big numbers from verified stories ----
    draw_stat_strip(d, 124, 156)

    # ---- leads ----
    gap = 8
    col_w = (CONTENT_W - 2 * gap) / 3
    for i, s in enumerate([s for s in stories if s["tier"] == "lead"]):
        draw_lead(d, s, MARGIN + i * (col_w + gap), 160, col_w)

    # ---- secondary rows ----
    seconds = [s for s in stories if s["tier"] == "second"]
    scol_w = (CONTENT_W - 4 * gap) / 5
    for row in range(2):
        y = 399 + row * SEC_ROW_H
        for i in range(5):
            s = seconds[row * 5 + i]
            draw_second(d, s, MARGIN + i * (scol_w + gap), y, scol_w)

    # ---- bottom: map + field chart (left) + also list (right) ----
    d.line([MARGIN, 679, W - MARGIN, 679], fill=INK, width=2)
    f_sec = F_SANS_B(13)
    d.text((MARGIN, 683), "WHERE IT HAPPENED", font=f_sec, fill=RED)
    d.text((316, 683), "ALSO ON TUESDAY 17 NOVEMBER", font=f_sec, fill=RED)
    draw_map(d, MARGIN, 703, 300, 808, stories, briefs)
    d.text((MARGIN, 810), "Pins: stories 1–13  ·  dots: briefs 14–%d" % total,
           font=F_SANS(9), fill=INK_SOFT)
    draw_field_chart(d, MARGIN, 824, 300, 932,
                     field_counts(stories, briefs))
    draw_also_list(d, 316, 703, W - MARGIN, 932, briefs)

    # ---- date check strip ----
    y_dc = 938
    d.rectangle([MARGIN, y_dc, W - MARGIN, y_dc + 30], fill=PAPER_DARK,
                outline=RED, width=1)
    bw, _ = banner(d, MARGIN + 5, y_dc + 6, "DATE CHECK", F_SANS_B(11),
                   WHITE, RED)
    f_dc = F_SANS(11)
    dc_lines = wrap_text(d, data["date_check"], f_dc,
                         CONTENT_W - bw - 16)
    draw_lines(d, MARGIN + 5 + bw + 6, y_dc + 3, dc_lines[:2], f_dc, INK, 13)

    # ---- footer ----
    d.line([MARGIN, 974, W - MARGIN, 974], fill=INK, width=2)
    foot1 = ("Every story here happened or was first reported on Tuesday "
             "17 November 2026. Contested claims are marked as claims.")
    d.text((MARGIN, 978), foot1, font=F_SANS_B(11), fill=INK)
    foot2 = ("Sources: Reuters, AP, AFP, BBC, Al Jazeera, WHO, UN. "
             "Original drawings.")
    d.text((MARGIN, 992), foot2, font=F_SANS(10), fill=INK_SOFT)
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
