import numpy as np
from PIL import Image, ImageDraw


def contrast_ratio(lum1: float, lum2: float) -> float:
    """Calculates WCAG 2.1 contrast ratio between two relative luminance values."""
    l1 = max(lum1, lum2)
    l2 = min(lum1, lum2)
    return (l1 + 0.05) / (l2 + 0.05)


def solve_scrim_alpha(bg_frame: Image.Image, box: tuple[int, int, int, int]) -> float:
    """Calculates minimum scrim opacity (0.0 to 0.8) to reach 4.5:1 contrast over background."""
    x1, y1, x2, y2 = box
    w, h = max(1, x2 - x1), max(1, y2 - y1)
    
    crop_patch = bg_frame.crop((x1, y1, x2, y2)).convert("L").resize((16, 16))
    data = sorted(crop_patch.getdata())
    # 85th percentile luminance to account for bright specular highlights
    lum_85 = data[int(0.85 * len(data))] / 255.0

    # Test alpha values from 0.0 to 0.8
    for a in [i / 20.0 for i in range(0, 17)]:
        eff_lum = lum_85 * (1.0 - a)  # Black scrim overlay
        if contrast_ratio(1.0, eff_lum) >= 4.5:  # White text against effective dark scrim
            return a

    return 0.75  # Default safe scrim fallback


def draw_gradient_scrim(width: int, height: int, box: tuple[int, int, int, int], alpha: float) -> Image.Image:
    """Renders a smooth vertical gradient scrim image layer."""
    scrim = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(scrim)

    x1, y1, x2, y2 = box
    max_a = int(alpha * 255)

    for y in range(y1, y2):
        # Smooth gaussian fade at edges
        dist_center = abs((y - (y1 + y2) / 2) / ((y2 - y1) / 2))
        edge_a = int(max_a * (1.0 - 0.5 * (dist_center ** 2)))
        draw.line([(x1, y), (x2, y)], fill=(0, 0, 0, edge_a))

    return scrim
