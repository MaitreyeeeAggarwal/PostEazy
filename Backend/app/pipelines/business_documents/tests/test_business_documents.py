import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.ir import Block, DocIR, SourceRef
from app.pipelines.business_documents.plan_store import verify_and_canonicalize_citations
from app.pipelines.business_documents.planner import plan_business_document
from app.pipelines.business_documents.render_html import render_business_document_html
from app.pipelines.business_documents.render_pdf import render_business_document_pdf
from app.pipelines.business_documents.router import _document_from_request
from app.schemas import DocumentKind


@pytest.fixture(autouse=True)
def disable_live_llm(monkeypatch):
    """Keep fallback and renderer tests deterministic and offline."""
    monkeypatch.setattr(
        "app.pipelines.business_documents.planner.get_llm_client",
        lambda: SimpleNamespace(is_configured=False),
    )


@pytest.fixture
def source_doc():
    return DocIR(
        doc_id="business-doc-test",
        title="Operational Review",
        blocks=[
            Block(level=1, text="Delivery delays increased during the last quarter.", source=SourceRef(file="review.pdf", locator="page:1")),
            Block(level=3, text="The report identifies vendor dependency as a contributing review area.", source=SourceRef(file="review.pdf", locator="page:2")),
            Block(level=3, text="Leadership should review ownership and mitigation planning.", source=SourceRef(file="review.pdf", locator="page:3")),
        ],
    )


@pytest.mark.parametrize("kind", [DocumentKind.EXECUTIVE, DocumentKind.ADVISORY])
def test_rule_based_plans_are_source_cited(source_doc, kind):
    draft = plan_business_document(source_doc, kind, "source-plan", "Leadership")
    assert draft.source_document_id == "source-plan"
    assert draft.kind == kind.value
    html = render_business_document_html(draft)
    assert "page:1" in html
    assert "SOURCE-GROUNDED" in html
    assert "data:image/png;base64" in html
    assert "Finding 1" not in html
    assert "Review area 1" not in html


def test_unknown_citation_is_rejected(source_doc):
    draft = plan_business_document(source_doc, DocumentKind.EXECUTIVE, "source-plan")
    draft.key_findings[0].citations[0].locator = "page:99"
    with pytest.raises(HTTPException) as error:
        verify_and_canonicalize_citations(draft, source_doc)
    assert error.value.status_code == 422


def test_client_citation_excerpt_is_replaced_with_source_text(source_doc):
    draft = plan_business_document(source_doc, DocumentKind.EXECUTIVE, "source-plan")
    draft.key_findings[0].citations[0].excerpt = "client supplied text"
    verify_and_canonicalize_citations(draft, source_doc)
    assert draft.key_findings[0].citations[0].excerpt == source_doc.blocks[0].text


def test_plan_request_requires_exactly_one_source():
    with pytest.raises(HTTPException) as error:
        asyncio.run(_document_from_request(None, "https://example.com", "also a prompt"))
    assert error.value.status_code == 400


def test_pdf_renderer_creates_a_pdf(source_doc, tmp_path):
    draft = plan_business_document(source_doc, DocumentKind.ADVISORY, "source-plan")
    path = tmp_path / "advisory.pdf"
    render_business_document_pdf(draft, str(path))
    assert path.exists()
    assert path.read_bytes().startswith(b"%PDF")
