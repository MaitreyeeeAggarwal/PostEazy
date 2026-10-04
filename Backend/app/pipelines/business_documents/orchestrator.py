from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.jobs import job_store
from app.pipelines.business_documents.plan_store import delete_source_document
from app.pipelines.business_documents.render_html import render_business_document_html
from app.pipelines.business_documents.render_pdf import render_business_document_pdf
from app.schemas import BusinessDocumentDraft, JobState
from app.core.pipeline_logging import log_pipeline_event


async def run_business_document_job(job_id: str, draft: BusinessDocumentDraft) -> None:
    try:
        log_pipeline_event("business_documents", "pipeline_started", job_id=job_id, document_kind=draft.kind, audience=draft.audience)
        job_store.update_job(job_id, status=JobState.RUNNING, stage="Preparing approved document...", progress=15)
        out_dir = Path(settings.WORK_DIR) / "jobs" / job_id
        out_dir.mkdir(parents=True, exist_ok=True)

        job_store.update_job(job_id, stage="Rendering web document...", progress=45, script=draft.model_dump())
        html_path = out_dir / "document.html"
        html_path.write_text(render_business_document_html(draft), encoding="utf-8")
        log_pipeline_event("business_documents", "html_rendered", job_id=job_id, output=html_path.name, bytes=html_path.stat().st_size)

        job_store.update_job(job_id, stage="Creating PDF document...", progress=75)
        pdf_path = out_dir / "document.pdf"
        render_business_document_pdf(draft, str(pdf_path))
        log_pipeline_event("business_documents", "pdf_rendered", job_id=job_id, output=pdf_path.name, exists=pdf_path.exists())

        job_store.update_job(
            job_id,
            status=JobState.DONE,
            stage="Completed",
            progress=100,
            output_urls={
                "html_url": f"/api/documents/jobs/{job_id}/download?format=html",
                "pdf_url": f"/api/documents/jobs/{job_id}/download?format=pdf",
            },
        )
        delete_source_document(draft.source_document_id)
        log_pipeline_event("business_documents", "pipeline_completed", job_id=job_id, output_formats=["html", "pdf"])
    except Exception as error:
        import traceback
        traceback.print_exc()
        log_pipeline_event("business_documents", "pipeline_failed", job_id=job_id, level=40, error_summary=str(error)[:300])
        job_store.update_job(job_id, status=JobState.FAILED, stage="error", error=str(error))
