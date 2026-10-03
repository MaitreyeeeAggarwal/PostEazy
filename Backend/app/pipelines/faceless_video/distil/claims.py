import difflib
import re
from typing import List
from pydantic import BaseModel
from app.core.ir import Block, Claim, DocIR, SourceRef
from app.pipelines.faceless_video.core.llm import get_llm_client
from app.pipelines.faceless_video.distil.salience import compute_salience
from app.pipelines.faceless_video.distil.dedupe import deduplicate_claims


class ClaimResponseItem(BaseModel):
    text: str
    kind: str = "stat"
    verbatim_quote: str
    salience_rating: float = 0.7
    surprise_score: int = 5


class ClaimExtractorOutput(BaseModel):
    claims: list[ClaimResponseItem]


def verify_attribution(quote: str, chunk_blocks: list[Block]) -> tuple[bool, SourceRef]:
    """Checks if verbatim quote matches source blocks with >= 90% similarity."""
    quote_clean = quote.strip().lower()
    best_ratio = 0.0
    best_source = chunk_blocks[0].source

    for block in chunk_blocks:
        block_text = block.text.lower()
        if quote_clean in block_text:
            return True, block.source
        ratio = difflib.SequenceMatcher(None, quote_clean, block_text).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_source = block.source

    return best_ratio >= 0.85, best_source


def extract_claims(doc: DocIR) -> list[Claim]:
    """Stage 2: Chunk document, extract atomic claims via NVIDIA LLM (or fallback), verify attribution, dedupe."""
    llm = get_llm_client()
    raw_claims: list[Claim] = []

    # 1. Chunk blocks by section/heading (max 12 blocks per chunk for fast LLM response)
    chunks: list[list[Block]] = []
    current_chunk: list[Block] = []

    for block in doc.blocks:
        if (block.level <= 2 or len(current_chunk) >= 12) and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [block]
        else:
            current_chunk.append(block)
    if current_chunk:
        chunks.append(current_chunk)

    # 2. Extract claims per chunk
    for chunk in chunks:
        chunk_text = "\n".join([f"[{b.source.locator}] ({b.kind}): {b.text}" for b in chunk])

        if llm.is_configured:
            prompt = (
                f"Extract 3 to 8 atomic, high-impact claims from this document section.\n"
                f"Rules:\n"
                f"1. Each claim must present ONE single idea under 20 words.\n"
                f"2. Rate surprise_score (1 to 10): 10 = highly surprising, counter-intuitive, or shocking stat; 1 = boring setup.\n"
                f"3. Include the verbatim_quote sentence from the text.\n\n"
                f"SECTION TEXT:\n{chunk_text}"
            )
            try:
                result = llm.complete_structured(
                    prompt=prompt,
                    response_schema=ClaimExtractorOutput,
                    system_prompt="You are an expert document analyst distilling viral claims for high-retention video."
                )
                for item in result.claims:
                    is_valid, source_ref = verify_attribution(item.verbatim_quote, chunk)
                    if is_valid:
                        src_block = next((b for b in chunk if b.source.locator == source_ref.locator), chunk[0])
                        img_path = src_block.images[0] if src_block.images else (next((b.images[0] for b in chunk if b.images), None))
                        salience = compute_salience(item.text, src_block, item.salience_rating)
                        raw_claims.append(
                            Claim(
                                text=item.text,
                                salience=salience,
                                surprise_score=max(1, min(10, item.surprise_score)),
                                kind=item.kind if item.kind in ("stat", "contrast", "definition", "consequence", "step", "quote") else "stat",
                                source=source_ref,
                                image_path=img_path
                            )
                        )
                continue
            except Exception as e:
                print(f"[Distil] NVIDIA LLM call failed or skipped: {e}. Falling back to rule-based extraction.")

        # Deterministic Rule-Based Fallback
        for b in chunk:
            img_path = b.images[0] if b.images else (next((blk.images[0] for blk in chunk if blk.images), None))
            sentences = re.split(r"(?<=[.!?])\s+", b.text)
            for s in sentences:
                s_clean = s.strip()
                if len(s_clean) >= 15 and len(s_clean.split()) <= 25:
                    salience = compute_salience(s_clean, b, 0.6)
                    has_number = bool(re.search(r"\d+", s_clean))
                    kind = "stat" if has_number else "definition"
                    surprise = 9 if has_number and ("%" in s_clean or "$" in s_clean) else (7 if has_number else 4)
                    raw_claims.append(
                        Claim(
                            text=s_clean,
                            salience=salience,
                            surprise_score=surprise,
                            kind=kind,
                            source=b.source,
                            image_path=img_path
                        )
                    )

    # 3. Deduplicate and return
    return deduplicate_claims(raw_claims)
