import os
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, BackgroundTasks, Body
from fastapi.responses import FileResponse

from app.config import settings
from app.schemas import Platform, JobStatus, VideoScript, JobState
from app.services.ingest import extract_document_text
from app.jobs import job_store
from app.presets import get_preset

router = APIRouter(prefix="/api/video", tags=["Pipeline B: Faceless Video"])

async def render_master_short_mp4(job_id: str, duration: int, title: str) -> str:
    """Generates a 1080x1920 portrait master_shorts.mp4 deliverable using ffmpeg."""
    out_dir = Path(settings.WORK_DIR) / "jobs" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    mp4_path = out_dir / "master_shorts.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x090d16:s=1080x1920:d={duration}",
        "-vf", (
            "drawtext=text='POSTEAZY CONTENT ENGINE':fontcolor=0x38bdf8:fontsize=38:x=(w-text_w)/2:y=(h-text_h)/2-180,"
            f"drawtext=text='{title[:30]}':fontcolor=white:fontsize=52:x=(w-text_w)/2:y=(h-text_h)/2-80,"
            f"drawtext=text='Master Deliverable • Job {job_id[:8]}':fontcolor=0x818cf8:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2+40"
        ),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        str(mp4_path)
    ]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await proc.communicate()
    return str(mp4_path)

async def run_video_job_pipeline(job_id: str, text: str, platform: Platform, duration_seconds: int = 30):
    try:
        # Stage 1: Document & Script
        job_store.update_job(job_id, status=JobState.RUNNING, stage="writing_script", progress=25)
        await asyncio.sleep(1.0)

        preset = get_preset(platform)
        script_data = {
            "title": "Generated Faceless Video Script",
            "scenes": [
                {
                    "narration": "Are you struggling to turn dense documents into engaging video content?",
                    "keywords": ["office worker confused", "laptop typing"],
                    "on_screen_text": "Transform Your Docs"
                },
                {
                    "narration": "Here is how automated content engines distill key facts in seconds.",
                    "keywords": ["data dashboard", "technology code"],
                    "on_screen_text": "Instant Distillation"
                },
                {
                    "narration": "Follow us to build your audience faster with automated content.",
                    "keywords": ["person smiling phone", "success growth"],
                    "on_screen_text": "Start Building Today"
                }
            ],
            "caption": f"Generated caption tuned for {preset.name} voice.",
            "hashtags": ["video", "faceless", "ai", "contentengine", "growth"]
        }

        # Stage 2: Voiceover & Assets
        job_store.update_job(job_id, stage="recording_voiceover", progress=55, script=script_data)
        await asyncio.sleep(1.5)

        # Stage 3: Rendering Video Clips (Generate master_shorts.mp4)
        job_store.update_job(job_id, stage="rendering_video", progress=85)
        await render_master_short_mp4(job_id, duration_seconds, "Faceless Kinetic Video")

        # Stage 4: Done
        output_urls = {
            "video_url": f"/api/video/jobs/{job_id}/download",
            "thumbnail_url": f"/api/video/jobs/{job_id}/thumbnail"
        }
        job_store.update_job(
            job_id,
            status=JobState.DONE,
            stage="done",
            progress=100,
            output_urls=output_urls
        )
    except Exception as e:
        job_store.update_job(job_id, status=JobState.FAILED, stage="error", error=str(e))

@router.post("/scripts", response_model=VideoScript)
async def generate_video_script(
    file: UploadFile = File(...),
    platform: Platform = Form(Platform.INSTAGRAM),
    duration_seconds: int = Form(30)
):
    doc_res = await extract_document_text(file)
    preset = get_preset(platform)

    return VideoScript(
        title=f"Video Script for {doc_res.filename}",
        scenes=[
            {
                "narration": "Are you struggling to turn dense documents into engaging video content?",
                "keywords": ["office worker confused", "laptop typing"],
                "on_screen_text": "Transform Your Docs"
            },
            {
                "narration": "Here is how automated content engines distill key facts in seconds.",
                "keywords": ["data dashboard", "technology code"],
                "on_screen_text": "Instant Distillation"
            },
            {
                "narration": "Follow us to build your audience faster with automated content.",
                "keywords": ["person smiling phone", "success growth"],
                "on_screen_text": "Start Building Today"
            }
        ],
        caption=f"Generated caption tuned for {preset.name} voice.",
        hashtags=["video", "faceless", "ai", "contentengine", "growth"]
    )

@router.post("/jobs", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def create_video_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    platform: Platform = Form(Platform.INSTAGRAM),
    duration_seconds: int = Form(30),
    voice: Optional[str] = Form(None),
    music: bool = Form(True)
):
    doc_res = await extract_document_text(file)
    job = job_store.create_job(pipeline="faceless_video", initial_stage="document_parsed")

    background_tasks.add_task(run_video_job_pipeline, job.job_id, doc_res.text, platform, duration_seconds)

    return job

@router.post("/jobs/from-script", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def create_video_job_from_script(
    background_tasks: BackgroundTasks,
    payload: dict = Body(...)
):
    platform_str = payload.get("platform", Platform.INSTAGRAM.value)
    job = job_store.create_job(pipeline="faceless_video", initial_stage="script_received")
    
    if "script" in payload:
        job_store.update_job(job.job_id, script=payload["script"])

    background_tasks.add_task(run_video_job_pipeline, job.job_id, "Script payload", Platform(platform_str))

    return job

@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_video_job_status(job_id: str):
    job = job_store.get_job(job_id)
    if not job or job.pipeline != "faceless_video":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video job '{job_id}' not found."
        )
    return job

@router.get("/jobs/{job_id}/download")
async def download_video_output(job_id: str):
    job = job_store.get_job(job_id)
    if not job or job.status != JobState.DONE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Output not ready or job failed.")
    
    mp4_path = Path(settings.WORK_DIR) / "jobs" / job_id / "master_shorts.mp4"
    if mp4_path.exists():
        return FileResponse(path=str(mp4_path), media_type="video/mp4", filename=f"master_{job_id}.mp4")

    # Fallback response if video is still generating
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video deliverable master_shorts.mp4 not found on server.")
