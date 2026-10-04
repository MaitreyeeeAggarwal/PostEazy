import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, BackgroundTasks, Body
from fastapi.responses import FileResponse, HTMLResponse

from app.config import settings
from app.schemas import (
    JobStatus, JobState, PresentationDeckScript, 
    UrlIngestRequest, PromptIngestRequest
)
from app.services.ingest import load_document, extract_url_text, extract_prompt_text
from app.jobs import job_store
from app.pipelines.presentation.core.llm_planner import plan_presentation_deck
from app.pipelines.presentation.orchestrator import run_presentation_job_pipeline

router = APIRouter(prefix="/api/presentation", tags=["Pipeline C: Presentation Deck"])


@router.post("/plan", response_model=PresentationDeckScript)
async def generate_presentation_plan(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    theme: str = Form("bold_tech")
):
    """Generates an AI presentation slide deck JSON outline from File, URL, or Prompt input."""
    uploads_dir = Path(settings.WORK_DIR) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    if file:
        temp_path = uploads_dir / f"temp_pres_{file.filename}"
        file.file.seek(0)
        with open(temp_path, "wb") as f_out:
            f_out.write(await file.read())
        doc = load_document(str(temp_path))
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
    elif url:
        doc = load_document(url)
    elif prompt:
        doc = load_document(prompt)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either a file, url, or prompt."
        )

    return plan_presentation_deck(doc, theme=theme)


@router.post("/jobs", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def create_presentation_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    theme: str = Form("bold_tech"),
    script_json: Optional[str] = Form(None)
):
    """Launch presentation slide deck generation pipeline from uploaded file."""
    job = job_store.create_job(pipeline="presentation_slides", initial_stage="file_received")

    uploads_dir = Path(settings.WORK_DIR) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / f"{job.job_id}_{file.filename}"
    
    file.file.seek(0)
    with open(file_path, "wb") as f_out:
        f_out.write(await file.read())

    parsed_script = None
    if script_json:
        try:
            parsed_script = json.loads(script_json)
        except Exception:
            pass

    background_tasks.add_task(
        run_presentation_job_pipeline,
        job.job_id,
        str(file_path),
        theme,
        parsed_script
    )

    return job


@router.post("/jobs/from-url", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def create_presentation_job_from_url(
    background_tasks: BackgroundTasks,
    payload: UrlIngestRequest,
    theme: str = "bold_tech"
):
    """Launch presentation slide deck generation directly from a Web URL."""
    job = job_store.create_job(pipeline="presentation_slides", initial_stage="url_ingested")
    uploads_dir = Path(settings.WORK_DIR) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / f"{job.job_id}_url.txt"
    
    doc_res = extract_url_text(payload.url)
    with open(file_path, "w", encoding="utf-8") as f_out:
        f_out.write(doc_res.text)

    background_tasks.add_task(run_presentation_job_pipeline, job.job_id, str(file_path), theme)
    return job


@router.post("/jobs/from-prompt", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def create_presentation_job_from_prompt(
    background_tasks: BackgroundTasks,
    payload: PromptIngestRequest,
    theme: str = "bold_tech"
):
    """Launch presentation slide deck generation directly from a topic prompt."""
    job = job_store.create_job(pipeline="presentation_slides", initial_stage="prompt_received")
    uploads_dir = Path(settings.WORK_DIR) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / f"{job.job_id}_prompt.txt"
    
    doc_res = extract_prompt_text(payload.prompt)
    with open(file_path, "w", encoding="utf-8") as f_out:
        f_out.write(doc_res.text)

    background_tasks.add_task(run_presentation_job_pipeline, job.job_id, str(file_path), theme)
    return job


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_presentation_job_status(job_id: str):
    job = job_store.get_job(job_id)
    if not job or job.pipeline != "presentation_slides":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Presentation job '{job_id}' not found."
        )
    return job


@router.get("/jobs/{job_id}/download")
async def download_presentation_output(job_id: str, format: str = "html"):
    job = job_store.get_job(job_id)
    if not job or job.status != JobState.DONE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Presentation deliverable not ready or job failed.")

    job_dir = Path(settings.WORK_DIR) / "jobs" / job_id

    if format.lower() == "pdf":
        pdf_path = job_dir / "presentation.pdf"
        if pdf_path.exists():
            return FileResponse(path=str(pdf_path), media_type="application/pdf", filename=f"presentation_{job_id[:8]}.pdf")
    elif format.lower() == "pptx":
        pptx_path = job_dir / "presentation.pptx"
        if pptx_path.exists():
            return FileResponse(path=str(pptx_path), media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename=f"presentation_{job_id[:8]}.pptx")

    html_path = job_dir / "presentation.html"
    if html_path.exists():
        if format.lower() == "html_view":
            with open(html_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return FileResponse(path=str(html_path), media_type="text/html", filename=f"presentation_{job_id[:8]}.html")

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requested presentation format not found.")
