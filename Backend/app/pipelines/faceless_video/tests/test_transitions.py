import pytest
from app.core.ir import Beat, Claim, SourceRef, SceneSpec, Fragment
from app.pipelines.faceless_video.compile.scenes import compile_scenes
from app.pipelines.faceless_video.render.frames import render_frame
from app.pipelines.faceless_video.mix.audio import mix_master_audio
from app.pipelines.faceless_video.mix.export import export_deliverable, get_video_duration


def test_compile_scenes_transitions():
    source = SourceRef(file="test.pdf", locator="slide:1")
    claims = [Claim(id=1, text="AI advances rapidly.", salience=0.9, source=source)]
    beats = [
        Beat(idx=1, role="hook", claim_ids=[1], narration="AI is evolving fast", budget_s=3.0),
        Beat(idx=2, role="body", claim_ids=[1], narration="100 percent growth YoY", budget_s=3.5),
        Beat(idx=3, role="turn", claim_ids=[1], narration="But challenges remain now", budget_s=3.0),
        Beat(idx=4, role="payoff", claim_ids=[1], narration="Future looks very bright", budget_s=3.0),
    ]

    scenes = compile_scenes(beats, claims)
    assert len(scenes) == 4
    
    # Check that transitions are properly assigned and not raw cut
    transitions = [s.transition for s in scenes]
    assert scenes[0].transition == "dip"  # hook
    assert scenes[2].transition == "push" # turn
    assert scenes[3].transition == "dip"  # payoff
    
    for s in scenes:
        assert s.transition in ("cut", "dip", "push", "fade", "crossfade", "slide", "dissolve", "zoom")


def test_render_frame_smooth_fade():
    source = SourceRef(file="test.pdf", locator="slide:1")
    scene = SceneSpec(
        idx=1,
        narration="Test transition scene",
        fragments=[Fragment(words=["Test", "transition", "scene"])],
        layout="center_stack",
        bg_query="dark abstract",
        transition="fade",
        duration_s=3.0,
        source=source
    )
    
    # Render frames at start, middle, and end of scene
    frame_start = render_frame(scene, 0.05)
    frame_mid = render_frame(scene, 1.5)
    frame_end = render_frame(scene, 2.95)
    
    assert frame_start.size == (1080, 1920)
    assert frame_mid.size == (1080, 1920)
    assert frame_end.size == (1080, 1920)
