import re
from typing import Iterable, Optional
from app.core.ir import DocIR
from app.schemas import PresentationDeckScript, PresentationSlide, PresentationSlideLayout
from app.pipelines.faceless_video.core.llm import get_llm_client
from app.services.ingest.video_ingest import clean_display_title


_METRIC_RE = re.compile(r"(?<![\w.])(?:[$€£]\s?\d[\d,.]*|\d[\d,.]*\s?(?:%|x|X|days?|weeks?|months?|years?|users?|customers?|hours?))(?!\w)")
_GENERIC_HEADINGS = {
    "overview", "key insights", "key strategic pillars", "core impact & key metric",
    "deep dive & key takeaways", "next steps & conclusion", "additional insight",
}


def _clean_text(text: str, limit: int = 150) -> str:
    """Make a source phrase compact without changing its meaning."""
    value = " ".join((text or "").split()).strip(" -:;,.\u2013\u2014")
    if len(value) <= limit:
        return value
    clipped = value[:limit].rsplit(" ", 1)[0]
    return f"{clipped}\u2026"


def _source_heading(text: str, fallback: str, max_words: int = 8) -> str:
    """Return a distinct, source-derived slide heading rather than a template label."""
    source = _clean_text(text, 180)
    if not source:
        return fallback
    first_clause = re.split(r"[.:;\u2013\u2014]", source, maxsplit=1)[0].strip()
    words = first_clause.split()
    if len(words) > max_words:
        # Keep the subject and the first predicate, which makes a useful headline
        # while staying extractive instead of inventing a claim.
        verbs = {"is", "are", "was", "were", "increases", "increase", "decreases", "decrease", "requires", "require", "identifies", "identify", "enables", "enable", "drives", "drive", "should", "will", "can"}
        cut = next((idx + 2 for idx, word in enumerate(words) if word.lower().strip(",") in verbs), max_words)
        words = words[:max(4, min(max_words, cut))]
    heading = " ".join(words).strip(" -:;,.\u2013\u2014")
    if heading.lower() in _GENERIC_HEADINGS or len(heading) < 3:
        return fallback
    return heading


def _content_blocks(doc: DocIR) -> list[str]:
    title = _clean_text(doc.title).lower()
    seen: set[str] = set()
    result: list[str] = []
    for block in doc.blocks:
        text = _clean_text(block.text)
        key = text.lower()
        if not text or key == title or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _first_metric(blocks: Iterable[str]) -> tuple[str | None, str | None]:
    for block in blocks:
        match = _METRIC_RE.search(block)
        if match:
            return match.group(0).replace(" ", ""), block
    return None, None


def _action_block(blocks: Iterable[str]) -> str | None:
    action_words = ("should", "next", "recommend", "implement", "review", "launch", "prioritize", "assign", "plan")
    return next((block for block in blocks if any(word in block.lower() for word in action_words)), None)


def plan_presentation_deck(doc: DocIR, theme: str = "bold_tech") -> PresentationDeckScript:
    """Creates an editable, content-proportional presentation plan from DocIR."""
    display_title = clean_display_title(doc.title or "Presentation")
    llm = get_llm_client()

    doc_text_summary = "\n".join([b.text for b in doc.blocks[:30]])

    if llm.is_configured:
        try:
            prompt = (
                f"Analyze the following document content and create a professional, visually compelling presentation slide deck.\n"
                f"Document Title: '{display_title}'\n"
                f"Content Summary:\n{doc_text_summary}\n\n"
                f"Rules:\n"
                f"1. Choose the number of slides from the amount and structure of source content (minimum 4, maximum 12). Use one cohesive idea per slide, avoid filler, and include a conclusion only when it is warranted.\n"
                f"2. Build the deck from the available evidence, covering as appropriate:\n"
                f"   - Slide 1: title_hero (Title, Subtitle, Key Hook)\n"
                f"   - big_stat only if a defensible metric or core insight exists\n"
                f"   - feature_cards or process_stepper when the source has grouped ideas or a workflow\n"
                f"   - split_image_text, quote_card, or comparison_table only when that layout suits the content\n"
                f"   - Final Slide: end_cta for the strongest next step or summary\n"
                f"3. Keep text crisp, executive-ready, and bullet points concise (under 12 words per point).\n"
                f"4. Every slide heading must be a distinct, document-specific phrase grounded in the source. Never use generic labels such as 'Overview', 'Key Insights', 'Pillars', 'Deep Dive', or 'Next Steps'.\n"
                f"5. Return ONLY valid JSON structured according to PresentationDeckScript."
            )

            res = llm.complete_structured(
                prompt=prompt,
                response_schema=PresentationDeckScript,
                system_prompt="You are an executive presentation designer & deck strategist."
            )
            if res and res.slides:
                res.theme = theme
                return res
        except Exception as llm_err:
            print(f"[Presentation Planner Note]: LLM slide planning failed ({llm_err}). Using rule-based generator.")

    # Rule-based fallback. It intentionally keeps headings and labels tethered
    # to the source so a deck about shipping, hiring, or product adoption does
    # not collapse into the same five generic slides.
    blocks = _content_blocks(doc)
    if not blocks:
        blocks = [display_title]
    metric, metric_block = _first_metric(blocks)
    action = _action_block(blocks)
    lead = blocks[0]
    supporting = blocks[1:] or [lead]

    slides: list[PresentationSlide] = [
        PresentationSlide(
            idx=1,
            layout=PresentationSlideLayout.TITLE_HERO,
            heading=display_title,
            subheading=_clean_text(lead, 110),
            body_points=[_clean_text(supporting[0], 105)],
        )
    ]

    if metric and metric_block:
        slides.append(PresentationSlide(
            idx=0,
            layout=PresentationSlideLayout.BIG_STAT,
            heading=_source_heading(metric_block, "Measured source signal"),
            stat_number=metric,
            stat_label=_clean_text(metric_block.replace(metric, "").strip(" .,:;-"), 90),
            body_points=[_clean_text(metric_block, 120)],
        ))
    else:
        slides.append(PresentationSlide(
            idx=0,
            layout=PresentationSlideLayout.SPLIT_IMAGE_TEXT,
            heading=_source_heading(supporting[0], "Primary source finding"),
            image_query=_source_heading(supporting[0], display_title, 5),
            body_points=[_clean_text(supporting[0], 115), _clean_text(supporting[-1], 115)],
        ))

    card_source = (supporting + [lead])[:3]
    slides.append(PresentationSlide(
        idx=0,
        layout=PresentationSlideLayout.FEATURE_CARDS,
        heading=_source_heading(card_source[0], "Evidence to consider"),
        subheading="Source signals to carry into the discussion",
        card_items=[
            {"title": _source_heading(item, f"Source signal {idx}"), "desc": _clean_text(item, 105)}
            for idx, item in enumerate(card_source, start=1)
        ],
    ))

    deep_dive = supporting[2:5] or supporting[:2]
    slides.append(PresentationSlide(
        idx=0,
        layout=PresentationSlideLayout.PROCESS_STEPPER if len(deep_dive) >= 3 else PresentationSlideLayout.SPLIT_IMAGE_TEXT,
        heading=_source_heading(deep_dive[-1], "Source detail"),
        subheading=_clean_text(deep_dive[0], 105),
        image_query=_source_heading(deep_dive[-1], display_title, 5),
        body_points=[_clean_text(item, 110) for item in deep_dive],
        card_items=[
            {"title": _source_heading(item, f"Source step {idx}"), "desc": _clean_text(item, 95)}
            for idx, item in enumerate(deep_dive, start=1)
        ],
    ))

    if action:
        slides.append(PresentationSlide(
            idx=0,
            layout=PresentationSlideLayout.END_CTA,
            heading=f"{display_title}: {_source_heading(action, 'Action from the source')}",
            subheading="A source-grounded action to resolve next",
            body_points=[_clean_text(action, 130)],
        ))

    # Preserve more source detail in longer documents instead of forcing every
    # plan into the same five-slide outline.
    additional_blocks = supporting[5:15]
    for offset in range(0, len(additional_blocks), 3):
        points = additional_blocks[offset:offset + 3]
        if not points:
            continue
        slides.insert(-1, PresentationSlide(
            idx=0,
            layout=PresentationSlideLayout.FEATURE_CARDS,
            heading=_source_heading(points[0], f"Source detail {offset // 3 + 1}"),
            subheading="Additional source detail",
            body_points=[point[:120] for point in points]
        ))

    for index, slide in enumerate(slides, start=1):
        slide.idx = index

    return PresentationDeckScript(
        title=f"Presentation: {display_title}",
        subtitle="A source-grounded briefing",
        target_audience="Executive & General",
        theme=theme,
        aspect_ratio="16:9",
        slides=slides
    )
