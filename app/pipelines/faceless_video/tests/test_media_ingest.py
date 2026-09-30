import pytest
from pathlib import Path
from core.ir import Block, Claim, SourceRef, SceneSpec, Fragment
from distil.claims import extract_claims
from compile.layout_rules import select_layout
from compile.scenes import compile_scenes


def test_claim_and_scene_image_linking():
    source = SourceRef(file="test.pdf", locator="page:1")
    # Simulate block with extracted document image
    img_path = "work/media/test_doc/page_1_img_1.png"
    
    # Verify select_layout picks stat_callout for percentage/metric text
    layout1 = select_layout(["Growth", "reached", "85%"], "body")
    assert layout1 == "stat_callout"

    layout2 = select_layout(["Revenue", "of", "$12.5M"], "body")
    assert layout2 == "stat_callout"

    # Verify claim image linking
    claim = Claim(
        id=1,
        text="Market share grew by 85 percent this quarter.",
        salience=0.9,
        source=source,
        image_path=img_path
    )
    
    claims_by_id = {1: claim}
    beats = [
        from_beat := type("BeatObj", (), {
            "idx": 1,
            "role": "body",
            "claim_ids": [1],
            "narration": "Market share grew by 85 percent this quarter",
            "budget_s": 3.5
        })()
    ]

    from compile.scenes import compile_scenes
    scenes = compile_scenes(beats, [claim])
    
    assert len(scenes) == 1
    assert scenes[0].layout == "document_figure"
    assert scenes[0].doc_image_path == img_path
