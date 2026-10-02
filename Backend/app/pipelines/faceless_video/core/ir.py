from typing import Literal, Optional
from pydantic import BaseModel, Field


# ---- IR 1: What the document actually says ----
class SourceRef(BaseModel):
    file: str
    locator: str  # e.g., "slide:12" | "page:4" | "para:88" | "line:10"
    char_span: Optional[tuple[int, int]] = None


class Block(BaseModel):
    level: int  # 0 = title, 1 = h1, 2 = h2, 3 = body, 4 = caption
    text: str
    kind: Literal["heading", "body", "bullet", "table", "caption", "notes"] = "body"
    source: SourceRef
    images: list[str] = []


class DocIR(BaseModel):
    doc_id: str  # sha256 of raw document bytes
    title: str
    blocks: list[Block]
    language: str = "en"


# ---- IR 2: What is worth saying ----
class Claim(BaseModel):
    id: int = 0
    text: str  # one atomic assertion, <= 25 words
    salience: float = Field(default=0.5, ge=0.0, le=1.0)
    kind: Literal["stat", "contrast", "definition", "consequence", "step", "quote"] = "stat"
    source: SourceRef  # never optional - source traceability guard rail
    embedding_id: Optional[str] = None
    image_path: Optional[str] = None


# ---- IR 3: The narrative arc ----
class Beat(BaseModel):
    idx: int = 0
    role: Literal["hook", "context", "body", "turn", "payoff", "cta"]
    claim_ids: list[int] = []
    narration: str  # <= 14 words formatted for typography (with digits)
    narration_spoken: str = ""  # spelled out string for TTS ("forty percent" vs "40%")
    budget_s: float = 3.4


# ---- IR 4: The shot list ----
class Fragment(BaseModel):
    words: list[str]  # <= 4 words
    emphasis: list[int] = []  # indices into words array for visual highlight


class SceneSpec(BaseModel):
    idx: int
    narration: str
    fragments: list[Fragment]  # <= 3 fragments per scene
    layout: Literal["center_stack", "lower_third", "split_left", "full_bleed_number", "document_figure", "stat_callout"] = "center_stack"
    bg_query: str
    bg_asset_id: Optional[str] = None
    doc_image_path: Optional[str] = None
    music_section: Literal["intro", "build", "drop", "outro"] = "build"
    transition: Literal["cut", "dip", "push", "fade", "crossfade", "slide", "dissolve", "zoom"] = "fade"
    duration_s: float = 3.5  # provisional until aligned audio overwrites
    word_times: list[tuple[str, float, float]] = []  # [(token, start_s, end_s)]
    source: SourceRef
