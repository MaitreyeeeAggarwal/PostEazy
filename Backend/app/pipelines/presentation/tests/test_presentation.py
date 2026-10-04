import pytest
from app.core.ir import DocIR, Block, SourceRef
from app.pipelines.presentation.core.llm_planner import plan_presentation_deck
from app.pipelines.presentation.render.html_renderer import render_presentation_html


def test_presentation_planner_rule_fallback():
    ref = SourceRef(file="test.pdf", locator="page:1")
    doc = DocIR(
        doc_id="test_123",
        title="AI Automation in Enterprise Workflows",
        blocks=[
            Block(level=1, text="AI Automation Overview", kind="heading", source=ref),
            Block(level=3, text="Implementing generative AI tools increases team output by 300%.", kind="body", source=ref),
            Block(level=3, text="Key architectural pillars require security, scalability, and integration.", kind="body", source=ref),
            Block(level=3, text="First step is workflow mapping followed by pipeline deployment.", kind="body", source=ref)
        ]
    )

    deck = plan_presentation_deck(doc, theme="bold_tech")
    assert deck.title.startswith("Presentation:")
    assert len(deck.slides) >= 4
    assert deck.slides[0].layout.value == "title_hero"


def test_html_presentation_renderer():
    ref = SourceRef(file="test.pdf", locator="page:1")
    doc = DocIR(
        doc_id="test_456",
        title="Sample Presentation",
        blocks=[Block(level=1, text="Sample Text for Presentation Slide", kind="heading", source=ref)]
    )

    deck = plan_presentation_deck(doc, theme="minimalist_editorial")
    html_out = render_presentation_html(deck)
    assert "<!DOCTYPE html>" in html_out
    assert "Sample Presentation" in html_out
    assert "Minimalist Editorial" in html_out or "#fcf8f3" in html_out
