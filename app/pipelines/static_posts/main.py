import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Path as FastAPIPath, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse

from models import (
    JobResultResponse,
    JobState,
    JobStatus,
    JobStatusResponse,
    UploadedFileInfo,
    UploadResponse,
)
from services import generator_service, parser_service, renderer_service

# Load environment configuration
load_dotenv()

# App configuration
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="SIH Backend API",
    description="FastAPI backend with file upload, async job processing, and Gemini-powered services.",
    version="1.0.0",
)

# CORS middleware allowing all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    """Ensure Swagger UI properly renders file upload picker widget for multipart file uploads."""
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Swagger UI requires format: 'binary' instead of OpenAPI 3.1 contentMediaType to display file inputs
    for schema in openapi_schema.get("components", {}).get("schemas", {}).values():
        for prop in schema.get("properties", {}).values():
            if prop.get("contentMediaType") == "application/octet-stream":
                del prop["contentMediaType"]
                prop["format"] = "binary"
            if isinstance(prop.get("items"), dict) and prop["items"].get("contentMediaType") == "application/octet-stream":
                del prop["items"]["contentMediaType"]
                prop["items"]["format"] = "binary"
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# In-memory dictionary for job state tracking (No DB)
jobs: Dict[str, JobState] = {}


async def process_job(job_id: str) -> None:
    """Background task processing uploaded files through parser, generator, and renderer."""
    job = jobs.get(job_id)
    if not job:
        return

    try:
        job.status = JobStatus.PROCESSING
        job.updated_at = datetime.now(timezone.utc)

        # 1. Parse uploaded files
        file_paths = [file_info.saved_path for file_info in job.files]
        parsed_files = parser_service.parse_files(file_paths)

        # 2. Generate analysis and synthesis
        generated_data = await generator_service.generate_summary_and_analysis(
            job_id=job_id,
            parsed_files=parsed_files,
        )

        # 3. Render final output
        rendered_result = renderer_service.render_json_result(
            job_id=job_id,
            generated_data=generated_data,
        )

        job.status = JobStatus.COMPLETED
        job.result = rendered_result
        job.updated_at = datetime.now(timezone.utc)

        # 4. Aggregate file analyses and generate social media content hooks
        file_analyses = generated_data.get("file_analyses", [])
        parser_service.aggregate_and_generate_hooks(
            file_analyses=file_analyses,
            job_id=job_id,
            jobs=jobs,
        )

    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.updated_at = datetime.now(timezone.utc)


@app.get("/", tags=["Health"])
async def root():
    """Root health check and API metadata."""
    return {
        "status": "online",
        "service": "SIH Backend API",
        "endpoints": {
            "upload": "POST /upload",
            "status": "GET /status/{job_id}",
            "result": "GET /result/{job_id}",
            "image": "GET /image/{job_id}/{filename} (serves from storage/{job_id}/renders/; filename must come from result['renders'], e.g. 'linkedin_1.png', NOT original uploaded filename)",
            "docs": "GET /docs",
        },
    }


@app.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Jobs"],
)
async def upload_files(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Accepts multiple file uploads, saves them to the storage/ folder under a dedicated
    job folder, registers the job in memory, and triggers background processing.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were provided.",
        )

    job_id = str(uuid.uuid4())
    job_storage_dir = STORAGE_DIR / job_id
    job_storage_dir.mkdir(parents=True, exist_ok=True)

    saved_files: List[UploadedFileInfo] = []
    saved_filenames: List[str] = []

    for upload_file in files:
        filename = Path(upload_file.filename).name if upload_file.filename else f"file_{uuid.uuid4().hex[:8]}"
        destination_path = job_storage_dir / filename

        # Write uploaded file stream to storage
        with open(destination_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        size_bytes = destination_path.stat().st_size

        saved_files.append(
            UploadedFileInfo(
                filename=filename,
                saved_path=str(destination_path.resolve()),
                size_bytes=size_bytes,
                content_type=upload_file.content_type,
            )
        )
        saved_filenames.append(filename)

    # Initialize job state in memory
    job_state = JobState(
        job_id=job_id,
        status=JobStatus.PENDING,
        files=saved_files,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    jobs[job_id] = job_state

    # Enqueue async background processing
    background_tasks.add_task(process_job, job_id)

    return UploadResponse(
        job_id=job_id,
        message="Files uploaded successfully. Processing started.",
        files_count=len(saved_files),
        filenames=saved_filenames,
    )


@app.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    tags=["Jobs"],
)
async def get_job_status(job_id: str):
    """Retrieve current processing status for a given job_id."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        files_count=len(job.files),
        filenames=[f.filename for f in job.files],
        error=job.error,
    )


@app.get(
    "/result/{job_id}",
    response_model=JobResultResponse,
    tags=["Jobs"],
)
async def get_job_result(job_id: str):
    """
    Retrieve output result for a given job_id.
    Returns current status and any generated result or error details.
    """
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    return JobResultResponse(
        job_id=job.job_id,
        status=job.status,
        result=job.result,
        error=job.error,
    )


# ============================================================================
# NOTE: The /image/{job_id}/{filename} endpoint serves rendered post images
# directly from storage/{job_id}/renders/.
# The `filename` parameter MUST come from the "renders" array in the /result/{job_id}
# response (e.g., "linkedin_1.png", "instagram_2.png", "twitter_3.png"),
# NOT the original uploaded document filename (e.g. "document.pdf").
# ============================================================================
@app.get(
    "/image/{job_id}/{filename}",
    tags=["Renders"],
    response_class=FileResponse,
    summary="Serve rendered post image",
    description=(
        "Serve a rendered PNG file directly from `storage/{job_id}/renders/` so that clients or frontends "
        "can embed it in an `<img>` tag or download it.\n\n"
        "**Important Usage Note:** The `filename` path parameter MUST match one of the rendered filenames "
        "returned in the `renders` array of the `/result/{job_id}` response (for example: `linkedin_1.png`, "
        "`instagram_2.png`, or `twitter_3.png`). It is **NOT** the original uploaded document filename."
    ),
    responses={
        200: {
            "description": "Rendered PNG image file.",
            "content": {"image/png": {}},
        },
        404: {
            "description": "Rendered image not found. Ensure the filename comes from result['renders'].",
        },
    },
)
async def get_rendered_image(
    job_id: str = FastAPIPath(
        ...,
        description="The unique job identifier returned by POST /upload.",
        openapi_examples={"default": {"summary": "Sample Job ID", "value": "fccfdea8-33bf-4389-8418-9717f9095919"}},
    ),
    filename: str = FastAPIPath(
        ...,
        description="Rendered filename from result['renders'] (e.g. 'linkedin_1.png', 'instagram_1.png', 'twitter_1.png'). Do NOT pass the original uploaded file name.",
        openapi_examples={"default": {"summary": "Sample Rendered File", "value": "linkedin_1.png"}},
    ),
):
    """
    Serve a rendered PNG file directly from storage/{job_id}/renders/.

    Example:
        GET /image/fccfdea8-33bf-4389-8418-9717f9095919/linkedin_1.png

    NOTE: The filename MUST come from the "renders" array in the /result response
    (e.g., "linkedin_1.png", "instagram_2.png", "twitter_3.png"), NOT the original
    uploaded document filename.
    """
    safe_filename = Path(filename).name
    image_path = STORAGE_DIR / job_id / "renders" / safe_filename

    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Rendered image '{safe_filename}' for job '{job_id}' not found. "
                "Ensure the filename comes from the 'renders' array in /result/{job_id} "
                "(e.g., 'linkedin_1.png'), not the original uploaded filename."
            ),
        )

    return FileResponse(
        path=str(image_path),
        media_type="image/png",
        filename=safe_filename,
    )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "true").lower() == "true"

    uvicorn.run("main:app", host=host, port=port, reload=debug)
