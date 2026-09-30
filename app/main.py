import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.auth.router import router as auth_router
from app.pipelines.static_posts.router import router as static_posts_router
from app.pipelines.faceless_video.router import router as faceless_video_router
from app.services.media import check_ffmpeg_available

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for Content Engine: Transforming documents into social media static posts & faceless videos."
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Event: Ensure runtime data directories exist
@app.on_event("startup")
async def startup_event():
    os.makedirs(settings.WORK_DIR, exist_ok=True)
    os.makedirs(settings.MUSIC_DIR, exist_ok=True)
    os.makedirs(settings.FONTS_DIR, exist_ok=True)

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Static Files & UI Mounting
frontend_dir = Path(__file__).parent.parent / "frontend"
static_dir = Path(__file__).parent / "static"

ui_dir = frontend_dir if frontend_dir.exists() else static_dir

if ui_dir.exists():
    app.mount("/css", StaticFiles(directory=str(ui_dir / "css")), name="css") if (ui_dir / "css").exists() else None
    app.mount("/js", StaticFiles(directory=str(ui_dir / "js")), name="js") if (ui_dir / "js").exists() else None
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static") if static_dir.exists() else None

@app.get("/", include_in_schema=False)
async def read_index():
    index_path = ui_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "PostEazy Content Engine API server running."}

# Register Routers
app.include_router(auth_router)
app.include_router(static_posts_router)
app.include_router(faceless_video_router)

@app.get("/health", tags=["Health"])
async def health_check():
    ffmpeg_ok = check_ffmpeg_available()
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "ffmpeg_available": ffmpeg_ok,
        "configured_keys": {
            "anthropic": bool(settings.ANTHROPIC_API_KEY),
            "pexels": bool(settings.PEXELS_API_KEY)
        }
    }

