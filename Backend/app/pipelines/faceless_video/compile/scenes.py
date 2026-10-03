from typing import List, Optional
from pydantic import BaseModel
from app.core.ir import Beat, Fragment, SceneSpec, SourceRef, Claim
from app.core.brand import BrandKit
from app.pipelines.faceless_video.core.llm import get_llm_client
from app.pipelines.faceless_video.compile.layout_rules import select_layout, generate_mood_query


class FragmentSpec(BaseModel):
    words: list[str]  # <= 4 words
    emphasis: list[int] = []


class SceneSpecItem(BaseModel):
    idx: int
    narration: str
    fragments: list[FragmentSpec]
    layout: str = "center_stack"
    bg_query: str = "abstract dark technology"


class SceneCompilerOutput(BaseModel):
    scenes: list[SceneSpecItem]


def split_narration_into_fragments(narration: str) -> list[Fragment]:
    """Splits narration string into kinetic 2-3 word chunks for high-retention readability."""
    words = narration.split()
    fragments: list[Fragment] = []

    i = 0
    while i < len(words):
        # Alternate 2 and 3 word chunks for punchy rhythm
        chunk_size = 2 if (len(fragments) % 2 == 0) else 3
        frag_words = words[i:i+chunk_size]
        if frag_words:
            # Highlight keyword/longest word
            max_w_idx = max(range(len(frag_words)), key=lambda k: len(frag_words[k]))
            fragments.append(Fragment(words=frag_words, emphasis=[max_w_idx]))
        i += chunk_size

    if not fragments:
        fragments = [Fragment(words=["Video"], emphasis=[0])]

    return fragments


def compile_scenes(beats: list[Beat], claims: list[Claim], brand_kit: Optional[BrandKit] = None) -> list[SceneSpec]:
    """Stage 4: Convert Beat[] script into SceneSpec[] shot list with typography constraints."""
    llm = get_llm_client()
    scenes: list[SceneSpec] = []
    
    claims_by_id = {c.id: c for c in claims}

    prev_layout = ""
    repeat_count = 0

    for idx, beat in enumerate(beats, start=1):
        # Resolve source reference from beat claims
        source_ref = SourceRef(file="doc.pdf", locator="slide:1")
        if beat.claim_ids and beat.claim_ids[0] in claims_by_id:
            source_ref = claims_by_id[beat.claim_ids[0]].source

        # Check for extracted document image/diagram/map linked to claims
        doc_image_path = None
        for c_id in beat.claim_ids:
            if c_id in claims_by_id and claims_by_id[c_id].image_path:
                doc_image_path = claims_by_id[c_id].image_path
                break

        fragments = split_narration_into_fragments(beat.narration)
        frag_texts = [" ".join(f.words) for f in fragments]

        if doc_image_path:
            layout = "document_figure"
        else:
            layout = select_layout(frag_texts, beat.role, prev_layout, repeat_count)
            
        if layout == prev_layout:
            repeat_count += 1
        else:
            prev_layout = layout
            repeat_count = 1

        bg_query = generate_mood_query(beat.narration)

        # Select smooth transition type for seamless scene flow
        if beat.role in ("hook", "payoff"):
            transition_type = "dip"
        elif beat.role == "turn":
            transition_type = "push"
        elif layout != prev_layout:
            transition_type = "crossfade"
        else:
            transition_type = "fade"

        # Vary pacing: hook/punchy scenes shorter (2.0-2.5s), body alternating (2.2-3.8s)
        if beat.role in ("hook", "cta"):
            dur_budget = min(2.5, max(1.8, beat.budget_s))
        elif idx % 2 == 0:
            dur_budget = min(2.4, max(1.8, beat.budget_s * 0.8))
        else:
            dur_budget = min(3.8, max(2.5, beat.budget_s * 1.1))

        scenes.append(
            SceneSpec(
                idx=idx,
                narration=beat.narration,
                fragments=fragments,
                layout=layout,
                bg_query=bg_query,
                bg_asset_id=None,
                doc_image_path=doc_image_path,
                music_section="intro" if idx == 1 else ("drop" if beat.role == "payoff" else "build"),
                transition=transition_type,
                duration_s=round(dur_budget, 2),
                max_scene_seconds=4.0,
                word_times=[],
                source=source_ref
            )
        )

    if brand_kit and brand_kit.show_end_card:
        end_text = brand_kit.tagline or brand_kit.company_name or "Thank You"
        end_frags = split_narration_into_fragments(end_text)
        scenes.append(
            SceneSpec(
                idx=len(scenes) + 1,
                narration=end_text,
                fragments=end_frags,
                layout="end_card",
                bg_query="abstract dark clean background",
                bg_asset_id=None,
                doc_image_path=None,
                music_section="outro",
                transition="fade",
                duration_s=2.5,
                max_scene_seconds=4.0,
                word_times=[],
                source=SourceRef(file="brand_kit", locator="end_card")
            )
        )

    return scenes
