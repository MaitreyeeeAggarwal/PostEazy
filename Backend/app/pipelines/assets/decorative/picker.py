"""
picker.py
=========
Vibe/tone-based asset picker for PostEazy decorative elements.

Reads from manifest.json and returns randomised sets of assets
matching a theme, energy level, and placement zone.

Usage:
    from app.pipelines.assets.decorative.picker import AssetPicker

    picker = AssetPicker()
    stickers = picker.pick("stickers", tone="techy", k=2, energy="medium")
    frames   = picker.pick("frames",   tone="professional", placement="frame")
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Literal

from PIL import Image

HERE = Path(__file__).parent
MANIFEST_PATH = HERE / "manifest.json"

# ---------------------------------------------------------------------------
# Valid tag values (must match seed_assets.py)
# ---------------------------------------------------------------------------

ToneType      = Literal["professional", "fun", "bold", "minimal", "techy", "elegant"]
EnergyType    = Literal["low", "medium", "high"]
PlacementType = Literal["corner", "underline", "background", "highlight", "frame", "accent"]
CategoryType  = Literal["stickers", "shapes", "frames", "textures", "handdrawn"]


# ---------------------------------------------------------------------------
# Theme presets → used by the video pipeline
# ---------------------------------------------------------------------------

THEMES: dict[str, dict] = {
    "professional": {
        "tone": "professional",
        "energy": "low",
        "sticker_count": 1,
        "frame_count": 1,
        "blob_count": 1,
        "texture_opacity": 0.08,
        "handdrawn_count": 0,
    },
    "fun": {
        "tone": "fun",
        "energy": "high",
        "sticker_count": 3,
        "frame_count": 0,
        "blob_count": 2,
        "texture_opacity": 0.12,
        "handdrawn_count": 2,
    },
    "bold": {
        "tone": "bold",
        "energy": "high",
        "sticker_count": 2,
        "frame_count": 1,
        "blob_count": 2,
        "texture_opacity": 0.10,
        "handdrawn_count": 1,
    },
    "techy": {
        "tone": "techy",
        "energy": "medium",
        "sticker_count": 2,
        "frame_count": 2,
        "blob_count": 1,
        "texture_opacity": 0.12,
        "handdrawn_count": 0,
    },
    "minimal": {
        "tone": "minimal",
        "energy": "low",
        "sticker_count": 1,
        "frame_count": 1,
        "blob_count": 0,
        "texture_opacity": 0.06,
        "handdrawn_count": 1,
    },
    "elegant": {
        "tone": "elegant",
        "energy": "medium",
        "sticker_count": 2,
        "frame_count": 1,
        "blob_count": 2,
        "texture_opacity": 0.08,
        "handdrawn_count": 1,
    },
}

# Map StyleTemplate keys → theme names
STYLE_TO_THEME: dict[str, str] = {
    "bold_creator": "bold",
    "documentary":  "elegant",
    "news_ticker":  "professional",
    "minimal_dark": "techy",
}


# ---------------------------------------------------------------------------
# Picker class
# ---------------------------------------------------------------------------

class AssetPicker:
    """
    Loads and caches the decorative asset manifest.
    Provides filtered random sampling by tone, energy, and placement.
    """

    def __init__(self, manifest_path: Path | str = MANIFEST_PATH, seed: int | None = None):
        self._rng = random.Random(seed)
        self._manifest: list[dict] = []
        self._load(Path(manifest_path))

    def _load(self, path: Path) -> None:
        if not path.exists():
            print(f"[AssetPicker] manifest.json not found at {path}. Run seed_assets.py first.")
            return
        self._manifest = json.loads(path.read_text())

    def pick(
        self,
        category: CategoryType,
        tone: ToneType | None = None,
        k: int = 1,
        energy: EnergyType | None = None,
        placement: PlacementType | None = None,
        recolorable_only: bool = False,
        exclude_backgrounds: bool = True,
    ) -> list[dict]:
        """
        Returns up to `k` random asset entries matching the given filters.

        Args:
            category:           Asset folder (stickers, shapes, frames, etc.)
            tone:               Vibe tag to filter by. None = no filter.
            k:                  Number of assets to return.
            energy:             Energy level filter. None = no filter.
            placement:          Placement zone filter. None = no filter.
            recolorable_only:   If True, only assets with recolorable=True.
            exclude_backgrounds: If True, skip assets with placement=background only.

        Returns:
            List of manifest dicts (may be fewer than `k` if pool is small).
        """
        pool = [a for a in self._manifest if a["category"] == category]

        if tone:
            pool = [a for a in pool if tone in (a.get("tone") or [])]
        if energy:
            pool = [a for a in pool if a.get("energy") == energy]
        if placement:
            pool = [a for a in pool if placement in (a.get("placement") or [])]
        if recolorable_only:
            pool = [a for a in pool if a.get("recolorable") is True]
        if exclude_backgrounds:
            pool = [
                a for a in pool
                if not (set(a.get("placement") or []) <= {"background"})
            ]

        return self._rng.sample(pool, min(k, len(pool)))

    def pick_for_theme(self, theme_name: str, reseed: int | None = None) -> dict[str, list[dict]]:
        """
        Returns a full decoration set (stickers, frames, blobs, textures, handdrawn)
        for a named theme.  Maps StyleTemplate keys via STYLE_TO_THEME automatically.

        Args:
            theme_name:  One of THEMES keys, or a StyleTemplate key.
            reseed:      Optional int to vary picks while keeping determinism.

        Returns:
            Dict with keys: stickers, frames, blobs, textures, handdrawn
        """
        resolved = STYLE_TO_THEME.get(theme_name, theme_name)
        cfg = THEMES.get(resolved, THEMES["bold"])
        tone = cfg["tone"]

        if reseed is not None:
            self._rng = random.Random(reseed)

        return {
            "stickers":  self.pick("stickers",  tone=tone, k=cfg["sticker_count"],  energy=cfg["energy"]),
            "frames":    self.pick("frames",     tone=tone, k=cfg["frame_count"]),
            "blobs":     self.pick("shapes",     tone=tone, k=cfg["blob_count"]),
            "textures":  self.pick("textures",   k=1, placement="background",         exclude_backgrounds=False),
            "handdrawn": self.pick("handdrawn",  tone=tone, k=cfg["handdrawn_count"], energy=cfg["energy"]),
            "texture_opacity": cfg["texture_opacity"],
        }

    def get_full_path(self, entry: dict) -> Path:
        """Returns absolute path to an asset file."""
        return HERE / entry["file"]

    # ------------------------------------------------------------------
    # Coverage / validation helpers
    # ------------------------------------------------------------------

    def coverage(self) -> dict[str, int]:
        """Returns tone → count mapping across all assets."""
        from collections import Counter
        return dict(Counter(t for a in self._manifest for t in (a.get("tone") or [])))

    def validate(self) -> list[str]:
        """Returns list of warning strings for malformed manifest entries."""
        VALID_TONES = {"professional", "fun", "bold", "minimal", "techy", "elegant"}
        VALID_ENERGIES = {"low", "medium", "high"}
        VALID_PLACEMENTS = {"corner", "underline", "background", "highlight", "frame", "accent"}
        issues = []
        for a in self._manifest:
            f = a["file"]
            bad_t = set(a.get("tone") or []) - VALID_TONES
            if bad_t:
                issues.append(f"Bad tone in {f}: {bad_t}")
            if not a.get("tone"):
                issues.append(f"Unlabeled (no tone): {f}")
            e = a.get("energy")
            if e and e not in VALID_ENERGIES:
                issues.append(f"Bad energy in {f}: {e}")
            bad_p = set(a.get("placement") or []) - VALID_PLACEMENTS
            if bad_p:
                issues.append(f"Bad placement in {f}: {bad_p}")
        return issues
