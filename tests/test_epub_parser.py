from .fixtures import make_simple_epub, make_multi_image_epub, KNOWN_TEXT_CH1, KNOWN_TEXT_CH2
from epub2pdf.epub_parser import parse_epub, plain_text, referenced_image_hrefs


def test_parses_simple_fixture(tmp_path):
    path = str(tmp_path / "fixture.epub")
    make_simple_epub(path)
    doc = parse_epub(path)

    assert doc.title == "Fidelity Test Book"
    assert doc.author == "Test Author"
    assert len(doc.spine_html) == 2, "nav document should be excluded from spine content"
    assert len(doc.images) == 1
    assert len(doc.toc) == 2

    text = plain_text(doc)
    assert KNOWN_TEXT_CH1 in text
    assert KNOWN_TEXT_CH2 in text
    assert "Fidelity Test Book" not in text, "nav/TOC text must not leak into body content"


def test_referenced_images_excludes_orphans(tmp_path):
    path = str(tmp_path / "fixture2.epub")
    make_multi_image_epub(path)
    doc = parse_epub(path)

    # the fixture bundles 3 image files but only 2 are referenced in content
    assert len(doc.images) == 3
    assert len(referenced_image_hrefs(doc)) == 2


def test_nested_toc_sections_have_no_href(tmp_path):
    path = str(tmp_path / "fixture2.epub")
    make_multi_image_epub(path)
    doc = parse_epub(path)

    section_entries = [e for e in doc.toc if not e.href]
    content_entries = [e for e in doc.toc if e.href]
    assert len(section_entries) == 1  # the "Part Two" grouping label
    assert len(content_entries) == 3


def test_unicode_metadata_and_text_preserved(tmp_path):
    path = str(tmp_path / "fixture2.epub")
    make_multi_image_epub(path)
    doc = parse_epub(path)

    assert "Café" in doc.title
    assert "É" in doc.author
    text = plain_text(doc)
    assert "résumé" in text
    assert "—" in text
