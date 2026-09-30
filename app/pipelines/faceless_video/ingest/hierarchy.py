import re
import unicodedata
from collections import Counter
from typing import List
from core.ir import Block, DocIR
from core.hashing import hash_bytes

BULLET_PATTERN = re.compile(r"^[\s•\-–—◦►*]+\s*")
SMART_QUOTES_MAP = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"
})

def clean_text(text: str) -> str:
    """Normalizes text encoding, collapses whitespace, and straightens quotes."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(SMART_QUOTES_MAP)
    text = BULLET_PATTERN.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize_doc_ir(blocks: list[Block], file_bytes: bytes, filename: str) -> DocIR:
    """Performs cleaning, noise filtering, and slide/page furniture deduplication."""
    doc_id = hash_bytes(file_bytes)
    cleaned_blocks: list[Block] = []

    # 1. Clean strings and filter out trivial noise (<3 chars, standalone page numbers)
    for b in blocks:
        text = clean_text(b.text)
        if len(text) < 3 or re.match(r"^(page\s*)?\d+(\s*of\s*\d+)?$", text, re.IGNORECASE):
            continue
        b.text = text
        cleaned_blocks.append(b)

    # 2. Slide/Page furniture deduplication (exact-match blocks repeating > 2 times)
    text_counts = Counter(b.text for b in cleaned_blocks if b.level >= 2)
    deduped_blocks: list[Block] = []
    for b in cleaned_blocks:
        if b.level >= 2 and text_counts[b.text] > 2:
            # Skip recurring template furniture (agenda, slide header footers)
            continue
        deduped_blocks.append(b)

    # 3. Infer Title if not explicitly marked
    title = filename
    for b in deduped_blocks:
        if b.level == 0:
            title = b.text
            break
        elif b.level == 1 and title == filename:
            title = b.text

    return DocIR(doc_id=doc_id, title=title, blocks=deduped_blocks)
