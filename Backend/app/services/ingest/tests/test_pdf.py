import fitz

from app.services.ingest.pdf import PDFExtractor


def test_pdf_extractor_keeps_multiline_paragraphs_together(tmp_path):
    path = tmp_path / "content-plan.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_textbox(
        fitz.Rect(72, 72, 520, 220),
        "Maitreyee Aggarwal - Instagram Content Plan\n"
        "This paragraph contains an intact, multi-line description of a builder-strategist content niche.",
        fontsize=12,
    )
    pdf.save(path)
    pdf.close()

    doc = PDFExtractor().extract(str(path))
    texts = [block.text for block in doc.blocks]

    assert any("Maitreyee Aggarwal" in text for text in texts)
    assert any("builder-strategist content niche" in text for text in texts)
    assert "Mai" not in texts
    assert doc.title.startswith("Maitreyee Aggarwal")
