"""Structured planners with conservative, source-cited fallback documents."""
from __future__ import annotations

import re

from app.core.ir import Block, DocIR
from app.pipelines.faceless_video.core.llm import get_llm_client
from app.schemas import (
    AdvisoryRecommendation,
    AdvisoryReportDraft,
    AdvisoryRisk,
    BusinessDocumentDraft,
    DocumentKind,
    EvidenceCitation,
    EvidenceFinding,
    ExecutiveSummaryDraft,
    PriorityAction,
)


def _useful_blocks(doc: DocIR) -> list[Block]:
    return [block for block in doc.blocks if block.text and block.text.strip()][:24]


def _citation(block: Block) -> EvidenceCitation:
    return EvidenceCitation(locator=block.source.locator, excerpt=block.text.strip()[:280])


def _short(text: str, length: int = 260) -> str:
    text = " ".join(text.split())
    return text[:length].rstrip()


def _topic(text: str, fallback: str = "Source item") -> str:
    """Extract a short, readable label from a cited source sentence."""
    value = _short(text, 150).strip(" .,:;-\u2013\u2014")
    value = re.split(r"[.:;\u2013\u2014]", value, maxsplit=1)[0].strip()
    words = value.split()
    if len(words) > 9:
        verbs = {"is", "are", "was", "were", "increased", "increases", "decreased", "requires", "identified", "identifies", "should", "need", "needs"}
        cut = next((idx + 2 for idx, word in enumerate(words) if word.lower().strip(",") in verbs), 8)
        words = words[:max(4, min(9, cut))]
    return " ".join(words) or fallback


def _directive(block: Block) -> str:
    text = _short(block.text, 170)
    directive_match = re.search(r"\b(should|recommend(?:ed|s)?|need(?:s)? to|must|prioriti[sz]e|review|implement|assign)\b.*", text, re.I)
    if directive_match:
        return directive_match.group(0)[0].upper() + directive_match.group(0)[1:].rstrip(".")
    return f"Review {_topic(block.text).lower()}"


def _severity(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ("critical", "breach", "failure", "blocked", "severe")):
        return "critical"
    if any(word in lower for word in ("delay", "decline", "risk", "dependency", "gap", "increase")):
        return "high"
    if any(word in lower for word in ("monitor", "watch", "potential")):
        return "low"
    return "medium"


def _fallback_executive(doc: DocIR, source_document_id: str, audience: str) -> ExecutiveSummaryDraft:
    blocks = _useful_blocks(doc)
    selected = blocks[:4]
    if not selected:
        raise ValueError("A source document needs at least one non-empty content block.")
    findings = [
        EvidenceFinding(heading=_topic(block.text, f"Source finding {idx}"), detail=_short(block.text), citations=[_citation(block)])
        for idx, block in enumerate(selected[:3], start=1)
    ]
    anchor = selected[0]
    implications = [
        EvidenceFinding(
            heading=f"Decision attention: {_topic(anchor.text)}",
            detail=f"The cited evidence makes {_topic(anchor.text).lower()} a leadership item for review.",
            citations=[_citation(anchor)],
        )
    ]
    return ExecutiveSummaryDraft(
        source_document_id=source_document_id,
        title=f"Executive Summary: {doc.title or 'Source Brief'}",
        audience=audience,
        overview=_short(" ".join(block.text for block in selected[:2]), 420),
        key_findings=findings,
        implications=implications,
        decision_requests=[PriorityAction(action=_directive(anchor), rationale=f"This request is anchored in the cited evidence on {_topic(anchor.text).lower()}.", citations=[_citation(anchor)])],
        priority_actions=[PriorityAction(action=f"Assign an owner for {_topic(anchor.text).lower()}.", rationale="Ownership is needed to move the cited item from review into action.", citations=[_citation(anchor)])],
    )


def _fallback_advisory(doc: DocIR, source_document_id: str, audience: str) -> AdvisoryReportDraft:
    blocks = _useful_blocks(doc)
    selected = blocks[:4]
    if not selected:
        raise ValueError("A source document needs at least one non-empty content block.")
    risks = [
        AdvisoryRisk(
            title=f"Risk: {_topic(block.text, f'Source area {idx}')}",
            severity=_severity(block.text),
            impact=_short(block.text),
            citations=[_citation(block)],
        )
        for idx, block in enumerate(selected[:3], start=1)
    ]
    anchor = selected[0]
    return AdvisoryReportDraft(
        source_document_id=source_document_id,
        title=f"Advisory Report: {doc.title or 'Source Assessment'}",
        audience=audience,
        assessment=_short(" ".join(block.text for block in selected[:2]), 500),
        risks=risks,
        recommendations=[AdvisoryRecommendation(recommendation=_directive(anchor), priority="now" if _severity(anchor.text) in {"high", "critical"} else "next", timeframe="Current planning cycle", rationale=f"The recommendation addresses the cited evidence on {_topic(anchor.text).lower()}.", citations=[_citation(anchor)])],
        immediate_next_steps=[PriorityAction(action=f"Confirm owner and review date for {_topic(anchor.text).lower()}.", rationale="An accountable review turns the cited risk into a tracked next step.", citations=[_citation(anchor)])],
    )


def _canonicalize_generated_draft(draft: BusinessDocumentDraft, doc: DocIR, source_document_id: str) -> BusinessDocumentDraft:
    """Ensure generated drafts only point to real source locations and excerpts."""
    from app.pipelines.business_documents.plan_store import verify_and_canonicalize_citations

    draft.source_document_id = source_document_id
    verify_and_canonicalize_citations(draft, doc)
    return draft


def plan_business_document(doc: DocIR, kind: DocumentKind, source_document_id: str, audience: str = "Executive leadership") -> BusinessDocumentDraft:
    blocks = _useful_blocks(doc)
    source_text = "\n".join(f"[{block.source.locator}] {block.text}" for block in blocks)
    schema = ExecutiveSummaryDraft if kind == DocumentKind.EXECUTIVE else AdvisoryReportDraft
    llm = get_llm_client()

    if llm.is_configured and source_text:
        try:
            prompt = (
                f"Create a {kind.value} document for {audience} using only the supplied source.\n"
                "Every factual finding, implication, risk, decision request, action, and recommendation "
                "must include at least one citation locator copied exactly from the source. Do not invent metrics, "
                "facts, causes, or external knowledge. Keep executive summaries concise and advisory reports decision-ready.\n\n"
                f"Set source_document_id to '{source_document_id}'. Citation excerpts may be omitted; they are restored from source.\n\n"
                f"SOURCE:\n{source_text}"
            )
            draft = llm.complete_structured(
                prompt=prompt,
                response_schema=schema,
                system_prompt="You are a cautious executive analyst. Return only source-grounded structured JSON.",
            )
            return _canonicalize_generated_draft(draft, doc, source_document_id)
        except Exception as error:
            print(f"[Business Document Planner Note]: LLM planning failed ({error}). Using extractive fallback.")

    if kind == DocumentKind.EXECUTIVE:
        return _fallback_executive(doc, source_document_id, audience)
    return _fallback_advisory(doc, source_document_id, audience)
