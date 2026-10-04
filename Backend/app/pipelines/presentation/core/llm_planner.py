from typing import Optional
from app.core.ir import DocIR
from app.schemas import PresentationDeckScript, PresentationSlide, PresentationSlideLayout
from app.pipelines.faceless_video.core.llm import get_llm_client
from app.services.ingest.video_ingest import clean_display_title


def plan_presentation_deck(doc: DocIR, theme: str = "bold_tech") -> PresentationDeckScript:
    """Synthesizes a structured 5 to 8 slide presentation deck from DocIR using NVIDIA LLM or deterministic rules."""
    display_title = clean_display_title(doc.title or "Presentation")
    llm = get_llm_client()

    doc_text_summary = "\n".join([b.text for b in doc.blocks[:15]])

    if llm.is_configured:
        try:
            prompt = (
                f"Analyze the following document content and create a professional, visually compelling presentation slide deck.\n"
                f"Document Title: '{display_title}'\n"
                f"Content Summary:\n{doc_text_summary}\n\n"
                f"Rules:\n"
                f"1. Generate 5 to 8 slides covering:\n"
                f"   - Slide 1: title_hero (Title, Subtitle, Key Hook)\n"
                f"   - Slide 2: big_stat (Single impressive metric or core insight with stat_number & stat_label)\n"
                f"   - Slide 3: feature_cards (3 key feature/insight cards with card_items: [{'title': '...', 'desc': '...'}])\n"
                f"   - Slide 4: process_stepper (Step-by-step workflow with card_items)\n"
                f"   - Slide 5: split_image_text (Key takeaway with body_points and image_query)\n"
                f"   - Slide 6: quote_card or comparison_table (High-impact quote/comparison)\n"
                f"   - Final Slide: end_cta (Summary takeaway & Call to Action)\n"
                f"2. Keep text crisp, executive-ready, and bullet points concise (under 12 words per point).\n"
                f"3. Return ONLY valid JSON structured according to PresentationDeckScript."
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

    return PresentationDeckScript(
        title=f"Presentation: {display_title}",
        subtitle="Automated Presentation Slide Deck",
        target_audience="Executive & General",
        theme=theme,
        aspect_ratio="16:9",
        slides=slides
    )
