import re
import hashlib
from urllib.parse import urlparse
import httpx
from html.parser import HTMLParser

from app.core.ir import DocIR, Block, SourceRef
from app.services.ingest.base import DocumentExtractor


class SimpleHTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.blocks = []
        self.current_tag = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag.lower()
        if tag.lower() == 'title':
            self.in_title = True
        elif tag.lower() in ('p', 'h1', 'h2', 'h3', 'h4', 'li', 'article', 'section'):
            self.current_text = []

    def handle_endtag(self, tag):
        if tag.lower() == 'title':
            self.in_title = False
        elif tag.lower() in ('p', 'h1', 'h2', 'h3', 'h4', 'li'):
            text = " ".join("".join(self.current_text).split())
            if text and len(text) > 15:
                level = 1 if tag.lower() in ('h1', 'h2') else 3
                kind = "heading" if level == 1 else "body"
                self.blocks.append((level, kind, text))
            self.current_text = []

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        elif self.current_tag not in ('script', 'style', 'noscript', 'head'):
            self.current_text.append(data)


class URLExtractor(DocumentExtractor):
    def extract(self, url: str) -> DocIR:
        """Fetch web URL content and convert into DocIR structure."""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL format: '{url}'")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PostEazyIngest/1.0"
        }

        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                html_content = resp.text
        except Exception as e:
            raise ValueError(f"Failed to fetch content from URL '{url}': {str(e)}")

        parser = SimpleHTMLTextExtractor()
        parser.feed(html_content)

        doc_id = hashlib.sha256(url.encode("utf-8")).hexdigest()
        doc_title = parser.title.strip() or f"Article from {parsed.netloc}"

        ir_blocks = []
        for idx, (level, kind, text) in enumerate(parser.blocks, start=1):
            ref = SourceRef(file=url, locator=f"url:block:{idx}")
            ir_blocks.append(Block(level=level, text=text, kind=kind, source=ref))

        if not ir_blocks:
            # Fallback if parser extracted no blocks
            clean_text = re.sub(r'<[^>]+>', ' ', html_content)
            clean_text = " ".join(clean_text.split())
            if len(clean_text) > 50:
                ref = SourceRef(file=url, locator="url:body")
                ir_blocks.append(Block(level=3, text=clean_text[:4000], kind="body", source=ref))

        return DocIR(doc_id=doc_id, title=doc_title, blocks=ir_blocks)
