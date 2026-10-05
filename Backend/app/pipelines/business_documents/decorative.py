"""Topic-aware decorative assets for business-document exports.

The source asset pack is intentionally reused here rather than introducing
another icon family. Data URIs keep generated HTML self-contained for preview,
download, and PDF conversion workflows.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

from app.schemas import AdvisoryReportDraft, BusinessDocumentDraft


ASSET_DIR = Path(__file__).parents[1] / "assets" / "decorative" / "stickers"


@lru_cache(maxsize=32)
def asset_data_uri(name: str) -> str:
    path = ASSET_DIR / name
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def document_decoration_names(draft: BusinessDocumentDraft) -> list[str]:
    """Pick a restrained, relevant three-sticker set for a document's subject."""
    text = " ".join(
        [draft.title]
        + ([draft.assessment] if isinstance(draft, AdvisoryReportDraft) else [draft.overview])
    ).lower()
    if any(word in text for word in ("security", "system", "automation", "technology", "ai", "data")):
        names = ["brain.png", "code_brackets.png", "arrow_up_right.png"]
    elif any(word in text for word in ("risk", "delay", "dependency", "decline", "gap", "failure")):
        names = ["target.png", "lightning_purple.png", "arrow_up_right.png"]
    elif any(word in text for word in ("revenue", "growth", "cost", "budget", "sales", "performance", "%")):
        names = ["chart_up.png", "target.png", "arrow_up_right.png"]
    else:
        names = ["sparkle_purple.png", "target.png", "arrow_up_right.png"]
    return names


def document_decorations(draft: BusinessDocumentDraft) -> list[str]:
    return [asset_data_uri(name) for name in document_decoration_names(draft)]


def document_decoration_paths(draft: BusinessDocumentDraft) -> list[Path]:
    return [ASSET_DIR / name for name in document_decoration_names(draft) if (ASSET_DIR / name).exists()]
