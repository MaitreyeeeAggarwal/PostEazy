from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from app.schemas import PresentationDeckScript, PresentationSlideLayout
from app.pipelines.presentation.core.theme_engine import get_theme_config
from app.pipelines.presentation.render.decorative import get_slide_decorations


def hex_to_rgb(hex_str: str) -> RGBColor:
    hex_str = hex_str.lstrip('#')
    if len(hex_str) != 6:
        return RGBColor(31, 27, 21)
    return RGBColor(
        int(hex_str[0:2], 16),
        int(hex_str[2:4], 16),
        int(hex_str[4:6], 16)
    )


def render_presentation_pptx(deck: PresentationDeckScript, output_path: str) -> str:
    """Generates an editable, themed 16:9 PowerPoint (.pptx) presentation deck."""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    theme = get_theme_config(deck.theme)
    background_color = hex_to_rgb(theme["bg"])
    primary_text_color = hex_to_rgb(theme["text_primary"])
    secondary_text_color = hex_to_rgb(theme["text_secondary"])
    accent_color = hex_to_rgb(theme["accent"])
    surface_color = hex_to_rgb(theme["surface"])

    blank_layout = prs.slide_layouts[6]  # Blank layout

    for s in deck.slides:
        slide = prs.slides.add_slide(blank_layout)

        background = slide.background.fill
        background.solid()
        background.fore_color.rgb = background_color

        decorations = get_slide_decorations(deck.theme, s.idx)
        # Place transparent frame art behind content, then sparse corner accents.
        # Images are deliberately kept outside the primary text region.
        if decorations.frame:
            slide.shapes.add_picture(str(decorations.frame), Inches(0), Inches(0), width=prs.slide_width, height=prs.slide_height)
        sticker_positions = [
            (Inches(11.6), Inches(0.45), Inches(0.85)),
            (Inches(0.3), Inches(3.85), Inches(0.78)),
            (Inches(11.76), Inches(3.95), Inches(0.68)),
        ]
        for sticker, (x, y, size) in zip(decorations.stickers or ((decorations.sticker,) if decorations.sticker else ()), sticker_positions):
            slide.shapes.add_picture(str(sticker), x, y, width=size, height=size)
        if decorations.accent:
            slide.shapes.add_picture(str(decorations.accent), Inches(0.45), Inches(5.95), width=Inches(1.1), height=Inches(0.8))

        accent_rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.52), Inches(1.4), Inches(0.08))
        accent_rule.fill.solid()
        accent_rule.fill.fore_color.rgb = accent_color
        accent_rule.line.fill.background()
        
        is_title_slide = s.layout == PresentationSlideLayout.TITLE_HERO
        title_x = Inches(1.1) if is_title_slide else Inches(0.8)
        title_y = Inches(1.7) if is_title_slide else Inches(0.8)
        title_width = Inches(11.1) if is_title_slide else Inches(11.7)

        # Slide Title
        txBox = slide.shapes.add_textbox(title_x, title_y, title_width, Inches(1.5))
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = s.heading
        p.font.size = Pt(42 if is_title_slide else 36)
        p.font.bold = True
        p.font.color.rgb = primary_text_color
        if is_title_slide:
            p.alignment = PP_ALIGN.CENTER

        # Subheading / Badge
        if s.subheading:
            p2 = tf.add_paragraph()
            p2.text = s.subheading
            p2.font.size = Pt(20)
            p2.font.color.rgb = secondary_text_color
            if is_title_slide:
                p2.alignment = PP_ALIGN.CENTER

        # Content Box
        if s.layout == PresentationSlideLayout.BIG_STAT and s.stat_number:
            statBox = slide.shapes.add_textbox(Inches(7.5), Inches(2.2), Inches(4.5), Inches(3.0))
            stf = statBox.text_frame
            sp = stf.paragraphs[0]
            sp.text = s.stat_number
            sp.font.size = Pt(72)
            sp.font.bold = True
            sp.font.color.rgb = accent_color
            sp.alignment = PP_ALIGN.CENTER

            if s.stat_label:
                sp2 = stf.add_paragraph()
                sp2.text = s.stat_label
                sp2.font.size = Pt(18)
                sp2.font.color.rgb = secondary_text_color
                sp2.alignment = PP_ALIGN.CENTER

        content_x = Inches(1.45) if is_title_slide else Inches(0.8)
        content_y = Inches(3.65) if is_title_slide else Inches(2.3)
        content_width = Inches(10.4) if is_title_slide else Inches(6.5)
        contentBox = slide.shapes.add_textbox(content_x, content_y, content_width, Inches(2.4 if is_title_slide else 4.2))
        ctf = contentBox.text_frame
        ctf.word_wrap = True

        for pt in s.body_points:
            cp = ctf.add_paragraph()
            cp.text = f"• {pt}"
            cp.font.size = Pt(18)
            cp.font.color.rgb = primary_text_color
            cp.space_after = Pt(12)
            if is_title_slide:
                cp.alignment = PP_ALIGN.CENTER

        if s.layout == PresentationSlideLayout.FEATURE_CARDS and s.card_items:
            card_count = min(len(s.card_items), 3)
            card_width = Inches(3.65)
            for index, item in enumerate(s.card_items[:card_count]):
                card = slide.shapes.add_shape(
                    MSO_SHAPE.ROUNDED_RECTANGLE,
                    Inches(0.8 + (index * 4.1)),
                    Inches(2.55),
                    card_width,
                    Inches(2.75)
                )
                card.fill.solid()
                card.fill.fore_color.rgb = surface_color
                card.line.color.rgb = accent_color
                card_tf = card.text_frame
                card_tf.word_wrap = True
                card_tf.margin_left = Inches(0.25)
                card_tf.margin_right = Inches(0.25)
                card_tf.margin_top = Inches(0.2)
                card_title = card_tf.paragraphs[0]
                card_title.text = item.get('title', 'Item')
                card_title.font.size = Pt(20)
                card_title.font.bold = True
                card_title.font.color.rgb = accent_color
                card_desc = card_tf.add_paragraph()
                card_desc.text = item.get('desc', '')
                card_desc.font.size = Pt(14)
                card_desc.font.color.rgb = primary_text_color
        else:
            for item in s.card_items:
                cp = ctf.add_paragraph()
                cp.text = f"✦ {item.get('title', 'Item')}: {item.get('desc', '')}"
                cp.font.size = Pt(16)
                cp.font.bold = False
                cp.font.color.rgb = primary_text_color
                cp.space_after = Pt(10)

    prs.save(output_path)
    return output_path
