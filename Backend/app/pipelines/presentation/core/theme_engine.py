from typing import Dict, Any

THEMES: Dict[str, Dict[str, Any]] = {
    "bold_tech": {
        "name": "Bold Tech",
        "bg": "#0b0f19",
        "surface": "#141c2e",
        "surface_border": "rgba(56, 189, 248, 0.2)",
        "text_primary": "#f8fafc",
        "text_secondary": "#94a3b8",
        "accent": "#38bdf8",
        "accent_secondary": "#818cf8",
        "font_family_heading": "'Quicksand', 'Inter', sans-serif",
        "font_family_body": "'Nunito Sans', sans-serif",
        "card_bg": "rgba(20, 28, 46, 0.75)",
        "card_shadow": "0 20px 40px rgba(0, 0, 0, 0.4)",
        "badge_bg": "rgba(56, 189, 248, 0.15)",
        "badge_text": "#38bdf8"
    },
    "minimalist_editorial": {
        "name": "Minimalist Editorial",
        "bg": "#fcf8f3",
        "surface": "#ffffff",
        "surface_border": "rgba(63, 58, 51, 0.12)",
        "text_primary": "#1f1b15",
        "text_secondary": "#536349",
        "accent": "#904c30",
        "accent_secondary": "#cd7d5e",
        "font_family_heading": "'Fraunces', 'Georgia', serif",
        "font_family_body": "'Nunito Sans', sans-serif",
        "card_bg": "#ffffff",
        "card_shadow": "3px 5px 0px rgba(63, 58, 51, 0.15)",
        "badge_bg": "#f6ece2",
        "badge_text": "#904c30"
    },
    "neon_cyberpunk": {
        "name": "Neon Cyberpunk",
        "bg": "#090d16",
        "surface": "#131b2e",
        "surface_border": "rgba(236, 72, 153, 0.3)",
        "text_primary": "#ffffff",
        "text_secondary": "#a1a1aa",
        "accent": "#ec4899",
        "accent_secondary": "#06b6d4",
        "font_family_heading": "'Quicksand', sans-serif",
        "font_family_body": "'Nunito Sans', sans-serif",
        "card_bg": "rgba(19, 27, 46, 0.85)",
        "card_shadow": "0 10px 30px rgba(236, 72, 153, 0.2)",
        "badge_bg": "rgba(236, 72, 153, 0.2)",
        "badge_text": "#f472b6"
    },
    "warm_corporate": {
        "name": "Warm Corporate",
        "bg": "#fff8f3",
        "surface": "#f0e7dc",
        "surface_border": "rgba(74, 102, 62, 0.2)",
        "text_primary": "#1f1b15",
        "text_secondary": "#4a663e",
        "accent": "#4a663e",
        "accent_secondary": "#7c9a6d",
        "font_family_heading": "'Quicksand', sans-serif",
        "font_family_body": "'Nunito Sans', sans-serif",
        "card_bg": "#ffffff",
        "card_shadow": "0 8px 24px rgba(74, 102, 62, 0.12)",
        "badge_bg": "#cbecb9",
        "badge_text": "#17300e"
    }
}

def get_theme_config(theme_key: str = "bold_tech") -> Dict[str, Any]:
    """Return theme config dictionary with fallbacks."""
    return THEMES.get(theme_key, THEMES["bold_tech"])
