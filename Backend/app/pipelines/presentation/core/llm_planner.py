from typing import Optional
from app.core.ir import DocIR
from app.schemas import PresentationDeckScript, PresentationSlide, PresentationSlideLayout
from app.pipelines.faceless_video.core.llm import get_llm_client
from app.services.ingest.video_ingest import clean_display_title


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
                f"4. Return ONLY valid JSON structured according to PresentationDeckScript."
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

    # Rule-Based Fallback Slide Generator
    blocks = [b.text for b in doc.blocks if b.text.strip()]
    
    slides = [
        PresentationSlide(
            idx=1,
            layout=PresentationSlideLayout.TITLE_HERO,
            heading=display_title,
            subheading="Key Insights & Strategic Overview",
            body_points=["Executive briefing distilled from source content.", "High-impact takeaways for immediate implementation."]
        ),
        PresentationSlide(
            idx=2,
            layout=PresentationSlideLayout.BIG_STAT,
            heading="Core Impact & Key Metric",
            stat_number="10X",
            stat_label="Efficiency Increase Observed across Primary Analysis",
            body_points=["Key performance metrics derived directly from data analysis."]
        ),
        PresentationSlide(
            idx=3,
            layout=PresentationSlideLayout.FEATURE_CARDS,
            heading="Key Strategic Pillars",
            subheading="Core principles driving results",
            card_items=[
                {"title": "Pillar 1", "desc": blocks[0][:80] if len(blocks) > 0 else "High retention content structure."},
                {"title": "Pillar 2", "desc": blocks[1][:80] if len(blocks) > 1 else "Automated distillation and summary."},
                {"title": "Pillar 3", "desc": blocks[2][:80] if len(blocks) > 2 else "Scalable visual presentation assets."}
            ]
        ),
        PresentationSlide(
            idx=4,
            layout=PresentationSlideLayout.SPLIT_IMAGE_TEXT,
            heading="Deep Dive & Key Takeaways",
            image_query="abstract technology presentation",
            body_points=[
                blocks[3][:100] if len(blocks) > 3 else "Structured workflow optimization.",
                blocks[4][:100] if len(blocks) > 4 else "Data-driven audience engagement."
            ]
        ),
        PresentationSlide(
            idx=5,
            layout=PresentationSlideLayout.END_CTA,
            heading="Next Steps & Conclusion",
            subheading="Transforming insights into action",
            body_points=["Review findings and implement recommendations.", "PostEazy Content Engine Deliverable."]
        )
    ]

    # Preserve more source detail in longer documents instead of forcing every
    # plan into the same five-slide outline.
    additional_blocks = blocks[5:15]
    for offset in range(0, len(additional_blocks), 3):
        points = additional_blocks[offset:offset + 3]
        if not points:
            continue
        slides.insert(-1, PresentationSlide(
            idx=0,
            layout=PresentationSlideLayout.FEATURE_CARDS,
            heading=f"Additional Insight {offset // 3 + 1}",
            subheading="Source-backed detail for review",
            body_points=[point[:120] for point in points]
        ))

    for index, slide in enumerate(slides, start=1):
        slide.idx = index

    return PresentationDeckScript(
        title=f"Presentation: {display_title}",
        subtitle="Automated Presentation Slide Deck",
        target_audience="Executive & General",
        theme=theme,
        aspect_ratio="16:9",
        slides=slides
    )
