import pytest
from PIL import Image
from app.core.ir import SceneSpec, Fragment, SourceRef
from app.pipelines.faceless_video.render.frames import render_frame


def test_render_stat_callout_frame():
    source = SourceRef(file="test.pdf", locator="page:1")
    scene = SceneSpec(
        idx=1,
        narration="Revenue surged to $12.5M in Q3",
        fragments=[Fragment(words=["Revenue", "surged", "to"]), Fragment(words=["$12.5M", "in", "Q3"])],
        layout="stat_callout",
        bg_query="dark technology",
        duration_s=3.5,
        source=source
    )
    
    img = render_frame(scene, t=1.0)
    assert isinstance(img, Image.Image)
    assert img.size == (1080, 1920)


def test_render_document_figure_frame(tmp_path):
    source = SourceRef(file="test.pdf", locator="page:1")
    # Create a dummy image for testing document_figure layout
    dummy_img_path = tmp_path / "diagram.png"
    dummy = Image.new("RGBA", (400, 300), (34, 197, 94, 255))
    dummy.save(dummy_img_path)

    scene = SceneSpec(
        idx=1,
        narration="System architecture diagram shown below",
        fragments=[Fragment(words=["System", "architecture", "diagram"])],
        layout="document_figure",
        bg_query="abstract blue",
        doc_image_path=str(dummy_img_path),
        duration_s=3.5,
        source=source
    )

    img = render_frame(scene, t=1.0)
    assert isinstance(img, Image.Image)
    assert img.size == (1080, 1920)
