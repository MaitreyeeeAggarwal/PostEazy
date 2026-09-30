import os
import tempfile
from pathlib import Path
from fastapi import UploadFile, HTTPException, status

from app.config import settings
from app.schemas import DocumentExtractResponse
from app.core.ir import DocIR, Block
from app.services.ingest.base import DocumentExtractor
from app.services.ingest.pptx import PPTXExtractor
from app.services.ingest.pdf import PDFExtractor
from app.services.ingest.docx import DOCXExtractor
from app.services.ingest.markdown import MarkdownExtractor

ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".ppt", ".docx", ".doc", ".txt", ".md", ".markdown"}


def load_document(file_path: str) -> DocIR:
    """
    Common data extractor used across all pipelines (Static Posts & Faceless Video).
    Extracts structured document IR (DocIR) with section levels, source locators, and images.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".pptx", ".ppt"):
        extractor: DocumentExtractor = PPTXExtractor()
    elif suffix == ".pdf":
        extractor = PDFExtractor()
    elif suffix in (".docx", ".doc"):
        extractor = DOCXExtractor()
    elif suffix in (".md", ".markdown", ".txt"):
        extractor = MarkdownExtractor()
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    return extractor.extract(file_path)


async def extract_document_text(file: UploadFile) -> DocumentExtractResponse:
    """
    HTTP upload handler that extracts text and metadata into a DocumentExtractResponse.
    Shared by both Pipeline A (Static Posts) and Pipeline B (Faceless Video).
    """
    filename = file.filename or "uploaded_doc"
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

    # Save to temp file for extraction
    temp_dir = Path(settings.WORK_DIR) / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file_path = temp_dir / f"upload_{os.urandom(8).hex()}{ext}"

    try:
        with open(temp_file_path, "wb") as temp_f:
            temp_f.write(content_bytes)

        # Extract using the common document IR loader
        doc_ir: DocIR = load_document(str(temp_file_path))

        # Format blocks into page/slide text blocks
        formatted_parts = []
        locators_seen = set()

        for b in doc_ir.blocks:
            loc = b.source.locator
            if loc not in locators_seen:
                locators_seen.add(loc)
                formatted_parts.append(f"[{loc}]")
            formatted_parts.append(b.text)

        raw_text = "\n".join(formatted_parts)

        if len(raw_text.strip()) < 200:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Document contains insufficient text (likely scanned or image-only document)."
            )

        truncated = False
        if len(raw_text) > settings.MAX_SOURCE_CHARS:
            raw_text = raw_text[: settings.MAX_SOURCE_CHARS]
            truncated = True

        return DocumentExtractResponse(
            filename=filename,
            char_count=len(raw_text),
            page_or_slide_count=len(locators_seen),
            text=raw_text,
            truncated=truncated
        )

    finally:
        if temp_file_path.exists():
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
