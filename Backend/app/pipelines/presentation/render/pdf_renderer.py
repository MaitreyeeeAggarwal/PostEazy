from pathlib import Path
from app.schemas import PresentationDeckScript, PresentationSlideLayout
from app.pipelines.presentation.core.theme_engine import get_theme_config
from app.pipelines.presentation.render.decorative import get_slide_decorations


def render_presentation_pdf(deck: PresentationDeckScript, output_path: str) -> str:
    """Renders 16:9 vector PDF presentation deck using ReportLab."""
    try:
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.utils import ImageReader
    except ImportError as err:
        print(f"[PDF Render Warning]: ReportLab library missing ({err}). Skipping PDF render.")
        return output_path
    theme = get_theme_config(deck.theme)
    page_width, page_height = landscape(A4)
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=(page_width, page_height),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    bg_color = colors.HexColor(theme["bg"])
    text_color = colors.HexColor(theme["text_primary"])
    accent_color = colors.HexColor(theme["accent"])
    surface_color = colors.HexColor(theme["surface"])

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'SlideTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=text_color,
        spaceAfter=12
    )
    subtitle_style = ParagraphStyle(
        'SlideSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor(theme["text_secondary"]),
        spaceAfter=18
    )
    body_style = ParagraphStyle(
        'SlideBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=18,
        textColor=text_color,
        spaceAfter=8
    )
    stat_style = ParagraphStyle(
        'SlideStat',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=48,
        leading=54,
        textColor=accent_color,
        alignment=1
    )

    story = []

    for s in deck.slides:
        story.append(Paragraph(f"<font color='{theme['badge_text']}'><b>• {deck.target_audience.upper()}</b></font>", body_style))
        story.append(Spacer(1, 10))

        if s.layout == PresentationSlideLayout.TITLE_HERO:
            story.append(Spacer(1, 40))
            story.append(Paragraph(s.heading, title_style))
            story.append(Paragraph(s.subheading or deck.subtitle, subtitle_style))
            story.append(Spacer(1, 20))
            for pt in s.body_points:
                story.append(Paragraph(f"• {pt}", body_style))
                
        elif s.layout == PresentationSlideLayout.BIG_STAT:
            story.append(Paragraph(s.heading, title_style))
            if s.subheading:
                story.append(Paragraph(s.subheading, subtitle_style))
            
            data = [
                [
                    Paragraph("<br/>".join([f"• {pt}" for pt in s.body_points]), body_style),
                    Paragraph(f"{s.stat_number or '10X'}<br/><font size=12 color='gray'>{s.stat_label or 'Impact'}</font>", stat_style)
                ]
            ]
            t = Table(data, colWidths=[page_width * 0.5, page_width * 0.4])
            t.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BACKGROUND', (1,0), (1,0), surface_color),
                ('PADDING', (1,0), (1,0), 20),
            ]))
            story.append(t)

        elif s.layout == PresentationSlideLayout.FEATURE_CARDS:
            story.append(Paragraph(s.heading, title_style))
            card_cells = []
            for item in s.card_items:
                title = item.get("title", "Pillar")
                desc = item.get("desc", "")
                card_cells.append(Paragraph(f"<b>{title}</b><br/><font size=10 color='gray'>{desc}</font>", body_style))
            
            if card_cells:
                t = Table([card_cells], colWidths=[page_width * 0.28] * len(card_cells))
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), surface_color),
                    ('PADDING', (0,0), (-1,-1), 12),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ]))
                story.append(t)
        else:
            story.append(Paragraph(s.heading, title_style))
            if s.subheading:
                story.append(Paragraph(s.subheading, subtitle_style))
            story.append(Spacer(1, 15))
            for pt in s.body_points:
                story.append(Paragraph(f"✦ {pt}", body_style))

        story.append(Spacer(1, 20))
        story.append(Paragraph(f"<font size=8 color='gray'>{deck.title} | Slide {s.idx} of {len(deck.slides)}</font>", body_style))
        story.append(PageBreak())

    def draw_bg(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(bg_color)
        canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        decorations = get_slide_decorations(deck.theme, canvas.getPageNumber())
        if decorations.frame:
            canvas.drawImage(ImageReader(str(decorations.frame)), 0, 0, page_width, page_height, mask="auto")
        sticker_positions = [
            (page_width - 78, page_height - 78, 42),
            (36, page_height - 126, 38),
            (page_width - 72, page_height - 210, 34),
        ]
        for sticker, (x, y, size) in zip(decorations.stickers or ((decorations.sticker,) if decorations.sticker else ()), sticker_positions):
            canvas.drawImage(ImageReader(str(sticker)), x, y, size, size, mask="auto", preserveAspectRatio=True)
        if decorations.accent:
            canvas.drawImage(ImageReader(str(decorations.accent)), 36, 36, 58, 40, mask="auto", preserveAspectRatio=True)
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_bg, onLaterPages=draw_bg)
    return output_path
