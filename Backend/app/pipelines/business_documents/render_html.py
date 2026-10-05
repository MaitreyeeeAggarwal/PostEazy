from __future__ import annotations

import html
from typing import Iterable

from app.pipelines.business_documents.decorative import document_decorations
from app.schemas import AdvisoryReportDraft, BusinessDocumentDraft, EvidenceCitation, ExecutiveSummaryDraft


def _citations(citations: Iterable[EvidenceCitation]) -> str:
    return " ".join(
        f'<span class="citation" title="{html.escape(citation.excerpt)}">{html.escape(citation.locator)}</span>'
        for citation in citations
    )


def _item(title: str, detail: str, citations: Iterable[EvidenceCitation], label: str = "") -> str:
    label_html = f'<span class="label">{html.escape(label)}</span>' if label else ""
    return f"<article class=\"item\">{label_html}<h3>{html.escape(title)}</h3><p>{html.escape(detail)}</p><div class=\"citations\">{_citations(citations)}</div></article>"


def _section(title: str, content: str, tone: str = "") -> str:
    return f'<section class="section {tone}"><div class="section-title"><span></span><h2>{html.escape(title)}</h2></div><div class="items">{content}</div></section>'


def render_business_document_html(draft: BusinessDocumentDraft) -> str:
    """Render a compact, print-ready decision brief with traceable evidence."""
    decorations = document_decorations(draft)
    decor_html = "".join(
        f'<img class="sticker sticker-{idx}" src="{src}" alt="" aria-hidden="true">'
        for idx, src in enumerate(decorations) if src
    )
    if isinstance(draft, ExecutiveSummaryDraft):
        sections = (
            _section("Key findings", "".join(_item(item.heading, item.detail, item.citations) for item in draft.key_findings), "findings"),
            _section("Leadership implications", "".join(_item(item.heading, item.detail, item.citations) for item in draft.implications), "implications"),
            _section("Decision requests", "".join(_item(item.action, item.rationale, item.citations, "DECIDE") for item in draft.decision_requests), "decisions"),
            _section("Priority actions", "".join(_item(item.action, item.rationale, item.citations, "ACT") for item in draft.priority_actions), "actions"),
        )
        opening_title, opening, kind_label = "The executive read", draft.overview, "EXECUTIVE SUMMARY"
    else:
        assert isinstance(draft, AdvisoryReportDraft)
        sections = (
            _section("Risk register", "".join(_item(item.title, item.impact, item.citations, item.severity.upper()) for item in draft.risks), "risks"),
            _section("Recommendations", "".join(_item(item.recommendation, item.rationale, item.citations, f"{item.priority.upper()} · {item.timeframe}") for item in draft.recommendations), "recommendations"),
            _section("Immediate next steps", "".join(_item(item.action, item.rationale, item.citations, "NEXT") for item in draft.immediate_next_steps), "actions"),
        )
        opening_title, opening, kind_label = "Assessment", draft.assessment, "ADVISORY BRIEF"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(draft.title)}</title><style>
:root{{--ink:#14233b;--muted:#627187;--paper:#fbfaf6;--line:#dce3e9;--accent:#7653ef;--mint:#e7f4ee;--peach:#fff0e6}}*{{box-sizing:border-box}}body{{margin:0;background:#e8edf2;color:var(--ink);font-family:Inter,Arial,sans-serif;line-height:1.42}}main{{position:relative;overflow:hidden;max-width:980px;margin:28px auto;padding:36px 42px 28px;background:var(--paper);box-shadow:0 18px 54px #14233b24}}header{{position:relative;padding:22px 0 25px;border-bottom:1px solid var(--line);z-index:1}}header:before{{content:"";position:absolute;inset:0 auto auto 0;width:76px;height:5px;border-radius:9px;background:linear-gradient(90deg,var(--accent),#34b28a)}}.eyebrow{{font-size:.69rem;font-weight:800;letter-spacing:.14em;color:var(--accent)}}h1{{max-width:75%;font-family:Georgia,serif;font-size:2.3rem;line-height:1.06;margin:10px 0 9px}}.meta{{color:var(--muted);font-size:.8rem}}.sticker{{position:absolute;z-index:0;pointer-events:none}}.sticker-0{{width:74px;right:26px;top:18px;transform:rotate(10deg)}}.sticker-1{{width:58px;left:-13px;top:35%;opacity:.82;transform:rotate(-13deg)}}.sticker-2{{width:51px;right:16px;bottom:22px;opacity:.8;transform:rotate(10deg)}}.opening{{position:relative;margin:25px 0 21px;padding:18px 21px 18px 23px;border-radius:12px;background:linear-gradient(110deg,#eff0ff,#f7fbf8);border-left:5px solid var(--accent)}}.opening h2{{margin:0 0 6px;font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}}.opening p{{margin:0;max-width:90ch;font-family:Georgia,serif;font-size:1.06rem;line-height:1.5}}.section{{position:relative;margin:18px 0;z-index:1}}.section-title{{display:flex;align-items:center;gap:8px;margin:0 0 8px}}.section-title span{{width:8px;height:8px;border-radius:50%;background:var(--accent)}}h2{{margin:0;font-size:.76rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}}.items{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}.item{{min-width:0;border:1px solid var(--line);border-radius:10px;padding:12px 13px 11px;background:#fff;break-inside:avoid;box-shadow:0 2px 5px #14233b08}}.risks .item{{border-top:3px solid #d46b53}}.decisions .item{{border-top:3px solid var(--accent)}}.actions .item{{border-top:3px solid #34a980}}h3{{font-size:.94rem;line-height:1.22;margin:0 0 5px}}.item p{{margin:0;color:#44536a;font-size:.82rem}}.citation,.label{{display:inline-block;margin:8px 4px 0 0;padding:2px 6px;border-radius:999px;font-size:.64rem;font-weight:800;letter-spacing:.03em}}.citation{{background:var(--mint);color:#27634d}}.label{{background:var(--peach);color:#a74c31}}footer{{position:relative;margin-top:21px;padding-top:12px;border-top:1px solid var(--line);color:var(--muted);font-size:.69rem;z-index:1}}@media(max-width:650px){{main{{margin:0;padding:27px 20px}}h1{{max-width:82%;font-size:1.85rem}}.items{{grid-template-columns:1fr}}.sticker-1{{display:none}}}}@media print{{body{{background:#fff}}main{{max-width:none;margin:0;min-height:0;padding:18mm 17mm 14mm;box-shadow:none}}.section{{margin:13px 0}}.item{{padding:9px 10px}}.item p{{font-size:.76rem}}}}
</style></head><body><main>{decor_html}<header><div class="eyebrow">SOURCE-GROUNDED {kind_label}</div><h1>{html.escape(draft.title)}</h1><div class="meta">Prepared for {html.escape(draft.audience)} · Evidence citations retained</div></header><section class="opening"><h2>{opening_title}</h2><p>{html.escape(opening)}</p></section>{''.join(sections)}<footer>Citations identify traceable locations in the submitted source. This brief does not add facts beyond that evidence.</footer></main></body></html>"""
