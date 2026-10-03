from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

# --- Platform Enums ---
class Platform(str, Enum):
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"

class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

# --- Authentication Schemas ---
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

# --- Input Enums ---
class InputType(str, Enum):
    FILE = "file"
    URL = "url"
    VIDEO = "video"
    IMAGE = "image"
    PROMPT = "prompt"

# --- Ingestion Schemas ---
class UrlIngestRequest(BaseModel):
    url: str

class PromptIngestRequest(BaseModel):
    prompt: str

class DocumentExtractResponse(BaseModel):
    filename: str
    input_type: InputType = InputType.FILE
    char_count: int
    page_or_slide_count: int
    text: str
    truncated: bool

# --- Shared Job Schemas ---
class JobStatus(BaseModel):
    job_id: str
    pipeline: str  # "static_posts" or "faceless_video"
    status: JobState
    stage: str
    progress: int = Field(ge=0, le=100)
    created_at: str
    updated_at: str
    error: Optional[str] = None
    script: Optional[Dict[str, Any]] = None
    output_urls: Optional[Dict[str, str]] = None

# --- Video Script Schemas (Pipeline B placeholder contract) ---
class VideoScene(BaseModel):
    narration: str
    keywords: List[str]
    on_screen_text: str

class VideoScript(BaseModel):
    title: str
    scenes: List[VideoScene]
    caption: str
    hashtags: List[str]

# --- Static Post Script Schemas (Pipeline A placeholder contract) ---
class SlideContent(BaseModel):
    layout_type: str = "insight"  # hook, insight, big_stat, list, quote, cta
    heading: str
    body: str
    stat: Optional[str] = None

class StaticPostScript(BaseModel):
    title: str
    slides: List[SlideContent]
    caption: str
    hashtags: List[str]
