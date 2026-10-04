from __future__ import annotations

import html
from typing import Iterable

from app.schemas import AdvisoryReportDraft, BusinessDocumentDraft, EvidenceCitation, ExecutiveSummaryDraft


def _citations(citations: Iterable[EvidenceCitation]) -> str:
    return " ".join(
        f'<span class="citation" title="{html.escape(citation.excerpt)}">{html.escape(citation.locator)}</span>'
        for citation in citations
    )


def _item(title: str, detail: str, citations: Iterable[EvidenceCitation], label: str = "") -> str:
    label_html = f'<span class="label">{html.escape(label)}</span>' if label else ""
    return f"<article class=\"item\">{label_html}<h3>{html.escape(title)}</h3><p>{html.escape(detail)}</p><div class=\"citations\">{_citations(citations)}</div></article>"


def render_business_document_html(draft: BusinessDocumentDraft) -> str:
    if isinstance(draft, ExecutiveSummaryDraft):
        sections = (
            ("Key findings", "".join(_item(item.heading, item.detail, item.citations) for item in draft.key_findings)),
            ("Implications", "".join(_item(item.heading, item.detail, item.citations) for item in draft.implications)),
            ("Decision requests", "".join(_item(item.action, item.rationale, item.citations) for item in draft.decision_requests)),
            ("Priority actions", "".join(_item(item.action, item.rationale, item.citations) for item in draft.priority_actions)),
        )
        opening_title, opening = "Executive overview", draft.overview
    else:
        assert isinstance(draft, AdvisoryReportDraft)
        sections = (
            ("Risks and review areas", "".join(_item(item.title, item.impact, item.citations, item.severity.upper()) for item in draft.risks)),
            ("Recommendations", "".join(_item(item.recommendation, item.rationale, item.citations, f"{item.priority.upper()} · {item.timeframe}") for item in draft.recommendations)),
            ("Immediate next steps", "".join(_item(item.action, item.rationale, item.citations) for item in draft.immediate_next_steps)),
        )
        opening_title, opening = "Assessment", draft.assessment

    section_html = "".join(f"<section><h2>{html.escape(title)}</h2>{content}</section>" for title, content in sections)
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{html.escape(draft.title)}</title><style>
body{{margin:0;background:#f5f2ec;color:#1f2933;font-family:Inter,Arial,sans-serif;line-height:1.5}} main{{max-width:900px;margin:32px auto;padding:42px;background:#fff;box-shadow:0 8px 30px #1f293320}} header{{border-bottom:4px solid #466653;padding-bottom:20px}} h1{{font-family:Georgia,serif;font-size:2.1rem;margin:0 0 6px}} h2{{font-size:1.05rem;letter-spacing:.08em;text-transform:uppercase;color:#466653;margin:28px 0 10px}} h3{{font-size:1rem;margin:0 0 4px}} .meta{{color:#5d6670;font-size:.9rem}} .opening{{font-size:1.08rem;max-width:75ch}} .item{{border:1px solid #d9ded9;border-radius:8px;padding:14px 16px;margin:10px 0;break-inside:avoid}} .item p{{margin:0}} .citation,.label{{display:inline-block;margin:9px 5px 0 0;padding:2px 7px;border-radius:999px;font-size:.74rem;font-weight:700}} .citation{{background:#e6f0e6;color:#305238}} .label{{background:#f6e6de;color:#8a4e34}} footer{{margin-top:28px;padding-top:12px;border-top:1px solid #d9ded9;color:#667085;font-size:.78rem}} @media print{{body{{background:#fff}}main{{margin:0;box-shadow:none;padding:0}}}}
</style></head><body><main><header><div class=\"meta\">SOURCE-GROUNDED {html.escape(draft.kind.upper())} · {html.escape(draft.audience)}</div><h1>{html.escape(draft.title)}</h1></header><section><h2>{opening_title}</h2><p class=\"opening\">{html.escape(opening)}</p></section>{section_html}<footer>Citations identify source locations from the submitted document.</footer></main></body></html>"""
