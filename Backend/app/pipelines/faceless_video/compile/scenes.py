from typing import List
from pydantic import BaseModel
from app.core.ir import Beat, Fragment, SceneSpec, SourceRef, Claim
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
    """Splits narration string into fragments of <=4 words each, preserving all words."""
    words = narration.split()
    fragments: list[Fragment] = []

    for i in range(0, len(words), 4):
        frag_words = words[i:i+4]
        if frag_words:
            # Highlight first important looking word
            emphasis = [0] if len(frag_words) > 0 and len(frag_words[0]) > 4 else []
            fragments.append(Fragment(words=frag_words, emphasis=emphasis))

    if not fragments:
        fragments = [Fragment(words=["Video"], emphasis=[0])]

    return fragments


def compile_scenes(beats: list[Beat], claims: list[Claim]) -> list[SceneSpec]:
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
                duration_s=beat.budget_s,
                word_times=[],
                source=source_ref
            )
        )

    return scenes
