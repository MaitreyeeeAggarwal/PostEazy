from pathlib import Path
from app.core.ir import DocIR
from app.pipelines.faceless_video.ingest.pptx import PPTXExtractor
from app.pipelines.faceless_video.ingest.pdf import PDFExtractor
from app.pipelines.faceless_video.ingest.docx import DOCXExtractor
from app.pipelines.faceless_video.ingest.markdown import MarkdownExtractor


def load_document(file_path: str) -> DocIR:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".pptx", ".ppt"):
        extractor = PPTXExtractor()
    elif suffix == ".pdf":
        extractor = PDFExtractor()
    elif suffix in (".docx", ".doc"):
        extractor = DOCXExtractor()
    elif suffix in (".md", ".markdown", ".txt"):
        extractor = MarkdownExtractor()
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    return extractor.extract(file_path)
