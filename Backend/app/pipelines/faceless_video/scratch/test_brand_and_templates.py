import os
import sys
from pathlib import Path

# Add project backend root to python path
backend_dir = Path(r"c:\development\SiH\PostEazy\Backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from PIL import Image, ImageDraw
from app.core.ir import SceneSpec, Fragment, SourceRef
from app.core.brand import BrandKit, StyleTemplate, STYLE_TEMPLATES
from app.pipelines.faceless_video.render.frames import render_frame

def run_tests():
    print("=== Testing Brand Kit & Style Templates ===")

    # 1. Create dummy logo image
    logo_path = backend_dir / "work" / "test_logo.png"
    logo_path.parent.mkdir(parents=True, exist_ok=True)
    img_logo = Image.new("RGBA", (200, 200), (255, 0, 100, 255))
    draw = ImageDraw.Draw(img_logo)
    draw.ellipse([40, 40, 160, 160], fill=(255, 255, 255, 255))
    img_logo.save(str(logo_path))
    print(f"Created test logo at {logo_path}")

    # 2. Test BrandKit
    bkit = BrandKit(
        logo_path=str(logo_path),
        primary_color="#ff3366",
        secondary_color="#00ffcc",
        badge_color="#ffff00",
        company_name="PostEazy Studio",
        tagline="Automate your visual stories!",
        show_end_card=True
    )
    print("BrandKit initialized successfully:", bkit)

    # 3. Create test SceneSpecs
    scene_normal = SceneSpec(
        idx=1,
        narration="Here is how our brand kit works seamlessly across all style presets.",
        fragments=[
            Fragment(words=["Brand", "Kit"], emphasis=[0]),
            Fragment(words=["Works", "Everywhere"], emphasis=[1])
        ],
        layout="center_stack",
        bg_query="abstract dark technology",
        duration_s=3.0,
        source=SourceRef(file="test.pdf", locator="slide:1")
    )

    scene_endcard = SceneSpec(
        idx=2,
        narration="Automate your visual stories!",
        fragments=[Fragment(words=["PostEazy", "Studio"], emphasis=[0])],
        layout="end_card",
        bg_query="abstract dark clean background",
        duration_s=2.5,
        source=SourceRef(file="brand", locator="end_card")
    )

    # 4. Test rendering frame for each style template
    for tmpl_key, tmpl in STYLE_TEMPLATES.items():
        print(f"\nRendering frame for template '{tmpl_key}'...")
        frame = render_frame(
            scene_normal,
            t=1.0,
            width=1080,
            height=1920,
            brand_kit=bkit,
            style_template=tmpl
        )
        assert frame.size == (1080, 1920), f"Frame size mismatch: {frame.size}"
        print(f"  -> Template '{tmpl_key}' normal frame rendered successfully ({frame.mode}, {frame.size}).")

    # 5. Test End Card rendering
    print("\nRendering End Card frame...")
    frame_endcard = render_frame(
        scene_endcard,
        t=1.0,
        width=1080,
        height=1920,
        brand_kit=bkit,
        style_template=STYLE_TEMPLATES["bold_creator"]
    )
    assert frame_endcard.size == (1080, 1920), f"End card frame size mismatch: {frame_endcard.size}"
    print("  -> End card frame rendered successfully.")

    print("\nALL BRAND KIT & STYLE TEMPLATE TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    run_tests()
