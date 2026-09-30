import re
from pathlib import Path
from app.core.ir import Block, DocIR, SourceRef
from app.services.ingest.base import DocumentExtractor
from app.services.ingest.hierarchy import normalize_doc_ir


class MarkdownExtractor(DocumentExtractor):
    def extract(self, file_path: str) -> DocIR:
        path = Path(file_path)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        file_bytes = content.encode("utf-8")
        lines = content.splitlines()
        blocks: list[Block] = []

        for line_num, line in enumerate(lines, start=1):
            line_str = line.strip()
            if not line_str:
                continue

            # Header detection
            header_match = re.match(r"^(#{1,6})\s+(.*)$", line_str)
            if header_match:
                h_level = len(header_match.group(1))
                text = header_match.group(2).strip()
                level = 0 if h_level == 1 else (1 if h_level == 2 else 2)
                kind = "heading"
            elif line_str.startswith(("- ", "* ", "+ ", "1. ", "2. ")):
                text = re.sub(r"^([\-*+]|\d+\.)\s+", "", line_str).strip()
                level = 3
                kind = "bullet"
            else:
                text = line_str
                level = 3
                kind = "body"

            blocks.append(
                Block(
                    level=level,
                    text=text,
                    kind=kind,
                    source=SourceRef(file=path.name, locator=f"line:{line_num}")
                )
            )

        return normalize_doc_ir(blocks, file_bytes, path.name)
