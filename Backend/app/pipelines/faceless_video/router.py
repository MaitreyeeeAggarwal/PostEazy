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

async def render_master_short_mp4(job_id: str, duration: int, title: str, narration: str = None) -> str:
    """Generates a 1080x1920 portrait master_shorts.mp4 deliverable with TTS neural voiceover audio using ffmpeg."""
    out_dir = Path(settings.WORK_DIR) / "jobs" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    mp4_path = out_dir / "master_shorts.mp4"
    audio_path = out_dir / "voiceover.wav"

    # Synthesize neural voiceover audio
    voice_text = narration or (
        "Welcome to Post Eazy Content Engine. "
        "Transforming dense documents into automated faceless kinetic videos. "
        "Here is your AI generated video short distilled from your source document."
    )

    try:
        from app.pipelines.faceless_video.assets.tts import TTSEngine
        tts = TTSEngine()
        tts.synth_scene(voice_text, str(audio_path))
    except Exception as tts_err:
        print(f"[TTS Synthesis Warning]: {tts_err}")

    # Build FFmpeg command with Video + Audio Voiceover stream
    if audio_path.exists():
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=0x090d16:s=1080x1920:d={duration}",
            "-i", str(audio_path),
            "-vf", (
                "drawtext=text='POSTEAZY CONTENT ENGINE':fontcolor=0x38bdf8:fontsize=38:x=(w-text_w)/2:y=(h-text_h)/2-180,"
                f"drawtext=text='{title[:30]}':fontcolor=white:fontsize=52:x=(w-text_w)/2:y=(h-text_h)/2-80,"
                f"drawtext=text='Master Deliverable • Job {job_id[:8]}':fontcolor=0x818cf8:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2+40"
            ),
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-r", "30",
            str(mp4_path)
        ]
    else:
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

async def run_video_job_pipeline(
    job_id: str,
    file_path: str,
    platform: Platform,
    duration_seconds: int = 60,
    typography_option: int = 1,
    song_option: int = 1,
    script_json: Optional[str] = None,
    brand_kit: Optional[dict] = None,
    style_template_key: str = "bold_creator"
):
    try:
        preset = get_preset(platform)
        print(f"\n=== Starting doc2video Pipeline: {file_path} ({duration_seconds}.0s target) ===", flush=True)
        print(f"[UI Sync] Typography Option: {typography_option}, Template: {style_template_key}, Song Option: {song_option}", flush=True)

        job_store.update_job(job_id, status=JobState.RUNNING, stage="Initializing pipeline...", progress=5)

        # Try running Orchestrator if available, otherwise generate fallback mp4
        try:
            from app.pipelines.faceless_video.orchestrator import PipelineOrchestrator
            from app.core.brand import BrandKit
            if isinstance(brand_kit, dict):
                clean_bkit = {k: v for k, v in brand_kit.items() if v is not None}
                b_kit = BrandKit(**clean_bkit)
            else:
                b_kit = brand_kit
            orch = PipelineOrchestrator(work_dir=str(Path(settings.WORK_DIR) / "jobs" / job_id))
            out_mp4 = await asyncio.to_thread(
                orch.run_pipeline,
                input_file=file_path,
                target_seconds=float(duration_seconds),
                preset="shorts",
                brand_kit=b_kit,
                style_template_key=style_template_key,
                song_option=song_option,
                job_id=job_id
            )
        except Exception as orch_err:
            import traceback
            print(f"[Orchestrator Fallback Traceback]:", flush=True)
            traceback.print_exc()
            v_script = generate_document_video_script(file_path, Path(file_path).name, platform, duration_seconds)
            script_data = v_script.model_dump()
            scenes_list = script_data.get("scenes", []) if isinstance(script_data, dict) else getattr(script_data, "scenes", [])
            narrative_text = " ".join([
                (s.get("narration", "") if isinstance(s, dict) else getattr(s, "narration", ""))
                for s in scenes_list
            ])
            out_mp4 = await render_master_short_mp4(job_id, duration_seconds, f"Faceless Video ({duration_seconds}s)", narration=narrative_text)

        print(f"SUCCESS! Video generated -> {out_mp4}\n", flush=True)

        output_urls = {
            "video_url": f"/api/video/jobs/{job_id}/download",
            "thumbnail_url": f"/api/video/jobs/{job_id}/thumbnail"
        }
        job_store.update_job(
            job_id,
            status=JobState.DONE,
            stage="Completed",
            progress=100,
            output_urls=output_urls
        )
    except Exception as e:
        import traceback
        print(f"[Pipeline Error Traceback]:", flush=True)
        traceback.print_exc()
        job_store.update_job(job_id, status=JobState.FAILED, stage="error", error=str(e))

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "because", "as", "what", "which",
    "this", "that", "these", "those", "then", "just", "so", "than", "such",
    "when", "who", "how", "where", "why", "we're", "you're", "they're", "it's",
    "i'm", "he's", "she's", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "to", "from", "in", "out", "on",
    "off", "over", "under", "again", "further", "then", "once", "here", "there",
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "no",
    "nor", "not", "only", "own", "same", "than", "too", "very", "can", "will", "should"
}

def extract_punchy_on_screen_text(narration: str, llm=None) -> str:
    """Extracts a punchy 2-4 word high-impact key phrase for on-screen text display using AI LLM with smart fallback."""
    if llm and llm.is_configured:
        try:
            prompt = (
                f"Extract a punchy 2 to 4 word on-screen title text card highlighting the core concept of this narration:\n"
                f"Narration: \"{narration}\"\n\n"
                f"Rules:\n"
                f"1. Never include filler words like 'we are', 'it is', 'here is', 'so', 'and', 'but', 'we're on'.\n"
                f"2. Capitalize each word.\n"
                f"3. Return ONLY the 2-4 word phrase."
            )
            res = llm.complete(prompt, max_tokens=25, timeout=4.0).strip().strip('"\'')
            if res and 2 <= len(res.split()) <= 5 and not any(res.lower().startswith(fw) for fw in ["here is", "we're on", "so", "and"]):
                return res.title()
        except Exception:
            pass

    import re
    clean_words = re.findall(r"\b[A-Za-z0-9%-]+\b", narration)
    meaningful = [w for w in clean_words if w.lower() not in STOP_WORDS]

    if len(meaningful) >= 2:
        return " ".join(meaningful[:3]).title()

    if clean_words:
        return " ".join(clean_words[:3]).title()

    return narration.title()

def generate_document_video_script(file_path: str, filename: str, platform: Platform, duration_seconds: int) -> VideoScript:
    """Generates dynamic VideoScript from document IR, claims, and narrative arc."""
    try:
        from app.services.ingest import load_document
        from app.pipelines.faceless_video.distil.claims import extract_claims
        from app.pipelines.faceless_video.plan.arc import plan_narrative_arc
        from app.pipelines.faceless_video.compile.scenes import compile_scenes
        from app.pipelines.faceless_video.core.llm import get_llm_client

        doc = load_document(file_path)
        claims = extract_claims(doc)
        beats = plan_narrative_arc(claims, target_seconds=float(duration_seconds))
        scenes = compile_scenes(beats, claims)
        llm = get_llm_client()

        preset = get_preset(platform)
        script_scenes = []
        for sc in scenes:
            screen_text = extract_punchy_on_screen_text(sc.narration, llm=llm)
            keywords = [k for k in sc.bg_query.split() if len(k) > 2]
            script_scenes.append({
                "narration": sc.narration,
                "keywords": keywords,
                "on_screen_text": screen_text
            })

        clean_words = [w.lower() for w in doc.title.replace("_", " ").replace(".", " ").split() if len(w) > 3]
        hashtags = list(dict.fromkeys(["video", "faceless", "ai", "contentengine"] + clean_words))[:6]

        return VideoScript(
            title=f"Video Script for {doc.title or filename}",
            scenes=script_scenes,
            caption=f"Distilled video short from '{doc.title or filename}' optimized for {preset.name}.",
            hashtags=hashtags
        )
    except Exception as err:
        print(f"[Script Generation Error]: {err}. Falling back to basic script.")
        preset = get_preset(platform)
        return VideoScript(
            title=f"Video Script for {filename}",
            scenes=[
                {
                    "narration": f"Key insights from {filename}.",
                    "keywords": ["document", "technology"],
                    "on_screen_text": filename[:20]
                }
            ],
            caption=f"Generated caption for {preset.name}.",
            hashtags=["video", "faceless", "ai"]
        )

@router.post("/scripts", response_model=VideoScript)
async def generate_video_script(
    file: UploadFile = File(...),
    platform: Platform = Form(Platform.INSTAGRAM),
    duration_seconds: int = Form(60)
):
    uploads_dir = Path(settings.WORK_DIR) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    temp_path = uploads_dir / f"temp_script_{file.filename}"
    
    file.file.seek(0)
    with open(temp_path, "wb") as f_out:
        f_out.write(await file.read())

    v_script = generate_document_video_script(str(temp_path), file.filename, platform, duration_seconds)
    
    if temp_path.exists():
        try:
            temp_path.unlink()
        except Exception:
            pass

    return v_script

@router.post("/jobs", response_model=JobStatus, status_code=status.HTTP_202_ACCEPTED)
async def create_video_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    platform: Platform = Form(Platform.INSTAGRAM),
    duration_seconds: int = Form(60),
    typography_option: int = Form(1),
    song_option: int = Form(1),
    template: Optional[str] = Form("bold_creator"),
    logo_file: Optional[UploadFile] = File(None),
    primary_color: Optional[str] = Form(None),
    secondary_color: Optional[str] = Form(None),
    badge_color: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    tagline: Optional[str] = Form(None),
    show_end_card: bool = Form(False),
    script_json: Optional[str] = Form(None),
    voice: Optional[str] = Form(None),
    theme: Optional[str] = Form("neon"),
    music: bool = Form(True)
):
    doc_res = await extract_document_text(file)
    job = job_store.create_job(pipeline="faceless_video", initial_stage="document_parsed")

    # Save uploaded file to disk
    uploads_dir = Path(settings.WORK_DIR) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / f"{job.job_id}_{file.filename}"
    
    file.file.seek(0)
    with open(file_path, "wb") as f_out:
        f_out.write(await file.read())

    # Handle brand kit logo upload if provided
    logo_path_str = None
    if logo_file and logo_file.filename:
        logo_dest = uploads_dir / f"{job.job_id}_logo_{logo_file.filename}"
        logo_file.file.seek(0)
        with open(logo_dest, "wb") as f_logo:
            f_logo.write(await logo_file.read())
        logo_path_str = str(logo_dest)

    brand_kit_dict = {
        "logo_path": logo_path_str,
        "primary_color": primary_color,
        "secondary_color": secondary_color,
        "badge_color": badge_color,
        "company_name": company_name,
        "tagline": tagline,
        "show_end_card": show_end_card
    }

    background_tasks.add_task(
        run_video_job_pipeline,
        job.job_id,
        str(file_path),
        platform,
        duration_seconds,
        typography_option,
        song_option,
        script_json,
        brand_kit_dict,
        template or "bold_creator"
    )

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

    # Create dummy file path for script job
    file_path = Path(settings.WORK_DIR) / "uploads" / f"{job.job_id}_script.txt"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f_out:
        f_out.write(str(payload.get("script", "")))

    background_tasks.add_task(run_video_job_pipeline, job.job_id, str(file_path), Platform(platform_str), 30)

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
    
    job_dir = Path(settings.WORK_DIR) / "jobs" / job_id
    mp4_path = job_dir / "master_shorts.mp4"
    if not mp4_path.exists():
        # Look for any master MP4 generated by orchestrator
        mp4_files = list(job_dir.glob("master_*.mp4"))
        if mp4_files:
            mp4_path = mp4_files[0]

    if mp4_path.exists():
        return FileResponse(path=str(mp4_path), media_type="video/mp4", filename=f"master_{job_id}.mp4")

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video deliverable master_shorts.mp4 not found on server.")
