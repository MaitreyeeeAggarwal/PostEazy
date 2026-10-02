# Content Engine Backend API

High-performance FastAPI backend for **Content Engine**: turning dense PDFs, PPTs, TXTs, and MDs into postable social media content (Pipeline A: Static Posts, Pipeline B: Faceless Videos).

## Project Structure

```
c:\development\SiH\PostEazy\
├── frontend/                       # Separated Frontend SPA Web Application
└── Backend/                        # FastAPI Backend API Server
    ├── app/
│   ├── main.py                     # FastAPI application setup, CORS & health checks
│   ├── config.py                   # Pydantic settings & environment configuration
│   ├── schemas.py                  # Pydantic data models (Auth, JobStatus, Presets, Scripts)
│   ├── presets.py                  # Platform style presets (LinkedIn, Instagram)
│   ├── jobs.py                     # Thread-safe in-memory job store & state manager
│   ├── auth/                       # Authentication Module
│   │   ├── __init__.py
│   │   ├── security.py             # JWT generation, password hashing & user validation
│   │   └── router.py               # Auth endpoints (/register, /login, /me)
│   ├── pipelines/                  # Individual Pipeline Directories
│   │   ├── static_posts/           # Pipeline A: Static Posts (Carousels/Images)
│   │   │   ├── __init__.py
│   │   │   └── router.py           # Endpoints for script generation & job rendering
│   │   └── faceless_video/         # Pipeline B: Faceless Video (9:16 MP4)
│   │       ├── __init__.py
│   │       └── router.py           # Endpoints for script generation, jobs & review flow
│   └── services/                   # Shared Services Layer
│       ├── __init__.py
│       ├── ingest.py               # Text extractor (PDF page markers, PPTX slide markers)
│       └── media.py                # Subprocess & ffprobe media helpers
├── data/                           # Work directory for outputs, caches, music, fonts
├── .env.example                    # Environment variables template
├── requirements.txt                # Python package dependencies
└── README.md                       # Documentation
```

## Features Built

1. **Shared Document Ingestion Layer** (`app/services/ingest.py`):
   - Extracts structured text with `[Page n]` / `[Slide n]` markers from PDF, PPTX, TXT, MD.
   - Extracts table cells (`cell 1 | cell 2`) and speaker notes for PPTX.
   - Rejects scanned/image-only documents (<200 chars) with `422 Unprocessable Entity`.
   - Truncation guard to `MAX_SOURCE_CHARS` (60,000 chars default).

2. **Authentication System** (`app/auth/`):
   - User registration (`POST /api/auth/register`).
   - JWT authentication login (`POST /api/auth/login`).
   - OAuth2 Bearer token validation and current user endpoint (`GET /api/auth/me`).

3. **Platform Presets** (`app/presets.py`):
   - Configurable tone, speaking rate, neural voice, active-word colors, font sizing, margin offsets, and background dimming for **LinkedIn** and **Instagram**.

4. **Thread-Safe Job Manager** (`app/jobs.py`):
   - Queueing, state tracking (`queued`, `running`, `done`, `failed`), stage logging, and progress reporting (0–100%).

5. **Two Separate Pipeline Directories**:
   - `app/pipelines/static_posts/`: Ready for insertion of Playwright/HTML rendering logic.
   - `app/pipelines/faceless_video/`: Ready for insertion of TTS + Pexels + ffmpeg composition logic.

## Quick Start

### 1. Installation
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and fill in API keys:
```bash
cp .env.example .env
```

### 3. Run the Backend
```bash
uvicorn app.main:app --reload --port 8000
```
Interactive API Docs available at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Run with Docker / Docker Compose

From the root `PostEazy` directory:

```bash
# Using Docker Compose (Recommended)
docker compose up --build

# Or building Docker image directly
docker build -t posteazy .
docker run -p 8000:8000 --env-file Backend/.env posteazy
```
