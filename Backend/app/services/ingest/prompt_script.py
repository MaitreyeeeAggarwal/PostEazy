import hashlib
from app.core.ir import DocIR, Block, SourceRef
from app.services.ingest.base import DocumentExtractor


class PromptSynthesizer(DocumentExtractor):
    def extract(self, prompt_text: str) -> DocIR:
        """Synthesize a structured DocIR outline directly from a user prompt or topic request."""
        prompt = prompt_text.strip()
        if not prompt:
            raise ValueError("Prompt text cannot be empty.")

        doc_id = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        
        # Derive concise document title from prompt
        words = prompt.split()
        short_title = " ".join(words[:6]) + ("..." if len(words) > 6 else "")
        doc_title = f"Topic Prompt: {short_title}"

        ref_title = SourceRef(file="user_prompt", locator="prompt:topic")
        ref_body = SourceRef(file="user_prompt", locator="prompt:concept")

        ir_blocks = [
            Block(level=0, text=short_title.upper(), kind="heading", source=ref_title),
            Block(
                level=3,
                text=f"User Generation Request: {prompt}. Focus on high-impact insights, key takeaways, and engagement.",
                kind="body",
                source=ref_body
            )
        ]

        return DocIR(doc_id=doc_id, title=doc_title, blocks=ir_blocks)
