from .fixtures import make_simple_epub, make_multi_image_epub
from epub2pdf.epub_parser import parse_epub
from epub2pdf.html_normalizer import build_combined_html
from epub2pdf.pdf_renderer import render_to_pdf
from epub2pdf.verify import verify

TEXT_SIMILARITY_FLOOR = 0.97


def _convert(epub_path: str, pdf_path: str):
    doc = parse_epub(epub_path)
    html_str = build_combined_html(doc)
    render_to_pdf(html_str, pdf_path)
    return doc


def test_simple_fixture_passes_fidelity_gate(tmp_path):
    epub_path = str(tmp_path / "fixture.epub")
    pdf_path = str(tmp_path / "fixture.pdf")
    make_simple_epub(epub_path)
    doc = _convert(epub_path, pdf_path)

    result = verify(doc, pdf_path)

    assert result.failures == [], result.failures
    assert result.passed
    assert result.text_similarity >= TEXT_SIMILARITY_FLOOR
    assert result.epub_image_count == result.pdf_image_count == 1
    assert result.epub_heading_count == result.pdf_outline_count == 2


def test_multi_image_unicode_nested_toc_fixture_passes_fidelity_gate(tmp_path):
    epub_path = str(tmp_path / "fixture2.epub")
    pdf_path = str(tmp_path / "fixture2.pdf")
    make_multi_image_epub(epub_path)
    doc = _convert(epub_path, pdf_path)

    result = verify(doc, pdf_path)

    assert result.failures == [], result.failures
    assert result.passed
    assert result.text_similarity >= TEXT_SIMILARITY_FLOOR
    assert result.epub_image_count == result.pdf_image_count == 2
    assert result.epub_heading_count == result.pdf_outline_count == 3


def test_conversion_is_deterministic(tmp_path):
    """Running the same conversion twice should produce the same fidelity
    result — guards against any source of nondeterminism (e.g. dict
    ordering, temp-file races) sneaking into the pipeline."""
    epub_path = str(tmp_path / "fixture.epub")
    make_simple_epub(epub_path)

    results = []
    for i in range(2):
        pdf_path = str(tmp_path / f"fixture_{i}.pdf")
        doc = _convert(epub_path, pdf_path)
        results.append(verify(doc, pdf_path))

    assert results[0].text_similarity == results[1].text_similarity
    assert results[0].epub_image_count == results[1].epub_image_count
    assert results[0].pdf_image_count == results[1].pdf_image_count
