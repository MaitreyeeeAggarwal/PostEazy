import os
import sys
from pathlib import Path

# Ensure Backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

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

from app.database import engine, Base
from app import models  # Register models

# Startup Event: Ensure runtime data directories and DB tables exist
@app.on_event("startup")
async def startup_event():
    os.makedirs(settings.WORK_DIR, exist_ok=True)
    os.makedirs(settings.MUSIC_DIR, exist_ok=True)
    os.makedirs(settings.FONTS_DIR, exist_ok=True)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[Database Init Warning] Could not initialize database tables: {e}")

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Static Files & UI Mounting
frontend_dir_env = os.getenv("FRONTEND_DIR")
if frontend_dir_env:
    frontend_dir = Path(frontend_dir_env)
else:
    # Check candidates: PostEazy/frontend (sibling to Backend), Backend/frontend, and root /frontend
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "frontend",  # PostEazy/frontend
        Path(__file__).resolve().parent.parent / "frontend",         # Backend/frontend
        Path("/frontend"),
    ]
    frontend_dir = next((p for p in candidates if p.exists()), candidates[0])

if frontend_dir.exists():
    if (frontend_dir / "css").exists():
        app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")
    if (frontend_dir / "js").exists():
        app.mount("/js", StaticFiles(directory=str(frontend_dir / "js")), name="js")

@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
async def read_index():
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "PostEazy Content Engine API server running."}

@app.get("/studio", include_in_schema=False)
@app.get("/studio.html", include_in_schema=False)
async def read_studio():
    studio_path = frontend_dir / "studio.html"
    if studio_path.exists():
        return FileResponse(str(studio_path))
    return FileResponse(str(frontend_dir / "index.html"))

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    fav = frontend_dir / "favicon.ico"
    if fav.exists():
        return FileResponse(str(fav))
    return FileResponse(str(frontend_dir / "index.html"))

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

