from .fixtures import make_simple_epub, make_multi_image_epub
from epub2pdf.epub_parser import parse_epub
from epub2pdf.html_normalizer import build_combined_html


def test_images_inlined_as_data_uri_no_leftover_wrapper_tags(tmp_path):
    path = str(tmp_path / "fixture.epub")
    make_simple_epub(path)
    doc = parse_epub(path)
    html_str = build_combined_html(doc)

    assert "data:image/jpeg;base64," in html_str
    assert "images/red.jpg" not in html_str, "raw relative src should be replaced, not duplicated"
    assert html_str.count("<html") == 1, "fragment parsing must not leak extra <html> wrappers"
    assert html_str.count("<body") == 1


def test_bookmark_css_present_for_outline_generation(tmp_path):
    path = str(tmp_path / "fixture.epub")
    make_simple_epub(path)
    doc = parse_epub(path)
    html_str = build_combined_html(doc)

    assert "bookmark-level: 1" in html_str
    assert "<h1>Chapter 1</h1>" in html_str
    assert "<h1>Chapter 2</h1>" in html_str


def test_multiple_image_formats_all_inlined(tmp_path):
    path = str(tmp_path / "fixture2.epub")
    make_multi_image_epub(path)
    doc = parse_epub(path)
    html_str = build_combined_html(doc)

    assert html_str.count("data:image/png;base64,") == 2
