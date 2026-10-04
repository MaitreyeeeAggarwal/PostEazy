import pymupdf as fitz  # PyMuPDF
from collections import Counter
from statistics import median
from pathlib import Path
from app.core.ir import Block, DocIR, SourceRef
from app.services.ingest.base import DocumentExtractor
from app.services.ingest.hierarchy import normalize_doc_ir


class PDFExtractor(DocumentExtractor):
    def extract(self, file_path: str) -> DocIR:
        path = Path(file_path)
        doc = fitz.open(file_path)
        with open(path, "rb") as f:
            file_bytes = f.read()

        font_sizes = []
        page_spans = []

        # Pass 1: Gather paragraph-sized text blocks and font size statistics.
        # A PDF "span" is only a run with the same styling and may split a word
        # or sentence. Business-document planners need meaningful paragraphs, not
        # individual spans such as "Mai" / "ee Agga".
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_blocks = page.get_text("dict", sort=True)["blocks"]
            paragraphs = []
            for b in text_blocks:
                if b.get("type") == 0:  # Text block
                    line_texts = []
                    line_sizes = []
                    line_flags = []
                    for line in b.get("lines", []):
                        spans = line.get("spans", [])
                        # Do not introduce spaces between spans: visual styling can
                        # split a single word into separate spans.
                        text = "".join(span.get("text", "") for span in spans).strip()
                        if not text:
                            continue
                        line_texts.append(text)
                        for span in spans:
                            span_text = span.get("text", "").strip()
                            if span_text:
                                size = round(span.get("size", 10), 1)
                                font_sizes.append(size)
                                line_sizes.append(size)
                                line_flags.append(span.get("flags", 0))
                    if line_texts:
                        paragraphs.append({
                            "text": " ".join(line_texts),
                            "size": median(line_sizes) if line_sizes else 10.0,
                            "bbox": b.get("bbox", (0, 0, 0, 0)),
                            "flags": max(line_flags, default=0),
                            "page": page_num + 1,
                        })
            page_spans.append(paragraphs)

        # Mode of font sizes is body text
        mode_size = Counter(font_sizes).most_common(1)[0][0] if font_sizes else 10.0

        media_dir = Path("./data/media") / path.stem
        media_dir.mkdir(parents=True, exist_ok=True)

        ir_blocks: list[Block] = []

        # Pass 2: Classify headings, extract page images, and build reading order
        for page_num, paragraphs in enumerate(page_spans, start=1):
            locator = f"page:{page_num}"
            page_obj = doc[page_num - 1]
            
            # Extract embedded images/maps/graphs from current page
            page_image_paths = []
            try:
                image_list = page_obj.get_images(full=True)
                for img_idx, img_info in enumerate(image_list, start=1):
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image.get("image")
                    image_ext = base_image.get("ext", "png")
                    w = base_image.get("width", 0)
                    h = base_image.get("height", 0)
                    
                    # Filter out tiny icon / bullet images
                    if w >= 100 and h >= 100 and image_bytes:
                        img_path = media_dir / f"page_{page_num}_img_{img_idx}.{image_ext}"
                        with open(img_path, "wb") as f_img:
                            f_img.write(image_bytes)
                        page_image_paths.append(str(img_path))
            except Exception as err:
                print(f"[PDFExtractor] Warning extracting images for page {page_num}: {err}")

            # The PDF engine returns visual blocks. Sorting by top then left keeps
            # prose paragraphs intact while retaining sensible table-cell ordering.
            paragraphs_sorted = sorted(paragraphs, key=lambda p: (round(p["bbox"][1], 1), p["bbox"][0]))
            
            page_first_block_idx = len(ir_blocks)

            for paragraph in paragraphs_sorted:
                text = paragraph["text"]
                size = paragraph["size"]
                flags = paragraph["flags"]
                is_bold = bool(flags & (1 << 4))

                if size >= mode_size * 1.5:
                    level = 1  # Title/H1
                    kind = "heading"
                elif size >= mode_size * 1.15:
                    level = 2  # H2
                    kind = "heading"
                elif is_bold:
                    level = 3  # Lead-in
                    kind = "bullet"
                else:
                    level = 3  # Body
                    kind = "body"

                ir_blocks.append(
                    Block(
                        level=level,
                        text=text,
                        kind=kind,
                        source=SourceRef(file=path.name, locator=locator)
                    )
                )

            # Attach extracted page images to the first block on this page
            if page_image_paths and len(ir_blocks) > page_first_block_idx:
                ir_blocks[page_first_block_idx].images.extend(page_image_paths)

        doc.close()
        normalized = normalize_doc_ir(ir_blocks, file_bytes, path.name)
        # Some PDFs use a title font that is not sufficiently larger than the
        # document body to be classified as a heading. Prefer the first
        # extracted text block over a temporary upload filename in that case.
        if normalized.title == path.name and normalized.blocks:
            normalized.title = normalized.blocks[0].text
        return normalized
