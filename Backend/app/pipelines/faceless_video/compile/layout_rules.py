import re
from typing import Literal

LayoutType = Literal["center_stack", "lower_third", "split_left", "full_bleed_number", "document_figure", "stat_callout"]


def select_layout(fragment_words: list[str], beat_role: str, prev_layout: str = "", repeat_count: int = 0) -> LayoutType:
    """Selects visual layout according to content structure and visual variety rules."""
    full_text = " ".join(fragment_words)

    # 1. Full bleed number if fragment is a single statistic or numeral
    if len(fragment_words) == 1 and re.search(r"^\$?[\d,]+(\.\d+)?(%|k|M|B|x|\+)?$", fragment_words[0].strip(), re.IGNORECASE):
        chosen = "full_bleed_number"
    # 2. Stat Callout layout if narration contains key percentage / metric / currency statistics
    elif re.search(r"(\$|\b)[\d,]+(\.\d+)?\s*(percent|%|billion|million|k|M|B|x|\+)?(\b|\s|$)", full_text, re.IGNORECASE) and re.search(r"\d+", full_text):
        chosen = "stat_callout"
    elif beat_role in ("hook", "payoff"):
        chosen = "center_stack"
    elif len(fragment_words) >= 3:
        chosen = "lower_third"
    else:
        chosen = "center_stack"

    # 3. Prevent more than 2 consecutive identical layouts
    if chosen == prev_layout and repeat_count >= 2:
        alternates: list[LayoutType] = ["center_stack", "lower_third", "split_left", "stat_callout"]
        if chosen in alternates:
            alternates.remove(chosen)
        chosen = alternates[0]

    return chosen


def generate_mood_query(narration: str) -> str:
    """Generates a 2-5 word cinematic mood stock footage search query."""
    clean = re.sub(r"[^\w\s]", "", narration).lower()
    words = clean.split()
    
    mood_keywords = ["dark office", "abstract light", "slow motion technology", "modern architecture", "finance abstract", "digital network"]
    
    # Pick mood keyword based on hash or content
    idx = len(clean) % len(mood_keywords)
    return mood_keywords[idx]
