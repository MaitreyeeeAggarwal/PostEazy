from __future__ import annotations

import html

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from app.schemas import AdvisoryReportDraft, BusinessDocumentDraft, ExecutiveSummaryDraft


def _safe(value: str) -> str:
    return html.escape(value).replace("\n", "<br/>")


def _citation_text(citations) -> str:
    return ", ".join(citation.locator for citation in citations)


def render_business_document_pdf(draft: BusinessDocumentDraft, output_path: str) -> str:
    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=25, textColor=colors.HexColor("#1f2933"), spaceAfter=8)
    heading = ParagraphStyle("DocHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#466653"), spaceBefore=13, spaceAfter=5)
    body = ParagraphStyle("DocBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13, spaceAfter=4)
    citation = ParagraphStyle("DocCitation", parent=body, fontSize=7.5, leading=10, textColor=colors.HexColor("#466653"))
    story = [Paragraph(_safe(draft.title), title), Paragraph(_safe(f"SOURCE-GROUNDED {draft.kind.upper()} · {draft.audience}"), citation), Spacer(1, 6)]

    def add_section(name, items, first_heading, first_detail, first_citations, label_getter=lambda _: ""):
        story.append(Paragraph(_safe(name), heading))
        for item in items:
            title_text = label_getter(item) + first_heading(item)
            content = [Paragraph(_safe(title_text), body), Paragraph(_safe(first_detail(item)), body), Paragraph(_safe("Sources: " + _citation_text(first_citations(item))), citation), Spacer(1, 4)]
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
    doc.build(story)
    return output_path
