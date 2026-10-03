from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class BrandKit(BaseModel):
    logo_path: Optional[str] = None          # Path to PNG logo image
    font_path: Optional[str] = None          # Path to TTF/OTF custom font
    primary_color: Optional[str] = "#38bdf8" # Accent highlight color
    secondary_color: Optional[str] = "#fbbf24" # Secondary highlight / number color
    badge_color: Optional[str] = "#7c3aed"     # Badge fill color
    company_name: Optional[str] = None
    tagline: Optional[str] = None
    watermark_position: str = "top_right"    # "top_left", "top_right", "bottom_left"
    watermark_opacity: float = 0.85
    show_end_card: bool = False
    end_card_title: str = "PostEazy Content Engine"
    end_card_tagline: str = "Transforming Documents into Viral Media"


class StyleTemplate(BaseModel):
    name: str
    key: str
    description: str
    font_name: str
    text_color: str
    highlight_color: str
    badge_bg: str
    badge_border: str
    number_color: str
    scrim_opacity: float
    transition_default: str
    letterbox: bool = False
    news_ticker: bool = False
    vignette_intensity: str = "medium"


STYLE_TEMPLATES: Dict[str, StyleTemplate] = {
    "bold_creator": StyleTemplate(
        name="Bold Creator",
        key="bold_creator",
        description="High-energy TikTok/Reels aesthetic with kinetic neon colors and punchy bounce.",
        font_name="Outfit-Bold",
        text_color="#FFFFFF",
        highlight_color="#FBBF24",   # Amber Gold
        badge_bg="#7C3AED",          # Purple
        badge_border="#FBBF24",
        number_color="#FBBF24",
        scrim_opacity=0.60,
        transition_default="push",
        vignette_intensity="medium"
    ),
    "documentary": StyleTemplate(
        name="Documentary",
        key="documentary",
        description="Cinematic film look with letterbox bars, sepia accents, and gentle dissolves.",
        font_name="Georgia",
        text_color="#FEF3C7",        # Warm Ivory
        highlight_color="#D97706",   # Sepia Gold
        badge_bg="#1E293B",          # Slate
        badge_border="#D97706",
        number_color="#D97706",
        scrim_opacity=0.75,
        transition_default="dip",
        letterbox=True,
        vignette_intensity="heavy"
    ),
    "news_ticker": StyleTemplate(
        name="News Ticker",
        key="news_ticker",
        description="Broadcast news look with top breaking banner, bottom ticker, and crimson badges.",
        font_name="FiraCode-Bold",
        text_color="#FFFFFF",
        highlight_color="#FACC15",   # Bright Yellow
        badge_bg="#DC2626",          # Crimson Red
        badge_border="#FFFFFF",
        number_color="#FACC15",
        scrim_opacity=0.70,
        transition_default="slide",
        news_ticker=True,
        vignette_intensity="low"
    ),
    "minimal_dark": StyleTemplate(
        name="Minimal Dark",
        key="minimal_dark",
        description="Ultra-clean tech look with spacious typography, dark void background, and cyan accents.",
        font_name="Inter-Regular",
        text_color="#F8FAFC",
        highlight_color="#00F2FE",   # Electric Cyan
        badge_bg="#0F172A",          # Dark Slate
        badge_border="#00F2FE",
        number_color="#00F2FE",
        scrim_opacity=0.50,
        transition_default="fade",
        vignette_intensity="low"
    )
}

def get_style_template(key: str) -> StyleTemplate:
    """Retrieves style template by key, defaulting to bold_creator."""
    clean_key = (key or "bold_creator").lower().strip()
    return STYLE_TEMPLATES.get(clean_key, STYLE_TEMPLATES["bold_creator"])
