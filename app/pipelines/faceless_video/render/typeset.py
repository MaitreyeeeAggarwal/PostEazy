from pathlib import Path
from PIL import ImageFont


_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def load_font(font_size: int, font_path: str = "") -> ImageFont.FreeTypeFont:
    """Loads and caches TrueType fonts."""
    cache_key = (font_path, font_size)
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]

    try:
        if font_path and Path(font_path).exists():
            font = ImageFont.truetype(font_path, font_size)
        else:
            # Fallback to standard system fonts (Arial, Segoe UI, DejaVuSans)
            font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    _FONT_CACHE[cache_key] = font
    return font


def fit_text_size(text: str, max_width: int, max_height: int, min_size: int = 24, max_size: int = 340, font_path: str = "") -> int:
    """Binary search solver to find the largest font size fitting within bounds."""
    low = min_size
    high = max_size
    best_size = min_size

    for _ in range(12):  # 12 iterations for exact precision
        mid = (low + high) // 2
        font = load_font(mid, font_path)
        bbox = font.getbbox(text)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        if w <= max_width and h <= max_height:
            best_size = mid
            low = mid + 1
        else:
            high = mid - 1

    return best_size
