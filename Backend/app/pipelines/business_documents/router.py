from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse

from app.config import settings
from app.jobs import job_store
from app.pipelines.business_documents.orchestrator import run_business_document_job
from app.pipelines.business_documents.plan_store import (
    load_source_document,
    save_source_document,
    verify_and_canonicalize_citations,
)
from app.pipelines.business_documents.planner import plan_business_document
from app.schemas import (
    AdvisoryReportDraft,
    BusinessDocumentPlan,
    DocumentKind,
    ExecutiveSummaryDraft,
    JobState,
    JobStatus,
)
from app.services.ingest import ALLOWED_EXTENSIONS, load_document
from app.core.pipeline_logging import log_pipeline_event

router = APIRouter(prefix="/api/documents", tags=["Business Documents"])
ApprovedDraft = Union[ExecutiveSummaryDraft, AdvisoryReportDraft]


async def _document_from_request(file: Optional[UploadFile], url: Optional[str], prompt: Optional[str]):
    provided = sum(bool(value) for value in (file, url, prompt))
    if provided != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide exactly one source: file, url, or prompt.")
    if url:
        return load_document(url)
    if prompt:
        return load_document(prompt)

    assert file is not None
    suffix = Path(file.filename or "upload.txt").suffix.lower()
    if not suffix:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Uploaded files require a supported extension.")
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"File size exceeds {settings.MAX_UPLOAD_MB} MB.")
    upload_dir = Path(settings.WORK_DIR) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Unsupported file type '{suffix}'.")
    import uuid
    temporary_path = upload_dir / f"business_doc_{uuid.uuid4().hex}{suffix}"
    try:
        temporary_path.write_bytes(content)
        return load_document(str(temporary_path))
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


@router.post("/plan", response_model=BusinessDocumentPlan)
async def create_document_plan(
    kind: DocumentKind = Form(...),
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    audience: str = Form("Executive leadership"),
):
    """Create an editable, source-traceable business-document draft."""
    doc = await _document_from_request(file, url, prompt)
    if not any(block.text.strip() for block in doc.blocks):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The source did not contain usable text for a source-grounded document.")
    source_document_id = save_source_document(doc)
    try:
        draft = plan_business_document(doc, kind, source_document_id, audience.strip() or "Executive leadership")
        log_pipeline_event("business_documents", "plan_created", document_kind=kind.value, document_title=doc.title, blocks=len(doc.blocks), source_type="file" if file else "url" if url else "prompt")
        return BusinessDocumentPlan(source_document_id=source_document_id, draft=draft)
    except Exception:
        # No reviewable draft exists if planning fails, so avoid retaining its source.
        from app.pipelines.business_documents.plan_store import delete_source_document
        delete_source_document(source_document_id)
        raise


@router.post("/jobs/from-draft", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def render_approved_document(background_tasks: BackgroundTasks, draft: ApprovedDraft):
    doc = load_source_document(draft.source_document_id)
    verify_and_canonicalize_citations(draft, doc)
    job = job_store.create_job(pipeline="business_documents", initial_stage="document_approved")
    log_pipeline_event("business_documents", "approved_draft_received", job_id=job.job_id, document_kind=draft.kind, source_document_id=draft.source_document_id)
    background_tasks.add_task(run_business_document_job, job.job_id, draft)
    return job


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_document_job(job_id: str):
    job = job_store.get_job(job_id)
    if not job or job.pipeline != "business_documents":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Business document job '{job_id}' not found.")
    return job


@router.get("/jobs/{job_id}/download")
async def download_document(job_id: str, format: str = "html"):
    job = job_store.get_job(job_id)
    if not job or job.pipeline != "business_documents" or job.status != JobState.DONE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document deliverable is not ready.")
    job_dir = Path(settings.WORK_DIR) / "jobs" / job_id
    if format.lower() == "pdf":
        path = job_dir / "document.pdf"
        if path.exists():
            return FileResponse(str(path), media_type="application/pdf", filename=f"{job.pipeline}_{job_id}.pdf")
    path = job_dir / "document.html"
    if path.exists():
        if format.lower() == "html_view":
            return HTMLResponse(path.read_text(encoding="utf-8"))
        return FileResponse(str(path), media_type="text/html", filename=f"{job.pipeline}_{job_id}.html")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requested document format was not found.")
