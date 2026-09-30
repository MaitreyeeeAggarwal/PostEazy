import os
import sys
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Ensure workspace root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from orchestrator import PipelineOrchestrator
from core.llm import get_llm_client, NVIDIA_BASE_URL, DEFAULT_MODEL

app = FastAPI(title="doc2video - Kinetic Typography Video Generator")

WORK_DIR = ROOT_DIR / "work"
UPLOAD_DIR = WORK_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

STATIC_DIR = ROOT_DIR / "web" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class GenerateRequest(BaseModel):
    filename: str
    target_seconds: float = 60.0
    preset: str = "shorts"
    nvidia_api_key: Optional[str] = None
    nvidia_model: Optional[str] = DEFAULT_MODEL


@app.get("/")
def get_index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/status")
def get_status():
    llm = get_llm_client()
    return {
        "status": "online",
        "nvidia_api_configured": llm.is_configured,
        "default_model": DEFAULT_MODEL,
        "base_url": NVIDIA_BASE_URL
    }


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    return {
        "filename": file.filename,
        "size_bytes": len(content),
        "file_path": str(file_path.resolve())
    }


@app.post("/api/generate")
def generate_video(req: GenerateRequest):
    file_path = UPLOAD_DIR / req.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded file not found.")

    if req.nvidia_api_key:
        os.environ["NVIDIA_API_KEY"] = req.nvidia_api_key
    if req.nvidia_model:
        os.environ["NVIDIA_MODEL"] = req.nvidia_model

    orchestrator = PipelineOrchestrator(draft_mode=False)
    try:
        master_mp4_path = orchestrator.run_pipeline(
            input_file=str(file_path),
            target_seconds=req.target_seconds,
            preset=req.preset
        )
        video_filename = Path(master_mp4_path).name
        return {
            "status": "success",
            "video_url": f"/api/video/{video_filename}",
            "master_path": master_mp4_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/video/{filename}")
def stream_video(filename: str):
    video_path = WORK_DIR / filename
    if not video_path.exists():
        found = list(WORK_DIR.rglob(filename))
        if found:
            video_path = found[0]
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")
    return FileResponse(str(video_path), media_type="video/mp4", headers={"Accept-Ranges": "bytes"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=True)
