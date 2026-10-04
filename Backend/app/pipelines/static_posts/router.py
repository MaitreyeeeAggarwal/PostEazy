import asyncio
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, BackgroundTasks, Depends

from app.schemas import Platform, JobStatus, StaticPostScript, JobState
from app.services.ingest import extract_document_text
from app.jobs import job_store
from app.presets import get_preset
from app.core.pipeline_logging import log_pipeline_event

router = APIRouter(prefix="/api/posts", tags=["Pipeline A: Static Posts"])

async def run_static_post_pipeline(job_id: str, text: str, platform: Platform):
    try:
        log_pipeline_event("static_posts", "pipeline_started", job_id=job_id, platform=platform.value, source_chars=len(text))
        # Stage 1: Parsed
        job_store.update_job(job_id, status=JobState.RUNNING, stage="distilling_insights", progress=30)
        await asyncio.sleep(1.5)

        preset = get_preset(platform)
        script_data = {
            "title": "Static Carousel Output",
            "slides": [
                {
                    "layout_type": "hook",
                    "heading": "Transform Dense Docs Into Social Media Content",
                    "body": "Stop wasting hours rewriting decks and PDFs.",
                    "stat": None
                },
                {
                    "layout_type": "insight",
                    "heading": "Automated Content Pipelines",
                    "body": text[:180] + "...",
                    "stat": "85%"
                },
                {
                    "layout_type": "cta",
                    "heading": "Ready to scale your content?",
                    "body": "Follow for daily high-impact breakdowns.",
                    "stat": None
                }
            ],
            "caption": f"Generated caption tuned for {preset.name} voice.",
            "hashtags": ["content", "innovation", "insights", "tech", "growth"]
        }

        # Stage 2: Slide Rendering
        job_store.update_job(job_id, stage="rendering_slides", progress=70, script=script_data)
        log_pipeline_event("static_posts", "script_ready", job_id=job_id, slides=len(script_data["slides"]), preset=preset.name)
        await asyncio.sleep(2.0)

        # Stage 3: Done
        output_urls = {
            "download_url": f"/api/posts/jobs/{job_id}/download"
        }
        job_store.update_job(
            job_id,
            status=JobState.DONE,
            stage="done",
            progress=100,
            output_urls=output_urls
        )
        log_pipeline_event("static_posts", "pipeline_completed", job_id=job_id, output_formats=["download"])
    except Exception as e:
        log_pipeline_event("static_posts", "pipeline_failed", job_id=job_id, level=40, error_summary=str(e)[:300])
        job_store.update_job(job_id, status=JobState.FAILED, stage="error", error=str(e))

@router.post("/scripts", response_model=StaticPostScript)
async def generate_post_script(
    file: UploadFile = File(...),
    platform: Platform = Form(Platform.LINKEDIN)
):
    doc_res = await extract_document_text(file)
    preset = get_preset(platform)

    return StaticPostScript(
        title=f"Static Carousel for {doc_res.filename}",
        slides=[
            {
                "layout_type": "hook",
                "heading": "Transform Dense Docs Into Social Media Content",
                "body": "Stop wasting hours rewriting decks and PDFs.",
                "stat": None
            },
            {
                "layout_type": "insight",
                "heading": "Automated Content Pipelines",
                "body": doc_res.text[:180] + "...",
                "stat": "85%"
            },
            {
                "layout_type": "cta",
                "heading": "Ready to scale your content?",
                "body": "Follow for daily high-impact breakdowns.",
                "stat": None
            }
        ],
        caption=f"Generated caption tuned for {preset.name} voice.",
        hashtags=["content", "innovation", "insights", "tech", "growth"]
    )

@router.post("/jobs", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def create_static_post_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    platform: Platform = Form(Platform.LINKEDIN)
):
    doc_res = await extract_document_text(file)
    job = job_store.create_job(pipeline="static_posts", initial_stage="document_parsed")
    log_pipeline_event("static_posts", "source_ingested", job_id=job.job_id, filename=doc_res.filename, characters=doc_res.char_count, platform=platform.value)

    background_tasks.add_task(run_static_post_pipeline, job.job_id, doc_res.text, platform)

    return job

@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_static_post_job_status(job_id: str):
    job = job_store.get_job(job_id)
    if not job or job.pipeline != "static_posts":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Static post job '{job_id}' not found."
        )
    return job

@router.get("/jobs/{job_id}/download")
async def download_static_post_output(job_id: str):
    job = job_store.get_job(job_id)
    if not job or job.status != JobState.DONE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Output not ready or job failed.")
    return {"message": f"Static post slides ready for job {job_id}"}
