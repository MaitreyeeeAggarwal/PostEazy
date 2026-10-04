"""Shared decorative-asset selection for presentation renderers."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.pipelines.assets.decorative import AssetPicker


PRESENTATION_TO_ASSET_THEME = {
    "bold_tech": "techy",
    "minimalist_editorial": "elegant",
    "neon_cyberpunk": "bold",
    "warm_corporate": "professional",
}


@dataclass(frozen=True)
class SlideDecorations:
    frame: Optional[Path] = None
    sticker: Optional[Path] = None
    stickers: tuple[Path, ...] = ()
    accent: Optional[Path] = None


def get_slide_decorations(theme_key: str, slide_idx: int) -> SlideDecorations:
    """Pick a stable, restrained decoration set for one presentation slide."""
    picker = AssetPicker(seed=slide_idx)
    if not picker._manifest:
        return SlideDecorations()

    asset_theme = PRESENTATION_TO_ASSET_THEME.get(theme_key, "professional")
    assets = picker.pick_for_theme(asset_theme, reseed=slide_idx)

    def first_path(category: str, require_tone_fallback: bool = False) -> Optional[Path]:
        entries = assets.get(category, [])
        # Theme presets use energy filters. A theme can have relevant assets but
        # no asset at that exact energy, which previously left slides bare.
        if not entries and require_tone_fallback:
            entries = picker.pick(category, tone=asset_theme, k=1)
        if not entries:
            return None
        path = picker.get_full_path(entries[0])
        return path if path.exists() else None

    sticker_entries = picker.pick("stickers", tone=asset_theme, k=3)
    sticker_paths = tuple(
        path for entry in sticker_entries
        if (path := picker.get_full_path(entry)).exists()
    )

    return SlideDecorations(
        frame=first_path("frames", require_tone_fallback=True),
        sticker=sticker_paths[0] if sticker_paths else first_path("stickers", require_tone_fallback=True),
        stickers=sticker_paths,
        accent=(
            first_path("handdrawn", require_tone_fallback=True)
            or first_path("blobs", require_tone_fallback=True)
        ),
    )


def asset_data_uri(path: Optional[Path]) -> str:
    """Embed an asset so exported HTML remains self-contained."""
    if not path or not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
