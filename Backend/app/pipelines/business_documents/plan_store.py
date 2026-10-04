"""Short-lived plan source storage used to verify reviewed document citations."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, status

from app.config import settings
from app.core.ir import DocIR
from app.schemas import (
    AdvisoryReportDraft,
    BusinessDocumentDraft,
    EvidenceCitation,
    ExecutiveSummaryDraft,
)


def _plans_dir() -> Path:
    path = Path(settings.WORK_DIR) / "plans"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _source_path(source_document_id: str, require_valid: bool = True) -> Path | None:
    try:
        uuid.UUID(hex=source_document_id)
    except (ValueError, AttributeError, TypeError):
        if require_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The review draft source identifier is invalid.",
            )
        return None
    return _plans_dir() / f"{source_document_id}.json"


def save_source_document(doc: DocIR) -> str:
    source_document_id = uuid.uuid4().hex
    (_plans_dir() / f"{source_document_id}.json").write_text(
        doc.model_dump_json(), encoding="utf-8"
    )
    return source_document_id


def load_source_document(source_document_id: str) -> DocIR:
    path = _source_path(source_document_id)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This review draft has expired. Generate a new document plan from the source.",
        )
    return DocIR.model_validate_json(path.read_text(encoding="utf-8"))


def delete_source_document(source_document_id: str) -> None:
    path = _source_path(source_document_id, require_valid=False)
    if path and path.exists():
        path.unlink()


def _citation_groups(draft: BusinessDocumentDraft) -> Iterable[list[EvidenceCitation]]:
    if isinstance(draft, ExecutiveSummaryDraft):
        for item in draft.key_findings + draft.implications:
            yield item.citations
        for item in draft.decision_requests + draft.priority_actions:
            yield item.citations
    elif isinstance(draft, AdvisoryReportDraft):
        for item in draft.risks + draft.recommendations + draft.immediate_next_steps:
            yield item.citations


def verify_and_canonicalize_citations(draft: BusinessDocumentDraft, doc: DocIR) -> None:
    """Reject unknown locations and replace client-provided excerpts with source text."""
    source_by_locator = {}
    for block in doc.blocks:
        source_by_locator.setdefault(block.source.locator, block.text.strip())

    for citations in _citation_groups(draft):
        if not citations:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Every finding, risk, and recommendation needs a source citation.",
            )
        for citation in citations:
            source_text = source_by_locator.get(citation.locator)
            if not source_text:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Citation '{citation.locator}' does not exist in the reviewed source.",
                )
            citation.excerpt = source_text[:280]
