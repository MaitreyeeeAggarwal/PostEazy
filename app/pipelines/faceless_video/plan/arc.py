import re
from typing import List, Literal
from pydantic import BaseModel
from core.ir import Claim, Beat
from core.llm import get_llm_client

WPM = 152  # Faceless video speaking rate (words per minute)
BANNED_HOOK_OPENINGS = [
    "in this video", "let's talk about", "have you ever wondered",
    "today we will", "welcome back", "in today's video"
]

class BeatResponseItem(BaseModel):
    role: Literal["hook", "context", "body", "turn", "payoff", "cta"]
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
    """Stage 3: Select top claims, construct narrative arc (hook -> context -> body -> turn -> payoff -> cta)."""
    budget_info = budget_time(target_seconds)
    n_scenes = budget_info["n_scenes"]
    llm = get_llm_client()

    # Sort claims by salience
    candidate_pool = sorted(claims, key=lambda c: c.salience, reverse=True)[:int(n_scenes * 1.5)]
    claims_formatted = "\n".join([f"ID {c.id} [{c.kind}]: {c.text}" for c in candidate_pool])

    if llm.is_configured and candidate_pool:
        prompt = (
            f"Build a tight {n_scenes}-scene narrative video arc ({target_seconds}s video budget).\n"
            f"You MUST assign exactly one 'hook' at the start, 3-8 'body' beats, at most one 'turn', one 'payoff', and optional 'cta'.\n"
            f"Rules:\n"
            f"1. Each beat narration MUST be <= 14 words.\n"
            f"2. Hook MUST NOT start with banned openers like 'In this video' or 'Let's talk about'.\n"
            f"3. Each beat MUST cite the claim IDs it uses.\n\n"
            f"CLAIMS POOL:\n{claims_formatted}"
        )
        try:
            result = llm.complete_structured(
                prompt=prompt,
                response_schema=NarrativeArcOutput,
                system_prompt="You are a master viral video scriptwriter.",
                temperature=0.7
            )
            beats: list[Beat] = []
            for idx, item in enumerate(result.beats, start=1):
                # Clean narration and check banned hooks
                narration = item.narration.strip()
                if item.role == "hook":
                    for banned in BANNED_HOOK_OPENINGS:
                        if narration.lower().startswith(banned):
                            narration = f"Here is what matters: {narration[len(banned):].lstrip(', ')}"

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
    
    roles: list[Literal["hook", "context", "body", "turn", "payoff", "cta"]] = ["hook", "context"] + ["body"] * max(1, len(selected_claims)-3) + ["payoff"]

    for idx, c in enumerate(selected_claims, start=1):
        role = roles[min(idx-1, len(roles)-1)]
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
