# SIH Backend - FastAPI Project

Modular FastAPI backend service for file upload, asynchronous background processing, in-memory job state tracking, and AI generation pipeline integration.

---

## 📁 Project Structure

```
sih-backend/
├── main.py                     # FastAPI application, CORS, in-memory job state & endpoints
├── models.py                   # Pydantic schemas (JobState, UploadResponse, etc.)
├── services/
│   ├── __init__.py             # Exports service singletons and classes
│   ├── parser.py               # File parsing service (reads & extracts file contents)
│   ├── generator.py            # AI synthesis & generation orchestration
│   ├── renderer.py             # Result formatting & markdown/JSON rendering
│   └── gemini_client.py        # Gemini API client wrapper
├── storage/                    # Directory for uploaded files (subfolder per job)
│   └── .gitkeep
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment variables
├── .env                        # Local environment settings
└── .gitignore                  # Git ignore rules
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ installed

### 2. Setup Virtual Environment (Recommended)

```bash
# In C:\Users\HP\sih-backend
python -m venv .venv

# Activate on Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Open `.env` and configure your settings:
```env
GEMINI_API_KEY=your_actual_gemini_api_key
PORT=8000
DEBUG=True
```

### 5. Run the Server

```bash
# Using uvicorn directly
uvicorn main:app --reload --port 8000

# Or run the script
python main.py
```

The interactive API documentation is accessible at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🔌 API Endpoints

### 1. `POST /upload`
Uploads multiple files and starts an asynchronous background processing job.

- **Request**: `multipart/form-data` with form field `files`
- **Response**: `202 Accepted`

```bash
curl -X POST "http://127.0.0.1:8000/upload" \
  -F "files=@sample1.txt" \
  -F "files=@sample2.csv"
```

```json
{
  "job_id": "b73a6288-5eb8-42fa-9d04-4ad2ee3c3733",
  "message": "Files uploaded successfully. Processing started.",
  "files_count": 2,
  "filenames": ["sample1.txt", "sample2.csv"]
}
```

---

### 2. `GET /status/{job_id}`
Checks the current processing status of a job.

- **Response**: `200 OK`

```bash
curl -X GET "http://127.0.0.1:8000/status/b73a6288-5eb8-42fa-9d04-4ad2ee3c3733"
```

```json
{
  "job_id": "b73a6288-5eb8-42fa-9d04-4ad2ee3c3733",
  "status": "completed",
  "created_at": "2026-09-10T09:45:00Z",
  "updated_at": "2026-09-10T09:45:02Z",
  "files_count": 2,
  "filenames": ["sample1.txt", "sample2.csv"],
  "error": null
}
```

---

### 3. `GET /result/{job_id}`
Retrieves the processed output and rendered results for a job.

- **Response**: `200 OK`

```bash
curl -X GET "http://127.0.0.1:8000/result/b73a6288-5eb8-42fa-9d04-4ad2ee3c3733"
```

```json
{
  "job_id": "b73a6288-5eb8-42fa-9d04-4ad2ee3c3733",
  "status": "completed",
  "result": {
    "job_id": "b73a6288-5eb8-42fa-9d04-4ad2ee3c3733",
    "rendered_at": "2026-09-10T09:45:02.123456Z",
    "status": "ready",
    "data": {
      "job_id": "b73a6288-5eb8-42fa-9d04-4ad2ee3c3733",
      "processed_file_count": 2,
      "summary": "Processed 2 file(s) successfully.",
      "insights": "..."
    },
    "render_format": "json"
  },
  "error": null
}
```

---

## 🛡️ CORS Middleware
CORS is configured in `main.py` allowing all origins (`*`), headers, and methods for seamless frontend integration during development.
