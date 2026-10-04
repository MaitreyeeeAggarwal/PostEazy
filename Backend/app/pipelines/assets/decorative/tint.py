"""
tint.py
-------
Palette recolouring utilities for PostEazy decorative assets.

Usage:
    from app.pipelines.assets.decorative.tint import tint, tint_to_palette

Functions:
    tint(img, color, preserve_alpha)  → recolors a single-channel icon to a flat colour
    tint_to_palette(img, palette)     → maps dominant hue regions to brand palette colors
    load_tinted(path, color)          → load + tint in one call, returns RGBA Image
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


# ---------------------------------------------------------------------------
# Brand palette (locked)
# ---------------------------------------------------------------------------

PALETTE = {
    "bg":       (15, 15, 20),
    "purple":   (124, 92, 255),
    "gold":     (255, 216, 77),
    "light":    (245, 245, 247),
    "white":    (255, 255, 255),
}


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Converts #RRGGBB hex string to RGB tuple."""
    clean = hex_str.lstrip("#")
    if len(clean) == 6:
        return tuple(int(clean[i:i + 2], 16) for i in (0, 2, 4))
    return (255, 255, 255)


def tint(img: Image.Image, color: tuple[int, int, int], preserve_alpha: bool = True) -> Image.Image:
    """
    Recolors a single-colour icon/shape to `color`.

    Converts the image to greyscale luminance, then maps luminance to the
    target colour, preserving the original alpha channel.

    Args:
        img:            Source RGBA PIL image.
        color:          Target RGB tuple, e.g. (124, 92, 255).
        preserve_alpha: If True, keep original alpha; else set alpha = luminance.

    Returns:
        Recolored RGBA PIL image.
    """
    img = img.convert("RGBA")
    arr = np.array(img, dtype=np.float32)  # (H, W, 4)

    r, g, b = color
    lum = arr[:, :, 0] * 0.299 + arr[:, :, 1] * 0.587 + arr[:, :, 2] * 0.114
    lum_n = lum / 255.0  # 0..1

    out = np.zeros_like(arr)
    out[:, :, 0] = r * lum_n
    out[:, :, 1] = g * lum_n
    out[:, :, 2] = b * lum_n
    out[:, :, 3] = arr[:, :, 3] if preserve_alpha else lum

    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


def tint_hex(img: Image.Image, hex_color: str, preserve_alpha: bool = True) -> Image.Image:
    """Convenience wrapper: accepts a hex color string."""
    return tint(img, hex_to_rgb(hex_color), preserve_alpha)


def load_tinted(
    path: str | Path,
    color: tuple[int, int, int] | str,
    size: tuple[int, int] | None = None,
) -> Image.Image:
    """
    Load a PNG asset, apply a tint, and optionally resize.

    Args:
        path:   Absolute or relative path to the PNG.
        color:  RGB tuple or hex string.
        size:   Optional (width, height) to resize to after tinting.

    Returns:
        RGBA PIL Image ready to composite onto a frame.
    """
    img = Image.open(path).convert("RGBA")
    if isinstance(color, str):
        color = hex_to_rgb(color)
    img = tint(img, color)
    if size:
        img = img.resize(size, Image.Resampling.LANCZOS)
    return img


def apply_opacity(img: Image.Image, opacity: float) -> Image.Image:
    """Scales the alpha channel by `opacity` (0.0–1.0)."""
    img = img.convert("RGBA")
    arr = np.array(img, dtype=np.float32)
    arr[:, :, 3] *= max(0.0, min(1.0, opacity))
    return Image.fromarray(arr.astype(np.uint8), "RGBA")
