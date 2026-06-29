import os

from .fixtures import make_simple_epub
from epub2pdf.epub_parser import parse_epub
from epub2pdf.html_normalizer import build_combined_html
from epub2pdf.pdf_renderer import render_to_pdf


def test_pdf_is_created_and_nonempty(tmp_path):
    epub_path = str(tmp_path / "fixture.epub")
    pdf_path = str(tmp_path / "fixture.pdf")
    make_simple_epub(epub_path)
    doc = parse_epub(epub_path)
    html_str = build_combined_html(doc)
    render_to_pdf(html_str, pdf_path)

    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000


def test_letter_page_size_option(tmp_path):
    epub_path = str(tmp_path / "fixture.epub")
    pdf_path = str(tmp_path / "fixture_letter.pdf")
    make_simple_epub(epub_path)
    doc = parse_epub(epub_path)
    html_str = build_combined_html(doc)
    render_to_pdf(html_str, pdf_path, page_size="LETTER")

    assert os.path.exists(pdf_path)
