from PIL import Image

from app.pipelines.assets.decorative import AssetPicker
from app.pipelines.faceless_video.render.decorate import overlay_decoration


def test_shared_decorative_assets_are_available_and_composite():
    picker = AssetPicker()
    assert picker._manifest

    frame = Image.new("RGBA", (360, 640), (0, 0, 0, 0))
    decorated = overlay_decoration(frame, scene_idx=1, style_key="bold_creator")

    assert decorated.size == frame.size
    assert decorated.getbbox() is not None
