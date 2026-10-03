import os
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException, status

from app.config import settings
from app.schemas import DocumentExtractResponse, InputType
from app.core.ir import DocIR, Block
from app.services.ingest.base import DocumentExtractor
from app.services.ingest.pptx import PPTXExtractor
from app.services.ingest.pdf import PDFExtractor
from app.services.ingest.docx import DOCXExtractor
from app.services.ingest.markdown import MarkdownExtractor
from app.services.ingest.url import URLExtractor
from app.services.ingest.image import ImageExtractor
from app.services.ingest.video_ingest import VideoIngestExtractor
from app.services.ingest.prompt_script import PromptSynthesizer

DOC_EXTENSIONS = {".pdf", ".pptx", ".ppt", ".docx", ".doc", ".txt", ".md", ".markdown"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}

ALLOWED_EXTENSIONS = DOC_EXTENSIONS | IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def load_document(source: str, input_type: Optional[InputType] = None) -> DocIR:
    """
    Common data extractor used across all pipelines (Static Posts & Faceless Video).
    Extracts structured document IR (DocIR) from Files, URLs, Videos, Images, or Prompts.
    """
    # 1. URL Source
    if input_type == InputType.URL or source.startswith(("http://", "https://")):
        extractor: DocumentExtractor = URLExtractor()
        return extractor.extract(source)

    # 2. Raw Prompt Source
    if input_type == InputType.PROMPT or not os.path.exists(source):
        extractor = PromptSynthesizer()
        return extractor.extract(source)

    # 3. File Path Ingestion
    path = Path(source)
    suffix = path.suffix.lower()

    if suffix in (".pptx", ".ppt"):
        extractor = PPTXExtractor()
    elif suffix == ".pdf":
        extractor = PDFExtractor()
    elif suffix in (".docx", ".doc"):
        extractor = DOCXExtractor()
    elif suffix in (".md", ".markdown", ".txt"):
        extractor = MarkdownExtractor()
    elif suffix in IMAGE_EXTENSIONS:
        extractor = ImageExtractor()
    elif suffix in VIDEO_EXTENSIONS:
        extractor = VideoIngestExtractor()
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    return extractor.extract(source)


def format_doc_ir_response(doc_ir: DocIR, filename: str, input_type: InputType) -> DocumentExtractResponse:
    """Helper to convert DocIR into standardized DocumentExtractResponse."""
    formatted_parts = []
    locators_seen = set()

    for b in doc_ir.blocks:
        loc = b.source.locator
        if loc not in locators_seen:
            locators_seen.add(loc)
            formatted_parts.append(f"[{loc}]")
        formatted_parts.append(b.text)

    raw_text = "\n".join(formatted_parts)
    if not raw_text.strip():
        raw_text = f"Content extracted from {filename}"

    truncated = False
    if len(raw_text) > settings.MAX_SOURCE_CHARS:
        raw_text = raw_text[: settings.MAX_SOURCE_CHARS]
        truncated = True

    return DocumentExtractResponse(
        filename=filename,
        input_type=input_type,
        char_count=len(raw_text),
        page_or_slide_count=max(1, len(locators_seen)),
        text=raw_text,
        truncated=truncated
    )


async def extract_document_text(file: UploadFile) -> DocumentExtractResponse:
    """HTTP upload handler that extracts text and metadata into DocumentExtractResponse for uploaded files (Docs/Images/Videos)."""
    filename = file.filename or "uploaded_media"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    content_bytes = await file.read()
    file_size_mb = len(content_bytes) / (1024 * 1024)
    if file_size_mb > settings.MAX_UPLOAD_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_MB} MB"
        )

    temp_dir = Path(settings.WORK_DIR) / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file_path = temp_dir / f"upload_{os.urandom(8).hex()}{ext}"

    try:
        with open(temp_file_path, "wb") as temp_f:
            temp_f.write(content_bytes)

        # Detect InputType
        if ext in IMAGE_EXTENSIONS:
            itype = InputType.IMAGE
        elif ext in VIDEO_EXTENSIONS:
            itype = InputType.VIDEO
        else:
            itype = InputType.FILE

        doc_ir: DocIR = load_document(str(temp_file_path), input_type=itype)
        return format_doc_ir_response(doc_ir, filename, itype)

    finally:
        if temp_file_path.exists():
            try:
                os.remove(temp_file_path)
            except Exception:
                pass


def extract_url_text(url: str) -> DocumentExtractResponse:
    """Extract content from a Web URL into DocumentExtractResponse."""
    doc_ir = load_document(url, input_type=InputType.URL)
    return format_doc_ir_response(doc_ir, url, InputType.URL)


def extract_prompt_text(prompt: str) -> DocumentExtractResponse:
    """Synthesize content from a user prompt into DocumentExtractResponse."""
    doc_ir = load_document(prompt, input_type=InputType.PROMPT)
    return format_doc_ir_response(doc_ir, "user_prompt", InputType.PROMPT)
