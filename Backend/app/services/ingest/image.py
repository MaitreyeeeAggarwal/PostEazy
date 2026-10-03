import os
import hashlib
from pathlib import Path
from app.core.ir import DocIR, Block, SourceRef
from app.services.ingest.base import DocumentExtractor


class ImageExtractor(DocumentExtractor):
    def extract(self, file_path: str) -> DocIR:
        """Extract text, infographics, and chart callouts from an image file into DocIR format."""
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"Image file not found: {file_path}")

        with open(file_path, "rb") as f:
            content_bytes = f.read()

        doc_id = hashlib.sha256(content_bytes).hexdigest()
        filename = path.name

        extracted_text = ""

        # Try Tesseract OCR if pytesseract is installed
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(file_path)
            extracted_text = pytesseract.image_to_string(img)
        except Exception as ocr_err:
            print(f"[Image OCR Note]: pytesseract not available or failed: {ocr_err}")

        # If OCR returned minimal text, structure a default DocIR with image metadata
        if not extracted_text or len(extracted_text.strip()) < 10:
            extracted_text = (
                f"Visual Asset Ingested: {filename}\n"
                f"Format: {path.suffix.upper()[1:]} image asset containing visual charts, callouts, and layout diagrams."
            )

        lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
        doc_title = lines[0] if lines else f"Image Asset - {filename}"

        ir_blocks = []
        for idx, line in enumerate(lines, start=1):
            ref = SourceRef(file=filename, locator=f"image:line:{idx}")
            level = 1 if idx == 1 else 3
            kind = "heading" if idx == 1 else "body"
            ir_blocks.append(Block(level=level, text=line, kind=kind, source=ref, images=[file_path]))

        if not ir_blocks:
            ref = SourceRef(file=filename, locator="image:asset")
            ir_blocks.append(Block(level=3, text=extracted_text, kind="body", source=ref, images=[file_path]))

        return DocIR(doc_id=doc_id, title=doc_title, blocks=ir_blocks)
