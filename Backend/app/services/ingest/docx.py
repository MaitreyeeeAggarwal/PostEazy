from pathlib import Path
from docx import Document
from app.core.ir import Block, DocIR, SourceRef
from app.services.ingest.base import DocumentExtractor
from app.services.ingest.hierarchy import normalize_doc_ir


class DOCXExtractor(DocumentExtractor):
    def extract(self, file_path: str) -> DocIR:
        path = Path(file_path)
        with open(path, "rb") as f:
            file_bytes = f.read()

        doc = Document(file_path)
        blocks: list[Block] = []

        media_dir = Path("./data/media") / path.stem
        media_dir.mkdir(parents=True, exist_ok=True)
        img_counter = 0

        for p_idx, p in enumerate(doc.paragraphs, start=1):
            text = p.text.strip()
            
            # Check for embedded images in paragraph xml elements
            p_images = []
            try:
                for blip in p._element.xpath('.//a:blip'):
                    r_id = blip.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                    if r_id and r_id in p.part.rels:
                        rel = p.part.rels[r_id]
                        if "image" in rel.target_ref:
                            img_counter += 1
                            img_path = media_dir / f"docx_img_{p_idx}_{img_counter}.png"
                            with open(img_path, "wb") as f_img:
                                f_img.write(rel.target_part.blob)
                            p_images.append(str(img_path))
            except Exception as err:
                print(f"[DOCXExtractor] Warning extracting image for para {p_idx}: {err}")

            if not text and not p_images:
                continue

            # Fallback text if paragraph only contains an image
            if not text and p_images:
                text = f"[Figure {img_counter}]"

            style_name = p.style.name.lower() if p.style else ""
            if "title" in style_name:
                level = 0
                kind = "heading"
            elif "heading 1" in style_name:
                level = 1
                kind = "heading"
            elif "heading 2" in style_name:
                level = 2
                kind = "heading"
            elif "list" in style_name or "bullet" in style_name:
                level = 3
                kind = "bullet"
            else:
                level = 3
                kind = "body"

            blocks.append(
                Block(
                    level=level,
                    text=text,
                    kind=kind,
                    source=SourceRef(file=path.name, locator=f"para:{p_idx}"),
                    images=p_images
                )
            )

        return normalize_doc_ir(blocks, file_bytes, path.name)
