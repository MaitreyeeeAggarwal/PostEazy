"""
seed_assets.py
==============
Procedurally generates the starter decorative asset pack for PostEazy.
Run once:  python -m app.pipelines.assets.decorative.seed_assets

Outputs (all 512 x 512 RGBA PNGs):
  stickers/  — 15 icon-style shapes (sparkle, lightning, arrow, star, etc.)
  shapes/    — 8 organic blobs + 4 gradient mesh backgrounds (1080x1920)
  textures/  — noise grain + halftone dot grid
  frames/    — 3 corner bracket sets + 2 terminal window frames
  handdrawn/ — 5 arrows + 3 underlines + 3 squiggles (vector-style)

No external API keys or internet access required.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# ---------------------------------------------------------------------------
# Palette (locked brand colours)
# ---------------------------------------------------------------------------
BG_COLOR       = (15, 15, 20)
ACCENT_PURPLE  = (124, 92, 255)
HIGHLIGHT_GOLD = (255, 216, 77)
TEXT_LIGHT     = (245, 245, 247)

PALETTE = {
    "purple": ACCENT_PURPLE,
    "gold":   HIGHLIGHT_GOLD,
    "light":  TEXT_LIGHT,
    "white":  (255, 255, 255),
}

HERE = Path(__file__).parent
SIZES = {
    "stickers":  512,
    "shapes":    512,
    "textures":  512,
    "frames":    512,
    "handdrawn": 512,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _blank(size: int = 512) -> Image.Image:
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def _save(img: Image.Image, folder: str, name: str) -> Path:
    out = HERE / folder / name
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    print(f"  [seed] {out.relative_to(HERE.parent.parent.parent.parent.parent)}")
    return out


# ---------------------------------------------------------------------------
# 1. STICKERS — icon-style vector art (15 shapes)
# ---------------------------------------------------------------------------

def _draw_sparkle(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    """4-pointed star / sparkle."""
    pts = []
    for i in range(8):
        angle = math.pi * i / 4 - math.pi / 4
        radius = r if i % 2 == 0 else r * 0.38
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    draw.polygon(pts, fill=(*color, 255))


def _draw_lightning(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    """Thick lightning bolt."""
    w = int(r * 0.55)
    pts = [
        (cx + w // 2, cy - r),
        (cx - w // 3, cy - r // 6),
        (cx + w // 4, cy - r // 6),
        (cx - w // 2, cy + r),
        (cx + w // 3, cy + r // 6),
        (cx - w // 4, cy + r // 6),
    ]
    draw.polygon(pts, fill=(*color, 255))


def _draw_arrow_up_right(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    """Diagonal arrow pointing up-right (thick)."""
    t = max(4, r // 6)
    # Shaft
    draw.line([(cx - r * 0.55, cy + r * 0.55), (cx + r * 0.55, cy - r * 0.55)], fill=(*color, 255), width=t * 2)
    # Head
    head = [
        (cx + r * 0.55, cy - r * 0.55),
        (cx + r * 0.10, cy - r * 0.55),
        (cx + r * 0.55, cy - r * 0.10),
    ]
    draw.polygon(head, fill=(*color, 255))


def _draw_star_four(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    """4-pointed star with thin elongated points."""
    pts = []
    for i in range(8):
        angle = math.pi * i / 4
        radius = r if i % 2 == 0 else r * 0.15
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    draw.polygon(pts, fill=(*color, 255))


def _draw_circle_ring(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    """Thick ring."""
    t = max(8, r // 5)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*color, 255), width=t)


def _draw_plus(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    t = max(4, r // 4)
    draw.rectangle([cx - t, cy - r, cx + t, cy + r], fill=(*color, 255))
    draw.rectangle([cx - r, cy - t, cx + r, cy + t], fill=(*color, 255))


def _draw_asterisk(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    t = max(3, r // 7)
    for angle in [0, 60, 120]:
        rad = math.radians(angle)
        x1 = cx + r * math.cos(rad)
        y1 = cy + r * math.sin(rad)
        x2 = cx - r * math.cos(rad)
        y2 = cy - r * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=(*color, 255), width=t * 2)


def _draw_target(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    t = max(3, r // 8)
    for factor in [1.0, 0.65, 0.30]:
        rr = int(r * factor)
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(*color, 255), width=t)
    draw.line([(cx - r * 1.1, cy), (cx + r * 1.1, cy)], fill=(*color, 255), width=t)
    draw.line([(cx, cy - r * 1.1), (cx, cy + r * 1.1)], fill=(*color, 255), width=t)


def _draw_cursor(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    """Arrow cursor shape."""
    pts = [
        (cx - r * 0.1, cy - r),
        (cx - r * 0.1, cy + r * 0.40),
        (cx + r * 0.20, cy + r * 0.10),
        (cx + r * 0.50, cy + r),
        (cx + r * 0.65, cy + r * 0.85),
        (cx + r * 0.35, cy + r * 0.05),
        (cx + r * 0.55, cy - r * 0.10),
    ]
    draw.polygon(pts, fill=(*color, 255))


def _draw_rocket(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    """Simple rocket silhouette pointing up."""
    body = [
        (cx, cy - r),
        (cx + r * 0.38, cy + r * 0.20),
        (cx + r * 0.22, cy + r * 0.20),
        (cx + r * 0.22, cy + r * 0.60),
        (cx - r * 0.22, cy + r * 0.60),
        (cx - r * 0.22, cy + r * 0.20),
        (cx - r * 0.38, cy + r * 0.20),
    ]
    draw.polygon(body, fill=(*color, 255))
    # Fins
    draw.polygon([(cx + r * 0.22, cy + r * 0.35), (cx + r * 0.55, cy + r * 0.65), (cx + r * 0.22, cy + r * 0.60)], fill=(*color, 200))
    draw.polygon([(cx - r * 0.22, cy + r * 0.35), (cx - r * 0.55, cy + r * 0.65), (cx - r * 0.22, cy + r * 0.60)], fill=(*color, 200))


def _draw_brain(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    """Simplified brain outline using ellipses."""
    t = max(4, r // 6)
    draw.ellipse([cx - r, cy - r * 0.7, cx, cy + r * 0.7], outline=(*color, 255), width=t)
    draw.ellipse([cx, cy - r * 0.7, cx + r, cy + r * 0.7], outline=(*color, 255), width=t)
    draw.line([(cx, cy - r * 0.3), (cx, cy + r * 0.3)], fill=(*color, 255), width=t)


def _draw_code_brackets(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    """< /> code symbol."""
    t = max(3, r // 8)
    gap = int(r * 0.25)
    # Left <
    lx = cx - gap - int(r * 0.5)
    for sign in [-1, 1]:
        draw.line([(lx + int(r * 0.35), cy + sign * int(r * 0.5)), (lx, cy)], fill=(*color, 255), width=t)
    # Right >
    rx = cx + gap + int(r * 0.15)
    for sign in [-1, 1]:
        draw.line([(rx, cy + sign * int(r * 0.5)), (rx + int(r * 0.35), cy)], fill=(*color, 255), width=t)
    # Slash /
    draw.line([(cx - int(r * 0.08), cy + int(r * 0.5)), (cx + int(r * 0.08), cy - int(r * 0.5))], fill=(*color, 255), width=t)


def _draw_chart_up(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    """Rising bar chart silhouette."""
    t = max(3, r // 7)
    bars = [0.35, 0.60, 0.80, 1.00]
    bw = int(r * 0.28)
    for i, h in enumerate(bars):
        bx = cx - r + int(i * r * 0.6)
        by_top = cy + r - int(h * r * 1.8)
        draw.rectangle([bx, by_top, bx + bw, cy + r], fill=(*color, 255))
    draw.line([(cx - r, cy + r), (cx + r, cy + r)], fill=(*color, 255), width=t)


def _draw_terminal(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    """Terminal prompt symbol."""
    t = max(3, r // 7)
    # Prompt >
    draw.line([(cx - r * 0.4, cy - r * 0.4), (cx, cy)], fill=(*color, 255), width=t * 2)
    draw.line([(cx, cy), (cx - r * 0.4, cy + r * 0.4)], fill=(*color, 255), width=t * 2)
    # Cursor bar
    draw.rectangle([cx + r * 0.1, cy - r * 0.1, cx + r * 0.65, cy + r * 0.1], fill=(*color, 255))


STICKER_DRAWERS = [
    ("sparkle_purple",    _draw_sparkle,        "purple"),
    ("sparkle_gold",      _draw_sparkle,        "gold"),
    ("lightning_purple",  _draw_lightning,      "purple"),
    ("lightning_gold",    _draw_lightning,      "gold"),
    ("arrow_up_right",    _draw_arrow_up_right, "light"),
    ("star_four_purple",  _draw_star_four,      "purple"),
    ("star_four_gold",    _draw_star_four,      "gold"),
    ("circle_ring",       _draw_circle_ring,    "purple"),
    ("plus",              _draw_plus,           "light"),
    ("asterisk",          _draw_asterisk,       "gold"),
    ("target",            _draw_target,         "purple"),
    ("cursor",            _draw_cursor,         "light"),
    ("rocket",            _draw_rocket,         "gold"),
    ("brain",             _draw_brain,          "purple"),
    ("chart_up",          _draw_chart_up,       "gold"),
    ("code_brackets",     _draw_code_brackets,  "light"),
    ("terminal",          _draw_terminal,       "purple"),
]


def generate_stickers():
    print("\n[seed] Generating stickers...")
    for name, drawer, color_key in STICKER_DRAWERS:
        img = _blank(512)
        draw = ImageDraw.Draw(img)
        color = PALETTE[color_key]
        drawer(draw, 256, 256, 200, color)
        # Slight glow via blur + composite
        glow = img.filter(ImageFilter.GaussianBlur(radius=8))
        img = Image.alpha_composite(glow, img)
        _save(img, "stickers", f"{name}.png")


# ---------------------------------------------------------------------------
# 2. SHAPES — organic blobs + gradient backgrounds
# ---------------------------------------------------------------------------

def _random_blob(size: int, color: tuple, seed: int, complexity: int = 6) -> Image.Image:
    """Draws a smooth organic blob using a polar coordinate spline approach."""
    rng = random.Random(seed)
    cx, cy = size // 2, size // 2
    r_base = size * 0.38

    # Generate radii at N control points and interpolate
    n_pts = complexity * 2
    angles_ctrl = [2 * math.pi * i / n_pts for i in range(n_pts)]
    radii_ctrl  = [r_base * rng.uniform(0.72, 1.28) for _ in range(n_pts)]

    # Smooth by re-sampling at 360 steps using linear interpolation
    pts = []
    for step in range(360):
        angle = 2 * math.pi * step / 360
        # Find surrounding control points
        frac = (angle / (2 * math.pi)) * n_pts
        lo = int(frac) % n_pts
        hi = (lo + 1) % n_pts
        t_lerp = frac - int(frac)
        r = radii_ctrl[lo] * (1 - t_lerp) + radii_ctrl[hi] * t_lerp
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.polygon(pts, fill=(*color, 210))
    # Soft edge
    img = img.filter(ImageFilter.GaussianBlur(radius=6))
    return img


def generate_shapes():
    print("\n[seed] Generating shapes/blobs...")
    blob_configs = [
        ("blob_purple_1", ACCENT_PURPLE, 1),
        ("blob_purple_2", ACCENT_PURPLE, 2),
        ("blob_gold_1",   HIGHLIGHT_GOLD, 3),
        ("blob_gold_2",   HIGHLIGHT_GOLD, 4),
        ("blob_light_1",  TEXT_LIGHT, 5),
        ("blob_light_2",  TEXT_LIGHT, 6),
        ("blob_purple_3", (160, 100, 255), 7),
        ("blob_gold_3",   (255, 190, 50), 8),
    ]
    for name, color, seed in blob_configs:
        img = _random_blob(512, color, seed=seed, complexity=6)
        _save(img, "shapes", f"{name}.png")

    # Gradient mesh backgrounds (1080x1920)
    print("\n[seed] Generating gradient backgrounds...")
    bg_configs = [
        ("bg_mesh_purple", [(15, 15, 20), (40, 20, 80), (124, 92, 255)]),
        ("bg_mesh_gold",   [(15, 15, 20), (50, 30, 5), (180, 130, 30)]),
        ("bg_mesh_teal",   [(10, 30, 30), (15, 60, 60), (30, 180, 150)]),
        ("bg_mesh_dark",   [(5, 5, 10), (20, 10, 40), (80, 50, 180)]),
    ]
    for name, colors in bg_configs:
        img = Image.new("RGB", (1080, 1920), colors[0])
        arr = np.zeros((1920, 1080, 3), dtype=np.uint8)
        c0 = np.array(colors[0], dtype=float)
        c1 = np.array(colors[1], dtype=float)
        c2 = np.array(colors[2], dtype=float)
        for y in range(1920):
            t = y / 1919
            if t < 0.5:
                col = c0 + (c1 - c0) * (t * 2)
            else:
                col = c1 + (c2 - c1) * ((t - 0.5) * 2)
            arr[y, :, :] = np.clip(col, 0, 255).astype(np.uint8)

        # Radial glow center
        center_x, center_y = 540, 960
        Y, X = np.ogrid[:1920, :1080]
        dist = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
        max_d = math.sqrt(540**2 + 960**2)
        glow = np.clip(1 - dist / max_d, 0, 1)[:, :, np.newaxis] * 0.25
        glow_color = np.array(colors[2], dtype=float) / 255
        arr_f = arr.astype(float) / 255 + glow * glow_color
        arr = np.clip(arr_f * 255, 0, 255).astype(np.uint8)

        img = Image.fromarray(arr, "RGB").convert("RGBA")
        _save(img, "shapes", f"{name}.png")


# ---------------------------------------------------------------------------
# 3. TEXTURES
# ---------------------------------------------------------------------------

def generate_textures():
    print("\n[seed] Generating textures...")

    # Noise grain (512x512, transparent, grey noise)
    rng = np.random.default_rng(42)
    grain_vals = rng.integers(0, 255, (512, 512), dtype=np.uint8)
    alpha_vals = (grain_vals * 0.12).astype(np.uint8)  # 10-15% opacity baked in
    grain_arr = np.stack([grain_vals, grain_vals, grain_vals, alpha_vals], axis=-1)
    grain_img = Image.fromarray(grain_arr, "RGBA")
    _save(grain_img, "textures", "noise_grain.png")

    # Halftone dot grid (512x512, transparent)
    dot_img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dot_img)
    spacing = 20
    dot_r = 2
    dot_alpha = 35  # ~14% opacity
    for y in range(0, 512, spacing):
        for x in range(0, 512, spacing):
            draw.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r],
                         fill=(255, 255, 255, dot_alpha))
    _save(dot_img, "textures", "halftone_dots.png")

    # Diagonal line grid (techy crosshatch)
    line_img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(line_img)
    for i in range(-512, 1024, 28):
        draw.line([(i, 0), (i + 512, 512)], fill=(255, 255, 255, 20), width=1)
    _save(line_img, "textures", "crosshatch_lines.png")


# ---------------------------------------------------------------------------
# 4. FRAMES — corner brackets + terminal windows
# ---------------------------------------------------------------------------

def generate_frames():
    print("\n[seed] Generating frames...")

    def corner_bracket(size: int, color: tuple, thickness: int, bracket_len: int) -> Image.Image:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        m = int(size * 0.06)
        bl = bracket_len
        t = thickness
        c = (*color, 255)
        # Top-left
        draw.rectangle([m, m, m + bl, m + t], fill=c)
        draw.rectangle([m, m, m + t, m + bl], fill=c)
        # Top-right
        draw.rectangle([size - m - bl, m, size - m, m + t], fill=c)
        draw.rectangle([size - m - t, m, size - m, m + bl], fill=c)
        # Bottom-left
        draw.rectangle([m, size - m - t, m + bl, size - m], fill=c)
        draw.rectangle([m, size - m - bl, m + t, size - m], fill=c)
        # Bottom-right
        draw.rectangle([size - m - bl, size - m - t, size - m, size - m], fill=c)
        draw.rectangle([size - m - t, size - m - bl, size - m, size - m], fill=c)
        return img

    _save(corner_bracket(512, ACCENT_PURPLE, 6, 80),   "frames", "corner_bracket_purple.png")
    _save(corner_bracket(512, HIGHLIGHT_GOLD, 6, 80),  "frames", "corner_bracket_gold.png")
    _save(corner_bracket(512, TEXT_LIGHT, 4, 60),      "frames", "corner_bracket_light.png")

    def terminal_frame(size: int, color: tuple) -> Image.Image:
        """macOS-style terminal window chrome."""
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        c = (*color, 200)
        m = int(size * 0.05)
        t = 3
        # Outer rounded rect
        draw.rounded_rectangle([m, m, size - m, size - m], radius=18, outline=c, width=t)
        # Title bar line
        bar_y = m + int(size * 0.10)
        draw.line([(m, bar_y), (size - m, bar_y)], fill=c, width=t)
        # Traffic-light dots
        for i, dot_color in enumerate([(255, 95, 87), (255, 189, 46), (39, 201, 63)]):
            dx = m + 22 + i * 22
            dy = m + int(size * 0.05)
            draw.ellipse([dx - 7, dy - 7, dx + 7, dy + 7], fill=(*dot_color, 200))
        return img

    _save(terminal_frame(512, ACCENT_PURPLE), "frames", "terminal_frame_purple.png")
    _save(terminal_frame(512, HIGHLIGHT_GOLD), "frames", "terminal_frame_gold.png")

    def viewfinder_frame(size: int, color: tuple) -> Image.Image:
        """Camera viewfinder / targeting reticle."""
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        c = (*color, 220)
        cx, cy = size // 2, size // 2
        r = int(size * 0.38)
        t = 3
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=t)
        # Cross-hairs (with gap)
        gap = int(r * 0.35)
        draw.line([(cx - r - 20, cy), (cx - gap, cy)], fill=c, width=t)
        draw.line([(cx + gap, cy), (cx + r + 20, cy)], fill=c, width=t)
        draw.line([(cx, cy - r - 20), (cx, cy - gap)], fill=c, width=t)
        draw.line([(cx, cy + gap), (cx, cy + r + 20)], fill=c, width=t)
        # Corner ticks on circle
        for angle_deg in [0, 90, 180, 270]:
            a = math.radians(angle_deg)
            x = cx + r * math.cos(a)
            y = cy + r * math.sin(a)
            draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=c)
        return img

    _save(viewfinder_frame(512, ACCENT_PURPLE), "frames", "viewfinder_purple.png")
    _save(viewfinder_frame(512, HIGHLIGHT_GOLD), "frames", "viewfinder_gold.png")


# ---------------------------------------------------------------------------
# 5. HAND-DRAWN — arrows, underlines, squiggles
# ---------------------------------------------------------------------------

def _wavy_line(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, wave_amp: int,
               wave_freq: float, color: tuple, width: int):
    """Draws a wavy horizontal line simulating a hand-drawn stroke."""
    steps = abs(x1 - x0)
    pts = []
    for i in range(steps + 1):
        t = i / max(steps, 1)
        x = x0 + (x1 - x0) * t
        y = y0 + wave_amp * math.sin(wave_freq * 2 * math.pi * t)
        pts.append((x, y))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=(*color, 255), width=width)


def _arrow_head(draw: ImageDraw.ImageDraw, x: int, y: int, angle_deg: float,
                size: int, color: tuple):
    a = math.radians(angle_deg)
    pts = [
        (x, y),
        (x - size * math.cos(a - math.radians(30)), y - size * math.sin(a - math.radians(30))),
        (x - size * math.cos(a + math.radians(30)), y - size * math.sin(a + math.radians(30))),
    ]
    draw.polygon(pts, fill=(*color, 255))


def generate_handdrawn():
    print("\n[seed] Generating hand-drawn elements...")

    # 5 Curved arrows
    arrow_configs = [
        ("arrow_right_curve",   0),
        ("arrow_down_curve",    90),
        ("arrow_up_curve",      270),
        ("arrow_diagonal",      45),
        ("arrow_swoosh",        -20),
    ]
    for name, angle_offset in arrow_configs:
        img = _blank(512)
        draw = ImageDraw.Draw(img)
        cx, cy = 256, 256
        # Draw wavy shaft
        _wavy_line(draw, cx - 170, cy, cx + 120, 30, 1.5 + angle_offset / 200,
                   HIGHLIGHT_GOLD, width=7)
        # Arrow head
        _arrow_head(draw, cx + 120, cy, 0, 28, HIGHLIGHT_GOLD)
        # Slight rotation to vary
        img = img.rotate(angle_offset, expand=False, resample=Image.BICUBIC)
        _save(img, "handdrawn", f"{name}.png")

    # 3 Underline strokes
    for i in range(1, 4):
        img = _blank(512)
        draw = ImageDraw.Draw(img)
        amp = [12, 8, 18][i - 1]
        freq = [1.0, 2.0, 0.8][i - 1]
        _wavy_line(draw, 40, 256, 472, amp, freq, HIGHLIGHT_GOLD, width=9)
        _save(img, "handdrawn", f"underline_{i}.png")

    # 3 Squiggles / scribble circles
    for i in range(1, 4):
        img = _blank(512)
        draw = ImageDraw.Draw(img)
        cx, cy = 256, 256
        r_base = 160 + i * 15
        pts = []
        rng = random.Random(i * 77)
        for step in range(361):
            a = math.radians(step)
            jitter = rng.uniform(-12, 12)
            r = r_base + jitter
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        for j in range(len(pts) - 1):
            draw.line([pts[j], pts[j + 1]], fill=(*ACCENT_PURPLE, 220), width=6)
        _save(img, "handdrawn", f"scribble_circle_{i}.png")


# ---------------------------------------------------------------------------
# 6. BUILD MANIFEST
# ---------------------------------------------------------------------------

def build_manifest():
    print("\n[seed] Building manifest.json...")

    VALID_TONES = {"professional", "fun", "bold", "minimal", "techy", "elegant"}
    VALID_ENERGIES = {"low", "medium", "high"}
    VALID_PLACEMENTS = {"corner", "underline", "background", "highlight", "frame", "accent"}

    # Pre-assigned tags for procedurally generated assets
    PRESET_TAGS: dict[str, dict] = {
        # Stickers
        "sparkle_purple": {"tone": ["fun", "bold"], "energy": "high", "placement": ["corner", "accent"], "recolorable": True},
        "sparkle_gold":   {"tone": ["fun", "bold"], "energy": "high", "placement": ["corner", "accent"], "recolorable": True},
        "lightning_purple": {"tone": ["bold", "techy"], "energy": "high", "placement": ["accent"], "recolorable": True},
        "lightning_gold":   {"tone": ["bold", "fun"], "energy": "high", "placement": ["accent"], "recolorable": True},
        "arrow_up_right": {"tone": ["professional", "minimal"], "energy": "medium", "placement": ["corner", "accent"], "recolorable": True},
        "star_four_purple": {"tone": ["fun", "elegant"], "energy": "high", "placement": ["accent"], "recolorable": True},
        "star_four_gold":   {"tone": ["fun", "elegant"], "energy": "high", "placement": ["accent"], "recolorable": True},
        "circle_ring": {"tone": ["minimal", "elegant"], "energy": "low", "placement": ["highlight", "accent"], "recolorable": True},
        "plus": {"tone": ["minimal", "techy"], "energy": "low", "placement": ["corner", "accent"], "recolorable": True},
        "asterisk": {"tone": ["fun", "bold"], "energy": "medium", "placement": ["accent"], "recolorable": True},
        "target": {"tone": ["techy", "professional"], "energy": "medium", "placement": ["accent", "corner"], "recolorable": True},
        "cursor": {"tone": ["techy", "minimal"], "energy": "medium", "placement": ["accent"], "recolorable": True},
        "rocket": {"tone": ["fun", "bold"], "energy": "high", "placement": ["accent", "corner"], "recolorable": True},
        "brain": {"tone": ["techy", "professional"], "energy": "medium", "placement": ["accent"], "recolorable": True},
        "chart_up": {"tone": ["professional", "bold"], "energy": "high", "placement": ["accent"], "recolorable": True},
        "code_brackets": {"tone": ["techy", "minimal"], "energy": "medium", "placement": ["accent", "frame"], "recolorable": True},
        "terminal": {"tone": ["techy", "minimal"], "energy": "medium", "placement": ["accent"], "recolorable": True},
        # Shapes
        "blob_purple_1": {"tone": ["bold", "elegant"], "energy": "low", "placement": ["background", "accent"], "recolorable": True},
        "blob_purple_2": {"tone": ["bold", "elegant"], "energy": "low", "placement": ["background", "accent"], "recolorable": True},
        "blob_purple_3": {"tone": ["elegant", "fun"], "energy": "medium", "placement": ["background"], "recolorable": True},
        "blob_gold_1": {"tone": ["bold", "fun"], "energy": "medium", "placement": ["background", "accent"], "recolorable": True},
        "blob_gold_2": {"tone": ["bold", "fun"], "energy": "medium", "placement": ["background", "accent"], "recolorable": True},
        "blob_gold_3": {"tone": ["fun", "elegant"], "energy": "medium", "placement": ["background"], "recolorable": True},
        "blob_light_1": {"tone": ["minimal", "elegant"], "energy": "low", "placement": ["background"], "recolorable": True},
        "blob_light_2": {"tone": ["minimal", "elegant"], "energy": "low", "placement": ["background"], "recolorable": True},
        "bg_mesh_purple": {"tone": ["bold", "techy"], "energy": "medium", "placement": ["background"], "recolorable": False},
        "bg_mesh_gold": {"tone": ["bold", "fun"], "energy": "medium", "placement": ["background"], "recolorable": False},
        "bg_mesh_teal": {"tone": ["minimal", "professional"], "energy": "low", "placement": ["background"], "recolorable": False},
        "bg_mesh_dark": {"tone": ["techy", "elegant"], "energy": "low", "placement": ["background"], "recolorable": False},
        # Textures
        "noise_grain": {"tone": ["professional", "minimal"], "energy": "low", "placement": ["background"], "recolorable": False},
        "halftone_dots": {"tone": ["techy", "minimal"], "energy": "low", "placement": ["background", "accent"], "recolorable": True},
        "crosshatch_lines": {"tone": ["techy", "minimal"], "energy": "low", "placement": ["background"], "recolorable": True},
        # Frames
        "corner_bracket_purple": {"tone": ["techy", "professional"], "energy": "low", "placement": ["frame", "corner"], "recolorable": True},
        "corner_bracket_gold": {"tone": ["bold", "elegant"], "energy": "medium", "placement": ["frame", "corner"], "recolorable": True},
        "corner_bracket_light": {"tone": ["minimal", "professional"], "energy": "low", "placement": ["frame", "corner"], "recolorable": True},
        "terminal_frame_purple": {"tone": ["techy", "bold"], "energy": "medium", "placement": ["frame"], "recolorable": True},
        "terminal_frame_gold": {"tone": ["techy", "fun"], "energy": "medium", "placement": ["frame"], "recolorable": True},
        "viewfinder_purple": {"tone": ["techy", "professional"], "energy": "medium", "placement": ["frame", "accent"], "recolorable": True},
        "viewfinder_gold": {"tone": ["bold", "fun"], "energy": "medium", "placement": ["frame", "accent"], "recolorable": True},
        # Hand-drawn
        "arrow_right_curve": {"tone": ["fun", "bold"], "energy": "high", "placement": ["accent", "highlight"], "recolorable": True},
        "arrow_down_curve":  {"tone": ["fun", "bold"], "energy": "high", "placement": ["accent"], "recolorable": True},
        "arrow_up_curve":    {"tone": ["fun", "bold"], "energy": "high", "placement": ["accent"], "recolorable": True},
        "arrow_diagonal":    {"tone": ["fun", "bold"], "energy": "high", "placement": ["accent", "corner"], "recolorable": True},
        "arrow_swoosh":      {"tone": ["fun", "elegant"], "energy": "medium", "placement": ["accent", "highlight"], "recolorable": True},
        "underline_1":       {"tone": ["fun", "bold"], "energy": "high", "placement": ["underline", "highlight"], "recolorable": True},
        "underline_2":       {"tone": ["minimal", "professional"], "energy": "medium", "placement": ["underline"], "recolorable": True},
        "underline_3":       {"tone": ["fun", "elegant"], "energy": "high", "placement": ["underline", "highlight"], "recolorable": True},
        "scribble_circle_1": {"tone": ["fun", "bold"], "energy": "high", "placement": ["highlight", "accent"], "recolorable": True},
        "scribble_circle_2": {"tone": ["fun", "minimal"], "energy": "medium", "placement": ["highlight"], "recolorable": True},
        "scribble_circle_3": {"tone": ["fun", "elegant"], "energy": "medium", "placement": ["highlight", "accent"], "recolorable": True},
    }

    manifest = []
    for path in sorted(HERE.rglob("*.png")):
        if path.name.startswith(".") or "manifest" in path.name:
            continue
        rel = path.relative_to(HERE)
        category = rel.parts[0]
        stem = path.stem
        preset = PRESET_TAGS.get(stem, {})
        try:
            w, h = Image.open(path).size
        except Exception:
            w, h = 512, 512

        manifest.append({
            "file": str(rel).replace("\\", "/"),
            "category": category,
            "size": [w, h],
            "tone": preset.get("tone", []),
            "energy": preset.get("energy"),
            "placement": preset.get("placement", []),
            "recolorable": preset.get("recolorable"),
        })

    manifest_path = HERE / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"  [seed] manifest.json -> {len(manifest)} assets")

    # Validate
    errors = 0
    for a in manifest:
        bad_tones = set(a["tone"]) - VALID_TONES
        if bad_tones:
            print(f"  [warn] Bad tone in {a['file']}: {bad_tones}")
            errors += 1
        if a["energy"] and a["energy"] not in VALID_ENERGIES:
            print(f"  [warn] Bad energy in {a['file']}: {a['energy']}")
            errors += 1
        bad_placements = set(a["placement"]) - VALID_PLACEMENTS
        if bad_placements:
            print(f"  [warn] Bad placement in {a['file']}: {bad_placements}")
            errors += 1
    if errors == 0:
        print("  [seed] All tags valid [OK]")

    # Coverage report
    from collections import Counter
    tone_counts = Counter(t for a in manifest for t in a["tone"])
    print(f"\n  [seed] Tone coverage: {dict(tone_counts)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("PostEazy Decorative Asset Seeder")
    print("=" * 60)
    generate_stickers()
    generate_shapes()
    generate_textures()
    generate_frames()
    generate_handdrawn()
    build_manifest()
    print("\n[seed] Done! All assets written to assets/decorative/")


if __name__ == "__main__":
    main()
