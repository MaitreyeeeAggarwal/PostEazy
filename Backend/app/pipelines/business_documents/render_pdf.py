from __future__ import annotations

import html

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from app.pipelines.business_documents.decorative import document_decoration_paths
from app.schemas import AdvisoryReportDraft, BusinessDocumentDraft, ExecutiveSummaryDraft


def _safe(value: str) -> str:
    return html.escape(value).replace("\n", "<br/>")


def _citation_text(citations) -> str:
    return ", ".join(citation.locator for citation in citations)


def render_business_document_pdf(draft: BusinessDocumentDraft, output_path: str) -> str:
    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=17 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#14233b"), spaceAfter=7)
    heading = ParagraphStyle("DocHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=colors.HexColor("#7653ef"), spaceBefore=11, spaceAfter=4)
    body = ParagraphStyle("DocBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=12.3, spaceAfter=3)
    citation = ParagraphStyle("DocCitation", parent=body, fontSize=7.2, leading=9, textColor=colors.HexColor("#27634d"))
    story = [Paragraph(_safe(draft.title), title), Paragraph(_safe(f"SOURCE-GROUNDED {draft.kind.upper()} · {draft.audience}"), citation), Spacer(1, 6)]

    def add_section(name, items, first_heading, first_detail, first_citations, label_getter=lambda _: ""):
        story.append(Paragraph(_safe(name), heading))
        for item in items:
            title_text = label_getter(item) + first_heading(item)
            content = [Paragraph(_safe(title_text), body), Paragraph(_safe(first_detail(item)), body), Paragraph(_safe("Sources: " + _citation_text(first_citations(item))), citation), Spacer(1, 3)]
            story.append(KeepTogether(content))

    if isinstance(draft, ExecutiveSummaryDraft):
        story.extend([Paragraph(_safe("Executive overview"), heading), Paragraph(_safe(draft.overview), body)])
        add_section("Key findings", draft.key_findings, lambda x: x.heading, lambda x: x.detail, lambda x: x.citations)
        add_section("Implications", draft.implications, lambda x: x.heading, lambda x: x.detail, lambda x: x.citations)
        add_section("Decision requests", draft.decision_requests, lambda x: x.action, lambda x: x.rationale, lambda x: x.citations)
        add_section("Priority actions", draft.priority_actions, lambda x: x.action, lambda x: x.rationale, lambda x: x.citations)
    else:
        assert isinstance(draft, AdvisoryReportDraft)
        story.extend([Paragraph(_safe("Assessment"), heading), Paragraph(_safe(draft.assessment), body)])
        add_section("Risks and review areas", draft.risks, lambda x: x.title, lambda x: x.impact, lambda x: x.citations, lambda x: f"[{x.severity.upper()}] ")
        add_section("Recommendations", draft.recommendations, lambda x: x.recommendation, lambda x: x.rationale, lambda x: x.citations, lambda x: f"[{x.priority.upper()} · {x.timeframe}] ")
        add_section("Immediate next steps", draft.immediate_next_steps, lambda x: x.action, lambda x: x.rationale, lambda x: x.citations)
    stickers = document_decoration_paths(draft)

    def decorate_page(canvas, pdf_doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#7653ef"))
        canvas.setLineWidth(3)
        canvas.line(18 * mm, A4[1] - 12 * mm, 43 * mm, A4[1] - 12 * mm)
        for idx, sticker in enumerate(stickers[:3]):
            positions = ((A4[0] - 31 * mm, A4[1] - 26 * mm, 13 * mm), (10 * mm, 98 * mm, 10 * mm), (A4[0] - 26 * mm, 14 * mm, 9 * mm))
            x, y, size = positions[idx]
            try:
                canvas.drawImage(str(sticker), x, y, width=size, height=size, mask="auto", preserveAspectRatio=True)
            except Exception:
                continue
        canvas.restoreState()

    doc.build(story, onFirstPage=decorate_page, onLaterPages=decorate_page)
    return output_path
