"""Structured planners with conservative, source-cited fallback documents."""
from __future__ import annotations

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


def _fallback_executive(doc: DocIR, source_document_id: str, audience: str) -> ExecutiveSummaryDraft:
    blocks = _useful_blocks(doc)
    selected = blocks[:4]
    findings = [
        EvidenceFinding(heading=f"Finding {idx}", detail=_short(block.text), citations=[_citation(block)])
        for idx, block in enumerate(selected[:3], start=1)
    ]
    anchor = selected[0]
    implications = [
        EvidenceFinding(
            heading="Leadership implication",
            detail="This source item should be reviewed in the current leadership decision context.",
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
        decision_requests=[PriorityAction(action="Confirm the accountable decision owner.", rationale="The source identifies material items requiring leadership review.", citations=[_citation(anchor)])],
        priority_actions=[PriorityAction(action="Review and prioritize the cited source finding.", rationale="The action preserves traceability to the supplied evidence.", citations=[_citation(anchor)])],
    )


def _fallback_advisory(doc: DocIR, source_document_id: str, audience: str) -> AdvisoryReportDraft:
    blocks = _useful_blocks(doc)
    selected = blocks[:4]
    risks = [
        AdvisoryRisk(
            title=f"Review area {idx}",
            severity="medium",
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
        recommendations=[AdvisoryRecommendation(recommendation="Validate the cited review area and assign an accountable owner.", priority="now", timeframe="Current planning cycle", rationale="The recommendation is limited to reviewing the supplied source evidence.", citations=[_citation(anchor)])],
        immediate_next_steps=[PriorityAction(action="Schedule review of the cited source evidence.", rationale="A documented review is the next source-grounded action.", citations=[_citation(anchor)])],
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
