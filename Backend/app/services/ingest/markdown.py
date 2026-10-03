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

        media_dir = Path("./data/media") / path.stem
        media_dir.mkdir(parents=True, exist_ok=True)

        table_buffer: list[str] = []
        table_start_line = 0

        def _flush_table_buffer():
            nonlocal table_buffer, table_start_line
            if not table_buffer:
                return
            from app.services.ingest.table_parser import parse_markdown_table
            from app.pipelines.faceless_video.render.chart import generate_chart_from_table

            t_data = parse_markdown_table(table_buffer)
            table_images = []
            if t_data:
                chart_path = media_dir / f"table_chart_line_{table_start_line}.png"
                chart_file = generate_chart_from_table(t_data, str(chart_path))
                table_images.append(chart_file)

            summary_text = " | ".join([l.strip("|").replace("|", "-") for l in table_buffer if not re.match(r"^\|[\s\-:|]+\|$", l.strip())])
            blocks.append(
                Block(
                    level=3,
                    text=summary_text[:300],
                    kind="table",
                    source=SourceRef(file=path.name, locator=f"line:{table_start_line}"),
                    images=table_images
                )
            )
            table_buffer = []

        for line_num, line in enumerate(lines, start=1):
            line_str = line.strip()
            if not line_str:
                _flush_table_buffer()
                continue

            # Table detection
            if line_str.startswith("|") and line_str.endswith("|"):
                if not table_buffer:
                    table_start_line = line_num
                table_buffer.append(line_str)
                continue
            else:
                _flush_table_buffer()

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

        _flush_table_buffer()
        return normalize_doc_ir(blocks, file_bytes, path.name)
