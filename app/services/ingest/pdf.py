import fitz  # PyMuPDF
from collections import Counter
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

        # Pass 1: Gather spans and font size statistics
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            spans = []
            for b in blocks:
                if b.get("type") == 0:  # Text block
                    for line in b.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                size = round(span.get("size", 10), 1)
                                bbox = span.get("bbox", (0, 0, 0, 0))
                                flags = span.get("flags", 0)
                                font_sizes.append(size)
                                spans.append({
                                    "text": text,
                                    "size": size,
                                    "bbox": bbox,
                                    "flags": flags,
                                    "page": page_num + 1
                                })
            page_spans.append(spans)

        # Mode of font sizes is body text
        mode_size = Counter(font_sizes).most_common(1)[0][0] if font_sizes else 10.0

        media_dir = Path("./data/media") / path.stem
        media_dir.mkdir(parents=True, exist_ok=True)

        ir_blocks: list[Block] = []

        # Pass 2: Classify headings, extract page images, and build reading order
        for page_num, spans in enumerate(page_spans, start=1):
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

            # Sort spans by x-center for 2-column detection
            spans_sorted = sorted(spans, key=lambda s: (s["bbox"][1] // 20, s["bbox"][0]))
            
            page_first_block_idx = len(ir_blocks)

            for span in spans_sorted:
                text = span["text"]
                size = span["size"]
                flags = span["flags"]
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
        return normalize_doc_ir(ir_blocks, file_bytes, path.name)
