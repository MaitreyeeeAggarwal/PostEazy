from dataclasses import dataclass
from typing import Dict
from app.schemas import Platform

@dataclass
class PlatformPreset:
    platform: Platform
    name: str
    tone: str
    voice_name: str
    speaking_rate: str
    words_per_second: float
    active_word_color: str
    caption_font_size: int
    caption_text_case: str  # UPPERCASE or Sentence
    caption_bottom_margin: int
    background_dim: float
    music_volume: float
    # Static post extensions
    primary_color: str
    background_color: str
    aspect_ratio: str  # "1080x1350" or "1080x1080"

PRESETS: Dict[Platform, PlatformPreset] = {
    Platform.INSTAGRAM: PlatformPreset(
        platform=Platform.INSTAGRAM,
        name="Instagram",
        tone="Energetic, curious, punchy fragments",
        voice_name="en-US-AndrewNeural",
        speaking_rate="+8%",
        words_per_second=2.8,
        active_word_color="#FF007F",  # Vivid Pink
        caption_font_size=88,
        caption_text_case="UPPERCASE",
        caption_bottom_margin=560,
        background_dim=-0.12,
        music_volume=0.14,
        primary_color="#E1306C",
        background_color="#0F0F14",
        aspect_ratio="1080x1350"
    ),
    Platform.LINKEDIN: PlatformPreset(
        platform=Platform.LINKEDIN,
        name="LinkedIn",
        tone="Professional, insightful, precise, data-driven",
        voice_name="en-US-AriaNeural",
        speaking_rate="+0%",
        words_per_second=2.5,
        active_word_color="#38BDF8",  # Sky Blue
        caption_font_size=76,
        caption_text_case="Sentence",
        caption_bottom_margin=520,
        background_dim=-0.22,
        music_volume=0.08,
        primary_color="#0A66C2",
        background_color="#F3F6F8",
        aspect_ratio="1080x1350"
    )
}

def get_preset(platform: Platform) -> PlatformPreset:
    return PRESETS.get(platform, PRESETS[Platform.LINKEDIN])
