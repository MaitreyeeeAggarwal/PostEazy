import re
from typing import List, Literal
from pydantic import BaseModel
from app.core.ir import Claim, Beat
from app.pipelines.faceless_video.core.llm import get_llm_client

WPM = 152  # Faceless video speaking rate (words per minute)
BANNED_HOOK_OPENINGS = [
    "in this video", "let's talk about", "have you ever wondered", "have you ever",
    "today we will", "today we'll", "welcome back", "in today's video", "let us look at"
]


class BeatResponseItem(BaseModel):
    role: Literal["hook", "context", "body", "turn", "payoff", "cta", "loop_closer"]
    claim_ids: list[int] = []
    narration: str
    narration_spoken: str = ""

class NarrativeArcOutput(BaseModel):
    hook_type: str  # "number", "contradiction", "question", "stakes"
    beats: list[BeatResponseItem]


def budget_time(target_seconds: float = 60.0) -> dict:
    """Calculates word and scene budgets for target video duration."""
    total_words = int(WPM * target_seconds / 60.0)
    n_scenes = max(6, min(18, round(target_seconds / 3.4)))
    words_per_scene = max(5, total_words // n_scenes)
    return {
        "total_words": total_words,
        "n_scenes": n_scenes,
        "words_per_scene": words_per_scene,
        "budget_s": target_seconds
    }


def spell_out_digits(text: str) -> str:
    """Converts numerals to spelled-out words for speech synthesis."""
    replacements = {
        "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
        "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
        "10": "ten", "40%": "forty percent", "50%": "fifty percent",
        "100%": "one hundred percent", "2024": "twenty twenty four"
    }
    res = text
    for num, word in replacements.items():
        res = re.sub(rf"\b{re.escape(num)}\b", word, res)
    return res


def plan_narrative_arc(claims: list[Claim], target_seconds: float = 60.0) -> list[Beat]:
    """Stage 3: Select top claims by surprise_score, construct high-retention narrative arc."""
    budget_info = budget_time(target_seconds)
    n_scenes = budget_info["n_scenes"]
    llm = get_llm_client()

    # Sort claims by surprise_score descending, then salience
    candidate_pool = sorted(claims, key=lambda c: (c.surprise_score, c.salience), reverse=True)[:int(n_scenes * 1.5)]
    claims_formatted = "\n".join([f"ID {c.id} [Surprise: {c.surprise_score}/10, {c.kind}]: {c.text}" for c in candidate_pool])

    if llm.is_configured and candidate_pool:
        prompt = (
            f"Build a tight {n_scenes}-scene viral video narrative script ({target_seconds}s video budget).\n"
            f"Structure:\n"
            f"  - Beat 1 (HOOK): High-impact hook using the most surprising claim. Max 8 words. MUST be a number, a question, or a bold contradiction. NO INTRO OR SETUP.\n"
            f"  - Beat 2 (OPEN LOOP / CONTEXT): Tease an upcoming twist (e.g., 'but the second stat changes everything').\n"
            f"  - Beat 3..{n_scenes-2} (BODY): One punchy idea per scene. Max 14 words per beat. Use spoken contractions (it's, don't, we're).\n"
            f"  - Beat {n_scenes-1} (PAYOFF): Deliver on the open-loop teaser.\n"
            f"  - Beat {n_scenes} (LOOP CLOSER): Last line must seamlessly connect back to the hook for replayability.\n\n"
            f"BANNED OPENERS: NEVER start beat 1 with 'In this video', 'Today we'll', 'Let's talk about', 'Have you ever'.\n\n"
            f"CLAIMS POOL:\n{claims_formatted}"
        )
        try:
            result = llm.complete_structured(
                prompt=prompt,
                response_schema=NarrativeArcOutput,
                system_prompt="You are a top-tier TikTok/Reels viral scriptwriter focused on 90%+ retention.",
                temperature=0.7
            )
            beats: list[Beat] = []
            for idx, item in enumerate(result.beats, start=1):
                narration = item.narration.strip()
                
                # Enforce hook rules for beat 1
                if idx == 1 or item.role == "hook":
                    for banned in BANNED_HOOK_OPENINGS:
                        if narration.lower().startswith(banned):
                            narration = narration[len(banned):].strip(" ,:-")
                    # Trim hook to max 8 words
                    words = narration.split()
                    if len(words) > 8:
                        narration = " ".join(words[:8])

                spoken = item.narration_spoken or spell_out_digits(narration)
                beats.append(
                    Beat(
                        idx=idx,
                        role=item.role,
                        claim_ids=item.claim_ids or ([candidate_pool[min(idx-1, len(candidate_pool)-1)].id] if candidate_pool else []),
                        narration=narration,
                        narration_spoken=spoken,
                        budget_s=round(target_seconds / max(1, len(result.beats)), 2)
                    )
                )
            return beats
        except Exception as e:
            print(f"[Plan] NVIDIA LLM arc planning error: {e}. Falling back to deterministic beat generator.")

    # Rule-Based Fallback Narrative Arc
    fallback_beats: list[Beat] = []
    selected_claims = candidate_pool[:n_scenes] if candidate_pool else claims[:n_scenes]
    
    for idx, c in enumerate(selected_claims, start=1):
        if idx == 1:
            role = "hook"
            words = c.text.split()[:8]
            narration = " ".join(words)
        elif idx == 2:
            role = "context"
            narration = "But here is what most people miss."
        elif idx == len(selected_claims):
            role = "payoff"
            narration = "And that is why this changes everything."
        else:
            role = "body"
            words = c.text.split()[:12]
            narration = " ".join(words)

        fallback_beats.append(
            Beat(
                idx=idx,
                role=role,
                claim_ids=[c.id],
                narration=narration,
                narration_spoken=spell_out_digits(narration),
                budget_s=round(target_seconds / max(1, len(selected_claims)), 2)
            )
        )

    return fallback_beats
