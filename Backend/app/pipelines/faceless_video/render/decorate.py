"""
decorate.py
===========
Composites decorative assets (stickers, blobs, frames, handdrawn, textures)
onto a rendered video frame using the AssetPicker and tint utilities.

Integrates with render_frame() in render/frames.py.  Call overlay_decoration()
after render_frame() to layer assets on top without modifying core frame logic.

Usage:
    from app.pipelines.faceless_video.render.decorate import overlay_decoration

    frame = render_frame(scene, t, ...)
    frame = overlay_decoration(frame, scene_idx=0, style_key="bold_creator")
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Literal

from PIL import Image

from app.pipelines.assets.decorative.picker import AssetPicker, STYLE_TO_THEME
from app.pipelines.assets.decorative.tint import (
    load_tinted, apply_opacity, tint, PALETTE,
)

# ---------------------------------------------------------------------------
# Safe zones (9:16, 1080×1920) — don't place assets where text lives
# ---------------------------------------------------------------------------

# Each zone: (x_frac, y_frac, w_frac, h_frac) — relative to frame size
SAFE_ZONES: dict[str, tuple[float, float, float, float]] = {
    # Corners — good for stickers / brackets
    "top_left":      (0.00, 0.02, 0.22, 0.18),
    "top_right":     (0.78, 0.02, 0.22, 0.18),
    "bottom_left":   (0.00, 0.80, 0.22, 0.18),
    "bottom_right":  (0.78, 0.80, 0.22, 0.18),
    # Mid-edge bands — good for blobs, underlines
    "mid_left":      (0.00, 0.38, 0.15, 0.24),
    "mid_right":     (0.85, 0.38, 0.15, 0.24),
    # Top bar — above text, good for handdrawn underlines
    "top_bar":       (0.08, 0.18, 0.84, 0.08),
    # Bottom area — below text zone
    "bottom_bar":    (0.08, 0.78, 0.84, 0.08),
}

CORNER_ZONES  = ["top_left", "top_right", "bottom_left", "bottom_right"]
MIDEDGE_ZONES = ["mid_left", "mid_right"]
TOPBAR_ZONES  = ["top_bar"]
BOTTOM_ZONES  = ["bottom_bar"]

# Per-placement zone mapping
PLACEMENT_ZONES: dict[str, list[str]] = {
    "corner":     CORNER_ZONES,
    "accent":     CORNER_ZONES + MIDEDGE_ZONES,
    "highlight":  TOPBAR_ZONES + BOTTOM_ZONES,
    "underline":  TOPBAR_ZONES + BOTTOM_ZONES,
    "frame":      CORNER_ZONES,
    "background": [],  # handled separately (full-frame blend)
}

# Sticker target sizes in pixels (512 source → scaled down)
ASSET_SIZES: dict[str, int] = {
    "stickers":  140,
    "handdrawn": 180,
    "frames":    480,  # corner brackets fill most of the 1080-wide frame
    "blobs":     300,
    "textures":  None,  # full-frame, see below
}

# ---------------------------------------------------------------------------
# Module-level picker (lazy singleton, one instance per process)
# ---------------------------------------------------------------------------

_picker: AssetPicker | None = None
_rng = random.Random()


def _get_picker() -> AssetPicker:
    global _picker
    if _picker is None:
        _picker = AssetPicker()
    return _picker


# ---------------------------------------------------------------------------
# Placement helpers
# ---------------------------------------------------------------------------

def _resolve_pos(
    zone_name: str,
    asset_w: int,
    asset_h: int,
    frame_w: int,
    frame_h: int,
) -> tuple[int, int]:
    """Returns (x, y) top-left pixel position for an asset in the given zone."""
    xf, yf, wf, hf = SAFE_ZONES[zone_name]
    zone_x = int(xf * frame_w)
    zone_y = int(yf * frame_h)
    zone_w = int(wf * frame_w)
    zone_h = int(hf * frame_h)

    # Centre within zone, with small random jitter (±15% of zone)
    jitter_x = int(_rng.uniform(-0.15, 0.15) * zone_w)
    jitter_y = int(_rng.uniform(-0.15, 0.15) * zone_h)

    x = zone_x + (zone_w - asset_w) // 2 + jitter_x
    y = zone_y + (zone_h - asset_h) // 2 + jitter_y

    # Clamp to frame bounds
    x = max(0, min(frame_w - asset_w, x))
    y = max(0, min(frame_h - asset_h, y))
    return x, y


def _pick_zone(placement: str, used_zones: set[str]) -> str | None:
    """Pick an unused zone for a placement type, else return None."""
    candidates = [z for z in PLACEMENT_ZONES.get(placement, CORNER_ZONES) if z not in used_zones]
    if not candidates:
        return None
    return _rng.choice(candidates)


def _pick_tint_color(entry: dict) -> tuple[int, int, int]:
    """Choose a tint colour based on asset tones."""
    tones = entry.get("tone") or []
    if "gold" in tones or "fun" in tones or "bold" in tones:
        return PALETTE["gold"]
    if "professional" in tones or "minimal" in tones:
        return PALETTE["light"]
    return PALETTE["purple"]


def _semantic_stickers(picker: AssetPicker, context: str, count: int) -> list[dict]:
    """Use sticker semantics that reinforce the current narration when possible."""
    text = (context or "").lower()
    if any(word in text for word in ("data", "ai", "automation", "software", "code", "system")):
        preferred = ("brain", "code_brackets", "terminal")
    elif any(word in text for word in ("growth", "revenue", "metric", "sales", "increase", "%", "performance")):
        preferred = ("chart_up", "arrow_up_right", "target")
    elif any(word in text for word in ("launch", "start", "build", "next", "action", "roadmap")):
        preferred = ("rocket", "target", "arrow_up_right")
    elif any(word in text for word in ("risk", "challenge", "delay", "problem", "warning")):
        preferred = ("lightning", "target", "circle_ring")
    else:
        return []

    matches: list[dict] = []
    stickers = [entry for entry in picker._manifest if entry.get("category") == "stickers"]
    for token in preferred:
        entry = next((candidate for candidate in stickers if token in candidate.get("file", "")), None)
        if entry and entry not in matches:
            matches.append(entry)
    return matches[:count]


# ---------------------------------------------------------------------------
# Main compositing function
# ---------------------------------------------------------------------------

def overlay_decoration(
    frame: Image.Image,
    scene_idx: int,
    style_key: str = "bold_creator",
    scene_fade: float = 1.0,
    rotation_deg: float = 0.0,
    scene_context: str = "",
    enabled: bool = True,
) -> Image.Image:
    """
    Composites decorative assets onto a rendered RGBA frame.

    Args:
        frame:          The output of render_frame() — RGBA PIL Image.
        scene_idx:      Scene index, used to vary asset picks per scene.
        style_key:      StyleTemplate key (e.g. "bold_creator", "minimal_dark").
                        Automatically maps to a decoration theme.
        scene_fade:     Opacity multiplier matching the scene's fade in/out.
                        Pass the same value computed in render_frame().
        rotation_deg:   Optional overall rotation offset (subtle tilt on stickers).
        scene_context:  Narration/background cue used to choose topical stickers.
        enabled:        Master switch; if False, returns frame unchanged.

    Returns:
        Composited RGBA PIL Image.
    """
    if not enabled:
        return frame

    picker = _get_picker()
    if not picker._manifest:
        return frame  # No assets seeded yet; skip gracefully

    frame_w, frame_h = frame.size
    _rng.seed(scene_idx * 1337)  # deterministic per scene

    assets = picker.pick_for_theme(style_key, reseed=scene_idx)
    topical_stickers = _semantic_stickers(picker, scene_context, len(assets.get("stickers", [])))
    if topical_stickers:
        assets["stickers"] = topical_stickers
    used_zones: set[str] = set()

    # -----------------------------------------------------------------------
    # A. Full-frame texture overlay
    # -----------------------------------------------------------------------
    if assets.get("textures"):
        tex_entry = assets["textures"][0]
        tex_path = picker.get_full_path(tex_entry)
        if tex_path.exists():
            try:
                tex = Image.open(tex_path).convert("RGBA")
                tex = tex.resize((frame_w, frame_h), Image.Resampling.NEAREST)
                opacity = assets.get("texture_opacity", 0.10) * scene_fade
                tex = apply_opacity(tex, opacity)
                frame = Image.alpha_composite(frame, tex)
            except Exception as e:
                print(f"[decorate] texture error: {e}")

    # -----------------------------------------------------------------------
    # B. Blob shapes (soft corner accents, low opacity)
    # -----------------------------------------------------------------------
    for blob_entry in assets.get("blobs", []):
        blob_path = picker.get_full_path(blob_entry)
        if not blob_path.exists():
            continue
        try:
            blob_sz = ASSET_SIZES["blobs"]
            color = _pick_tint_color(blob_entry)
            blob = load_tinted(blob_path, color, size=(blob_sz, blob_sz))
            blob = apply_opacity(blob, 0.22 * scene_fade)

            # Blobs go in mid-edge zones to avoid text
            placements = blob_entry.get("placement") or ["accent"]
            zone = _pick_zone(placements[0], used_zones)
            if zone is None:
                zone = _rng.choice(MIDEDGE_ZONES)
            used_zones.add(zone)

            # Slight random rotation for organic feel
            angle = _rng.uniform(-25, 25) + rotation_deg
            blob = blob.rotate(angle, expand=True, resample=Image.BICUBIC)

            x, y = _resolve_pos(zone, blob.width, blob.height, frame_w, frame_h)
            frame.paste(blob, (x, y), blob)
        except Exception as e:
            print(f"[decorate] blob error: {e}")

    # -----------------------------------------------------------------------
    # C. Full-frame corner bracket frames
    # -----------------------------------------------------------------------
    for frame_entry in assets.get("frames", []):
        asset_path = picker.get_full_path(frame_entry)
        if not asset_path.exists():
            continue
        try:
            color = _pick_tint_color(frame_entry)
            overlay = load_tinted(asset_path, color, size=(frame_w, frame_h))
            overlay = apply_opacity(overlay, 0.75 * scene_fade)
            frame = Image.alpha_composite(frame, overlay)
        except Exception as e:
            print(f"[decorate] frame error: {e}")

    # -----------------------------------------------------------------------
    # D. Sticker icons (corner / accent zones)
    # -----------------------------------------------------------------------
    for sticker_entry in assets.get("stickers", []):
        sticker_path = picker.get_full_path(sticker_entry)
        if not sticker_path.exists():
            continue
        try:
            sz = ASSET_SIZES["stickers"]
            color = _pick_tint_color(sticker_entry)
            sticker = load_tinted(sticker_path, color, size=(sz, sz))
            sticker = apply_opacity(sticker, 0.88 * scene_fade)

            angle = _rng.uniform(-18, 18) + rotation_deg
            sticker = sticker.rotate(angle, expand=True, resample=Image.BICUBIC)

            placements = sticker_entry.get("placement") or ["accent"]
            zone = _pick_zone(placements[0], used_zones)
            if zone is None:
                zone = _rng.choice(CORNER_ZONES)
            used_zones.add(zone)

            x, y = _resolve_pos(zone, sticker.width, sticker.height, frame_w, frame_h)
            frame.paste(sticker, (x, y), sticker)
        except Exception as e:
            print(f"[decorate] sticker error: {e}")

    # -----------------------------------------------------------------------
    # E. Hand-drawn elements (underlines, arrows above/below text)
    # -----------------------------------------------------------------------
    for hd_entry in assets.get("handdrawn", []):
        hd_path = picker.get_full_path(hd_entry)
        if not hd_path.exists():
            continue
        try:
            sz = ASSET_SIZES["handdrawn"]
            color = PALETTE["gold"]  # always gold for hand-drawn
            hd = load_tinted(hd_path, color, size=(sz, sz))
            hd = apply_opacity(hd, 0.80 * scene_fade)

            placements = hd_entry.get("placement") or ["highlight"]
            zone = _pick_zone(placements[0], used_zones)
            if zone is None:
                zone = _rng.choice(TOPBAR_ZONES + BOTTOM_ZONES)
            used_zones.add(zone)

            x, y = _resolve_pos(zone, hd.width, hd.height, frame_w, frame_h)
            frame.paste(hd, (x, y), hd)
        except Exception as e:
            print(f"[decorate] handdrawn error: {e}")

    return frame


# ---------------------------------------------------------------------------
# Convenience: decorate a list of frames (e.g. a full scene strip)
# ---------------------------------------------------------------------------

def decorate_frames(
    frames: list[Image.Image],
    scene_idx: int,
    style_key: str = "bold_creator",
    scene_durations: list[float] | None = None,
    fps: int = 30,
    enabled: bool = True,
) -> list[Image.Image]:
    """
    Applies decoration to every frame in a list, respecting fade in/out.

    Args:
        frames:           List of RGBA PIL Images (one per video frame).
        scene_idx:        Scene index for deterministic asset picking.
        style_key:        StyleTemplate key.
        scene_durations:  [duration_s] per frame for fade calculation. If None,
                          all frames use scene_fade=1.0.
        fps:              Frame rate for converting frame index → time.
        enabled:          Master on/off switch.

    Returns:
        New list of composited RGBA Images.
    """
    if not enabled:
        return frames

    result = []
    n = len(frames)
    total_dur = n / fps

    for i, f in enumerate(frames):
        t = i / fps
        enter_fade = min(1.0, t / 0.25) if t < 0.25 else 1.0
        exit_fade  = min(1.0, (total_dur - t) / 0.25) if t > total_dur - 0.25 else 1.0
        scene_fade = max(0.0, min(1.0, enter_fade * exit_fade))

        result.append(overlay_decoration(
            f, scene_idx=scene_idx, style_key=style_key,
            scene_fade=scene_fade, enabled=enabled,
        ))
    return result
