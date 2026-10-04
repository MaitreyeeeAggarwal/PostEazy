from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from app.schemas import PresentationDeckScript, PresentationSlideLayout


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
    """Generates an editable 16:9 PowerPoint (.pptx) presentation deck."""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    blank_layout = prs.slide_layouts[6]  # Blank layout

    for s in deck.slides:
        slide = prs.slides.add_slide(blank_layout)
        
        # Slide Title
        txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(11.7), Inches(1.2))
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = s.heading
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = RGBColor(15, 23, 42)

        # Subheading / Badge
        if s.subheading:
            p2 = tf.add_paragraph()
            p2.text = s.subheading
            p2.font.size = Pt(20)
            p2.font.color.rgb = RGBColor(71, 85, 105)

        # Content Box
        if s.layout == PresentationSlideLayout.BIG_STAT and s.stat_number:
            statBox = slide.shapes.add_textbox(Inches(7.5), Inches(2.2), Inches(4.5), Inches(3.0))
            stf = statBox.text_frame
            sp = stf.paragraphs[0]
            sp.text = s.stat_number
            sp.font.size = Pt(72)
            sp.font.bold = True
            sp.font.color.rgb = RGBColor(56, 189, 248)
            sp.alignment = PP_ALIGN.CENTER

            if s.stat_label:
                sp2 = stf.add_paragraph()
                sp2.text = s.stat_label
                sp2.font.size = Pt(18)
                sp2.alignment = PP_ALIGN.CENTER

        contentBox = slide.shapes.add_textbox(Inches(0.8), Inches(2.3), Inches(6.5), Inches(4.2))
        ctf = contentBox.text_frame
        ctf.word_wrap = True

        for pt in s.body_points:
            cp = ctf.add_paragraph()
            cp.text = f"• {pt}"
            cp.font.size = Pt(18)
            cp.font.color.rgb = RGBColor(30, 41, 59)
            cp.space_after = Pt(12)

        for item in s.card_items:
            cp = ctf.add_paragraph()
            cp.text = f"✦ {item.get('title', 'Item')}: {item.get('desc', '')}"
            cp.font.size = Pt(16)
            cp.font.bold = False
            cp.space_after = Pt(10)

    prs.save(output_path)
    return output_path
